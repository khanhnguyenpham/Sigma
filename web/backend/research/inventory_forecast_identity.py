"""F1 only: check the original H14 forecast on sealed, fixed inventory paths."""

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import gzip
import json
import math
from pathlib import Path
import sys
import uuid

from core.hashes import code_digest, digest
from modules.alerts.service import project
from web.backend.research import inventory_alert_opportunity_audit as audit
from web.backend.research import inventory_alert_opportunity_verification as independent


AUDIT_MANIFEST_SHA256 = "23ed307ea2e3fdf86d3f91c2759bc4c6f52deaccc6e199e1c1bb97ee928a35e9"
AUDIT_RECEIPT_SHA256 = "5af9a8bf253d7fa6fe0973de2e77b6016fab226c2e9a167c36b34670a622b8d7"
FIXED_TABLES = ("initialization", "ledger", "transactions", "orders", "events")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def indexed(rows, day_field):
    require(all(type(r["item_id"]) is int for r in rows), "Invalid item identifier")
    result = {(r[day_field], r["item_id"]): r for r in rows}
    require(len(result) == len(rows), "Duplicate item/date row")
    return result


def coverage(snapshot, baseline):
    """Check every known item, decision origin, H14 value and observed history day."""
    start, end = (date.fromisoformat(snapshot["period"][k]) for k in ("origin", "end"))
    catalog = snapshot["catalog"]
    ids = {r["item_id"] for r in catalog}
    require(bool(ids) and len(ids) == len(catalog), "Missing or duplicate catalog item")
    require(all(type(r["item_id"]) is int and r["first_seen_date"] <= str(start)
                for r in catalog), "Catalog cohort differs from the fixed baseline")
    require(start <= end, "Invalid period")
    expected = {(str(start + timedelta(days=n)), i)
                for n in range((end - start).days + 1) for i in ids}
    ledger = indexed(baseline["ledger"], "date")
    forecasts = indexed(snapshot["forecasts"], "as_of_date")
    require(set(ledger) == set(forecasts) == expected, "Decision/forecast coverage differs")
    require(all(r["forecast_as_of_date"] == r["date"] for r in ledger.values()),
            "Forecast origin differs from decision date")
    for row in forecasts.values():
        vector = row["forecast"]
        require(isinstance(vector, list) and len(vector) == 14, "Incomplete H14 vector")
        require(all(type(q) in (int, float) and math.isfinite(q) and q >= 0
                    for q in vector), "Invalid forecast value")
    daily = indexed(snapshot["daily"], "date")
    history = {(str(start + timedelta(days=n)), i)
               for n in range(-27, (end - start).days + 1) for i in ids}
    require(set(daily) == history, "Observed history coverage differs")
    require(all(r["actual_available"] is True and type(r["quantity"]) is int
                and r["quantity"] >= 0 for r in daily.values()), "Missing or invalid actual")
    require(all(type(r["closing_qty"]) is int and r["closing_qty"] >= 0
                for r in ledger.values()), "Invalid closing stock")
    require(all(o["item_id"] in ids and type(o["ordered_qty"]) is int
                and o["ordered_qty"] >= 0 and type(o["is_initial"]) is bool
                for o in baseline["orders"]), "Invalid frozen receipt")
    return forecasts


def known_receipts(orders, day):
    """Use only initial lots or orders made before today's new recommendation."""
    receipts = defaultdict(int)
    for order in orders:
        eta = date.fromisoformat(order["eta"])
        if day < eta <= day + timedelta(days=14) and (
            order["is_initial"] or order["ordered_on"] < str(day)
        ):
            receipts[eta] += order["ordered_qty"]
    return dict(receipts)


def reference_projection(origin, on_hand, forecast, receipts):
    """Independent scalar calculation, including paths from already depleted stock."""
    balance, first_zero, rows = float(on_hand), None, []
    for h, demand in enumerate(forecast, 1):
        target = origin + timedelta(days=h)
        arrival = receipts.get(target, 0)
        balance += arrival
        balance -= demand
        if balance < 0:
            balance = 0.0
        rows.append(dict(date=str(target), closing_forecast=balance, receipts_qty=arrival))
        if balance == 0 and first_zero is None:
            first_zero = target
    if on_hand == 0:
        state, first_zero, lead = "already_depleted", origin, 0
    else:
        lead = (first_zero - origin).days if first_zero else None
        state = "not_within_horizon" if lead is None else "early" if lead >= 7 else "urgent"
    return dict(state=state, predicted_depletion_date=first_zero, lead_days=lead, projection=rows)


