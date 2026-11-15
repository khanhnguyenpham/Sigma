"""Dedicated, read-only supplier portal. Scope is applied in SQL before totals/pages."""
from fastapi import APIRouter, Request, Query
from sqlalchemy import select, func
from core.errors import DomainError
from modules.catalog.models import Item, Warehouse, Supplier
from modules.configuration.models import Policy
from modules.purchasing.models import Replenishment

router = APIRouter(prefix="/api/v1/supplier", tags=["supplier"])


def scope(request):
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "supplier" or user["supplier_id"] is None:
        raise DomainError("supplier_required", "Trang này dành cho tài khoản nhà cung cấp.", 403)
    return user["supplier_id"]


def products_query(supplier_id):
    return select(Item.id, Item.sku, Item.product_type, Warehouse.destination_country, Warehouse.code.label("warehouse"),
                  Supplier.carrier).join(Warehouse, Item.warehouse_id == Warehouse.id).join(
                      Supplier, Warehouse.carrier == Supplier.carrier).where(Supplier.id == supplier_id)


def page_result(session, query, page, page_size):
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.execute(query.order_by(query.selected_columns.id).offset((page - 1) * page_size).limit(page_size)).mappings()
    return {"items": [dict(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/products")
def products(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    supplier = scope(request)
    with request.app.state.sessions() as session:
        return page_result(session, products_query(supplier), page, page_size)


@router.get("/shipments")
def shipments(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    supplier = scope(request)
    # Policy owns the supplier of each simulated order, independent of current catalog mapping.
    query = select(Replenishment.id, Item.sku, Replenishment.run_id, Replenishment.window_origin,
                   Replenishment.ordered_on, Replenishment.eta, Replenishment.ordered_qty,
                   Replenishment.received_qty, Replenishment.status, Replenishment.is_simulated).join(
                       Item, Replenishment.item_id == Item.id).join(Policy, Replenishment.policy_id == Policy.id).where(
                           Policy.supplier_id == supplier)
    with request.app.state.sessions() as session:
        return page_result(session, query, page, page_size)
