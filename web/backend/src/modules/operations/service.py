"""Document posting is atomic: order, balance, ledger and actor audit commit together."""
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, text, or_
from sqlalchemy.dialects.postgresql import insert
from core.errors import DomainError
from core.hashes import digest
from core.http import record
from modules.auth.models import User
from modules.catalog.models import Item, Warehouse as SourceWarehouse, Supplier
from modules.operations.models import SupplierSettings, OperationalOrder as Order, OperationalOrderLine as Line
from modules.operations.models import StockBalance as Balance, StockDocument as Document, StockDocumentLine as Entry, OperationAudit
from modules.operations.models import OperationalWarehouse as Warehouse, OperationalProduct as Product
from modules.operations.schemas import MAX_QTY



def today():
    return datetime.now(timezone(timedelta(hours=7))).date()


def now():
    return datetime.now(timezone.utc)


def audit(session, entity_type, key, action, actor, **details):
    session.add(OperationAudit(entity_type=entity_type, entity_key=str(key), action=action, actor_id=actor, details=details))


def check_version(actual, expected):
    if actual != expected:
        raise DomainError("version_conflict", "Dữ liệu đã thay đổi. Tải lại trước khi lưu.", 409)


def idempotency(session, model, key, body):
    if not key or len(key) > 128 or not key.isprintable():
        raise DomainError("invalid_input", "Mã yêu cầu không hợp lệ.")
    session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": model.__tablename__ + ":" + key})
    fingerprint = digest(body)
    row = session.scalar(select(model).where(model.request_key == key))
    if row and row.request_digest != fingerprint:
        raise DomainError("idempotency_conflict", "Mã yêu cầu đã dùng cho nội dung khác.", 409)
    return row, fingerprint


def order_view(session, key, supplier_id=None):
    query = select(Order, Supplier.carrier).join(Supplier, Order.supplier_id == Supplier.id).where(Order.id == key)
    if supplier_id is not None:
        query = query.where(Order.supplier_id == supplier_id)
    found = session.execute(query).first()
    if not found:
        raise DomainError("not_found", "Không có đơn nhập hàng này.", 404)
    order, carrier = found
    result = record(order)
    # Request fingerprints are internal retry metadata, not a user-facing business field.
    result.pop("request_digest", None); result.pop("request_key", None)
    rows = session.execute(select(Line, Item.sku, Item.product_type, Warehouse.name, Product.name).join(Item, Line.item_id == Item.id).join(
        Warehouse, Line.warehouse_id == Warehouse.id).join(Product, Product.item_id == Item.id).where(Line.order_id == key).order_by(Line.id)).all()
    result.update(carrier=carrier, lines=[{**record(line), "sku": sku, "name": name, "product_type": product_type, "warehouse": city,
        "remaining_qty": line.ordered_qty - line.received_qty} for line, sku, product_type, city, name in rows])
    return result


def validate_order(session, payload):
    supplier = session.scalar(select(Supplier).where(Supplier.id == payload.supplier_id).with_for_update(read=True))
    if supplier is None:
        raise DomainError("not_found", "Nhà cung cấp không tồn tại.", 404)
    settings = session.get(SupplierSettings, supplier.id)
    if sum(row.quantity for row in payload.lines) > MAX_QTY:
        raise DomainError("invalid_input", "Tổng số lượng đơn vượt giới hạn hỗ trợ.")
    for row in payload.lines:
        carrier = session.scalar(select(SourceWarehouse.carrier).join(Item, Item.warehouse_id == SourceWarehouse.id).where(Item.id == row.item_id))
        if carrier != supplier.carrier:
            raise DomainError("supplier_carrier_mismatch", "Sản phẩm không thuộc nhà cung cấp đã chọn.")
        product = session.scalar(select(Product).where(Product.item_id == row.item_id).with_for_update(read=True))
        if product is None or not product.active:
            raise DomainError("inactive_product", "Sản phẩm chưa đăng ký vận hành hoặc đã ngừng nhập.", 409)
        warehouse = session.scalar(select(Warehouse).where(Warehouse.id == row.warehouse_id).with_for_update(read=True))
        if warehouse is None or not warehouse.active:
            raise DomainError("inactive_warehouse", "Kho nhận không tồn tại hoặc đã đóng.", 409)
    return settings.lead_time_days if settings else 7, settings.version if settings else 0


