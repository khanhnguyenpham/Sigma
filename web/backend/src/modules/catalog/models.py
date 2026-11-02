from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, ForeignKey, ForeignKeyConstraint, Index, Integer, Text, UniqueConstraint, text
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
        CheckConstraint("(action='stop' AND target_change_id IS NULL AND effective_on>=known_on+7) OR "
                        "(action IN ('cancel_stop','resume') AND target_change_id IS NOT NULL AND effective_on=known_on)",
                        name="ck_supply_action_dates"),
        CheckConstraint("length(reason) BETWEEN 1 AND 1000 AND reason ~ '[^[:space:]]'", name="ck_supply_reason"),
        CheckConstraint("is_assumed AND assumption_source='user_declared_supply_simulation_v1'", name="ck_supply_provenance"),
        Index("ix_supply_item_known_version", "item_id", "known_on", "version"),
    )
