"""Independent F3 validation-only verification and forecast/report arithmetic."""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import csv
import gzip
import json
import math
from pathlib import Path

from core.hashes import code_digest, digest
from web.backend.research import forecast_postprocessing_verification as reference
from web.backend.research import inventory_alert_opportunity_verification as original


ROOT = Path(__file__).resolve().parents[3]
F2_LOCK_SHA256 = "deb5dcec7417a2134a6d58695d96bc50fe41156d34683666fa122030d668c934"
HORIZONS = ["daily_H1_7", "daily_H8_14", "daily_H1_14"] + [f"cumulative_H{h:02}" for h in range(1, 15)]


def load_sources(audit_run, f1_run, f2_lock):
    p = reference.protocol()
    pins = p["source_pins"]
    audit_run, f1_run, f2_lock = Path(audit_run).resolve(), Path(f1_run).resolve(), Path(f2_lock).resolve()
    reference.require(original.sha(f2_lock) == F2_LOCK_SHA256)
    lock = original.read(f2_lock)
    for rel, checksum in lock["files"].items():
        path = (ROOT / rel).resolve()
        reference.require(path.is_relative_to(ROOT) and original.sha(path) == checksum)
    for folder, name, field in [(audit_run, "manifest.json", "audit_manifest_sha256"),
                                 (audit_run, "verification.json", "audit_receipt_sha256"),
                                 (f1_run, "manifest.json", "f1_manifest_sha256"),
                                 (f1_run, "summary.json", "f1_summary_sha256")]:
        reference.require(original.sha(folder / name) == pins[field])
    am, proof = original.read(audit_run / "manifest.json"), original.read(audit_run / "verification.json")
    reference.require(proof["status"] == "verified" and proof["manifest_sha256"] == pins["audit_manifest_sha256"])
    reference.require(code_digest() == pins["application_code_sha256"] == am["application_code_sha256"])
    reference.require(am["protocol_sha256"] == pins["original_protocol_sha256"])
    reference.require(original.sha(original.__file__) == am["verifier_code_sha256"])
    for folder, manifest in [(audit_run, am), (f1_run, original.read(f1_run / "manifest.json"))]:
        for name, checksum in manifest["artifacts"].items():
            path = (folder / name).resolve()
            reference.require(path.is_relative_to(folder) and original.sha(path) == checksum)
    source, frozen = original.parent(am["parents"]["validation"], "validation", am["protocol"])
    baseline = original.read(audit_run / "validation-replay.json.gz")
    cases, metrics = original.score_events(baseline, date.fromisoformat(source["period"]["score_start"]),
                                           date.fromisoformat(source["period"]["end"]))
    original.equal(cases, frozen["cases"])
    original.equal(metrics, {k: frozen["metrics"][k] for k in metrics})
    reference.require((metrics["early_numerator"], metrics["event_denominator"]) == (151, 486))
    return source, baseline, cases


def metric_row(scope, key, horizon, sums, quantile):
    expected, n, total, absolute, error, covered, loss = sums
    n, expected = int(n), int(expected)
    return dict(scope=scope, key=key, horizon=horizon, expected=expected, observed=n,
                coverage=n / expected if expected else None, actual_quantity=float(total),
                mae=float(absolute / n) if n else None, wape=float(absolute / total) if total else None,
                bias=float(error / n) if n else None, bias_ratio=float(error / total) if total else None,
                empirical_coverage=float(covered / n) if n and quantile is not None else None,
                pinball_loss=float(loss / n) if n and quantile is not None else None)


