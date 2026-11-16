from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Header, Query, Request, Response
from sqlalchemy import select, func
from core.errors import DomainError
from modules.auth.models import User
from modules.catalog.models import Supplier
from modules.operations.models import SupplierSettings, StockBalance, OperationalOrder, StockDocument, OperationAudit
from modules.operations.models import OperationalWarehouse
from modules.operations.schemas import OpsSupplierSettingsInput, OpsOrderInput, OpsOrderUpdate, OpsOrderTransition, OpsReceiptInput, OpsMovementInput
from modules.operations.schemas import OpsWarehouseInput, OpsWarehouseUpdate, OpsProductInput, OpsProductUpdate
from modules.operations import service
from modules.dealers.models import DealerRequest
from modules.operations.schemas import OpsQrScanInput, OpsEtaChange

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/recommendations")
def stock_recommendations(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), forecast_run_id: UUID | None = None):
    actor(request)
    from modules.operations.planning import recommendations
    with request.app.state.sessions.begin() as session:
        return recommendations(session, page, page_size, forecast_run_id)


@router.post('/orders/{key}/receipt-qr')
def receipt_qr(key: int, payload: OpsReceiptInput, request: Request):
    actor(request)
    from modules.operations.qr import create_qr
    with request.app.state.sessions() as session:
        return create_qr(session,key,payload)


@router.post('/orders/{key}/receipt-qr/preview')
def scan_receipt_qr(key: int, payload: OpsQrScanInput, request: Request):
    actor(request)
    from modules.operations.qr import preview_qr
    with request.app.state.sessions() as session:
        return preview_qr(session,key,payload.payload)


def actor(request):
    identity = getattr(request.state, "user", None)
    if not identity or identity["role"] != "admin":
        raise DomainError("admin_required", "Cần đăng nhập bằng tài khoản quản trị.", 403)
    return identity["id"]


@router.get("/summary")
def summary(request: Request):
    actor(request)
    with request.app.state.sessions() as session:
        pending = session.scalar(select(func.count()).select_from(OperationalOrder).where(OperationalOrder.status.in_(["ordered", "partially_received"])))
        total = session.scalar(select(func.coalesce(func.sum(StockBalance.on_hand_qty), 0)))
        late = session.scalar(select(func.count()).select_from(OperationalOrder).where(OperationalOrder.status.in_(["ordered", "partially_received"]),
            OperationalOrder.eta < service.today()))
        dealer_requests = session.scalar(select(func.count()).select_from(DealerRequest).where(DealerRequest.status.in_(["submitted", "approved"])))
        return {"business_date": service.today(), "timezone": "Asia/Ho_Chi_Minh", "pending_orders": pending, "late_orders": late,
            "pending_dealer_requests": dealer_requests,
            "draft_orders": session.scalar(select(func.count()).select_from(OperationalOrder).where(OperationalOrder.status == "draft")),
            "stocked_items": session.scalar(select(func.count()).select_from(StockBalance).where(StockBalance.on_hand_qty > 0)),
            "on_hand_units": int(total) if total <= service.MAX_QTY else str(total),
            "documents_today": session.scalar(select(func.count()).select_from(StockDocument).where(StockDocument.occurred_on == service.today()))}


@router.get('/queue-status')
def worker_queue_status(request: Request):
    actor(request)
    from modules.runs.redis_queue import queue_status
    return queue_status(request.app.state.settings)


@router.get("/warehouses")
def warehouses(request: Request, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), active: bool | None = None):
    actor(request)
    query = select(OperationalWarehouse.id, OperationalWarehouse.code, OperationalWarehouse.name,
        OperationalWarehouse.country, OperationalWarehouse.active, OperationalWarehouse.version).order_by(OperationalWarehouse.name)
    if active is not None:
        query = query.where(OperationalWarehouse.active == active)
    with request.app.state.sessions() as session:
        return service.page_rows(session, query, page, page_size)


