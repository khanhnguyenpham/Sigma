"""Persist inventory policy parameters without rewriting frozen run/scenario JSON.

Revision ID: 0002_policy
Revises: 0001_m3
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_policy"
down_revision = "0001_m3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("supplier_item_policies", sa.Column("safety_mode", sa.Text(), nullable=False, server_default="days"))
    op.add_column("supplier_item_policies", sa.Column("safety_lookback_days", sa.SmallInteger(), nullable=False, server_default="28"))
    op.add_column("supplier_item_policies", sa.Column("safety_factor", sa.Double(), nullable=False, server_default="1"))
    op.add_column("supplier_item_policies", sa.Column("rop_mode", sa.Text(), nullable=False, server_default="forecast"))
    op.add_column("supplier_item_policies", sa.Column("warning_horizon_days", sa.SmallInteger(), nullable=False, server_default="7"))
    op.create_check_constraint("ck_policy_safety_mode", "supplier_item_policies", "safety_mode IN ('days','volatility')")
    op.create_check_constraint("ck_policy_safety_lookback", "supplier_item_policies", "safety_lookback_days BETWEEN 7 AND 90")
    op.create_check_constraint("ck_policy_safety_factor", "supplier_item_policies", "safety_factor>=0 AND safety_factor<'Infinity'::float8")
    op.create_check_constraint("ck_policy_rop_mode", "supplier_item_policies", "rop_mode IN ('fixed','forecast')")
    op.create_check_constraint("ck_policy_warning_horizon", "supplier_item_policies", "warning_horizon_days BETWEEN 1 AND 14")


def downgrade():
    for name in ("ck_policy_warning_horizon", "ck_policy_rop_mode", "ck_policy_safety_factor", "ck_policy_safety_lookback", "ck_policy_safety_mode"):
        op.drop_constraint(name, "supplier_item_policies", type_="check")
    for name in ("warning_horizon_days", "rop_mode", "safety_factor", "safety_lookback_days", "safety_mode"):
        op.drop_column("supplier_item_policies", name)
