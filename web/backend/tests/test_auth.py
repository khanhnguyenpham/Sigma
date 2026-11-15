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
from modules.catalog.models import Item, Warehouse, Supplier
from test_postgres_api import seed, settings, D

PASSWORD = "Synthetic-only-Password-2026"


@pytest.fixture
def auth_app(pg, tmp_path):
    _, sessions = pg
    _, a, b = seed(sessions)
    with sessions.begin() as session:
        w = Warehouse(code="OTHER", destination_country="OtherLand", carrier="OtherCarrier", city="Other City", assumption_source="synthetic")
        session.add(w); session.flush()
        session.add(Item(warehouse_id=w.id, sku="OTHER-ONLY", product_type="physical_SIM", first_seen_date=D))
        for username, role, supplier in (("admin", "admin", None), ("partner-a", "supplier", a), ("partner-b", "supplier", b)):
            create_user(session, UserCreate(username=username, display_name=username, password=PASSWORD, role=role, supplier_id=supplier))
    app = create_app(replace(settings(tmp_path), auth_required=True))
    yield app, sessions
    app.state.engine.dispose()


def login(client, username="admin"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_anonymous_and_supplier_cannot_reach_admin_routes(auth_app):
    app, _ = auth_app
    with TestClient(app) as client:
        for path in ("/products", "/runs", "/auth/users", "/runs/00000000-0000-0000-0000-000000000000/snapshot"):
            assert client.get("/api/v1" + path).status_code == 401
        assert client.get("/api/v1/health").status_code == 200
        headers = login(client, "partner-a")
        for method, path in (("GET", "/products/2"), ("GET", "/runs"), ("GET", "/auth/users"),
                             ("GET", "/runs/00000000-0000-0000-0000-000000000000/snapshot"),
                             ("GET", "/runs/00000000-0000-0000-0000-000000000000/exports/inventory_daily"),
                             ("POST", "/runs"), ("PATCH", "/products/2/receiving-warehouse")):
            assert client.request(method, "/api/v1" + path, headers=headers).status_code == 403
        own = client.get("/api/v1/supplier/products?page_size=1").json()
        assert own["total"] == 1 and own["items"][0]["sku"] == "DEMO-ESIM-01"
        assert client.get("/api/v1/supplier/products?page=2&page_size=1").json()["items"] == []
        # A caller-supplied scope cannot override the authenticated supplier.
        assert client.get("/api/v1/supplier/products?supplier_id=2").json()["items"][0]["sku"] == "DEMO-ESIM-01"
    with TestClient(app) as other:
        login(other, "partner-b")
        assert other.get("/api/v1/supplier/products").json()["items"][0]["sku"] == "OTHER-ONLY"


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


def test_admin_creates_disables_and_revokes_supplier_sessions(auth_app):
    app, _ = auth_app
    with TestClient(app) as admin, TestClient(app) as supplier:
        headers = login(admin)
        login(supplier, "partner-a")
        rows = admin.get("/api/v1/auth/users").json()["items"]
        user = next(row for row in rows if row["username"] == "partner-a")
        assert "password_hash" not in user
        assert admin.patch(f'/api/v1/auth/users/{user["id"]}', headers=headers, json={"active": False}).status_code == 200
        assert supplier.get("/api/v1/supplier/products").status_code == 401
        assert supplier.post("/api/v1/auth/login", json={"username": "partner-a", "password": PASSWORD}).status_code == 401
        me = admin.get("/api/v1/auth/session").json()["user"]["id"]
        assert admin.patch(f"/api/v1/auth/users/{me}", headers=headers, json={"active": False}).status_code == 409
        created = admin.post("/api/v1/auth/users", headers=headers, json={"username": "new-user", "password": PASSWORD,
            "display_name": "New", "role": "supplier", "supplier_id": user["supplier_id"]})
        assert created.status_code == 201
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
    for fields in ({"role": "admin", "supplier_id": 1}, {"role": "supplier"}, {"role": "admin", "password": "short"}):
        with pytest.raises(ValidationError):
            UserCreate(**{"username": "user", "display_name": "Name", "password": PASSWORD, **fields})


def test_supplier_shipments_are_scoped_before_paging(auth_app):
    from modules.configuration.models import Policy
    from modules.purchasing.models import Replenishment
    from modules.runs.service import enqueue
    from modules.runs.schemas import RunCreate
    app, sessions = auth_app
    with sessions.begin() as session:
        run, _ = enqueue(session, RunCreate(kind="source_import", source_key="orders_snapshot", as_of_date=D), "auth-scope-test")
        for index, (item_id, supplier_id) in enumerate(session.execute(select(Item.id, User.supplier_id).join(
                Warehouse, Item.warehouse_id == Warehouse.id).join(Supplier, Warehouse.carrier == Supplier.carrier).join(
                    User, User.supplier_id == Supplier.id).where(User.role == "supplier"))):
            policy = Policy(item_id=item_id, supplier_id=supplier_id, version=1, effective_from=D,
                configured_rop_floor=0, moq=None, fixed_order_qty=15, safety_days=1, assumption_source="synthetic")
            session.add(policy); session.flush()
            session.add(Replenishment(run_id=run.id, window_origin=D, item_id=item_id, policy_id=policy.id,
                order_key=f"synthetic-{index}", ordered_on=D, eta=D + timedelta(days=7), ordered_qty=15,
                received_qty=0, status="ordered", is_initial=False, is_simulated=True))
    with TestClient(app) as client:
        login(client, "partner-a")
        data = client.get("/api/v1/supplier/shipments?page_size=1").json()
        assert data["total"] == 1 and data["items"][0]["sku"] == "DEMO-ESIM-01"
        assert data["items"][0]["is_simulated"] is True
        assert client.get("/api/v1/supplier/shipments?page=2&page_size=1").json()["items"] == []
    with TestClient(app) as client:
        login(client, "partner-b")
        assert client.get("/api/v1/supplier/shipments").json()["items"][0]["sku"] == "OTHER-ONLY"


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
    with pytest.raises(RuntimeError, match="Authentication data exists"):
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
