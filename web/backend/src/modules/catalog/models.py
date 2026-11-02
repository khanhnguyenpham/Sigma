from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, ForeignKey, ForeignKeyConstraint, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from core.db import Base, created, fk, identity


class Warehouse(Base):
    __tablename__ = "warehouses"
    id = identity()
    code = Column(Text, nullable=False, unique=True)
    destination_country = Column(Text, nullable=False)
    carrier = Column(Text, ForeignKey("suppliers.carrier", name="fk_warehouse_carrier", ondelete="RESTRICT"), nullable=False)
    city = Column(Text, nullable=False)
    is_assumed = Column(Boolean, nullable=False, default=True)
    assumption_source = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = created()
    __table_args__ = (
        UniqueConstraint("destination_country", "carrier"),
        CheckConstraint("version >= 1"),
        CheckConstraint("length(city)>0"),
    )


class Item(Base):
    __tablename__ = "items"
    id = identity()
    warehouse_id = fk("warehouses")
    sku = Column(Text, nullable=False)
    product_type = Column(Text, nullable=False)
    first_seen_date = Column(Date, nullable=False)
    created_at = created()
    __table_args__ = (
        UniqueConstraint("warehouse_id", "sku", "product_type"),
        CheckConstraint("product_type IN ('eSIM','physical_SIM')"),
        Index("ix_items_warehouse", "warehouse_id"),
    )


class Supplier(Base):
    __tablename__ = "suppliers"
    id = identity()
    carrier = Column(Text, nullable=False)
    created_at = created()
    __table_args__ = (
        UniqueConstraint("carrier", name="uq_suppliers_carrier"),
        CheckConstraint("length(btrim(carrier))>0 AND carrier=btrim(carrier)", name="ck_supplier_carrier"),
    )


class ItemSupplyChange(Base):
    __tablename__ = "item_supply_changes"
    id = identity()
    item_id = fk("items")
    version = Column(Integer, nullable=False)
    action = Column(Text, nullable=False)
    known_on = Column(Date, nullable=False)
    effective_on = Column(Date, nullable=False)
    target_change_id = Column(BigInteger)
    reason = Column(Text, nullable=False)
    is_assumed = Column(Boolean, nullable=False, server_default=text("true"))
    assumption_source = Column(Text, nullable=False, server_default="user_declared_supply_simulation_v1")
    created_at = created()
    __table_args__ = (
        UniqueConstraint("item_id", "version", name="uq_supply_item_version"),
        UniqueConstraint("id", "item_id", name="uq_supply_id_item"),
        ForeignKeyConstraint(["target_change_id", "item_id"],
                             ["item_supply_changes.id", "item_supply_changes.item_id"],
                             name="fk_supply_target_item", ondelete="RESTRICT"),
        CheckConstraint("version >= 1", name="ck_supply_version"),
        CheckConstraint("(action='stop' AND target_change_id IS NULL AND effective_on>=known_on) OR "
                        "(action IN ('cancel_stop','resume') AND target_change_id IS NOT NULL AND effective_on=known_on)",
                        name="ck_supply_action_dates"),
        CheckConstraint("length(reason) BETWEEN 1 AND 1000 AND reason ~ '[^[:space:]]'", name="ck_supply_reason"),
        CheckConstraint("is_assumed AND assumption_source='user_declared_supply_simulation_v1'", name="ck_supply_provenance"),
        Index("ix_supply_item_known_version", "item_id", "known_on", "version"),
    )


class ProviderProductNotice(Base):
    __tablename__ = "provider_product_notices"
    id = identity()
    supplier_id = fk("suppliers")
    scope_definition = Column(JSONB, nullable=False)
    created_at = created()
    __table_args__ = (
        CheckConstraint("jsonb_typeof(scope_definition)='object' AND scope_definition <> '{}'::jsonb",
                        name="ck_provider_notice_scope"),
    )


class ProviderProductNoticeItem(Base):
    __tablename__ = "provider_product_notice_items"
    notice_id = Column(BigInteger, ForeignKey("provider_product_notices.id", ondelete="RESTRICT"), primary_key=True)
    item_id = Column(BigInteger, ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True)
    __table_args__ = (Index("ix_provider_item_notice", "item_id", "notice_id"),)


class ProviderProductNoticeEvent(Base):
    __tablename__ = "provider_product_notice_events"
    id = identity()
    notice_id = fk("provider_product_notices")
    version = Column(Integer, nullable=False)
    action = Column(Text, nullable=False)
    target_event_id = Column(BigInteger)
    known_on = Column(Date, nullable=False)
    effective_on = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    source_description = Column(Text, nullable=False)
    source_ref = Column(Text)
    is_assumed = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = created()
    __table_args__ = (
        UniqueConstraint("notice_id", "version", name="uq_provider_notice_version"),
        UniqueConstraint("id", "notice_id", name="uq_provider_event_notice"),
        ForeignKeyConstraint(["target_event_id", "notice_id"],
                             ["provider_product_notice_events.id", "provider_product_notice_events.notice_id"],
                             name="fk_provider_target_notice", ondelete="RESTRICT"),
        CheckConstraint("(version=1 AND action='stop' AND target_event_id IS NULL) OR "
                        "(version=2 AND action IN ('cancel_stop','resume_supply') AND target_event_id IS NOT NULL "
                        "AND target_event_id<>id)", name="ck_provider_event_action"),
        CheckConstraint("action='stop' OR (action='cancel_stop' AND effective_on=known_on) OR "
                        "(action='resume_supply' AND effective_on>=known_on)", name="ck_provider_event_dates"),
        CheckConstraint("length(reason) BETWEEN 1 AND 1000 AND reason ~ '[^[:space:]]'",
                        name="ck_provider_event_reason"),
        CheckConstraint("length(source_description) BETWEEN 1 AND 1000 AND source_description ~ '[^[:space:]]'",
                        name="ck_provider_event_source"),
        CheckConstraint("source_ref IS NULL OR (length(source_ref)<=2048 AND source_ref ~ '^https?://[^[:space:]]+$')",
                        name="ck_provider_event_ref"),
        CheckConstraint("is_assumed", name="ck_provider_event_assumed"),
        Index("ix_provider_notice_known", "notice_id", "known_on", "version"),
    )
