"""Local A/B/C/D research; calculations are sealed and independently checked by verify."""

import argparse
import csv
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import html
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
from fractions import Fraction
import sys
import uuid

import numpy as np
from core.hashes import code_digest, digest
from core.serialization import clean_json
from core.settings import PROJECT_ROOT
from modules.alerts.service import project, project_threshold, replay_metrics, threshold_metrics
from modules.inventory.service import PolicyValues, eta, fulfill_day, history_quantities, quantity, recommend, vector14


PROTOCOL_PATH = PROJECT_ROOT / "web/backend/configs/inventory-alert-experiments.json"


def protocol():
    p = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    constants = dict(horizon_days=14, lead_time_days=7, review_days=1, warning_horizon_days=7,
                     minimum_early_days=7, warmup_days=28, safety_lookback_days=28, safety_factor=1.0,
                     cover_days=7, safety_modes=["days", "volatility"], safety_multipliers=[.5, 1, 1.5],
                     sensitivity_cover_days=[3, 14])
    if any(p[k] != value for k, value in constants.items()):
        raise ValueError("Protocol changes require a new supported research version")
    for split in ("validation", "test"):
        if date.fromisoformat(p[split]["score_start"]) != date.fromisoformat(p[split]["origin"]) + timedelta(days=29):
            raise ValueError("The protocol requires 28 warmup days")
    return p


def days(start, end):
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def experiment_matrix():
    p = protocol()
    configs = [dict(id="A-base", group="A"), dict(id="B-daily", group="B")]
    for group in ("C", "D"):
        for mode in p["safety_modes"]:
            for multiplier in p["safety_multipliers"]:
                configs.append(dict(id=f"{group}-{mode}-m{multiplier:g}-cover7",
                                    group=group, mode=mode, multiplier=multiplier))
        for cover in p["sensitivity_cover_days"]:
            configs.append(dict(id=f"{group}-cover{cover}", group=group, cover=cover))
    configs.append(dict(id="D-days-m0-cover7", group="D", multiplier=0))
    return [dict({"cover": 7, "mode": "days", "multiplier": 1,
                  "add_ss": c["group"] == "C" and "cover" not in c}, **c) for c in configs]


def prepare_inputs(snapshot):
    """Reject gaps/duplicates; preserve integer counts and audited transaction order."""
    if type(snapshot.get("version")) is not int or snapshot["version"] != 1:
        raise ValueError("Unsupported research input version")
    period = {k: date.fromisoformat(snapshot["period"][k]) for k in ("origin", "end", "score_start")}
    origin, end = period["origin"], period["end"]
    if not origin < period["score_start"] <= end:
        raise ValueError("Invalid research period")
    catalog = {i["item_id"]: i for i in snapshot["catalog"]}
    if len(catalog) != len(snapshot["catalog"]):
        raise ValueError("Duplicate catalog item")
    if any(type(i) is not int or i <= 0 for i in catalog):
        raise ValueError("Catalog IDs must be positive integers")
    for collection in ("daily", "forecasts", "sales", "policies", "receipts"):
        if any(type(r["item_id"]) is not int or r["item_id"] not in catalog for r in snapshot.get(collection, [])):
            raise ValueError("Research row has an invalid item ID")
    cohort = sorted(i for i, r in catalog.items() if date.fromisoformat(r["first_seen_date"]) <= origin)
    if not cohort:
        raise ValueError("Empty research cohort")
    daily, forecasts, sales, policies = {}, {}, defaultdict(list), defaultdict(list)
    for row in snapshot["daily"]:
        key = (date.fromisoformat(row["date"]), row["item_id"])
        if key in daily or row["actual_available"] is not True or key[1] not in catalog:
            raise ValueError("Daily history must be unique and observed")
        daily[key] = quantity(row["quantity"])
    for row in snapshot["forecasts"]:
        key = (date.fromisoformat(row["as_of_date"]), row["item_id"])
        if key in forecasts or key[1] not in catalog:
            raise ValueError("Duplicate or unknown forecast item")
        forecasts[key] = vector14(row["forecast"])
    sequences = set()
    for row in snapshot["sales"]:
        day, item = date.fromisoformat(row["date"]), row["item_id"]
        seq = quantity(row["sequence"])
        if seq == 0 or seq in sequences or item not in catalog or not origin < day <= end:
            raise ValueError("Invalid audited sales sequence")
        sequences.add(seq)
        sales[(day, item)].append(dict(sequence=seq, quantity=quantity(row["quantity"])))
    for rows in sales.values():
        rows.sort(key=lambda r: r["sequence"])
    for p in snapshot["policies"]:
        policies[p["item_id"]].append(dict(p))
    for item in cohort:
        for day in days(origin - timedelta(days=27), end):
            if (day, item) not in daily:
                raise ValueError("Missing observed daily quantity")
            if day > origin and sum(r["quantity"] for r in sales[(day, item)]) != daily[(day, item)]:
                raise ValueError("Audited sales differ from daily quantity")
            if day >= origin:
                if (day, item) not in forecasts:
                    raise ValueError("Missing daily H14 vector")
                effective_policy(policies, item, day)
    lots, keys = [], set()
    for r in snapshot.get("receipts", []):
        ordered, arrival = date.fromisoformat(r["ordered_on"]), date.fromisoformat(r["eta"])
        q = quantity(r["ordered_qty"])
        if r["lot_key"] in keys or ordered > origin or arrival != eta(ordered) or q == 0 or r["item_id"] not in catalog:
            raise ValueError("Invalid known receipt")
        keys.add(r["lot_key"])
        lots.append(dict(item_id=r["item_id"], ordered_on=ordered, eta=arrival,
                         ordered_qty=q, order_key=r["lot_key"], is_initial=True))
    excluded = sorted(set(catalog) - set(cohort))
    return dict(**period, cohort=cohort, daily=daily, forecasts=forecasts, sales=sales,
                policies=policies, receipts=lots, excluded_items=excluded,
                excluded_sales_qty=sum(q for (d, i), q in daily.items() if origin < d <= end and i in excluded))


