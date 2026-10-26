from sqlalchemy import Boolean, CheckConstraint, Column, Date, ForeignKey, Index, SmallInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from core.db import Base, fk, identity


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
    predicted_threshold_date = Column(Date)
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
        CheckConstraint("alert_type IN ('below_rop','depletion','projected_below_rop')", name="ck_alert_type"),
        CheckConstraint(
            "state IN ('low_stock','pending_covers','urgent','early','already_depleted','not_within_horizon','threshold_warning')",
            name="ck_alert_state",
        ),
        CheckConstraint(
            "(alert_type = 'projected_below_rop' AND state = 'threshold_warning' AND predicted_threshold_date IS NOT NULL AND predicted_threshold_date > as_of_date AND predicted_threshold_date <= as_of_date + 14) OR "
            "(alert_type <> 'projected_below_rop' AND state <> 'threshold_warning' AND predicted_threshold_date IS NULL)",
            name="ck_alert_threshold_date",
        ),
        CheckConstraint(
            "evaluation_class IS NULL OR evaluation_class IN ('TP','FP','FN','TN')"
        ),
        Index("ix_alert_state", "run_id", "state", "as_of_date"),
    )
