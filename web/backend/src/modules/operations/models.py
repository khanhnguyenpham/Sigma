import uuid
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from core.db import Base, created, fk, identity


class OperationalWarehouse(Base):
    __tablename__ = "ops_warehouses"
    id = identity()
    code = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    country = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    created_by = fk("auth_users")
    created_at = created()
    __table_args__ = (CheckConstraint("length(btrim(code)) BETWEEN 1 AND 40 AND length(btrim(name)) BETWEEN 1 AND 120 AND length(btrim(country)) BETWEEN 1 AND 100 AND version>=1", name="ck_ops_warehouse"),)


class OperationalProduct(Base):
    __tablename__ = "ops_products"
    item_id = Column(BigInteger, ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True)
    name = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    created_by = fk("auth_users")
    created_at = created()
    __table_args__ = (CheckConstraint("length(btrim(name)) BETWEEN 1 AND 160 AND version>=1", name="ck_ops_product"),)


class SupplierSettings(Base):
    __tablename__ = "ops_supplier_settings"
    supplier_id = Column(BigInteger, ForeignKey("suppliers.id", ondelete="RESTRICT"), primary_key=True)
    lead_time_days = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False)
    updated_by = fk("auth_users")
    updated_at = created()
    __table_args__ = (CheckConstraint("lead_time_days BETWEEN 1 AND 365 AND version>=1", name="ck_ops_supplier_settings"),)


class OperationalOrder(Base):
    __tablename__ = "ops_purchase_orders"
    id = identity()
    number = Column(Text, nullable=False, unique=True)
    supplier_id = fk("suppliers")
    ordered_on = Column(Date, nullable=False)
    eta = Column(Date, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    supplier_settings_version = Column(Integer, nullable=False)
    status = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, server_default=text("1"))
    note = Column(Text, nullable=False, server_default="")
    request_key = Column(Text, nullable=False, unique=True)
    request_digest = Column(Text, nullable=False)
    created_by = fk("auth_users")
    confirmed_by = fk("auth_users", nullable=True)
    confirmed_at = Column(DateTime(timezone=True))
    cancelled_by = fk("auth_users", nullable=True)
    cancelled_at = Column(DateTime(timezone=True))
    created_at = created()
    __table_args__ = (
        CheckConstraint("lead_time_days BETWEEN 1 AND 365 AND eta=ordered_on+lead_time_days AND supplier_settings_version>=0 AND version>=1", name="ck_ops_order_dates"),
        CheckConstraint("status IN ('draft','ordered','partially_received','received','cancelled')", name="ck_ops_order_status"),
        CheckConstraint("(confirmed_by IS NULL)=(confirmed_at IS NULL) AND (cancelled_by IS NULL)=(cancelled_at IS NULL)", name="ck_ops_order_actors"),
        Index("ix_ops_order_supplier_status", "supplier_id", "status", "id"),
    )


class OperationalOrderLine(Base):
    __tablename__ = "ops_purchase_order_lines"
    id = identity()
    order_id = fk("ops_purchase_orders")
    item_id = fk("items")
    warehouse_id = fk("ops_warehouses")
    ordered_qty = Column(BigInteger, nullable=False)
    received_qty = Column(BigInteger, nullable=False, server_default=text("0"))
    __table_args__ = (
        UniqueConstraint("order_id", "item_id", "warehouse_id", name="uq_ops_order_product_location"),
        UniqueConstraint("id", "order_id", "item_id", "warehouse_id", name="uq_ops_line_identity"),
        CheckConstraint("ordered_qty>0 AND received_qty BETWEEN 0 AND ordered_qty", name="ck_ops_line_quantity"),
        Index("ix_ops_line_order", "order_id"),
    )


class StockDocument(Base):
    __tablename__ = "ops_stock_documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number = Column(Text, nullable=False, unique=True)
    kind = Column(Text, nullable=False)
    order_id = fk("ops_purchase_orders", nullable=True)
    occurred_on = Column(Date, nullable=False)
    external_ref = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    request_key = Column(Text, nullable=False, unique=True)
    request_digest = Column(Text, nullable=False)
    created_by = fk("auth_users")
    created_at = created()
    __table_args__ = (
        UniqueConstraint("id", "kind", name="uq_ops_document_kind"),
        UniqueConstraint("id", "order_id", name="uq_ops_document_order"),
        UniqueConstraint("order_id", "external_ref", name="uq_ops_order_delivery_ref"),
        CheckConstraint("(kind='receipt' AND order_id IS NOT NULL) OR (kind IN ('issue','adjustment') AND order_id IS NULL)", name="ck_ops_document_kind"),
        CheckConstraint("length(btrim(external_ref)) BETWEEN 1 AND 120 AND length(reason)<=1000 AND length(request_key) BETWEEN 1 AND 128", name="ck_ops_document_text"),
        Index("ix_ops_document_date", "occurred_on", "created_at"),
    )


class StockDocumentLine(Base):
    __tablename__ = "ops_stock_document_lines"
    id = identity()
    document_id = Column(UUID(as_uuid=True), ForeignKey("ops_stock_documents.id", ondelete="RESTRICT"), nullable=False)
    kind = Column(Text, nullable=False)
    order_id = Column(BigInteger)
    order_line_id = Column(BigInteger)
    item_id = fk("items")
    warehouse_id = fk("ops_warehouses")
    quantity_delta = Column(BigInteger, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["document_id", "kind"], ["ops_stock_documents.id", "ops_stock_documents.kind"], ondelete="RESTRICT", name="fk_ops_line_document_kind"),
        ForeignKeyConstraint(["document_id", "order_id"], ["ops_stock_documents.id", "ops_stock_documents.order_id"], ondelete="RESTRICT", name="fk_ops_line_document_order"),
        ForeignKeyConstraint(["order_line_id", "order_id", "item_id", "warehouse_id"], ["ops_purchase_order_lines.id", "ops_purchase_order_lines.order_id", "ops_purchase_order_lines.item_id", "ops_purchase_order_lines.warehouse_id"], ondelete="RESTRICT", name="fk_ops_receipt_line_order"),
        UniqueConstraint("document_id", "item_id", "warehouse_id", name="uq_ops_document_product_location"),
        CheckConstraint("balance_after>=0 AND ((kind='receipt' AND quantity_delta>0 AND order_id IS NOT NULL AND order_line_id IS NOT NULL) OR (kind='issue' AND quantity_delta<0 AND order_id IS NULL AND order_line_id IS NULL) OR (kind='adjustment' AND order_id IS NULL AND order_line_id IS NULL))", name="ck_ops_posted_line"),
        Index("ix_ops_ledger_product_location", "warehouse_id", "item_id", "id"),
    )


class StockBalance(Base):
    __tablename__ = "ops_stock_balances"
    warehouse_id = Column(BigInteger, ForeignKey("ops_warehouses.id", ondelete="RESTRICT"), primary_key=True)
    item_id = Column(BigInteger, ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True)
    on_hand_qty = Column(BigInteger, nullable=False, server_default=text("0"))
    version = Column(Integer, nullable=False, server_default=text("0"))
    last_movement_on = Column(Date)
    updated_at = created()
    __table_args__ = (CheckConstraint("on_hand_qty>=0 AND version>=0", name="ck_ops_balance"),)


class OperationAudit(Base):
    __tablename__ = "ops_audit_events"
    id = identity()
    entity_type = Column(Text, nullable=False)
    entity_key = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    actor_id = fk("auth_users")
    details = Column(JSONB, nullable=False)
    created_at = created()
    __table_args__ = (Index("ix_ops_audit_entity", "entity_type", "entity_key", "id"),)