def effective_policy(policies, item, day):
    matches = [p for p in policies[item] if date.fromisoformat(p["effective_from"]) <= day
               and (p.get("effective_to") is None or day < date.fromisoformat(p["effective_to"]))]
    if len(matches) != 1:
        raise ValueError("Exactly one effective frozen policy is required")
    return matches[0]


def history(data, item, origin):
    try:
        values = [data["daily"][(d, item)] for d in days(origin - timedelta(days=27), origin)]
    except KeyError as exc:
        raise ValueError("Missing 28-day observed history") from exc
    return history_quantities(values, 28)


def decision(data, config, item, day, stock, pending):
    p = effective_policy(data["policies"], item, day)
    values = PolicyValues(configured_rop_floor=p["configured_rop_floor"], moq=p["moq"],
                          safety_days=p["safety_days"], safety_mode=config["mode"], rop_mode="forecast",
                          safety_lookback_days=28, safety_factor=1, safety_multiplier=config["multiplier"])
    return recommend(data["forecasts"][(day, item)], stock, pending, values,
                     history(data, item, day) if config["mode"] == "volatility" else None)


def simulate(data, config):
    """One frozen-cohort experiment; decisions use only the current prefix."""
    if config not in experiment_matrix():
        raise ValueError("Configuration is outside the locked matrix")
    group, origin, end = config["group"], data["origin"], data["end"]
    windows = [(origin, end)] if group == "D" else [
        (d, d + timedelta(days=14)) for d in days(origin, end)
        if (d - origin).days % 14 == 0 and d + timedelta(days=14) <= end]
    if not windows:
        raise ValueError("No complete 14-day research window")
    result = {name: [] for name in ("ledger", "alarms", "events", "transactions", "orders", "initialization")}
    for start, finish in windows:
        stocks, lots, lots_by_item = {}, [], defaultdict(list)
        for item in data["cohort"]:
            base = quantity(math.ceil(float(np.mean(history(data, item, start))) * config["cover"]))
            ss = decision(data, config, item, start, 0, 0)["ss"] if config["add_ss"] else 0
            stocks[item] = quantity(base + ss)
            result["initialization"].append(dict(window_origin=start, item_id=item,
                                                  base_qty=base, added_ss=ss, initial_qty=stocks[item]))
        lots.extend(dict(r, received=False, window_origin=start) for r in data["receipts"]
                    if r["item_id"] in stocks and r["eta"] > start)
        for lot in lots:
            lots_by_item[lot["item_id"]].append(lot)
        for day in days(start, finish):
            for item in data["cohort"]:
                opening = stocks[item]
                item_lots = lots_by_item[item]
                arriving = [r for r in item_lots if r["eta"] == day and not r["received"]]
                received = sum(r["ordered_qty"] for r in arriving)
                balance = quantity(opening + received)
                for lot in arriving:
                    lot["received"] = True
                demands = data["sales"][(day, item)] if day > start else []
                fulfilled = fulfill_day(opening, received, [r["quantity"] for r in demands])
                for demand, event in zip(demands, fulfilled["events"], strict=True):
                    record = dict(window_origin=start, date=day, item_id=item,
                                  sequence=demand["sequence"], **event)
                    result["transactions"].append(record)
                    if balance > 0 and event["balance_after"] == 0:
                        result["events"].append(dict(event_id=f"{start}:{item}:{demand['sequence']}",
                                                      window_origin=start, item_id=item, date=day,
                                                      sequence=demand["sequence"]))
                    balance = event["balance_after"]
                stocks[item] = fulfilled["closing_qty"]
                pending = sum(r["ordered_qty"] for r in item_lots if not r["received"])
                cutoff = start if group == "A" else day
                values = decision(data, config, item, cutoff, stocks[item], pending)
                result["ledger"].append(dict(window_origin=start, date=day, item_id=item,
                    opening_qty=opening, receipts_qty=received, sales_qty=fulfilled["sales_qty"],
                    fulfilled_qty=fulfilled["fulfilled_qty"], shortage_qty=fulfilled["shortage_qty"],
                    closing_qty=stocks[item], forecast_as_of_date=cutoff, **values))
                if group != "A" or day == start:
                    known = defaultdict(int)
                    for lot in item_lots:
                        if not lot["received"]:
                            known[lot["eta"]] += lot["ordered_qty"]
                    projection = project(day, stocks[item], data["forecasts"][(cutoff, item)], known)
                    predicted = projection["predicted_depletion_date"] if stocks[item] > 0 else None
                    if group != "D" and predicted is not None and predicted > finish:
                        predicted = None
                    threshold = project_threshold(day, stocks[item], values["rop"], 7, projection["projection"])
                    result["alarms"].append(dict(window_origin=start, date=day, item_id=item,
                        origin_on_hand=stocks[item], rop=values["rop"], predicted_depletion_date=predicted,
                        predicted_threshold_date=threshold, below_rop=stocks[item] < values["rop"]))
                if group == "D" and values["recommended_qty"]:
                    lot = dict(window_origin=start, item_id=item, ordered_on=day, eta=eta(day),
                               ordered_qty=values["recommended_qty"], is_initial=False,
                               order_key=f"{start}:{item}:{day}", received=False)
                    lots.append(lot)
                    item_lots.append(lot)
        result["orders"].extend(lots)
    result["cases"], alert_metrics = score_continuous(data, result) if group == "D" else score_windows(result)
    result["threshold_cases"] = score_thresholds(data, result, group)
    result["metrics"] = dict(config=config, **alert_metrics,
        **inventory_metrics(result, data["score_start"] if group == "D" else origin + timedelta(days=1)),
        threshold_metrics=threshold_metrics(result["threshold_cases"]),
        excluded_tail_days=0 if group == "D" else (end - windows[-1][1]).days,
        cohort_items=len(data["cohort"]), excluded_items=data["excluded_items"],
        excluded_sales_qty=data["excluded_sales_qty"], metrics_status="unverified")
    # Ledger excludes the initialization row; whole-period order totals include Q placed at origin.
    result["all_period_inventory"] = inventory_metrics(result, origin)
    return result


