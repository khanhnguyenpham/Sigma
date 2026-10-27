"""Independent arithmetic, causal-prefix and forged-artifact checks; synthetic only."""

from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import shutil

import pytest
from web.backend.research import inventory_alert_experiments as runner
from web.backend.research import inventory_alert_verification as verifier
from web.backend.tests.test_inventory_alert_experiments import fixture_snapshot, config, ORIGIN


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    p = runner.protocol()["validation"]
    snapshot = fixture_snapshot(length=(date.fromisoformat(p["end"])-ORIGIN).days,
        score_start=date.fromisoformat(p["score_start"]), past=list(range(7))*4,
        actual=lambda h: h*7 % 9, forecast=lambda h: [(h+n)%5/3+.25 for n in range(14)])
    snapshot["receipts"] = [dict(item_id=1, ordered_on=ORIGIN.isoformat(),
        eta=(ORIGIN+timedelta(days=7)).isoformat(), ordered_qty=8, lot_key="synthetic-known")]
    return runner.calculate(snapshot, runner.experiment_matrix(), tmp_path_factory.mktemp("independent"))


def clone(bundle, tmp_path):
    target = tmp_path/"run"
    shutil.copytree(bundle, target)
    return target


def reseal(folder, relative, value):
    runner.write_json(folder/relative, value)
    manifest = runner.read_json(folder/"manifest.json")
    manifest["artifacts"][relative] = runner.file_hash(folder/relative)
    runner.write_json(folder/"manifest.json", manifest)


def test_verify_reconstructs_every_table_and_receipt_is_idempotent(bundle, tmp_path):
    folder = clone(bundle, tmp_path)
    original = {p.relative_to(folder).as_posix(): verifier.sha(p) for p in folder.rglob("*") if p.is_file()}
    receipt = verifier.verify_run(folder)
    assert receipt["status"] == "verified" and receipt["independent_replay"] is True
    assert receipt["configurations_checked"] == 19
    assert receipt["evidence_class"] == "synthetic" and receipt["anchor_scope"] == "frozen_synthetic_inputs"
    assert receipt["rows_checked"]["ledger"] > 1000
    before = (folder/"verification.json").read_bytes()
    assert verifier.verify_run(folder) == receipt
    assert (folder/"verification.json").read_bytes() == before
    assert all(verifier.sha(folder/name) == h for name, h in original.items())


