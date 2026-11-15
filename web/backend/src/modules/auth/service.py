"""Opaque sessions; tokens/passwords never appear in DTOs or log messages."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from sqlalchemy import select, update
from core.errors import DomainError
from modules.auth.models import User, LoginSession
from modules.catalog.models import Supplier

PASSWORDS = PasswordHash.recommended()
DUMMY_PASSWORD = PASSWORDS.hash(secrets.token_urlsafe(32))
COOKIE = "sigma_session"
SESSION_HOURS = 8


def now():
    return datetime.now(timezone.utc)


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def public_user(user):
    return {key: getattr(user, key) for key in ("id", "username", "display_name", "role", "supplier_id", "active")}


def create_user(session, payload):
    if payload.role == "supplier" and session.get(Supplier, payload.supplier_id) is None:
        raise DomainError("supplier_not_found", "Nhà cung cấp không tồn tại.", 404)
    if session.scalar(select(User.id).where(User.username == payload.username)) is not None:
        raise DomainError("username_exists", "Tên đăng nhập đã được sử dụng.", 409)
    row = User(username=payload.username, display_name=payload.display_name, role=payload.role,
               supplier_id=payload.supplier_id, password_hash=PASSWORDS.hash(payload.password.get_secret_value()))
    session.add(row)
    session.flush()
    return row


def authenticate(sessions, username, password):
    """Commit failed counters before raising; row lock serializes password attempts."""
    rejected = False
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    with sessions.begin() as session:
        user = session.scalar(select(User).where(User.username == username).with_for_update())
        valid = PASSWORDS.verify(password, user.password_hash if user else DUMMY_PASSWORD)
        stamp = now()
        if not user or not user.active or (user.locked_until and user.locked_until > stamp):
            rejected = True
        elif not valid:
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = stamp + timedelta(minutes=15)
                user.failed_attempts = 0
            rejected = True
        else:
            user.failed_attempts, user.locked_until = 0, None
            # New random session on every login; no session supplied by client is reused.
            session.add(LoginSession(token_digest=digest(token), user_id=user.id, csrf_token=csrf,
                                     expires_at=stamp + timedelta(hours=SESSION_HOURS)))
            result = public_user(user)
    if rejected:
        raise DomainError("invalid_credentials", "Không đăng nhập được. Kiểm tra tài khoản hoặc thử lại sau.", 401)
    return result, token, csrf


def resolve(sessions, token):
    if not token or len(token) > 256:
        return None
    with sessions() as session:
        row = session.execute(select(User, LoginSession).join(LoginSession, User.id == LoginSession.user_id).where(
            LoginSession.token_digest == digest(token), LoginSession.revoked_at.is_(None),
            LoginSession.expires_at > now(), User.active.is_(True))).first()
        return (public_user(row[0]), row[1].csrf_token) if row else None


def revoke(sessions, token):
    if token:
        with sessions.begin() as session:
            session.execute(update(LoginSession).where(LoginSession.token_digest == digest(token)).values(revoked_at=now()))


def change_password(sessions, user_id, current_password, new_password):
    rejected = False
    with sessions.begin() as session:
        user = session.scalar(select(User).where(User.id == user_id).with_for_update())
        stamp = now()
        valid = PASSWORDS.verify(current_password, user.password_hash if user else DUMMY_PASSWORD)
        if not user or not user.active or (user.locked_until and user.locked_until > stamp):
            rejected = True
        elif not valid:
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.failed_attempts = 0
                user.locked_until = stamp + timedelta(minutes=15)
            rejected = True
        else:
            user.password_hash = PASSWORDS.hash(new_password)
            user.failed_attempts, user.locked_until = 0, None
            session.execute(update(LoginSession).where(LoginSession.user_id == user.id).values(revoked_at=stamp))
    if rejected:
        raise DomainError('password_change_rejected', 'Mật khẩu hiện tại không đúng hoặc tài khoản đang tạm khóa. Vui lòng kiểm tra hoặc thử lại sau.', 403)


def operator_reset_password(session, username, new_password):
    """Privileged offline recovery; no public reset endpoint or default credentials."""
    if not 12 <= len(new_password) <= 128:
        raise DomainError('invalid_input', 'Mật khẩu mới phải từ12–128 ký tự.')
    user = session.scalar(select(User).where(User.username == username).with_for_update())
    if user is None:
        raise DomainError('not_found', 'Không tìm thấy tài khoản.', 404)
    user.password_hash = PASSWORDS.hash(new_password)
    user.failed_attempts, user.locked_until = 0, None
    session.execute(update(LoginSession).where(LoginSession.user_id == user.id).values(revoked_at=now()))