class ReferenceScores:
    """Scalar observations, independent of the vectorized producer accumulators."""

    def __init__(self, snapshot, quantile=None):
        self.catalog = snapshot["catalog"]
        self.actual = {(r["date"], r["item_id"]): r["quantity"] if r["actual_available"] else None for r in snapshot["daily"]}
        self.start, self.end = snapshot["period"]["score_start"], snapshot["period"]["end"]
        self.effective = reference.protocol()["effective_from"]
        self.quantile = quantile
        self.sums = defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0, 0, 0.0])

    def add(self, scope, key, horizon, f, y):
        s = self.sums[(scope, key, horizon)]
        s[0] += 1
        if y is None:
            return
        s[1] += 1
        s[2] += y
        s[3] += abs(f - y)
        s[4] += f - y
        if self.quantile is not None and horizon.startswith("cumulative"):
            s[5] += int(y <= f)
            s[6] += (self.quantile - int(y < f)) * (y - f)

    def observe(self, origin, values):
        if str(origin) < self.effective:
            return
        days = [str(origin + timedelta(days=h)) for h in range(1, 15)]
        mask = [self.start <= d <= self.end for d in days]
        groups = []
        by_route = defaultdict(list)
        actuals = {}
        for item in self.catalog:
            i = item["item_id"]
            actuals[i] = [self.actual.get((d, i)) for d in days]
            groups.extend([("item", str(i), values[i], actuals[i]), ("items_pooled", "all", values[i], actuals[i])])
            by_route[reference.route(item)].append(i)
        for route, members in by_route.items():
            f = [math.fsum(values[i][h] for i in members) for h in range(14)]
            y = [math.fsum(actuals[i][h] for i in members) if all(actuals[i][h] is not None for i in members) else None for h in range(14)]
            groups.extend([("route", route, f, y), ("routes_pooled", "all", f, y)])
        for scope, key, f, y in groups:
            for h in range(14):
                if mask[h]:
                    self.add(scope, key, HORIZONS[int(h >= 7)], f[h], y[h])
                    self.add(scope, key, HORIZONS[2], f[h], y[h])
                if all(mask[:h + 1]):
                    self.add(scope, key, HORIZONS[h + 3], math.fsum(f[:h + 1]),
                             math.fsum(y[:h + 1]) if all(z is not None for z in y[:h + 1]) else None)

    def rows(self):
        return [metric_row(scope, key, horizon, sums,
                           self.quantile if horizon.startswith("cumulative") else None)
                for (scope, key, horizon), sums in sorted(self.sums.items()) if sums[0]]


def diagnostics(cases, alarms, baseline_cases, period):
    start, end = period["score_start"], period["end"]
    scored = [a for a in alarms if start <= a["date"] <= end and a["predicted_depletion_date"] is not None]
    days = [str(date.fromisoformat(start) + timedelta(days=n)) for n in range((date.fromisoformat(end) - date.fromisoformat(start)).days + 1)]
    paired = [c for c in cases if c["alarm_date"]]
    error = lambda c: (date.fromisoformat(c["predicted_depletion_date"]) - date.fromisoformat(c["date"])).days
    baseline = {c["event_id"]: c for c in baseline_cases}
    reference.require(set(baseline) == {c["event_id"] for c in cases})
    common = [c for c in paired if baseline[c["event_id"]]["alarm_date"]]
    avg = lambda xs: math.fsum(xs) / len(xs) if xs else None
    return dict(late_count=sum(c["alarm_date"] is not None and not c["early"] for c in cases),
                no_alarm_count=sum(c["alarm_date"] is None for c in cases),
                gained_early=sum(c["early"] and not baseline[c["event_id"]]["early"] for c in cases),
                lost_early=sum(not c["early"] and baseline[c["event_id"]]["early"] for c in cases),
                alarm_item_days=len(scored), alarm_item_days_all_period=sum(a["predicted_depletion_date"] is not None for a in alarms),
                distinct_items=len({a["item_id"] for a in scored}), alarms_per_day=len(scored) / len(days),
                daily_alarm_counts=[dict(date=d, count=sum(a["date"] == d for a in scored)) for d in days],
                date_pairs=len(paired), date_bias=avg([error(c) for c in paired]), common_pairs=len(common),
                common_date_mae=avg([abs(error(c)) for c in common]), common_date_bias=avg([error(c) for c in common]),
                baseline_common_date_mae=avg([abs(error(baseline[c["event_id"]])) for c in common]),
                baseline_common_date_bias=avg([error(baseline[c["event_id"]]) for c in common]))