def test_verifier_does_not_delegate_to_any_production_arithmetic(bundle, tmp_path, monkeypatch):
    from modules.inventory import service as inventory
    from modules.alerts import service as alerts
    folder = clone(bundle, tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("Independent verifier called the production arithmetic")
    for name in ("simulate", "prepare_inputs", "decision", "score_windows", "score_continuous", "inventory_metrics",
                 "score_thresholds", "compare_events", "verify_artifacts", "recommend", "project", "fulfill_day"):
        monkeypatch.setattr(runner, name, forbidden)
    for module, names in ((inventory, ("recommend", "fulfill_day", "history_quantities", "vector14", "eta")),
                          (alerts, ("project", "project_threshold", "replay_metrics", "threshold_metrics"))):
        for name in names: monkeypatch.setattr(module, name, forbidden)
    assert verifier.verify_run(folder)["status"] == "verified"


@pytest.mark.parametrize("area", ["ledger", "ss", "rop", "transactions", "events", "orders", "initialization",
    "alarms", "cases", "threshold_cases", "alarm_evaluation", "event_changes", "metrics", "integer_type"])
def test_resealed_math_tamper_is_rejected_without_success_receipt(bundle, tmp_path, area):
    folder = clone(bundle, tmp_path)
    identity = "C-days-m1-cover7" if area == "event_changes" else "D-volatility-m1-cover7"
    path = "results/"+identity+".json.gz"
    result = runner.read_json(folder/path)
    if area == "ledger": result["ledger"][1]["closing_qty"] += 1
    elif area in ("ss", "rop"): result["ledger"][1][area] += 1
    elif area == "transactions": result["transactions"][0]["fulfilled_qty"] += 1
    elif area == "events": result["events"].append(deepcopy(result["events"][0]))
    elif area == "orders": result["orders"][0]["eta"] = "2025-07-30"
    elif area == "initialization": result["initialization"][0]["initial_qty"] += 1
    elif area == "alarms": result["alarms"][0]["predicted_depletion_date"] = "2025-07-01"
    elif area == "cases": result["cases"] = []
    elif area == "threshold_cases": result["threshold_cases"][0]["is_evaluable"] = not result["threshold_cases"][0]["is_evaluable"]
    elif area == "alarm_evaluation": result["alarm_evaluation"][0]["status"] = "invented"
    elif area == "event_changes": result["event_changes"] = [dict(invented=True)]
    elif area == "metrics": result["metrics"]["early_numerator"] += 1
    elif area == "integer_type": result["metrics"]["event_denominator"] = True
    reseal(folder, path, result)
    with pytest.raises(ValueError): verifier.verify_run(folder)
    assert not (folder/"verification.json").exists()


@pytest.mark.parametrize("area", ["missing", "checksum", "summary", "report", "matrix", "protocol", "code", "input_meta", "receipt"])
def test_artifact_and_binding_tamper_are_rejected(bundle, tmp_path, area):
    folder = clone(bundle, tmp_path)
    manifest = runner.read_json(folder/"manifest.json")
    if area == "missing": (folder/"results/A-base.json.gz").unlink()
    elif area == "checksum": (folder/"metrics.json").write_text("[]", encoding="utf-8")
    elif area == "summary":
        summary = runner.read_json(folder/"metrics.json"); summary[0]["early_rate"] = .999
        reseal(folder, "metrics.json", summary)
    elif area == "report":
        (folder/"report.html").write_text("<table><tr><td>fake</td></tr></table>", encoding="utf-8")
        manifest["artifacts"]["report.html"] = verifier.sha(folder/"report.html")
        runner.write_json(folder/"manifest.json", manifest)
    elif area == "matrix":
        manifest["config_ids"].pop(); runner.write_json(folder/"manifest.json", manifest)
    elif area == "protocol":
        manifest["protocol"]["minimum_early_days"] = 3
        manifest["protocol_sha256"] = verifier.checksum(manifest["protocol"])
        runner.write_json(folder/"manifest.json", manifest)
    elif area == "code":
        manifest["research_code_sha256"] = "0"*64; runner.write_json(folder/"manifest.json", manifest)
    elif area == "input_meta":
        snapshot = runner.read_json(folder/"inputs.json.gz"); snapshot["meta"]["source_sha256"] = "0"*64
        reseal(folder, "inputs.json.gz", snapshot)
    elif area == "receipt":
        runner.write_json(folder/"verification.json", dict(status="verified", independent_replay=True,
            manifest_sha256=verifier.sha(folder/"manifest.json")))
    with pytest.raises((ValueError, KeyError)): verifier.verify_run(folder)


@pytest.mark.parametrize("name", ["A-base", "B-daily", "C-volatility-m1-cover7", "D-volatility-m1-cover7"])
def test_future_actual_mutation_cannot_change_either_engines_past_decisions(name):
    snapshot = fixture_snapshot(length=20)
    changed = deepcopy(snapshot)
    cutoff = ORIGIN + timedelta(days=5)
    for row in changed["daily"]:
        if date.fromisoformat(row["date"]) > cutoff: row["quantity"] = 100
    for row in changed["sales"]:
        if date.fromisoformat(row["date"]) > cutoff: row["quantity"] = 100
    c = config(name)
    before, after = (verifier.rebuild(s, c) for s in (snapshot, changed))
    for table, field in (("ledger", "date"), ("alarms", "date"), ("transactions", "date"), ("orders", "ordered_on")):
        assert [r for r in before[table] if r[field] <= cutoff.isoformat()] == [r for r in after[table] if r[field] <= cutoff.isoformat()]
    for s in (snapshot, changed):
        actual = runner.simulate(runner.prepare_inputs(s), c)
        verifier.same(json.loads(json.dumps(actual, default=runner.json_date)), verifier.rebuild(s, c))


@pytest.mark.parametrize("day,early", [(6,0), (7,1), (14,1)])
def test_independent_boundary_days_have_hand_calculated_early_counts(day, early):
    s = fixture_snapshot(past=4, actual=lambda h: 28 if h == day else 0,
                         forecast=lambda h: [0]*(day-1)+[28]+[0]*(14-day))
    result = verifier.rebuild(s, config("A-base"))
    assert result["metrics"]["early_numerator"] == early
    assert result["metrics"]["event_denominator"] == 1


def test_population_variance_zero_factor_and_safety_is_added_once():
    snapshot = fixture_snapshot(past=list(range(7))*4)
    c = verifier.rebuild(snapshot, config("C-volatility-m1-cover7"))
    assert c["initialization"][0] == dict(window_origin=ORIGIN.isoformat(), item_id=1, base_qty=21, added_ss=6, initial_qty=27)
    assert c["ledger"][2]["closing_qty"] == 25
    d = verifier.rebuild(snapshot, config("D-days-m0-cover7"))
    assert all(r["ss"] == 0 for r in d["ledger"])


def test_same_day_receipt_and_depletion_create_new_episode_but_persistent_zero_does_not():
    s = fixture_snapshot(actual=lambda h: 7 if h == 1 else 1 if h == 7 else 0, forecast=lambda h: [0]*14)
    s["receipts"] = [dict(item_id=1, ordered_on=ORIGIN.isoformat(), eta=(ORIGIN+timedelta(days=7)).isoformat(),
                          ordered_qty=1, lot_key="recovery")]
    result = verifier.rebuild(s, config("D-days-m0-cover7"))
    assert [e["date"] for e in result["events"]] == [(ORIGIN+timedelta(days=h)).isoformat() for h in (1,7)]
    assert result["metrics"]["event_denominator"] == 2
    assert all(r["closing_qty"] == 0 for r in result["ledger"] if r["date"] >= (ORIGIN+timedelta(days=1)).isoformat())


def test_warmup_alarm_counts_once_for_a_scored_event():
    s = fixture_snapshot(length=20, actual=lambda h: 12 if h == 10 else 0,
                         score_start=ORIGIN+timedelta(days=8))
    result = verifier.rebuild(s, config("D-days-m1-cover7"))
    assert result["metrics"]["early_numerator"] == result["metrics"]["event_denominator"] == 1
    assert result["cases"][0]["lead_days"] == 10
    assert sum(r["event_id"] == result["cases"][0]["event_id"] for r in result["alarm_evaluation"]) > 1


def test_same_day_new_order_is_intervention_and_tail_is_censored_without_false_success():
    s = fixture_snapshot(length=20, actual=lambda h: 0, forecast=lambda h: [10]*14)
    result = verifier.rebuild(s, config("D-days-m1-cover7"))
    origin_alarm = next(r for r in result["alarm_evaluation"] if r["date"] == ORIGIN.isoformat())
    assert origin_alarm["status"] == "intervened"
    assert result["alarm_evaluation"][-1]["status"] == "right_censored"
    assert result["metrics"]["early_rate"] is None


def test_threshold_equality_does_not_cross_and_stays_separate_from_depletion():
    s = fixture_snapshot(past=[2]*12+[1]*16, actual=lambda h: 1 if h == 1 else 0, forecast=lambda h: [0]*14)
    s["policies"][0]["configured_rop_floor"] = 10
    result = verifier.rebuild(s, config("A-base"))
    assert result["initialization"][0]["initial_qty"] == result["alarms"][0]["rop"] == 10
    assert result["alarms"][0]["predicted_threshold_date"] is None
    assert result["metrics"]["threshold_metrics"]["FN"] == 1
    assert result["metrics"]["event_denominator"] == 0


def test_forged_receipt_and_resealed_outputs_cannot_authorize_test_reads(bundle, tmp_path, monkeypatch):
    folder = clone(bundle, tmp_path)
    verifier.verify_run(folder)
    path = "results/D-volatility-m1-cover7.json.gz"
    data = runner.read_json(folder/path); data["ledger"][2]["ss"] += 1; reseal(folder, path, data)
    receipt = runner.read_json(folder/"verification.json"); receipt["manifest_sha256"] = verifier.sha(folder/"manifest.json")
    runner.write_json(folder/"verification.json", receipt)
    manifest = runner.read_json(folder/"manifest.json")
    lock = dict(validation_run=str(folder), validation_manifest_sha256=receipt["manifest_sha256"],
        validation_verification_sha256=verifier.sha(folder/"verification.json"), protocol_sha256=manifest["protocol_sha256"],
        selected_configs=["C-cover3"], **{k: manifest["input_meta"][k] for k in ("source_sha256","forecast_config_sha256","selection_sha256")})
    lock_path = tmp_path/"lock.json"; runner.write_json(lock_path, lock)
    def forbidden(*args, **kwargs): pytest.fail("Forged evidence read test inputs")
    monkeypatch.setattr(runner, "load_database_inputs", forbidden)
    assert runner.main(["evaluate", "--selection-lock", str(lock_path)]) == 1


def test_synthetic_verification_cannot_authorize_real_data_evaluation(bundle, tmp_path, monkeypatch):
    folder = clone(bundle, tmp_path); proof = verifier.verify_run(folder)
    manifest = runner.read_json(folder/"manifest.json")
    lock = dict(validation_run=str(folder), validation_manifest_sha256=proof["manifest_sha256"],
        validation_verification_sha256=verifier.sha(folder/"verification.json"), protocol_sha256=manifest["protocol_sha256"],
        selected_configs=["C-cover3"], **{k: manifest["input_meta"][k] for k in ("source_sha256","forecast_config_sha256","selection_sha256")})
    path = tmp_path/"lock.json"; runner.write_json(path, lock)
    def forbidden(*args, **kwargs): pytest.fail("Synthetic lock read real test data")
    monkeypatch.setattr(runner, "load_database_inputs", forbidden)
    assert runner.main(["evaluate", "--selection-lock", str(path)]) == 1


def test_duplicate_json_keys_and_nonfinite_constants_are_rejected(tmp_path):
    p = tmp_path/"bad.json"
    for text in ('{"status":1,"status":2}', '{"n":NaN}'):
        p.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError): verifier.read(p)


