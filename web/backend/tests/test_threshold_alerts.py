"""Synthetic ROP crossings: hand boundaries, sealed API/CSV and reconciliation."""
from copy import deepcopy
from datetime import timedelta
import csv
import io
import json
import uuid

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError

from core.errors import DomainError
from main import create_app
from models import Base
from modules.alerts.models import Alert
from modules.alerts.service import project, project_threshold, threshold_metrics, replay_metrics
from modules.inventory.simulation import pure_window
from modules.runs.models import Run
from modules.runs.verification import verify_run
from test_configurable_inventory import worker_fixture
from test_postgres_api import D, request, settings
from test_results_api import result_fixture
from test_simulation import inputs, ORIGIN
from worker import serve


def crossing(stock=100, rop=50, n=7, receipts=None, f=None):
    path = project(ORIGIN, stock, f or [10] * 14, receipts or {})["projection"]
    return project_threshold(ORIGIN, stock, rop, n, path)


@pytest.mark.parametrize("stock,rop,n,day", [
    (49, 50, 7, None), (50, 50, 7, 1), (51, 50, 7, 1),
    (100, 50, 5, None), (100, 50, 6, 6), (100, 50, 7, 6),
    (100, 0, 14, None), (0, 0, 14, None), (0, 50, 14, None),
    (140, 10, 13, None), (140, 10, 14, 14),
])
def test_strict_origin_and_n_boundaries(stock, rop, n, day):
    assert crossing(stock, rop, n) == (ORIGIN + timedelta(days=day) if day else None)


@pytest.mark.parametrize("n", [0, 15, 7.0, True, None])
def test_warning_horizon_validation(n):
    with pytest.raises(DomainError):
        crossing(n=n)


def test_receipts_before_sale_and_first_crossing_survives_later_receipt():
    assert crossing(receipts={ORIGIN + timedelta(days=6): 100}) is None
    assert crossing(receipts={ORIGIN + timedelta(days=7): 100}) == ORIGIN + timedelta(days=6)
    assert crossing(stock=50, receipts={ORIGIN + timedelta(days=1): 20}) == ORIGIN + timedelta(days=3)


@pytest.mark.parametrize("kind", ["stock_projection", "alert_replay", "policy_replay"])
def test_simulation_signal_is_exclusive_from_current_low_and_deduplicated(kind):
    args = list(inputs())
    args[5]["cover_days"] = 14
    args[4][0].update(rop_mode="fixed", configured_rop_floor=100, warning_horizon_days=7)
    end = ORIGIN if kind == "stock_projection" else ORIGIN + timedelta(days=14)
    result = pure_window(*args, kind, ORIGIN, end)
    first = [r for r in result["alerts"] if r["as_of_date"] == ORIGIN]
    assert {r["alert_type"] for r in first} == {"depletion", "projected_below_rop"}
    threshold = next(r for r in first if r["alert_type"] == "projected_below_rop")
    assert threshold["predicted_threshold_date"] == ORIGIN + timedelta(days=5)
    assert threshold["predicted_depletion_date"] is None and threshold["lead_days"] is None
    assert threshold["explanation"]["thresholds"]["rop"] == 100
    assert threshold["explanation"]["receipts"] == []
    keys = {(r["window_origin"], r["item_id"], r["as_of_date"], r["alert_type"]) for r in result["alerts"]}
    assert len(keys) == len(result["alerts"])
    for row in result["ledger"]:
        types = {r["alert_type"] for r in result["alerts"] if r["as_of_date"] == row["date"]}
        assert not {"below_rop", "projected_below_rop"} <= types
    if kind == "alert_replay":
        metrics = threshold_metrics(result["threshold_cases"])
        assert metrics["TP"] == metrics["event_denominator"] == 1
        assert metrics["date_mae"] == 0
        assert len(result["cases"]) == 1
        assert replay_metrics(result["cases"])["event_denominator"] == 1


def test_threshold_receipts_causal_and_depletion_metric_is_unchanged_by_n():
    args = list(inputs())
    args[5]["cover_days"] = 14
    args[4][0].update(rop_mode="fixed", configured_rop_floor=100, warning_horizon_days=4)
    a = pure_window(*args, "alert_replay", ORIGIN, ORIGIN + timedelta(days=14))
    args[4][0]["warning_horizon_days"] = 5
    b = pure_window(*args, "alert_replay", ORIGIN, ORIGIN + timedelta(days=14))
    assert not any(r["alert_type"] == "projected_below_rop" for r in a["alerts"])
    assert any(r["alert_type"] == "projected_below_rop" for r in b["alerts"])
    assert a["cases"] == b["cases"] and replay_metrics(a["cases"]) == replay_metrics(b["cases"])
    args[5]["receipts_initial"] = [dict(item_id=1, lot_key="known", ordered_on=str(ORIGIN - timedelta(days=2)),
        eta=str(ORIGIN + timedelta(days=5)), ordered_qty=100)]
    c = pure_window(*args, "stock_projection", ORIGIN, ORIGIN)
    assert not any(r["alert_type"] == "projected_below_rop" for r in c["alerts"])
    args[5]["receipts_initial"][0]["ordered_on"] = str(ORIGIN + timedelta(days=1))
    with pytest.raises(DomainError, match="known"):
        pure_window(*args, "stock_projection", ORIGIN, ORIGIN)


