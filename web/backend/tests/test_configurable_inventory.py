"""Hand calculations, causal windows and a real synthetic worker/PG reconciliation."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import csv
import hashlib
import io
import json
import uuid

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update, text

from core.errors import DomainError
from core.hashes import digest
from main import create_app
from modules.forecasting.models import DailySales, ItemForecast
from modules.inventory.models import InventoryDaily
from modules.inventory.service import PolicyValues, recommend
from modules.inventory.simulation import history_at, pure_window
from modules.runs.models import Run
from modules.runs.verification import verify_run
from src.data import SOURCE_COLUMNS
from test_postgres_api import D, request, settings
from test_results_api import result_fixture
from test_simulation import inputs, ORIGIN
from worker import serve


F = [2] * 7 + [4] + [6] * 6
P = PolicyValues(10, 5, 2, safety_lookback_days=7, safety_factor=2, safety_multiplier=1.5)


@pytest.mark.parametrize("safety,rop,ss,threshold,q", [
    ("days", "fixed", 12, 10, 5),
    ("days", "forecast", 12, 26, 19),
    ("volatility", "fixed", 16, 10, 5),
    ("volatility", "forecast", 16, 30, 23),
])
def test_four_modes_match_hand_calculation(safety, rop, ss, threshold, q):
    # mean(f14)=27/7; std_population(0..6)=2, not sample std.
    row = recommend(F, 8, 3, replace(P, safety_mode=safety, rop_mode=rop), list(range(7)))
    assert (row["ss"], row["rop_forecast"], row["rop"], row["target_stock"]) == (ss, 14 + ss, threshold, threshold + 4)
    assert (row["inventory_position"], row["needs_replenishment"], row["recommended_qty"]) == (11, True, q)


@pytest.mark.parametrize("multiplier,ss", [(0, 0), (0.5, 4), (1, 8), (1.5, 12), (10, 78)])
def test_legacy_days_multiplier_parity(multiplier, ss):
    # safety_days=2, mean(f14)=27/7; keep the original multiplication/ceiling.
    row = recommend(F, 0, 0, replace(P, safety_multiplier=multiplier))
    assert (row["ss"], row["rop_forecast"], row["rop"], row["target_stock"], row["recommended_qty"]) == (ss, 14 + ss, 14 + ss, 18 + ss, 18 + ss)


@pytest.mark.parametrize("safety", ["days", "volatility"])
@pytest.mark.parametrize("rop", ["fixed", "forecast"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_strict_trigger_uses_closing_and_pending_only_changes_order(safety, rop, offset):
    policy = replace(P, safety_mode=safety, rop_mode=rop)
    threshold = (10 if rop == "fixed" else 26 if safety == "days" else 30)
    row = recommend(F, threshold + offset, 1000, policy, list(range(7)))
    assert row["needs_replenishment"] is (offset < 0)
    assert row["recommended_qty"] == 0
    assert row["inventory_position"] == threshold + offset + 1000
    if offset < 0:
        assert row["state"] == "pending_covers"


@pytest.mark.parametrize("days", [7, 28, 90])
@pytest.mark.parametrize("value", [0, 10])
def test_constant_and_zero_observed_sales_are_valid(days, value):
    policy = replace(P, safety_mode="volatility", safety_lookback_days=days)
    assert recommend(F, 0, 0, policy, [value] * days)["ss"] == 0


@pytest.mark.parametrize("bad", [None, [0] * 6, [0] * 8, [0] * 6 + [None],
    [0] * 6 + [np.nan], [0] * 6 + [np.inf], [0] * 6 + [-1],
    [0] * 6 + [0.5], [0] * 6 + [True], [0] * 6 + [2**63], [[0]] * 7])
def test_missing_or_invalid_observations_are_never_zero_filled(bad):
    # Even zero scaling does not waive the observed-window contract.
    policy = replace(P, safety_mode="volatility", safety_multiplier=0)
    with pytest.raises(DomainError) as exc:
        recommend(F, 0, 0, policy, bad)
    assert exc.value.code == "insufficient_history"


def test_zero_multiplier_factor_and_large_integer_population_std():
    policy = replace(P, safety_mode="volatility")
    assert recommend(F, 0, 0, replace(policy, safety_factor=0), list(range(7)))["ss"] == 0
    assert recommend(F, 0, 0, replace(policy, safety_multiplier=0), list(range(7)))["ss"] == 0
    assert recommend(F, 0, 0, replace(policy, safety_factor=1e308), [2] * 7)["ss"] == 0
    maximum = 2**63 - 1
    policy = PolicyValues(0, 1, 0, safety_mode="volatility", safety_lookback_days=28)
    # Exact integer variance is 1/4 even near bigint max; float centering loses it.
    assert recommend([0] * 14, 0, 0, policy, [maximum, maximum - 1] * 14)["ss"] == 2


@pytest.mark.parametrize("change", [dict(safety_mode="bad"), dict(rop_mode="bad"),
    dict(safety_lookback_days=6), dict(safety_lookback_days=91), dict(safety_lookback_days=True),
    dict(safety_factor=np.nan), dict(safety_factor=-1), dict(safety_factor=True),
    dict(safety_multiplier=np.inf), dict(safety_multiplier=11)])
def test_pure_policy_validates_frozen_parameters(change):
    with pytest.raises(DomainError):
        replace(P, **change)


@pytest.mark.parametrize("case", ["days", "volatility", "forecast_sum", "target", "position"])
def test_numeric_overflow_is_explicit(case):
    policy, f, closing, pending, history = P, F, 0, 0, list(range(7))
    if case == "days":
        policy = replace(P, safety_days=1e308)
    elif case == "volatility":
        policy = replace(P, safety_mode="volatility", safety_factor=1e308)
    elif case == "forecast_sum":
        f = [1e308] * 14
    elif case == "target":
        policy = replace(P, rop_mode="fixed", configured_rop_floor=2**63 - 1)
    else:
        closing, pending = 2**63 - 1, 1
    with pytest.raises(DomainError) as exc:
        recommend(f, closing, pending, policy, history)
    assert exc.value.code == "numeric_overflow"


def configured_inputs():
    args = list(inputs())
    args[4][0].update(safety_mode="volatility", safety_lookback_days=7, safety_factor=1, configured_rop_floor=0)
    args[0].loc[pd.date_range(ORIGIN - timedelta(days=6), ORIGIN), 1] = list(range(7))
    return args


def test_future_mutation_cannot_change_an_origin_decision():
    args = configured_inputs()
    before = pure_window(*args, "stock_projection", ORIGIN, ORIGIN)
    args[0].loc[args[0].index > pd.Timestamp(ORIGIN), 1] = np.nan
    assert digest(pure_window(*args, "stock_projection", ORIGIN, ORIGIN)) == digest(before)
    assert before["ledger"][0]["ss"] == 6
    # Data before the seven-day window may affect initial stock, but never this SS.
    args[0].loc[args[0].index < pd.Timestamp(ORIGIN - timedelta(days=6)), 1] = 100
    assert pure_window(*args, "stock_projection", ORIGIN, ORIGIN)["ledger"][0]["ss"] == 6


def test_policy_replay_advances_cutoff_but_alert_replay_keeps_origin():
    args = configured_inputs()
    policy = pure_window(*args, "policy_replay", ORIGIN, ORIGIN + timedelta(days=14))
    alert = pure_window(*args, "alert_replay", ORIGIN, ORIGIN + timedelta(days=14))
    # Day+1 uses [1,2,3,4,5,6,10]: variance=376/49, SS=ceil(sqrt(376/7))=8.
    assert [r["ss"] for r in policy["ledger"][:2]] == [6, 8]
    assert {r["ss"] for r in alert["ledger"]} == {6}
    assert not alert["orders"]


def test_calendar_gaps_duplicates_and_insufficient_long_window_fail():
    args = configured_inputs()
    assert history_at(args[0], 1, ORIGIN, 7) == list(range(7))
    for matrix in [args[0].drop(pd.Timestamp(ORIGIN)), pd.concat([args[0], args[0].loc[[pd.Timestamp(ORIGIN)]]])]:
        with pytest.raises(DomainError, match="observed|Observed"):
            history_at(matrix, 1, ORIGIN, 7)
    args[4][0]["safety_lookback_days"] = 90
    with pytest.raises(DomainError) as exc:
        pure_window(*args, "stock_projection", ORIGIN, ORIGIN)
    assert exc.value.code == "insufficient_history"


def worker_fixture(sessions, tmp_path):
    """Only synthetic parents/forecasts are injected; audit, simulation and verifier run for real."""
    source, forecast, item = result_fixture(sessions)
    raw = tmp_path / "data/sigma_sim_data_orders.csv"
    raw.parent.mkdir()
    days = [D + timedelta(days=h) for h in range(-89, 15)]
    counts = {day: ((day - D).days + 6) % 7 if day <= D else 10 for day in days}
    with raw.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=SOURCE_COLUMNS)
        writer.writeheader()
        for day, qty in counts.items():
            if not qty:
                continue
            row = {k: "synthetic" for k in SOURCE_COLUMNS}
            row.update(order_id="SYN-" + str(day), customer_id="SYN-ONLY", order_datetime=str(day) + "T12:00:00Z",
                activation_datetime="", product_type="eSIM", destination_country="DemoLand", carrier="DemoCarrier",
                sku="DEMO-ESIM-01", order_status="success", quantity=qty,
                unit_price_vnd=1, unit_cost_vnd=0, gross_revenue_vnd=qty)
            writer.writerow(row)
    with sessions.begin() as s:
        source_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
        s.get(Run, source).source_sha256 = source_hash
        s.get(Run, forecast).source_sha256 = source_hash
        s.execute(delete(DailySales).where(DailySales.source_import_run_id == source))
        s.execute(delete(ItemForecast).where(ItemForecast.run_id == forecast))
        s.add_all([DailySales(source_import_run_id=source, item_id=item, date=day, sales_qty=qty,
                             order_count=int(qty > 0), actual_available=True) for day, qty in counts.items()])
        # An unknown label outside every used window must not block a decision.
        s.add(DailySales(source_import_run_id=source, item_id=item, date=D + timedelta(days=40),
                         sales_qty=None, order_count=None, actual_available=False))
        s.add_all([ItemForecast(run_id=forecast, item_id=item, as_of_date=origin, target_date=origin + timedelta(days=h),
            horizon_day=h, forecast_qty=f, actual_qty=None, actual_available=False, item_share=1,
            weekday_weight=1/7, share_window_days=30, allocation_basis="injected_synthetic")
            for origin in days if origin >= D for h, f in enumerate(F, 1)])
    return source, forecast, item


def enqueue_fixture(c, source, forecast, item, safety, rop, kind, lookback=7):
    policy = request(item, 1).model_dump(mode="json")
    policy.update(configured_rop_floor=10, fixed_order_qty=5)
    assert c.post("/api/v1/supplier-item-policies", json=policy).status_code == 201
    scenario = dict(name="Synthetic calculation", code="calculation", settings=dict(
        cover_days=7, safety_multiplier=1.5, receipts_declared=True,
        receipts_initial=[dict(item_id=item, ordered_on=str(D - timedelta(days=3)), eta=str(D + timedelta(days=4)),
                               ordered_qty=20, lot_key="synthetic-incoming")],
        policy_overrides=[dict(item_id=item, safety_mode=safety, rop_mode=rop, safety_lookback_days=lookback, safety_factor=2)],
    ))
    response = c.post("/api/v1/scenarios", json=scenario)
    assert response.status_code == 201
    body = dict(kind=kind, source_import_run_id=str(source), forecast_run_id=str(forecast),
                scenario_id=response.json()["id"], as_of_date=str(D))
    if kind.endswith("replay"):
        body.update(period_start=str(D + timedelta(days=1)), period_end=str(D + timedelta(days=14)))
    response = c.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "synthetic-calculation"})
    assert response.status_code == 202
    return uuid.UUID(response.json()["run_id"])


@pytest.mark.parametrize("safety,rop", [("days", "fixed"), ("days", "forecast"), ("volatility", "fixed"), ("volatility", "forecast")])
@pytest.mark.parametrize("kind", ["stock_projection", "policy_replay", "alert_replay"])
def test_worker_verifies_all_modes_and_replay_kinds(pg, tmp_path, safety, rop, kind):
    _, sessions = pg
    source, forecast, item = worker_fixture(sessions, tmp_path)
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as c:
        key = enqueue_fixture(c, source, forecast, item, safety, rop, kind)
        with sessions() as s:
            snapshot = deepcopy(s.get(Run, key).config_snapshot)
            checksum = s.get(Run, key).config_sha256
        assert serve(cfg, once=True) == key
        with sessions() as s:
            row = s.get(Run, key)
            assert row.status == "complete", row.error_code
            assert row.result_summary["verification"]["status"] == "verified"
            assert row.result_summary["verification"]["thresholds_checked"] == (1 if kind == "stock_projection" else 15)
            assert row.config_snapshot == snapshot and row.config_sha256 == checksum
        manifest = json.loads((cfg.output_root / str(key) / "manifest.json").read_text())
        assert manifest["status"] == "verified"
        rows = c.get(f"/api/v1/runs/{key}/inventory").json()["items"]
        first = rows[0]
        assert first["fixed_order_qty"] == 5 and first["moq"] is None
        with sessions() as s:
            snapshot_policy = s.get(Run, key).config_snapshot["policies"][0]
            assert snapshot_policy["fixed_order_qty"] == 5 and snapshot_policy["moq"] is None
            orders = s.execute(text("SELECT ordered_qty FROM replenishment_orders WHERE run_id=:key AND NOT is_initial"), {"key":key}).scalars().all()
            assert all(q == 5 for q in orders)
        expected_ss = 12 if safety == "days" else 16
        assert (first["ss"], first["rop_forecast"], first["rop"]) == (
            expected_ss, 14 + expected_ss, 10 if rop == "fixed" else 14 + expected_ss)
        assert first["pending_qty"] == 20
        exported = c.get(f"/api/v1/runs/{key}/exports/inventory_daily")
        assert exported.status_code == 200
        csv_first = next(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        assert int(csv_first["fixed_order_qty"]) == 5
        assert int(csv_first["ss"]) == expected_ss and int(csv_first["rop"]) == first["rop"]
        if (safety, rop, kind) == ("days", "forecast", "policy_replay"):
            with sessions.begin() as s:
                changed = s.scalar(select(InventoryDaily).where(InventoryDaily.run_id == key, InventoryDaily.recommended_qty > 0).order_by(InventoryDaily.date))
                assert changed is not None
                changed_id, original_qty = changed.id, changed.recommended_qty
                changed.recommended_qty += 1
            with pytest.raises(DomainError, match="thresholds differ"):
                verify_run(cfg, sessions, key)
            with sessions.begin() as s:
                s.get(InventoryDaily, changed_id).recommended_qty = original_qty
        if (safety, rop, kind) == ("volatility", "fixed", "policy_replay"):
            with sessions.begin() as s:
                record = s.scalar(select(InventoryDaily).where(InventoryDaily.run_id == key, InventoryDaily.date == D))
                record.ss += 1
            with pytest.raises(DomainError, match="thresholds differ"):
                verify_run(cfg, sessions, key, allow_running=True)
            with sessions.begin() as s:
                s.execute(update(InventoryDaily).where(InventoryDaily.run_id == key, InventoryDaily.date == D)
                          .values(ss=expected_ss, forecast_as_of_date=D + timedelta(days=1)))
            with pytest.raises(DomainError, match="cutoff"):
                verify_run(cfg, sessions, key, allow_running=True)


def test_worker_missing_observed_long_history_fails_without_partial_ledger(pg, tmp_path):
    _, sessions = pg
    source, forecast, item = worker_fixture(sessions, tmp_path)
    with sessions.begin() as s:
        s.execute(update(DailySales).where(DailySales.source_import_run_id == source, DailySales.date == D - timedelta(days=40))
                  .values(sales_qty=None, order_count=None, actual_available=False))
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as c:
        key = enqueue_fixture(c, source, forecast, item, "volatility", "fixed", "stock_projection", 90)
        assert serve(cfg, once=True) == key
        with sessions() as s:
            row = s.get(Run, key)
            assert row.status == "failed" and row.error_code == "insufficient_history"
            assert not s.scalars(select(InventoryDaily).where(InventoryDaily.run_id == key)).all()
        assert c.get(f"/api/v1/runs/{key}/inventory").status_code == 409
