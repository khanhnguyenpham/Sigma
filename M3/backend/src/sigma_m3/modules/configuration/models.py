from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, Index, Integer, Numeric,
    Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sigma_m3.core.db import Base, created, fk, identity


class Policy(Base):
    __tablename__ = "supplier_item_policies"
    id = identity()
    item_id = fk("items")
    supplier_id = fk("suppliers")
    version = Column(Integer, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    configured_rop_floor = Column(BigInteger, nullable=False)
    moq = Column(BigInteger, nullable=False)
    safety_days = Column(Numeric(8, 3), nullable=False)
    is_assumed = Column(Boolean, nullable=False, default=True)
    assumption_source = Column(Text, nullable=False)
    created_at = created()
    __table_args__ = (
        UniqueConstraint("item_id", "version"),
        UniqueConstraint("item_id", "effective_from"),
        UniqueConstraint("id", "item_id"),
        CheckConstraint(
            "configured_rop_floor>=0 AND moq>=1 AND safety_days>=0 AND version>=1"
        ),
        CheckConstraint("effective_to IS NULL OR effective_to>effective_from"),
        Index("ix_policy_effective", "item_id", "effective_from", "effective_to"),
    )


class Scenario(Base):
    __tablename__ = "scenarios"
    id = identity()
    code = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False, default="")
    settings = Column(JSONB, nullable=False)
    assumption_version = Column(Text, nullable=False)
    created_at = created()
    __table_args__ = (
        UniqueConstraint("code", "version"),
        CheckConstraint("version>=1"),
    )
