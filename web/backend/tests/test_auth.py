"""Real PostgreSQL auth isolation and revocation; synthetic accounts only."""
from dataclasses import replace
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select, update
import pytest
from main import create_app
from modules.auth.models import User, LoginSession
from modules.auth.schemas import UserCreate
from modules.auth.service import create_user, now, COOKIE, digest
from modules.catalog.models import Item, Warehouse
from modules.dealers.models import Dealer
from test_postgres_api import seed, settings, D

PASSWORD = "Synthetic-only-Password-2026"


@pytest.fixture
def auth_app(pg, tmp_path):
    _, sessions = pg
    seed(sessions)
    with sessions.begin() as session:
        w = Warehouse(code="OTHER", destination_country="OtherLand", carrier="OtherCarrier", city="Other City", assumption_source="synthetic")
        session.add(w); session.flush()
        session.add(Item(warehouse_id=w.id, sku="OTHER-ONLY", product_type="physical_SIM", first_seen_date=D))
        admin = create_user(session, UserCreate(username="admin", display_name="admin", password=PASSWORD, role="admin"))
        # Non-admin test accounts are dealers since supplier logins were retired (0012).
        for username, code in (("partner-a", "DL-A"), ("partner-b", "DL-B")):
            dealer = Dealer(code=code, name="Đại lý " + code, created_by=admin.id)
            session.add(dealer); session.flush()
            create_user(session, UserCreate(username=username, display_name=username, password=PASSWORD, role="dealer", dealer_id=dealer.id))
    app = create_app(replace(settings(tmp_path), auth_required=True))
    yield app, sessions
    app.state.engine.dispose()


def login(client, username="admin"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_anonymous_and_dealer_cannot_reach_admin_routes(auth_app):
    app, _ = auth_app
    with TestClient(app) as client:
        for path in ("/products", "/runs", "/auth/users", "/runs/00000000-0000-0000-0000-000000000000/snapshot"):
            assert client.get("/api/v1" + path).status_code == 401
        assert client.get("/api/v1/health").status_code == 200
        headers = login(client, "partner-a")
        for method, path in (("GET", "/products/2"), ("GET", "/runs"), ("GET", "/auth/users"),
                             ("GET", "/runs/00000000-0000-0000-0000-000000000000/snapshot"),
                             ("GET", "/runs/00000000-0000-0000-0000-000000000000/exports/inventory_daily"),
                             ("POST", "/runs"), ("PATCH", "/products/2/receiving-warehouse"),
                             ("GET", "/operations/summary"), ("GET", "/dealers"), ("GET", "/dealers/requests"),
                             ("GET", "/supplier/products")):
            assert client.request(method, "/api/v1" + path, headers=headers).status_code == 403
        assert client.get("/api/v1/dealer/products").status_code == 200


def test_session_csrf_logout_expiry_and_cookie_flags(auth_app):
    app, sessions = auth_app
    with TestClient(app) as client:
        headers = login(client)
        response = client.get("/api/v1/auth/session")
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["user"]["role"] == "admin"
        assert "password" not in str(response.json())
        token = client.cookies.get(COOKIE)
        cookie = next(c for c in client.cookies.jar if c.name == COOKIE)
        assert cookie.has_nonstandard_attr("HttpOnly") and cookie.get_nonstandard_attr("SameSite") == "lax"
        assert client.post("/api/v1/auth/logout").status_code == 403
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        client.cookies.set(COOKIE, token, path="/api/v1")
        assert client.get("/api/v1/auth/session").status_code == 401
        client.cookies.clear()
        login(client)
        with sessions.begin() as session:
            session.execute(update(LoginSession).values(expires_at=now() - timedelta(seconds=1)))
        assert client.get("/api/v1/auth/session").status_code == 401
        with sessions() as session:
            assert session.get(LoginSession, digest(token)).revoked_at is not None


def test_admin_creates_disables_and_revokes_dealer_sessions(auth_app):
    app, sessions = auth_app
    with TestClient(app) as admin, TestClient(app) as supplier:
        headers = login(admin)
        login(supplier, "partner-a")
        rows = admin.get("/api/v1/auth/users").json()["items"]
        user = next(row for row in rows if row["username"] == "partner-a")
        assert "password_hash" not in user
        assert admin.patch(f'/api/v1/auth/users/{user["id"]}', headers=headers, json={"active": False}).status_code == 200
        assert supplier.get("/api/v1/dealer/products").status_code == 401
        assert supplier.post("/api/v1/auth/login", json={"username": "partner-a", "password": PASSWORD}).status_code == 401
        me = admin.get("/api/v1/auth/session").json()["user"]["id"]
        assert admin.patch(f"/api/v1/auth/users/{me}", headers=headers, json={"active": False}).status_code == 409
        created = admin.post("/api/v1/auth/users", headers=headers, json={"username": "new-user", "password": PASSWORD,
            "display_name": "New", "role": "dealer", "dealer_id": user["dealer_id"]})
        assert created.status_code == 201 and created.json()["dealer_id"] == user["dealer_id"]
        assert admin.post("/api/v1/auth/users", headers=headers, json={"username": "old-supplier", "password": PASSWORD,
            "display_name": "Old", "role": "supplier", "supplier_id": 1}).status_code == 422
        with sessions.begin() as session:
            session.add(User(username="legacy-supplier", display_name="Legacy", role="supplier", supplier_id=1,
                password_hash="retired", active=False))
        legacy = next(r for r in admin.get("/api/v1/auth/users").json()["items"] if r["username"] == "legacy-supplier")
        # Retired supplier accounts cannot be switched back on.
        assert admin.patch(f'/api/v1/auth/users/{legacy["id"]}', headers=headers, json={"active": True}).status_code == 409
        assert admin.post("/api/v1/auth/users", headers=headers, json={"username": "new-user", "password": PASSWORD,
            "display_name": "New", "role": "admin"}).status_code == 409


def test_lockout_and_login_origin(auth_app):
    app, sessions = auth_app
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/login", headers={"Origin": "https://untrusted.invalid"},
            json={"username": "admin", "password": PASSWORD}).status_code == 403
        for _ in range(5):
            assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"username": "admin", "password": PASSWORD}).status_code == 401
        with sessions.begin() as session:
            user = session.scalar(select(User).where(User.username == "admin"))
            assert user.locked_until > now()
            user.locked_until = now() - timedelta(seconds=1)
        login(client)


