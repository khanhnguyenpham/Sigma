"""F3 only: frozen-path validation, complete locked grid, no test execution."""

import argparse
from collections import defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import html
import json
from pathlib import Path
import sys
import traceback
import uuid

import numpy as np

from core.hashes import code_digest, digest
from web.backend.research import forecast_postprocessing as post
from web.backend.research import forecast_postprocessing_validation_verification as verification
from web.backend.research import inventory_alert_opportunity_audit as audit
from web.backend.research import inventory_forecast_identity as identity


ROOT = Path(__file__).resolve().parents[3]
HORIZONS = ["daily_H1_7", "daily_H8_14", "daily_H1_14"] + [f"cumulative_H{h:02}" for h in range(1, 15)]
HEADERS = ["ID", "Kind", "Early", "Rate", "Precision", "Recall", "FP", "Alarm item-days", "Date MAE", "Item WAPE", "Item bias"]


class ForecastScores:
    """Vectorized per-item and route sums; scalar verifier uses its own arithmetic."""

    def __init__(self, source, quantile=None):
        self.items = sorted(source["catalog"], key=lambda r: r["item_id"])
        self.routes = sorted({post.route_key(r) for r in self.items})
        self.indices = [[n for n, r in enumerate(self.items) if post.route_key(r) == key] for key in self.routes]
        self.actual = {(r["date"], r["item_id"]): r["quantity"] if r["actual_available"] else np.nan for r in source["daily"]}
        self.start, self.end = source["period"]["score_start"], source["period"]["end"]
        self.effective = post.load_protocol()["effective_from"]
        self.quantile = quantile
        self.item_sums = np.zeros((len(self.items), 17, 7))
        self.route_sums = np.zeros((len(self.routes), 17, 7))

    def update(self, sums, slot, f, y, expected, cumulative=False):
        valid = np.isfinite(y)
        sums[:, slot, 0] += expected
        sums[:, slot, 1] += valid.sum(axis=1)
        sums[:, slot, 2] += np.where(valid, y, 0).sum(axis=1)
        sums[:, slot, 3] += np.where(valid, np.abs(f - y), 0).sum(axis=1)
        sums[:, slot, 4] += np.where(valid, f - y, 0).sum(axis=1)
        if cumulative and self.quantile is not None:
            sums[:, slot, 5] += (valid & (y <= f)).sum(axis=1)
            loss = (self.quantile - (y < f)) * (y - f)
            sums[:, slot, 6] += np.where(valid, loss, 0).sum(axis=1)

    def observe(self, origin, values):
        if str(origin) < self.effective:
            return
        days = [str(origin + timedelta(days=h)) for h in range(1, 15)]
        mask = np.array([self.start <= d <= self.end for d in days])
        f = np.array([values[i["item_id"]] for i in self.items], dtype=float)
        y = np.array([[self.actual.get((d, i["item_id"]), np.nan) for d in days] for i in self.items])
        rf = np.array([f[idx].sum(axis=0) for idx in self.indices])
        ry = np.array([y[idx].sum(axis=0) for idx in self.indices])
        for predictions, actuals, sums in [(f, y, self.item_sums), (rf, ry, self.route_sums)]:
            for slot, bounds in enumerate([(0, 7), (7, 14), (0, 14)]):
                selected = np.arange(*bounds)[mask[slice(*bounds)]]
                self.update(sums, slot, predictions[:, selected], actuals[:, selected], len(selected))
            for h in range(1, 15):
                if mask[:h].all():
                    self.update(sums, h + 2, predictions[:, :h].sum(axis=1)[:, None],
                                actuals[:, :h].sum(axis=1)[:, None], 1, cumulative=True)

    def rows(self):
        result = []
        for scope, keys, sums in [("item", [str(i["item_id"]) for i in self.items], self.item_sums),
                                   ("route", self.routes, self.route_sums),
                                   ("items_pooled", ["all"], self.item_sums.sum(axis=0)[None, :, :]),
                                   ("routes_pooled", ["all"], self.route_sums.sum(axis=0)[None, :, :])]:
            for key, values in zip(keys, sums, strict=True):
                for horizon, counts in zip(HORIZONS, values, strict=True):
                    expected, n, actual, absolute, error, covered, loss = map(float, counts)
                    if not expected:
                        continue
                    is_risk = self.quantile is not None and horizon.startswith("cumulative")
                    result.append(dict(scope=scope, key=key, horizon=horizon, expected=int(expected), observed=int(n),
                                       coverage=n / expected, actual_quantity=actual,
                                       mae=absolute / n if n else None, wape=absolute / actual if actual else None,
                                       bias=error / n if n else None, bias_ratio=error / actual if actual else None,
                                       empirical_coverage=covered / n if n and is_risk else None,
                                       pinball_loss=loss / n if n and is_risk else None))
        return sorted(result, key=lambda r: (r["scope"], r["key"], r["horizon"]))


