"""Record the origin whose 90-day window built each allocation basis (M7/W1).

New forecast runs build the weekday weights and SKU shares once per route and reuse them until a new SKU
appears. NULL keeps the earlier meaning: the basis was recomputed at the row's own as_of_date.
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_item_forecast_basis_date"
down_revision = "0016_run_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("item_forecasts", sa.Column("basis_as_of_date", sa.Date()))
    op.create_check_constraint("ck_item_forecast_basis_date", "item_forecasts", "basis_as_of_date<=as_of_date")


def downgrade():
    op.execute("LOCK TABLE item_forecasts IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM item_forecasts WHERE basis_as_of_date IS NOT NULL)")):
        raise RuntimeError("Forecasts with a reused allocation basis exist; downgrade would lose their basis date")
    op.drop_constraint("ck_item_forecast_basis_date", "item_forecasts", type_="check")
    op.drop_column("item_forecasts", "basis_as_of_date")
