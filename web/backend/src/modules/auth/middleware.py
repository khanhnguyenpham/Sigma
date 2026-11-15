import secrets
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import OperationalError
from modules.auth.service import COOKIE, resolve

PUBLIC = {"/api/v1/live", "/api/v1/ready", "/api/v1/health", "/api/v1/auth/login"}
SAFE = {"GET", "HEAD", "OPTIONS"}


def install_auth(app):
    @app.middleware("http")
    async def session_guard(request, call_next):
        path = request.url.path.rstrip("/")
        if (not request.app.state.settings.auth_required or not path.startswith("/api/v1/")
                or path in PUBLIC or request.method == "OPTIONS"):
            return await call_next(request)
        try:
            identity = await run_in_threadpool(resolve, request.app.state.sessions, request.cookies.get(COOKIE))
        except OperationalError:
            return JSONResponse(status_code=503, content={"error": {"code": "database_unavailable", "message": "Không kết nối được hệ thống tài khoản. Vui lòng thử lại."}})
        if identity is None:
            return JSONResponse(status_code=401, content={"error": {"code": "authentication_required", "message": "Vui lòng đăng nhập lại."}})
        user, csrf = identity
        request.state.user, request.state.csrf_token = user, csrf
        if (user["role"] != "admin" and not path.startswith("/api/v1/supplier/")
                and path not in {"/api/v1/auth/session", "/api/v1/auth/logout"}):
            return JSONResponse(status_code=403, content={"error": {"code": "forbidden", "message": "Tài khoản không có quyền thực hiện thao tác này."}})
        if request.method not in SAFE and not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), csrf):
            return JSONResponse(status_code=403, content={"error": {"code": "csrf_required", "message": "Phiên thao tác không hợp lệ. Vui lòng đăng nhập lại."}})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response