def test_separate_threshold_confusion_exclusions_and_null_denominators():
    def case(pred, actual, eligible=True):
        return dict(predicted_threshold_date=ORIGIN + timedelta(days=pred) if pred else None,
                    actual_threshold_date=ORIGIN + timedelta(days=actual) if actual else None, is_evaluable=eligible)
    m = threshold_metrics([case(2, 3), case(2, None), case(None, 3), case(None, None), case(None, None, False)])
    assert {k:m[k] for k in ("TP", "FP", "FN", "TN")} == dict(TP=1, FP=1, FN=1, TN=1)
    assert (m["precision"], m["recall"], m["event_denominator"], m["excluded_count"], m["date_mae"]) == (.5, .5, 2, 1, 1)
    assert threshold_metrics([])["precision"] is None
    assert threshold_metrics([])["recall"] is None
    assert threshold_metrics([])["date_mae"] is None
    assert "early_rate" not in m
    args = list(inputs())  # stock70, ROP100: excluded only from threshold metric.
    r = pure_window(*args, "alert_replay", ORIGIN, ORIGIN + timedelta(days=14))
    assert threshold_metrics(r["threshold_cases"])["excluded_count"] == 1
    assert replay_metrics(r["cases"])["event_denominator"] == 1


def enqueue_threshold(client, source, forecast, item, kind, n=7):
    body = request(item, 1).model_dump(mode="json")
    body.update(rop_mode="fixed", configured_rop_floor=20, warning_horizon_days=n)
    assert client.post("/api/v1/supplier-item-policies", json=body).status_code == 201
    scenario = client.post("/api/v1/scenarios", json=dict(name="Threshold fixture", code="threshold", settings=dict(
        cover_days=7, safety_multiplier=1, policy_overrides=[], receipts_initial=[], receipts_declared=True))).json()
    payload = dict(kind=kind, source_import_run_id=str(source), forecast_run_id=str(forecast), scenario_id=scenario["id"], as_of_date=str(D))
    if kind.endswith("replay"):
        payload.update(period_start=str(D + timedelta(days=1)), period_end=str(D + timedelta(days=14)))
    response = client.post("/api/v1/runs", json=payload, headers={"Idempotency-Key":"synthetic-threshold"})
    assert response.status_code == 202
    assert client.post("/api/v1/runs", json=payload, headers={"Idempotency-Key":"synthetic-threshold"}).json()["run_id"] == response.json()["run_id"]
    return uuid.UUID(response.json()["run_id"])


@pytest.mark.parametrize("kind", ["stock_projection", "alert_replay", "policy_replay"])
def test_worker_threshold_api_csv_and_independent_tamper_checks(pg, tmp_path, kind):
    _, sessions = pg
    source, forecast, item = worker_fixture(sessions, tmp_path)
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as c:
        key = enqueue_threshold(c, source, forecast, item, kind)
        assert serve(cfg, once=True) == key
        with sessions() as s:
            run = s.get(Run, key)
            assert run.status == "complete", run.error_code
            summary = deepcopy(run.result_summary)
            checksum = run.config_sha256
        manifest = json.loads((cfg.output_root / str(key) / "manifest.json").read_text())
        assert manifest["status"] == "verified"
        path = f"/api/v1/runs/{key}"
        query = "?alert_type=projected_below_rop&state=threshold_warning&as_of_date=" + str(D)
        result = c.get(path + "/alerts" + query)
        assert result.status_code == 200, result.text
        rows = result.json()["items"]
        assert result.json()["total"] == len(rows) == 1
        row = rows[0]
        assert row["predicted_threshold_date"] == str(D + timedelta(days=1))
        assert row["predicted_depletion_date"] is row["actual_depletion_date"] is None
        assert row["is_evaluable"] == (kind == "alert_replay")
        exported = c.get(path + "/exports/alerts" + query)
        csv_rows = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        assert len(csv_rows) == 1 and csv_rows[0]["predicted_threshold_date"] == row["predicted_threshold_date"]
        assert csv_rows[0]["config_sha256"] == checksum
        assert c.get(path + "/alerts?alert_type=invalid").status_code == 422
        assert c.get(path + "/inventory?alert_type=depletion").status_code == 422
        if kind == "alert_replay":
            m = c.get(path + "/metrics?granularity=threshold").json()["items"]
            assert len(m) == 1 and m[0]["TP"] == m[0]["event_denominator"] == 1
            assert summary["alert_metrics"]["event_denominator"] == 1
            assert c.get(path + "/alert-opportunities").json()["diagnostic"]["event_denominator"] == 1
            c.get(path + "/alerts?item_id=999")
            with sessions() as s:
                assert s.get(Run, key).result_summary == summary
            with sessions.begin() as s:
                changed = deepcopy(summary)
                changed["threshold_metrics"]["event_denominator"] += 1
                s.get(Run, key).result_summary = changed
            with pytest.raises(DomainError, match="Threshold metric denominator"):
                verify_run(cfg, sessions, key, allow_running=True)
            with sessions.begin() as s:
                s.get(Run, key).result_summary = summary
        with sessions.begin() as s:
            s.execute(update(Alert).where(Alert.id == row["id"]).values(predicted_threshold_date=D + timedelta(days=2)))
        with pytest.raises(DomainError, match="ROP crossing"):
            verify_run(cfg, sessions, key, allow_running=True)
        with sessions.begin() as s:
            s.execute(delete(Alert).where(Alert.id == row["id"]))
        with pytest.raises(DomainError, match="ROP crossing"):
            verify_run(cfg, sessions, key, allow_running=True)


