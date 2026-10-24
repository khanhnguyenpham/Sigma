"""Run HTTP routes, kept here until the runs-module refactor in step 6."""
import uuid
from fastapi import APIRouter, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sigma_m3.models import Run
from sigma_m3.schemas import RunCreate
from sigma_m3.services.runs import enqueue
from sigma_m3.core.run_context import required_run

router = APIRouter(prefix="/api/v1")


def run_view(row):
    # Detailed config, manifest file paths and request payload are private.
    return {
        name: getattr(row, name)
        for name in [
            "id",
            "kind",
            "status",
            "source_import_run_id",
            "forecast_run_id",
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


@router.post("/runs")
def runs_post(
    http: Request,
    request: RunCreate,
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    with http.app.state.sessions.begin() as session:
        row, created = enqueue(session, request, idempotency_key)
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


@router.get("/runs")
def runs_get(
    http: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    with http.app.state.sessions() as session:
        rows = session.scalars(
            select(Run)
            .order_by(Run.created_at.desc(), Run.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        output = []
        for row in rows:
            r = run_view(row)
            r["result_summary"] = {
                k: v
                for k, v in r["result_summary"].items()
                if k not in {"metrics", "selections", "audit"}
            }
            output.append(r)
        return dict(
            items=output,
            total=session.scalar(select(func.count()).select_from(Run)),
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
