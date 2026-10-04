"""Explicitly simulated inventory: strict on-hand triggers and dated receipts."""
from __future__ import annotations

import copy
import hashlib
import math

import numpy as np
import pandas as pd

from src.common import ITEM, ROUTE


def initialize_partners(sales, cfg):
    cfg = copy.deepcopy(cfg)
    inventory = cfg["inventory"]
    # Bootstrap is explicit, train-only and persisted in effective_config.json.
    if not inventory["partner_map"] and not inventory["partners"]:
        carriers = sorted(sales.loc[sales.date.le(pd.Timestamp(cfg["train_end"])), "carrier"].unique())
        for carrier in carriers:
            partner = "Vinaphone" if carrier == "Vina" else carrier
            inventory["partner_map"][carrier] = partner
            inventory["partners"][partner] = {"lead_time_days": 3, "review_days": 1,
                                               "safety_days": 4 if partner == "Vinaphone" else 2,
                                               "moq": 1, "is_assumed": True}
        inventory["mapping_origin"] = "train-only bootstrap of A09-A13; not verified business partners"
    return cfg


def partner_params(carrier, cfg):
    inventory = cfg["inventory"]
    partner = inventory["partner_map"].get(carrier)
    if partner is None or partner not in inventory["partners"]:
        raise ValueError("missing_partner_config")
    params = inventory["partners"][partner]
    for key in ["lead_time_days", "review_days", "safety_days", "moq"]:
        if key not in params or not np.isfinite(params[key]) or params[key] < 0:
            raise ValueError("invalid_partner_config")
    if params["lead_time_days"] < 1 or params["review_days"] < 1 or params["moq"] < 1:
        raise ValueError("invalid_partner_config")
    if params["lead_time_days"] + params["review_days"] > cfg["horizon"]:
        raise ValueError("horizon_shorter_than_lead_plus_review")
    return partner, params


def replenishment(on_hand, forecast, pending_quantity, params):
    forecast = np.asarray(forecast, dtype=float)
    L, R = int(params["lead_time_days"]), int(params["review_days"])
    if len(forecast) < L + R or not np.isfinite(forecast).all() or (forecast < 0).any():
        raise ValueError("Invalid or insufficient inventory forecast")
    safety = math.ceil(params["safety_days"] * forecast.mean())
    rop = math.ceil(forecast[:L].sum() + safety)
    order_up_to = math.ceil(forecast[:L + R].sum() + safety)
    ip = on_hand + pending_quantity
    trigger = on_hand < rop
    q = math.ceil(max(0, order_up_to - ip)) if trigger else 0
    if q > 0:
        q = max(q, int(params["moq"]))
    return {"SS": safety, "ROP": rop, "S": order_up_to, "IP": ip, "Q": q,
            "needs_replenishment": trigger, "on_hand": on_hand}


def consume(on_hand, sales):
    if on_hand < 0 or sales < 0:
        raise ValueError("Negative inventory or demand")
    fulfilled = min(on_hand, sales)
    return on_hand - fulfilled, fulfilled, sales - fulfilled


def project_depletion(on_hand, forecast, origin, receipts=()):
    if on_hand <= 0:
        return {"state": "already_empty", "days": None, "date": None}
    stock = float(on_hand)
    origin = pd.Timestamp(origin)
    for h, demand in enumerate(forecast, 1):
        day = origin + pd.Timedelta(days=h)
        stock += sum(r["quantity"] for r in receipts if pd.Timestamp(r["eta"]) == day)
        stock, _, _ = consume(stock, demand)
        if stock <= 1e-9:
            return {"state": "early" if h >= 7 else "urgent", "days": h, "date": day}
    return {"state": "no_depletion_within_horizon", "days": None, "date": None}


def item_matrix(sales, cfg):
    grouped = sales.groupby(["date"] + ITEM).quantity.sum().unstack(ITEM, fill_value=0)
    return grouped.reindex(pd.date_range(cfg["observation_start"], cfg["observation_end"]), fill_value=0).astype(float)


def allocation(matrix, forecasts, origin, cfg):
    """SKU shares only from history <= origin. Output preserves route totals."""
    origin = pd.Timestamp(origin)
    known = matrix.loc[:origin].sum().gt(0)
    result, issues = {}, []
    for route, group in forecasts.groupby(ROUTE, sort=True):
        keys = [key for key in matrix.columns if key[:2] == route and known[key]]
        if not keys:
            issues.append({**dict(zip(ROUTE, route)), "as_of_date": origin, "status": "missing_allocation_basis"}); continue
        totals = None
        for window in [cfg["inventory"]["allocation_window_days"], cfg["inventory"]["allocation_fallback_days"]]:
            totals = matrix.loc[origin - pd.Timedelta(days=window - 1):origin, keys].sum()
            if totals.sum() > 0:
                break
        if totals.sum() <= 0:
            issues.append({**dict(zip(ROUTE, route)), "as_of_date": origin, "status": "missing_allocation_basis"}); continue
        vector = group.sort_values("horizon_day").forecast_qty.to_numpy(dtype=float)
        if len(vector) != cfg["horizon"] or not np.isfinite(vector).all():
            raise ValueError("Incomplete route inventory forecast")
        weights = totals / totals.sum()
        for key in keys:
            result[key] = vector * weights[key]
        if not np.allclose(sum(result[key] for key in keys), vector, atol=cfg["numeric_tolerance"], rtol=0):
            raise ValueError("Allocation failed conservation")
    return result, issues


