"""Simulated lots may arrive after the frozen supplier lead time (1..13 days) instead of a fixed D+7."""
from alembic import op
import sqlalchemy as sa

revision = "0014_supplier_lead_simulation"
down_revision = "0013_adjustable_eta"
branch_labels = None
depends_on = None

STATUS = "((status='ordered' AND received_qty=0) OR (status='received' AND received_qty=ordered_qty))"


def upgrade():
    op.execute("ALTER TABLE replenishment_orders DROP CONSTRAINT replenishment_orders_check")
    op.execute(f"ALTER TABLE replenishment_orders ADD CONSTRAINT replenishment_orders_check CHECK (ordered_qty>0 AND eta>ordered_on AND eta<=ordered_on+13 AND {STATUS})")


def downgrade():
    op.execute("LOCK TABLE replenishment_orders IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM replenishment_orders WHERE eta<>ordered_on+7)")):
        raise RuntimeError("Simulated lots with a non-7-day lead time exist; downgrade would lose data")
    op.execute("ALTER TABLE replenishment_orders DROP CONSTRAINT replenishment_orders_check")
    op.execute(f"ALTER TABLE replenishment_orders ADD CONSTRAINT replenishment_orders_check CHECK (ordered_qty>0 AND eta=ordered_on+7 AND {STATUS})")
