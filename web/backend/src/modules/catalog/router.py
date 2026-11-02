import uuid
from datetime import date
from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from core.http import listing, record
from modules.catalog.models import Supplier
from modules.catalog.schemas import WarehouseUpdate, SupplyChangeCreate, SupplyStatus
from modules.catalog.supply_service import create_supply_change, list_supply_changes
from modules.catalog.service import list_warehouses, list_items, update_warehouse, get_warehouse, list_products
from core.errors import DomainError

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


@router.get("/warehouses/{key}")
def warehouse_detail(http: Request, key: int):
    with http.app.state.sessions() as session:
        return jsonable_encoder(get_warehouse(session, key))


@router.get("/products")
def products(http: Request, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
             warehouse_id: int | None = Query(None, gt=0), product_type: str | None = None,
             search: str | None = None, as_of_date: date | None = None, supply_status: SupplyStatus | None = None):
    return jsonable_encoder(list_products(http.app.state.sessions, page, page_size, warehouse_id, product_type, search,
                                         as_of_date=as_of_date, supply_status=supply_status))


@router.get("/products/{key}")
def product_detail(http: Request, key: int, as_of_date: date | None = None):
    result = list_products(http.app.state.sessions, item_id=key, as_of_date=as_of_date)
    if not result["items"]:
        raise DomainError("not_found", "Product does not exist", 404)
    return jsonable_encoder(result["items"][0])


@router.get("/products/{key}/supply-changes")
def supply_history(http: Request, key: int, page: int = Query(1, ge=1),
                   page_size: int = Query(50, ge=1, le=100), as_of_date: date | None = None):
    with http.app.state.sessions() as session:
        return jsonable_encoder(list_supply_changes(session, key, page, page_size, as_of_date))


@router.post("/products/{key}/supply-changes", status_code=201)
def supply_create(http: Request, key: int, request: SupplyChangeCreate):
    with http.app.state.sessions.begin() as session:
        return jsonable_encoder(create_supply_change(session, key, request))


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
