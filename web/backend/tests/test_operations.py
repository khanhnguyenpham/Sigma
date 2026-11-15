"""Operational documents on real isolated PostgreSQL; all values are synthetic."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
import uuid
import pytest
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text, update
from sqlalchemy.exc import DBAPIError
from models import Base
from modules.operations import service
from modules.operations.models import StockBalance, StockDocument, StockDocumentLine, OperationalOrder, OperationAudit
from test_auth import auth_app, login

BASE = "/api/v1/operations"


def post(client, path, body, key=None):
    return client.post(BASE + path, json=body, headers={"Idempotency-Key": key or str(uuid.uuid4())})


def setup_catalog(client):
    warehouse = post(client, "/warehouses", {"code": "QA-01", "name": "Kho kiểm thử", "country": "Vietnam"})
    assert warehouse.status_code == 201, warehouse.text
    product = post(client, "/products", {"name": "SIM kiểm thử", "sku": "DEMO-ESIM-01", "product_type": "eSIM",
        "carrier": "DemoCarrier", "destination_country": "DemoLand"})
    assert product.status_code == 201, product.text
    return warehouse.json()["id"], product.json()["id"], product.json()["supplier_id"]


def draft(client, warehouse, item, supplier, quantity=10, key=None):
    result = post(client, "/orders", {"supplier_id": supplier, "ordered_on": str(service.today()), "note": "Synthetic",
        "lines": [{"item_id": item, "warehouse_id": warehouse, "quantity": quantity}]}, key)
    assert result.status_code in (200, 201), result.text
    return result.json()


def confirm(client, order):
    result = post(client, f'/orders/{order["id"]}/confirm', {"expected_version": order["version"]})
    assert result.status_code == 200, result.text
    return result.json()


def receipt_body(order, quantity, reference="DELIVERY-1"):
    return {"expected_version": order["version"], "occurred_on": str(service.today()), "external_ref": reference,
        "lines": [{"order_line_id": order["lines"][0]["id"], "quantity": quantity}]}


def movement(warehouse, item, quantity, version=0, reference="COUNT-1", day=None):
    return {"warehouse_id": warehouse, "item_id": item, "quantity": quantity, "expected_balance_version": version,
        "occurred_on": str(day or service.today()), "external_ref": reference, "reason": "Đối soát kiểm thử"}


def test_real_order_receipts_issue_count_and_ledger_reconcile(auth_app):
    app, sessions = auth_app
    with TestClient(app) as client:
        client.headers.update(login(client))
        warehouse, item, supplier = setup_catalog(client)
        order = draft(client, warehouse, item, supplier)
        assert client.get(BASE + "/stock").json()["total"] == 0
        empty_position = client.get(BASE + f"/stock/{warehouse}/{item}")
        assert empty_position.status_code == 200
        assert empty_position.json()["on_hand_qty"] == empty_position.json()["version"] == 0
        assert client.get(BASE + "/stock/999999/999999").status_code == 404
        order = confirm(client, order)
        assert client.get(BASE + "/stock").json()["total"] == 0
        first = post(client, f'/orders/{order["id"]}/receipts', receipt_body(order, 4))
        assert first.status_code == 201, first.text
        order = client.get(BASE + f'/orders/{order["id"]}').json()
        assert order["status"] == "partially_received" and order["lines"][0]["received_qty"] == 4
        assert post(client, f'/orders/{order["id"]}/receipts', receipt_body(order, 6, "DELIVERY-2")).status_code == 201
        assert client.get(BASE + f'/orders/{order["id"]}').json()["status"] == "received"
        assert post(client, "/issues", movement(warehouse, item, 3, 2, "ISSUE-1")).status_code == 201
        assert post(client, "/counts", movement(warehouse, item, 8, 3)).status_code == 201
        balance = client.get(BASE + "/stock").json()["items"][0]
        assert balance["on_hand_qty"] == 8 and balance["version"] == 4
        assert client.get(BASE + f"/stock/{warehouse}/{item}").json()["on_hand_qty"] == 8
        assert client.get(BASE + "/documents").json()["total"] == 4
        assert client.get(BASE + "/summary").json()["pending_orders"] == 0
        assert client.get(BASE + "/audit").json()["total"] >= 8
    with sessions() as session:
        assert session.scalar(select(func.sum(StockDocumentLine.quantity_delta))) == session.scalar(select(StockBalance.on_hand_qty)) == 8
        assert session.scalar(text("SELECT count(*) FROM inventory_daily")) == 0
        assert session.scalar(text("SELECT count(*) FROM runs")) == 0


def test_retry_conflict_over_receipt_and_cancel_remainder(auth_app):
    app, sessions = auth_app
    with TestClient(app) as client:
        client.headers.update(login(client)); warehouse, item, supplier = setup_catalog(client)
        order = draft(client, warehouse, item, supplier, key="same-order")
        again = draft(client, warehouse, item, supplier, key="same-order")
        assert again["id"] == order["id"]
        order = confirm(client, order)
        bad = post(client, f'/orders/{order["id"]}/receipts', receipt_body(order, 11), "bad-receipt")
        assert bad.status_code == 409
        assert client.get(BASE + "/stock").json()["total"] == 0
        body = receipt_body(order, 4)
        first = post(client, f'/orders/{order["id"]}/receipts', body, "same-receipt")
        replay = post(client, f'/orders/{order["id"]}/receipts', body, "same-receipt")
        assert first.status_code == 201 and replay.status_code == 200
        assert first.json()["id"] == replay.json()["id"]
        assert post(client, f'/orders/{order["id"]}/receipts', {**body, "reason": "changed"}, "same-receipt").status_code == 409
        order = client.get(BASE + f'/orders/{order["id"]}').json()
        assert post(client, f'/orders/{order["id"]}/receipts', receipt_body(order, 1), "new-key-same-note").status_code == 409
        cancelled = post(client, f'/orders/{order["id"]}/cancel', {"expected_version": order["version"], "reason": "NCC chỉ giao được 4"})
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
        assert client.get(BASE + "/stock").json()["items"][0]["on_hand_qty"] == 4
        assert client.get(BASE + "/summary").json()["pending_orders"] == 0
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(OperationalOrder)) == 1
        assert session.scalar(select(func.count()).select_from(StockDocument)) == 1


def test_supplier_defaults_freeze_new_orders_without_changing_legacy_l7(auth_app):
    app, _ = auth_app
    with TestClient(app) as client:
        client.headers.update(login(client)); warehouse, item, supplier = setup_catalog(client)
        old = draft(client, warehouse, item, supplier)
        changed = client.patch(BASE + f"/suppliers/{supplier}/settings", json={"lead_time_days": 30, "expected_version": 0, "reason": "Điều chỉnh hợp đồng"})
        assert changed.status_code == 200, changed.text
        new = draft(client, warehouse, item, supplier)
        assert new["lead_time_days"] == 30 and old["lead_time_days"] == 7
        assert client.get(BASE + f'/orders/{old["id"]}').json()["eta"] == old["eta"]
        assert new["eta"] == str(service.today() + timedelta(days=30))
        assert client.patch(BASE + f"/suppliers/{supplier}/settings", json={"lead_time_days": 1, "expected_version": 0, "reason": "stale"}).status_code == 409
    from modules.inventory.service import eta
    assert eta(service.today()) == service.today() + timedelta(days=7)


def test_zero_count_negative_stock_dates_and_stale_balance_are_checked(auth_app):
    app, _ = auth_app
    with TestClient(app) as client:
        client.headers.update(login(client)); warehouse, item, _ = setup_catalog(client)
        assert post(client, "/counts", movement(warehouse, item, 0)).status_code == 201
        assert client.get(BASE + "/stock").json()["items"][0]["on_hand_qty"] == 0
        assert post(client, "/issues", movement(warehouse, item, 1, 1, "OUT")).status_code == 409
        assert post(client, "/counts", movement(warehouse, item, 2, 0, "STALE")).status_code == 409
        assert post(client, "/counts", movement(warehouse, item, 2, 1, "FUTURE", service.today() + timedelta(days=1))).status_code == 422
        assert post(client, "/counts", movement(warehouse, item, 2, 1, "PAST", service.today() - timedelta(days=1))).status_code == 409
        assert client.get(BASE + "/documents").json()["total"] == 1


@pytest.mark.parametrize("same_key", [True, False])
def test_two_clients_receipts_have_one_effect(auth_app, same_key):
    app, sessions = auth_app
    with TestClient(app) as a, TestClient(app) as b:
        a.headers.update(login(a)); b.headers.update(login(b))
        warehouse, item, supplier = setup_catalog(a)
        order = confirm(a, draft(a, warehouse, item, supplier))
        body = receipt_body(order, 4)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda pair: post(pair[0], f'/orders/{order["id"]}/receipts',
                {**body, "external_ref": "DELIVERY" if same_key else "DELIVERY-" + pair[1]},
                "concurrent" if same_key else pair[1]), [(a, "A"), (b, "B")]))
        assert sorted(result.status_code for result in results) == ([200, 201] if same_key else [201, 409])
    with sessions() as session:
        assert session.scalar(select(StockBalance.on_hand_qty)) == 4
        assert session.scalar(select(func.count()).select_from(StockDocument)) == 1


def test_posting_failure_rolls_back_all_effects_and_retry_recovers(auth_app):
    app, sessions = auth_app
    with TestClient(app, raise_server_exceptions=False) as client:
        client.headers.update(login(client)); warehouse, item, supplier = setup_catalog(client)
        order = confirm(client, draft(client, warehouse, item, supplier))
        original = service.audit
        def interrupted(session, entity_type, key, action, actor, **details):
            if action == "posted":
                raise RuntimeError("Synthetic interruption after balance update")
            return original(session, entity_type, key, action, actor, **details)
        with patch.object(service, "audit", interrupted):
            assert post(client, f'/orders/{order["id"]}/receipts', receipt_body(order, 4), "interrupted").status_code == 500
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(StockDocument)) == 0
            assert session.scalar(select(func.count()).select_from(StockBalance)) == 0
        assert post(client, f'/orders/{order["id"]}/receipts', receipt_body(order, 4), "interrupted").status_code == 201


def test_supplier_scope_and_anonymous_operations_are_denied(auth_app):
    app, _ = auth_app
    with TestClient(app) as admin, TestClient(app) as a, TestClient(app) as b:
        assert admin.get(BASE + "/stock").status_code == 401
        admin.headers.update(login(admin)); login(a, "partner-a"); login(b, "partner-b")
        warehouse, item, supplier = setup_catalog(admin)
        order = confirm(admin, draft(admin, warehouse, item, supplier))
        assert a.get("/api/v1/supplier/orders").json()["total"] == 1
        assert b.get("/api/v1/supplier/orders").json()["total"] == 0
        assert b.get(f'/api/v1/supplier/orders/{order["id"]}').status_code == 404
        assert a.get(BASE + "/stock").status_code == 403
        assert a.post(BASE + "/counts", json={}).status_code == 403
        assert "note" not in a.get(f'/api/v1/supplier/orders/{order["id"]}').json()


def test_warehouse_archive_blocks_stock_and_pending_orders(auth_app):
    app, _ = auth_app
    with TestClient(app) as client:
        client.headers.update(login(client)); warehouse, item, supplier = setup_catalog(client)
        order = confirm(client, draft(client, warehouse, item, supplier))
        change = {"name": "Kho kiểm thử", "country": "Vietnam", "active": False, "expected_version": 1, "reason": "Đóng kho"}
        assert client.patch(BASE + f"/warehouses/{warehouse}", json=change).status_code == 409
        assert post(client, f'/orders/{order["id"]}/cancel', {"expected_version": order["version"], "reason": "Hủy phần chờ"}).status_code == 200
        assert client.patch(BASE + f"/warehouses/{warehouse}", json=change).status_code == 200
        assert post(client, "/counts", movement(warehouse, item, 1)).status_code == 409


def test_migration_matches_models_and_posted_documents_are_immutable(auth_app):
    app, sessions = auth_app
    engine = app.state.engine
    with TestClient(app) as client:
        client.headers.update(login(client)); warehouse, item, _ = setup_catalog(client)
        assert post(client, "/counts", movement(warehouse, item, 3)).status_code == 201
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True}), Base.metadata) == []
    with pytest.raises(DBAPIError), sessions.begin() as session:
        session.execute(update(StockDocument).values(reason="tampered"))
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["database_url"] = engine.url.render_as_string(hide_password=False)
    with pytest.raises(RuntimeError, match="Operational data exists"):
        command.downgrade(cfg, "0010_auth_sessions")


def test_operational_locations_and_product_registration_preserve_source_identity(auth_app):
    from modules.catalog.models import Item, Warehouse as SourceWarehouse
    app, sessions = auth_app
    with sessions() as session:
        original = session.get(Item, 1)
        identity = (original.warehouse_id, original.sku, original.product_type, original.first_seen_date)
        original_city = session.get(SourceWarehouse, original.warehouse_id).city
    with TestClient(app) as client:
        client.headers.update(login(client)); warehouse, item, supplier = setup_catalog(client)
        second = post(client, "/warehouses", {"code": "QA-02", "name": "Kho thứ hai", "country": "Vietnam"})
        assert second.status_code == 201 and second.json()["id"] != warehouse
        assert client.get(BASE + "/warehouses").json()["total"] == 2
        catalog = client.get(BASE + "/products?search=DEMO").json()
        assert catalog["total"] == 1 and catalog["items"][0]["id"] == item
        order = confirm(client, draft(client, warehouse, item, supplier))
        assert client.patch(BASE + f"/products/{item}", json={"name": "Ngừng nhập mới", "active": False,
            "expected_version": 1, "reason": "Ngừng kinh doanh"}).status_code == 200
        forbidden = post(client, "/orders", {"supplier_id": supplier, "ordered_on": str(service.today()),
            "lines": [{"item_id": item, "warehouse_id": warehouse, "quantity": 1}]})
        assert forbidden.status_code == 409
        assert post(client, f'/orders/{order["id"]}/receipts', receipt_body(order, 10)).status_code == 201
    with sessions() as session:
        original = session.get(Item, 1)
        assert (original.warehouse_id, original.sku, original.product_type, original.first_seen_date) == identity
        assert session.get(SourceWarehouse, original.warehouse_id).city == original_city
