from fastapi import APIRouter, Request, Response, Query
from sqlalchemy import select, func, update
from core.errors import DomainError
from modules.auth.models import User, LoginSession
from modules.auth.schemas import LoginInput, UserCreate, UserActive, PasswordChange
from modules.auth.service import COOKIE, SESSION_HOURS, authenticate, create_user, public_user, revoke, now

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post('/password')
def update_password(payload: PasswordChange, request: Request, response: Response):
    enabled(request)
    from modules.auth.service import change_password
    change_password(request.app.state.sessions, request.state.user['id'],
        payload.current_password.get_secret_value(), payload.new_password.get_secret_value())
    response.delete_cookie(COOKIE, path='/api/v1')
    return {'ok': True, 'login_required': True}


def enabled(request):
    if not request.app.state.settings.auth_required:
        raise DomainError("auth_disabled", "Đăng nhập chưa bật trong môi trường thử này.", 503)


@router.get("/session")
def session_info(request: Request):
    if not request.app.state.settings.auth_required:
        return {"required": False, "user": None}
    return {"required": True, "user": request.state.user, "csrf_token": request.state.csrf_token}


@router.post("/login")
def login(payload: LoginInput, request: Request, response: Response):
    enabled(request)
    # Login CSRF: browser origins must be this API or the explicitly configured FE.
    origin = request.headers.get("origin")
    own_origin = str(request.base_url).rstrip("/")
    if origin and origin not in {own_origin, request.app.state.settings.frontend_origin}:
        raise DomainError("forbidden_origin", "Nguồn đăng nhập không hợp lệ.", 403)
    user, token, csrf = authenticate(request.app.state.sessions, payload.username, payload.password.get_secret_value())
    revoke(request.app.state.sessions, request.cookies.get(COOKIE))
    secure = request.app.state.settings.frontend_origin.startswith("https://") or request.url.scheme == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_HOURS * 3600, httponly=True, secure=secure, samesite="lax", path="/api/v1")
    response.headers["Cache-Control"] = "no-store"
    return {"required": True, "user": user, "csrf_token": csrf}


@router.post("/logout")
def logout(request: Request, response: Response):
    enabled(request)
    revoke(request.app.state.sessions, request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path="/api/v1")
    return {"ok": True}


@router.get("/users")
def users(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    enabled(request)
    with request.app.state.sessions() as session:
        total = session.scalar(select(func.count()).select_from(User))
        rows = session.scalars(select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size))
        return {"items": [public_user(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/users", status_code=201)
def add_user(payload: UserCreate, request: Request):
    enabled(request)
    with request.app.state.sessions.begin() as session:
        return public_user(create_user(session, payload))


@router.patch("/users/{key}")
def activate_user(key: int, payload: UserActive, request: Request):
    enabled(request)
    if key == request.state.user["id"] and not payload.active:
        raise DomainError("self_disable", "Không thể khóa tài khoản đang sử dụng.", 409)
    with request.app.state.sessions.begin() as session:
        user = session.get(User, key, with_for_update=True)
        if user is None:
            raise DomainError("user_not_found", "Không có tài khoản này.", 404)
        user.active = payload.active
        if not payload.active:
            session.execute(update(LoginSession).where(LoginSession.user_id == key).values(revoked_at=now()))
        return public_user(user)
