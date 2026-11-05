from datetime import date
from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func
from datetime import datetime, timezone
from core.errors import DomainError
from modules.runs.models import Run
from core.http import listing, record
from modules.configuration.models import Scenario
from modules.configuration.schemas import PolicyCreate, ScenarioCreate
from modules.configuration.service import create_policy, create_scenario, list_policies

router = APIRouter(prefix="/api/v1")


@router.get("/supplier-item-policies")
def policies(
    http: Request,
    item_id: int | None = None,
    supplier_id: int | None = None,
    effective_on: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return list_policies(
        http.app.state.sessions, item_id, supplier_id, effective_on, page, page_size,
    )


@router.post("/supplier-item-policies", status_code=201)
def policy(http: Request, request: PolicyCreate):
    with http.app.state.sessions.begin() as session:
        return jsonable_encoder(record(create_policy(session, request)))


@router.get("/scenarios")
def scenarios(
    http: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    include_deleted: bool = False,
):
    with http.app.state.sessions() as session:
        query = select(Scenario)
        if not include_deleted:
            query = query.where(Scenario.settings["_deleted_at"].astext.is_(None))
        rows = session.scalars(query.order_by(Scenario.id).offset((page-1)*page_size).limit(page_size)).all()
        return jsonable_encoder(dict(items=[record(r) for r in rows],
            total=session.scalar(select(func.count()).select_from(query.subquery())),page=page,page_size=page_size))


def scenario_trash(http, key, deleted):
    with http.app.state.sessions.begin() as session:
        row = session.scalar(select(Scenario).where(Scenario.id == key).with_for_update())
        if row is None:
            raise DomainError("not_found", "Scenario does not exist", 404)
        if deleted and session.scalar(select(Run.id).where(Run.scenario_id == key,Run.status.in_(["queued","running"])).limit(1)):
            raise DomainError("scenario_busy", "Wait for active runs to finish before deleting this scenario", 409)
        settings = dict(row.settings)
        if deleted:
            settings.setdefault("_deleted_at", datetime.now(timezone.utc).isoformat())
        else:
            settings.pop("_deleted_at",None)
        row.settings = settings
        session.flush()
        return jsonable_encoder(record(row))


@router.delete("/scenarios/{key}")
def delete_scenario(http: Request, key: int):
    return scenario_trash(http,key,True)


@router.post("/scenarios/{key}/restore")
def restore_scenario(http: Request, key: int):
    return scenario_trash(http,key,False)


@router.post("/scenarios", status_code=201)
def scenario(http: Request, request: ScenarioCreate):
    with http.app.state.sessions.begin() as session:
        return jsonable_encoder(record(create_scenario(session, request)))
