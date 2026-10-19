from datetime import date
import hashlib, json
from pathlib import Path
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sigma_m3 import PROFILE
from sigma_m3.errors import DomainError
from sigma_m3.models import Run, Scenario


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False
        ).encode()
    ).hexdigest()


def source_data_id(source):
    """A deduplicated import keeps its own request identity, not duplicate observations."""
    return (
        uuid.UUID(source.config_snapshot["resolved_source_import_run_id"])
        if source.config_snapshot.get("resolved_source_import_run_id")
        else source.id
    )


def code_digest():
    project = Path(__file__).resolve().parents[5]
    paths = [
        p
        for folder in ["M3/backend/src/sigma_m3", "src", "M2/models"]
        for p in (project / folder).rglob("*.py")
    ]
    paths.append(project / "M2/final_report.py")
    return digest(
        {
            p.relative_to(project).as_posix(): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sorted(paths)
        }
    )


def required_run(session, key, kind=None, complete=False, _ancestors=frozenset()):
    row = session.get(Run, key)
    if row is None:
        raise DomainError("not_found", "Run does not exist", 404)
    if complete and row.status != "complete":
        raise DomainError("run_not_complete", "Results require a complete run", 409)
    if kind and row.kind != kind:
        raise DomainError("parent_mismatch", "Parent has the wrong run kind", 409)
    if complete:
        if row.id in _ancestors:
            raise DomainError("parent_mismatch", "Parent graph contains a cycle", 409)
        if digest(row.config_snapshot) != row.config_sha256:
            raise DomainError(
                "parent_mismatch", "Frozen run configuration checksum differs", 409
            )
        for attr, expected_kind in [
            ("source_import_run_id", "source_import"),
            ("forecast_run_id", "forecast"),
        ]:
            parent_id = getattr(row, attr)
            if not parent_id:
                continue
            parent = required_run(
                session,
                parent_id,
                expected_kind,
                complete=True,
                _ancestors=_ancestors | {row.id},
            )
            if (
                parent is None
                or parent.status != "complete"
                or parent.kind != expected_kind
                or parent.source_sha256 != row.source_sha256
                or parent.target_version != row.target_version
            ):
                raise DomainError(
                    "parent_mismatch", "A frozen parent is no longer compatible", 409
                )
            frozen = row.config_snapshot.get(
                "source_parent_config_sha256"
                if attr == "source_import_run_id"
                else "forecast_parent_config_sha256"
            )
            if frozen and parent.config_sha256 != frozen:
                raise DomainError(
                    "parent_mismatch", "Parent configuration changed", 409
                )
    return row


def enqueue(session, request, key):
    if not key or len(key) > 128 or not key.isprintable():
        raise DomainError(
            "invalid_input", "Idempotency-Key must contain 1–128 printable characters"
        )
    body = request.model_dump(mode="json", exclude_none=True)
    body_hash = digest(body)
    existing = session.scalar(select(Run).where(Run.request_key == key))
    if existing:
        if existing.request_sha256 != body_hash:
            raise DomainError(
                "idempotency_conflict",
                "Key already belongs to a different request",
                409,
            )
        return existing, False
    profile_path = Path(__file__).resolve().parents[4] / "configs/m3-profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    snapshot = dict(profile=profile, request=body, **PROFILE)
    source_sha = None
    if request.source_import_run_id:
        source = required_run(
            session, request.source_import_run_id, "source_import", complete=True
        )
        source_sha = source.source_sha256
        if request.as_of_date > source.observation_end:
            raise DomainError(
                "parent_mismatch", "Origin exceeds observed source coverage", 409
            )
        snapshot["source_parent_config_sha256"] = source.config_sha256
    if request.forecast_run_id:
        parent = required_run(
            session, request.forecast_run_id, "forecast", complete=True
        )
        if (
            parent.source_import_run_id != request.source_import_run_id
            or parent.source_sha256 != source_sha
        ):
            raise DomainError(
                "parent_mismatch", "Source and forecast parent do not match", 409
            )
        if parent.target_version != profile["target_version"]:
            raise DomainError("parent_mismatch", "Target versions do not match", 409)
        if request.mode == "future" and not parent.selection_sha256:
            raise DomainError(
                "parent_mismatch", "Future mode requires a selection lock", 409
            )
        if request.mode == "future" and request.as_of_date < date(2025, 9, 30):
            raise DomainError(
                "parent_mismatch",
                "Origin precedes the completed validation selection window",
                409,
            )
        snapshot["forecast_parent_config_sha256"] = parent.config_sha256
    if request.scenario_id:
        scenario = session.get(Scenario, request.scenario_id)
        if scenario is None:
            raise DomainError("not_found", "Scenario does not exist", 404)
        if scenario.settings.get("receipts_declared") is not True:
            raise DomainError(
                "missing_partner_config",
                "Receipts must be explicitly declared, including an empty list",
            )
        snapshot["scenario"] = dict(
            id=scenario.id, version=scenario.version, settings=scenario.settings
        )
        from sigma_m3.services.context import freeze_inventory

        snapshot.update(freeze_inventory(session, request, source, scenario))
    if request.retry_of_run_id:
        old = required_run(session, request.retry_of_run_id)
        if old.status != "failed" or old.kind != request.kind:
            raise DomainError(
                "parent_mismatch",
                "Only a failed run of the same kind can be retried",
                409,
            )
    values = dict(
        id=uuid.uuid4(),
        kind=request.kind,
        status="queued",
        as_of_date=request.as_of_date,
        observation_end=date.fromisoformat(profile["observation_end"]),
        source_import_run_id=request.source_import_run_id,
        forecast_run_id=request.forecast_run_id,
        retry_of_run_id=request.retry_of_run_id,
        scenario_id=request.scenario_id,
        period_start=request.period_start,
        period_end=request.period_end,
        target_version=profile["target_version"],
        config_version=profile["version"],
        assumption_version=profile["assumption_version"],
        source_sha256=source_sha,
        code_revision=revision(),
        code_sha256=code_digest(),
        config_snapshot=snapshot,
        config_sha256=digest(snapshot),
        request_key=key,
        request_sha256=body_hash,
        result_summary={},
        artifact_manifest={},
    )
    inserted = session.scalar(
        insert(Run)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["request_key"])
        .returning(Run.id)
    )
    if inserted:
        return session.get(Run, inserted), True
    # A concurrent request may have committed while this insert waited.
    row = session.scalar(select(Run).where(Run.request_key == key))
    if row.request_sha256 != body_hash:
        raise DomainError(
            "idempotency_conflict", "Key already belongs to a different request", 409
        )
    return row, False


def revision():
    import subprocess
    import shutil

    try:
        executable = shutil.which("git") or "F:/code/Git/cmd/git.exe"
        return subprocess.check_output(
            [executable, "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[5],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted-source"
