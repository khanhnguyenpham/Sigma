import uuid
from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from core.http import listing, record
from modules.catalog.models import Supplier
from modules.catalog.schemas import WarehouseUpdate
from modules.catalog.service import list_warehouses, list_items, update_warehouse

router = APIRouter(prefix="/api/v1")


@router.get("/warehouses")
def warehouses(
    http: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    country: str | None = None,
    run_id: uuid.UUID | None = None,
):
    return list_warehouses(http.app.state.sessions, page, page_size, country, run_id)


@router.patch("/warehouses/{key}")
def warehouse_patch(http: Request, key: int, request: WarehouseUpdate):
    with http.app.state.sessions.begin() as session:
        return jsonable_encoder(record(update_warehouse(session, key, request)))


@router.get("/items")
def items(
    http: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    warehouse_id: int | None = Query(None, gt=0),
    product_type: str | None = None,
    run_id: uuid.UUID | None = None,
    search: str | None = None,
):
    return list_items(
        http.app.state.sessions, page, page_size,
        warehouse_id, product_type, run_id, search,
    )


@router.get("/suppliers")
def suppliers(
    http: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return listing(http.app.state.sessions, Supplier, page, page_size)
