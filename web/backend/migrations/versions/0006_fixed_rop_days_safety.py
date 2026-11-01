"""Retire live policy modes; frozen runs keep their original configuration."""
from alembic import op
import sqlalchemy as sa

revision = "0006_fixed_days"
down_revision = "0005_carrier"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("ck_policy_safety_mode", "ck_policy_safety_lookback", "ck_policy_safety_factor", "ck_policy_rop_mode"):
        op.drop_constraint(name, "supplier_item_policies", type_="check")
    for name in ("safety_mode", "safety_lookback_days", "safety_factor", "rop_mode"):
        op.drop_column("supplier_item_policies", name)
    # Only editable scenarios change. Never rewrite runs.config_snapshot/hash.
    op.execute("""
        UPDATE scenarios s SET settings=jsonb_set(s.settings, '{policy_overrides}',
            (SELECT COALESCE(jsonb_agg(o.value - ARRAY['safety_mode','rop_mode','safety_lookback_days','safety_factor'] ORDER BY o.ordinality), '[]'::jsonb)
             FROM jsonb_array_elements(s.settings->'policy_overrides') WITH ORDINALITY o), false)
        WHERE jsonb_typeof(s.settings->'policy_overrides')='array'
          AND EXISTS (SELECT 1 FROM jsonb_array_elements(s.settings->'policy_overrides') o
                      WHERE o ?| ARRAY['safety_mode','rop_mode','safety_lookback_days','safety_factor'])
    """)


def downgrade():
    # Restore the previous shape/defaults only; the backup retains removed values.
    for name, kind, default in (("safety_mode", sa.Text(), "days"),
                                 ("safety_lookback_days", sa.SmallInteger(), "28"),
                                 ("safety_factor", sa.Double(), "1"), ("rop_mode", sa.Text(), "forecast")):
        op.add_column("supplier_item_policies", sa.Column(name, kind, nullable=False, server_default=default))
    for name, condition in (("ck_policy_safety_mode", "safety_mode IN ('days','volatility')"),
                            ("ck_policy_safety_lookback", "safety_lookback_days BETWEEN 7 AND 90"),
                            ("ck_policy_safety_factor", "safety_factor>=0 AND safety_factor<'Infinity'::float8"),
                            ("ck_policy_rop_mode", "rop_mode IN ('fixed','forecast')")):
        op.create_check_constraint(name, "supplier_item_policies", condition)