def check_split(snapshot, frozen, baseline, projection_stream=None):
    """Identity only; never create orders or pass a candidate into policy replay."""
    vectors = coverage(snapshot, baseline)
    fixed_before = {k: digest(frozen[k]) for k in FIXED_TABLES}
    forecast_before = digest(snapshot["forecasts"])
    audit.compare_replay(baseline, frozen)
    independent.equal(independent.reconstruct(snapshot, frozen), baseline)
    by_item = defaultdict(list)
    for order in baseline["orders"]:
        by_item[order["item_id"]].append(order)
    alarms = []
    for row in baseline["ledger"]:
        origin = date.fromisoformat(row["date"])
        vector = list(vectors[(row["date"], row["item_id"])]["forecast"])
        receipts = known_receipts(by_item[row["item_id"]], origin)
        actual = project(origin, row["closing_qty"], vector, receipts)
        expected = reference_projection(origin, row["closing_qty"], vector, receipts)
        independent.equal(actual, expected)
        predicted = actual["predicted_depletion_date"]
        alarms.append(dict(date=row["date"], item_id=row["item_id"],
                           origin_on_hand=row["closing_qty"],
                           predicted_depletion_date=str(predicted)
                           if predicted and actual["state"] != "already_depleted" else None))
        if projection_stream is not None:
            record = dict(date=row["date"], item_id=row["item_id"], **actual)
            projection_stream.write((json.dumps(record, sort_keys=True, default=str,
                                                allow_nan=False) + "\n").encode("utf-8"))
    result = dict(baseline, alarms=alarms)
    audit.compare_replay(result, frozen)
    period = snapshot["period"]
    score_start, end = (date.fromisoformat(period[k]) for k in ("score_start", "end"))
    cases, metrics = audit.score(result, score_start, end)
    independent_cases, independent_metrics = independent.score_events(result, score_start, end)
    independent.equal(cases, independent_cases)
    independent.equal(metrics, independent_metrics)
    independent.equal(cases, frozen["cases"])
    independent.equal(metrics, {k: frozen["metrics"][k] for k in metrics})
    require(fixed_before == {k: digest(frozen[k]) for k in FIXED_TABLES}, "Frozen tables mutated")
    require(forecast_before == digest(snapshot["forecasts"]), "Original forecast mutated")
    summary = dict(identity_passed=True, item_count=len(snapshot["catalog"]),
                   forecast_vectors=len(vectors), forecast_values=len(vectors) * 14,
                   projection_rows_checked=len(alarms) * 14, alarm_rows_checked=len(alarms),
                   forecast_sha256=forecast_before, fixed_table_sha256=fixed_before, metrics=metrics)
    return summary, cases, alarms


def load_audit(folder):
    folder = Path(folder).resolve()
    require(audit.sha(folder / "manifest.json") == AUDIT_MANIFEST_SHA256, "Audit manifest changed")
    require(audit.sha(folder / "verification.json") == AUDIT_RECEIPT_SHA256, "Audit receipt changed")
    manifest, proof = audit.read(folder / "manifest.json"), audit.read(folder / "verification.json")
    protocol = audit.read(audit.PROTOCOL)
    require(digest(protocol) == audit.PROTOCOL_SHA256 and manifest["protocol"] == protocol,
            "Original protocol differs")
    require(code_digest() == protocol["application_code_sha256"], "Application code differs")
    require(audit.sha(audit.__file__) == manifest["research_code_sha256"]
            and audit.sha(independent.__file__) == manifest["verifier_code_sha256"],
            "Original audit code differs")
    require(proof["status"] == "verified" and proof["manifest_sha256"] == AUDIT_MANIFEST_SHA256,
            "Audit proof differs")
    for name, checksum in manifest["artifacts"].items():
        path = (folder / name).resolve()
        require(path.is_relative_to(folder) and audit.sha(path) == checksum, "Audit artifact differs")
    return manifest, protocol


def run_identity(audit_run, output_root):
    audit_run = Path(audit_run).resolve()
    manifest, protocol = load_audit(audit_run)
    folder = Path(output_root).resolve() / ("forecast-identity-f1-" + str(uuid.uuid4()))
    require(not folder.is_relative_to(audit_run), "Output cannot be inside the frozen audit")
    for parent in manifest["parents"].values():
        require(not folder.is_relative_to(Path(parent).resolve()), "Output cannot be inside a frozen parent")
    folder.mkdir(parents=True, exist_ok=False)
    protected = {str(p): audit.sha(p) for base in [audit_run, *map(Path, manifest["parents"].values())]
                 for p in base.rglob("*") if p.is_file()}
    summaries = {}
    for split in ("validation", "test"):
        source, frozen = audit.load_parent(manifest["parents"][split], split, protocol)
        baseline = audit.read(audit_run / (split + "-replay.json.gz"))
        with (folder / (split + "-projections.jsonl.gz")).open("xb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
                summary, cases, alarms = check_split(source, frozen, baseline, stream)
        independent.equal(cases, audit.read(audit_run / (split + "-cases.json.gz")))
        require((summary["metrics"]["early_numerator"], summary["metrics"]["event_denominator"])
                == (protocol[split]["early_numerator"], protocol[split]["event_denominator"]),
                "Baseline event counts differ")
        audit.write(folder / (split + "-cases.json.gz"), cases)
        audit.write(folder / (split + "-alarms.json.gz"), alarms)
        summaries[split] = summary
        print("F1 identity passed: " + split, file=sys.stderr, flush=True)
    require(all(audit.sha(p) == h for p, h in protected.items()), "Frozen files changed")
    require(code_digest() == protocol["application_code_sha256"], "Application code changed during F1")
    audit.write(folder / "summary.json", summaries)
    audit.write(folder / "manifest.json", dict(
        status="identity_passed", phase="F1_only", created_at=datetime.now(timezone.utc).isoformat(),
        evidence_class="previously_verified_frozen_inputs_and_results", raw_csv_or_db_reaudit=False,
        candidate_experiments=False, f2_implemented=False, github_actions=False,
        audit_manifest_sha256=AUDIT_MANIFEST_SHA256, audit_receipt_sha256=AUDIT_RECEIPT_SHA256,
        application_code_sha256=code_digest(), f1_code_sha256=audit.sha(__file__),
        protocol_sha256=audit.PROTOCOL_SHA256, source_audit=str(audit_run),
        parents=manifest["parents"], original_files_unchanged=len(protected),
        artifacts={p.name: audit.sha(p) for p in folder.iterdir() if p.is_file()},
    ))
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-run", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("outputs/research/forecast-identity-f1"))
    args = parser.parse_args(argv)
    try:
        output = run_identity(args.audit_run, args.output_root)
        print(json.dumps(dict(status="identity_passed", output=str(output))))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status="failed", error_type=type(exc).__name__,
                              reason=str(exc) if isinstance(exc, ValueError) else "F1 input/check failure")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
