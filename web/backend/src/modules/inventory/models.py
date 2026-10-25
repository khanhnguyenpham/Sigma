from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from core.db import Base, fk, identity


class InventoryEvent(Base):
    __tablename__ = "inventory_events"
    id = identity()
    run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    window_origin = Column(Date, nullable=False)
    item_id = fk("items")
    event_at = Column(DateTime(timezone=True), nullable=False)
    event_sequence = Column(BigInteger, nullable=False)
    event_kind = Column(Text, nullable=False)
    source_sequence = Column(BigInteger)
    replenishment_order_id = fk("replenishment_orders", nullable=True)
    quantity = Column(BigInteger, nullable=False)
    fulfilled_qty = Column(BigInteger, nullable=False)
    shortage_qty = Column(BigInteger, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    is_simulated = Column(Boolean, nullable=False, default=True)
    __table_args__ = (
        UniqueConstraint("run_id", "window_origin", "item_id", "event_sequence"),
        CheckConstraint(
            "quantity>=0 AND fulfilled_qty>=0 AND shortage_qty>=0 AND balance_after>=0 AND event_sequence>=0"
        ),
        CheckConstraint(
            "(event_kind='sale' AND quantity=fulfilled_qty+shortage_qty AND source_sequence IS NOT NULL AND replenishment_order_id IS NULL) OR (event_kind='receipt' AND fulfilled_qty=0 AND shortage_qty=0 AND replenishment_order_id IS NOT NULL) OR (event_kind='initial_stock' AND fulfilled_qty=0 AND shortage_qty=0 AND replenishment_order_id IS NULL)"
        ),
        Index(
            "uq_receipt_once",
            "replenishment_order_id",
            unique=True,
            postgresql_where=text("event_kind='receipt'"),
        ),
    )


class InventoryDaily(Base):
    __tablename__ = "inventory_daily"
    id = identity()
    run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    window_origin = Column(Date, nullable=False)
    item_id = fk("items")
    date = Column(Date, nullable=False)
    policy_id = Column(BigInteger)
    forecast_as_of_date = Column(Date, nullable=False)
    opening_qty = Column(BigInteger, nullable=False)
    receipts_qty = Column(BigInteger, nullable=False)
    sales_qty = Column(BigInteger, nullable=False)
    fulfilled_qty = Column(BigInteger, nullable=False)
    shortage_qty = Column(BigInteger, nullable=False)
    closing_qty = Column(BigInteger, nullable=False)
    ss = Column(BigInteger)
    rop_forecast = Column(BigInteger)
    rop = Column(BigInteger)
    target_stock = Column(BigInteger)
    pending_qty = Column(BigInteger, nullable=False)
    inventory_position = Column(BigInteger, nullable=False)
    needs_replenishment = Column(Boolean)
    recommended_qty = Column(BigInteger)
    config_status = Column(Text, nullable=False)
    is_simulated = Column(Boolean, nullable=False, default=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["policy_id", "item_id"],
            ["supplier_item_policies.id", "supplier_item_policies.item_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("run_id", "window_origin", "item_id", "date"),
        CheckConstraint(
            "opening_qty>=0 AND receipts_qty>=0 AND sales_qty>=0 AND fulfilled_qty>=0 AND shortage_qty>=0 AND closing_qty>=0 AND pending_qty>=0"
        ),
        CheckConstraint(
            "closing_qty=opening_qty+receipts_qty-fulfilled_qty AND sales_qty=fulfilled_qty+shortage_qty AND inventory_position=closing_qty+pending_qty"
        ),
        CheckConstraint(
            "ss>=0 AND rop_forecast>=0 AND rop>=0 AND target_stock>=0 AND recommended_qty>=0"
        ),
        Index("ix_inventory_date", "run_id", "date", "item_id"),
    )