def score_windows(result):
    cases, first_events, alarms = [], {}, defaultdict(list)
    for event in result["events"]:
        first_events.setdefault((event["window_origin"], event["item_id"]), event["date"])
    for alarm in result["alarms"]:
        alarms[(alarm["window_origin"], alarm["item_id"])].append(alarm)
    for initial in result["initialization"]:
        key = (initial["window_origin"], initial["item_id"])
        actual = first_events.get(key)
        alarm = next((r for r in alarms[key] if r["predicted_depletion_date"] is not None
                      and (actual is None or r["date"] < actual)), None)
        cases.append(dict(window_origin=key[0], item_id=key[1], actual_depletion_date=actual,
                          predicted_depletion_date=alarm["predicted_depletion_date"] if alarm else None,
                          as_of_date=alarm["date"] if alarm else key[0], already_depleted=initial["initial_qty"] == 0))
    return cases, dict(unit="item_window", **replay_metrics(cases))


def score_continuous(data, result):
    matches, evaluations = {}, []
    by_item, orders = defaultdict(list), defaultdict(list)
    for e in result["events"]:
        by_item[e["item_id"]].append(e)
    for order in result["orders"]:
        orders[order["item_id"]].append(order)
    for alarm in result["alarms"]:
        if alarm["predicted_depletion_date"] is None:
            continue
        day, item = alarm["date"], alarm["item_id"]
        limit = day + timedelta(days=14)
        event = next((e for e in by_item[item] if day < e["date"] <= limit), None)
        if event is not None:
            matches.setdefault(event["event_id"], alarm)
        # New Q is placed after that day's alarm; same-day Q was not a known receipt.
        intervened = any(not o.get("is_initial", False) and day <= o["ordered_on"]
                         and o["eta"] <= min(limit, data["end"])
                         for o in orders[item])
        status = ("TP" if event else "intervened" if intervened else "right_censored"
                  if limit > data["end"] else "FP")
        evaluations.append(dict(date=day, item_id=item, status=status,
            precision_evaluable=day >= data["score_start"] and status in ("TP", "FP"),
            event_id=event["event_id"] if event else None, intervened=intervened,
            right_censored=limit > data["end"]))
    cases, errors = [], []
    for event in result["events"]:
        if event["date"] < data["score_start"]:
            continue
        alarm = matches.get(event["event_id"])
        lead = (event["date"] - alarm["date"]).days if alarm else None
        cases.append(dict(**event, alarm_date=alarm["date"] if alarm else None,
                          predicted_depletion_date=alarm["predicted_depletion_date"] if alarm else None,
                          lead_days=lead, early=lead is not None and lead >= 7))
        if alarm:
            errors.append(abs((event["date"] - alarm["predicted_depletion_date"]).days))
    tp = sum(r["status"] == "TP" and r["precision_evaluable"] for r in evaluations)
    fp = sum(r["status"] == "FP" and r["precision_evaluable"] for r in evaluations)
    n, early = len(cases), sum(r["early"] for r in cases)
    result["alarm_evaluation"] = evaluations
    return cases, dict(unit="unique_depletion_episode", precision_unit="item_alarm_day", early_numerator=early,
        event_denominator=n, early_rate=early / n if n else None,
        recall=sum(r["alarm_date"] is not None for r in cases) / n if n else None,
        precision=tp / (tp + fp) if tp + fp else None, alarm_TP=tp, alarm_FP=fp,
        intervened_count=sum(r["status"] == "intervened" and r["date"] >= data["score_start"] for r in evaluations),
        right_censored_count=sum(r["status"] == "right_censored" and r["date"] >= data["score_start"] for r in evaluations),
        date_mae=float(np.mean(errors)) if errors else None)


