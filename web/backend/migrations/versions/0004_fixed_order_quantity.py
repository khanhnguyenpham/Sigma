"""Add the configured quantity per order; do not reinterpret historical MOQ."""
from alembic import op
import sqlalchemy as sa

revision = "0004_fixed_qty"
down_revision = "0003_threshold"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("supplier_item_policies", sa.Column("fixed_order_qty", sa.BigInteger()))
    op.alter_column("supplier_item_policies", "moq", existing_type=sa.BigInteger(), nullable=True)
    op.create_check_constraint(
        "ck_policy_order_quantity", "supplier_item_policies",
        "(fixed_order_qty IS NULL AND moq IS NOT NULL) OR "
        "(fixed_order_qty IS NOT NULL AND fixed_order_qty>=1 AND moq IS NULL)",
    )


def downgrade():
    # NOT NULL deliberately fails if fixed-quantity rows exist; never convert
    # their quantity to MOQ or delete them merely to permit a downgrade.
    op.alter_column("supplier_item_policies", "moq", existing_type=sa.BigInteger(), nullable=False)
    op.drop_constraint("ck_policy_order_quantity", "supplier_item_policies", type_="check")
    op.drop_column("supplier_item_policies", "fixed_order_qty")
