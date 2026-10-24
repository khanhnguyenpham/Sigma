from datetime import date
from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
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
):
    return listing(http.app.state.sessions, Scenario, page, page_size)


@router.post("/scenarios", status_code=201)
def scenario(http: Request, request: ScenarioCreate):
    with http.app.state.sessions.begin() as session:
        return jsonable_encoder(record(create_scenario(session, request)))