def test_threshold_migration_preserves_legacy_rows_and_checks_metadata(pg):
    engine, sessions = pg
    source, _, item = result_fixture(sessions)
    cfg = Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    cfg.attributes["database_url"] = str(engine.url.render_as_string(hide_password=False))
    with sessions.begin() as s:
        s.add(Alert(run_id=source, window_origin=D, item_id=item, as_of_date=D, alert_type="depletion",
            state="not_within_horizon", is_evaluable=False, explanation={}, is_simulated=True))
    command.downgrade(cfg, "0002_policy")
    try:
        with engine.connect() as c:
            before = c.scalar(text("SELECT row_to_json(t)::text FROM alerts t"))
            runs = c.execute(text("SELECT row_to_json(t)::text FROM runs t ORDER BY id")).scalars().all()
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")
        with engine.connect() as c:
            assert c.scalar(text("SELECT (to_jsonb(t) - 'predicted_threshold_date') FROM alerts t")) == json.loads(before)
            assert c.execute(text("SELECT row_to_json(t)::text FROM runs t ORDER BY id")).scalars().all() == runs
            assert compare_metadata(MigrationContext.configure(c, opts={"compare_type": True, "compare_server_default": True}), Base.metadata) == []
            assert c.scalar(text("SELECT version_num FROM alembic_version")) == "0005_carrier"
    finally:
        command.upgrade(cfg, "head")


def test_threshold_database_rejects_invalid_dates_states_and_duplicates(pg):
    _, sessions = pg
    source, _, item = result_fixture(sessions)
    base = dict(run_id=source, window_origin=D, item_id=item, as_of_date=D, alert_type="projected_below_rop",
        state="threshold_warning", predicted_threshold_date=D + timedelta(days=1), is_evaluable=False, explanation={})
    for change in [dict(predicted_threshold_date=None), dict(predicted_threshold_date=D),
                   dict(predicted_threshold_date=D + timedelta(days=15)), dict(state="early"),
                   dict(alert_type="below_rop", state="low_stock")]:
        with pytest.raises(IntegrityError), sessions.begin() as s:
            s.add(Alert(**{**base, **change}))
    with sessions.begin() as s:
        s.add(Alert(**base))
    with pytest.raises(IntegrityError), sessions.begin() as s:
        s.add(Alert(**base))
    cfg = Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    cfg.attributes["database_url"] = sessions.kw["bind"].url.render_as_string(hide_password=False)
    with pytest.raises(IntegrityError):
        command.downgrade(cfg, "0002_policy")
    with sessions() as s:
        assert s.scalar(select(Alert).where(Alert.alert_type == "projected_below_rop")) is not None
        assert s.scalar(text("SELECT version_num FROM alembic_version")) == "0005_carrier"


def test_two_items_apply_their_own_origin_rop_and_keep_first_crossing():
    args = list(inputs())
    args[5]["cover_days"] = 14
    args[0][2] = args[0][1]
    args[2].append({**args[2][0], "item_id":2, "sku":"SECOND"})
    args[3].update({(d, 2):v for (d, i), v in list(args[3].items())})
    args[4][0].update(rop_mode="fixed", configured_rop_floor=100)
    args[4].append({**args[4][0], "id":2, "item_id":2, "supplier_id":2, "configured_rop_floor":50})
    result = pure_window(*args, "stock_projection", ORIGIN, ORIGIN)
    signals = [r for r in result["alerts"] if r["alert_type"] == "projected_below_rop"]
    assert len(signals) == 1 and signals[0]["item_id"] == 1
    assert signals[0]["predicted_threshold_date"] == ORIGIN + timedelta(days=5)
