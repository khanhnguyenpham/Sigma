"""Dealers, dealer stock requests and the dealer login role; supplier logins are retired."""
from alembic import op
import sqlalchemy as sa

revision = "0012_dealers"
down_revision = "0011_operational_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE dealers (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	code TEXT NOT NULL,
	name TEXT NOT NULL,
	contact TEXT DEFAULT '' NOT NULL,
	active BOOLEAN DEFAULT true NOT NULL,
	version INTEGER DEFAULT 1 NOT NULL,
	created_by BIGINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_dealer CHECK (length(btrim(code)) BETWEEN 1 AND 40 AND length(btrim(name)) BETWEEN 1 AND 120 AND length(contact)<=200 AND version>=1),
	UNIQUE (code),
	FOREIGN KEY(created_by) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE dealer_requests (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	number TEXT NOT NULL,
	dealer_id BIGINT NOT NULL,
	status TEXT NOT NULL,
	note TEXT DEFAULT '' NOT NULL,
	reject_reason TEXT,
	warehouse_id BIGINT,
	document_id UUID,
	version INTEGER DEFAULT 1 NOT NULL,
	request_key TEXT NOT NULL,
	request_digest TEXT NOT NULL,
	created_by BIGINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	decided_by BIGINT,
	decided_at TIMESTAMP WITH TIME ZONE,
	received_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT ck_dealer_request_status CHECK (status IN ('submitted','approved','rejected','cancelled','issued','received')),
	CONSTRAINT ck_dealer_request_state CHECK ((status='rejected')=(reject_reason IS NOT NULL) AND (status IN ('issued','received'))=(document_id IS NOT NULL AND warehouse_id IS NOT NULL) AND (status='received')=(received_at IS NOT NULL) AND (decided_by IS NULL)=(decided_at IS NULL) AND length(note)<=1000 AND version>=1),
	UNIQUE (number),
	FOREIGN KEY(dealer_id) REFERENCES dealers (id) ON DELETE RESTRICT,
	FOREIGN KEY(warehouse_id) REFERENCES ops_warehouses (id) ON DELETE RESTRICT,
	FOREIGN KEY(document_id) REFERENCES ops_stock_documents (id) ON DELETE RESTRICT,
	UNIQUE (request_key),
	FOREIGN KEY(created_by) REFERENCES auth_users (id) ON DELETE RESTRICT,
	FOREIGN KEY(decided_by) REFERENCES auth_users (id) ON DELETE RESTRICT
)""")
    op.execute("CREATE INDEX ix_dealer_request_dealer_status ON dealer_requests (dealer_id, status, id)")
    op.execute("""CREATE TABLE dealer_request_lines (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	request_id BIGINT NOT NULL,
	item_id BIGINT NOT NULL,
	quantity BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_dealer_request_item UNIQUE (request_id, item_id),
	CONSTRAINT ck_dealer_request_quantity CHECK (quantity>0),
	FOREIGN KEY(request_id) REFERENCES dealer_requests (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT
)""")
    op.execute("CREATE INDEX ix_dealer_request_line_request ON dealer_request_lines (request_id)")
    op.execute("ALTER TABLE auth_users ADD COLUMN dealer_id BIGINT REFERENCES dealers (id) ON DELETE RESTRICT")
    # Retire supplier logins: keep rows for audit history, revoke any open session first.
    op.execute("UPDATE auth_sessions SET revoked_at=now() WHERE revoked_at IS NULL AND user_id IN (SELECT id FROM auth_users WHERE role='supplier')")
    op.execute("UPDATE auth_users SET active=false WHERE role='supplier'")
    op.execute("ALTER TABLE auth_users DROP CONSTRAINT ck_auth_scope")
    op.execute("""ALTER TABLE auth_users ADD CONSTRAINT ck_auth_scope CHECK ((role='admin' AND supplier_id IS NULL AND dealer_id IS NULL) OR (role='supplier' AND supplier_id IS NOT NULL AND dealer_id IS NULL AND NOT active) OR (role='dealer' AND dealer_id IS NOT NULL AND supplier_id IS NULL))""")


def downgrade():
    op.execute("LOCK TABLE dealers, dealer_requests, dealer_request_lines, auth_users IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM dealers) OR EXISTS(SELECT 1 FROM auth_users WHERE role='dealer')")):
        raise RuntimeError("Dealer data exists; downgrade would lose data")
    op.execute("ALTER TABLE auth_users DROP CONSTRAINT ck_auth_scope")
    op.execute("ALTER TABLE auth_users ADD CONSTRAINT ck_auth_scope CHECK ((role='admin' AND supplier_id IS NULL) OR (role='supplier' AND supplier_id IS NOT NULL))")
    op.execute("ALTER TABLE auth_users DROP COLUMN dealer_id")
    op.drop_table("dealer_request_lines")
    op.drop_table("dealer_requests")
    op.drop_table("dealers")
