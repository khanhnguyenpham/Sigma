"""F4 independent verification: one validation-locked representative, no reselection."""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path

from core.hashes import code_digest
from web.backend.research import forecast_postprocessing_validation_verification as validation


ROOT = Path(__file__).resolve().parents[3]
F3_MANIFEST_SHA256 = "f53a99ad5e38929af10e5203a2110f38ad353ca0d68e19247bbce0d25c9fcf51"
F3_RECEIPT_SHA256 = "a5bf676a77f03d0b566bb657791917df373173268a49ac53578f8b84b69799fd"
F3_SELECTION_SHA256 = "33087505d977c046efa5f9f5e86e283caa0aefbf9e685bf5c1c4d636a1d9e4db"
PARAMETERS_FILE_SHA256 = "58052b211c908e1b9c3f19c4e04f455d968d35ed285979c3afc1f07380bdd737"


def load_locked_test(f3_run):
    f3_run = Path(f3_run).resolve()
    original, reference = validation.original, validation.reference
    for name, checksum in [("manifest.json", F3_MANIFEST_SHA256), ("verification.json", F3_RECEIPT_SHA256),
                            ("selection.json", F3_SELECTION_SHA256), ("parameters.json", PARAMETERS_FILE_SHA256)]:
        reference.require(original.sha(f3_run / name) == checksum)
    m, proof, selection, parameters = (original.read(f3_run / name) for name in
                                      ("manifest.json", "verification.json", "selection.json", "parameters.json"))
    reference.require(proof["status"] == "verified" and proof["candidates_verified"] == 13
                      and proof["manifest_sha256"] == F3_MANIFEST_SHA256 and proof["selected_candidate"] == selection["candidate_id"])
    reference.require(selection["status"] == "representative_locked" and selection["validation_only"] is True
                      and selection["test_opened"] is False and selection["parameters_sha256"] == parameters["sha256"])
    for rel, checksum in m["code_sha256"].items():
        path = (ROOT / rel).resolve()
        reference.require(path.is_relative_to(ROOT) and original.sha(path) == checksum)
    for name, checksum in m["artifacts"].items():
        path = (f3_run / name).resolve()
        reference.require(path.is_relative_to(f3_run) and original.sha(path) == checksum)
    calibration, _, _ = validation.load_sources(**m["sources"])
    c = reference.protocol()["calibration"]
    calibration_inputs = dict(catalog=calibration["catalog"],
        daily=[r for r in calibration["daily"] if c["label_start"] <= r["date"] <= c["cutoff"]],
        forecasts=[r for r in calibration["forecasts"] if c["origin_start"] <= r["as_of_date"] <= c["origin_end"]])
    expected_parameters = reference.verify_parameters(calibration_inputs["catalog"], calibration_inputs["daily"],
                                                       calibration_inputs["forecasts"], parameters)
    audit_run = Path(m["sources"]["audit_run"])
    audit_manifest = original.read(audit_run / "manifest.json")
    source, frozen = original.parent(audit_manifest["parents"]["test"], "test", audit_manifest["protocol"])
    baseline = original.read(audit_run / "test-replay.json.gz")
    from datetime import date
    cases, metric = original.score_events(baseline, date.fromisoformat(source["period"]["score_start"]),
                                          date.fromisoformat(source["period"]["end"]))
    original.equal(cases, frozen["cases"])
    original.equal(metric, {k: frozen["metrics"][k] for k in metric})
    reference.require((metric["early_numerator"], metric["event_denominator"]) == (193, 578))
    return source, baseline, cases, parameters, expected_parameters, selection["candidate_id"]


