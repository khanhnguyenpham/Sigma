"""F2 synthetic-only checks. No private input, DB, model fitting or native run."""

import ast
import json
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest

from core.hashes import digest
from web.backend.research import forecast_postprocessing as p
from web.backend.research import forecast_postprocessing_verification as v


@pytest.fixture
def synthetic():
    start, end = date(2025, 6, 30), date(2025, 8, 12)
    catalog = [dict(item_id=i, destination_country="Synthetic", carrier="A" if i < 3 else "B",
                    first_seen_date="2024-01-01", sku="FAKE" + str(i), product_type="demo") for i in (1, 2, 3)]
    days = [start + timedelta(days=n) for n in range(-27, (end - start).days + 1)]
    daily = [dict(date=str(d), item_id=i, quantity=(i + d.weekday() % 3) if d.weekday() < 5 else 0,
                  actual_available=True) for d in days for i in (1, 2, 3)]
    forecasts = [dict(as_of_date=str(d), item_id=i, forecast=[float(i + h % 3) / 2 for h in range(14)])
                 for d in days if d >= start for i in (1, 2, 3)]
    policies = [dict(id=i, item_id=i, supplier_id=i, version=1, effective_from=str(start), effective_to=None,
                     configured_rop_floor=3, moq=2, safety_days=1) for i in (1, 2, 3)]
    snapshot = dict(period=dict(origin=str(start), end=str(end), score_start="2025-07-29"),
                    catalog=catalog, daily=daily, forecasts=forecasts, policies=policies, receipts=[],
                    sales=[dict(date=r["date"], item_id=r["item_id"], quantity=r["quantity"], sequence=n)
                           for n, r in enumerate(daily) if r["date"] > str(start) and r["quantity"] > 0])
    baseline = p.audit.replay(snapshot)
    parameters = p.calibrate(catalog, daily, forecasts)
    return snapshot, baseline, parameters


def test_protocol_matrix_and_cli_have_no_native_runner(capsys):
    assert [c["id"] for c in p.load_protocol()["candidates"]] == ["C00", "S10", "S25", "S50", "B00", "B07", "BND", "I14", "I28", "D14", "D28", "R75", "R90"]
    assert p.main(["--check-protocol"]) == 0
    assert '"real_candidate_runs": false' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        p.main(["--validation-run", "FORBIDDEN"])


@pytest.mark.parametrize("candidate", ["C00", "S10", "S25", "S50", "B00", "B07", "BND", "I14", "I28", "D14", "D28", "R75", "R90"])
def test_all_candidates_have_independent_parameters_forecasts_paths_and_scores(candidate, synthetic, monkeypatch):
    snapshot, baseline, parameters = synthetic
    before = deepcopy((snapshot, baseline, parameters))
    def forbid(*args, **kwargs):
        raise AssertionError("Candidate evaluation must not regenerate inventory/orders")
    monkeypatch.setattr(p.audit, "replay", forbid)
    monkeypatch.setattr(p.audit, "pure_window", forbid)
    actual = p.evaluate(candidate, snapshot, baseline, parameters)
    assert v.verify_candidate(candidate, snapshot, baseline, parameters, actual, calibration_inputs=snapshot)["status"] == "verified_synthetic_candidate"
    assert (snapshot, baseline, parameters) == before
    if candidate == "C00":
        assert actual["alarms"] == baseline["alarms"]


def test_hand_calculated_bias_quantile_and_zero_fallbacks(synthetic):
    snapshot, _, _ = synthetic
    for row in snapshot["daily"]:
        row["quantity"] = 4
    for row in snapshot["forecasts"]:
        row["forecast"] = [2.0] * 7 + [1.0] * 7
    params = p.calibrate(snapshot["catalog"], snapshot["daily"], snapshot["forecasts"])
    assert params["global_factor"] == pytest.approx(8 / 3)
    assert params["block_factors"] == pytest.approx([7 / 3, 10 / 3])
    assert set(params["route_levels"].values()) == {"low", "high"}
    assert all(x == 4 for x in params["scales"].values())
    assert params["risk_quantiles"]["0.75"][0] == .5
    v.verify_parameters(snapshot["catalog"], snapshot["daily"], snapshot["forecasts"], params)
    for row in snapshot["forecasts"]:
        row["forecast"] = [0.0] * 14
    zero = p.calibrate(snapshot["catalog"], snapshot["daily"], snapshot["forecasts"])
    assert zero["global_factor"] == 1 and zero["block_factors"] == [1, 1]
    risk = p.transform("R90", "2025-07-29", snapshot["catalog"], snapshot["daily"], snapshot["forecasts"], zero)
    assert all(vector == [4.0] * 14 for vector in risk.values())
    v.verify_parameters(snapshot["catalog"], snapshot["daily"], snapshot["forecasts"], zero)


