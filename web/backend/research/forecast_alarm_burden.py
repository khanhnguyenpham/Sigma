"""Describe locked C00/S25 alarms; never generate forecasts or select a candidate."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
import html
import json
from pathlib import Path
import uuid

from core.hashes import code_digest, digest
from web.backend.research import inventory_alert_opportunity_audit as audit
from web.backend.research.inventory_alert_opportunity_verification import score_events


ROOT = Path(__file__).resolve().parents[3]
PINS = {
    "validation": ("f53a99ad5e38929af10e5203a2110f38ad353ca0d68e19247bbce0d25c9fcf51", "a5bf676a77f03d0b566bb657791917df373173268a49ac53578f8b84b69799fd"),
    "test": ("c5df347726d4e446082c72bd7f1bf2f7ed7f505bdb4eb40b41bebaa16ed846da", "314794eb2fe75465cf78d5d58052ef0b108d0c4588222de3fd267c98bbc1a718"),
}
AUDIT_SHA = "23ed307ea2e3fdf86d3f91c2759bc4c6f52deaccc6e199e1c1bb97ee928a35e9"
LABELS = ("TP", "FP", "intervened", "right_censored")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def classify(alarms, events, orders, end):
    """Same priority and H14 as the frozen scorer; return signal item-days only."""
    event_days, item_orders = defaultdict(list), defaultdict(list)
    for row in events:
        event_days[row["item_id"]].append(row["date"])
    for days in event_days.values():
        days.sort()
    for row in orders:
        item_orders[row["item_id"]].append(row)
    result, seen = [], set()
    for row in sorted(alarms, key=lambda r: (r["date"], r["item_id"])):
        key = row["date"], row["item_id"]
        require(key not in seen, "Duplicate decision item-day")
        seen.add(key)
        if row["predicted_depletion_date"] is None:
            continue
        day = date.fromisoformat(row["date"])
        lead = (date.fromisoformat(row["predicted_depletion_date"]) - day).days
        require(row["origin_on_hand"] > 0 and 1 <= lead <= 14, "Invalid valid-alarm boundary")
        limit = str(min(end, day + timedelta(days=14)))
        days = event_days[row["item_id"]]
        index = bisect_right(days, row["date"])
        hit = index < len(days) and days[index] <= limit
        intervention = any(not o["is_initial"] and o["ordered_on"] >= row["date"] and o["eta"] <= limit
                           for o in item_orders[row["item_id"]])
        label = "TP" if hit else "intervened" if intervention else "right_censored" if day + timedelta(days=14) > end else "FP"
        known = sum(o["ordered_qty"] for o in item_orders[row["item_id"]]
                    if row["date"] < o["eta"] <= str(day + timedelta(days=14))
                    and (o["is_initial"] or o["ordered_on"] < row["date"]))
        result.append(dict(row, label=label, predicted_lead=lead, known_receipts_H14=known))
    return result


def streaks(rows, label=None):
    """Calendar-consecutive signals; FP-only streaks break at any non-FP day."""
    result, previous = [], {}
    for row in sorted(rows, key=lambda r: (r["item_id"], r["date"])):
        if label is not None and row["label"] != label:
            continue
        item, day = row["item_id"], date.fromisoformat(row["date"])
        prior = previous.get(item)
        if prior is not None and day == date.fromisoformat(prior["end"]) + timedelta(days=1):
            prior["end"], prior["length"] = str(day), prior["length"] + 1
        else:
            prior = dict(item_id=item, start=str(day), end=str(day), length=1)
            result.append(prior)
        previous[item] = prior
    return result


def distribution(values):
    values = sorted(values)
    if not values:
        return dict(count=0, mean=None, median=None, p90=None, p95=None, maximum=None)
    def quantile(q):
        index = (len(values) - 1) * q
        lower = int(index)
        return values[lower] + (values[min(lower + 1, len(values) - 1)] - values[lower]) * (index - lower)
    return dict(count=len(values), mean=sum(values) / len(values), median=quantile(.5), p90=quantile(.9), p95=quantile(.95), maximum=values[-1])


def write_csv(path, rows):
    require(bool(rows), "Empty report table")
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_run(folder, split):
    manifest_pin, receipt_pin = PINS[split]
    require(audit.sha(folder / "manifest.json") == manifest_pin, "Unexpected source manifest")
    require(audit.sha(folder / "verification.json") == receipt_pin, "Unexpected source receipt")
    manifest, receipt = audit.read(folder / "manifest.json"), audit.read(folder / "verification.json")
    require(receipt["status"] == "verified" and receipt["manifest_sha256"] == manifest_pin, "Unverified source")
    require(code_digest() == manifest["application_code_sha256"], "Application code changed")
    for relative, checksum in manifest["artifacts"].items():
        require(audit.sha(folder / relative) == checksum, "Source artifact changed: " + relative)
    return manifest


def analyze_split(folder, split, audit_dir, output):
    baseline = audit.read(audit_dir / (split + "-replay.json.gz"))
    audit_manifest = audit.read(audit_dir / "manifest.json")
    snapshot = audit.read(Path(audit_manifest["parents"][split]) / "inputs.json.gz")
    catalog = {r["item_id"]: r for r in snapshot["catalog"]}
    period = snapshot["period"]
    start, end = period["score_start"], date.fromisoformat(period["end"])
    first = date.fromisoformat(period["origin"])
    days = [str(first + timedelta(days=i)) for i in range((end - first).days + 1)]
    signals, cases, summaries = {}, {}, {}
    for candidate in ("C00", "S25"):
        alarms = audit.read(folder / candidate / "alarms.json.gz")
        summary = audit.read(folder / candidate / "summary.json")
        require(digest(baseline) == summary["fixed_input_sha256"], "Frozen stock/order/event input differs")
        require(len(alarms) == len(catalog) * len(days)
                and {(r["date"], r["item_id"]) for r in alarms} == {(d, i) for d in days for i in catalog}, "Incomplete alarm grid")
        observed_cases, metrics = score_events(dict(baseline, alarms=alarms), date.fromisoformat(start), end)
        sealed_cases = audit.read(folder / candidate / "cases.json.gz")
        require(observed_cases == sealed_cases and metrics == summary["metrics"], "Independent scorer reconciliation failed")
        rows = classify(alarms, baseline["events"], baseline["orders"], end)
        counts = Counter(r["label"] for r in rows if r["date"] >= start)
        for label, metric in zip(LABELS, ("alarm_TP", "alarm_FP", "intervened_count", "right_censored_count")):
            require(counts[label] == metrics[metric], "Classification reconciliation failed: " + label)
        require(len(rows) == summary["diagnostics"]["alarm_item_days_all_period"], "Full-period load differs")
        signals[candidate], cases[candidate], summaries[candidate] = rows, sealed_cases, summary
    original = {(r["date"], r["item_id"]): r for r in signals["C00"]}
    stressed = {(r["date"], r["item_id"]): r for r in signals["S25"]}
    require(original.keys() <= stressed.keys(), "Stress lost a baseline signal")
    require(all(original[k]["label"] == stressed[k]["label"] for k in original), "Shared signal labels differ")

    all_rows, day_rows, group_rows, streak_rows = [], [], [], []
    for candidate, rows in signals.items():
        for row in rows:
            item = catalog[row["item_id"]]
            all_rows.append(dict(split=split, candidate=candidate, phase="scored" if row["date"] >= start else "pre_score",
                                 added=candidate == "S25" and (row["date"], row["item_id"]) not in original,
                                 **row, **{k: item[k] for k in ("destination_country", "carrier", "sku", "product_type")}))
        for phase in ("pre_score", "scored", "all"):
            subset = [r for r in rows if phase == "all" or (r["date"] >= start) == (phase == "scored")]
            phase_days = [d for d in days if phase == "all" or (d >= start) == (phase == "scored")]
            daily = Counter(r["date"] for r in subset)
            runs = streaks(subset)
            fp_runs = streaks(subset, "FP")
            for kind, values in (("signal", runs), ("FP", fp_runs)):
                streak_rows.extend(dict(split=split, candidate=candidate, phase=phase, kind=kind, **v) for v in values)
            group_rows.append(dict(candidate=candidate, phase=phase, signals=len(subset), days=len(phase_days),
                                   labels={label: sum(r["label"] == label for r in subset) for label in LABELS},
                                   unique_items=len({r["item_id"] for r in subset}),
                                   unique_FP_items=len({r["item_id"] for r in subset if r["label"] == "FP"}),
                                   daily_load=distribution([daily[d] for d in phase_days]),
                                   signal_streak=distribution([r["length"] for r in runs]),
                                   FP_streak=distribution([r["length"] for r in fp_runs])))
        for day in days:
            selected = [r for r in rows if r["date"] == day]
            day_rows.append(dict(split=split, candidate=candidate, date=day, phase="scored" if day >= start else "pre_score",
                                 signals=len(selected), **{label: sum(r["label"] == label for r in selected) for label in LABELS}))

    # Keep zero-burden items/routes in the tables. Event benefits use the sealed cohort.
    old_cases = {r["event_id"]: r for r in cases["C00"]}
    require(old_cases.keys() == {r["event_id"] for r in cases["S25"]}, "Event cohort differs")
    gained = [r for r in cases["S25"] if r["early"] and not old_cases[r["event_id"]]["early"]]
    lost = [r for r in cases["S25"] if not r["early"] and old_cases[r["event_id"]]["early"]]
    tables = {}
    for scope in ("route", "item"):
        keys = ("destination_country", "carrier") if scope == "route" else ("destination_country", "carrier", "sku", "product_type", "item_id")
        groups = {tuple(r[k] for k in keys): Counter() for r in catalog.values()}
        for row in all_rows:
            counts = groups[tuple(row[k] for k in keys)]
            phase, candidate = row["phase"], row["candidate"]
            counts[candidate + "_" + phase + "_signals"] += 1
            counts[candidate + "_" + phase + "_" + row["label"]] += 1
            if row["added"]:
                counts["added_" + phase + "_signals"] += 1
                if row["label"] == "FP":
                    counts["new_" + phase + "_FP"] += 1
        for kind, event_rows in (("gained_early", gained), ("lost_early", lost)):
            for row in event_rows:
                groups[tuple(catalog[row["item_id"]][k] for k in keys)][kind] += 1
        fields = sorted(set().union(*(r.keys() for r in groups.values())))
        table = [dict(zip(keys, key), **{f: values[f] for f in fields}) for key, values in groups.items()]
        table.sort(key=lambda r: (-r.get("new_scored_FP", 0), tuple(str(r[k]) for k in keys)))
        require(sum(r.get("new_scored_FP", 0) for r in table) == summaries["S25"]["metrics"]["alarm_FP"] - summaries["C00"]["metrics"]["alarm_FP"], "Group FP sum differs")
        tables[scope] = table
        write_csv(output / (split + "-" + scope + ".csv"), table)
    new_fp = [r for r in all_rows if r["candidate"] == "S25" and r["added"] and r["phase"] == "scored" and r["label"] == "FP"]
    fp_total = len(new_fp)
    result = dict(period=period, candidate_metrics={c: s["metrics"] for c, s in summaries.items()}, burden=group_rows,
                  gained_early=len(gained), lost_early=len(lost),
                  gained_early_alarm_phase=dict(Counter("pre_score" if r["alarm_date"] < start else "scored" for r in gained)),
                  new_scored_FP=fp_total, new_FP_items=len({r["item_id"] for r in new_fp}),
                  top5_route_new_FP_share=sum(r.get("new_scored_FP", 0) for r in tables["route"][:5]) / fp_total if fp_total else None,
                  top10_item_new_FP_share=sum(r.get("new_scored_FP", 0) for r in tables["item"][:10]) / fp_total if fp_total else None,
                  new_FP_stock=dict(Counter("1" if r["origin_on_hand"] == 1 else "2" if r["origin_on_hand"] == 2 else "3-5" if r["origin_on_hand"] <= 5 else ">5" for r in new_fp)),
                  new_FP_predicted_lead=dict(sorted(Counter(r["predicted_lead"] for r in new_fp).items())),
                  new_FP_known_receipts=dict(Counter("positive" if r["known_receipts_H14"] > 0 else "zero" for r in new_fp)),
                  top_routes=tables["route"][:5], top_items=tables["item"][:20])
    write_csv(output / (split + "-signals.csv"), all_rows)
    write_csv(output / (split + "-days.csv"), day_rows)
    write_csv(output / (split + "-streaks.csv"), streak_rows)
    return result, day_rows


def html_table(rows, fields):
    return "<table><thead><tr>" + "".join("<th>" + html.escape(f) + "</th>" for f in fields) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join("<td>" + html.escape(str(r.get(f, ""))) + "</td>" for f in fields) + "</tr>" for r in rows) + "</tbody></table>"


def run(validation_run, test_run, output_root):
    manifests = {s: check_run(p, s) for s, p in (("validation", validation_run), ("test", test_run))}
    audit_dir = Path(manifests["validation"]["sources"]["audit_run"])
    require(audit.sha(audit_dir / "manifest.json") == AUDIT_SHA, "Audit source differs")
    require(Path(manifests["test"]["source_F3_run"]).resolve() == validation_run.resolve(), "Test/validation lineage differs")
    am = audit.read(audit_dir / "manifest.json")
    for relative, checksum in am["artifacts"].items():
        require(audit.sha(audit_dir / relative) == checksum, "Audit artifact changed")
    # Parent snapshots are checked against the source protocol before reading catalog/period.
    for split in PINS:
        audit.load_parent(am["parents"][split], split, am["protocol"])
    output = output_root / ("alarm-burden-" + str(uuid.uuid4()))
    output.mkdir(parents=True, exist_ok=False)
    results, daily = {}, {}
    for split, folder in (("validation", validation_run), ("test", test_run)):
        results[split], daily[split] = analyze_split(folder, split, audit_dir, output)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, layout="constrained")
    for axis, metric, title in zip(axes, ("signals", "FP"), ("All alarm item-days", "FP item-days (intervened/censored excluded)")):
        for candidate, color in (("C00", "#3366a5"), ("S25", "#ca6529")):
            rows = [r for r in daily["test"] if r["candidate"] == candidate and r["phase"] == "scored"]
            axis.plot([date.fromisoformat(r["date"]) for r in rows], [r[metric] for r in rows], label=candidate, color=color)
        axis.set_title(title, loc="left"); axis.set_ylabel("Item-days / UTC day"); axis.grid(alpha=.2); axis.legend()
    fig.suptitle("Locked test retrospective: workload counts, not employee tasks")
    fig.savefig(output / "test-daily.png", dpi=150)
    fig.savefig(output / "test-daily.svg")
    plt.close(fig)
    audit.write(output / "summary.json", results)
    body = """<!doctype html><html lang="vi"><meta charset="utf-8"><title>SIGMA — Tải cảnh báo C00/S25</title>
