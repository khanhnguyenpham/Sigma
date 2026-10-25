from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, Double, ForeignKey, Index, SmallInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from core.db import Base, fk, identity

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