@pytest.mark.parametrize("candidate", ["I14", "I28", "D14", "D28"])
def test_allocations_conserve_totals_and_zero_history_keeps_original(candidate, synthetic):
    s, _, params = synthetic
    origin = date(2025, 7, 29)
    original = p.transform("C00", origin, s["catalog"], s["daily"], s["forecasts"])
    result = p.transform(candidate, origin, s["catalog"], s["daily"], s["forecasts"], params)
    if candidate.startswith("I"):
        for h in range(14):
            assert sum(result[i][h] for i in (1, 2)) == pytest.approx(sum(original[i][h] for i in (1, 2)))
    else:
        for i in result:
            for block in (0, 7):
                assert sum(result[i][block:block + 7]) == pytest.approx(sum(original[i][block:block + 7]))
    for row in s["daily"]:
        if row["date"] <= str(origin):
            row["quantity"] = 0
    assert p.transform(candidate, origin, s["catalog"], s["daily"], s["forecasts"], params) == original


def test_future_actual_and_forecast_never_change_locked_parameters_or_prior_predictions(synthetic):
    s, _, params = synthetic
    changed = deepcopy(s)
    for row in changed["daily"]:
        if row["date"] > "2025-07-28":
            row["quantity"] += 10000
    for row in changed["forecasts"]:
        if row["as_of_date"] > "2025-07-14":
            row["forecast"] = [9999.0] * 14
    assert p.calibrate(changed["catalog"], changed["daily"], changed["forecasts"]) == params
    changed = deepcopy(s)
    for row in changed["daily"]:
        if row["date"] > "2025-07-29":
            row["quantity"] = None
            row["actual_available"] = False
    for spec in p.load_protocol()["candidates"]:
        assert p.transform(spec["id"], "2025-07-29", s["catalog"], s["daily"], s["forecasts"], params) == p.transform(spec["id"], "2025-07-29", changed["catalog"], changed["daily"], changed["forecasts"], params)
        assert p.transform(spec["id"], "2025-07-28", s["catalog"], [], s["forecasts"]) == p.transform("C00", "2025-07-28", s["catalog"], [], s["forecasts"])


@pytest.mark.parametrize("kind", ["missing_actual", "duplicate_forecast", "short_horizon", "unknown_item", "unsealed_parameters"])
def test_invalid_inputs_fail_closed(kind, synthetic):
    s, _, params = synthetic
    if kind == "missing_actual":
        next(r for r in s["daily"] if r["date"] == "2025-07-28")["actual_available"] = False
    elif kind == "duplicate_forecast":
        s["forecasts"].append(deepcopy(s["forecasts"][0]))
    elif kind == "short_horizon":
        s["forecasts"][0]["forecast"].pop()
    elif kind == "unknown_item":
        s["catalog"][0]["first_seen_date"] = "2025-07-10"
    else:
        params["global_factor"] += 1
        with pytest.raises(ValueError):
            p.transform("B00", "2025-07-29", s["catalog"], s["daily"], s["forecasts"], params)
        return
    with pytest.raises(ValueError):
        p.calibrate(s["catalog"], s["daily"], s["forecasts"])


@pytest.mark.parametrize("kind", ["parameter_reseal", "forecast_reseal", "interior_path", "event_numerator", "frozen_order"])
def test_independent_verifier_rejects_tampering(kind, synthetic):
    s, baseline, params = synthetic
    output = p.evaluate("B00", s, baseline, params)
    if kind == "parameter_reseal":
        params["global_factor"] += 1
        params["sha256"] = digest({k: x for k, x in params.items() if k != "sha256"})
    elif kind == "forecast_reseal":
        output["forecasts"][-1]["forecast"][0] += 1
    elif kind == "interior_path":
        output["projections"][-1]["projection"][4]["closing_forecast"] += 1
    elif kind == "event_numerator":
        output["metrics"]["early_numerator"] += 1
    else:
        baseline["orders"][0]["ordered_qty"] += 1
    with pytest.raises(ValueError):
        v.verify_candidate("B00", s, baseline, params, output, calibration_inputs=s)


def test_validation_selection_requires_full_grid_fixed_denominator_and_locked_ties():
    summaries = [dict(candidate_id=c["id"], valid=True, alarm_item_days=20,
                      metrics=dict(early_numerator=219, event_denominator=486, precision=.8)) for c in p.load_protocol()["candidates"]]
    assert p.select_validation(summaries) == "C00"
    summaries[1]["alarm_item_days"] = 19
    assert p.select_validation(summaries) == "S10"
    for row in summaries:
        row["metrics"]["early_numerator"] = 218
    assert p.select_validation(summaries) is None
    with pytest.raises(ValueError):
        p.select_validation(summaries[:-1])
    summaries[0]["metrics"]["event_denominator"] = 578
    with pytest.raises(ValueError):
        p.select_validation(summaries)


def test_verifier_has_no_production_arithmetic_or_postprocessor_imports():
    tree = ast.parse(Path(v.__file__).read_text(encoding="utf-8"))
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(name.startswith("modules.") or name.endswith("forecast_postprocessing") or name.endswith("inventory_forecast_identity") for name in imports)


