"""Add simulated item supply history without changing existing business rows."""
from alembic import op
import sqlalchemy as sa

revision = "0007_supply_lifecycle"
down_revision = "0006_fixed_days"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_supply_changes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey("items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("known_on", sa.Date(), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("target_change_id", sa.BigInteger()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("is_assumed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("assumption_source", sa.Text(), nullable=False, server_default="user_declared_supply_simulation_v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("item_id", "version", name="uq_supply_item_version"),
        sa.UniqueConstraint("id", "item_id", name="uq_supply_id_item"),
        sa.ForeignKeyConstraint(["target_change_id", "item_id"], ["item_supply_changes.id", "item_supply_changes.item_id"],
                                name="fk_supply_target_item", ondelete="RESTRICT"),
        sa.CheckConstraint("version >= 1", name="ck_supply_version"),
        sa.CheckConstraint("(action='stop' AND target_change_id IS NULL AND effective_on>=known_on+7) OR "
                           "(action IN ('cancel_stop','resume') AND target_change_id IS NOT NULL AND effective_on=known_on)",
                           name="ck_supply_action_dates"),
        sa.CheckConstraint("length(reason) BETWEEN 1 AND 1000 AND reason ~ '[^[:space:]]'", name="ck_supply_reason"),
        sa.CheckConstraint("is_assumed AND assumption_source='user_declared_supply_simulation_v1'", name="ck_supply_provenance"),
    )
    op.create_index("ix_supply_item_known_version", "item_supply_changes", ["item_id", "known_on", "version"])


def downgrade():
    # Serialize with inserts: never drop history that arrives during this check.
    op.execute("LOCK TABLE item_supply_changes IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM item_supply_changes)")):
        raise RuntimeError("Supply history exists; downgrade would lose data")
    op.drop_table("item_supply_changes")