def score_thresholds(data, result, group):
    cases = []
    by_item, orders = defaultdict(list), defaultdict(list)
    for row in result["ledger"]:
        by_item[(row["window_origin"], row["item_id"])].append(row)
    for order in result["orders"]:
        orders[order["item_id"]].append(order)
    for alarm in result["alarms"]:
        if group == "D" and alarm["date"] < data["score_start"]:
            continue
        rows = by_item[(alarm["window_origin"], alarm["item_id"])]
        future = [r for r in rows if alarm["date"] < r["date"] <= alarm["date"] + timedelta(days=7)]
        actual = next((r["date"] for r in future if r["closing_qty"] < alarm["rop"]), None)
        reason = "already_below_rop" if alarm["below_rop"] else "right_censored" if actual is None and len(future) < 7 else None
        if reason is None and actual is None and group == "D" and any(
            not o.get("is_initial", False) and alarm["date"] <= o["ordered_on"]
            and o["eta"] <= min(data["end"], alarm["date"] + timedelta(days=7))
            for o in orders[alarm["item_id"]]):
            reason = "intervened"
        cases.append(dict(as_of_date=alarm["date"], item_id=alarm["item_id"], window_origin=alarm["window_origin"],
                          predicted_threshold_date=alarm["predicted_threshold_date"], actual_threshold_date=actual,
                          is_evaluable=reason is None, exclusion_reason=reason))
    return cases


def inventory_metrics(result, score_start):
    rows = [r for r in result["ledger"] if r["date"] > r["window_origin"] and r["date"] >= score_start]
    sales, fulfilled = sum(r["sales_qty"] for r in rows), sum(r["fulfilled_qty"] for r in rows)
    orders = [o for o in result["orders"] if not o["is_initial"] and o["ordered_on"] >= score_start]
    last_window = max(r["window_origin"] for r in result["ledger"])
    return dict(sales_qty=sales, fulfilled_qty=fulfilled, shortage_qty=sales - fulfilled,
                fill_rate=fulfilled / sales if sales else None,
                mean_closing=float(np.mean([r["closing_qty"] for r in rows])) if rows else None,
                mean_pending=float(np.mean([r["pending_qty"] for r in rows])) if rows else None,
                stockout_item_days=sum(r["closing_qty"] == 0 for r in rows),
                depletion_episodes=sum(r["date"] >= score_start for r in result["events"]),
                order_count=len(orders), ordered_qty=sum(o["ordered_qty"] for o in orders),
                closing_pending_qty=sum(o["ordered_qty"] for o in result["orders"]
                                        if o["window_origin"] == last_window and not o["received"]))


def compare_events(baseline, candidate):
    def events(result):
        return {(r["window_origin"], r["item_id"]): r["actual_depletion_date"]
                for r in result["cases"] if not r["already_depleted"] and r["actual_depletion_date"] is not None}
    before, after = events(baseline), events(candidate)
    changes = []
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old != new:
            changes.append(dict(window_origin=key[0], item_id=key[1], baseline_date=old, candidate_date=new,
                                change="appeared" if old is None else "disappeared" if new is None else "moved"))
    return changes


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    payload = json.dumps(clean_json(value), ensure_ascii=False, sort_keys=True, indent=2,
                         allow_nan=False, default=json_date).encode("utf-8")
    Path(path).write_bytes(gzip.compress(payload, mtime=0) if str(path).endswith(".gz") else payload)


def json_date(value):
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError("Unsupported research JSON value")


def read_json(path):
    payload = Path(path).read_bytes()
    return json.loads(gzip.decompress(payload) if str(path).endswith(".gz") else payload)


