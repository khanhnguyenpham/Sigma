"""Product management reads current configuration without changing recorded results."""
from copy import deepcopy
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from main import create_app
from modules.catalog.models import Item
from modules.runs.models import Run
from test_postgres_api import D, settings
from test_results_api import result_fixture


def test_products_pagination_search_and_missing_policy_are_independent_of_runs(pg, tmp_path):
    _, sessions = pg
    _, _, item = result_fixture(sessions)
    with sessions.begin() as session:
        session.add(Item(warehouse_id=1, sku="DEMO_100%", product_type="physical_SIM", first_seen_date=D))
    with TestClient(create_app(settings(tmp_path))) as client:
        page = client.get("/api/v1/products?page_size=1&page=2").json()
        assert page["total"] == 2 and len(page["items"]) == 1
        row = page["items"][0]
        assert row["sku"] == "DEMO_100%" and row["policy"] is None
        assert row["warehouse"]["city"] == "Demo City" and row["supplier_id"] == 1
        assert client.get("/api/v1/products?search=%25").json()["total"] == 1
        assert client.get("/api/v1/products?product_type=physical_SIM&warehouse_id=1").json()["total"] == 1
        assert client.get("/api/v1/products?warehouse_id=999").json()["total"] == 0
        assert client.get(f"/api/v1/products/{item}").json()["sku"] == "DEMO-ESIM-01"
        assert client.get("/api/v1/products/999").status_code == 404
        assert client.get("/api/v1/products?page=0").status_code == 422


def test_product_save_reads_latest_version_and_keeps_frozen_runs(pg, tmp_path):
    _, sessions = pg
    _, _, item = result_fixture(sessions)
    with sessions() as session:
        before = {r.id: (deepcopy(r.config_snapshot), r.config_sha256) for r in session.scalars(select(Run))}
    body = dict(item_id=item, supplier_id=1, effective_from=str(D), configured_rop_floor=10,
                fixed_order_qty=25, safety_days=2, expected_version=0)
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.post("/api/v1/supplier-item-policies", json=body).status_code == 201
        body.update(effective_from=str(D + timedelta(days=1)), fixed_order_qty=35, safety_days=3, expected_version=1)
        assert client.post("/api/v1/supplier-item-policies", json=body).status_code == 201
        latest = client.get(f"/api/v1/products/{item}").json()["policy"]
        assert latest["version"] == 2 and latest["fixed_order_qty"] == 35 and float(latest["safety_days"]) == 3
        assert client.get("/api/v1/products").json()["total"] == 1
        assert client.get("/api/v1/products").json()["items"][0]["policy"]["id"] == latest["id"]
        assert client.post("/api/v1/supplier-item-policies", json=body).status_code == 409
    with sessions() as session:
        assert {r.id: (r.config_snapshot, r.config_sha256) for r in session.scalars(select(Run))} == before


def test_edit_warehouse_updates_display_name_while_preserving_frozen_city(pg, tmp_path):
    _, sessions = pg
    source, forecast, item = result_fixture(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        warehouse = client.get("/api/v1/warehouses/1").json()
        assert warehouse["city"] == "Demo City" and warehouse["version"] == 1
        patch = dict(city="Updated City", expected_version=1)
        assert client.patch("/api/v1/warehouses/1", json=patch).status_code == 200
        assert client.patch("/api/v1/warehouses/1", json=patch).status_code == 409
        assert client.get("/api/v1/warehouses/999").status_code == 404
        assert client.get(f"/api/v1/products/{item}").json()["city"] == "Updated City"
        frozen = client.get(f"/api/v1/warehouses?run_id={source}").json()["items"][0]
        assert frozen["city"] == "Frozen City" and frozen["display_city"] == "Updated City"
        result = client.get(f"/api/v1/runs/{forecast}/forecasts/routes").json()["items"][0]
        assert result["city"] == "Frozen City" and result["display_city"] == "Updated City"
        with sessions() as session:
            assert session.get(Run, source).config_snapshot["warehouse_snapshot"][0]["city"] == "Frozen City"
