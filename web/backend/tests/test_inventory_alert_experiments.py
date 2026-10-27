"""Hand-calculated research controls; all records are synthetic."""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json

import pandas as pd
import pytest
from core.errors import DomainError
from modules.inventory.simulation import pure_window
from web.backend.research import inventory_alert_experiments as research


ORIGIN = date(2025, 6, 30)


def fixture_snapshot(length=14, past=1, actual=None, forecast=None, score_start=None, origin=ORIGIN):
    end = origin + timedelta(days=length)
    actual = actual or (lambda h: 1)
    forecast = forecast or (lambda h: [1] * 14)
    daily, sales, forecasts = [], [], []
    for n, day in enumerate(research.days(origin - timedelta(days=27), end)):
        h = (day - origin).days
        q = (past[n] if isinstance(past, list) else past) if h <= 0 else actual(h)
        daily.append(dict(date=day.isoformat(), item_id=1, quantity=q, actual_available=True))
        if h > 0 and q:
            sales.append(dict(date=day.isoformat(), item_id=1, sequence=h, quantity=q))
        if h >= 0:
            forecasts.append(dict(as_of_date=day.isoformat(), item_id=1, forecast=forecast(h)))
    return dict(version=1, split="validation", period=dict(origin=origin.isoformat(), end=end.isoformat(),
        score_start=(score_start or origin + timedelta(days=1)).isoformat()),
        meta=dict(provenance="synthetic", source_sha256="a" * 64, forecast_config_sha256="b" * 64,
                  selection_sha256="c" * 64),
        catalog=[dict(item_id=1, sku="SYNTHETIC", product_type="eSIM", destination_country="Example",
                      carrier="Synthetic", first_seen_date="2024-01-01")], daily=daily, sales=sales,
        forecasts=forecasts, policies=[dict(id=1, item_id=1, effective_from=origin.isoformat(),
            effective_to=None, configured_rop_floor=0, moq=5, safety_days=2)], receipts=[])


def config(name):
    return next(c for c in research.experiment_matrix() if c["id"] == name)


def run(snapshot, name):
    return research.simulate(research.prepare_inputs(snapshot), config(name))


def test_matrix_is_exactly_the_nineteen_locked_controls():
    matrix = research.experiment_matrix()
    assert len(matrix) == len({c["id"] for c in matrix}) == 19
    assert {g: sum(c["group"] == g for c in matrix) for g in "ABCD"} == dict(A=1, B=1, C=8, D=9)
    assert sum(c["add_ss"] for c in matrix) == 6
    assert not config("D-days-m1-cover7")["add_ss"]


@pytest.mark.parametrize("depletion,early", [(6, 0), (7, 1), (14, 1)])
def test_hand_calculated_first_depletion_boundary(depletion, early):
    snapshot = fixture_snapshot(past=4, actual=lambda h: 28 if h == depletion else 0,
                               forecast=lambda h: [0] * (depletion - 1) + [28] + [0] * (14 - depletion))
    result = run(snapshot, "A-base")
    assert result["initialization"][0]["initial_qty"] == 28
    assert result["cases"][0]["actual_depletion_date"] == ORIGIN + timedelta(days=depletion)
    assert result["metrics"]["early_numerator"] == early
    assert result["metrics"]["event_denominator"] == 1


def test_no_depletion_is_null_not_a_pass_and_initial_zero_is_excluded():
    no_event = run(fixture_snapshot(actual=lambda h: 0, forecast=lambda h: [0] * 14), "A-base")
    assert no_event["metrics"]["early_rate"] is None
    assert no_event["metrics"]["TN"] == 1
    zero = run(fixture_snapshot(past=0), "B-daily")
    assert zero["metrics"]["excluded_count"] == 1
    assert zero["metrics"]["event_denominator"] == 0


def test_a_matches_existing_pure_replay_ledger_and_metric():
    snapshot = fixture_snapshot()
    data = research.prepare_inputs(snapshot)
    matrix = pd.DataFrame({1: [r["quantity"] for r in snapshot["daily"]]},
                          index=pd.DatetimeIndex([r["date"] for r in snapshot["daily"]]))
    grouped = {(d, i): [dict(event_at=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
                            source_sequence=r["sequence"], quantity=r["quantity"]) for r in records]
               for (d, i), records in data["sales"].items()}
    legacy = pure_window(matrix, grouped, snapshot["catalog"], data["forecasts"], snapshot["policies"],
                         dict(cover_days=7, safety_multiplier=1, receipts_initial=[]), "alert_replay", ORIGIN, data["end"])
    actual = research.simulate(data, config("A-base"))
    assert len(actual["ledger"]) == len(legacy["ledger"])
    for new, old in zip(actual["ledger"], legacy["ledger"], strict=True):
        for key in ("closing_qty", "ss", "rop", "target_stock", "recommended_qty", "shortage_qty"):
            assert new[key] == old[key]
    assert actual["metrics"]["early_rate"] == 1
    assert actual["metrics"]["fill_rate"] == legacy["summary"]["fill_rate"]


