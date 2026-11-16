"""Dealer requests reuse the operational ledger: issuing posts one GI document through the same balance locks."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from sqlalchemy import select, func
from core.errors import DomainError
from core.http import record
from modules.catalog.models import Item
from modules.dealers.models import Dealer, DealerRequest as Request, DealerRequestLine as Line
from modules.operations import service as ops
from modules.operations.models import OperationalProduct as Product, OperationalWarehouse as Warehouse, StockBalance as Balance

STATUS_ACTION = {"approved": "approve", "rejected": "reject", "cancelled": "cancel", "issued": "issue", "received": "receive"}


def now():
    return datetime.now(timezone.utc)


def create_dealer(session, payload, actor):
    if session.scalar(select(Dealer.id).where(Dealer.code == payload.code)) is not None:
        raise DomainError("dealer_exists", "Mã đại lý đã tồn tại.", 409)
    row = Dealer(code=payload.code, name=payload.name, contact=payload.contact.strip(), created_by=actor)
    session.add(row); session.flush()
    ops.audit(session, "dealer", row.id, "created", actor, code=row.code)
    return record(row)


def update_dealer(session, key, payload, actor):
    row = session.scalar(select(Dealer).where(Dealer.id == key).with_for_update())
    if row is None:
        raise DomainError("not_found", "Không có đại lý này.", 404)
    ops.check_version(row.version, payload.expected_version)
    row.name, row.contact, row.active, row.version = payload.name, payload.contact.strip(), payload.active, row.version + 1
    ops.audit(session, "dealer", key, "updated", actor, version=row.version, active=row.active)
    return record(row)


def dealers(session, page, size, active=None):
    query = select(Dealer.id, Dealer.code, Dealer.name, Dealer.contact, Dealer.active, Dealer.version)
    if active is not None:
        query = query.where(Dealer.active.is_(active))
    return ops.page_rows(session, query.order_by(Dealer.name, Dealer.id), page, size)


def available_products(session, page, size, search=None):
    # Dealers see sellable stock as one company-wide total; warehouses stay internal.
    stock = select(Balance.item_id, func.sum(Balance.on_hand_qty).label("available_qty")).join(
        Warehouse, Balance.warehouse_id == Warehouse.id).where(Warehouse.active.is_(True)).group_by(Balance.item_id).subquery()
    query = select(Product.item_id, Item.sku, Product.name, Item.product_type, func.coalesce(stock.c.available_qty, 0).label("available_qty")).join(
        Item, Product.item_id == Item.id).outerjoin(stock, stock.c.item_id == Product.item_id).where(Product.active.is_(True))
    if search:
        query = query.where(Item.sku.icontains(search, autoescape=True) | Product.name.icontains(search, autoescape=True))
    return ops.page_rows(session, query.order_by(Product.name, Product.item_id), page, size)


def create_request(session, dealer_id, payload, request_key, actor):
    existing, fingerprint = ops.idempotency(session, Request, request_key, {"dealer_id": dealer_id, **payload.model_dump(mode="json")})
    if existing:
        return request_view(session, existing.id), False
    dealer = session.get(Dealer, dealer_id)
    if dealer is None or not dealer.active:
        raise DomainError("inactive_dealer", "Đại lý đã ngừng hoạt động.", 409)
    for line in payload.lines:
        product = session.get(Product, line.item_id)
        if product is None or not product.active:
            raise DomainError("inactive_product", "Sản phẩm không còn kinh doanh.", 409)
    row = Request(number="DR-" + ops.today().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8].upper(), dealer_id=dealer_id,
        status="submitted", note=payload.note.strip(), request_key=request_key, request_digest=fingerprint, created_by=actor)
    session.add(row); session.flush()
    session.add_all([Line(request_id=row.id, item_id=line.item_id, quantity=line.quantity) for line in payload.lines])
    ops.audit(session, "dealer_request", row.id, "created", actor, number=row.number)
    session.flush()
    return request_view(session, row.id), True


def locked_request(session, key, expected_version, dealer_id=None):
    query = select(Request).where(Request.id == key).with_for_update()
    if dealer_id is not None:
        query = query.where(Request.dealer_id == dealer_id)
    row = session.scalar(query)
    if row is None:
        raise DomainError("not_found", "Không có yêu cầu này.", 404)
    ops.check_version(row.version, expected_version)
    return row


def transition(session, row, allowed_from, status, actor, **fields):
    if row.status not in allowed_from:
        raise DomainError("invalid_request_state", "Yêu cầu không còn ở trạng thái cho phép thao tác này.", 409)
    row.status, row.version = status, row.version + 1
    for name, value in fields.items():
        setattr(row, name, value)
    ops.audit(session, "dealer_request", row.id, STATUS_ACTION[status], actor, number=row.number, version=row.version)
    session.flush()
    return request_view(session, row.id)


def approve(session, key, payload, actor):
    return transition(session, locked_request(session, key, payload.expected_version), {"submitted"}, "approved", actor,
        decided_by=actor, decided_at=now())


def reject(session, key, payload, actor):
    return transition(session, locked_request(session, key, payload.expected_version), {"submitted", "approved"}, "rejected", actor,
        decided_by=actor, decided_at=now(), reject_reason=payload.reason)


def cancel(session, key, payload, dealer_id, actor):
    return transition(session, locked_request(session, key, payload.expected_version, dealer_id), {"submitted"}, "cancelled", actor)


def receive(session, key, payload, dealer_id, actor):
    return transition(session, locked_request(session, key, payload.expected_version, dealer_id), {"issued"}, "received", actor,
        received_at=now())


def issue(session, key, payload, request_key, actor):
    existing, fingerprint = ops.idempotency(session, ops.Document, request_key, {"dealer_request_id": key, **payload.model_dump(mode="json")})
    if existing:
        return request_view(session, session.scalar(select(Request.id).where(Request.document_id == existing.id))), False
    row = locked_request(session, key, payload.expected_version)
    if row.status != "approved":
        raise DomainError("invalid_request_state", "Chỉ xuất kho cho yêu cầu đã duyệt.", 409)
    dealer = session.get(Dealer, row.dealer_id)
    header = SimpleNamespace(occurred_on=payload.occurred_on, external_ref=row.number, reason=f"Xuất cho đại lý {dealer.code}")
    document = ops.new_document(session, "issue", header, request_key, fingerprint, actor)
    for line in session.scalars(select(Line).where(Line.request_id == key).order_by(Line.item_id)):
        balance = ops.lock_balance(session, line.item_id, payload.warehouse_id, payload.occurred_on)
        ops.post_entry(session, document, balance, -line.quantity)
    ops.audit(session, "stock_document", document.id, "posted", actor, number=document.number, kind="issue", dealer_request=row.number)
    return transition(session, row, {"approved"}, "issued", actor, warehouse_id=payload.warehouse_id, document_id=document.id), True


def request_view(session, key, dealer_id=None):
    query = select(Request, Dealer.code, Dealer.name).join(Dealer, Request.dealer_id == Dealer.id).where(Request.id == key)
    if dealer_id is not None:
        query = query.where(Request.dealer_id == dealer_id)
    found = session.execute(query).first()
    if not found:
        raise DomainError("not_found", "Không có yêu cầu này.", 404)
    row, code, name = found
    result = record(row)
    result.pop("request_digest", None); result.pop("request_key", None)
    result.update(dealer_code=code, dealer_name=name, lines=[dict(line) for line in session.execute(select(
        Line.item_id, Item.sku, Product.name, Line.quantity).join(Item, Line.item_id == Item.id).join(
        Product, Product.item_id == Line.item_id).where(Line.request_id == key).order_by(Line.id)).mappings()])
    return result


def requests(session, page, size, dealer_id=None, status=None):
    totals = select(Line.request_id, func.sum(Line.quantity).label("quantity"), func.count().label("line_count")).group_by(Line.request_id).subquery()
    query = select(Request.id, Request.number, Request.status, Request.dealer_id, Dealer.code.label("dealer_code"), Dealer.name.label("dealer_name"),
        Request.created_at, Request.version, totals.c.quantity, totals.c.line_count).join(Dealer, Request.dealer_id == Dealer.id).join(
        totals, totals.c.request_id == Request.id)
    if dealer_id is not None:
        query = query.where(Request.dealer_id == dealer_id)
    if status:
        query = query.where(Request.status == status)
    return ops.page_rows(session, query.order_by(Request.id.desc()), page, size)


def dealer_stock(session, dealer_id, page, size):
    query = select(Line.item_id, Item.sku, Product.name, func.sum(Line.quantity).label("received_qty")).join(
        Request, Line.request_id == Request.id).join(Item, Line.item_id == Item.id).join(Product, Product.item_id == Line.item_id).where(
        Request.dealer_id == dealer_id, Request.status == "received").group_by(Line.item_id, Item.sku, Product.name)
    return ops.page_rows(session, query.order_by(Product.name, Line.item_id), page, size)
