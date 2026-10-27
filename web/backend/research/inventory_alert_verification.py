"""Independent reconstruction of frozen inventory research; no runner/business helpers."""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
from statistics import pstdev

import numpy as np
from core.hashes import code_digest
from core.settings import PROJECT_ROOT


PROTOCOL = PROJECT_ROOT / "web/backend/configs/inventory-alert-experiments.json"
RUNNER = Path(__file__).with_name("inventory_alert_experiments.py")
MAX = 2**63 - 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str,
                                    allow_nan=False).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def read(path):
    payload = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        payload = gzip.decompress(payload)
    return json.loads(payload, object_pairs_hook=unique_object,
                      parse_constant=lambda _: require(False, "Nonfinite JSON constant"))


def count(value, minimum=0):
    require(type(value) is int and minimum <= value <= MAX, "Invalid integer quantity")
    return value


def calendar(start, end):
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def matrix():
    result = [dict(id="A-base", group="A", cover=7, mode="days", multiplier=1, add_ss=False),
              dict(id="B-daily", group="B", cover=7, mode="days", multiplier=1, add_ss=False)]
    for group in ("C", "D"):
        for mode in ("days", "volatility"):
            for m in (.5, 1., 1.5):
                result.append(dict(id=f"{group}-{mode}-m{m:g}-cover7", group=group,
                                   mode=mode, multiplier=m, cover=7, add_ss=group == "C"))
        for cover in (3, 14):
            result.append(dict(id=f"{group}-cover{cover}", group=group, cover=cover,
                               mode="days", multiplier=1, add_ss=False))
    result.append(dict(id="D-days-m0-cover7", group="D", cover=7, mode="days", multiplier=0, add_ss=False))
    return result


def inputs(snapshot):
    require(type(snapshot.get("version")) is int and snapshot["version"] == 1, "Unsupported snapshot")
    origin, end, score = (date.fromisoformat(snapshot["period"][k]) for k in ("origin", "end", "score_start"))
    require(origin < score <= end, "Invalid snapshot period")
    catalog = {}
    for row in snapshot["catalog"]:
        item = count(row["item_id"], 1)
        require(item not in catalog, "Duplicate catalog key")
        catalog[item] = row
    cohort = sorted(i for i, row in catalog.items() if date.fromisoformat(row["first_seen_date"]) <= origin)
    require(bool(cohort), "Empty cohort")
    daily, forecasts, sales, policies = {}, {}, defaultdict(list), defaultdict(list)
    for table in ("daily", "forecasts", "sales", "policies", "receipts"):
        for row in snapshot.get(table, []):
            require(count(row["item_id"], 1) in catalog, "Unknown snapshot item")
    for row in snapshot["daily"]:
        day, item = date.fromisoformat(row["date"]), row["item_id"]
        require((day, item) not in daily and row["actual_available"] is True, "Daily gap/duplicate/unavailable")
        require(origin - timedelta(days=27) <= day <= end, "Daily observation outside frozen period")
        daily[day, item] = count(row["quantity"])
    for row in snapshot["forecasts"]:
        day, item, f = date.fromisoformat(row["as_of_date"]), row["item_id"], row["forecast"]
        require((day, item) not in forecasts and origin <= day <= end, "Invalid forecast origin")
        require(type(f) is list and len(f) == 14, "Incomplete H14")
        require(all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in f), "Invalid forecast quantity")
        forecasts[day, item] = np.asarray(f, dtype=float)
    sequences = set()
    ordered_days = []
    for row in snapshot["sales"]:
        day, item, seq = date.fromisoformat(row["date"]), row["item_id"], count(row["sequence"], 1)
        require(seq not in sequences and origin < day <= end, "Invalid audited transaction")
        sequences.add(seq)
        ordered_days.append((seq, day))
        sales[day, item].append((seq, count(row["quantity"])))
    timeline = [d for _, d in sorted(ordered_days)]
    require(timeline == sorted(timeline), "Source sequence is not chronological")
    for rows in sales.values():
        rows.sort()
    for row in snapshot["policies"]:
        count(row["configured_rop_floor"]); count(row["moq"], 1)
        b = row["safety_days"]
        require(type(b) in (int, float) and math.isfinite(b) and b >= 0, "Invalid safety days")
        policies[row["item_id"]].append(row)
    for item in cohort:
        for day in calendar(origin - timedelta(days=27), end):
            require((day, item) in daily, "Missing observed history")
            if day > origin:
                require(sum(q for _, q in sales[day, item]) == daily[day, item], "Sales/daily mismatch")
            if day >= origin:
                require((day, item) in forecasts, "Missing H14 origin")
                policy(policies, item, day)
    receipts, keys = [], set()
    for row in snapshot.get("receipts", []):
        ordered, arrival = date.fromisoformat(row["ordered_on"]), date.fromisoformat(row["eta"])
        require(row["lot_key"] not in keys and ordered <= origin and arrival == ordered + timedelta(days=7), "Invalid known receipt")
        keys.add(row["lot_key"])
        receipts.append(dict(item_id=row["item_id"], ordered_on=ordered, eta=arrival,
                             ordered_qty=count(row["ordered_qty"], 1), order_key=row["lot_key"], is_initial=True))
    return dict(origin=origin, end=end, score_start=score, cohort=cohort, daily=daily, forecasts=forecasts,
                sales=sales, policies=policies, receipts=receipts, excluded_items=sorted(set(catalog) - set(cohort)))


