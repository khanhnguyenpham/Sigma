"""Dealers and their stock requests. Assumed business flow (not mentor-confirmed): submit -> approve -> issue -> receive."""
import uuid
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from core.db import Base, created, fk, identity


class Dealer(Base):
    __tablename__ = "dealers"
    id = identity()
    code = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    contact = Column(Text, nullable=False, server_default="")
    active = Column(Boolean, nullable=False, server_default=text("true"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    created_by = fk("auth_users")
    created_at = created()
    __table_args__ = (CheckConstraint("length(btrim(code)) BETWEEN 1 AND 40 AND length(btrim(name)) BETWEEN 1 AND 120 AND length(contact)<=200 AND version>=1", name="ck_dealer"),)


class DealerRequest(Base):
    __tablename__ = "dealer_requests"
    id = identity()
    number = Column(Text, nullable=False, unique=True)
    dealer_id = fk("dealers")
    status = Column(Text, nullable=False)
    note = Column(Text, nullable=False, server_default="")
    reject_reason = Column(Text)
    warehouse_id = fk("ops_warehouses", nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("ops_stock_documents.id", ondelete="RESTRICT"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    request_key = Column(Text, nullable=False, unique=True)
    request_digest = Column(Text, nullable=False)
    created_by = fk("auth_users")
    created_at = created()
    decided_by = fk("auth_users", nullable=True)
    decided_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('submitted','approved','rejected','cancelled','issued','received')", name="ck_dealer_request_status"),
        CheckConstraint("(status='rejected')=(reject_reason IS NOT NULL) AND (status IN ('issued','received'))=(document_id IS NOT NULL AND warehouse_id IS NOT NULL) AND (status='received')=(received_at IS NOT NULL) AND (decided_by IS NULL)=(decided_at IS NULL) AND length(note)<=1000 AND version>=1", name="ck_dealer_request_state"),
        Index("ix_dealer_request_dealer_status", "dealer_id", "status", "id"),
    )


class DealerRequestLine(Base):
    __tablename__ = "dealer_request_lines"
    id = identity()
    request_id = fk("dealer_requests")
    item_id = fk("items")
    quantity = Column(BigInteger, nullable=False)
    __table_args__ = (
        UniqueConstraint("request_id", "item_id", name="uq_dealer_request_item"),
        CheckConstraint("quantity>0", name="ck_dealer_request_quantity"),
        Index("ix_dealer_request_line_request", "request_id"),
    )
