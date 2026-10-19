"""Synthetic fixtures in the dedicated PostgreSQL test DB; no private source records."""

from datetime import timedelta
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sigma_m3.main import create_app
from sigma_m3.models import (
    Run,
    DailySales,
    RouteForecast,
    ItemForecast,
    Item,
    Warehouse,
)
from sigma_m3.schemas import RunCreate
from sigma_m3.services.runs import enqueue, digest, source_data_id
from sigma_m3.services.ingestion import import_snapshot
from test_postgres_api import seed, settings, D


def result_fixture(sessions):
    item, _, _ = seed(sessions)
    with sessions.begin() as s:
        source, _ = enqueue(
            s,
            RunCreate(
                kind="source_import",
                source_key="orders_snapshot",
                as_of_date="2025-12-31",
            ),
            "source",
        )
        source.status = "complete"
        source.source_sha256 = "a" * 64
        source.config_snapshot = {
            **source.config_snapshot,
            "catalog_snapshot": [
                dict(
                    item_id=item,
                    destination_country="DemoLand",
                    carrier="DemoCarrier",
                    sku="DEMO-ESIM-01",
                    product_type="eSIM",
                    first_seen_date="2024-01-01",
                )
            ],
            "warehouse_snapshot": [
                dict(
                    id=1,
                    code="DEMO-W1",
                    destination_country="DemoLand",
                    carrier="DemoCarrier",
                    city="Frozen City",
                )
            ],
        }
        source.config_sha256 = digest(source.config_snapshot)
        s.flush()
        forecast, _ = enqueue(
            s,
            RunCreate(
                kind="forecast",
                source_import_run_id=source.id,
                as_of_date="2025-12-31",
                mode="replay",
            ),
            "forecast",
        )
        forecast.status = "complete"
        forecast.config_snapshot = {
            **forecast.config_snapshot,
            **{
                k: source.config_snapshot[k]
                for k in ["catalog_snapshot", "warehouse_snapshot"]
            },
        }
        forecast.config_sha256 = digest(forecast.config_snapshot)
        s.add_all(
            [
                RouteForecast(
                    run_id=forecast.id,
                    warehouse_id=1,
                    as_of_date=D,
                    block=1,
                    window_start=D + timedelta(days=1),
                    target_date=D + timedelta(days=7),
                    forecast_qty=7.5,
                    actual_qty=0,
                    actual_available=True,
                    family="synthetic",
                    model_id="fixture",
                    selection_basis="injected_fixture",
                ),
                ItemForecast(
                    run_id=forecast.id,
                    item_id=item,
                    as_of_date=D,
                    target_date=D + timedelta(days=1),
                    horizon_day=1,
                    forecast_qty=1.5,
                    actual_qty=0,
                    actual_available=True,
                    item_share=1,
                    weekday_weight=1 / 7,
                    share_window_days=30,
                    allocation_basis="synthetic",
                ),
                DailySales(
                    source_import_run_id=source.id,
                    item_id=item,
                    date=D + timedelta(days=1),
                    sales_qty=0,
                    order_count=0,
                    actual_available=True,
                ),
            ]
        )
        return source.id, forecast.id, item