def create_order(session, payload, key, actor):
    existing, fingerprint = idempotency(session, Order, key, payload.model_dump(mode="json"))
    if existing:
        return order_view(session, existing.id), False
    lead, version = validate_order(session, payload)
    order = Order(number="PO-" + today().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:12].upper(),
        supplier_id=payload.supplier_id, ordered_on=payload.ordered_on, eta=payload.ordered_on + timedelta(days=lead),
        lead_time_days=lead, supplier_settings_version=version, status="draft", version=1,
        note=payload.note.strip(), created_by=actor, request_key=key, request_digest=fingerprint)
    session.add(order); session.flush()
    session.add_all([Line(order_id=order.id, item_id=row.item_id, warehouse_id=row.warehouse_id,
        ordered_qty=row.quantity, received_qty=0) for row in payload.lines])
    audit(session, "purchase_order", order.id, "created", actor, line_count=len(payload.lines), lead_time_days=lead)
    session.flush()
    return order_view(session, order.id), True


def required_order(session, key, expected_version):
    order = session.scalar(select(Order).where(Order.id == key).with_for_update())
    if order is None:
        raise DomainError("not_found", "Không có đơn nhập hàng này.", 404)
    check_version(order.version, expected_version)
    return order


def update_order(session, key, payload, actor):
    order = required_order(session, key, payload.expected_version)
    if order.status != "draft":
        raise DomainError("order_not_draft", "Chỉ sửa được đơn chưa xác nhận.", 409)
    lead, version = validate_order(session, payload)
    session.query(Line).filter(Line.order_id == key).delete(synchronize_session=False)
    order.supplier_id, order.ordered_on = payload.supplier_id, payload.ordered_on
    order.lead_time_days, order.supplier_settings_version = lead, version
    order.eta, order.note, order.version = payload.ordered_on + timedelta(days=lead), payload.note.strip(), order.version + 1
    session.add_all([Line(order_id=key, item_id=row.item_id, warehouse_id=row.warehouse_id,
        ordered_qty=row.quantity, received_qty=0) for row in payload.lines])
    audit(session, "purchase_order", key, "updated", actor, version=order.version)
    session.flush()
    return order_view(session, key)


def transition_order(session, key, payload, actor, action):
    order = required_order(session, key, payload.expected_version)
    if action == "confirm":
        if order.status != "draft":
            raise DomainError("order_not_draft", "Đơn đã xác nhận hoặc đã hủy.", 409)
        if order.ordered_on > today():
            raise DomainError("future_order", "Chưa thể xác nhận đơn có ngày đặt trong tương lai.")
        for line in session.scalars(select(Line).where(Line.order_id == key).order_by(Line.warehouse_id, Line.item_id)):
            warehouse = session.scalar(select(Warehouse).where(Warehouse.id == line.warehouse_id).with_for_update(read=True))
            product = session.scalar(select(Product).where(Product.item_id == line.item_id).with_for_update(read=True))
            if not warehouse.active or not product.active:
                raise DomainError("inactive_catalog", "Kho hoặc sản phẩm đã ngừng hoạt động; sửa lại đơn trước khi xác nhận.", 409)
        order.status, order.confirmed_by, order.confirmed_at = "ordered", actor, now()
    else:
        if order.status not in {"draft", "ordered", "partially_received"}:
            raise DomainError("order_closed", "Đơn đã kết thúc, không thể hủy.", 409)
        if not payload.reason.strip():
            raise DomainError("reason_required", "Cần ghi lý do hủy phần chưa nhận.")
        order.status, order.cancelled_by, order.cancelled_at = "cancelled", actor, now()
    order.version += 1
    audit(session, "purchase_order", key, action, actor, reason=payload.reason.strip(), version=order.version)
    session.flush()
    return order_view(session, key)


def set_supplier_settings(session, key, payload, actor):
    supplier = session.scalar(select(Supplier).where(Supplier.id == key).with_for_update())
    if supplier is None:
        raise DomainError("not_found", "Không có nhà cung cấp này.", 404)
    row = session.get(SupplierSettings, key)
    check_version(row.version if row else 0, payload.expected_version)
    if row is None:
        row = SupplierSettings(supplier_id=key, lead_time_days=payload.lead_time_days, version=1, updated_by=actor)
        session.add(row)
    else:
        row.lead_time_days, row.version, row.updated_by, row.updated_at = payload.lead_time_days, row.version + 1, actor, now()
    audit(session, "supplier_settings", key, "updated", actor, lead_time_days=row.lead_time_days,
          version=row.version, reason=payload.reason)
    session.flush()
    return {**record(row), "carrier": supplier.carrier}