def diagnostics(cases, alarms, baseline_cases, period):
    signals = [a for a in alarms if a["predicted_depletion_date"] is not None]
    scored = [a for a in signals if period["score_start"] <= a["date"] <= period["end"]]
    days = [str(date.fromisoformat(period["score_start"]) + timedelta(days=n))
            for n in range((date.fromisoformat(period["end"]) - date.fromisoformat(period["score_start"])).days + 1)]
    base = {c["event_id"]: c for c in baseline_cases}
    identity.require(set(base) == {c["event_id"] for c in cases}, "Event cohort changed")
    paired = [c for c in cases if c["alarm_date"]]
    common = [c for c in paired if base[c["event_id"]]["alarm_date"]]
    error = lambda c: (date.fromisoformat(c["predicted_depletion_date"]) - date.fromisoformat(c["date"])).days
    mean = lambda values: float(np.mean(values)) if values else None
    return dict(late_count=sum(c["alarm_date"] is not None and not c["early"] for c in cases),
                no_alarm_count=sum(c["alarm_date"] is None for c in cases),
                gained_early=sum(c["early"] and not base[c["event_id"]]["early"] for c in cases),
                lost_early=sum(not c["early"] and base[c["event_id"]]["early"] for c in cases),
                alarm_item_days=len(scored), alarm_item_days_all_period=len(signals), distinct_items=len({a["item_id"] for a in scored}),
                alarms_per_day=len(scored) / len(days), daily_alarm_counts=[dict(date=d, count=sum(a["date"] == d for a in scored)) for d in days],
                date_pairs=len(paired), date_bias=mean([error(c) for c in paired]), common_pairs=len(common),
                common_date_mae=mean([abs(error(c)) for c in common]), common_date_bias=mean([error(c) for c in common]),
                baseline_common_date_mae=mean([abs(error(base[c["event_id"]])) for c in common]),
                baseline_common_date_bias=mean([error(base[c["event_id"]]) for c in common]))


def calculate_candidate(spec, source, baseline, baseline_cases, parameters, folder):
    folder.mkdir(exist_ok=False)
    scores = ForecastScores(source, spec.get("quantile"))
    by_day, by_item = defaultdict(list), defaultdict(list)
    for row in baseline["ledger"]:
        by_day[row["date"]].append(row)
    for order in baseline["orders"]:
        by_item[order["item_id"]].append(order)
    fixed = digest(baseline)
    alarms = []
    with (folder / "paths.jsonl.gz").open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        for day in sorted(by_day):
            values = post.transform(spec["id"], day, source["catalog"], source["daily"], source["forecasts"], parameters)
            origin = date.fromisoformat(day)
            scores.observe(origin, values)
            for row in by_day[day]:
                vector = values[row["item_id"]]
                path = identity.project(origin, row["closing_qty"], vector, identity.known_receipts(by_item[row["item_id"]], origin))
                path["predicted_depletion_date"] = str(path["predicted_depletion_date"]) if path["predicted_depletion_date"] else None
                stream.write((json.dumps(dict(date=day, item_id=row["item_id"], forecast=vector, projection=path), sort_keys=True,
                                         allow_nan=False) + "\n").encode("utf-8"))
                alarms.append(dict(date=day, item_id=row["item_id"], origin_on_hand=row["closing_qty"],
                                   predicted_depletion_date=path["predicted_depletion_date"] if path["state"] != "already_depleted" else None))
    period = source["period"]
    cases, metrics = audit.score(dict(baseline, alarms=alarms), date.fromisoformat(period["score_start"]), date.fromisoformat(period["end"]))
    extra = diagnostics(cases, alarms, baseline_cases, period)
    forecast_metrics = scores.rows()
    identity.require(fixed == digest(baseline), "Frozen baseline mutated")
    valid = bool(forecast_metrics) and all(r["coverage"] == 1 for r in forecast_metrics)
    summary = dict(candidate_id=spec["id"], kind=spec["kind"], valid=valid, metrics=metrics,
                   alarm_item_days=extra["alarm_item_days"], diagnostics=extra, fixed_input_sha256=fixed,
                   forecast_paths=len(alarms), projection_rows=len(alarms) * 14)
    audit.write(folder / "alarms.json.gz", alarms)
    audit.write(folder / "cases.json.gz", cases)
    audit.write(folder / "forecast_metrics.json.gz", forecast_metrics)
    audit.write(folder / "summary.json", summary)
    if spec["id"] == "C00":
        audit.same(alarms, baseline["alarms"])
        audit.same(cases, baseline_cases)
    return summary


def table_row(summary, forecast_metrics):
    m = summary["metrics"]
    accuracy = next(r for r in forecast_metrics if r["scope"] == "items_pooled" and r["horizon"] == "daily_H1_14")
    percent = lambda value: f"{100 * value:.4f}%" if value is not None else "null"
    number = lambda value: f"{value:.6f}" if value is not None else "null"
    return [summary["candidate_id"], summary["kind"], f"{m['early_numerator']}/{m['event_denominator']}",
            percent(m["early_rate"]), percent(m["precision"]), percent(m["recall"]), str(m["alarm_FP"]),
            str(summary["alarm_item_days"]), number(m["date_mae"]), percent(accuracy["wape"]), number(accuracy["bias"])]


