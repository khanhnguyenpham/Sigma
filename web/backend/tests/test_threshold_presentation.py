"""Read models count items, preserve frozen policy and match alert CSV signals."""
import csv
import io
from sqlalchemy import select, update
from fastapi.testclient import TestClient
import pytest

from main import create_app
from modules.configuration.models import Policy
from modules.forecasting.models import ItemForecast
from test_configurable_inventory import worker_fixture
from test_postgres_api import D, settings
from test_threshold_alerts import enqueue_threshold
from test_workspace_api import workspace_fixture
from worker import serve


@pytest.mark.parametrize("crossing", [True, False])
def test_workspace_counts_unique_items_with_threshold_and_depletion_and_csv(pg, tmp_path, crossing):
    _, sessions = pg
    source, forecast, item = worker_fixture(sessions, tmp_path)
    if not crossing:
        with sessions.begin() as s:
            s.execute(update(ItemForecast).where(ItemForecast.run_id == forecast).values(forecast_qty=0))
    with TestClient(create_app(settings(tmp_path))) as c:
        key = enqueue_threshold(c, source, forecast, item, "stock_projection")
        assert serve(settings(tmp_path), once=True) == key
        path = f"/api/v1/runs/{key}"
        data = c.get(path + f"/workspace?as_of_date={D}").json()
        summary = data["summary"]
        assert summary["item_count"] == 1
        assert summary["projected_below_rop_items"] == summary["warning_items"] == int(crossing)
        assert summary["urgent_items"] == summary["low_stock_items"] == 0
        signals = c.get(path + f"/alerts?as_of_date={D}&page_size=1").json()
        assert signals["total"] == (2 if crossing else 1)  # One item, separate signals.
        filtered = c.get(path + f"/alerts?as_of_date={D}&alert_type=projected_below_rop").json()
        exported = c.get(path + f"/exports/alerts?as_of_date={D}&alert_type=projected_below_rop")
        rows = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        assert len(rows) == filtered["total"] == int(crossing)
        if crossing:
            assert rows[0]["predicted_threshold_date"] == filtered["items"][0]["predicted_threshold_date"]
            assert rows[0]["predicted_depletion_date"] == ""
        assert c.get(path + f"/workspace?as_of_date={D}&item_id=999").json()["summary"]["warning_items"] == 0
        assert c.get(path + f"/workspace?as_of_date={D}&product_type=physical_SIM").json()["summary"]["projected_below_rop_items"] == 0
        # Editing the live catalog cannot reinterpret this complete run.
        with sessions.begin() as s:
            policy = s.scalar(select(Policy).where(Policy.item_id == item))
            policy.rop_mode = "forecast"
            policy.warning_horizon_days = 14
            policy.configured_rop_floor = 999
        inventory = c.get(path + "/inventory").json()["items"][0]
        assert (inventory["rop_mode"], inventory["warning_horizon_days"], inventory["configured_rop_floor"]) == ("fixed", 7, 20)
        assert c.get(path + f"/workspace?as_of_date={D}").json()["summary"] == summary


def test_legacy_run_uses_frozen_defaults_and_does_not_gain_projected_alerts(pg, tmp_path):
    _, sessions = pg
    key, _, _ = workspace_fixture(sessions)
    with TestClient(create_app(settings(tmp_path))) as c:
        path = f"/api/v1/runs/{key}"
        summary = c.get(path + f"/workspace?as_of_date={D}").json()["summary"]
        assert summary["warning_items"] == summary["urgent_items"] == 1
        assert summary["projected_below_rop_items"] == 0
        row = c.get(path + "/inventory").json()["items"][0]
        assert (row["safety_mode"], row["rop_mode"], row["warning_horizon_days"]) == ("days", "forecast", 7)
        rows = list(csv.DictReader(io.StringIO(c.get(path + "/exports/inventory_daily").text.lstrip("\ufeff"))))
        assert rows[0]["rop_mode"] == "forecast" and rows[0]["warning_horizon_days"] == "7"