def lock_balance(session, item_id, warehouse_id, occurred_on):
    if occurred_on > today():
        raise DomainError("future_stock_document", "Không ghi sổ kho cho ngày trong tương lai.")
    warehouse = session.scalar(select(Warehouse).where(Warehouse.id == warehouse_id).with_for_update(read=True))
    if session.get(Product, item_id) is None or warehouse is None:
        raise DomainError("not_found", "Sản phẩm hoặc kho không tồn tại.", 404)
    if not warehouse.active:
        raise DomainError("inactive_warehouse", "Kho đã đóng, không thể ghi thêm chứng từ.", 409)
    session.execute(insert(Balance).values(item_id=item_id, warehouse_id=warehouse_id, on_hand_qty=0, version=0).on_conflict_do_nothing())
    balance = session.scalar(select(Balance).where(Balance.item_id == item_id, Balance.warehouse_id == warehouse_id).with_for_update())
    if balance.last_movement_on and occurred_on < balance.last_movement_on:
        raise DomainError("backdated_stock_document", "Ngày chứng từ sớm hơn lần ghi sổ gần nhất của mặt hàng; cần đối soát trước khi ghi.", 409)
    return balance


def post_entry(session, document, balance, delta, order_line=None):
    quantity = balance.on_hand_qty + delta
    if quantity < 0:
        raise DomainError("insufficient_stock", "Số lượng xuất vượt tồn hiện có.", 409)
    if quantity > MAX_QTY:
        raise DomainError("numeric_overflow", "Số lượng vượt giới hạn lưu trữ.")
    balance.on_hand_qty, balance.version = quantity, balance.version + 1
    balance.last_movement_on, balance.updated_at = document.occurred_on, now()
    session.add(Entry(document_id=document.id, kind=document.kind, order_id=document.order_id,
        order_line_id=order_line.id if order_line else None, item_id=balance.item_id, warehouse_id=balance.warehouse_id,
        quantity_delta=delta, balance_after=quantity))


def new_document(session, kind, payload, key, fingerprint, actor, order_id=None):
    document = Document(number={"receipt": "GR", "issue": "GI", "adjustment": "SC"}[kind] + "-" +
        today().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:12].upper(), kind=kind,
        order_id=order_id, occurred_on=payload.occurred_on, external_ref=payload.external_ref,
        reason=payload.reason.strip(), request_key=key, request_digest=fingerprint, created_by=actor)
    session.add(document); session.flush()
    return document


def document_view(session, key):
    row = session.get(Document, key)
    if row is None:
        raise DomainError("not_found", "Không có chứng từ này.", 404)
    result = record(row)
    result.pop("request_digest", None); result.pop("request_key", None)
    result["lines"] = [dict(line) for line in session.execute(select(Entry.id, Entry.item_id, Item.sku,
        Entry.warehouse_id, Warehouse.name.label("warehouse"), Entry.quantity_delta, Entry.balance_after)
        .join(Item, Entry.item_id == Item.id).join(Warehouse, Entry.warehouse_id == Warehouse.id)
        .where(Entry.document_id == key).order_by(Entry.id)).mappings()]
    return result


def receive_order(session, key, payload, request_key, actor):
    existing, fingerprint = idempotency(session, Document, request_key, {"order_id": key, "kind": "receipt", **payload.model_dump(mode="json")})
    if existing:
        return document_view(session, existing.id), False
    order = required_order(session, key, payload.expected_version)
    if order.status not in {"ordered", "partially_received"}:
        raise DomainError("order_not_receivable", "Đơn chưa xác nhận hoặc đã kết thúc.", 409)
    if payload.occurred_on < order.ordered_on:
        raise DomainError("receipt_before_order", "Ngày nhận không được trước ngày đặt.")
    duplicate = session.scalar(select(Document.id).where(Document.order_id == key, Document.external_ref == payload.external_ref))
    if duplicate:
        raise DomainError("duplicate_delivery", "Phiếu giao hàng này đã được ghi nhận cho đơn.", 409)
    lines = {line.id: line for line in session.scalars(select(Line).where(Line.order_id == key).order_by(Line.id))}
    for entry in payload.lines:
        line = lines.get(entry.order_line_id)
        if line is None or entry.quantity > line.ordered_qty - line.received_qty:
            raise DomainError("invalid_receipt_quantity", "Mặt hàng không thuộc đơn hoặc lượng nhận vượt phần còn lại.", 409)
    document = new_document(session, "receipt", payload, request_key, fingerprint, actor, key)
    for entry in sorted(payload.lines, key=lambda row: (lines[row.order_line_id].warehouse_id, lines[row.order_line_id].item_id)):
        line = lines[entry.order_line_id]
        balance = lock_balance(session, line.item_id, line.warehouse_id, payload.occurred_on)
        post_entry(session, document, balance, entry.quantity, line)
        line.received_qty += entry.quantity
    order.status = "received" if all(line.received_qty == line.ordered_qty for line in lines.values()) else "partially_received"
    order.version += 1
    audit(session, "stock_document", document.id, "posted", actor, number=document.number, kind=document.kind, order_id=key)
    audit(session, "purchase_order", key, "received", actor, document_id=str(document.id), status=order.status, version=order.version)
    session.flush()
    return document_view(session, document.id), True


