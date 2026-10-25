"""Register all thirteen tables; inventory domain models move in step 7."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID


from core.db import Base, fk, identity
from modules.catalog.models import (
    Warehouse as Warehouse,
    Item as Item,
    Supplier as Supplier,
)
from modules.configuration.models import Policy as Policy, Scenario as Scenario
from modules.runs.models import Run as Run
from modules.forecasting.models import DailySales as DailySales, RouteForecast as RouteForecast, ItemForecast as ItemForecast


class Replenishment(Base):
    __tablename__ = "replenishment_orders"
    id = identity()
    run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    window_origin = Column(Date, nullable=False)
    item_id = fk("items")
    policy_id = Column(BigInteger, nullable=False)
    order_key = Column(Text, nullable=False)
    ordered_on = Column(Date, nullable=False)
    eta = Column(Date, nullable=False)
    ordered_qty = Column(BigInteger, nullable=False)
    received_qty = Column(BigInteger, nullable=False, default=0)
    status = Column(Text, nullable=False, default="ordered")
    is_initial = Column(Boolean, nullable=False, default=False)
    is_simulated = Column(Boolean, nullable=False, default=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["policy_id", "item_id"],
            ["supplier_item_policies.id", "supplier_item_policies.item_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("run_id", "window_origin", "order_key"),
        CheckConstraint(
            "ordered_qty>0 AND eta=ordered_on+7 AND ((status='ordered' AND received_qty=0) OR (status='received' AND received_qty=ordered_qty))"
        ),
        Index("ix_orders_eta", "run_id", "eta", "status"),
    )


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


class Alert(Base):
    __tablename__ = "alerts"
    id = identity()
    run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    window_origin = Column(Date, nullable=False)
    item_id = fk("items")
    as_of_date = Column(Date, nullable=False)
    alert_type = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    predicted_depletion_date = Column(Date)
    actual_depletion_date = Column(Date)
    lead_days = Column(SmallInteger)
    is_evaluable = Column(Boolean, nullable=False)
    evaluation_class = Column(Text)
    exclusion_reason = Column(Text)
    explanation = Column(JSONB, nullable=False)
    is_simulated = Column(Boolean, nullable=False, default=True)
    __table_args__ = (
        UniqueConstraint(
            "run_id", "window_origin", "item_id", "as_of_date", "alert_type"
        ),
        CheckConstraint("alert_type IN ('below_rop','depletion')"),
        CheckConstraint(
            "state IN ('low_stock','pending_covers','urgent','early','already_depleted','not_within_horizon')"
        ),
        CheckConstraint(
            "evaluation_class IS NULL OR evaluation_class IN ('TP','FP','FN','TN')"
        ),
        Index("ix_alert_state", "run_id", "state", "as_of_date"),
    )
