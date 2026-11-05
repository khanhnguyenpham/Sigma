"""HTTP adapters for run creation, status and summaries."""
import uuid
from typing import Literal
from fastapi import APIRouter, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from modules.runs.models import Run
from modules.runs.schemas import RunCreate
from modules.runs.service import enqueue
from core.run_context import required_run
from modules.configuration.models import Scenario

router = APIRouter(prefix="/api/v1")


def run_view(row):
    # Detailed config, manifest file paths and request payload are private.
    result = {
        name: getattr(row, name)
        for name in [
            "id",
            "kind",
            "status",
            "source_import_run_id",
            "forecast_run_id",
            "retry_of_run_id",
            "scenario_id",
            "as_of_date",
            "observation_end",
            "config_version",
            "assumption_version",
            "target_version",
            "created_at",
            "started_at",
            "finished_at",
            "heartbeat_at",
            "error_code",
            "result_summary",
            "period_start",
            "period_end",
        ]
    }
    result["trade_lifecycle_profile"] = row.config_snapshot.get("trade_lifecycle_profile")
    result["receiving_warehouse_profile"] = row.config_snapshot.get("receiving_warehouse_profile")
    result["scenario_supply_profile"] = row.config_snapshot.get("scenario_supply_profile")
    scenario = row.config_snapshot.get("scenario", {})
    result["scenario_name"] = scenario.get("name")
    result["scenario_version"] = scenario.get("version")
    settings = scenario.get("settings", {})
    result["scenario_settings"] = {key: settings[key] for key in
        ("cover_days", "safety_multiplier", "policy_overrides", "receipts_initial", "receipts_declared", "supply_schedule") if key in settings}
    return result


@router.post("/runs")
def runs_post(
    http: Request,
    request: RunCreate,
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    with http.app.state.sessions.begin() as session:
        row, created = enqueue(session, request, idempotency_key, http.app.state.settings)
        return JSONResponse(
            status_code=202 if created else 200,
            content=jsonable_encoder(
                dict(
                    run_id=row.id,
                    status=row.status,
                    status_url=f"/api/v1/runs/{row.id}",
                )
            ),
        )


@router.post('/runs/{key}/retry')
def retry_run(http: Request, key: uuid.UUID, idempotency_key: str = Header(alias='Idempotency-Key')):
    from core.errors import DomainError
    with http.app.state.sessions.begin() as session:
        previous = required_run(session, key)
        if previous.status != 'failed':
            raise DomainError('parent_mismatch', 'Only failed runs can be retried', 409)
        body = {**previous.config_snapshot['request'], 'retry_of_run_id': str(key)}
        if body.get('trade_lifecycle_profile'):
            body['scenario_supply_profile'] = 'scenario_supply_v1'
        row, created = enqueue(session, RunCreate(**body), idempotency_key, http.app.state.settings)
        return JSONResponse(status_code=202 if created else 200, content=jsonable_encoder(
            dict(run_id=row.id, status=row.status, status_url=f'/api/v1/runs/{row.id}')))


@router.get("/runs")
def runs_get(
    http: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    scenario_id: int | None = Query(None, gt=0),
    kind: Literal["source_import", "forecast", "policy_replay", "alert_replay", "stock_projection"] | None = None,
    status: Literal["queued", "running", "complete", "failed", "invalidated"] | None = None,
):
    with http.app.state.sessions() as session:
        query = select(Run)
        if scenario_id is None:
            query = query.where(~select(Scenario.id).where(Scenario.id==Run.scenario_id,
                Scenario.settings["_deleted_at"].astext.is_not(None)).exists())
        for field, value in ((Run.scenario_id, scenario_id), (Run.kind, kind), (Run.status, status)):
            if value is not None:
                query = query.where(field == value)
        rows = session.scalars(
            query
            .order_by(Run.created_at.desc(), Run.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        output = []
        for row in rows:
            r = run_view(row)
            r.pop("scenario_settings")
            r["result_summary"] = {
                k: v
                for k, v in r["result_summary"].items()
                if k not in {"metrics", "selections", "audit"}
            }
            output.append(r)
        return dict(
            items=output,
            total=session.scalar(select(func.count()).select_from(query.subquery())),
            page=page,
            page_size=page_size,
        )


@router.get("/runs/{key}")
def run_get(http: Request, key: uuid.UUID):
    with http.app.state.sessions() as session:
        return run_view(required_run(session, key))


@router.get("/runs/{key}/summary")
def run_summary(http: Request, key: uuid.UUID):
    with http.app.state.sessions() as session:
        row = required_run(session, key, complete=True)
        return dict(context=run_view(row), summary=row.result_summary)