def load_database_inputs(split, settings, baseline_root=None):
    """Freeze bounded research inputs in one repeatable-read, read-only transaction."""
    import pandas as pd
    from sqlalchemy import text
    from core.db import database
    from core.run_context import required_run, source_data_id
    from src.data import audit_orders

    p, period = protocol(), protocol()[split]
    origin, end = date.fromisoformat(period["origin"]), date.fromisoformat(period["end"])
    baseline_root = Path(baseline_root or PROJECT_ROOT / "outputs/step15/runs")
    engine, sessions = database(settings.database_url)
    engine.update_execution_options(postgresql_readonly=True, isolation_level="REPEATABLE READ")
    try:
        with sessions() as session:
            if session.scalar(text("SHOW transaction_read_only")) != "on":
                raise ValueError("Research database connection is not read-only")
            parents = {}
            for role, kind in [("source_run", "source_import"), ("forecast_run", "forecast"),
                               ("baseline_alert_run", "alert_replay"), ("baseline_policy_run", "policy_replay")]:
                run = required_run(session, uuid.UUID(p[role]), kind, complete=True)
                folder = (baseline_root if role.startswith("baseline") else settings.output_root) / str(run.id)
                if not run.artifact_manifest:
                    raise ValueError("Parent has no sealed artifacts")
                for name, checksum in run.artifact_manifest.items():
                    path = (folder / name).resolve()
                    if not path.is_relative_to(folder.resolve()) or file_hash(path) != checksum:
                        raise ValueError("Sealed parent artifact differs")
                parents[role] = run
            source, forecast = parents["source_run"], parents["forecast_run"]
            for run in list(parents.values())[1:]:
                if run.source_import_run_id != source.id or run.source_sha256 != source.source_sha256:
                    raise ValueError("Frozen source lineage differs")
            if not forecast.selection_sha256 or any(parents[r].forecast_run_id != forecast.id
                                                    for r in ("baseline_alert_run", "baseline_policy_run")):
                raise ValueError("Frozen forecast lineage differs")
            daily_frame = pd.read_sql(text("""SELECT item_id,date,sales_qty,actual_available FROM daily_sales
                WHERE source_import_run_id=:source AND date BETWEEN :start AND :finish ORDER BY date,item_id"""),
                session.connection(), params=dict(source=source_data_id(source),
                start=origin - timedelta(days=27), finish=end))
            forecast_frame = pd.read_sql(text("""SELECT item_id,as_of_date,horizon_day,forecast_qty FROM item_forecasts
                WHERE run_id=:run AND as_of_date BETWEEN :start AND :finish ORDER BY as_of_date,item_id,horizon_day"""),
                session.connection(), params=dict(run=forecast.id, start=origin, finish=end))
            catalog = source.config_snapshot["catalog_snapshot"]
            warehouses = source.config_snapshot["warehouse_snapshot"]
            base = parents["baseline_alert_run"].config_snapshot
            frozen_policies = clean_json(base["policies"])
            receipts = clean_json(base["scenario"]["settings"]["receipts_initial"])
            meta = dict(provenance="local_frozen_db", source_sha256=source.source_sha256,
                        forecast_config_sha256=forecast.config_sha256, selection_sha256=forecast.selection_sha256,
                        parents={role: dict(id=str(r.id), config_sha256=r.config_sha256,
                                          artifact_manifest=r.artifact_manifest) for role, r in parents.items()})
    finally:
        engine.dispose()
    cfg = read_json(PROJECT_ROOT / "data/configs/config.json")
    raw_sales, audit = audit_orders(settings.order_source("orders_snapshot"), cfg)
    if audit["source_sha256_before"] != meta["source_sha256"]:
        raise ValueError("Raw source changed since import")
    item_map = {(i["destination_country"], i["carrier"], i["sku"], i["product_type"]): i["item_id"] for i in catalog}
    sales = []
    for sequence, row in enumerate(raw_sales.sort_values(["order_datetime", "order_id"], kind="mergesort").itertuples(index=False), 1):
        day = row.date.date()
        if origin < day <= end:
            sales.append(dict(date=day.isoformat(), item_id=item_map[(row.destination_country, row.carrier, row.sku, row.product_type)],
                              sequence=sequence, quantity=int(row.quantity)))
    daily = [dict(date=r.date.isoformat(), item_id=int(r.item_id), quantity=int(r.sales_qty) if pd.notna(r.sales_qty) else None,
                  actual_available=bool(r.actual_available)) for r in daily_frame.itertuples(index=False)]
    forecasts = []
    for (day, item), rows in forecast_frame.groupby(["as_of_date", "item_id"], sort=False):
        if rows.horizon_day.tolist() != list(range(1, 15)):
            raise ValueError("Incomplete or duplicate forecast horizons")
        forecasts.append(dict(as_of_date=day.isoformat(), item_id=int(item), forecast=rows.forecast_qty.tolist()))
    if split == "validation":
        history_map = {(r["date"], r["item_id"]): r for r in daily}
        route_codes = {(w["destination_country"], w["carrier"]): w["code"] for w in warehouses}
        frozen_policies = []
        for item in catalog:
            if item["first_seen_date"] > period["origin"]:
                continue
            rows = [history_map[(d.isoformat(), item["item_id"])] for d in days(origin - timedelta(days=27), origin)]
            if not all(r["actual_available"] is True for r in rows):
                raise ValueError("Validation seed needs observed history")
            avg = sum(history_quantities([r["quantity"] for r in rows], 28)) / 28
            ordinal = int(route_codes[(item["destination_country"], item["carrier"])].split("-")[-1])
            frozen_policies.append(dict(item_id=item["item_id"], effective_from=period["origin"], effective_to=None,
                configured_rop_floor=math.ceil((6 if ordinal % 2 else 8) * avg),
                safety_days=2 if ordinal % 2 else 3, moq=5 if item["product_type"] == "eSIM" else 10,
                assumption_source="research_synthetic_seed_v1", is_assumed=True))
        # This protocol's baseline declares no initial lots; never invent validation receipts.
        if receipts:
            raise ValueError("Validation requires a separately declared receipt scenario")
    return clean_json(dict(version=1, split=split, period=period, meta=meta, catalog=catalog,
                           daily=daily, forecasts=forecasts, sales=sales, policies=frozen_policies, receipts=receipts))