@pytest.mark.parametrize("change", ["forecast", "policy"])
def test_future_origin_forecast_or_effective_policy_cannot_rewrite_past(change):
    before = fixture_snapshot(length=20)
    after = deepcopy(before)
    cutoff = ORIGIN + timedelta(days=5)
    if change == "forecast":
        for row in after["forecasts"]:
            if row["as_of_date"] > cutoff.isoformat(): row["forecast"] = [99]*14
    else:
        effective = (cutoff+timedelta(days=1)).isoformat()
        after["policies"][0]["effective_to"] = effective
        new = deepcopy(before["policies"][0]); new.update(effective_from=effective, configured_rop_floor=99, safety_days=9)
        after["policies"].append(new)
    c = config("D-volatility-m1-cover7")
    results = [verifier.rebuild(s, c) for s in (before, after)]
    for table in ("ledger", "alarms"):
        assert [r for r in results[0][table] if r["date"] <= cutoff.isoformat()] == [r for r in results[1][table] if r["date"] <= cutoff.isoformat()]
    for snapshot, result in zip((before, after), results, strict=True):
        produced = runner.simulate(runner.prepare_inputs(snapshot), c)
        verifier.same(json.loads(json.dumps(produced, default=runner.json_date)), result)


def test_future_item_is_reported_outside_frozen_cohort():
    s = fixture_snapshot(length=20)
    extra = deepcopy(s["catalog"][0]); extra.update(item_id=2, sku="FUTURE-SYNTHETIC",
        first_seen_date=(ORIGIN+timedelta(days=3)).isoformat())
    s["catalog"].append(extra)
    for row in s["sales"]: row["sequence"] *= 2
    extra_daily = []
    for row in s["daily"]:
        d = date.fromisoformat(row["date"])
        q = 100 if d >= ORIGIN+timedelta(days=3) else 0
        extra_daily.append(dict(row, item_id=2, quantity=q))
        if q:
            s["sales"].append(dict(date=row["date"], item_id=2, quantity=q,
                                   sequence=2*(d-ORIGIN).days+1))
    s["daily"].extend(extra_daily)
    c = config("D-days-m1-cover7")
    result = verifier.rebuild(s, c)
    assert result["metrics"]["cohort_items"] == 1
    assert result["metrics"]["excluded_items"] == [2]
    assert result["metrics"]["excluded_sales_qty"] == 1800
    assert all(row["item_id"] == 1 for row in result["ledger"])
    verifier.same(json.loads(json.dumps(runner.simulate(runner.prepare_inputs(s), c), default=runner.json_date)), result)


