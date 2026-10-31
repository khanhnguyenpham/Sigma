from sqlalchemy import Boolean, CheckConstraint, Column, Date, ForeignKey, Index, Integer, Text, UniqueConstraint
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