def verify(folder):
    original, reference = validation.original, validation.reference
    folder = Path(folder).resolve()
    m = original.read(folder / "manifest.json")
    reference.require(m["status"] == "calculated_unverified" and m["phase"] == "F4_test_only")
    reference.require(m["protocol_sha256"] == reference.PROTOCOL_SHA256 and m["protocol"] == reference.protocol())
    reference.require(m["source_F3_manifest_sha256"] == F3_MANIFEST_SHA256 and m["source_F3_receipt_sha256"] == F3_RECEIPT_SHA256)
    reference.require(m["application_code_sha256"] == code_digest() == reference.protocol()["source_pins"]["application_code_sha256"])
    reference.require(set(m["code_sha256"]) == {"web/backend/research/forecast_postprocessing_test.py",
                                              "web/backend/research/forecast_postprocessing_test_verification.py"})
    for rel, checksum in m["code_sha256"].items():
        path = (ROOT / rel).resolve()
        reference.require(path.is_relative_to(ROOT) and original.sha(path) == checksum)
    for rel, checksum in m["artifacts"].items():
        path = (folder / rel).resolve()
        reference.require(path.is_relative_to(folder) and original.sha(path) == checksum)
    source, baseline, baseline_cases, parameters, expected_parameters, representative = load_locked_test(m["source_F3_run"])
    reference.require(original.sha(folder / "parameters.json") == PARAMETERS_FILE_SHA256)
    expected_names = {candidate + "/" + name for candidate in ("C00", representative) for name in
                      ("paths.jsonl.gz", "alarms.json.gz", "cases.json.gz", "forecast_metrics.json.gz", "summary.json")}
    expected_names |= {"execution_lock.json", "parameters.json", "summary.json", "evaluation.json", "summary.csv", "report.html"}
    reference.require(set(m["artifacts"]) == expected_names)
    summaries = []
    p = reference.protocol()
    for candidate in ("C00", representative):
        spec = next(s for s in p["candidates"] if s["id"] == candidate)
        summary = validation.verify_candidate_export(folder / candidate, source, baseline, baseline_cases, expected_parameters, spec)
        reference.require(summary["metrics"]["event_denominator"] == 578 and summary["valid"] is True)
        summaries.append(summary)
        print("Independently verified test " + candidate, flush=True)
    original.equal(original.read(folder / "summary.json"), summaries)
    target = p["evaluation"]["test_target"]
    expected = dict(representative_id=representative, selected_on="validation", parameters_sha256=parameters["sha256"],
                    target=target, target_met=summaries[1]["metrics"]["early_numerator"] >= target["early_numerator"],
                    retrospective=True, reselection=False, source_F3_manifest_sha256=F3_MANIFEST_SHA256)
    original.equal(original.read(folder / "evaluation.json"), expected)
    rows = [["ID", "Kind", "Early", "Rate", "Precision", "Recall", "FP", "Alarm item-days", "Date MAE", "Item WAPE", "Item bias"]]
    for summary in original.read(folder / "summary.json"):
        metric = summary["metrics"]
        scores = original.read(folder / summary["candidate_id"] / "forecast_metrics.json.gz")
        item = next(x for x in scores if x["scope"] == "items_pooled" and x["horizon"] == "daily_H1_14")
        pct = lambda x: format(x * 100, ".4f") + "%" if x is not None else "null"
        number = lambda x: format(x, ".6f") if x is not None else "null"
        rows.append([summary["candidate_id"], summary["kind"], str(metric["early_numerator"]) + "/" + str(metric["event_denominator"]),
                     pct(metric["early_rate"]), pct(metric["precision"]), pct(metric["recall"]), str(metric["alarm_FP"]),
                     str(summary["alarm_item_days"]), number(metric["date_mae"]), pct(item["wape"]), number(item["bias"])])
    with (folder / "summary.csv").open(encoding="utf-8", newline="") as stream:
        original.equal(list(csv.reader(stream)), rows)
    table = original.Table()
    table.feed((folder / "report.html").read_text(encoding="utf-8"))
    original.equal(table.rows, rows)
    proof = dict(status="verified", phase="F4_test_only", candidates_verified=2, representative_id=representative,
                 target_met=expected["target_met"], retrospective=True, reselection=False,
                 manifest_sha256=original.sha(folder / "manifest.json"), source_F3_manifest_sha256=F3_MANIFEST_SHA256,
                 parameters_file_sha256=PARAMETERS_FILE_SHA256, application_code_sha256=code_digest())
    receipt = folder / "verification.json"
    if receipt.exists():
        previous = original.read(receipt)
        stamp = previous.pop("created_at")
        original.equal(previous, proof)
        proof["created_at"] = stamp
    else:
        proof["created_at"] = datetime.now(timezone.utc).isoformat()
        with receipt.open("x", encoding="utf-8") as stream:
            json.dump(proof, stream, indent=2, sort_keys=True, allow_nan=False)
    return proof
