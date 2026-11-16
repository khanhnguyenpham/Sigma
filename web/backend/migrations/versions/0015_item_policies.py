"""Name configuration tables by what they hold: item_policies (per product) and supplier_settings (per supplier).

The policy supplier is always the item's carrier (CHG-079), so the stored supplier_id column is redundant and is
derived instead. Items and warehouses that already have policies still cannot change carrier.
"""
from alembic import op

revision = "0015_item_policies"
down_revision = "0014_supplier_lead_simulation"
branch_labels = None
depends_on = None

POLICY_RENAMES = [
    ("supplier_item_policies_pkey", "item_policies_pkey"),
    ("supplier_item_policies_item_id_version_key", "item_policies_item_id_version_key"),
    ("supplier_item_policies_item_id_effective_from_key", "item_policies_item_id_effective_from_key"),
    ("supplier_item_policies_id_item_id_key", "item_policies_id_item_id_key"),
    ("supplier_item_policies_check", "item_policies_check"),
    ("supplier_item_policies_check1", "item_policies_check1"),
    ("supplier_item_policies_item_id_fkey", "item_policies_item_id_fkey"),
]
SETTINGS_RENAMES = [
    ("ops_supplier_settings_pkey", "supplier_settings_pkey"),
    ("ops_supplier_settings_supplier_id_fkey", "supplier_settings_supplier_id_fkey"),
    ("ops_supplier_settings_updated_by_fkey", "supplier_settings_updated_by_fkey"),
    ("ck_ops_supplier_settings", "ck_supplier_settings"),
]

STABLE_CARRIER = """
CREATE FUNCTION check_policy_carrier_stable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME='items' THEN
        IF (SELECT carrier FROM warehouses WHERE id=NEW.warehouse_id) IS DISTINCT FROM
           (SELECT carrier FROM warehouses WHERE id=OLD.warehouse_id)
           AND EXISTS (SELECT 1 FROM item_policies WHERE item_id=NEW.id) THEN
            RAISE EXCEPTION 'Item move conflicts with supplier carrier' USING ERRCODE='23514';
        END IF;
    ELSIF NEW.carrier IS DISTINCT FROM OLD.carrier AND EXISTS (
        SELECT 1 FROM items i JOIN item_policies p ON p.item_id=i.id WHERE i.warehouse_id=NEW.id) THEN
        RAISE EXCEPTION 'Warehouse carrier conflicts with supplier' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$
"""

# Exact 0005 definition, restored on downgrade.
LEGACY_CARRIER = """
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
"""


def rename(table, pairs):
    for old, new in pairs:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}")


def upgrade():
    op.execute("DROP TRIGGER policy_supplier_carrier ON supplier_item_policies")
    op.execute("DROP TRIGGER item_supplier_carrier ON items")
    op.execute("DROP TRIGGER warehouse_supplier_carrier ON warehouses")
    op.execute("DROP FUNCTION check_supplier_carrier()")
    op.execute("ALTER TABLE supplier_item_policies DROP COLUMN supplier_id")
    op.execute("ALTER TABLE supplier_item_policies RENAME TO item_policies")
    rename("item_policies", POLICY_RENAMES)
    op.execute(STABLE_CARRIER)
    op.execute("CREATE TRIGGER item_policy_carrier BEFORE UPDATE OF warehouse_id ON items FOR EACH ROW EXECUTE FUNCTION check_policy_carrier_stable()")
    op.execute("CREATE TRIGGER warehouse_policy_carrier BEFORE UPDATE OF carrier ON warehouses FOR EACH ROW EXECUTE FUNCTION check_policy_carrier_stable()")
    op.execute("ALTER TABLE ops_supplier_settings RENAME TO supplier_settings")
    rename("supplier_settings", SETTINGS_RENAMES)


def downgrade():
    op.execute("ALTER TABLE supplier_settings RENAME TO ops_supplier_settings")
    rename("ops_supplier_settings", [(new, old) for old, new in SETTINGS_RENAMES])
    op.execute("DROP TRIGGER item_policy_carrier ON items")
    op.execute("DROP TRIGGER warehouse_policy_carrier ON warehouses")
    op.execute("DROP FUNCTION check_policy_carrier_stable()")
    rename("item_policies", [(new, old) for old, new in POLICY_RENAMES])
    op.execute("ALTER TABLE item_policies RENAME TO supplier_item_policies")
    # Lossless: the supplier is the carrier of the item's source warehouse.
    op.execute("ALTER TABLE supplier_item_policies ADD COLUMN supplier_id BIGINT")
    op.execute("""UPDATE supplier_item_policies p SET supplier_id=s.id FROM items i
        JOIN warehouses w ON w.id=i.warehouse_id JOIN suppliers s ON s.carrier=w.carrier WHERE i.id=p.item_id""")
    op.execute("ALTER TABLE supplier_item_policies ALTER COLUMN supplier_id SET NOT NULL")
    op.execute("ALTER TABLE supplier_item_policies ADD CONSTRAINT supplier_item_policies_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES suppliers (id) ON DELETE RESTRICT")
    op.execute(LEGACY_CARRIER)
    op.execute("CREATE TRIGGER policy_supplier_carrier BEFORE INSERT OR UPDATE OF item_id,supplier_id ON supplier_item_policies FOR EACH ROW EXECUTE FUNCTION check_supplier_carrier()")
    op.execute("CREATE TRIGGER item_supplier_carrier BEFORE UPDATE OF warehouse_id ON items FOR EACH ROW EXECUTE FUNCTION check_supplier_carrier()")
    op.execute("CREATE TRIGGER warehouse_supplier_carrier BEFORE UPDATE OF carrier ON warehouses FOR EACH ROW EXECUTE FUNCTION check_supplier_carrier()")
