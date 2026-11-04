"""Store the product default separately from its immutable source route."""
from alembic import op
import sqlalchemy as sa

revision = "0009_receiving_warehouse"
down_revision = "0008_trade_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("items", sa.Column("receiving_warehouse_id", sa.BigInteger(), nullable=True))
    op.add_column("items", sa.Column("receiving_version", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.create_foreign_key("fk_item_receiving_warehouse", "items", "warehouses",
                          ["receiving_warehouse_id"], ["id"], ondelete="RESTRICT")
    op.create_check_constraint("ck_item_receiving_version", "items",
        "(receiving_warehouse_id IS NULL AND receiving_version=0) OR "
        "(receiving_warehouse_id IS NOT NULL AND receiving_version>=1)")
    op.add_column("replenishment_orders", sa.Column("receiving_warehouse_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_order_receiving_warehouse", "replenishment_orders", "warehouses",
                          ["receiving_warehouse_id"], ["id"], ondelete="RESTRICT")


def downgrade():
    op.execute("LOCK TABLE items, replenishment_orders, runs IN ACCESS EXCLUSIVE MODE")
    unsafe = op.get_bind().scalar(sa.text("""
        SELECT EXISTS(SELECT 1 FROM items WHERE receiving_version<>0 OR receiving_warehouse_id IS NOT NULL)
            OR EXISTS(SELECT 1 FROM replenishment_orders WHERE receiving_warehouse_id IS NOT NULL)
            OR EXISTS(SELECT 1 FROM runs WHERE config_snapshot ? 'receiving_warehouse_profile'
                                           OR config_snapshot ? 'receiving_warehouse_snapshot')
    """))
    if unsafe:
        raise RuntimeError("Receiving warehouse data exists; downgrade would lose data")
    op.drop_constraint("fk_order_receiving_warehouse", "replenishment_orders", type_="foreignkey")
    op.drop_column("replenishment_orders", "receiving_warehouse_id")
    op.drop_constraint("ck_item_receiving_version", "items", type_="check")
    op.drop_constraint("fk_item_receiving_warehouse", "items", type_="foreignkey")
    op.drop_column("items", "receiving_version")
    op.drop_column("items", "receiving_warehouse_id")
