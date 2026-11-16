from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, Text, Index, text
from core.db import Base, created, fk, identity


class User(Base):
    __tablename__ = "auth_users"
    id = identity()
    username = Column(Text, nullable=False, unique=True)
    display_name = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    supplier_id = fk("suppliers", nullable=True)
    dealer_id = fk("dealers", nullable=True)
    password_hash = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    failed_attempts = Column(Integer, nullable=False, server_default=text("0"))
    locked_until = Column(DateTime(timezone=True))
    created_at = created()
    __table_args__ = (
        CheckConstraint("username ~ '^[a-z0-9][a-z0-9._-]{2,63}$'", name="ck_auth_username"),
        CheckConstraint("length(btrim(display_name)) BETWEEN 1 AND 100", name="ck_auth_display_name"),
        # Supplier logins were retired in 0012; legacy rows stay for audit but can never be active.
        CheckConstraint("(role='admin' AND supplier_id IS NULL AND dealer_id IS NULL) OR (role='supplier' AND supplier_id IS NOT NULL AND dealer_id IS NULL AND NOT active) OR (role='dealer' AND dealer_id IS NOT NULL AND supplier_id IS NULL)", name="ck_auth_scope"),
        CheckConstraint("failed_attempts>=0", name="ck_auth_failed"),
    )


class LoginSession(Base):
    __tablename__ = "auth_sessions"
    token_digest = Column(Text, primary_key=True)
    user_id = fk("auth_users")
    csrf_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    created_at = created()
    __table_args__ = (Index("ix_auth_session_user", "user_id"), Index("ix_auth_session_expiry", "expires_at"))
