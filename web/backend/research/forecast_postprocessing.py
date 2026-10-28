"""F2 pure research kernels. The CLI checks the lock; it cannot run real candidates."""

import argparse
from collections import defaultdict
from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np

from core.hashes import digest
from web.backend.research import inventory_alert_opportunity_audit as audit
from web.backend.research import inventory_forecast_identity as identity


PROTOCOL = Path(__file__).resolve().parents[1] / "configs/forecast-postprocessing-v1.json"
PROTOCOL_SHA256 = "a4259ef7fbd1cfc7d484efdf757102a40298fca7a84c3f7a7d91ac3d18ff2410"


def load_protocol():
    protocol = audit.read(PROTOCOL)
    identity.require(digest(protocol) == PROTOCOL_SHA256, "F2 protocol differs")
    return protocol


def route_key(item):
    return json.dumps([item["destination_country"], item["carrier"]], ensure_ascii=False, separators=(",", ":"))


def catalog_at(catalog, origin):
    items = sorted(catalog, key=lambda r: r["item_id"])
    identity.require(bool(items) and len({r["item_id"] for r in items}) == len(items), "Invalid catalog")
    identity.require(all(type(r["item_id"]) is int and date.fromisoformat(r["first_seen_date"]) <= origin
                         for r in items), "Unknown item at origin")
    return items


def observed(daily, items, start, end):
    selected = [r for r in daily if str(start) <= r["date"] <= str(end)]
    indexed = {(r["date"], r["item_id"]): r for r in selected}
    days = [start + timedelta(days=n) for n in range((end - start).days + 1)]
    expected = {(str(d), r["item_id"]) for d in days for r in items}
    identity.require(len(indexed) == len(selected) and set(indexed) == expected, "Missing/duplicate observed history")
    identity.require(all(type(r["item_id"]) is int and r["actual_available"] is True and type(r["quantity"]) is int and r["quantity"] >= 0
                         for r in selected), "Invalid/missing actual history")
    return np.array([[indexed[(str(d), r["item_id"])]["quantity"] for r in items] for d in days], dtype=float)


def forecast_at(forecasts, items, origin):
    selected = [r for r in forecasts if r["as_of_date"] == str(origin)]
    indexed = {r["item_id"]: r["forecast"] for r in selected}
    identity.require(all(type(r["item_id"]) is int for r in selected) and len(indexed) == len(selected) == len(items)
                     and set(indexed) == {r["item_id"] for r in items}, "Forecast cohort/coverage differs")
    identity.require(all(isinstance(v, list) and len(v) == 14
                         and all(type(q) in (int, float) and np.isfinite(q) and q >= 0 for q in v)
                         for v in indexed.values()), "Invalid H14 forecast")
    return np.array([indexed[r["item_id"]] for r in items], dtype=float)


def calibration_source(catalog, daily, forecasts):
    """Select only mature warmup labels; unused future values are never inspected."""
    c = load_protocol()["calibration"]
    start, finish, cutoff = (date.fromisoformat(c[k]) for k in ("origin_start", "origin_end", "cutoff"))
    items = catalog_at(catalog, start)
    labels = observed(daily, items, date.fromisoformat(c["label_start"]), cutoff)
    origins = [start + timedelta(days=n) for n in range((finish - start).days + 1)]
    f = np.array([forecast_at(forecasts, items, o) for o in origins])
    actual = np.array([labels[n:n + 14].T for n in range(len(origins))])
    source = dict(catalog=[{k: r[k] for k in ("item_id", "destination_country", "carrier", "first_seen_date")} for r in items],
                  daily=[{k: r[k] for k in ("date", "item_id", "quantity", "actual_available")}
                         for r in sorted((r for r in daily if c["label_start"] <= r["date"] <= c["cutoff"]),
                                         key=lambda r: (r["date"], r["item_id"]))],
                  forecasts=[{k: r[k] for k in ("as_of_date", "item_id", "forecast")}
                             for r in sorted((r for r in forecasts if c["origin_start"] <= r["as_of_date"] <= c["origin_end"]),
                                             key=lambda r: (r["as_of_date"], r["item_id"]))])
    return items, labels, f, actual, digest(source)


