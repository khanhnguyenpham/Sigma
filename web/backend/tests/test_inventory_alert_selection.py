"""Predeclared validation-only representative selection; no private data."""

from copy import deepcopy
from datetime import date
from pathlib import Path
import json

import pytest
from web.backend.research import inventory_alert_experiments as r
from web.backend.research import inventory_alert_verification as v
from web.backend.tests.test_inventory_alert_experiments import fixture_snapshot, ORIGIN, config


def row(identity, n, d, shortage, mean, ordered):
    return dict(config=config(identity), early_numerator=n, event_denominator=d,
                early_rate=n/d if d else None, shortage_qty=shortage, mean_closing=mean, ordered_qty=ordered)


def samples():
    return [row("C-days-m0.5-cover7", 3, 5, 7, 4, 10), row("C-days-m1-cover7", 6, 10, 4, 5, 5),
            row("D-days-m0-cover7", 0, 0, 5, 1, 1), row("D-days-m1-cover7", 0, 4, 3, 2, 2)]


def test_three_objectives_exact_rates_null_zero_and_dedup_have_known_winners():
    selected, details = r.select_representatives(samples())
    assert selected == ["C-days-m1-cover7", "C-days-m0.5-cover7", "D-days-m1-cover7", "D-days-m0-cover7"]
    assert [d["config_id"] for d in details] == [selected[0], selected[0], selected[1], selected[2], selected[2], selected[3]]
    assert (selected, details) == v.representatives(samples())


def test_ties_use_quantity_then_id_and_all_null_early_is_skipped():
    rows = [row(i, 0, 0, 2, 2, 2) for i in ("C-cover3", "C-cover14", "D-cover3", "D-cover14")]
    selected, details = r.select_representatives(rows)
    assert selected == ["C-cover14", "D-cover14"]
    assert details[0]["config_id"] is details[3]["config_id"] is None
    assert (selected, details) == v.representatives(list(reversed(rows)))


@pytest.mark.parametrize("area", ["rate", "counts", "mean", "duplicate"])
def test_invalid_or_nonfinite_selection_values_are_rejected(area):
    rows = samples()
    if area == "rate": rows[0]["early_rate"] = .99
    elif area == "counts": rows[0]["early_numerator"] = True
    elif area == "mean": rows[0]["mean_closing"] = float("nan")
    else: rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError): r.select_representatives(rows)


@pytest.fixture
def validation(tmp_path):
    p = r.protocol()["validation"]
    snapshot = fixture_snapshot(length=(date.fromisoformat(p["end"])-ORIGIN).days,
                                score_start=date.fromisoformat(p["score_start"]))
    return r.calculate(snapshot, r.experiment_matrix(), tmp_path)


def test_select_cli_verifies_and_seals_idempotently_without_modifying_bundle(validation, capsys):
    folder = validation
    originals = {str(p.relative_to(folder)): r.file_hash(p) for p in folder.rglob("*") if p.is_file()}
    assert r.main(["select", "--run-dir", str(folder)]) == 0
    answer = json.loads(capsys.readouterr().out)
    assert answer["status"] == "validation_selection_locked"
    path = Path(answer["selection_lock"]); first = path.read_bytes()
    proof = (folder/"verification.json").read_bytes()
    lock, configs = r.read_selection_lock(path)
    assert lock["selected_configs"] == answer["selected_configs"]
    assert len(lock["selected_configs"]) <= 6
    assert {c["id"] for c in configs} >= {"A-base", "B-daily", "C-days-m1-cover7", "D-days-m1-cover7"}
    assert r.main(["select", "--run-dir", str(folder)]) == 0
    capsys.readouterr()
    assert first == path.read_bytes() and proof == (folder/"verification.json").read_bytes()
    assert all(r.file_hash(folder/name) == h for name, h in originals.items())
    assert (folder/"validation-comparison.csv").is_file() and (folder/"validation-comparison.html").is_file()
    changed = r.read_json(path); changed["selection_details"][0]["config_id"] = "C-cover3"
    r.write_json(path, changed)
    with pytest.raises(ValueError): r.read_selection_lock(path)


def test_selection_refuses_test_split_before_verifying_or_reading_metrics(tmp_path, monkeypatch):
    r.write_json(tmp_path/"manifest.json", dict(split="test"))
    def forbidden(*args, **kwargs): pytest.fail("Selection inspected test outcomes")
    monkeypatch.setattr(v, "verify_run", forbidden)
    with pytest.raises(ValueError, match="test outcomes"):
        r.write_selection_lock(tmp_path)
