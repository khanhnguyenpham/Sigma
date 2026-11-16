"""Allow confirmed purchase orders to move their ETA after a supply incident.

The planned ETA stays derivable as ordered_on + lead_time_days; the current one only has to be on or after ordering.
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_adjustable_eta"
down_revision = "0012_dealers"
branch_labels = None
depends_on = None

OLD = "lead_time_days BETWEEN 1 AND 365 AND eta=ordered_on+lead_time_days AND supplier_settings_version>=0 AND version>=1"
NEW = "lead_time_days BETWEEN 1 AND 365 AND eta>=ordered_on AND supplier_settings_version>=0 AND version>=1"


def upgrade():
    op.execute("ALTER TABLE ops_purchase_orders DROP CONSTRAINT ck_ops_order_dates")
    op.execute(f"ALTER TABLE ops_purchase_orders ADD CONSTRAINT ck_ops_order_dates CHECK ({NEW})")


def downgrade():
    op.execute("LOCK TABLE ops_purchase_orders IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM ops_purchase_orders WHERE eta<>ordered_on+lead_time_days)")):
        raise RuntimeError("Adjusted ETA data exists; downgrade would lose data")
    op.execute("ALTER TABLE ops_purchase_orders DROP CONSTRAINT ck_ops_order_dates")
    op.execute(f"ALTER TABLE ops_purchase_orders ADD CONSTRAINT ck_ops_order_dates CHECK ({OLD})")