def calibrate(catalog, daily, forecasts):
    p = load_protocol()
    items, labels, f, actual, source_hash = calibration_source(catalog, daily, forecasts)
    routes = sorted({route_key(i) for i in items})
    route_indices = {r: [n for n, item in enumerate(items) if route_key(item) == r] for r in routes}
    means = {r: float(labels[:, idx].sum() / 28) for r, idx in route_indices.items()}
    median = float(np.median(list(means.values())))
    levels = {r: "low" if means[r] <= median else "high" for r in routes}
    global_factor = float(actual.sum() / f.sum()) if f.sum() else 1.0
    blocks = []
    level_blocks = {level: [] for level in ("low", "high")}
    for b in range(2):
        segment = slice(b * 7, (b + 1) * 7)
        denominator = f[:, :, segment].sum()
        factor = (float(actual[:, :, segment].sum() / denominator) + global_factor) / 2 if denominator else global_factor
        blocks.append(factor)
        for level in level_blocks:
            idx = [n for n, item in enumerate(items) if levels[route_key(item)] == level]
            den = f[:, idx, segment].sum()
            factor = (float(actual[:, idx, segment].sum() / den) + global_factor) / 2 if den else blocks[b]
            level_blocks[level].append(factor)
    scales = np.maximum(labels.mean(axis=0), 1.0)
    errors = (actual.cumsum(axis=2) - f.cumsum(axis=2)) / scales[None, :, None]
    risks = {str(q): np.quantile(errors.reshape(-1, 14), q, axis=0, method="linear").tolist() for q in (.75, .90)}
    result = dict(protocol_sha256=PROTOCOL_SHA256, cutoff=p["calibration"]["cutoff"], effective_from=p["effective_from"],
                  calibration_input_sha256=source_hash, global_factor=global_factor, block_factors=blocks,
                  level_block_factors=level_blocks, route_levels=levels,
                  scales={str(i["item_id"]): float(s) for i, s in zip(items, scales, strict=True)}, risk_quantiles=risks)
    result["sha256"] = digest(result)
    return result


def check_parameters(parameters):
    p = load_protocol()
    identity.require(isinstance(parameters, dict) and parameters.get("protocol_sha256") == PROTOCOL_SHA256
                     and parameters.get("cutoff") == p["calibration"]["cutoff"]
                     and parameters.get("effective_from") == p["effective_from"], "Parameter lock differs")
    identity.require(parameters.get("sha256") == digest({k: v for k, v in parameters.items() if k != "sha256"}),
                     "Parameter checksum differs")


def transform(candidate_id, origin, catalog, daily, forecasts, parameters=None):
    """No ledger, event dates or opportunity flags are available to this function."""
    p = load_protocol()
    specification = next((c for c in p["candidates"] if c["id"] == candidate_id), None)
    identity.require(specification is not None, "Unknown candidate")
    origin = date.fromisoformat(str(origin))
    items = catalog_at(catalog, origin)
    base = forecast_at(forecasts, items, origin)
    output = base.copy()
    family = specification["family"]
    if origin < date.fromisoformat(p["effective_from"]) or family == "identity":
        pass
    elif family == "stress":
        output *= specification["alpha"]
    elif family.startswith("bias_") or family == "risk":
        check_parameters(parameters)
        if family.startswith("bias_"):
            for n, item in enumerate(items):
                factors = [parameters["global_factor"]] * 2
                if family == "bias_block":
                    factors = parameters["block_factors"]
                elif family == "bias_level_block":
                    factors = parameters["level_block_factors"][parameters["route_levels"][route_key(item)]]
                output[n] *= np.repeat(factors, 7)
        else:
            scale = np.array([parameters["scales"][str(i["item_id"])] for i in items])
            quantile = np.maximum(parameters["risk_quantiles"][str(specification["quantile"])], 0)
            cumulative = np.maximum.accumulate(base.cumsum(axis=1) + scale[:, None] * quantile, axis=1)
            output = np.diff(cumulative, axis=1, prepend=0)
    else:
        window = specification["window_days"]
        history = observed(daily, items, origin - timedelta(days=window - 1), origin)
        for route in sorted({route_key(i) for i in items}):
            idx = [n for n, item in enumerate(items) if route_key(item) == route]
            counts = history[:, idx].sum(axis=0)
            if counts.sum() == 0:
                continue
            if family == "item_share":
                totals = base[idx].sum(axis=0)
                output[idx] = .5 * base[idx] + .5 * counts[:, None] / counts.sum() * totals
                identity.require(np.allclose(output[idx].sum(axis=0), totals, rtol=0, atol=1e-8), "Route/day total changed")
            else:
                weekdays = np.zeros(7)
                for n, amount in enumerate(history[:, idx].sum(axis=1)):
                    day = origin - timedelta(days=window - 1 - n)
                    weekdays[day.weekday()] += amount
                weekdays /= weekdays.sum()
                for b in range(2):
                    segment = slice(b * 7, (b + 1) * 7)
                    totals = base[idx, segment].sum(axis=1)
                    weights = np.array([weekdays[(origin + timedelta(days=h)).weekday()] for h in range(b * 7 + 1, b * 7 + 8)])
                    output[idx, segment] = .5 * base[idx, segment] + .5 * totals[:, None] * weights
                    identity.require(np.allclose(output[idx, segment].sum(axis=1), totals, rtol=0, atol=1e-8), "Item/week total changed")
    identity.require(np.isfinite(output).all() and (output >= 0).all(), "Invalid candidate forecast")
    return {item["item_id"]: output[n].tolist() for n, item in enumerate(items)}


