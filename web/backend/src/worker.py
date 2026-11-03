"""One local worker, protected by a PostgreSQL session advisory lock."""

import argparse
from datetime import datetime, timezone
import hashlib, json, os, time, threading
from sqlalchemy import select, text, update
from core.db import database
from core.errors import DomainError
from modules.runs.models import Run
from modules.forecasting.ingestion import import_snapshot
from core.hashes import digest, code_digest
from core.settings import Settings
from core.demo import worker_heartbeat
import models  # Register every foreign-key target before a standalone worker flushes Run.

LOCK_ID = 734100719
LOADED_CODE = code_digest()


def now():
    return datetime.now(timezone.utc)


def claim_one(sessions):
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
        return row.id, row.kind, row.code_sha256


def process_one(settings, sessions, claimed=None):
    claimed = claimed or claim_one(sessions)
    if claimed is None:
        return None
    key, kind, expected_code = claimed
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
            from modules.forecasting.service import forecast_run

            summary = forecast_run(settings, sessions, key)
        else:
            from modules.inventory.simulation import simulate_run

            summary = simulate_run(settings, sessions, key)
        with sessions.begin() as session:
            row = session.get(Run, key)
            row.config_sha256 = digest(row.config_snapshot)
            row.result_summary = summary
        from modules.runs.verification import verify_run

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


def demo_process_one(settings, sessions):
    """Keep the lock/heartbeat in the parent; own and bound the complete job tree."""
    import subprocess, sys
    import psutil
    from web.backend.scripts.demo_stack import stop
    claimed = claim_one(sessions)
    if claimed is None:
        return None
    key = claimed[0]
    # Producers create a new artifact directory themselves (forecast uses exist_ok=False).
    private_root = settings.output_root.parent
    env = {k: v for k, v in os.environ.items() if k != 'M3_OPERATOR_DATABASE_URL'}
    env.update(M3_MODE='demo', M3_DATABASE_URL=settings.database_url,
        M3_DEMO_ROOT=str(settings.demo_root), M3_SOURCE_ROOT=str(settings.source_root),
        M3_OUTPUT_ROOT=str(settings.output_root), M3_FRONTEND_ORIGIN=settings.frontend_origin,
        M3_WORKER_INSTANCE=settings.worker_instance,
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    from dataclasses import fields
    env.update({'M3_DEMO_' + f.name.upper(): str(getattr(settings.demo_limits, f.name))
                for f in fields(settings.demo_limits)})
    started = time.monotonic()
    limit_code = None
    peak = 0
    owned = {}
    with (private_root / (str(key) + '_supervisor.private.log')).open('ab') as log:
        process = subprocess.Popen([sys.executable, '-m', 'worker', '--claimed-run', str(key)],
            env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            while process.poll() is None:
                memory = 0
                try:
                    parent = psutil.Process(process.pid)
                    for child in [parent, *parent.children(recursive=True)]:
                        owned[child.pid] = child
                        try:
                            memory += child.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                except psutil.NoSuchProcess:
                    pass
                peak = max(peak, memory)
                if time.monotonic() - started > settings.demo_limits.job_seconds:
                    limit_code = 'demo_job_timeout'
                elif memory > settings.demo_limits.job_memory_mb * 1024**2:
                    limit_code = 'demo_job_memory'
                if limit_code:
                    break
                time.sleep(.2)
        finally:
            # Also remove model descendants if their job parent exited unexpectedly.
            stop(process, group=False, owned=owned.values())
    with sessions.begin() as session:
        row = session.get(Run, key)
        if row.status == 'running' or limit_code:
            row.status = 'failed'
            row.error_code = limit_code or 'demo_job_exited'
            row.finished_at = row.heartbeat_at = now()
    receipt = dict(run_id=str(key), elapsed_seconds=time.monotonic()-started,
        peak_tree_rss_bytes=peak, job_seconds=settings.demo_limits.job_seconds,
        job_memory_mb=settings.demo_limits.job_memory_mb, limit_code=limit_code,
        model_processes=1, model_threads=1)
    (private_root / (str(key) + '_resources.private.log')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
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
                with worker_heartbeat(settings, LOADED_CODE):
                    while True:
                        key = (demo_process_one(settings, sessions) if settings.mode == 'demo'
                               else process_one(settings, sessions))
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
    parser.add_argument('--claimed-run')
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.claimed_run:
        import uuid
        if settings.mode != 'demo':
            raise SystemExit('Claimed jobs require demo mode')
        engine, sessions = database(settings.database_url)
        try:
            with sessions() as session:
                row = session.get(Run, uuid.UUID(args.claimed_run))
                if row is None or row.status != 'running':
                    raise SystemExit('Job is not claimed')
                claimed = row.id, row.kind, row.code_sha256
            process_one(settings, sessions, claimed)
        finally:
            engine.dispose()
        return
    key = serve(settings, args.once)
    print("Processed one queued run" if key else "No queued run")


if __name__ == "__main__":
    main()
