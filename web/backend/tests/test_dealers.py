"""Dealer request flow on real PostgreSQL; synthetic data only. Business flow is a team assumption."""
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from modules.operations import service
from modules.operations.models import StockBalance, StockDocument
from test_auth import auth_app, login  # noqa: F401
from test_operations import BASE, post, setup_catalog, movement

DEALERS = "/api/v1/dealers"
PORTAL = "/api/v1/dealer"


def write(client, path, body, key=None):
    return client.post(path, json=body, headers={"Idempotency-Key": key or str(uuid.uuid4())})


def stocked(admin, quantity=10):
    warehouse, item, _ = setup_catalog(admin)
    assert post(admin, "/counts", movement(warehouse, item, quantity)).status_code == 201
    return warehouse, item


def test_dealer_request_flow_issues_stock_and_scopes_each_dealer(auth_app):
    app, sessions = auth_app
    with TestClient(app) as admin, TestClient(app) as a, TestClient(app) as b:
        admin.headers.update(login(admin)); a.headers.update(login(a, "partner-a")); b.headers.update(login(b, "partner-b"))
        warehouse, item = stocked(admin)
        products = a.get(PORTAL + "/products").json()["items"]
        assert [(p["item_id"], p["available_qty"]) for p in products] == [(item, 10)]
        assert "warehouse" not in products[0]
        body = {"note": "Bổ sung tuần này", "lines": [{"item_id": item, "quantity": 4}]}
        created = write(a, PORTAL + "/requests", body, "dealer-a-1")
        replay = write(a, PORTAL + "/requests", body, "dealer-a-1")
        assert created.status_code == 201 and replay.status_code == 200 and replay.json()["id"] == created.json()["id"]
        request = created.json()
        assert request["status"] == "submitted" and request["lines"][0]["quantity"] == 4
        # Another dealer cannot see, cancel or receive it; a caller-supplied dealer id is ignored.
        assert b.get(PORTAL + "/requests").json()["total"] == 0
        assert b.get(PORTAL + "/requests?dealer_id=" + str(request["dealer_id"])).json()["total"] == 0
        assert b.get(f'{PORTAL}/requests/{request["id"]}').status_code == 404
        assert b.post(f'{PORTAL}/requests/{request["id"]}/cancel', json={"expected_version": 1}).status_code == 404
        assert a.post(f'{DEALERS}/requests/{request["id"]}/approve', json={"expected_version": 1}).status_code == 403
        issue = {"expected_version": 1, "warehouse_id": warehouse, "occurred_on": str(service.today())}
        assert write(admin, f'{DEALERS}/requests/{request["id"]}/issue', issue).status_code == 409  # not approved yet
        assert admin.get(BASE + "/summary").json()["pending_dealer_requests"] == 1
        approved = admin.post(f'{DEALERS}/requests/{request["id"]}/approve', json={"expected_version": 1})
        assert approved.status_code == 200 and approved.json()["status"] == "approved"
        assert a.post(f'{PORTAL}/requests/{request["id"]}/cancel', json={"expected_version": 2}).status_code == 409
        issued = write(admin, f'{DEALERS}/requests/{request["id"]}/issue', {**issue, "expected_version": 2}, "issue-1")
        again = write(admin, f'{DEALERS}/requests/{request["id"]}/issue', {**issue, "expected_version": 2}, "issue-1")
        assert issued.status_code == 200 and issued.json()["status"] == "issued" and again.json()["version"] == issued.json()["version"]
        assert admin.get(BASE + "/stock").json()["items"][0]["on_hand_qty"] == 6
        assert a.get(PORTAL + "/stock").json()["total"] == 0  # not received yet
        received = a.post(f'{PORTAL}/requests/{request["id"]}/receive', json={"expected_version": 3})
        assert received.status_code == 200 and received.json()["status"] == "received"
        assert [(r["item_id"], r["received_qty"]) for r in a.get(PORTAL + "/stock").json()["items"]] == [(item, 4)]
        assert b.get(PORTAL + "/stock").json()["total"] == 0
        assert admin.get(DEALERS + "/requests?status=received").json()["total"] == 1
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(StockDocument).where(StockDocument.kind == "issue")) == 1
        assert session.scalar(select(StockBalance.on_hand_qty)) == 6