<style>body{font:16px system-ui;margin:32px auto;max-width:1250px;padding:0 20px;color:#193047}h1,h2{color:#173e61}table{border-collapse:collapse;margin:20px 0;font-size:14px}th,td{border:1px solid #ccd5df;padding:8px;text-align:right}th{background:#eaf0f6}img{width:100%}a{color:#125f9b}.scroll{overflow-x:auto}</style>
<h1>SIGMA — Đánh đổi báo sớm và tải cảnh báo</h1>
<p>Phân tích hậu kiểm các output C00/S25 đã khóa và kiểm độc lập; không chạy forecast, chọn lại hoặc thay phương án chính m3-implementation. S25 là stress ×1,25, không phải cải thiện độ chính xác forecast điểm. Test đã xem, model gốc có lịch sử test-selected; không là holdout độc lập. R07/T14 chưa nghiệm thu.</p>
<p>Đơn vị tải là <b>item-ngày</b>, không phải số công việc/nhân sự. TP ưu tiên sự kiện đầu tiên trong H14; nếu không có thì can thiệp → thiếu nhãn cuối kỳ → FP. Can thiệp và thiếu nhãn không gộp vào FP. Early tính theo episode một lần; không dùng số item-ngày làm mẫu số early. Chưa có mức FP/tải được nghiệp vụ chấp nhận.</p>
<p>pre_score bao gồm origin khởi tạo và 28 ngày warmup (29 origin); scored có 64 ngày. Chuỗi liên tiếp chỉ là thống kê mô tả, không thay luật chấm hoặc cơ chế gộp cảnh báo trong ứng dụng. Phân tích tuyến/SKU không dùng để lọc hay chọn lại S25. Không đổi đơn nhập, tồn, receipts hoặc nhãn.</p>"""
    for split, result in results.items():
        body += "<h2>" + split + "</h2>"
        compare = []
        for candidate in ("C00", "S25"):
            metric = result["candidate_metrics"][candidate]
            row = next(r for r in result["burden"] if r["candidate"] == candidate and r["phase"] == "scored")
            compare.append(dict(candidate=candidate, early=f'{metric["early_numerator"]}/{metric["event_denominator"]}',
                                precision=round(metric["precision"] * 100, 4), FP=metric["alarm_FP"],
                                signals=row["signals"], mean_per_day=round(row["daily_load"]["mean"], 3),
                                p95=row["daily_load"]["p95"], max_per_day=row["daily_load"]["maximum"], unique_items=row["unique_items"]))
        body += html_table(compare, list(compare[0]))
        body += "<p>Early mới: " + str(result["gained_early"]) + "; mất: " + str(result["lost_early"]) + "; ngày cảnh báo sớm nhất của early mới: " + html.escape(str(result["gained_early_alarm_phase"])) + ".</p>"
        phase_table = [dict(candidate=r["candidate"], phase=r["phase"], days=r["days"], signals=r["signals"], **r["labels"],
                            signal_streaks=r["signal_streak"]["count"], max_signal_streak=r["signal_streak"]["maximum"], FP_streaks=r["FP_streak"]["count"], max_FP_streak=r["FP_streak"]["maximum"]) for r in result["burden"]]
        body += '<div class="scroll">' + html_table(phase_table, list(phase_table[0])) + "</div>"
        body += "<p>FP mới tập trung top 5 tuyến: " + f'{result["top5_route_new_FP_share"]:.2%}' + "; top 10 item: " + f'{result["top10_item_new_FP_share"]:.2%}' + ". Đây là xếp hạng mô tả hồi cứu.</p>"
        body += "<p>FP mới theo tồn tại origin: " + html.escape(str(result["new_FP_stock"])) + "; receipts H14 đã biết: " + html.escape(str(result["new_FP_known_receipts"])) + ". Đây không phải kết luận nguyên nhân.</p>"
        body += "<h3>5 tuyến có nhiều FP mới nhất</h3><div class=scroll>" + html_table(result["top_routes"], ["destination_country", "carrier", "C00_scored_FP", "S25_scored_FP", "new_scored_FP", "added_scored_signals", "gained_early"]) + "</div>"
        body += "<details><summary>20 item có nhiều FP mới nhất</summary><div class=scroll>" + html_table(result["top_items"], ["destination_country", "carrier", "sku", "product_type", "item_id", "new_scored_FP", "added_scored_signals", "gained_early"]) + "</div></details>"
        body += "<p>CSV đầy đủ: " + " · ".join(f'<a href="{split}-{name}.csv">{name}</a>' for name in ("route", "item", "days", "signals", "streaks")) + "</p>"
    body += '<h2>Tải theo ngày test</h2><img src="test-daily.png" alt="C00 và S25: số cảnh báo và FP theo ngày UTC"><p>Đoạn FP cuối kỳ giảm chịu ảnh hưởng right-censor; không suy ra chất lượng tăng ở cuối kỳ. Chi tiết và provenance: <a href="summary.json">summary.json</a>, <a href="manifest.json">manifest.json</a>.</p></html>'
    (output / "report.html").write_text(body, encoding="utf-8")
    artifacts = {p.name: audit.sha(p) for p in sorted(output.iterdir())}
    audit.write(output / "manifest.json", dict(created_at=datetime.now(timezone.utc).isoformat(), phase="posthoc_alarm_burden_only",
                source_runs={"validation": str(validation_run.resolve()), "test": str(test_run.resolve())}, source_pins=PINS,
                audit_manifest_sha256=AUDIT_SHA, application_code_sha256=code_digest(),
                code_sha256={str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"): audit.sha(__file__)},
                reconciliation="independent frozen scorer cases/metrics and per-label totals matched for all four sources",
                application_replacement=False, reselection=False, artifacts=artifacts))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-run", type=Path, required=True)
    parser.add_argument("--test-run", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/research/forecast-alarm-burden")
    args = parser.parse_args()
    allowed = (ROOT / "outputs/research/forecast-alarm-burden").resolve()
    require(args.output_root.resolve().is_relative_to(allowed), "Output must remain in ignored local research folder")
    print(json.dumps(dict(run_dir=str(run(args.validation_run, args.test_run, args.output_root).resolve()))))


if __name__ == "__main__":
    main()