def test_alarm_matches_first_real_event_even_when_it_is_outside_scoring_period():
    s = fixture_snapshot(length=20, actual=lambda h: 7 if h == 1 else 6 if h == 7 else 0,
                         score_start=ORIGIN+timedelta(days=4))
    s["receipts"] = [dict(item_id=1, ordered_on=ORIGIN.isoformat(), eta=(ORIGIN+timedelta(days=7)).isoformat(),
                          ordered_qty=1, lot_key="known-first")]
    result = verifier.rebuild(s, config("D-days-m1-cover7"))
    assert result["cases"][0]["date"] == (ORIGIN+timedelta(days=7)).isoformat()
    assert result["cases"][0]["alarm_date"] is None
    assert result["metrics"]["early_numerator"] == 0


@pytest.mark.parametrize("crossing", [7, 8])
def test_threshold_horizon_includes_n_but_not_n_plus_one(crossing):
    s = fixture_snapshot(past=[2]*12+[1]*16, actual=lambda h: 1 if h == crossing else 0,
                         forecast=lambda h: [0]*(crossing-1)+[1]+[0]*(14-crossing))
    s["policies"][0]["configured_rop_floor"] = 10
    result = verifier.rebuild(s, config("A-base"))
    assert result["alarms"][0]["predicted_threshold_date"] == ((ORIGIN+timedelta(days=7)).isoformat() if crossing == 7 else None)
    assert result["metrics"]["threshold_metrics"]["TP" if crossing == 7 else "TN"] == 1
    assert result["metrics"]["event_denominator"] == 0
