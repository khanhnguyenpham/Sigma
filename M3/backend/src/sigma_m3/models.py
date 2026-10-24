"""Register all thirteen tables; remaining domain models move in steps 6–7."""

import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Double,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID



from sigma_m3.core.db import Base, created, fk, identity
from sigma_m3.modules.catalog.models import (
    Warehouse as Warehouse,
    Item as Item,
    Supplier as Supplier,
)
from sigma_m3.modules.configuration.models import Policy as Policy, Scenario as Scenario


class Run(Base):
    __tablename__ = "runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="queued")
    source_import_run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT")
    )
    forecast_run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT")
    )
    retry_of_run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT")
    )
    scenario_id = fk("scenarios", nullable=True)
    as_of_date = Column(Date, nullable=False)
    period_start = Column(Date)
    period_end = Column(Date)
    observation_end = Column(Date, nullable=False)
    target_version = Column(Text, nullable=False)
    config_version = Column(Text, nullable=False)
    assumption_version = Column(Text, nullable=False)
    source_sha256 = Column(String(64))
    code_revision = Column(Text, nullable=False)
    code_sha256 = Column(String(64), nullable=False)
    config_snapshot = Column(JSONB, nullable=False)
    config_sha256 = Column(String(64), nullable=False)
    request_key = Column(String(128), nullable=False, unique=True)
    request_sha256 = Column(String(64), nullable=False)
    selection_sha256 = Column(String(64))
    result_summary = Column(JSONB, nullable=False, default=dict)
    artifact_manifest = Column(JSONB, nullable=False, default=dict)
    error_code = Column(Text)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    heartbeat_at = Column(DateTime(timezone=True))
    created_at = created()
    __table_args__ = (
        CheckConstraint(
            "kind IN ('source_import','forecast','policy_replay','alert_replay','stock_projection')"
        ),
        CheckConstraint(
            "status IN ('queued','running','complete','failed','invalidated')"
        ),
        CheckConstraint(
            "source_import_run_id IS DISTINCT FROM id AND forecast_run_id IS DISTINCT FROM id AND retry_of_run_id IS DISTINCT FROM id"
        ),
        CheckConstraint(
            "period_end IS NULL OR (period_start IS NOT NULL AND period_end>=period_start)"
        ),
        Index("ix_runs_queue", "status", "created_at"),
    )


class DailySales(Base):
    __tablename__ = "daily_sales"
    source_import_run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), primary_key=True
    )
    item_id = Column(
        BigInteger, ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True
    )
    date = Column(Date, primary_key=True)
    sales_qty = Column(BigInteger)
    order_count = Column(BigInteger)
    actual_available = Column(Boolean, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "(actual_available AND sales_qty IS NOT NULL AND sales_qty>=0 AND order_count IS NOT NULL AND order_count>=0) OR (NOT actual_available AND sales_qty IS NULL AND order_count IS NULL)"
        ),
        Index("ix_sales_date", "source_import_run_id", "date", "item_id"),
    )


class RouteForecast(Base):
    __tablename__ = "route_forecasts"
    id = identity()
    run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id = fk("warehouses")
    as_of_date = Column(Date, nullable=False)
    block = Column(SmallInteger, nullable=False)
    window_start = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    forecast_qty = Column(Double, nullable=False)
    actual_qty = Column(Double)
    actual_available = Column(Boolean, nullable=False)
    family = Column(Text, nullable=False)
    model_id = Column(Text, nullable=False)
    selection_basis = Column(Text, nullable=False)
    parent_bundle_sha256 = Column(Text)
    __table_args__ = (
        UniqueConstraint("run_id", "warehouse_id", "as_of_date", "block"),
        CheckConstraint(
            "block IN (1,2) AND window_start=as_of_date+1+7*(block-1) AND target_date=as_of_date+7*block"
        ),
        CheckConstraint("forecast_qty>=0 AND forecast_qty<'Infinity'::float8"),
        CheckConstraint(
            "(actual_available AND actual_qty IS NOT NULL AND actual_qty>=0 AND actual_qty<'Infinity'::float8) OR (NOT actual_available AND actual_qty IS NULL)"
        ),
        Index("ix_route_forecast_origin", "run_id", "as_of_date", "warehouse_id"),
    )


class ItemForecast(Base):
    __tablename__ = "item_forecasts"
    id = identity()
    run_id = Column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    item_id = fk("items")
    as_of_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    horizon_day = Column(SmallInteger, nullable=False)
    forecast_qty = Column(Double, nullable=False)
    actual_qty = Column(BigInteger)
    actual_available = Column(Boolean, nullable=False)
    item_share = Column(Double, nullable=False)
    weekday_weight = Column(Double, nullable=False)
    share_window_days = Column(SmallInteger, nullable=False)
    allocation_basis = Column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint("run_id", "item_id", "as_of_date", "target_date"),
        CheckConstraint(
            "horizon_day BETWEEN 1 AND 14 AND target_date=as_of_date+horizon_day"
        ),
        CheckConstraint(
            "forecast_qty>=0 AND forecast_qty<'Infinity'::float8 AND item_share BETWEEN 0 AND 1 AND weekday_weight BETWEEN 0 AND 1 AND share_window_days IN (30,90)"
        ),
        CheckConstraint(
            "(actual_available AND actual_qty IS NOT NULL AND actual_qty>=0) OR (NOT actual_available AND actual_qty IS NULL)"
        ),
        Index("ix_item_forecast_origin", "run_id", "as_of_date", "item_id"),
        Index("ix_item_forecast_target", "run_id", "target_date"),
    )


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
