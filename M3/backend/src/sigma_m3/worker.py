"""One local worker, protected by a PostgreSQL session advisory lock."""

import argparse
from datetime import datetime, timezone
import hashlib, json, os, time, threading
from sqlalchemy import select, text, update
from sigma_m3.core.db import database
from sigma_m3.core.errors import DomainError
from sigma_m3.models import Run
from sigma_m3.services.ingestion import import_snapshot
from sigma_m3.core.hashes import digest, code_digest
from sigma_m3.core.settings import Settings

LOCK_ID = 734100719
LOADED_CODE = code_digest()


def now():
    return datetime.now(timezone.utc)


def process_one(settings, sessions):
    with sessions.begin() as session:
        row = session.scalar(
            select(Run)
            .where(Run.status == "queued")
            .order_by(Run.created_at, Run.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return None
        row.status = "running"
        row.started_at = now()
        row.heartbeat_at = now()
        key, kind, expected_code = row.id, row.kind, row.code_sha256
    heartbeat_stop = threading.Event()

    def heartbeat():
        while not heartbeat_stop.wait(30):
            try:
                with sessions.begin() as session:
                    session.execute(
                        update(Run)
                        .where(Run.id == key, Run.status == "running")
                        .values(heartbeat_at=now())
                    )
            except Exception:
                # The primary job will surface database failure; no credentials in heartbeat logs.
                pass

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        if expected_code != code_digest() or expected_code != LOADED_CODE:
            raise DomainError(
                "code_mismatch",
                "Code changed after enqueue or worker startup; restart the worker",
            )
        if kind == "source_import":
            summary = import_snapshot(settings, sessions, key)
        elif kind == "forecast":
            from sigma_m3.services.forecast import forecast_run

            summary = forecast_run(settings, sessions, key)
        else:
            from sigma_m3.services.simulation import simulate_run

            summary = simulate_run(settings, sessions, key)
        with sessions.begin() as session:
            row = session.get(Run, key)
            row.config_sha256 = digest(row.config_snapshot)
            row.result_summary = summary
        from sigma_m3.services.verification import verify_run

        verification = verify_run(settings, sessions, key, allow_running=True)
        if expected_code != code_digest():
            raise DomainError(
                "code_mismatch",
                "Code changed during execution; keep this run failed and retry after restarting",
            )
        summary = {**summary, "verification": verification}
        with sessions.begin() as session:
            row = session.get(Run, key)
            row.config_sha256 = digest(row.config_snapshot)
            import platform, importlib.metadata

            runtime = dict(
                python=platform.python_version(),
                packages={
                    name: importlib.metadata.version(name)
                    for name in [
                        "numpy",
                        "pandas",
                        "lightgbm",
                        "prophet",
                        "fastapi",
                        "SQLAlchemy",
                        "psycopg",
                    ]
                },
            )
            folder = settings.output_root / str(key)
            folder.mkdir(parents=True, exist_ok=True)
            config_bytes = json.dumps(
                row.config_snapshot, sort_keys=True, indent=2, allow_nan=False
            ).encode()
            (folder / "config_snapshot.json").write_bytes(config_bytes)
            row.artifact_manifest = {
                **row.artifact_manifest,
                "config_snapshot.json": hashlib.sha256(config_bytes).hexdigest(),
            }
            manifest = dict(
                run_id=str(key),
                kind=kind,
                status="verified",
                source_sha256=row.source_sha256,
                code_sha256=row.code_sha256,
                config_sha256=row.config_sha256,
                target_version=row.target_version,
                config_version=row.config_version,
                assumption_version=row.assumption_version,
                seed=42,
                runtime=runtime,
                source_import_run_id=str(row.source_import_run_id)
                if row.source_import_run_id
                else None,
                forecast_run_id=str(row.forecast_run_id)
                if row.forecast_run_id
                else None,
                selection_sha256=row.selection_sha256,
                summary=summary,
                artifacts=row.artifact_manifest,
            )
            folder = settings.output_root / str(key)
            folder.mkdir(parents=True, exist_ok=True)
            staging = folder / "manifest.staging.json"
            payload = json.dumps(
                manifest, sort_keys=True, indent=2, allow_nan=False
            ).encode()
            staging.write_bytes(payload)
            os.replace(staging, folder / "manifest.json")
            row.artifact_manifest = {
                **row.artifact_manifest,
                "manifest.json": hashlib.sha256(payload).hexdigest(),
            }
            row.result_summary = summary
            row.status = "complete"
            row.finished_at = now()
            row.heartbeat_at = now()
    except Exception as exc:
        # Do not expose a raw source/path/driver traceback through run status.
        code = (
            exc.code
            if isinstance(exc, DomainError)
            else "source_import_failed"
            if kind == "source_import"
            else "worker_failed"
        )
        with sessions.begin() as session:
            row = session.get(Run, key)
            row.status = "failed"
            row.error_code = code
            row.finished_at = now()
            row.heartbeat_at = now()
            row.result_summary = {
                **row.result_summary,
                "error_type": type(exc).__name__,
            }
        # Private diagnostic for development; never returned by HTTP or staged to Git.
        import traceback

        folder = settings.output_root / str(key)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "failure.private.log").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2)
    return key


def serve(settings, once=False):
    engine, sessions = database(settings.database_url)
    try:
        with engine.connect() as lock:
            if not lock.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_ID}
            ):
                raise DomainError(
                    "worker_already_running", "A local M3 worker is already active", 409
                )
            try:
                with sessions.begin() as session:
                    session.execute(
                        update(Run)
                        .where(Run.status == "running")
                        .values(
                            status="failed", error_code="interrupted", finished_at=now()
                        )
                    )
                while True:
                    key = process_one(settings, sessions)
                    if once:
                        return key
                    if key is None:
                        time.sleep(1)
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    key = serve(Settings.from_env(), args.once)
    print("Processed one queued run" if key else "No queued run")


if __name__ == "__main__":
    main()
