import uuid
from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from core.db import Base, created, fk

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
