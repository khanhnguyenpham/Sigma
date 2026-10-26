"""Add origin ROP crossing alerts; preserve all existing run and result rows.

Revision ID: 0003_threshold
Revises: 0002_policy
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_threshold"
down_revision = "0002_policy"
branch_labels = None
depends_on = None

OLD_TYPE = "alert_type IN ('below_rop','depletion')"
OLD_STATE = "state IN ('low_stock','pending_covers','urgent','early','already_depleted','not_within_horizon')"


def upgrade():
    # 0001 used unnamed checks. Resolve their PostgreSQL names from the column
    # expressions rather than assume a generated check/check1 suffix.
    for check in sa.inspect(op.get_bind()).get_check_constraints("alerts"):
        if check["sqltext"].lstrip("(").startswith(("alert_type ", "state ")):
            op.drop_constraint(check["name"], "alerts", type_="check")
    op.add_column("alerts", sa.Column("predicted_threshold_date", sa.Date(), nullable=True))
    op.create_check_constraint("ck_alert_type", "alerts", "alert_type IN ('below_rop','depletion','projected_below_rop')")
    op.create_check_constraint("ck_alert_state", "alerts", "state IN ('low_stock','pending_covers','urgent','early','already_depleted','not_within_horizon','threshold_warning')")
    op.create_check_constraint("ck_alert_threshold_date", "alerts",
        "(alert_type = 'projected_below_rop' AND state = 'threshold_warning' AND predicted_threshold_date IS NOT NULL AND predicted_threshold_date > as_of_date AND predicted_threshold_date <= as_of_date + 14) OR "
        "(alert_type <> 'projected_below_rop' AND state <> 'threshold_warning' AND predicted_threshold_date IS NULL)")


def downgrade():
    # Refuse to drop new results. The old type check fails transactionally if a
    # threshold alert exists; the caller must explicitly handle such runs first.
    op.create_check_constraint("alerts_alert_type_check", "alerts", OLD_TYPE)
    op.create_check_constraint("alerts_state_check", "alerts", OLD_STATE)
    for name in ("ck_alert_threshold_date", "ck_alert_state", "ck_alert_type"):
        op.drop_constraint(name, "alerts", type_="check")
    op.drop_column("alerts", "predicted_threshold_date")
