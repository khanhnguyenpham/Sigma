from datetime import date
import json
from pathlib import Path
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sigma_m3 import PROFILE
from sigma_m3.core.errors import DomainError
from sigma_m3.core.hashes import digest, code_digest, revision
from sigma_m3.core.run_context import required_run
from sigma_m3.models import Run
from sigma_m3.modules.configuration.models import Scenario

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
        from sigma_m3.modules.configuration.context import freeze_inventory

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