def test_partial_zero_group_inherits_parent_once_and_negative_quantiles_add_nothing(synthetic):
    s, _, _ = synthetic
    for row in s["daily"]:
        row["quantity"] = 1 if row["item_id"] < 3 else 10
    for row in s["forecasts"]:
        row["forecast"] = ([1.0] * 7 + [2.0] * 7) if row["item_id"] < 3 else [0.0] * 14
    params = p.calibrate(s["catalog"], s["daily"], s["forecasts"])
    assert params["global_factor"] == 4
    assert params["block_factors"] == [5, 3.5]
    assert params["level_block_factors"]["high"] == [5, 3.5]
    v.verify_parameters(s["catalog"], s["daily"], s["forecasts"], params)
    for row in s["daily"]:
        row["quantity"] = 0
    for row in s["forecasts"]:
        row["forecast"] = [2.0] * 14
    params = p.calibrate(s["catalog"], s["daily"], s["forecasts"])
    assert all(q < 0 for q in params["risk_quantiles"]["0.9"])
    assert p.transform("R90", "2025-07-29", s["catalog"], s["daily"], s["forecasts"], params) == p.transform("C00", "2025-07-29", s["catalog"], s["daily"], s["forecasts"])


def test_risk_arithmetic_never_creates_negative_daily_demand(synthetic):
    s, _, parameters = synthetic
    # Artificial synthetic parameter profile exercises a decreasing raw bound;
    # this is not passed off as a verified calibration result.
    parameters["risk_quantiles"]["0.9"] = [100.0] + [0.0] * 13
    parameters["sha256"] = digest({k: x for k, x in parameters.items() if k != "sha256"})
    result = p.transform("R90", "2025-07-29", s["catalog"], s["daily"], s["forecasts"], parameters)
    assert all(vector[0] > 0 and vector[1:] == [0.0] * 13 for vector in result.values())


def test_unused_event_flags_do_not_enter_parameters_and_json_roundtrip_is_stable(synthetic):
    s, _, parameters = synthetic
    for row in s["daily"]:
        row["actual_depletion_date"] = "FORBIDDEN"
        row["opportunity"] = True
    assert p.calibrate(s["catalog"], s["daily"], s["forecasts"]) == parameters
    restored = json.loads(json.dumps(parameters))
    v.verify_parameters(s["catalog"], s["daily"], s["forecasts"], restored)
    for spec in p.load_protocol()["candidates"]:
        assert p.transform(spec["id"], "2025-07-29", s["catalog"], s["daily"], s["forecasts"], restored) == p.transform(spec["id"], "2025-07-29", s["catalog"], s["daily"], s["forecasts"], parameters)


def test_incomplete_mature_labels_or_missing_allocation_history_cannot_be_zero_filled(synthetic):
    s, _, parameters = synthetic
    truncated = [r for r in s["daily"] if r["date"] < "2025-07-28"]
    with pytest.raises(ValueError):
        p.calibrate(s["catalog"], truncated, s["forecasts"])
    with pytest.raises(ValueError):
        p.transform("I28", "2025-07-29", s["catalog"], truncated, s["forecasts"], parameters)


def test_selection_rejects_impossible_or_nonfinite_summaries():
    original = [dict(candidate_id=c["id"], valid=True, alarm_item_days=20,
                     metrics=dict(early_numerator=219, event_denominator=486, precision=.8)) for c in p.load_protocol()["candidates"]]
    for field, value in [("precision", float("nan")), ("precision", 1.1), ("early_numerator", 487), ("early_numerator", True)]:
        summaries = deepcopy(original)
        summaries[0]["metrics"][field] = value
        with pytest.raises(ValueError):
            p.select_validation(summaries)


@pytest.mark.parametrize("collection", ["daily", "forecasts"])
def test_boolean_item_ids_cannot_alias_integer_ids(collection, synthetic):
    s, _, _ = synthetic
    for row in s[collection]:
        if row["item_id"] == 1:
            row["item_id"] = True
    with pytest.raises(ValueError):
        p.calibrate(s["catalog"], s["daily"], s["forecasts"])


def test_later_split_uses_separate_locked_calibration_source_without_refitting(synthetic):
    s, baseline, params = synthetic
    reference = v.verify_parameters(s["catalog"], s["daily"], s["forecasts"], params)
    later_daily = [r for r in s["daily"] if r["date"] >= "2025-07-15"]
    later_forecasts = [r for r in s["forecasts"] if r["as_of_date"] >= "2025-08-01"]
    for candidate in ("B00", "B07", "BND", "R75", "R90"):
        actual = p.transform(candidate, "2025-08-12", s["catalog"], later_daily, later_forecasts, params)
        expected = v.forecast_reference(candidate, "2025-08-12", s["catalog"], later_daily, later_forecasts, reference)
        v.equal(actual, expected)
    output = p.evaluate("B00", s, baseline, params)
    with pytest.raises(ValueError):
        v.verify_candidate("B00", s, baseline, params, output)