def evaluate(candidate_id, snapshot, baseline, parameters=None):
    """In-memory evaluator for synthetic checks; no native CLI or output writer."""
    identity.coverage(snapshot, baseline)
    before = digest(dict(snapshot=snapshot, baseline=baseline, parameters=parameters))
    by_day = defaultdict(list)
    for row in baseline["ledger"]:
        by_day[row["date"]].append(row)
    orders = defaultdict(list)
    for order in baseline["orders"]:
        orders[order["item_id"]].append(order)
    forecasts, projections, alarms = [], [], []
    for day in sorted(by_day):
        values = transform(candidate_id, day, snapshot["catalog"], snapshot["daily"], snapshot["forecasts"], parameters)
        for row in by_day[day]:
            vector = values[row["item_id"]]
            origin = date.fromisoformat(day)
            path = identity.project(origin, row["closing_qty"], vector, identity.known_receipts(orders[row["item_id"]], origin))
            path["predicted_depletion_date"] = str(path["predicted_depletion_date"]) if path["predicted_depletion_date"] else None
            forecasts.append(dict(as_of_date=day, item_id=row["item_id"], forecast=vector))
            projections.append(dict(date=day, item_id=row["item_id"], **path))
            alarms.append(dict(date=day, item_id=row["item_id"], origin_on_hand=row["closing_qty"],
                               predicted_depletion_date=path["predicted_depletion_date"] if path["state"] != "already_depleted" else None))
    period = snapshot["period"]
    cases, metrics = audit.score(dict(baseline, alarms=alarms), date.fromisoformat(period["score_start"]), date.fromisoformat(period["end"]))
    identity.require(before == digest(dict(snapshot=snapshot, baseline=baseline, parameters=parameters)), "Frozen inputs mutated")
    kind = next(c["kind"] for c in load_protocol()["candidates"] if c["id"] == candidate_id)
    return dict(candidate_id=candidate_id, kind=kind, fixed_input_sha256=digest(baseline), forecasts=forecasts,
                projections=projections, alarms=alarms, cases=cases, metrics=metrics)


def select_validation(summaries):
    """Locked representative rule; selection is not executed on real data in F2."""
    p = load_protocol()
    order = {c["id"]: n for n, c in enumerate(p["candidates"])}
    identity.require(len(summaries) == len(order) and {r["candidate_id"] for r in summaries} == set(order), "Incomplete candidate matrix")
    target = p["evaluation"]["validation_target"]
    identity.require(all(r["metrics"]["event_denominator"] == target["event_denominator"] for r in summaries), "Validation denominator changed")
    identity.require(all(type(r["valid"]) is bool and type(r["alarm_item_days"]) is int and r["alarm_item_days"] >= 0
                         and type(r["metrics"]["early_numerator"]) is int
                         and 0 <= r["metrics"]["early_numerator"] <= target["event_denominator"]
                         and (r["metrics"]["precision"] is None or type(r["metrics"]["precision"]) in (int, float)
                              and np.isfinite(r["metrics"]["precision"]) and 0 <= r["metrics"]["precision"] <= 1)
                         for r in summaries), "Invalid selection summary")
    eligible = [r for r in summaries if r["valid"] is True and r["metrics"]["early_numerator"] >= target["early_numerator"]
                and r["metrics"]["precision"] is not None]
    if not eligible:
        return None
    return min(eligible, key=lambda r: (-r["metrics"]["precision"], r["alarm_item_days"], order[r["candidate_id"]]))["candidate_id"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-protocol", action="store_true", required=True)
    parser.parse_args(argv)
    p = load_protocol()
    print(json.dumps(dict(status="locked", protocol_sha256=PROTOCOL_SHA256, candidates=[c["id"] for c in p["candidates"]], real_candidate_runs=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