def verify_artifacts(folder):
    """Integrity only. Independent mathematical replay is milestone 3."""
    folder = Path(folder).resolve()
    manifest = read_json(folder / "manifest.json")
    if manifest["status"] != "calculated_unverified" or manifest["independent_replay"] is not False:
        raise ValueError("Unsupported research manifest status")
    if digest(manifest["protocol"]) != manifest["protocol_sha256"]:
        raise ValueError("Research protocol checksum differs")
    artifacts = manifest["artifacts"]
    required = {"inputs.json.gz", "metrics.json", "report.html"} | {
        "results/" + c + ".json.gz" for c in manifest["config_ids"]}
    if not required.issubset(artifacts):
        raise ValueError("Missing required research artifact")
    for name, expected in artifacts.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or file_hash(path) != expected:
            raise ValueError("Research artifact checksum differs")
    return dict(status="artifact_integrity_passed", independent_replay=False,
                metrics_status="unverified", artifacts_checked=len(artifacts))


def select_representatives(metrics):
    """Three predeclared objectives, exact event-rate ordering, then quantity/ID ties."""
    known = {c["id"]: c for c in experiment_matrix()}
    groups = {g: [] for g in ("C", "D")}
    seen = set()
    for row in metrics:
        identity = row["config"]["id"]
        if identity not in known or identity in seen or row["config"] != known[identity]:
            raise ValueError("Invalid or duplicate selection configuration")
        seen.add(identity)
        if known[identity]["group"] not in groups:
            continue
        n, d = row["early_numerator"], row["event_denominator"]
        if type(n) is not int or type(d) is not int or not 0 <= n <= d:
            raise ValueError("Invalid event counts for selection")
        if (d == 0 and row["early_rate"] is not None) or (d > 0 and (
            type(row["early_rate"]) not in (int, float) or not math.isfinite(row["early_rate"])
            or abs(row["early_rate"]-n/d) > 1e-8)):
            raise ValueError("Selection rate differs from event counts")
        for field in ("shortage_qty", "ordered_qty"):
            quantity(row[field])
        if type(row["mean_closing"]) not in (int, float) or not math.isfinite(row["mean_closing"]) or row["mean_closing"] < 0:
            raise ValueError("Selection needs a finite inventory mean")
        groups[known[identity]["group"]].append(row)
    selected, details = [], []
    for group, rows in groups.items():
        if not rows:
            raise ValueError("Both C and D must be represented")
        for criterion in protocol()["selection"]:
            eligible = [r for r in rows if r["event_denominator"] > 0] if criterion == "highest_early_rate" else rows
            if not eligible:
                details.append(dict(group=group, criterion=criterion, config_id=None, value=None))
                continue
            field = {"highest_early_rate": "early_rate", "lowest_shortage_qty": "shortage_qty", "lowest_mean_closing": "mean_closing"}[criterion]
            def rank(r):
                value = -Fraction(r["early_numerator"], r["event_denominator"]) if field == "early_rate" else r[field]
                return value, r["ordered_qty"], r["config"]["id"]
            winner = min(eligible, key=rank)
            identity = winner["config"]["id"]
            if identity not in selected:
                selected.append(identity)
            details.append(dict(group=group, criterion=criterion, config_id=identity,
                                value=winner["early_numerator"]/winner["event_denominator"] if field == "early_rate" else winner[field]))
    return selected, details