def initial_stock(matrix, origin, cfg):
    params = cfg["inventory"]
    history = matrix.loc[pd.Timestamp(origin) - pd.Timedelta(days=params["initial_window_days"] - 1):pd.Timestamp(origin)]
    return {key: math.ceil(params["initial_cover_days"] * value) for key, value in history.mean().items()
            if matrix.loc[:pd.Timestamp(origin), key].sum() > 0}


def declared_receipts(cfg, origin):
    if "initial_receipts" not in cfg["inventory"]:
        raise ValueError("Missing receipt declaration is not an empty receipt list")
    entries = []
    for row in cfg["inventory"]["initial_receipts"]:
        key = tuple(row[field] for field in ITEM)
        quantity = int(row["quantity"])
        if quantity <= 0 or pd.Timestamp(row["eta"]) <= pd.Timestamp(origin):
            raise ValueError("Invalid pending receipt declaration")
        if pd.Timestamp(row.get("ordered_at", origin)) > pd.Timestamp(origin):
            raise ValueError("Initial receipt was not known at origin")
        entries.append({"key": key, "quantity": quantity, "eta": pd.Timestamp(row["eta"]),
                        "actual_eta": pd.Timestamp(row["eta"]), "actual_quantity": quantity})
    return entries


def run_policy(matrix, forecast_table, cfg, scenario, progress=lambda message: None):
    first = pd.Timestamp(cfg["test_start"])
    end = pd.Timestamp(cfg["test_end"])
    stocks = initial_stock(matrix, first - pd.Timedelta(days=1), cfg)
    pending = declared_receipts(cfg, first - pd.Timedelta(days=1))
    by_origin = {date: group for date, group in forecast_table.groupby("as_of_date")}
    ledgers, recommendations, issues = [], [], []
    for day in pd.date_range(first, end):
        opening = stocks.copy()
        received = {}
        keep = []
        for receipt in pending:
            if receipt["actual_eta"] <= day:
                key = receipt["key"]
                received[key] = received.get(key, 0) + receipt["actual_quantity"]
            else:
                if receipt["eta"] <= day:
                    # Delay is only revealed when the promise becomes overdue.
                    receipt["eta"] = receipt["actual_eta"]
                keep.append(receipt)
        pending = keep
        keys_today = set(stocks) | set(received) | set(matrix.columns[matrix.loc[day].gt(0)])
        daily_entries = {}
        for key in sorted(keys_today):
            start = opening.get(key, 0)
            amount = received.get(key, 0)
            # Demand stress is an explicit integer scenario, never edits actual sales.
            observed = float(matrix.loc[day, key]) if key in matrix.columns else 0
            active_shock = True
            if "demand_start" in scenario:
                shock_start = pd.Timestamp(scenario["demand_start"])
                active_shock = shock_start <= day < shock_start + pd.Timedelta(days=scenario["demand_days"])
            multiplier = scenario["demand_multiplier"] if active_shock else 1.0
            demand = int(round(observed * multiplier))
            closing, fulfilled, shortage = consume(start + amount, demand)
            stocks[key] = closing
            entry = {**dict(zip(ITEM, key)), "date": day, "scenario_id": scenario["name"],
                     "opening": start, "receipts": amount, "historical_sales": observed,
                     "scenario_demand": demand, "fulfilled": fulfilled, "shortage": shortage,
                     "closing": closing, "is_simulated": True, "assumption_version": cfg["assumption_version"]}
            ledgers.append(entry); daily_entries[key] = entry
        if day not in by_origin:
            # Tail origins still need a full H forecast, not truncated test labels.
            raise ValueError("Missing full-horizon policy forecast at decision origin")
        details, allocation_issues = allocation(matrix, by_origin[day], day, cfg)
        issues.extend(allocation_issues)
        for key, vector in details.items():
            stocks.setdefault(key, 0)
            try:
                partner, params = partner_params(key[1], cfg)
            except ValueError as error:
                issues.append({**dict(zip(ITEM, key)), "as_of_date": day, "scenario_id": scenario["name"], "status": str(error)}); continue
            receipts_for_item = [r for r in pending if r["key"] == key]
            decision = replenishment(stocks[key], vector, sum(r["quantity"] for r in receipts_for_item), params)
            depletion = project_depletion(stocks[key], vector, day, receipts_for_item)
            row = {**dict(zip(ITEM, key)), **decision, "as_of_date": day, "partner_id": partner,
                   "scenario_id": scenario["name"], "depletion_state": depletion["state"],
                   "depletion_days": depletion["days"], "expected_depletion_date": depletion["date"],
                   "eta": day + pd.Timedelta(days=int(params["lead_time_days"])) if decision["Q"] else None,
                   "status": "incoming_covers_order" if decision["needs_replenishment"] and not decision["Q"] else "ok",
                   "is_simulated": True, "assumption_version": cfg["assumption_version"]}
            recommendations.append(row)
            if decision["Q"]:
                eta = row["eta"]
                pending.append({"key": key, "quantity": decision["Q"], "eta": eta,
                                "actual_eta": eta + pd.Timedelta(days=scenario["receipt_delay_days"]),
                                "actual_quantity": math.floor(decision["Q"] * scenario["receipt_fraction"])})
        if day.day == 1:
            progress(f"Inventory {scenario['name']} {day.date()}")
    ledger = pd.DataFrame(ledgers)
    assert np.allclose(ledger.closing, ledger.opening + ledger.receipts - ledger.fulfilled, rtol=0, atol=cfg["numeric_tolerance"])
    assert np.allclose(ledger.scenario_demand, ledger.fulfilled + ledger.shortage, rtol=0, atol=cfg["numeric_tolerance"])
    return ledger, pd.DataFrame(recommendations), pd.DataFrame(issues)