def run(audit_run, f1_run, f2_lock, output_root):
    source, baseline, baseline_cases = verification.load_sources(audit_run, f1_run, f2_lock)
    identity.coverage(source, baseline)
    p = post.load_protocol()
    output_root = Path(output_root).resolve()
    identity.require(output_root.is_relative_to(ROOT / "outputs/research"), "Private output must stay under outputs/research")
    for parent in [Path(audit_run).resolve(), Path(f1_run).resolve(), Path(audit.read(Path(audit_run) / "manifest.json")["parents"]["validation"])]:
        identity.require(not output_root.is_relative_to(parent), "Cannot write inside sealed inputs")
    folder = output_root / ("forecast-validation-v1-" + str(uuid.uuid4()))
    folder.mkdir(parents=True, exist_ok=False)
    code = {str(Path(f).resolve().relative_to(ROOT)).replace("\\", "/"): audit.sha(f)
            for f in [__file__, verification.__file__]}
    audit.write(folder / "execution_lock.json", dict(created_at=datetime.now(timezone.utc).isoformat(), protocol_sha256=post.PROTOCOL_SHA256,
                code_sha256=code, F2_lock_sha256=verification.F2_LOCK_SHA256, phase="F3_validation_only", test_opened=False))
    parameters = post.calibrate(source["catalog"], source["daily"], source["forecasts"])
    verification.reference.verify_parameters(source["catalog"], source["daily"], source["forecasts"], parameters)
    audit.write(folder / "parameters.json", parameters)
    summaries, rows = [], []
    for spec in p["candidates"]:
        summary = calculate_candidate(spec, source, baseline, baseline_cases, parameters, folder / spec["id"])
        identity.require(summary["metrics"]["event_denominator"] == 486, "Validation denominator changed")
        summaries.append(summary)
        rows.append(table_row(summary, audit.read(folder / spec["id"] / "forecast_metrics.json.gz")))
        print("Calculated validation " + spec["id"], file=sys.stderr, flush=True)
    winner = post.select_validation(summaries)
    audit.write(folder / "summary.json", summaries)
    audit.write(folder / "selection.json", dict(candidate_id=winner, parameters_sha256=parameters["sha256"], protocol_sha256=post.PROTOCOL_SHA256,
                validation_only=True, test_opened=False, status="representative_locked" if winner else "no_candidate_reached_target"))
    with (folder / "summary.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    body = "".join("<tr>" + "".join("<td>" + html.escape(value) + "</td>" for value in row) + "</tr>" for row in rows)
    (folder / "report.html").write_text("<!doctype html><meta charset='utf-8'><title>SIGMA F3 validation</title>"
        "<h1>F3 validation — independent verification required</h1><p>Frozen inventory/orders/events; full locked grid. "
        "Stress and risk are separate from point accuracy. Test already seen historically; F4 has not been opened. "
        "No application/model/default change or R07/T14 acceptance. Target: at least 219/486.</p>"
        "<table border='1'><tr>" + "".join("<th>" + h + "</th>" for h in HEADERS) + "</tr>" + body + "</table>"
        "<p>Selection: " + html.escape(str(winner)) + ". See selection.json and verification.json before accepting it. "
        "Forecast metrics by item, route, horizon and cumulative horizon, including empirical risk coverage/pinball loss, "
        "are in each candidate/forecast_metrics.json.gz; event transitions, alarm frequency and common-pair date errors "
        "are in candidate/summary.json. Zero-denominator metrics remain null.</p>", encoding="utf-8")
    sources = dict(audit_run=str(Path(audit_run).resolve()), f1_run=str(Path(f1_run).resolve()), f2_lock=str(Path(f2_lock).resolve()))
    audit.write(folder / "manifest.json", dict(status="calculated_unverified", phase="F3_validation_only", protocol=p,
                protocol_sha256=post.PROTOCOL_SHA256, code_sha256=code, application_code_sha256=code_digest(), sources=sources,
                test_opened=False, artifacts={f.relative_to(folder).as_posix(): audit.sha(f) for f in folder.rglob("*") if f.is_file()}))
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    native = commands.add_parser("validation")
    native.add_argument("--audit-run", type=Path, required=True)
    native.add_argument("--f1-run", type=Path, required=True)
    native.add_argument("--f2-lock", type=Path, required=True)
    native.add_argument("--output-root", type=Path, default=ROOT / "outputs/research/forecast-postprocessing-f3")
    check = commands.add_parser("verify")
    check.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validation":
            folder = run(args.audit_run, args.f1_run, args.f2_lock, args.output_root)
            print(json.dumps(dict(status="calculated_unverified", output=str(folder))))
        else:
            print(json.dumps(verification.verify(args.run_dir)))
        return 0
    except Exception as exc:
        diagnostic = ROOT / "outputs/research/forecast-postprocessing-f3-checkpoint"
        diagnostic.mkdir(parents=True, exist_ok=True)
        (diagnostic / ("failure-" + str(uuid.uuid4()) + ".private.log")).write_text(traceback.format_exc(), encoding="utf-8")
        print(json.dumps(dict(status="failed", error_type=type(exc).__name__)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
