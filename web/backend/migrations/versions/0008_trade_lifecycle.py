"""Separate internal replenishment decisions from provider trade restrictions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_trade_lifecycle"
down_revision = "0007_supply_lifecycle"
branch_labels = None
depends_on = None

INTERNAL_DATES = ("(action='stop' AND target_change_id IS NULL AND effective_on>=known_on) OR "
                  "(action IN ('cancel_stop','resume') AND target_change_id IS NOT NULL AND effective_on=known_on)")
LEGACY_EVENT = ("(event_kind='sale' AND quantity=fulfilled_qty+shortage_qty AND source_sequence IS NOT NULL AND replenishment_order_id IS NULL) OR "
                "(event_kind='receipt' AND fulfilled_qty=0 AND shortage_qty=0 AND replenishment_order_id IS NOT NULL) OR "
                "(event_kind='initial_stock' AND fulfilled_qty=0 AND shortage_qty=0 AND replenishment_order_id IS NULL)")
BLOCKED_EVENT = ("(event_kind='sale_blocked' AND source_sequence IS NOT NULL AND replenishment_order_id IS NULL "
                 "AND fulfilled_qty=0 AND shortage_qty=0)")


def upgrade():
    op.drop_constraint("ck_supply_action_dates", "item_supply_changes", type_="check")
    op.create_check_constraint("ck_supply_action_dates", "item_supply_changes", INTERNAL_DATES)
    op.create_table(
        "provider_product_notices",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("supplier_id", sa.BigInteger(), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scope_definition", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("jsonb_typeof(scope_definition)='object' AND scope_definition <> '{}'::jsonb",
                           name="ck_provider_notice_scope"),
    )
    op.create_table(
        "provider_product_notice_items",
        sa.Column("notice_id", sa.BigInteger(), sa.ForeignKey("provider_product_notices.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_index("ix_provider_item_notice", "provider_product_notice_items", ["item_id", "notice_id"])
    op.create_table(
        "provider_product_notice_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("notice_id", sa.BigInteger(), sa.ForeignKey("provider_product_notices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_event_id", sa.BigInteger()),
        sa.Column("known_on", sa.Date(), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text()),
        sa.Column("is_assumed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("notice_id", "version", name="uq_provider_notice_version"),
        sa.UniqueConstraint("id", "notice_id", name="uq_provider_event_notice"),
        sa.ForeignKeyConstraint(["target_event_id", "notice_id"],
                                ["provider_product_notice_events.id", "provider_product_notice_events.notice_id"],
                                name="fk_provider_target_notice", ondelete="RESTRICT"),
        sa.CheckConstraint("(version=1 AND action='stop' AND target_event_id IS NULL) OR "
                           "(version=2 AND action IN ('cancel_stop','resume_supply') AND target_event_id IS NOT NULL "
                           "AND target_event_id<>id)", name="ck_provider_event_action"),
        sa.CheckConstraint("action='stop' OR (action='cancel_stop' AND effective_on=known_on) OR "
                           "(action='resume_supply' AND effective_on>=known_on)", name="ck_provider_event_dates"),
        sa.CheckConstraint("length(reason) BETWEEN 1 AND 1000 AND reason ~ '[^[:space:]]'", name="ck_provider_event_reason"),
        sa.CheckConstraint("length(source_description) BETWEEN 1 AND 1000 AND source_description ~ '[^[:space:]]'",
                           name="ck_provider_event_source"),
        sa.CheckConstraint("source_ref IS NULL OR (length(source_ref)<=2048 AND source_ref ~ '^https?://[^[:space:]]+$')",
                           name="ck_provider_event_ref"),
        sa.CheckConstraint("is_assumed", name="ck_provider_event_assumed"),
    )
    op.create_index("ix_provider_notice_known", "provider_product_notice_events", ["notice_id", "known_on", "version"])
    op.add_column("inventory_daily", sa.Column("source_sales_qty", sa.BigInteger(), nullable=True))
    op.add_column("inventory_daily", sa.Column("actual_blocked_qty", sa.BigInteger(), nullable=True))
    op.create_check_constraint("ck_inventory_source_sales", "inventory_daily",
        "(source_sales_qty IS NULL AND actual_blocked_qty IS NULL) OR "
        "(source_sales_qty IS NOT NULL AND actual_blocked_qty IS NOT NULL AND "
        "source_sales_qty>=0 AND actual_blocked_qty>=0 AND source_sales_qty=sales_qty+actual_blocked_qty)")
    checks = [c["name"] for c in sa.inspect(op.get_bind()).get_check_constraints("inventory_events")
              if "event_kind" in c["sqltext"]]
    if len(checks) != 1:
        raise RuntimeError("Unexpected inventory event constraints; inspect before migrating")
    op.drop_constraint(checks[0], "inventory_events", type_="check")
    op.create_check_constraint("ck_inventory_event_kind", "inventory_events", LEGACY_EVENT + " OR " + BLOCKED_EVENT)


def downgrade():
    # Serialize the check with all writes that could make this downgrade lossy.
    op.execute("LOCK TABLE provider_product_notices, provider_product_notice_items, provider_product_notice_events, "
               "item_supply_changes, inventory_daily, inventory_events, runs IN ACCESS EXCLUSIVE MODE")
    unsafe = op.get_bind().scalar(sa.text("""
        SELECT EXISTS(SELECT 1 FROM provider_product_notices)
            OR EXISTS(SELECT 1 FROM provider_product_notice_items)
            OR EXISTS(SELECT 1 FROM provider_product_notice_events)
            OR EXISTS(SELECT 1 FROM item_supply_changes WHERE action='stop' AND effective_on<known_on+7)
            OR EXISTS(SELECT 1 FROM inventory_daily WHERE source_sales_qty IS NOT NULL OR actual_blocked_qty IS NOT NULL)
            OR EXISTS(SELECT 1 FROM inventory_events WHERE event_kind='sale_blocked')
            OR EXISTS(SELECT 1 FROM runs WHERE config_snapshot ? 'trade_lifecycle_profile')
    """))
    if unsafe:
        raise RuntimeError("Trade lifecycle data exists; downgrade would lose data")
    op.drop_constraint("ck_inventory_event_kind", "inventory_events", type_="check")
    op.create_check_constraint(None, "inventory_events", LEGACY_EVENT)
    op.drop_constraint("ck_inventory_source_sales", "inventory_daily", type_="check")
    op.drop_column("inventory_daily", "actual_blocked_qty")
    op.drop_column("inventory_daily", "source_sales_qty")
    op.drop_table("provider_product_notice_events")
    op.drop_table("provider_product_notice_items")
    op.drop_table("provider_product_notices")
    op.drop_constraint("ck_supply_action_dates", "item_supply_changes", type_="check")
    op.create_check_constraint("ck_supply_action_dates", "item_supply_changes",
                               INTERNAL_DATES.replace("effective_on>=known_on)", "effective_on>=known_on+7)"))
