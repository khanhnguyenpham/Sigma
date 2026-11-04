"""Receiving defaults, immutable source identity and independent verification."""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from core.errors import DomainError
from main import create_app
from modules.catalog.models import Warehouse
from modules.catalog.receiving import update_receiving
from modules.catalog.schemas import ReceivingWarehouseUpdate
from modules.inventory.simulation import pure_window
from modules.runs.models import Run
from modules.runs.receiving_verification import verify_receiving_snapshot
from modules.runs.verification import verify_run
from test_simulation import inputs, ORIGIN
from test_configurable_inventory import worker_fixture, enqueue_fixture
from test_postgres_api import settings, D
from test_results_api import result_fixture
from worker import serve


def add_warehouse(sessions):
    with sessions.begin() as session:
        row = Warehouse(code="RECEIVING", city="Receiving City", destination_country="Other Market",
                        carrier="DemoCarrier", assumption_source="synthetic_fixture")
        session.add(row)
        session.flush()
        return row.id


def test_product_default_version_noop_invalid_and_legacy_run_preservation(pg, tmp_path):
    _, sessions = pg
    _, _, item_id = result_fixture(sessions)
    target = add_warehouse(sessions)
    with sessions() as session:
        before = {r.id: (deepcopy(r.config_snapshot), r.config_sha256) for r in session.scalars(select(Run))}
    with TestClient(create_app(settings(tmp_path))) as client:
        path = f"/api/v1/products/{item_id}"
        original = client.get(path).json()
        assert original["receiving_warehouse_id"] == original["warehouse_id"] == 1
        assert original["receiving_source"] == "inherited" and original["receiving_version"] == 0
        body = dict(receiving_warehouse_id=target, expected_version=0)
        assert client.patch(path + "/receiving-warehouse", json=body).status_code == 200
        saved = client.get(path).json()
        assert saved["warehouse_id"] == 1 and saved["receiving_warehouse_id"] == target
        assert saved["receiving_warehouse"]["city"] == "Receiving City" and saved["receiving_version"] == 1
        assert saved["carrier"] == original["carrier"] and saved["destination_country"] == original["destination_country"]
        assert client.patch(path + "/receiving-warehouse", json=body).status_code == 409
        body["expected_version"] = 1
        assert client.patch(path + "/receiving-warehouse", json=body).json()["receiving_version"] == 1
        assert client.patch(path + "/receiving-warehouse", json={**body, "receiving_warehouse_id": 999}).status_code == 404
        assert client.patch(path + "/receiving-warehouse", json={**body, "receiving_warehouse_id": True}).status_code == 422
    with sessions() as session:
        assert {r.id: (r.config_snapshot, r.config_sha256) for r in session.scalars(select(Run))} == before


@pytest.mark.parametrize("kind", ["stock_projection", "policy_replay", "alert_replay"])
def test_worker_freezes_default_and_counts_stock_only_at_receiving_warehouse(pg, tmp_path, kind):
    _, sessions = pg
    source, forecast, item_id = worker_fixture(sessions, tmp_path)
    target = add_warehouse(sessions)
    with sessions.begin() as session:
        update_receiving(session, item_id, ReceivingWarehouseUpdate(receiving_warehouse_id=target, expected_version=0))
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        run_id = enqueue_fixture(client, source, forecast, item_id, "days", "fixed", kind)
        with sessions.begin() as session:
            update_receiving(session, item_id, ReceivingWarehouseUpdate(receiving_warehouse_id=1, expected_version=1))
        serve(cfg, once=True)
        assert verify_run(cfg, sessions, run_id)["status"] == "verified"
        rows = client.get(f"/api/v1/runs/{run_id}/inventory?receiving_warehouse_id={target}").json()
        assert rows["total"] and all(r["warehouse_id"] == 1 and r["receiving_warehouse_id"] == target for r in rows["items"])
        assert client.get(f"/api/v1/runs/{run_id}/inventory?receiving_warehouse_id=1").json()["total"] == 0
        signals = client.get(f"/api/v1/runs/{run_id}/alerts?receiving_warehouse_id={target}")
        assert signals.status_code == 200
        assert all(r["receiving_warehouse_id"] == target for r in signals.json()["items"])
        stock = client.get(f"/api/v1/runs/{run_id}/workspace?as_of_date={D}").json()["warehouse_stock"]
        assert len(stock) == 1 and stock[0]["warehouse_id"] == target
        assert client.get(f"/api/v1/runs/{run_id}/exports/inventory_daily?receiving_warehouse_id={target}").status_code == 200
        assert client.get(f"/api/v1/products/{item_id}").json()["receiving_warehouse_id"] == 1


def test_receiving_location_does_not_change_simulated_quantities_and_tampered_orders_fail():
    end = ORIGIN + timedelta(days=14)
    legacy = pure_window(*inputs(), "policy_replay", ORIGIN, end)
    located = pure_window(*inputs(), "policy_replay", ORIGIN, end, receiving={1: 2})
    assert located["ledger"] == legacy["ledger"] and located["events"] == legacy["events"]
    assert located["summary"] == legacy["summary"] and located["orders"]
    assert all(r["receiving_warehouse_id"] == 2 for r in located["orders"])
    assert [{k:v for k,v in r.items() if k != "receiving_warehouse_id"} for r in located["orders"]] == legacy["orders"]
    snap = dict(warehouse_snapshot=[dict(id=1, destination_country="A", carrier="C"), dict(id=2, destination_country="B", carrier="C")],
        catalog_snapshot=[dict(item_id=1, destination_country="A", carrier="C", first_seen_date=str(ORIGIN))],
        receiving_warehouse_profile="product_default_receiving_v1",
        receiving_warehouse_snapshot=[dict(item_id=1, source_warehouse_id=1, receiving_warehouse_id=2, receiving_version=1)])
    run = SimpleNamespace(as_of_date=ORIGIN, period_end=end, kind="policy_replay", config_snapshot=snap)
    assert verify_receiving_snapshot(run) == {1: 2}
    with pytest.raises(DomainError, match="destinations differ"):
        verify_receiving_snapshot(run, pd.DataFrame([dict(item_id=1, receiving_warehouse_id=1)]))
    snap["receiving_warehouse_snapshot"].append(deepcopy(snap["receiving_warehouse_snapshot"][0]))
    with pytest.raises(DomainError):
        verify_receiving_snapshot(run)
