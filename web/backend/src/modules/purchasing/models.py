from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, ForeignKey, ForeignKeyConstraint, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from core.db import Base, fk, identity


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
