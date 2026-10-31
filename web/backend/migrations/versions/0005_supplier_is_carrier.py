"""Use the source carrier as supplier; preserve IDs and all frozen runs."""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0005_carrier"
down_revision = "0004_fixed_qty"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE suppliers, warehouses, items, supplier_item_policies IN ACCESS EXCLUSIVE MODE"))
    suppliers = connection.execute(sa.text("SELECT id, code, assumption_source FROM suppliers ORDER BY id")).all()
    warehouses = connection.execute(sa.text("SELECT code, carrier FROM warehouses")).all()
    linked = connection.execute(sa.text("""
        SELECT DISTINCT p.supplier_id, w.carrier FROM supplier_item_policies p
        JOIN items i ON i.id=p.item_id JOIN warehouses w ON w.id=i.warehouse_id
    """)).all()
    candidates = {}
    for supplier_id, carrier in linked:
        candidates.setdefault(supplier_id, set()).add(carrier)
    routes = {code: carrier for code, carrier in warehouses}
    mapping = {}
    for supplier_id, code, source in suppliers:
        carriers = candidates.get(supplier_id, set())
        if source == "route_supplier_seed_v1" and code.startswith("SUP-"):
            carrier = routes.get("WH-" + code[4:])
            if carrier is not None:
                carriers = carriers | {carrier}
        if len(carriers) > 1:
            raise RuntimeError("Supplier spans multiple carriers; resolve mapping before migration")
        mapping[supplier_id] = next(iter(carriers), code)
    if len(set(mapping.values())) != len(mapping):
        raise RuntimeError("Multiple supplier IDs map to one carrier; resolve references before migration")
    # Two phases avoid unique-code collisions when existing names are swapped.
    token = uuid4().hex
    for supplier_id in mapping:
        connection.execute(sa.text("UPDATE suppliers SET code=:code WHERE id=:id"),
                           dict(id=supplier_id, code=f"__chg079_{token}_{supplier_id}"))
    for supplier_id, carrier in mapping.items():
        connection.execute(sa.text("UPDATE suppliers SET code=:code WHERE id=:id"),
                           dict(id=supplier_id, code=carrier))
    op.drop_constraint("suppliers_code_key", "suppliers", type_="unique")
    op.alter_column("suppliers", "code", new_column_name="carrier")
    for column in ("display_name", "is_assumed", "assumption_source"):
        op.drop_column("suppliers", column)
    op.create_unique_constraint("uq_suppliers_carrier", "suppliers", ["carrier"])
    op.create_check_constraint("ck_supplier_carrier", "suppliers",
                               "length(btrim(carrier))>0 AND carrier=btrim(carrier)")
    connection.execute(sa.text("""
        INSERT INTO suppliers(carrier)
        SELECT DISTINCT w.carrier FROM warehouses w
        WHERE NOT EXISTS (SELECT 1 FROM suppliers s WHERE s.carrier=w.carrier)
    """))
    op.create_foreign_key("fk_warehouse_carrier", "warehouses", "suppliers",
                          ["carrier"], ["carrier"], ondelete="RESTRICT")
    op.execute("""
        CREATE FUNCTION check_supplier_carrier() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE item_carrier text; supplier_carrier text;
        BEGIN
            IF TG_TABLE_NAME='supplier_item_policies' THEN
                SELECT w.carrier, s.carrier INTO item_carrier, supplier_carrier
                FROM items i JOIN warehouses w ON w.id=i.warehouse_id
                CROSS JOIN suppliers s WHERE i.id=NEW.item_id AND s.id=NEW.supplier_id
                FOR SHARE OF i,w,s;
                IF item_carrier IS DISTINCT FROM supplier_carrier THEN
                    RAISE EXCEPTION 'Supplier must be the item carrier'
                        USING ERRCODE='23514', CONSTRAINT='ck_policy_supplier_carrier';
                END IF;
            ELSIF TG_TABLE_NAME='items' THEN
                SELECT carrier INTO item_carrier FROM warehouses WHERE id=NEW.warehouse_id FOR SHARE;
                IF EXISTS (SELECT 1 FROM supplier_item_policies p JOIN suppliers s ON s.id=p.supplier_id
                           WHERE p.item_id=NEW.id AND s.carrier IS DISTINCT FROM item_carrier) THEN
                    RAISE EXCEPTION 'Item move conflicts with supplier carrier' USING ERRCODE='23514';
                END IF;
            ELSE
                IF EXISTS (SELECT 1 FROM items i JOIN supplier_item_policies p ON p.item_id=i.id
                           JOIN suppliers s ON s.id=p.supplier_id
                           WHERE i.warehouse_id=NEW.id AND s.carrier IS DISTINCT FROM NEW.carrier) THEN
                    RAISE EXCEPTION 'Warehouse carrier conflicts with supplier' USING ERRCODE='23514';
                END IF;
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("CREATE TRIGGER policy_supplier_carrier BEFORE INSERT OR UPDATE OF item_id,supplier_id ON supplier_item_policies FOR EACH ROW EXECUTE FUNCTION check_supplier_carrier()")
    op.execute("CREATE TRIGGER item_supplier_carrier BEFORE UPDATE OF warehouse_id ON items FOR EACH ROW EXECUTE FUNCTION check_supplier_carrier()")
    op.execute("CREATE TRIGGER warehouse_supplier_carrier BEFORE UPDATE OF carrier ON warehouses FOR EACH ROW EXECUTE FUNCTION check_supplier_carrier()")


def downgrade():
    for table, trigger in (("supplier_item_policies", "policy_supplier_carrier"),
                           ("items", "item_supplier_carrier"), ("warehouses", "warehouse_supplier_carrier")):
        op.execute(f"DROP TRIGGER {trigger} ON {table}")
    op.execute("DROP FUNCTION check_supplier_carrier()")
    op.drop_constraint("fk_warehouse_carrier", "warehouses", type_="foreignkey")
    op.drop_constraint("ck_supplier_carrier", "suppliers", type_="check")
    op.drop_constraint("uq_suppliers_carrier", "suppliers", type_="unique")
    op.alter_column("suppliers", "carrier", new_column_name="code")
    op.create_unique_constraint("suppliers_code_key", "suppliers", ["code"])
    op.add_column("suppliers", sa.Column("display_name", sa.Text()))
    op.add_column("suppliers", sa.Column("is_assumed", sa.Boolean()))
    op.add_column("suppliers", sa.Column("assumption_source", sa.Text()))
    # Restore the old shape only. The pre-migration backup retains old labels.
    op.execute("UPDATE suppliers SET display_name=code, is_assumed=true, assumption_source='carrier_schema_downgrade'")
    for column, kind in (("display_name", sa.Text()), ("is_assumed", sa.Boolean()), ("assumption_source", sa.Text())):
        op.alter_column("suppliers", column, existing_type=kind, nullable=False)