def policy(policies, item, day):
    candidates = [p for p in policies[item] if date.fromisoformat(p["effective_from"]) <= day
                  and (p.get("effective_to") is None or day < date.fromisoformat(p["effective_to"]))]
    require(len(candidates) == 1, "Policy coverage/overlap differs")
    return candidates[0]


def arithmetic(data, config, item, cutoff, stock, pending):
    p, f = policy(data["policies"], item, cutoff), data["forecasts"][cutoff, item]
    past = [data["daily"][cutoff - timedelta(days=n), item] for n in range(27, -1, -1)]
    if config["mode"] == "days":
        reserve = float(p["safety_days"]) * float(config["multiplier"]) * float(np.mean(f))
    else:
        reserve = float(config["multiplier"]) * 1.0 * pstdev(past) * math.sqrt(7)
    require(math.isfinite(reserve), "Nonfinite safety stock")
    ss = count(math.ceil(reserve))
    rf = count(math.ceil(float(f[:7].sum()) + ss))
    rop = max(p["configured_rop_floor"], rf)
    target, ip = count(rop + math.ceil(float(f[7]))), count(stock + pending)
    triggered = stock < rop
    q = max(0, target - ip) if triggered else 0
    q = count(max(q, p["moq"]) if q else 0)
    return dict(ss=ss, rop_forecast=rf, rop=rop, target_stock=target, inventory_position=ip,
                pending_qty=pending, needs_replenishment=triggered, recommended_qty=q,
                state="pending_covers" if triggered and q == 0 else "low_stock" if triggered else "sufficient")


def rebuild(snapshot, config):
    return rebuild_prepared(inputs(snapshot), config)


