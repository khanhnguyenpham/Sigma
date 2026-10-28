"""F3 adapters/metrics on synthetic data, before any native candidate result."""

import ast
from copy import deepcopy
from datetime import date
import gzip
import json
from pathlib import Path

import pytest

from web.backend.research import forecast_postprocessing_validation as r
from web.backend.research import forecast_postprocessing_validation_verification as v
from test_forecast_postprocessing import synthetic


def metric_source():
    return dict(catalog=[dict(item_id=i, destination_country="SYNTHETIC", carrier="A") for i in (1, 2)],
                period=dict(score_start="2025-07-29", end="2025-07-30"),
                daily=[dict(date="2025-07-30", item_id=1, quantity=10, actual_available=True),
                       dict(date="2025-07-30", item_id=2, quantity=20, actual_available=True)])


def pick(rows, scope, horizon="daily_H1_14"):
    return next(row for row in rows if row["scope"] == scope and row["horizon"] == horizon)


def test_route_accuracy_aggregates_before_absolute_error_and_risk_pinball_is_cumulative():
    source = metric_source()
    producer, verifier = r.ForecastScores(source, .75), v.ReferenceScores(source, .75)
    values = {1: [20.0] * 14, 2: [10.0] * 14}
    for scores in (producer, verifier):
        scores.observe(date(2025, 7, 29), values)
    v.original.equal(producer.rows(), verifier.rows())
    assert pick(producer.rows(), "items_pooled")["mae"] == 10
    assert pick(producer.rows(), "routes_pooled")["mae"] == 0
    risk = pick(producer.rows(), "items_pooled", "cumulative_H01")
    assert risk["empirical_coverage"] == .5 and risk["pinball_loss"] == 5
    assert pick(producer.rows(), "items_pooled")["pinball_loss"] is None
    assert risk["expected"] == risk["observed"] == 2


@pytest.mark.parametrize("scenario", ["missing", "zero", "tail", "before_effective"])
def test_missing_zero_tail_and_warmup_masks_are_not_interchanged(scenario):
    source = metric_source()
    origin = date(2025, 7, 29)
    if scenario == "missing":
        source["daily"][1]["actual_available"] = False
    elif scenario == "zero":
        for row in source["daily"]:
            row["quantity"] = 0
    elif scenario == "tail":
        origin = date(2025, 7, 30)
    else:
        origin = date(2025, 7, 28)
    a, b = r.ForecastScores(source), v.ReferenceScores(source)
    for scores in (a, b):
        scores.observe(origin, {1: [2.0] * 14, 2: [3.0] * 14})
    v.original.equal(a.rows(), b.rows())
    if scenario in ("tail", "before_effective"):
        assert a.rows() == []
    elif scenario == "zero":
        row = pick(a.rows(), "items_pooled")
        assert row["wape"] is row["bias_ratio"] is None and row["mae"] == 2.5
    else:
        assert pick(a.rows(), "items_pooled")["coverage"] == .5
        assert pick(a.rows(), "routes_pooled")["coverage"] == 0


@pytest.mark.parametrize("candidate", ["C00", "I28", "R90"])
def test_streaming_adapter_matches_full_F2_and_independent_export_verifier(candidate, synthetic, tmp_path):
    source, baseline, parameters = synthetic
    before = deepcopy((source, baseline, parameters))
    cases, _ = r.audit.score(baseline, date.fromisoformat(source["period"]["score_start"]), date.fromisoformat(source["period"]["end"]))
    spec = next(s for s in r.post.load_protocol()["candidates"] if s["id"] == candidate)
    folder = tmp_path / candidate
    summary = r.calculate_candidate(spec, source, baseline, cases, parameters, folder)
    expected_parameters = v.reference.verify_parameters(source["catalog"], source["daily"], source["forecasts"], parameters)
    v.original.equal(v.verify_candidate_export(folder, source, baseline, cases, expected_parameters, spec), summary)
    full = r.post.evaluate(candidate, source, baseline, parameters)
    v.original.equal(summary["metrics"], full["metrics"])
    assert (source, baseline, parameters) == before
    assert summary["valid"] is True


@pytest.mark.parametrize("tamper", ["forecast", "interior_path", "duplicate", "metric", "summary", "case"])
def test_export_verifier_rejects_resealed_or_structurally_invalid_outputs(tamper, synthetic, tmp_path):
    source, baseline, parameters = synthetic
    cases, _ = r.audit.score(baseline, date.fromisoformat(source["period"]["score_start"]), date.fromisoformat(source["period"]["end"]))
    spec = r.post.load_protocol()["candidates"][0]
    folder = tmp_path / "C00"
    r.calculate_candidate(spec, source, baseline, cases, parameters, folder)
    if tamper in ("forecast", "interior_path", "duplicate"):
        with gzip.open(folder / "paths.jsonl.gz", "rt", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]
        if tamper == "forecast":
            rows[0]["forecast"][0] += 1
        elif tamper == "interior_path":
            rows[0]["projection"]["projection"][2]["closing_forecast"] += 1
        else:
            rows.append(deepcopy(rows[-1]))
        with gzip.open(folder / "paths.jsonl.gz", "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")
    else:
        file = folder / {"metric": "forecast_metrics.json.gz", "summary": "summary.json", "case": "cases.json.gz"}[tamper]
        value = r.audit.read(file)
        if tamper == "metric":
            value[0]["mae"] += 1
        elif tamper == "summary":
            value["metrics"]["early_numerator"] += 1
        else:
            value[0]["early"] = not value[0]["early"]
        r.audit.write(file, value)
    expected = v.reference.verify_parameters(source["catalog"], source["daily"], source["forecasts"], parameters)
    with pytest.raises(ValueError):
        v.verify_candidate_export(folder, source, baseline, cases, expected, spec)


def test_cli_has_no_test_execution_mode():
    with pytest.raises(SystemExit):
        r.main(["test"])


def test_new_verifier_has_no_producer_or_application_arithmetic_imports():
    modules = [n.module or "" for n in ast.walk(ast.parse(Path(v.__file__).read_text(encoding="utf-8"))) if isinstance(n, ast.ImportFrom)]
    assert not any(name.startswith("modules.") or name.endswith("forecast_postprocessing_validation")
                   or name.endswith("forecast_postprocessing") or name.endswith("inventory_forecast_identity") for name in modules)