def stock_movement(session, kind, payload, request_key, actor):
    existing, fingerprint = idempotency(session, Document, request_key, {"kind": kind, **payload.model_dump(mode="json")})
    if existing:
        return document_view(session, existing.id), False
    balance = lock_balance(session, payload.item_id, payload.warehouse_id, payload.occurred_on)
    check_version(balance.version, payload.expected_balance_version)
    if kind == "issue" and payload.quantity == 0:
        raise DomainError("invalid_input", "Lượng xuất phải lớn hơn 0.")
    delta = -payload.quantity if kind == "issue" else payload.quantity - balance.on_hand_qty
    document = new_document(session, kind, payload, request_key, fingerprint, actor)
    post_entry(session, document, balance, delta)
    audit(session, "stock_document", document.id, "posted", actor, number=document.number, kind=kind, quantity_delta=delta)
    session.flush()
    return document_view(session, document.id), True


def page_rows(session, query, page, size):
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return {"items": [dict(row) for row in session.execute(query.offset((page-1)*size).limit(size)).mappings()],
            "total": total, "page": page, "page_size": size}


def orders(session, page, size, status=None, supplier_id=None, search=None, sort="recent"):
    totals = select(Line.order_id, func.sum(Line.ordered_qty).label("ordered_qty"), func.sum(Line.received_qty).label("received_qty")).group_by(Line.order_id).subquery()
    query = select(Order.id, Order.number, Order.supplier_id, Supplier.carrier, Order.ordered_on, Order.eta, Order.status,
        Order.version, Order.lead_time_days, totals.c.ordered_qty, totals.c.received_qty).join(Supplier, Order.supplier_id == Supplier.id).join(totals, totals.c.order_id == Order.id)
    if supplier_id is not None:
        query = query.where(Order.supplier_id == supplier_id)
    if status == "open":
        query = query.where(Order.status.in_(["ordered", "partially_received"]))
    elif status:
        query = query.where(Order.status == status)
    if search:
        query = query.where(or_(Order.number.icontains(search, autoescape=True), Supplier.carrier.icontains(search, autoescape=True)))
    order = (Order.eta, Order.id) if sort == "eta" else (Order.id.desc(),)
    return page_rows(session, query.order_by(*order), page, size)


def stock(session, page, size, warehouse_id=None, search=None, sort="location"):
    query = select(Balance.warehouse_id, Warehouse.name.label("warehouse"), Balance.item_id, Item.sku, Product.name, Item.product_type,
        Balance.on_hand_qty, Balance.version, Balance.last_movement_on).join(Item, Balance.item_id == Item.id).join(Product,
        Product.item_id == Item.id).join(Warehouse, Balance.warehouse_id == Warehouse.id)
    if warehouse_id is not None:
        query = query.where(Balance.warehouse_id == warehouse_id)
    if search:
        query = query.where(or_(Item.sku.icontains(search, autoescape=True), Product.name.icontains(search, autoescape=True)))
    location = (Warehouse.name, Item.sku, Item.product_type, Balance.item_id)
    return page_rows(session, query.order_by(*((Balance.on_hand_qty,) if sort == "on_hand" else ()), *location), page, size)


def stock_position(session, warehouse_id, item_id):
    warehouse, product = session.get(Warehouse, warehouse_id), session.get(Product, item_id)
    if warehouse is None or product is None:
        raise DomainError("not_found", "Không có kho hoặc sản phẩm này.", 404)
    balance = session.get(Balance, (warehouse_id, item_id))
    return {"warehouse_id": warehouse_id, "item_id": item_id, "warehouse": warehouse.name, "name": product.name,
        "on_hand_qty": balance.on_hand_qty if balance else 0, "version": balance.version if balance else 0}


def create_warehouse(session, payload, actor):
    code = payload.code.upper()
    if session.scalar(select(Warehouse.id).where(Warehouse.code == code)):
        raise DomainError("warehouse_exists", "Mã kho đã tồn tại.", 409)
    row = Warehouse(code=code, name=payload.name, country=payload.country, active=True, version=1, created_by=actor)
    session.add(row); session.flush()
    audit(session, "warehouse", row.id, "created", actor, code=code, name=row.name)
    return record(row)