def rebuild_prepared(data, config):
    require(config in matrix(), "Configuration is outside the locked matrix")
    origin, end, group = data["origin"], data["end"], config["group"]
    windows = [(origin, end)] if group == "D" else [(d, d + timedelta(days=14))
        for d in calendar(origin, end) if (d - origin).days % 14 == 0 and d + timedelta(days=14) <= end]
    require(bool(windows), "No complete observation window")
    out = {k: [] for k in ("ledger", "alarms", "events", "transactions", "orders", "initialization")}
    # Each item is reconstructed independently, rather than using the runner's day/item state machine.
    for start, finish in windows:
        for item in data["cohort"]:
            prefix = [data["daily"][start - timedelta(days=n), item] for n in range(27, -1, -1)]
            base = count(math.ceil(float(np.mean(prefix)) * config["cover"]))
            extra = arithmetic(data, config, item, start, 0, 0)["ss"] if config["add_ss"] else 0
            stock = count(base + extra)
            out["initialization"].append(dict(window_origin=start.isoformat(), item_id=item,
                                              base_qty=base, added_ss=extra, initial_qty=stock))
            lots = [dict(r, window_origin=start.isoformat(), received=False) for r in data["receipts"]
                    if r["item_id"] == item and r["eta"] > start]
            for day in calendar(start, finish):
                opening = stock
                arrivals = [o for o in lots if o["eta"] == day and not o["received"]]
                received = sum(o["ordered_qty"] for o in arrivals)
                stock = count(stock + received)
                for order in arrivals:
                    order["received"] = True
                total = fulfilled = shortage = 0
                for seq, demand in data["sales"][day, item] if day > start else []:
                    before = stock
                    served = min(stock, demand)
                    stock -= served
                    total += demand; fulfilled += served; shortage += demand - served
                    out["transactions"].append(dict(window_origin=start.isoformat(), date=day.isoformat(), item_id=item,
                        sequence=seq, quantity=demand, fulfilled_qty=served, shortage_qty=demand-served, balance_after=stock))
                    if before > 0 and stock == 0:
                        out["events"].append(dict(window_origin=start.isoformat(), date=day.isoformat(), item_id=item,
                            sequence=seq, event_id=f"{start}:{item}:{seq}"))
                pending = sum(o["ordered_qty"] for o in lots if not o["received"])
                cutoff = start if group == "A" else day
                values = arithmetic(data, config, item, cutoff, stock, pending)
                out["ledger"].append(dict(window_origin=start.isoformat(), date=day.isoformat(), item_id=item,
                    opening_qty=opening, receipts_qty=received, sales_qty=total, fulfilled_qty=fulfilled,
                    shortage_qty=shortage, closing_qty=stock, forecast_as_of_date=cutoff.isoformat(), **values))
                if group != "A" or day == start:
                    projected, depletion, crossing = float(stock), None, None
                    for h, demand in enumerate(data["forecasts"][cutoff, item], 1):
                        target_day = day + timedelta(days=h)
                        arriving = sum(o["ordered_qty"] for o in lots if not o["received"] and o["eta"] == target_day)
                        projected = max(0., projected + arriving - float(demand))
                        if stock > 0 and projected == 0 and depletion is None:
                            depletion = target_day
                        if stock >= values["rop"] and h <= 7 and projected < values["rop"] and crossing is None:
                            crossing = target_day
                    if group != "D" and depletion is not None and depletion > finish:
                        depletion = None
                    out["alarms"].append(dict(window_origin=start.isoformat(), date=day.isoformat(), item_id=item,
                        origin_on_hand=stock, rop=values["rop"], below_rop=stock < values["rop"],
                        predicted_depletion_date=depletion.isoformat() if depletion else None,
                        predicted_threshold_date=crossing.isoformat() if crossing else None))
                if group == "D" and values["recommended_qty"]:
                    lots.append(dict(window_origin=start.isoformat(), item_id=item, ordered_on=day,
                        eta=day + timedelta(days=7), ordered_qty=values["recommended_qty"], is_initial=False,
                        order_key=f"{start}:{item}:{day}", received=False))
            out["orders"].extend({**o, "ordered_on": o["ordered_on"].isoformat(), "eta": o["eta"].isoformat()} for o in lots)
    for name in out:
        out[name].sort(key=row_key)
    cases, metrics = episode_metrics(out, data) if group == "D" else window_metrics(out)
    out["cases"] = cases
    out["threshold_cases"], thresholds = threshold_evaluation(out, data, group)
    excluded = data["excluded_items"]
    metrics.update(config=config, **inventory(out, data["score_start"] if group == "D" else origin + timedelta(days=1)),
        threshold_metrics=thresholds, excluded_tail_days=0 if group == "D" else (end-windows[-1][1]).days,
        cohort_items=len(data["cohort"]), excluded_items=excluded,
        excluded_sales_qty=sum(q for (d, i), q in data["daily"].items() if origin < d <= end and i in excluded),
        metrics_status="unverified")
    out["metrics"], out["all_period_inventory"] = metrics, inventory(out, origin)
    return out


def row_key(row):
    return tuple(str(row.get(k, "")) for k in ("window_origin", "date", "as_of_date", "item_id", "sequence", "order_key", "event_id"))


def mean(values):
    return float(np.mean(values)) if values else None


def ratio(n, d):
    return n / d if d else None


def window_metrics(out):
    events, alarms = defaultdict(list), defaultdict(list)
    for row in out["events"]:
        events[row["window_origin"], row["item_id"]].append(row)
    for row in out["alarms"]:
        alarms[row["window_origin"], row["item_id"]].append(row)
    cases, confusion, early, excluded, errors, late = [], dict(TP=0, FP=0, FN=0, TN=0), 0, 0, [], 0
    for initial in out["initialization"]:
        key = initial["window_origin"], initial["item_id"]
        actual = min((e["date"] for e in events[key]), default=None)
        valid = [a for a in alarms[key] if a["predicted_depletion_date"] is not None and (actual is None or a["date"] < actual)]
        alarm = min(valid, key=lambda a: a["date"]) if valid else None
        predicted = alarm["predicted_depletion_date"] if alarm else None
        emitted = alarm["date"] if alarm else key[0]
        zero = initial["initial_qty"] == 0
        cases.append(dict(window_origin=key[0], item_id=key[1], actual_depletion_date=actual,
                          predicted_depletion_date=predicted, as_of_date=emitted, already_depleted=zero))
        if zero:
            excluded += 1
            continue
        label = "TP" if predicted and actual else "FP" if predicted else "FN" if actual else "TN"
        confusion[label] += 1
        if actual and predicted:
            lead = (date.fromisoformat(actual) - date.fromisoformat(emitted)).days
            early += lead >= 7; late += lead < 7
            errors.append(abs((date.fromisoformat(actual) - date.fromisoformat(predicted)).days))
    n = confusion["TP"] + confusion["FN"]
    return cases, dict(unit="item_window", **confusion, early_numerator=early, event_denominator=n,
        early_rate=ratio(early, n), excluded_count=excluded, late_count=late, date_mae=mean(errors),
        precision=ratio(confusion["TP"], confusion["TP"]+confusion["FP"]),
        recall=ratio(confusion["TP"], n))


