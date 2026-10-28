"""F1 identity checks on synthetic records only; no database or private bundles."""

from copy import deepcopy
from datetime import timedelta
import io
import json

import pytest

from web.backend.research import inventory_forecast_identity as f1
from test_inventory_alert_opportunity_audit import fixture
from test_simulation import ORIGIN


def identity_inputs():
    snapshot, baseline, frozen = fixture()
    end = snapshot["period"]["end"]
    snapshot["forecasts"] = [r for r in snapshot["forecasts"] if r["as_of_date"] <= end]
    snapshot["daily"] = [r for r in snapshot["daily"]
                         if str(ORIGIN - timedelta(days=27)) <= r["date"] <= end]
    cases, metrics = f1.audit.score(baseline, ORIGIN + timedelta(days=1),
                                    ORIGIN + timedelta(days=14))
    frozen.update(cases=cases, metrics=metrics)
    return snapshot, frozen, baseline


def test_identity_preserves_inputs_and_checks_every_path_without_policy_replay(monkeypatch):
    snapshot, frozen, baseline = identity_inputs()
    before = deepcopy((snapshot, frozen, baseline))

    def forbid(*args, **kwargs):
        raise AssertionError("F1 must not recalculate purchasing")

    monkeypatch.setattr(f1.audit, "replay", forbid)
    monkeypatch.setattr(f1.audit, "pure_window", forbid)
    stream = io.BytesIO()
    summary, cases, alarms = f1.check_split(snapshot, frozen, baseline, stream)
    assert (snapshot, frozen, baseline) == before
    assert summary["forecast_vectors"] == summary["alarm_rows_checked"] == 15
    assert summary["projection_rows_checked"] == 210
    assert summary["metrics"] == frozen["metrics"]
    assert cases == frozen["cases"] and alarms == baseline["alarms"]
    exported = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert len(exported) == 15 and all(len(r["projection"]) == 14 for r in exported)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "short", "nan", "bool", "negative", "missing_actual"])
def test_coverage_rejects_incomplete_or_invalid_inputs(mutation):
    snapshot, _, baseline = identity_inputs()
    if mutation == "missing":
        snapshot["forecasts"].pop()
    elif mutation == "duplicate":
        snapshot["forecasts"].append(deepcopy(snapshot["forecasts"][0]))
    elif mutation == "short":
        snapshot["forecasts"][0]["forecast"].pop()
    elif mutation in ("nan", "bool", "negative"):
        snapshot["forecasts"][0]["forecast"][0] = {"nan": float("nan"), "bool": True, "negative": -1}[mutation]
    else:
        snapshot["daily"][0]["actual_available"] = False
    with pytest.raises(ValueError):
        f1.coverage(snapshot, baseline)


def test_same_day_new_order_and_future_orders_are_not_known_receipts():
    eta = str(ORIGIN + timedelta(days=7))
    orders = [dict(eta=eta, ordered_on=str(ORIGIN + timedelta(days=d)),
                   ordered_qty=q, is_initial=initial)
              for d, q, initial in [(-1, 2, False), (0, 3, False), (1, 5, False), (0, 7, True)]]
    assert f1.known_receipts(orders, ORIGIN) == {ORIGIN + timedelta(days=7): 9}
    assert f1.known_receipts(orders, ORIGIN + timedelta(days=7)) == {}


@pytest.mark.parametrize("stock,state", [(6, "urgent"), (7, "early"), (14, "early")])
def test_projection_lead_boundaries_and_already_depleted(stock, state):
    result = f1.reference_projection(ORIGIN, stock, [1] * 14, {})
    assert result == f1.project(ORIGIN, stock, [1] * 14, {})
    assert result["state"] == state and result["lead_days"] == stock
    receipts = {ORIGIN + timedelta(days=1): 2}
    zero = f1.reference_projection(ORIGIN, 0, [1] * 14, receipts)
    assert zero == f1.project(ORIGIN, 0, [1] * 14, receipts)
    assert zero["state"] == "already_depleted" and zero["predicted_depletion_date"] == ORIGIN


def test_wrong_interior_projection_is_rejected_even_when_depletion_date_is_unchanged(monkeypatch):
    snapshot, frozen, baseline = identity_inputs()
    original = f1.project

    def corrupted(*args):
        result = original(*args)
        result["projection"][2]["closing_forecast"] += 0.5
        return result

    monkeypatch.setattr(f1, "project", corrupted)
    with pytest.raises(ValueError, match="Independent opportunity verification failed"):
        f1.check_split(snapshot, frozen, baseline)


def test_fractional_demand_and_receipt_are_compared_at_every_horizon():
    receipts = {ORIGIN + timedelta(days=3): 1, ORIGIN + timedelta(days=9): 2}
    forecast = [0.1, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9] * 2
    assert f1.reference_projection(ORIGIN, 1, forecast, receipts) == f1.project(ORIGIN, 1, forecast, receipts)


def test_forged_audit_is_rejected_before_output_is_created(tmp_path):
    audit = tmp_path / "audit"
    audit.mkdir()
    (audit / "manifest.json").write_text("{}", encoding="utf-8")
    output = tmp_path / "output"
    assert f1.main(["--audit-run", str(audit), "--output-root", str(output)]) == 1
    assert not output.exists()