def test_reject_cancel_insufficient_stock_and_inactive_dealer(auth_app):
    app, _ = auth_app
    with TestClient(app) as admin, TestClient(app) as a:
        admin.headers.update(login(admin)); a.headers.update(login(a, "partner-a"))
        warehouse, item = stocked(admin, 3)
        first = write(a, PORTAL + "/requests", {"lines": [{"item_id": item, "quantity": 2}]}).json()
        assert a.post(f'{PORTAL}/requests/{first["id"]}/cancel', json={"expected_version": 1}).json()["status"] == "cancelled"
        second = write(a, PORTAL + "/requests", {"lines": [{"item_id": item, "quantity": 2}]}).json()
        rejected = admin.post(f'{DEALERS}/requests/{second["id"]}/reject', json={"expected_version": 1, "reason": "Hết hạn mức"})
        assert rejected.json()["status"] == "rejected" and rejected.json()["reject_reason"] == "Hết hạn mức"
        big = write(a, PORTAL + "/requests", {"lines": [{"item_id": item, "quantity": 5}]}).json()
        admin.post(f'{DEALERS}/requests/{big["id"]}/approve', json={"expected_version": 1})
        short = write(admin, f'{DEALERS}/requests/{big["id"]}/issue', {"expected_version": 2, "warehouse_id": warehouse, "occurred_on": str(service.today())})
        assert short.status_code == 409 and short.json()["error"]["code"] == "insufficient_stock"
        assert admin.get(f'{DEALERS}/requests/{big["id"]}').json()["status"] == "approved"  # rolled back
        assert write(a, PORTAL + "/requests", {"lines": [{"item_id": item, "quantity": 1}, {"item_id": item, "quantity": 1}]}).status_code == 422
        dealer = admin.get(DEALERS).json()["items"][0]
        assert admin.patch(f'{DEALERS}/{dealer["id"]}', json={"name": dealer["name"], "contact": "", "active": False,
            "expected_version": dealer["version"]}).status_code == 200
        assert write(a, PORTAL + "/requests", {"lines": [{"item_id": item, "quantity": 1}]}).status_code == 409


def test_admin_creates_dealer_with_unique_code(auth_app):
    app, _ = auth_app
    with TestClient(app) as admin:
        admin.headers.update(login(admin))
        created = admin.post(DEALERS, json={"code": "DL-HN", "name": "Đại lý Hà Nội", "contact": "0900000000"})
        assert created.status_code == 201 and created.json()["active"] is True
        assert admin.post(DEALERS, json={"code": "DL-HN", "name": "Trùng"}).status_code == 409
        assert admin.get(DEALERS + "?active=true").json()["total"] == 3


def test_dealer_catalog_filters_put_available_products_first(auth_app):
    app, _ = auth_app
    with TestClient(app) as admin, TestClient(app) as a:
        admin.headers.update(login(admin)); a.headers.update(login(a, "partner-a"))
        warehouse, item = stocked(admin, 6)
        empty = post(admin, "/products", {"name": "SIM chưa có hàng", "sku": "DEMO-PSIM-02", "product_type": "physical_SIM",
            "carrier": "OtherCarrier", "destination_country": "OtherLand"}).json()["id"]
        rows = a.get(PORTAL + "/products").json()["items"]
        assert [r["item_id"] for r in rows] == [item, empty]
        assert (rows[0]["carrier"], rows[0]["destination_country"]) == ("DemoCarrier", "DemoLand")
        listed = lambda **params: [r["item_id"] for r in a.get(PORTAL + "/products", params=params).json()["items"]]
        assert listed(in_stock="true") == [item]
        assert listed(product_type="physical_SIM") == listed(country="OtherLand") == listed(carrier="OtherCarrier") == [empty]
        assert a.get(PORTAL + "/product-filters").json() == {"countries": ["DemoLand", "OtherLand"], "carriers": ["DemoCarrier", "OtherCarrier"]}