def test_daily_warning_can_recover_a_miss_without_changing_events():
    snapshot = fixture_snapshot(past=4, actual=lambda h: 28 if h == 10 else 0,
                               forecast=lambda h: [28] + [0] * 13 if h == 1 else [0] * 14)
    a, b = run(snapshot, "A-base"), run(snapshot, "B-daily")
    assert a["metrics"]["early_numerator"] == 0
    assert b["metrics"]["early_numerator"] == 1
    assert b["cases"][0]["as_of_date"] == ORIGIN + timedelta(days=1)
    assert research.compare_events(a, b) == []
    assert [r["closing_qty"] for r in a["ledger"]] == [r["closing_qty"] for r in b["ledger"]]


def test_daily_projection_outside_remaining_window_does_not_create_false_positive():
    snapshot = fixture_snapshot(actual=lambda h: 0, forecast=lambda h: [0] * 13 + [100] if h == 1 else [0] * 14)
    b = run(snapshot, "B-daily")
    assert b["alarms"][1]["predicted_depletion_date"] is None
    assert b["metrics"]["FP"] == 0


@pytest.mark.parametrize("mode,multiplier,ss", [
    ("days", "0.5", 1), ("days", "1", 2), ("days", "1.5", 3),
    ("volatility", "0.5", 3), ("volatility", "1", 6), ("volatility", "1.5", 8),
])
def test_c_safety_stock_modes_have_hand_calculated_values(mode, multiplier, ss):
    # [0..6] repeated four times has population std 2, mean 3.
    result = run(fixture_snapshot(past=list(range(7)) * 4), f"C-{mode}-m{multiplier}-cover7")
    assert result["initialization"][0]["base_qty"] == 21
    assert result["initialization"][0]["added_ss"] == ss
    assert result["ledger"][1]["closing_qty"] == 21 + ss - 1


def test_c_adds_ss_once_and_reports_moved_event():
    snapshot = fixture_snapshot()
    b, c = run(snapshot, "B-daily"), run(snapshot, "C-days-m1-cover7")
    assert c["initialization"][0]["initial_qty"] == 9
    assert c["ledger"][2]["closing_qty"] == 7
    assert c["cases"][0]["actual_depletion_date"] == ORIGIN + timedelta(days=9)
    assert research.compare_events(b, c)[0]["change"] == "moved"
    assert c["orders"] == []
    assert run(snapshot, "C-cover3")["initialization"][0]["initial_qty"] == 3
    assert run(snapshot, "C-cover14")["initialization"][0]["initial_qty"] == 14


def test_d_uses_moq_eta_seven_and_pending_without_direct_safety_addition():
    result = run(fixture_snapshot(), "D-days-m1-cover7")
    assert result["initialization"][0]["initial_qty"] == 7
    assert result["initialization"][0]["added_ss"] == 0
    first = result["orders"][0]
    assert first["ordered_on"] == ORIGIN
    assert first["ordered_qty"] == 5  # target10 - stock7 = 3 -> MOQ5
    assert first["eta"] == ORIGIN + timedelta(days=7)
    day1 = result["ledger"][1]
    assert (day1["pending_qty"], day1["recommended_qty"], day1["receipts_qty"]) == (5, 0, 0)
    assert all(r["receipts_qty"] == 0 for r in result["ledger"][:7])
    assert result["ledger"][7]["receipts_qty"] == 5
    assert result["all_period_inventory"]["ordered_qty"] == sum(o["ordered_qty"] for o in result["orders"] if not o["is_initial"])
    zero = run(fixture_snapshot(), "D-days-m0-cover7")
    assert all(r["ss"] == 0 for r in zero["ledger"])


def test_known_receipt_covers_order_and_is_not_available_before_eta():
    snapshot = fixture_snapshot()
    snapshot["receipts"] = [dict(item_id=1, ordered_on=ORIGIN.isoformat(),
        eta=(ORIGIN + timedelta(days=7)).isoformat(), ordered_qty=10, lot_key="synthetic-lot")]
    result = run(snapshot, "D-days-m1-cover7")
    assert result["ledger"][0]["recommended_qty"] == 0
    assert result["ledger"][6]["receipts_qty"] == 0
    assert result["ledger"][7]["receipts_qty"] == 10