def test_paginated_results_frozen_context_null_and_exports(pg, tmp_path):
    _, sessions = pg
    source, key, item = result_fixture(sessions)
    with sessions.begin() as s:
        s.get(Warehouse, 1).city = "Changed live city"
    with TestClient(create_app(settings(tmp_path))) as c:
        path = f"/api/v1/runs/{key}"
        result = c.get(path + "/forecasts/routes?as_of_date=2025-10-31&block=1").json()
        assert "context" in result, result
        assert result["context"]["run_id"] == str(key) and result["total"] == 1
        assert (
            result["items"][0]["city"] == "Frozen City"
            and result["items"][0]["actual_qty"] == 0
        )
        assert c.get(path + "/forecasts/routes?warehouse_id=999").json()["total"] == 0
        assert c.get(path + "/forecasts/routes?item_id=" + str(item)).status_code == 422
        assert c.get(path + "/forecasts/routes?unrecognized=1").status_code == 422
        assert c.get(path + "/inventory").status_code == 409
        csv = c.get(
            path + "/exports/route_forecasts?warehouse_id=1&as_of_date=2025-10-31"
        )
        assert (
            csv.status_code == 200
            and "config_sha256" in csv.text
            and "Frozen City" in csv.text
            and str(key) in csv.text
        )
        assert c.get(path + "/exports/raw_orders").status_code == 404
        assert (
            c.get(path + "/forecasts/items?aggregate=route_day").json()["items"][0][
                "actual_qty"
            ]
            == 0
        )
        # A new source item not yet allocated at this origin still counts in route actuals.
        with sessions.begin() as s:
            other = Item(
                warehouse_id=1,
                sku="NEW-SKU",
                product_type="eSIM",
                first_seen_date=D + timedelta(days=1),
            )
            s.add(other)
            s.flush()
            s.add(
                DailySales(
                    source_import_run_id=source,
                    item_id=other.id,
                    date=D + timedelta(days=1),
                    sales_qty=9,
                    order_count=1,
                    actual_available=True,
                )
            )
            r = s.get(Run, source)
            catalog = r.config_snapshot["catalog_snapshot"] + [
                dict(
                    item_id=other.id,
                    destination_country="DemoLand",
                    carrier="DemoCarrier",
                    sku="NEW-SKU",
                    product_type="eSIM",
                    first_seen_date="2025-11-01",
                )
            ]
            # Explicitly rebuild this disposable fixture's frozen snapshots, never a real run.
            r.config_snapshot = {**r.config_snapshot, "catalog_snapshot": catalog}
            r.config_sha256 = digest(r.config_snapshot)
            f = s.get(Run, key)
            f.config_snapshot = {
                **f.config_snapshot,
                "catalog_snapshot": catalog,
                "source_parent_config_sha256": r.config_sha256,
            }
            f.config_sha256 = digest(f.config_snapshot)
        assert (
            c.get(path + "/forecasts/items?aggregate=route_day").json()["items"][0][
                "actual_qty"
            ]
            == 9
        )


def test_parent_invalidation_blocks_results(pg, tmp_path):
    _, sessions = pg
    source, key, _ = result_fixture(sessions)
    with sessions.begin() as s:
        s.get(Run, source).status = "invalidated"
    with TestClient(create_app(settings(tmp_path))) as c:
        assert c.get(f"/api/v1/runs/{key}/forecasts/routes").status_code == 409


def test_source_hash_reuse_retains_request_identity_without_duplicate_daily(
    pg, tmp_path
):
    _, sessions = pg
    source, _, _ = result_fixture(sessions)
    cfg = settings(tmp_path)
    raw = tmp_path / "data/sigma_sim_data_orders.csv"
    raw.parent.mkdir()
    raw.write_bytes(b"SYNTHETIC DEDUP ONLY")
    with sessions.begin() as s:
        original = s.get(Run, source)
        original.source_sha256 = hashlib.sha256(raw.read_bytes()).hexdigest()
        original.result_summary = {"sales_quantity": 0, "daily_rows": 1}
        alias, _ = enqueue(
            s,
            RunCreate(
                kind="source_import",
                source_key="orders_snapshot",
                as_of_date="2025-12-31",
            ),
            "second-key",
        )
        key = alias.id
    summary = import_snapshot(cfg, sessions, key)
    assert summary["reused_source"] is True
    with sessions() as s:
        alias = s.get(Run, key)
        assert source_data_id(alias) == source and alias.id != source
        assert s.scalar(select(func.count()).select_from(DailySales)) == 1


def test_warehouse_optimistic_version_and_scenario_validation(pg, tmp_path):
    _, sessions = pg
    seed(sessions)
    with TestClient(create_app(settings(tmp_path))) as c:
        path = "/api/v1/warehouses/1"
        body = {"city": "New City", "expected_version": 1}
        assert c.patch(path, json=body).json()["version"] == 2
        assert c.patch(path, json=body).status_code == 409
        scenario = {
            "name": "Fixture",
            "code": "fixture",
            "settings": {
                "cover_days": 7,
                "safety_multiplier": 1,
                "policy_overrides": [],
                "receipts_initial": [],
                "receipts_declared": True,
            },
        }
        assert c.post("/api/v1/scenarios", json=scenario).json()["version"] == 1
        assert c.post("/api/v1/scenarios", json=scenario).json()["version"] == 2
        scenario["settings"]["receipts_initial"] = [
            {
                "item_id": 1,
                "ordered_on": "2025-09-30",
                "eta": "2025-10-08",
                "ordered_qty": 5,
                "lot_key": "late",
            }
        ]
        assert c.post("/api/v1/scenarios", json=scenario).status_code == 422