def episode_metrics(out, data):
    matched, evaluations, by_item, orders = {}, [], defaultdict(list), defaultdict(list)
    for e in out["events"]:
        by_item[e["item_id"]].append(e)
    for o in out["orders"]:
        orders[o["item_id"]].append(o)
    for a in out["alarms"]:
        if a["predicted_depletion_date"] is None:
            continue
        day = date.fromisoformat(a["date"]); limit = day + timedelta(days=14)
        candidates = [e for e in by_item[a["item_id"]] if day < date.fromisoformat(e["date"]) <= limit]
        event = min(candidates, key=lambda e: (e["date"], e["sequence"])) if candidates else None
        if event and (event["event_id"] not in matched or a["date"] < matched[event["event_id"]]["date"]):
            matched[event["event_id"]] = a
        changed = any(not o["is_initial"] and day <= date.fromisoformat(o["ordered_on"])
                      and date.fromisoformat(o["eta"]) <= min(limit, data["end"]) for o in orders[a["item_id"]])
        status = "TP" if event else "intervened" if changed else "right_censored" if limit > data["end"] else "FP"
        evaluations.append(dict(date=a["date"], item_id=a["item_id"], status=status,
            event_id=event["event_id"] if event else None, intervened=changed, right_censored=limit > data["end"],
            precision_evaluable=day >= data["score_start"] and status in ("TP", "FP")))
    cases, errors = [], []
    for e in out["events"]:
        if date.fromisoformat(e["date"]) < data["score_start"]:
            continue
        a = matched.get(e["event_id"])
        lead = (date.fromisoformat(e["date"]) - date.fromisoformat(a["date"])).days if a else None
        cases.append(dict(**e, alarm_date=a["date"] if a else None,
            predicted_depletion_date=a["predicted_depletion_date"] if a else None, lead_days=lead,
            early=lead is not None and lead >= 7))
        if a:
            errors.append(abs((date.fromisoformat(e["date"]) - date.fromisoformat(a["predicted_depletion_date"])).days))
    tp = sum(e["status"] == "TP" and e["precision_evaluable"] for e in evaluations)
    fp = sum(e["status"] == "FP" and e["precision_evaluable"] for e in evaluations)
    early = sum(c["early"] for c in cases); n = len(cases)
    out["alarm_evaluation"] = evaluations
    return cases, dict(unit="unique_depletion_episode", precision_unit="item_alarm_day", early_numerator=early,
        event_denominator=n, early_rate=ratio(early, n), recall=ratio(sum(c["alarm_date"] is not None for c in cases), n),
        precision=ratio(tp, tp+fp), alarm_TP=tp, alarm_FP=fp, date_mae=mean(errors),
        intervened_count=sum(e["status"] == "intervened" and date.fromisoformat(e["date"]) >= data["score_start"] for e in evaluations),
        right_censored_count=sum(e["status"] == "right_censored" and date.fromisoformat(e["date"]) >= data["score_start"] for e in evaluations))