def test_continuous_episodes_require_recovery_before_depleting_again():
    snapshot = fixture_snapshot(actual=lambda h: 7 if h == 1 else 1 if h == 7 else 0,
                               forecast=lambda h: [0] * 14)
    snapshot["receipts"] = [dict(item_id=1, ordered_on=ORIGIN.isoformat(),
        eta=(ORIGIN + timedelta(days=7)).isoformat(), ordered_qty=1, lot_key="recovery")]
    result = run(snapshot, "D-days-m0-cover7")
    assert [r["date"] for r in result["events"]] == [ORIGIN + timedelta(days=n) for n in (1, 7)]
    assert result["metrics"]["event_denominator"] == 2
    assert result["ledger"][7]["opening_qty"] == result["ledger"][7]["closing_qty"] == 0
    assert result["ledger"][7]["receipts_qty"] == 1


def test_missing_duplicate_fractional_or_unavailable_inputs_are_rejected():
    original = fixture_snapshot()
    variants = []
    a = deepcopy(original); a["daily"].pop(0); variants.append(a)
    a = deepcopy(original); a["daily"].append(deepcopy(a["daily"][0])); variants.append(a)
    a = deepcopy(original); a["daily"][0]["actual_available"] = False; variants.append(a)
    a = deepcopy(original); a["daily"][0]["quantity"] = .5; variants.append(a)
    a = deepcopy(original); a["forecasts"][0]["forecast"] = [1] * 13; variants.append(a)
    a = deepcopy(original); a["forecasts"][0]["forecast"][0] = float("nan"); variants.append(a)
    a = deepcopy(original); a["sales"].append(deepcopy(a["sales"][0])); variants.append(a)
    a = deepcopy(original); a["daily"][0]["item_id"] = True; variants.append(a)
    a = deepcopy(original); a["version"] = True; variants.append(a)
    for snapshot in variants:
        with pytest.raises((ValueError, DomainError)):
            research.prepare_inputs(snapshot)