@router.post("/warehouses", status_code=201)
def create_warehouse(payload: OpsWarehouseInput, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.create_warehouse(session, payload, user)


@router.patch("/warehouses/{key}")
def update_warehouse(key: int, payload: OpsWarehouseUpdate, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.update_warehouse(session, key, payload, user)


@router.get("/products")
def products(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    supplier_id: int | None = Query(None, gt=0), search: str | None = Query(None, max_length=120), active: bool = True, include_inactive: bool = False):
    actor(request)
    with request.app.state.sessions() as session:
        return service.products(session, page, page_size, supplier_id, search, None if include_inactive else active)


@router.post("/products", status_code=201)
def create_product(payload: OpsProductInput, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.create_product(session, payload, user)


@router.patch("/products/{key}")
def update_product(key: int, payload: OpsProductUpdate, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.update_product(session, key, payload, user)


@router.get("/suppliers")
def suppliers(request: Request, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
    actor(request)
    query = select(Supplier.id, Supplier.carrier, func.coalesce(SupplierSettings.lead_time_days, 7).label("lead_time_days"),
        func.coalesce(SupplierSettings.version, 0).label("version"), SupplierSettings.updated_at).outerjoin(
            SupplierSettings, SupplierSettings.supplier_id == Supplier.id).order_by(Supplier.carrier)
    with request.app.state.sessions() as session:
        return service.page_rows(session, query, page, page_size)


@router.patch("/suppliers/{key}/settings")
def update_supplier(key: int, payload: OpsSupplierSettingsInput, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.set_supplier_settings(session, key, payload, user)


@router.get("/orders")
def orders(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    status: Literal["draft", "ordered", "partially_received", "received", "cancelled", "open"] | None = None,
    supplier_id: int | None = Query(None, gt=0), search: str | None = Query(None, max_length=120),
    sort: Literal["recent", "eta"] = "recent"):
    actor(request)
    with request.app.state.sessions() as session:
        return service.orders(session, page, page_size, status, supplier_id, search, sort)


@router.post("/orders", status_code=201)
def create_order(payload: OpsOrderInput, request: Request, response: Response, idempotency_key: str = Header(alias="Idempotency-Key")):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        result, created = service.create_order(session, payload, idempotency_key, user)
        response.status_code = 201 if created else 200
        return result


@router.get("/orders/{key}")
def order(key: int, request: Request):
    actor(request)
    with request.app.state.sessions() as session:
        return service.order_view(session, key)


@router.patch("/orders/{key}")
def update_order(key: int, payload: OpsOrderUpdate, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.update_order(session, key, payload, user)


@router.post("/orders/{key}/eta")
def change_eta(key: int, payload: OpsEtaChange, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.change_eta(session, key, payload, user)


@router.post("/orders/{key}/confirm")
def confirm_order(key: int, payload: OpsOrderTransition, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.transition_order(session, key, payload, user, "confirm")


@router.post("/orders/{key}/cancel")
def cancel_order(key: int, payload: OpsOrderTransition, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.transition_order(session, key, payload, user, "cancel")


@router.post("/orders/{key}/receipts", status_code=201)
def receive_order(key: int, payload: OpsReceiptInput, request: Request, response: Response, idempotency_key: str = Header(alias="Idempotency-Key")):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        result, created = service.receive_order(session, key, payload, idempotency_key, user)
        response.status_code = 201 if created else 200
        return result


@router.get("/stock")
def stock(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    warehouse_id: int | None = Query(None, gt=0), search: str | None = Query(None, max_length=120),
    sort: Literal["location", "on_hand"] = "location"):
    actor(request)
    with request.app.state.sessions() as session:
        return service.stock(session, page, page_size, warehouse_id, search, sort)


@router.post("/issues", status_code=201)
def issue_stock(payload: OpsMovementInput, request: Request, response: Response, idempotency_key: str = Header(alias="Idempotency-Key")):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        result, created = service.stock_movement(session, "issue", payload, idempotency_key, user)
        response.status_code = 201 if created else 200
        return result


@router.get("/stock/{warehouse_id}/{item_id}")
def stock_position(warehouse_id: int, item_id: int, request: Request):
    actor(request)
    with request.app.state.sessions() as session:
        return service.stock_position(session, warehouse_id, item_id)


@router.post("/counts", status_code=201)
def count_stock(payload: OpsMovementInput, request: Request, response: Response, idempotency_key: str = Header(alias="Idempotency-Key")):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        result, created = service.stock_movement(session, "adjustment", payload, idempotency_key, user)
        response.status_code = 201 if created else 200
        return result


@router.get("/documents")
def documents(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    actor(request)
    with request.app.state.sessions() as session:
        return service.journal(session, page, page_size)


@router.get("/documents/{key}")
def document(key: UUID, request: Request):
    actor(request)
    with request.app.state.sessions() as session:
        return service.document_view(session, key)


@router.get("/audit")
def audit(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    entity_type: str | None = Query(None, max_length=40), entity_key: str | None = Query(None, max_length=80)):
    actor(request)
    query = select(OperationAudit.id, OperationAudit.entity_type, OperationAudit.entity_key, OperationAudit.action,
        OperationAudit.details, OperationAudit.created_at, User.display_name.label("actor")).join(User, OperationAudit.actor_id == User.id)
    if entity_type:
        query = query.where(OperationAudit.entity_type == entity_type)
    if entity_key:
        query = query.where(OperationAudit.entity_key == entity_key)
    with request.app.state.sessions() as session:
        return service.page_rows(session, query.order_by(OperationAudit.id.desc()), page, page_size)