def threshold_evaluation(out, data, group):
    ledger, orders, cases = defaultdict(list), defaultdict(list), []
    for row in out["ledger"]:
        ledger[row["window_origin"], row["item_id"]].append(row)
    for o in out["orders"]:
        orders[o["item_id"]].append(o)
    for a in out["alarms"]:
        day = date.fromisoformat(a["date"])
        if group == "D" and day < data["score_start"]:
            continue
        future = [r for r in ledger[a["window_origin"], a["item_id"]]
                  if day < date.fromisoformat(r["date"]) <= day + timedelta(days=7)]
        actual = min((r["date"] for r in future if r["closing_qty"] < a["rop"]), default=None)
        reason = "already_below_rop" if a["below_rop"] else "right_censored" if actual is None and len(future) < 7 else None
        if reason is None and actual is None and group == "D" and any(
            not o["is_initial"] and day <= date.fromisoformat(o["ordered_on"])
            and date.fromisoformat(o["eta"]) <= min(data["end"], day+timedelta(days=7)) for o in orders[a["item_id"]]):
            reason = "intervened"
        cases.append(dict(as_of_date=a["date"], item_id=a["item_id"], window_origin=a["window_origin"],
            predicted_threshold_date=a["predicted_threshold_date"], actual_threshold_date=actual,
            is_evaluable=reason is None, exclusion_reason=reason))
    confusion, errors = dict(TP=0, FP=0, FN=0, TN=0), []
    for c in cases:
        if not c["is_evaluable"]:
            continue
        pred, actual = c["predicted_threshold_date"], c["actual_threshold_date"]
        confusion["TP" if pred and actual else "FP" if pred else "FN" if actual else "TN"] += 1
        if pred and actual:
            errors.append(abs((date.fromisoformat(pred)-date.fromisoformat(actual)).days))
    tp, fp, fn = (confusion[k] for k in ("TP", "FP", "FN"))
    return cases, dict(**confusion, scope="whole_alert_replay", basis="origin_rop_crossing_within_warning_horizon",
        precision=ratio(tp, tp+fp), recall=ratio(tp, tp+fn), signal_count=tp+fp, event_denominator=tp+fn,
        evaluated_count=sum(confusion.values()), excluded_count=sum(not c["is_evaluable"] for c in cases), date_mae=mean(errors))


def inventory(out, start):
    rows = sorted((r for r in out["ledger"] if r["date"] > r["window_origin"] and date.fromisoformat(r["date"]) >= start),
                  key=lambda r: (r["window_origin"], r["date"], r["item_id"]))
    orders = [o for o in out["orders"] if not o["is_initial"] and date.fromisoformat(o["ordered_on"]) >= start]
    sales = sum(r["sales_qty"] for r in rows); served = sum(r["fulfilled_qty"] for r in rows)
    last = max(r["window_origin"] for r in out["ledger"])
    return dict(sales_qty=sales, fulfilled_qty=served, shortage_qty=sales-served, fill_rate=ratio(served, sales),
        mean_closing=mean([r["closing_qty"] for r in rows]), mean_pending=mean([r["pending_qty"] for r in rows]),
        stockout_item_days=sum(r["closing_qty"] == 0 for r in rows),
        depletion_episodes=sum(date.fromisoformat(e["date"]) >= start for e in out["events"]),
        order_count=len(orders), ordered_qty=sum(o["ordered_qty"] for o in orders),
        closing_pending_qty=sum(o["ordered_qty"] for o in out["orders"] if o["window_origin"] == last and not o["received"]))


def changes(baseline, candidate):
    before = {(c["window_origin"], c["item_id"]): c["actual_depletion_date"] for c in baseline["cases"]
              if not c["already_depleted"] and c["actual_depletion_date"] is not None}
    after = {(c["window_origin"], c["item_id"]): c["actual_depletion_date"] for c in candidate["cases"]
             if not c["already_depleted"] and c["actual_depletion_date"] is not None}
    return [dict(window_origin=w, item_id=i, baseline_date=before.get((w,i)), candidate_date=after.get((w,i)),
                 change="appeared" if (w,i) not in before else "disappeared" if (w,i) not in after else "moved")
            for w,i in sorted(before.keys() | after.keys()) if before.get((w,i)) != after.get((w,i))]


def same(actual, expected, location="result"):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), "Fields differ at " + location)
        for key in expected:
            same(actual[key], expected[key], location + "." + key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), "Rows differ at " + location)
        # Table ordering is incidental; every keyed row and duplicate still has to match.
        left = sorted(actual, key=row_key) if expected and isinstance(expected[0], dict) else actual
        right = sorted(expected, key=row_key) if expected and isinstance(expected[0], dict) else expected
        for a, e in zip(left, right, strict=True):
            same(a, e, location + "[]")
    elif type(expected) is float:
        require(type(actual) in (int, float) and math.isfinite(actual) and abs(actual-expected) <= 1e-8,
                "Number differs at " + location)
    else:
        require(type(actual) is type(expected) and actual == expected, "Value differs at " + location)