def test_synthetic_cli_writes_unverified_results_and_checks_integrity(tmp_path, capsys):
    p = research.protocol()["validation"]
    snapshot = fixture_snapshot(length=(date.fromisoformat(p["end"]) - ORIGIN).days,
                                score_start=date.fromisoformat(p["score_start"]))
    source = tmp_path / "synthetic.json.gz"
    research.write_json(source, snapshot)
    assert research.main(["validate", "--snapshot", str(source), "--output-root", str(tmp_path / "runs")]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "calculated_unverified"
    folder = tmp_path / "runs" / output["output"].replace("\\", "/").split("/")[-1]
    manifest = research.read_json(folder / "manifest.json")
    assert manifest["independent_replay"] is False
    assert manifest["input_meta"]["provenance"] == "synthetic"
    assert len(research.read_json(folder / "metrics.json")) == 19
    assert not (folder / "selection_lock.json").exists()
    assert research.main(["verify", "--run-dir", str(folder)]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["status"] == "verified" and verified["independent_replay"] is True
    assert verified["evidence_class"] == "synthetic"
    assert research.read_json(folder / "manifest.json")["status"] == "calculated_unverified"
    (folder / "metrics.json").write_text("[]", encoding="utf-8")
    assert research.main(["verify", "--run-dir", str(folder)]) == 1
    capsys.readouterr()


def test_evaluate_rejects_unverified_lock_before_reading_database(tmp_path, monkeypatch, capsys):
    lock = tmp_path / "lock.json"
    research.write_json(lock, dict(validation_run=str(tmp_path / "missing")))
    def forbidden(*args, **kwargs):
        pytest.fail("Unverified selection must not read the test database")
    monkeypatch.setattr(research, "load_database_inputs", forbidden)
    assert research.main(["evaluate", "--selection-lock", str(lock), "--output-root", str(tmp_path / "runs")]) == 1
    assert not (tmp_path / "runs").exists()
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


def test_evaluate_honors_synthetic_selection_fixture_and_mandatory_controls(tmp_path, capsys):
    from core.hashes import digest
    from pathlib import Path

    p = research.protocol()
    validation = fixture_snapshot(length=(date.fromisoformat(p["validation"]["end"]) - ORIGIN).days,
                                   score_start=date.fromisoformat(p["validation"]["score_start"]))
    folder = research.calculate(validation, research.experiment_matrix(), tmp_path / "validation")
    from web.backend.research.inventory_alert_verification import verify_run

    # Actual independent verification, still explicitly synthetic rather than business evidence.
    manifest_hash = research.file_hash(folder / "manifest.json")
    verify_run(folder)
    lock_path = research.write_selection_lock(folder)
    lock = research.read_json(lock_path)
    start, finish = (date.fromisoformat(p["test"][k]) for k in ("origin", "end"))
    test = fixture_snapshot(origin=start, length=(finish - start).days,
                            score_start=date.fromisoformat(p["test"]["score_start"]))
    test["split"] = "test"
    snapshot_path = tmp_path / "test.json.gz"; research.write_json(snapshot_path, test)
    assert research.main(["evaluate", "--snapshot", str(snapshot_path), "--selection-lock", str(lock_path),
                          "--output-root", str(tmp_path / "test-runs")]) == 0
    result = json.loads(capsys.readouterr().out)
    metrics = research.read_json(Path(result["output"]) / "metrics.json")
    assert {r["config"]["id"] for r in metrics} == {
        "A-base", "B-daily", "C-days-m1-cover7", "D-days-m1-cover7"} | set(lock["selected_configs"])
    assert result["independent_replay"] is False
    lock["source_sha256"] = "changed"
    research.write_json(lock_path, lock)
    with pytest.raises(ValueError, match="lineage"):
        research.read_selection_lock(lock_path)


def test_continuous_scoring_uses_first_alarm_and_warmup_without_duplicate_events():
    event = dict(event_id="synthetic-event", item_id=1, date=ORIGIN + timedelta(days=10))
    result = dict(events=[event], orders=[], alarms=[dict(item_id=1, date=ORIGIN + timedelta(days=n),
        predicted_depletion_date=ORIGIN + timedelta(days=10)) for n in (0, 1, 3)])
    cases, metrics = research.score_continuous(dict(score_start=ORIGIN + timedelta(days=8),
                                                   end=ORIGIN + timedelta(days=20)), result)
    assert len(cases) == metrics["early_numerator"] == metrics["event_denominator"] == 1
    assert cases[0]["lead_days"] == 10
    assert metrics["precision"] is None  # Warmup alarms do not inflate scored alarm-day precision.


@pytest.mark.parametrize("order_day", [1, 2])
def test_continuous_scoring_does_not_call_intervention_or_incomplete_tail_false_positive(order_day):
    result = dict(events=[], orders=[dict(item_id=1, ordered_on=ORIGIN + timedelta(days=order_day),
        eta=ORIGIN + timedelta(days=order_day + 7))], alarms=[
        dict(item_id=1, date=ORIGIN + timedelta(days=1), predicted_depletion_date=ORIGIN + timedelta(days=8)),
        dict(item_id=1, date=ORIGIN + timedelta(days=19), predicted_depletion_date=ORIGIN + timedelta(days=25))])
    _, metrics = research.score_continuous(dict(score_start=ORIGIN + timedelta(days=1),
                                               end=ORIGIN + timedelta(days=20)), result)
    assert [r["status"] for r in result["alarm_evaluation"]] == ["intervened", "right_censored"]
    assert metrics["alarm_FP"] == 0
    assert metrics["intervened_count"] == metrics["right_censored_count"] == 1
    assert metrics["early_rate"] is None


def test_database_loader_freezes_only_bounded_validation_and_keeps_rows_unchanged(pg, tmp_path, monkeypatch):
    """Actual PostgreSQL read-only path; source audit is an explicitly injected synthetic boundary."""
    from dataclasses import replace
    from sqlalchemy import func, select
    from core.hashes import digest
    from modules.runs.models import Run
    from modules.forecasting.models import DailySales, ItemForecast
    from test_results_api import result_fixture
    from test_postgres_api import settings
    import src.data

    _, sessions = pg
    source_id, forecast_id, item = result_fixture(sessions)
    snap = fixture_snapshot()
    root = tmp_path / "sealed"
    p = research.protocol()
    p["validation"] = snap["period"]
    with sessions.begin() as session:
        source, forecast = session.get(Run, source_id), session.get(Run, forecast_id)
        source.config_snapshot = deepcopy(source.config_snapshot)
        source.config_snapshot["warehouse_snapshot"][0]["code"] = "WH-001"
        source.config_sha256 = digest(source.config_snapshot)
        forecast.config_snapshot = {**forecast.config_snapshot, "source_parent_config_sha256": source.config_sha256}
        forecast.config_sha256 = digest(forecast.config_snapshot)
        forecast.selection_sha256 = "d" * 64
        for role, parent in [("source_run", source), ("forecast_run", forecast)]:
            p[role] = str(parent.id)
            folder = root / str(parent.id); folder.mkdir(parents=True)
            research.write_json(folder / "sealed.json", dict(synthetic=True))
            parent.artifact_manifest = {"sealed.json": research.file_hash(folder / "sealed.json")}
        for role, kind in [("baseline_alert_run", "alert_replay"), ("baseline_policy_run", "policy_replay")]:
            attrs = {c.name: getattr(forecast, c.name) for c in Run.__table__.columns if c.name not in ("id", "created_at")}
            frozen = dict(source_parent_config_sha256=source.config_sha256,
                forecast_parent_config_sha256=forecast.config_sha256, policies=[dict(item_id=item,
                configured_rop_floor=9999, safety_days=9, moq=5, effective_from=ORIGIN.isoformat(), effective_to=None)],
                scenario=dict(settings=dict(receipts_initial=[])))
            attrs.update(kind=kind, request_key=role, forecast_run_id=forecast.id, as_of_date=ORIGIN,
                         config_snapshot=frozen, config_sha256=digest(frozen))
            baseline = Run(**attrs); session.add(baseline); session.flush()
            p[role] = str(baseline.id)
            folder = root / str(baseline.id); folder.mkdir(parents=True)
            research.write_json(folder / "sealed.json", dict(synthetic=True))
            baseline.artifact_manifest = {"sealed.json": research.file_hash(folder / "sealed.json")}
        for row in snap["daily"]:
            session.add(DailySales(source_import_run_id=source.id, item_id=item,
                date=date.fromisoformat(row["date"]), sales_qty=row["quantity"], order_count=row["quantity"], actual_available=True))
        for row in snap["forecasts"]:
            origin = date.fromisoformat(row["as_of_date"])
            for h, q in enumerate(row["forecast"], 1):
                session.add(ItemForecast(run_id=forecast.id, item_id=item, as_of_date=origin,
                    target_date=origin + timedelta(days=h), horizon_day=h, forecast_qty=q, actual_qty=None,
                    actual_available=False, item_share=1, weekday_weight=1 / 7, share_window_days=30, allocation_basis="synthetic"))
    with sessions() as session:
        before = (session.scalar(select(func.count()).select_from(Run)),
                  session.scalar(select(func.count()).select_from(DailySales)))
    rows = [dict(order_datetime=pd.Timestamp(r["date"], tz="UTC"), order_id=f"SYNTHETIC-{r['sequence']}",
        date=pd.Timestamp(r["date"]), destination_country="DemoLand", carrier="DemoCarrier", sku="DEMO-ESIM-01",
        product_type="eSIM", quantity=r["quantity"]) for r in snap["sales"]]
    monkeypatch.setattr(research, "protocol", lambda: deepcopy(p))
    monkeypatch.setattr(src.data, "audit_orders", lambda *args: (pd.DataFrame(rows), {"source_sha256_before": "a" * 64}))
    loaded = research.load_database_inputs("validation", replace(settings(tmp_path), output_root=root), root)
    research.prepare_inputs(loaded)
    assert loaded["meta"]["provenance"] == "local_frozen_db"
    assert loaded["policies"][0]["configured_rop_floor"] == 6  # Past28 × 6, never frozen9999.
    assert loaded["policies"][0]["safety_days"] == 2
    assert max(r["date"] for r in loaded["daily"]) == snap["period"]["end"]
    with sessions() as session:
        after = (session.scalar(select(func.count()).select_from(Run)),
                 session.scalar(select(func.count()).select_from(DailySales)))
    assert after == before
    from pathlib import Path
    from web.backend.research import inventory_alert_verification as verifier

    # Corroborate the reader against actual test-DB rows; raw audit/hash are explicit synthetic boundaries.
    original_sha = verifier.sha
    raw_path = replace(settings(tmp_path), output_root=root).order_source("orders_snapshot").resolve()
    monkeypatch.setattr(verifier, "sha", lambda path: "a"*64 if Path(path).resolve() == raw_path else original_sha(path))
    assert verifier.check_provenance(loaded, p, replace(settings(tmp_path), output_root=root), root) == "original_csv_and_readonly_db"
    for table, field, value in [("daily", "quantity", 99), ("forecasts", "forecast", [99]*14),
                                 ("policies", "configured_rop_floor", 9999), ("sales", "quantity", 99)]:
        tampered = deepcopy(loaded); tampered[table][0][field] = value
        with pytest.raises(ValueError):
            verifier.check_provenance(tampered, p, replace(settings(tmp_path), output_root=root), root)
