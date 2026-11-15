"""Admin/supplier users and revocable opaque sessions; no default accounts."""
from alembic import op
import sqlalchemy as sa

revision = "0010_auth_sessions"
down_revision = "0009_receiving_warehouse"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("auth_users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), sa.ForeignKey("suppliers.id", ondelete="RESTRICT")),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("username ~ '^[a-z0-9][a-z0-9._-]{2,63}$'", name="ck_auth_username"),
        sa.CheckConstraint("length(btrim(display_name)) BETWEEN 1 AND 100", name="ck_auth_display_name"),
        sa.CheckConstraint("(role='admin' AND supplier_id IS NULL) OR (role='supplier' AND supplier_id IS NOT NULL)", name="ck_auth_scope"),
        sa.CheckConstraint("failed_attempts>=0", name="ck_auth_failed"))
    op.create_table("auth_sessions",
        sa.Column("token_digest", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("csrf_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_auth_session_user", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_session_expiry", "auth_sessions", ["expires_at"])


def downgrade():
    op.execute("LOCK TABLE auth_users, auth_sessions IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM auth_users) OR EXISTS(SELECT 1 FROM auth_sessions)")):
        raise RuntimeError("Authentication data exists; downgrade would lose data")
    op.drop_table("auth_sessions")
    op.drop_table("auth_users")