def check_provenance(snapshot, p, settings=None, baseline_root=None):
    meta = snapshot["meta"]
    for key in ("source_sha256", "forecast_config_sha256", "selection_sha256"):
        require(isinstance(meta[key], str) and len(meta[key]) == 64
                and all(c in "0123456789abcdef" for c in meta[key]), "Invalid lineage checksum")
    require(meta.get("provenance") in ("synthetic", "local_frozen_db"), "Unknown evidence class")
    if meta["provenance"] == "synthetic":
        return "frozen_synthetic_inputs"
    # Original-source corroboration is I/O, separate from the independent arithmetic above.
    from sqlalchemy import text
    from core.db import database
    from core.settings import Settings
    from modules.runs.models import Run
    from src.data import audit_orders
    import uuid

    settings = settings or Settings.from_env()
    baseline_root = Path(baseline_root or PROJECT_ROOT / "outputs/step15/runs")
    origin, end = (date.fromisoformat(snapshot["period"][k]) for k in ("origin", "end"))
    engine, sessions = database(settings.database_url)
    engine.update_execution_options(postgresql_readonly=True, isolation_level="REPEATABLE READ")
    try:
        with sessions() as session:
            require(session.scalar(text("SHOW transaction_read_only")) == "on", "Verifier requires read-only DB")
            roles = {role: session.get(Run, uuid.UUID(p[role])) for role in
                     ("source_run", "forecast_run", "baseline_alert_run", "baseline_policy_run")}
            source, forecast = roles["source_run"], roles["forecast_run"]
            require(source is not None and forecast is not None, "Missing authoritative parent")
            kinds = dict(source_run="source_import", forecast_run="forecast",
                         baseline_alert_run="alert_replay", baseline_policy_run="policy_replay")
            for role, run in roles.items():
                require(run is not None and run.status == "complete" and run.kind == kinds[role], "Invalid parent status")
                require(checksum(run.config_snapshot) == run.config_sha256, "Parent config checksum differs")
                same(meta["parents"][role], dict(id=str(run.id), config_sha256=run.config_sha256,
                                                artifact_manifest=run.artifact_manifest), "parent_metadata")
                if role != "source_run":
                    require(run.source_import_run_id == source.id and run.source_sha256 == source.source_sha256
                            and run.target_version == source.target_version
                            and run.config_snapshot["source_parent_config_sha256"] == source.config_sha256,
                            "Authoritative source lineage differs")
                if role.startswith("baseline"):
                    require(run.forecast_run_id == forecast.id
                            and run.config_snapshot["forecast_parent_config_sha256"] == forecast.config_sha256,
                            "Authoritative forecast lineage differs")
                root = (baseline_root if role.startswith("baseline") else settings.output_root) / str(run.id)
                require(bool(run.artifact_manifest), "Parent has no sealed artifacts")
                for name, h in run.artifact_manifest.items():
                    path = (root / name).resolve()
                    require(path.is_relative_to(root.resolve()) and sha(path) == h, "Parent artifact differs")
            require(meta["source_sha256"] == source.source_sha256 and meta["forecast_config_sha256"] == forecast.config_sha256
                    and meta["selection_sha256"] == forecast.selection_sha256, "Authoritative lineage checksum differs")
            same(snapshot["catalog"], source.config_snapshot["catalog_snapshot"], "source_catalog")
            sid = source.config_snapshot.get("resolved_source_import_run_id", str(source.id))
            daily = {(r["date"], r["item_id"]): r for r in snapshot["daily"]}
            n = 0
            query = text("""SELECT date,item_id,sales_qty,actual_available FROM daily_sales
                WHERE source_import_run_id=:source AND date BETWEEN :start AND :finish""")
            for row in session.execute(query, dict(source=uuid.UUID(str(sid)), start=origin-timedelta(days=27), finish=end)):
                same(daily.get((row.date.isoformat(), row.item_id)), dict(date=row.date.isoformat(), item_id=row.item_id,
                     quantity=row.sales_qty, actual_available=row.actual_available), "source_daily")
                n += 1
            require(n == len(daily), "Daily snapshot coverage differs")
            vectors = {(r["as_of_date"], r["item_id"]): r["forecast"] for r in snapshot["forecasts"]}
            n = 0
            query = text("""SELECT as_of_date,item_id,horizon_day,forecast_qty FROM item_forecasts
                WHERE run_id=:run AND as_of_date BETWEEN :start AND :finish""")
            for row in session.execute(query, dict(run=forecast.id, start=origin, finish=end)):
                f = vectors.get((row.as_of_date.isoformat(), row.item_id))
                require(f is not None and len(f) == 14 and 1 <= row.horizon_day <= 14
                        and f[row.horizon_day-1] == row.forecast_qty, "Frozen forecast differs from DB")
                n += 1
            require(n == 14*len(vectors), "Forecast snapshot coverage differs")
            frozen = roles["baseline_alert_run"].config_snapshot
            same(snapshot.get("receipts", []), frozen["scenario"]["settings"]["receipts_initial"], "known_receipts")
            if snapshot["split"] == "test":
                same(snapshot["policies"], frozen["policies"], "frozen_test_policy")
            else:
                warehouses = {(w["destination_country"], w["carrier"]): w["code"] for w in source.config_snapshot["warehouse_snapshot"]}
                expected = []
                for item in snapshot["catalog"]:
                    if item["first_seen_date"] > origin.isoformat():
                        continue
                    sample = [daily[d.isoformat(), item["item_id"]]["quantity"] for d in calendar(origin-timedelta(days=27), origin)]
                    ordinal = int(warehouses[item["destination_country"], item["carrier"]].split("-")[-1])
                    expected.append(dict(item_id=item["item_id"], effective_from=origin.isoformat(), effective_to=None,
                        configured_rop_floor=math.ceil((6 if ordinal % 2 else 8) * (sum(sample)/28)),
                        safety_days=2 if ordinal % 2 else 3, moq=5 if item["product_type"] == "eSIM" else 10,
                        assumption_source="research_synthetic_seed_v1", is_assumed=True))
                same(snapshot["policies"], expected, "causal_validation_seed")
    finally:
        engine.dispose()
    raw = settings.order_source("orders_snapshot")
    require(sha(raw) == meta["source_sha256"], "Original CSV checksum differs")
    sales, audit = audit_orders(raw, read(PROJECT_ROOT / "data/configs/config.json"))
    require(audit["source_sha256_before"] == meta["source_sha256"], "Source audit differs")
    mapping = {(i["destination_country"], i["carrier"], i["sku"], i["product_type"]): i["item_id"] for i in snapshot["catalog"]}
    expected = []
    for seq, r in enumerate(sales.sort_values(["order_datetime", "order_id"], kind="mergesort").itertuples(index=False), 1):
        d = r.date.date()
        if origin < d <= end:
            expected.append(dict(date=d.isoformat(), item_id=mapping[r.destination_country,r.carrier,r.sku,r.product_type],
                                 sequence=seq, quantity=int(r.quantity)))
    same(snapshot["sales"], expected, "audited_source_transactions")
    return "original_csv_and_readonly_db"