def verify_candidate_export(folder, source, baseline, baseline_cases, expected_parameters, spec):
    fixed = digest(baseline)
    candidate = spec["id"]
    scores = ReferenceScores(source, spec.get("quantile"))
    ledger = {(r["date"], r["item_id"]): r for r in baseline["ledger"]}
    seen, alarms, values = set(), [], {}
    by_item = defaultdict(list)
    for order in baseline["orders"]:
        by_item[order["item_id"]].append(order)
    current, day_values = None, {}
    with gzip.open(folder / "paths.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            reference.require(set(row) == {"date", "item_id", "forecast", "projection"} and type(row["item_id"]) is int)
            key = (row["date"], row["item_id"])
            reference.require(key in ledger and key not in seen)
            seen.add(key)
            origin = date.fromisoformat(row["date"])
            if row["date"] != current:
                if current is not None:
                    scores.observe(date.fromisoformat(current), day_values)
                reference.require(current is None or current < row["date"])
                current, day_values = row["date"], {}
                values = reference.forecast_reference(candidate, origin, source["catalog"], source["daily"], source["forecasts"], expected_parameters)
            original.equal(row["forecast"], values[row["item_id"]])
            day_values[row["item_id"]] = row["forecast"]
            receipts = defaultdict(int)
            for order in by_item[row["item_id"]]:
                eta = date.fromisoformat(order["eta"])
                if origin < eta <= origin + timedelta(days=14) and (order["is_initial"] or order["ordered_on"] < row["date"]):
                    receipts[eta] += order["ordered_qty"]
            path = reference.projection_reference(origin, ledger[key]["closing_qty"], row["forecast"], receipts)
            original.equal(row["projection"], path)
            alarms.append(dict(date=row["date"], item_id=row["item_id"], origin_on_hand=ledger[key]["closing_qty"],
                               predicted_depletion_date=path["predicted_depletion_date"] if path["state"] != "already_depleted" else None))
    if current is not None:
        scores.observe(date.fromisoformat(current), day_values)
    reference.require(seen == set(ledger))
    original.equal(original.read(folder / "alarms.json.gz"), alarms)
    cases, metrics = original.score_events(dict(baseline, alarms=alarms), date.fromisoformat(source["period"]["score_start"]), date.fromisoformat(source["period"]["end"]))
    original.equal(original.read(folder / "cases.json.gz"), cases)
    forecast_metrics = scores.rows()
    original.equal(original.read(folder / "forecast_metrics.json.gz"), forecast_metrics)
    extra = diagnostics(cases, alarms, baseline_cases, source["period"])
    expected = dict(candidate_id=candidate, kind=spec["kind"], valid=all(r["coverage"] == 1 for r in forecast_metrics),
                    metrics=metrics, alarm_item_days=extra["alarm_item_days"], diagnostics=extra,
                    fixed_input_sha256=fixed, forecast_paths=len(seen), projection_rows=len(seen) * 14)
    original.equal(original.read(folder / "summary.json"), expected)
    if candidate == "C00":
        original.equal(cases, baseline_cases)
        original.equal(alarms, baseline["alarms"])
    return expected


def verify(folder):
    folder = Path(folder).resolve()
    m = original.read(folder / "manifest.json")
    p = reference.protocol()
    reference.require(m["status"] == "calculated_unverified" and m["phase"] == "F3_validation_only")
    reference.require(m["protocol_sha256"] == reference.PROTOCOL_SHA256 and m["protocol"] == p)
    reference.require(m["application_code_sha256"] == code_digest() == p["source_pins"]["application_code_sha256"])
    for rel, checksum in m["code_sha256"].items():
        path = (ROOT / rel).resolve()
        reference.require(path.is_relative_to(ROOT) and original.sha(path) == checksum)
    for name, checksum in m["artifacts"].items():
        path = (folder / name).resolve()
        reference.require(path.is_relative_to(folder) and original.sha(path) == checksum)
    names = {c["id"] + "/" + name for c in p["candidates"] for name in
             ("paths.jsonl.gz", "alarms.json.gz", "cases.json.gz", "forecast_metrics.json.gz", "summary.json")}
    names |= {"execution_lock.json", "parameters.json", "summary.json", "selection.json", "summary.csv", "report.html"}
    reference.require(set(m["artifacts"]) == names)
    reference.require(set(m["code_sha256"]) == {"web/backend/research/forecast_postprocessing_validation.py",
                                             "web/backend/research/forecast_postprocessing_validation_verification.py"})
    source, baseline, baseline_cases = load_sources(**m["sources"])
    parameters = original.read(folder / "parameters.json")
    expected_parameters = reference.verify_parameters(source["catalog"], source["daily"], source["forecasts"], parameters)
    fixed = digest(baseline)
    summary = []
    for spec in p["candidates"]:
        summary.append(verify_candidate_export(folder / spec["id"], source, baseline, baseline_cases, expected_parameters, spec))
        print("Independently verified validation " + spec["id"], flush=True)
    original.equal(original.read(folder / "summary.json"), summary)
    headers = ["ID", "Kind", "Early", "Rate", "Precision", "Recall", "FP", "Alarm item-days", "Date MAE", "Item WAPE", "Item bias"]
    report_rows = [headers]
    for row in original.read(folder / "summary.json"):
        metric = row["metrics"]
        scores = original.read(folder / row["candidate_id"] / "forecast_metrics.json.gz")
        item = next(r for r in scores if r["scope"] == "items_pooled" and r["horizon"] == "daily_H1_14")
        pct = lambda x: format(x * 100, ".4f") + "%" if x is not None else "null"
        number = lambda x: format(x, ".6f") if x is not None else "null"
        report_rows.append([row["candidate_id"], row["kind"], str(metric["early_numerator"]) + "/" + str(metric["event_denominator"]),
                            pct(metric["early_rate"]), pct(metric["precision"]), pct(metric["recall"]), str(metric["alarm_FP"]),
                            str(row["alarm_item_days"]), number(metric["date_mae"]), pct(item["wape"]), number(item["bias"])])
    with (folder / "summary.csv").open(encoding="utf-8", newline="") as stream:
        original.equal(list(csv.reader(stream)), report_rows)
    table = original.Table()
    table.feed((folder / "report.html").read_text(encoding="utf-8"))
    original.equal(table.rows, report_rows)
    eligible = [r for r in summary if r["valid"] and r["metrics"]["event_denominator"] == 486
                and r["metrics"]["early_numerator"] >= 219 and r["metrics"]["precision"] is not None]
    order = {s["id"]: n for n, s in enumerate(p["candidates"])}
    winner = min(eligible, key=lambda r: (-r["metrics"]["precision"], r["alarm_item_days"], order[r["candidate_id"]]))["candidate_id"] if eligible else None
    selection = original.read(folder / "selection.json")
    original.equal(selection, dict(candidate_id=winner, parameters_sha256=parameters["sha256"], protocol_sha256=reference.PROTOCOL_SHA256,
                                   validation_only=True, test_opened=False, status="representative_locked" if winner else "no_candidate_reached_target"))
    reference.require(digest(baseline) == fixed)
    proof = dict(status="verified", phase="F3_validation_only", candidates_verified=len(summary), selected_candidate=winner,
                 manifest_sha256=original.sha(folder / "manifest.json"), protocol_sha256=reference.PROTOCOL_SHA256,
                 test_opened=False, application_code_sha256=code_digest())
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