def write_selection_lock(folder, baseline_root=None):
    from web.backend.research.inventory_alert_verification import representatives, verify_run

    folder = Path(folder).resolve()
    manifest = read_json(folder/"manifest.json")
    if manifest["split"] != "validation":
        raise ValueError("Selection must not read test outcomes")
    proof = verify_run(folder, baseline_root=baseline_root)
    metrics = read_json(folder/"metrics.json")
    selected, details = select_representatives(metrics)
    if (selected, details) != representatives(metrics):
        raise ValueError("Independent selection differs")
    lock = dict(validation_run=str(folder), validation_manifest_sha256=proof["manifest_sha256"],
        validation_verification_sha256=file_hash(folder/"verification.json"), protocol_sha256=proof["protocol_sha256"],
        selected_configs=selected, selection_details=details,
        **{k: manifest["input_meta"][k] for k in ("source_sha256", "forecast_config_sha256", "selection_sha256")})
    target = folder/"selection_lock.json"
    if target.exists():
        previous = read_json(target); created = previous.pop("created_at")
        if previous != lock or datetime.fromisoformat(created).tzinfo is None:
            raise ValueError("Existing selection lock differs; create a new run")
    else:
        lock["created_at"] = datetime.now(timezone.utc).isoformat()
        with target.open("x", encoding="utf-8") as stream:
            json.dump(lock, stream, sort_keys=True, indent=2, allow_nan=False)
    # Human reports are derivatives; the lock and receipt bind the verified metrics/manifest.
    fields = ["early_numerator", "event_denominator", "early_rate", "precision", "recall", "date_mae",
              "fill_rate", "shortage_qty", "mean_closing", "ordered_qty", "mean_pending", "stockout_item_days"]
    with (folder/"validation-comparison.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream); writer.writerow(["config_id", "unit", "selected", *fields])
        for row in metrics:
            writer.writerow([row["config"]["id"], row["unit"], row["config"]["id"] in selected, *[row[k] for k in fields]])
    body = "".join("<tr><td>"+html.escape(row["config"]["id"])+"</td><td>"+str(row["config"]["id"] in selected)
        +"</td>"+"".join("<td>"+html.escape(str(row[k]))+"</td>" for k in fields)+"</tr>" for row in metrics)
    (folder/"validation-comparison.html").write_text("<!doctype html><meta charset='utf-8'><title>Validation comparison</title>"
        "<h1>Validation trên tồn mô phỏng — đã kiểm độc lập</h1><p>Chỉ validation, không phải nghiệm thu R07/T14. A/B cùng sự kiện; "
        "C/D thay tồn hoặc chính sách nên mẫu số riêng. D precision theo item/ngày; early theo đợt cạn duy nhất. "
        "Chưa chạy test hồi cứu. Evidence: "+html.escape(proof["evidence_class"])+".</p><p>Manifest SHA256: "+proof["manifest_sha256"]
        +"</p><table border='1'><tr><th>Config</th><th>Đại diện</th>"+"".join("<th>"+f+"</th>" for f in fields)
        +"</tr>"+body+"</table><pre>"+html.escape(json.dumps(details, indent=2))+"</pre>", encoding="utf-8")
    return target


def read_selection_lock(path, baseline_root=None):
    lock = read_json(path)
    validation = Path(lock["validation_run"]).resolve()
    verify_artifacts(validation)
    manifest, receipt = read_json(validation / "manifest.json"), read_json(validation / "verification.json")
    checksum = file_hash(validation / "manifest.json")
    if (receipt.get("status") != "verified" or receipt.get("independent_replay") is not True
        or receipt.get("manifest_sha256") != checksum or lock["validation_manifest_sha256"] != checksum
        or lock["validation_verification_sha256"] != file_hash(validation / "verification.json")
        or lock["protocol_sha256"] != digest(protocol()) or manifest["split"] != "validation"
        or manifest["research_code_sha256"] != file_hash(__file__)
        or manifest["application_code_sha256"] != code_digest()
        or manifest["protocol_sha256"] != lock["protocol_sha256"]):
        raise ValueError("Selection needs independently verified validation and matching code/protocol")
    from web.backend.research.inventory_alert_verification import representatives, verify_run

    verify_run(validation, write_receipt=False, baseline_root=baseline_root)
    selected = lock["selected_configs"]
    for key in ("source_sha256", "forecast_config_sha256", "selection_sha256"):
        if lock[key] != manifest["input_meta"][key]:
            raise ValueError("Selection lineage differs from validation")
    known = {c["id"]: c for c in experiment_matrix() if c["group"] in ("C", "D")}
    if not selected or len(selected) != len(set(selected)) or any(c not in known for c in selected):
        raise ValueError("Invalid locked representatives")
    if any(sum(known[c]["group"] == g for c in selected) > 3 for g in ("C", "D")):
        raise ValueError("Too many locked representatives")
    expected, details = representatives(read_json(validation/"metrics.json"))
    if selected != expected or lock.get("selection_details") != details:
        raise ValueError("Selection does not follow the predeclared validation rule")
    controls = {"A-base", "B-daily", "C-days-m1-cover7", "D-days-m1-cover7"}
    return lock, [c for c in experiment_matrix() if c["id"] in controls | set(selected)]


def calculate(snapshot, configs, output_root, selection_lock=None):
    p, split = protocol(), snapshot["split"]
    if split not in ("validation", "test") or snapshot["period"] != p[split]:
        raise ValueError("Snapshot period differs from the locked protocol")
    if snapshot["meta"].get("provenance") not in ("synthetic", "local_frozen_db"):
        raise ValueError("Research provenance must be explicit")
    if split == "validation" and configs != experiment_matrix():
        raise ValueError("Validation requires the complete locked matrix")
    data = prepare_inputs(snapshot)
    if split == "test":
        if selection_lock is None:
            raise ValueError("Test requires a verified validation selection lock")
        for key in ("source_sha256", "forecast_config_sha256", "selection_sha256"):
            if selection_lock[key] != snapshot["meta"][key]:
                raise ValueError("Test parent differs from validation selection")
    folder = Path(output_root) / (p["id"] + "-" + str(uuid.uuid4()))
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "results").mkdir()
    manifest = dict(status="running", independent_replay=False, metrics_status="unverified", split=split,
        protocol=p, protocol_sha256=digest(p), research_code_sha256=file_hash(__file__),
        application_code_sha256=code_digest(),
        python=platform.python_version(), created_at=datetime.now(timezone.utc).isoformat(),
        packages={name: version(name) for name in ("numpy", "pandas", "SQLAlchemy")},
        requirements_sha256={name: file_hash(PROJECT_ROOT / name)
                             for name in ("requirements.txt", "web/backend/requirements.txt")},
        input_meta=snapshot["meta"], config_ids=[c["id"] for c in configs], artifacts={})
    write_json(folder / "manifest.json", manifest)
    try:
        write_json(folder / "inputs.json.gz", snapshot)
        summaries, baseline, a_cases = [], None, None
        for config in configs:
            result = simulate(data, config)
            if config["group"] == "A":
                a_cases = [(r["window_origin"], r["item_id"], r["actual_depletion_date"], r["already_depleted"]) for r in result["cases"]]
            if config["group"] == "B":
                baseline = result
                b_cases = [(r["window_origin"], r["item_id"], r["actual_depletion_date"], r["already_depleted"]) for r in result["cases"]]
                if a_cases != b_cases:
                    raise ValueError("B changed the baseline event population")
            if config["group"] == "C":
                result["event_changes"] = compare_events(baseline, result)
                result["metrics"]["event_changes"] = {k: sum(r["change"] == k for r in result["event_changes"])
                                                       for k in ("appeared", "disappeared", "moved")}
            write_json(folder / "results" / (config["id"] + ".json.gz"), result)
            summaries.append(result["metrics"])
            print(f"Calculated {len(summaries)}/{len(configs)} {config['id']}", file=sys.stderr, flush=True)
        write_json(folder / "metrics.json", summaries)
        columns = ["early_numerator", "event_denominator", "early_rate", "shortage_qty", "mean_closing", "ordered_qty"]
        body = "".join("<tr><td>" + html.escape(r["config"]["id"]) + "</td>" + "".join(
            "<td>" + html.escape(str(r[k])) + "</td>" for k in columns) + "</tr>" for r in summaries)
        (folder / "report.html").write_text("<!doctype html><meta charset='utf-8'><title>SS research</title>"
            "<h1>Local research — unverified</h1><p>Retrospective; independent verifier pending. "
            "C/D populations differ from A/B. No acceptance or model improvement claimed.</p><table><tr><th>Config</th>"
            + "".join("<th>" + c + "</th>" for c in columns) + "</tr>" + body + "</table>", encoding="utf-8")
        if selection_lock is not None:
            write_json(folder / "selection_lock.json", selection_lock)
        manifest["artifacts"] = {f.relative_to(folder).as_posix(): file_hash(f) for f in sorted(folder.rglob("*"))
                                 if f.is_file() and f.name != "manifest.json"}
        manifest["status"] = "calculated_unverified"
        write_json(folder / "manifest.json", manifest)
    except Exception as exc:
        import traceback

        manifest.update(status="failed", error_type=type(exc).__name__)
        write_json(folder / "manifest.json", manifest)
        (folder / "failure.private.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("--snapshot", type=Path, help="Use an explicitly frozen local or synthetic input snapshot")
        command.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "outputs/research")
        command.add_argument("--baseline-root", type=Path, default=PROJECT_ROOT / "outputs/step15/runs")
        if name == "evaluate":
            command.add_argument("--selection-lock", type=Path, required=True)
    verify = commands.add_parser("verify", help="Independently reconstruct frozen inputs, outputs and metrics")
    verify.add_argument("--run-dir", type=Path, required=True)
    verify.add_argument("--baseline-root", type=Path, default=PROJECT_ROOT / "outputs/step15/runs")
    select = commands.add_parser("select", help="Independently verify validation and seal its representative selection")
    select.add_argument("--run-dir", type=Path, required=True)
    select.add_argument("--baseline-root", type=Path, default=PROJECT_ROOT / "outputs/step15/runs")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            from web.backend.research.inventory_alert_verification import verify_run

            print(json.dumps(verify_run(args.run_dir, baseline_root=args.baseline_root)))
            return 0
        if args.command == "select":
            path = write_selection_lock(args.run_dir, args.baseline_root)
            print(json.dumps(dict(selection_lock=str(path), selected_configs=read_json(path)["selected_configs"],
                                  status="validation_selection_locked")))
            return 0
        lock, configs = read_selection_lock(args.selection_lock, args.baseline_root) if args.command == "evaluate" else (None, experiment_matrix())
        split = "test" if args.command == "evaluate" else "validation"
        if args.snapshot:
            snapshot = read_json(args.snapshot)
        else:
            from core.settings import Settings

            if lock is not None and read_json(Path(lock["validation_run"])/"manifest.json")["input_meta"]["provenance"] != "local_frozen_db":
                raise ValueError("Synthetic validation cannot authorize a real-data evaluation")
            snapshot = load_database_inputs(split, Settings.from_env(), args.baseline_root)
        if lock is not None and snapshot["meta"]["provenance"] != read_json(Path(lock["validation_run"])/"manifest.json")["input_meta"]["provenance"]:
            raise ValueError("Validation and evaluation evidence classes differ")
        if snapshot["split"] != split:
            raise ValueError("Input split differs from command")
        folder = calculate(snapshot, configs, args.output_root, lock)
        print(json.dumps(dict(output=str(folder.resolve()), status="calculated_unverified", independent_replay=False)))
        return 0
    except Exception as exc:
        # Driver/JSON errors can contain local paths or credentials; do not print their text.
        print(json.dumps(dict(status="failed", error_type=type(exc).__name__,
                              message="Research command rejected; no independently verified result produced.")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