class ReportTable(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.row = None; self.cell = None

    def handle_starttag(self, tag, attrs):
        require(tag != "script", "Unexpected script in static report")
        if tag == "tr": self.row = []
        if tag in ("td", "th"): self.cell = ""

    def handle_data(self, data):
        if self.cell is not None: self.cell += data

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.row.append(self.cell); self.cell = None
        if tag == "tr": self.rows.append(self.row); self.row = None


def verify_run(folder, *, write_receipt=True, settings=None, baseline_root=None):
    folder = Path(folder).resolve()
    manifest = read(folder / "manifest.json")
    p = read(PROTOCOL)
    require(checksum(p) == "7cc329aa47583cbf5536416bfc04b291f40c262bc0b50cc7671f1965ebd1990a", "Unsupported protocol revision")
    require(manifest["status"] == "calculated_unverified" and manifest["independent_replay"] is False
            and manifest["metrics_status"] == "unverified", "Unsupported manifest state")
    same(manifest["protocol"], p, "protocol")
    require(manifest["protocol_sha256"] == checksum(p) and manifest["research_code_sha256"] == sha(RUNNER)
            and manifest["application_code_sha256"] == code_digest(), "Code/protocol binding differs")
    same(manifest["requirements_sha256"], {k: sha(PROJECT_ROOT/k) for k in ("requirements.txt", "web/backend/requirements.txt")}, "requirements")
    ids = manifest["config_ids"]
    require(type(ids) is list and len(ids) == len(set(ids)), "Duplicate configuration")
    known = {c["id"]: c for c in matrix()}
    require(all(i in known for i in ids), "Unknown configuration")
    split = manifest["split"]
    require(split in ("validation", "test"), "Unknown research split")
    required = {"inputs.json.gz", "metrics.json", "report.html"} | {"results/"+i+".json.gz" for i in ids}
    if split == "test": required.add("selection_lock.json")
    require(set(manifest["artifacts"]) == required, "Artifact inventory differs")
    for name, h in manifest["artifacts"].items():
        path = (folder/name).resolve()
        require(path.is_relative_to(folder) and path.is_file() and sha(path) == h, "Artifact checksum differs")
    snapshot = read(folder/"inputs.json.gz")
    require(snapshot["split"] == split and snapshot["period"] == p[split], "Snapshot period differs")
    same(snapshot["meta"], manifest["input_meta"], "input_metadata")
    data = inputs(snapshot)
    anchor = check_provenance(snapshot, p, settings, baseline_root)
    if split == "validation":
        require(ids == [c["id"] for c in matrix()], "Validation matrix differs")
    else:
        lock = read(folder/"selection_lock.json")
        validation = Path(lock["validation_run"]).resolve()
        vm = read(validation/"manifest.json")
        require(vm["split"] == "validation", "Selection parent is not validation")
        proof = verify_run(validation, write_receipt=False, settings=settings, baseline_root=baseline_root)
        require((validation/"verification.json").is_file() and proof["manifest_sha256"] == lock["validation_manifest_sha256"]
                and sha(validation/"verification.json") == lock["validation_verification_sha256"]
                and lock["protocol_sha256"] == checksum(p), "Selection receipt binding differs")
        for key in ("source_sha256", "forecast_config_sha256", "selection_sha256"):
            require(lock[key] == vm["input_meta"][key] == snapshot["meta"][key], "Selection lineage differs")
        require(proof["evidence_class"] == snapshot["meta"]["provenance"], "Evidence class cannot be upgraded")
        selected = lock["selected_configs"]
        require(bool(selected) and len(selected) == len(set(selected))
                and all(i in known and known[i]["group"] in ("C", "D") for i in selected), "Invalid representatives")
        require(all(sum(known[i]["group"] == g for i in selected) <= 3 for g in ("C", "D")), "Too many representatives")
        require(ids == [i for i in known if i in set(selected) | {"A-base", "B-daily", "C-days-m1-cover7", "D-days-m1-cover7"}], "Test matrix differs from lock")
    summaries, baseline, first_cases = [], None, None
    rows_checked = defaultdict(int)
    for identity in ids:
        expected = rebuild_prepared(data, known[identity])
        if known[identity]["group"] == "A": first_cases = expected["cases"]
        if known[identity]["group"] == "B":
            baseline = expected
            require([(r["window_origin"],r["item_id"],r["actual_depletion_date"],r["already_depleted"]) for r in first_cases]
                    == [(r["window_origin"],r["item_id"],r["actual_depletion_date"],r["already_depleted"]) for r in expected["cases"]], "A/B event populations differ")
        if known[identity]["group"] == "C":
            expected["event_changes"] = changes(baseline, expected)
            expected["metrics"]["event_changes"] = {k: sum(r["change"] == k for r in expected["event_changes"])
                                                    for k in ("appeared", "disappeared", "moved")}
        same(read(folder/"results"/(identity+".json.gz")), expected, identity)
        summaries.append(expected["metrics"])
        for name, table in expected.items():
            if isinstance(table, list): rows_checked[name] += len(table)
    reported = read(folder/"metrics.json")
    same(reported, summaries, "summary_metrics")
    columns = ["early_numerator", "event_denominator", "early_rate", "shortage_qty", "mean_closing", "ordered_qty"]
    parser = ReportTable(); parser.feed((folder/"report.html").read_text(encoding="utf-8"))
    same(parser.rows, [["Config", *columns]] + [[r["config"]["id"], *[str(r[k]) for k in columns]] for r in reported], "HTML_report")
    proof = dict(status="verified", independent_replay=True, verification_version="inventory-alert-safety-verifier-v1",
        evidence_class=snapshot["meta"]["provenance"], anchor_scope=anchor, manifest_sha256=sha(folder/"manifest.json"),
        input_snapshot_sha256=sha(folder/"inputs.json.gz"), verifier_code_sha256=sha(__file__),
        research_code_sha256=sha(RUNNER), application_code_sha256=code_digest(), protocol_sha256=checksum(p),
        configurations_checked=len(ids), rows_checked=dict(rows_checked))
    receipt = folder/"verification.json"
    if receipt.exists():
        previous = read(receipt)
        created = previous.pop("created_at")
        same(previous, proof, "existing_receipt")
        require(datetime.fromisoformat(created).tzinfo is not None, "Invalid receipt timestamp")
        proof["created_at"] = created
    else:
        proof["created_at"] = datetime.now(timezone.utc).isoformat()
        if write_receipt:
            with receipt.open("x", encoding="utf-8") as stream:
                json.dump(proof, stream, sort_keys=True, indent=2, allow_nan=False)
    return proof