def update_warehouse(session, key, payload, actor):
    row = session.scalar(select(Warehouse).where(Warehouse.id == key).with_for_update())
    if row is None:
        raise DomainError("not_found", "Không có kho này.", 404)
    check_version(row.version, payload.expected_version)
    if not payload.active:
        balance = session.scalar(select(Balance.item_id).where(Balance.warehouse_id == key, Balance.on_hand_qty > 0).limit(1))
        pending = session.scalar(select(Line.id).join(Order, Line.order_id == Order.id).where(Line.warehouse_id == key,
            Order.status.in_(["ordered", "partially_received"]), Line.ordered_qty > Line.received_qty).limit(1))
        if balance is not None or pending is not None:
            raise DomainError("warehouse_in_use", "Kho còn hàng hoặc còn đơn chờ nhận; chưa thể đóng.", 409)
    audit(session, "warehouse", key, "updated", actor, old_name=row.name, name=payload.name, active=payload.active, reason=payload.reason)
    row.name, row.country, row.active, row.version = payload.name, payload.country, payload.active, row.version + 1
    session.flush()
    return record(row)


def create_product(session, payload, actor):
    # Registration adds metadata; it never fabricates sales history or rewrites a raw SKU.
    session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": "ops-catalog:" + payload.carrier})
    supplier = session.scalar(select(Supplier).where(Supplier.carrier == payload.carrier))
    if supplier is None:
        supplier = Supplier(carrier=payload.carrier); session.add(supplier); session.flush()
    route = session.scalar(select(SourceWarehouse).where(SourceWarehouse.carrier == payload.carrier,
        SourceWarehouse.destination_country == payload.destination_country))
    if route is None:
        route = SourceWarehouse(code="ROUTE-" + uuid.uuid4().hex[:16].upper(), destination_country=payload.destination_country,
            carrier=payload.carrier, city=payload.destination_country, is_assumed=True, assumption_source="user_declared_route_v1", version=1)
        session.add(route); session.flush()
    item = session.scalar(select(Item).where(Item.warehouse_id == route.id, Item.sku == payload.sku, Item.product_type == payload.product_type))
    if item is None:
        item = Item(warehouse_id=route.id, sku=payload.sku, product_type=payload.product_type, first_seen_date=today())
        session.add(item); session.flush()
    if session.get(Product, item.id):
        raise DomainError("product_exists", "Sản phẩm đã có trong danh mục vận hành.", 409)
    product = Product(item_id=item.id, name=payload.name, active=True, version=1, created_by=actor)
    session.add(product); session.flush()
    audit(session, "product", item.id, "registered", actor, sku=payload.sku, supplier_id=supplier.id)
    return {"id": item.id, "sku": item.sku, "name": product.name, "product_type": item.product_type,
        "destination_country": payload.destination_country, "carrier": payload.carrier, "supplier_id": supplier.id, "active": True, "version": 1}


def update_product(session, key, payload, actor):
    row = session.scalar(select(Product).where(Product.item_id == key).with_for_update())
    if row is None:
        raise DomainError("not_found", "Không có sản phẩm vận hành này.", 404)
    check_version(row.version, payload.expected_version)
    audit(session, "product", key, "updated", actor, old_name=row.name, name=payload.name, active=payload.active, reason=payload.reason)
    row.name, row.active, row.version = payload.name, payload.active, row.version + 1
    session.flush()
    return record(row)


def products(session, page, size, supplier_id=None, search=None, active=True):
    query = select(Item.id, Item.sku, Product.name, Item.product_type, SourceWarehouse.destination_country,
        Supplier.id.label("supplier_id"), Supplier.carrier, Product.active, Product.version).select_from(Product).join(
        Item, Product.item_id == Item.id).join(SourceWarehouse, Item.warehouse_id == SourceWarehouse.id).join(
        Supplier, SourceWarehouse.carrier == Supplier.carrier)
    if supplier_id is not None:
        query = query.where(Supplier.id == supplier_id)
    if active is not None:
        query = query.where(Product.active == active)
    if search:
        query = query.where(or_(Item.sku.icontains(search, autoescape=True), Product.name.icontains(search, autoescape=True)))
    return page_rows(session, query.order_by(Product.name, Item.id), page, size)


def journal(session, page, size):
    query = select(Document.id, Document.number, Document.kind, Document.order_id, Document.occurred_on,
        Document.external_ref, Document.reason, Document.created_at, User.display_name.label("actor"))
    return page_rows(session, query.join(User, Document.created_by == User.id).order_by(Document.created_at.desc(), Document.id), page, size)
