import uuid
from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from core.db import Base, created, fk


class RunConfig(Base):
    """Frozen configuration of one run; written at enqueue, completed by the worker."""
    __tablename__ = "run_configs"
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    config_snapshot = Column(JSONB, nullable=False)


class RunResult(Base):
    """Progress/summary and artifact list of one run."""
    __tablename__ = "run_results"
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    result_summary = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    artifact_manifest = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))


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
    code_revision = Column(Text, nullable=False)
    request_key = Column(String(128), nullable=False, unique=True)
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
    config = relationship(RunConfig, uselist=False, lazy="selectin", cascade="all, delete-orphan")
    result = relationship(RunResult, uselist=False, lazy="selectin", cascade="all, delete-orphan")
    # Callers keep reading/assigning run.config_snapshot etc.; the values live in the two tables above.
    config_snapshot = association_proxy("config", "config_snapshot",
                                        creator=lambda value: RunConfig(config_snapshot=value))
    result_summary = association_proxy("result", "result_summary",
                                       creator=lambda value: RunResult(result_summary=value, artifact_manifest={}))
    artifact_manifest = association_proxy("result", "artifact_manifest",
                                          creator=lambda value: RunResult(result_summary={}, artifact_manifest=value))

    def __init__(self, **values):
        values.setdefault("result_summary", {})
        super().__init__(**values)