def test_schema_scope_and_password_rules():
    from pydantic import ValidationError
    for fields in ({"role": "admin", "dealer_id": 1}, {"role": "dealer"}, {"role": "supplier", "supplier_id": 1},
                   {"role": "admin", "password": "short"}):
        with pytest.raises(ValidationError):
            UserCreate(**{"username": "user", "display_name": "Name", "password": PASSWORD, **fields})


def test_auth_migration_metadata_and_downgrade_guard(auth_app):
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from models import Base
    app, _ = auth_app
    engine = app.state.engine
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["database_url"] = engine.url.render_as_string(hide_password=False)
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True}), Base.metadata) == []
    with pytest.raises(RuntimeError, match="Dealer data exists"):
        command.downgrade(cfg, "0009_receiving_warehouse")
    with TestClient(app) as client:
        login(client)  # Rejected downgrade leaves accounts and the schema intact.


def test_https_cookie_and_default_startup_enable_auth(auth_app, monkeypatch, tmp_path):
    from core.settings import Settings
    app, _ = auth_app
    monkeypatch.setenv("M3_DATABASE_URL", app.state.settings.database_url)
    monkeypatch.delenv("M3_MODE", raising=False)
    monkeypatch.delenv("M3_FRONTEND_ORIGIN", raising=False)
    assert Settings.from_env().auth_required is True
    with TestClient(app, base_url="https://testserver") as client:
        response = client.post("/api/v1/auth/login", json={"username": "admin", "password": PASSWORD})
        assert response.status_code == 200
        assert "Secure" in response.headers["set-cookie"] and "HttpOnly" in response.headers["set-cookie"]