def replay_alerts(matrix, forecast_table, cfg):
    by_origin = {day: group for day, group in forecast_table.groupby("as_of_date")}
    records = []
    first = pd.Timestamp(cfg["test_start"]) - pd.Timedelta(days=1)
    end = pd.Timestamp(cfg["test_end"])
    for origin in pd.date_range(first, end, freq=f"{cfg['horizon']}D"):
        if origin + pd.Timedelta(days=cfg["horizon"]) > end:
            continue
        details, _ = allocation(matrix, by_origin[origin], origin, cfg)
        stocks = initial_stock(matrix, origin, cfg)
        receipts = declared_receipts(cfg, origin)
        for key, vector in details.items():
            stock = stocks.get(key, 0)
            projected = project_depletion(stock, vector, origin, [r for r in receipts if r["key"] == key])
            realized = matrix.loc[origin + pd.Timedelta(days=1):origin + pd.Timedelta(days=cfg["horizon"]), key].to_numpy()
            actual = project_depletion(stock, realized, origin, [r for r in receipts if r["key"] == key])
            pred_event = projected["days"] is not None
            actual_event = actual["days"] is not None
            event_id = hashlib.sha256((str(origin.date()) + "|" + "|".join(key)).encode()).hexdigest()[:20]
            records.append({**dict(zip(ITEM, key)), "as_of_date": origin, "event_id": event_id,
                            "scenario_id": "alert_replay_no_new_orders", "is_simulated": True,
                            "predicted_depletion_date": projected["date"], "actual_depletion_date": actual["date"],
                            "predicted_days": projected["days"], "actual_days": actual["days"],
                            "state": projected["state"], "tp": pred_event and actual_event,
                            "fp": pred_event and not actual_event, "fn": actual_event and not pred_event,
                            "already_empty": stock <= 0,
                            "reported_early": pred_event and actual_event and actual["days"] >= 7,
                            "late": pred_event and actual_event and actual["days"] < 7,
                            "day_error": abs(projected["days"] - actual["days"]) if pred_event and actual_event else np.nan})
    return pd.DataFrame(records)


def simulation_metrics(ledgers, alerts):
    rows = []
    for name, ledger in ledgers.groupby("scenario_id"):
        total = ledger.scenario_demand.sum()
        rows.append({"evaluation": "continuous_replenishment_policy", "scenario_id": name,
                     "demand": total, "shortage": ledger.shortage.sum(),
                     "fill_rate": ledger.fulfilled.sum() / total if total else np.nan,
                     "mean_closing_on_hand": ledger.groupby("date").closing.sum().mean(), "is_simulated": True})
    tp, fp, fn = alerts.tp.sum(), alerts.fp.sum(), alerts.fn.sum()
    rows.append({"evaluation": "independent_no_new_order_alert_replay", "scenario_id": "alert_replay_no_new_orders",
                 "tp": tp, "fp": fp, "fn": fn, "precision": tp / (tp+fp) if tp+fp else np.nan,
                 "recall": tp / (tp+fn) if tp+fn else np.nan,
                 "early_event_rate": alerts.reported_early.sum() / (tp+fn) if tp+fn else np.nan,
                 "late_alerts": alerts.late.sum(), "mean_day_error": alerts.day_error.mean(),
                 "n_item_windows": len(alerts), "existing_empty_excluded": alerts.already_empty.sum(), "is_simulated": True})
    return pd.DataFrame(rows)
