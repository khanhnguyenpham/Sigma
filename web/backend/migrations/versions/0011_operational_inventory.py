"""Operational purchase orders and posted stock ledger; legacy runs are untouched."""
from alembic import op
import sqlalchemy as sa

revision = "0011_operational_inventory"
down_revision = "0010_auth_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE ops_audit_events (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	entity_type TEXT NOT NULL,
	entity_key TEXT NOT NULL,
	action TEXT NOT NULL,
	actor_id BIGINT NOT NULL,
	details JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(actor_id) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_ops_audit_entity ON ops_audit_events (entity_type, entity_key, id)""")
    op.execute("""CREATE TABLE ops_purchase_orders (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	number TEXT NOT NULL,
	supplier_id BIGINT NOT NULL,
	ordered_on DATE NOT NULL,
	eta DATE NOT NULL,
	lead_time_days INTEGER NOT NULL,
	supplier_settings_version INTEGER NOT NULL,
	status TEXT NOT NULL,
	version INTEGER DEFAULT 1 NOT NULL,
	note TEXT DEFAULT '' NOT NULL,
	request_key TEXT NOT NULL,
	request_digest TEXT NOT NULL,
	created_by BIGINT NOT NULL,
	confirmed_by BIGINT,
	confirmed_at TIMESTAMP WITH TIME ZONE,
	cancelled_by BIGINT,
	cancelled_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_ops_order_dates CHECK (lead_time_days BETWEEN 1 AND 365 AND eta=ordered_on+lead_time_days AND supplier_settings_version>=0 AND version>=1),
	CONSTRAINT ck_ops_order_status CHECK (status IN ('draft','ordered','partially_received','received','cancelled')),
	CONSTRAINT ck_ops_order_actors CHECK ((confirmed_by IS NULL)=(confirmed_at IS NULL) AND (cancelled_by IS NULL)=(cancelled_at IS NULL)),
	UNIQUE (number),
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id) ON DELETE RESTRICT,
	UNIQUE (request_key),
	FOREIGN KEY(created_by) REFERENCES auth_users (id) ON DELETE RESTRICT,
	FOREIGN KEY(confirmed_by) REFERENCES auth_users (id) ON DELETE RESTRICT,
	FOREIGN KEY(cancelled_by) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_ops_order_supplier_status ON ops_purchase_orders (supplier_id, status, id)""")
    op.execute("""CREATE TABLE ops_supplier_settings (
	supplier_id BIGINT NOT NULL,
	lead_time_days INTEGER NOT NULL,
	version INTEGER NOT NULL,
	updated_by BIGINT NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (supplier_id),
	CONSTRAINT ck_ops_supplier_settings CHECK (lead_time_days BETWEEN 1 AND 365 AND version>=1),
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id) ON DELETE RESTRICT,
	FOREIGN KEY(updated_by) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE ops_warehouses (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	code TEXT NOT NULL,
	name TEXT NOT NULL,
	country TEXT NOT NULL,
	active BOOLEAN DEFAULT true NOT NULL,
	version INTEGER DEFAULT 1 NOT NULL,
	created_by BIGINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_ops_warehouse CHECK (length(btrim(code)) BETWEEN 1 AND 40 AND length(btrim(name)) BETWEEN 1 AND 120 AND length(btrim(country)) BETWEEN 1 AND 100 AND version>=1),
	UNIQUE (code),
	FOREIGN KEY(created_by) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE ops_products (
	item_id BIGINT NOT NULL,
	name TEXT NOT NULL,
	active BOOLEAN DEFAULT true NOT NULL,
	version INTEGER DEFAULT 1 NOT NULL,
	created_by BIGINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (item_id),
	CONSTRAINT ck_ops_product CHECK (length(btrim(name)) BETWEEN 1 AND 160 AND version>=1),
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT,
	FOREIGN KEY(created_by) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE ops_purchase_order_lines (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	order_id BIGINT NOT NULL,
	item_id BIGINT NOT NULL,
	warehouse_id BIGINT NOT NULL,
	ordered_qty BIGINT NOT NULL,
	received_qty BIGINT DEFAULT 0 NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_ops_order_product_location UNIQUE (order_id, item_id, warehouse_id),
	CONSTRAINT uq_ops_line_identity UNIQUE (id, order_id, item_id, warehouse_id),
	CONSTRAINT ck_ops_line_quantity CHECK (ordered_qty>0 AND received_qty BETWEEN 0 AND ordered_qty),
	FOREIGN KEY(order_id) REFERENCES ops_purchase_orders (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT,
	FOREIGN KEY(warehouse_id) REFERENCES ops_warehouses (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_ops_line_order ON ops_purchase_order_lines (order_id)""")
    op.execute("""CREATE TABLE ops_stock_balances (
	warehouse_id BIGINT NOT NULL,
	item_id BIGINT NOT NULL,
	on_hand_qty BIGINT DEFAULT 0 NOT NULL,
	version INTEGER DEFAULT 0 NOT NULL,
	last_movement_on DATE,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (warehouse_id, item_id),
	CONSTRAINT ck_ops_balance CHECK (on_hand_qty>=0 AND version>=0),
	FOREIGN KEY(warehouse_id) REFERENCES ops_warehouses (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE ops_stock_documents (
	id UUID NOT NULL,
	number TEXT NOT NULL,
	kind TEXT NOT NULL,
	order_id BIGINT,
	occurred_on DATE NOT NULL,
	external_ref TEXT NOT NULL,
	reason TEXT NOT NULL,
	request_key TEXT NOT NULL,
	request_digest TEXT NOT NULL,
	created_by BIGINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_ops_document_kind UNIQUE (id, kind),
	CONSTRAINT uq_ops_document_order UNIQUE (id, order_id),
	CONSTRAINT uq_ops_order_delivery_ref UNIQUE (order_id, external_ref),
	CONSTRAINT ck_ops_document_kind CHECK ((kind='receipt' AND order_id IS NOT NULL) OR (kind IN ('issue','adjustment') AND order_id IS NULL)),
	CONSTRAINT ck_ops_document_text CHECK (length(btrim(external_ref)) BETWEEN 1 AND 120 AND length(reason)<=1000 AND length(request_key) BETWEEN 1 AND 128),
	UNIQUE (number),
	FOREIGN KEY(order_id) REFERENCES ops_purchase_orders (id) ON DELETE RESTRICT,
	UNIQUE (request_key),
	FOREIGN KEY(created_by) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_ops_document_date ON ops_stock_documents (occurred_on, created_at)""")
    op.execute("""CREATE TABLE ops_stock_document_lines (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	document_id UUID NOT NULL,
	kind TEXT NOT NULL,
	order_id BIGINT,
	order_line_id BIGINT,
	item_id BIGINT NOT NULL,
	warehouse_id BIGINT NOT NULL,
	quantity_delta BIGINT NOT NULL,
	balance_after BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_ops_line_document_kind FOREIGN KEY(document_id, kind) REFERENCES ops_stock_documents (id, kind) ON DELETE RESTRICT,
	CONSTRAINT fk_ops_line_document_order FOREIGN KEY(document_id, order_id) REFERENCES ops_stock_documents (id, order_id) ON DELETE RESTRICT,
	CONSTRAINT fk_ops_receipt_line_order FOREIGN KEY(order_line_id, order_id, item_id, warehouse_id) REFERENCES ops_purchase_order_lines (id, order_id, item_id, warehouse_id) ON DELETE RESTRICT,
	CONSTRAINT uq_ops_document_product_location UNIQUE (document_id, item_id, warehouse_id),
	CONSTRAINT ck_ops_posted_line CHECK (balance_after>=0 AND ((kind='receipt' AND quantity_delta>0 AND order_id IS NOT NULL AND order_line_id IS NOT NULL) OR (kind='issue' AND quantity_delta<0 AND order_id IS NULL AND order_line_id IS NULL) OR (kind='adjustment' AND order_id IS NULL AND order_line_id IS NULL))),
	FOREIGN KEY(document_id) REFERENCES ops_stock_documents (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT,
	FOREIGN KEY(warehouse_id) REFERENCES ops_warehouses (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_ops_ledger_product_location ON ops_stock_document_lines (warehouse_id, item_id, id)""")
    op.execute("""CREATE FUNCTION ops_reject_posted_change_v1() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Posted operational documents and audit are immutable'; END; $$""")
    op.execute("CREATE TRIGGER ops_stock_documents_immutable BEFORE UPDATE OR DELETE ON ops_stock_documents FOR EACH ROW EXECUTE FUNCTION ops_reject_posted_change_v1()")
    op.execute("CREATE TRIGGER ops_stock_document_lines_immutable BEFORE UPDATE OR DELETE ON ops_stock_document_lines FOR EACH ROW EXECUTE FUNCTION ops_reject_posted_change_v1()")
    op.execute("CREATE TRIGGER ops_audit_events_immutable BEFORE UPDATE OR DELETE ON ops_audit_events FOR EACH ROW EXECUTE FUNCTION ops_reject_posted_change_v1()")


def downgrade():
    op.execute("LOCK TABLE ops_audit_events, ops_purchase_orders, ops_supplier_settings, ops_warehouses, ops_products, ops_purchase_order_lines, ops_stock_balances, ops_stock_documents, ops_stock_document_lines IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM ops_audit_events) OR EXISTS(SELECT 1 FROM ops_purchase_orders) OR EXISTS(SELECT 1 FROM ops_supplier_settings) OR EXISTS(SELECT 1 FROM ops_warehouses) OR EXISTS(SELECT 1 FROM ops_products) OR EXISTS(SELECT 1 FROM ops_purchase_order_lines) OR EXISTS(SELECT 1 FROM ops_stock_balances) OR EXISTS(SELECT 1 FROM ops_stock_documents) OR EXISTS(SELECT 1 FROM ops_stock_document_lines)")):
        raise RuntimeError("Operational data exists; downgrade would lose data")
    op.drop_table("ops_stock_document_lines")
    op.drop_table("ops_stock_documents")
    op.drop_table("ops_stock_balances")
    op.drop_table("ops_purchase_order_lines")
    op.drop_table("ops_products")
    op.drop_table("ops_warehouses")
    op.drop_table("ops_supplier_settings")
    op.drop_table("ops_purchase_orders")
    op.drop_table("ops_audit_events")
    op.execute("DROP FUNCTION ops_reject_posted_change_v1()")
