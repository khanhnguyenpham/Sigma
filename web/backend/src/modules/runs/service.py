from datetime import date
import json
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from core.settings import PROFILE
from core.errors import DomainError
from core.settings import PROJECT_ROOT
from core.hashes import revision
from core.run_context import required_run
from modules.runs.models import Run, RunConfig, RunResult
from modules.configuration.models import Scenario

def enqueue(session, request, key, settings=None):
    if not key or len(key) > 128 or not key.isprintable():
        raise DomainError(
            "invalid_input", "Idempotency-Key must contain 1–128 printable characters"
        )
    body = request.model_dump(mode="json", exclude_none=True)
    if settings and settings.mode == 'demo':
        from sqlalchemy import text
        from core.demo_limits import ADMISSION_LOCK
        session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': ADMISSION_LOCK})
    existing = session.scalar(select(Run).where(Run.request_key == key))
    if existing:
        if existing.config_snapshot.get("request") != body:
            raise DomainError(
                "idempotency_conflict",
                "Key already belongs to a different request",
                409,
            )
        return existing, False
    if settings and settings.mode == 'demo':
        from core.demo_limits import admit
        admit(session, settings, request)
    profile_path = PROJECT_ROOT / "web/backend/configs/m3-profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    snapshot = dict(profile=profile, request=body, **PROFILE)
    from core.hashes import runtime_reference
    reference = runtime_reference()
    if reference:
        snapshot['runtime_code_reference'] = reference
    if settings and settings.mode == 'demo':
        from dataclasses import asdict
        snapshot['demo_limits'] = asdict(settings.demo_limits)
        snapshot['demo_compute'] = dict(model_processes=1, model_threads=1)
    if request.source_import_run_id:
        source = required_run(
            session, request.source_import_run_id, "source_import", complete=True
        )
        if request.as_of_date > source.observation_end:
            raise DomainError(
                "parent_mismatch", "Origin exceeds observed source coverage", 409
            )
    if request.forecast_run_id:
        parent = required_run(
            session, request.forecast_run_id, "forecast", complete=True
        )
        if parent.source_import_run_id != request.source_import_run_id:
            raise DomainError(
                "parent_mismatch", "Source and forecast parent do not match", 409
            )
        if parent.target_version != profile["target_version"]:
            raise DomainError("parent_mismatch", "Target versions do not match", 409)
        if request.mode == "future" and "selections" not in parent.config_snapshot:
            raise DomainError(
                "parent_mismatch", "Future mode requires a selection lock", 409
            )
        if request.mode == "future" and request.as_of_date < date(2025, 9, 30):
            raise DomainError(
                "parent_mismatch",
                "Origin precedes the completed validation selection window",
                409,
            )
    if request.scenario_id:
        scenario = session.scalar(select(Scenario).where(Scenario.id == request.scenario_id).with_for_update(read=True))
        if scenario is None:
            raise DomainError("not_found", "Scenario does not exist", 404)
        if scenario.settings.get("_deleted_at"):
            raise DomainError("scenario_deleted", "Restore the scenario before creating a run", 409)
        if scenario.settings.get("receipts_declared") is not True:
            raise DomainError(
                "missing_partner_config",
                "Receipts must be explicitly declared, including an empty list",
            )
        snapshot["scenario"] = dict(
            id=scenario.id, version=scenario.version, settings=scenario.settings
        )
        from modules.configuration.context import freeze_inventory

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
        code_revision=revision(),
        request_key=key,
    )
    inserted = session.scalar(
        insert(Run)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["request_key"])
        .returning(Run.id)
    )
    if inserted:
        session.add_all([RunConfig(run_id=inserted, config_snapshot=snapshot),
                         RunResult(run_id=inserted, result_summary={}, artifact_manifest={})])
        session.flush()
        return session.get(Run, inserted), True
    # A concurrent request may have committed while this insert waited.
    row = session.scalar(select(Run).where(Run.request_key == key))
    if row.config_snapshot.get("request") != body:
        raise DomainError(
            "idempotency_conflict", "Key already belongs to a different request", 409
        )
    return row, False


def progress(sessions, key, phase, **counts):
    with sessions.begin() as s:
        row = s.get(Run, key)
        row.result_summary = {"phase": phase, **counts}
