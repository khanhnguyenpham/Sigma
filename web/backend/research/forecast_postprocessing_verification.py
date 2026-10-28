"""Independent F2 scalar reference; no postprocessor or application arithmetic imports."""

from collections import defaultdict
from datetime import date, timedelta
import json
import math
from pathlib import Path
from statistics import median

from core.hashes import digest
from web.backend.research.inventory_alert_opportunity_verification import equal, read, score_events


PROTOCOL = Path(__file__).resolve().parents[1] / "configs/forecast-postprocessing-v1.json"
PROTOCOL_SHA256 = "a4259ef7fbd1cfc7d484efdf757102a40298fca7a84c3f7a7d91ac3d18ff2410"


def require(condition):
    if not condition:
        raise ValueError("Independent F2 verification failed")


def protocol():
    result = read(PROTOCOL)
    require(digest(result) == PROTOCOL_SHA256)
    return result


def route(item):
    return json.dumps([item["destination_country"], item["carrier"]], ensure_ascii=False, separators=(",", ":"))


def items_at(catalog, origin):
    result = sorted(catalog, key=lambda r: r["item_id"])
    require(bool(result) and len({i["item_id"] for i in result}) == len(result))
    require(all(type(i["item_id"]) is int and date.fromisoformat(i["first_seen_date"]) <= origin for i in result))
    return result


def history(daily, items, start, end):
    rows = [r for r in daily if str(start) <= r["date"] <= str(end)]
    values = {(r["date"], r["item_id"]): r for r in rows}
    days = [start + timedelta(days=n) for n in range((end - start).days + 1)]
    require(len(values) == len(rows) and set(values) == {(str(d), i["item_id"]) for d in days for i in items})
    require(all(type(r["item_id"]) is int and r["actual_available"] is True and type(r["quantity"]) is int and r["quantity"] >= 0 for r in rows))
    return {(d, i): r["quantity"] for (d, i), r in values.items()}


def forecast(forecasts, items, origin):
    rows = [r for r in forecasts if r["as_of_date"] == str(origin)]
    values = {r["item_id"]: list(r["forecast"]) for r in rows}
    require(all(type(r["item_id"]) is int for r in rows) and len(rows) == len(values) == len(items) and set(values) == {i["item_id"] for i in items})
    require(all(len(v) == 14 and all(type(x) in (float, int) and math.isfinite(x) and x >= 0 for x in v) for v in values.values()))
    return values


def quantile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (position - low) * (values[high] - values[low])


def calibration_reference(catalog, daily, forecasts):
    p = protocol()
    c = p["calibration"]
    start, finish, cutoff = (date.fromisoformat(c[k]) for k in ("origin_start", "origin_end", "cutoff"))
    items = items_at(catalog, start)
    labels = history(daily, items, date.fromisoformat(c["label_start"]), cutoff)
    origins = [start + timedelta(days=n) for n in range((finish - start).days + 1)]
    values = {o: forecast(forecasts, items, o) for o in origins}
    routes = sorted({route(i) for i in items})
    item_routes = {i["item_id"]: route(i) for i in items}
    quantities = defaultdict(list)
    for (d, i), q in labels.items():
        quantities[i].append(q)
    means = {r: math.fsum(q for i, values in quantities.items() if item_routes[i] == r for q in values) / 28 for r in routes}
    threshold = median(means.values())
    levels = {r: "low" if means[r] <= threshold else "high" for r in routes}
    scales = {str(i): max(math.fsum(values) / 28, 1.0) for i, values in quantities.items()}
    pairs = []
    errors = [[] for _ in range(14)]
    for o in origins:
        for item in items:
            i = item["item_id"]
            observed, predicted = [], []
            for h in range(1, 15):
                y, f = labels[(str(o + timedelta(days=h)), i)], values[o][i][h - 1]
                observed.append(y)
                predicted.append(f)
                pairs.append((route(item), (h - 1) // 7, y, f))
                errors[h - 1].append((math.fsum(observed) - math.fsum(predicted)) / scales[str(i)])
    def ratio(rows, fallback):
        rows = list(rows)
        denominator = math.fsum(r[3] for r in rows)
        return math.fsum(r[2] for r in rows) / denominator if denominator else fallback
    global_factor = ratio(pairs, 1.0)
    blocks = []
    level_blocks = {level: [] for level in ("low", "high")}
    for b in range(2):
        group = [r for r in pairs if r[1] == b]
        blocks.append((ratio(group, global_factor) + global_factor) / 2)
        for level in level_blocks:
            group = [r for r in pairs if r[1] == b and levels[r[0]] == level]
            denominator = math.fsum(r[3] for r in group)
            level_blocks[level].append((ratio(group, global_factor) + global_factor) / 2 if denominator else blocks[b])
    source = dict(catalog=[{k: r[k] for k in ("item_id", "destination_country", "carrier", "first_seen_date")} for r in items],
                  daily=sorted([{k: r[k] for k in ("date", "item_id", "quantity", "actual_available")}
                                for r in daily if c["label_start"] <= r["date"] <= c["cutoff"]], key=lambda r: (r["date"], r["item_id"])),
                  forecasts=sorted([{k: r[k] for k in ("as_of_date", "item_id", "forecast")}
                                    for r in forecasts if c["origin_start"] <= r["as_of_date"] <= c["origin_end"]], key=lambda r: (r["as_of_date"], r["item_id"])))
    return dict(protocol_sha256=PROTOCOL_SHA256, cutoff=c["cutoff"], effective_from=p["effective_from"],
                calibration_input_sha256=digest(source), global_factor=global_factor, block_factors=blocks,
                level_block_factors=level_blocks, route_levels=levels, scales=scales,
                risk_quantiles={str(q): [quantile(v, q) for v in errors] for q in (.75, .90)})


def verify_parameters(catalog, daily, forecasts, parameters):
    require(parameters.get("sha256") == digest({k: v for k, v in parameters.items() if k != "sha256"}))
    expected = calibration_reference(catalog, daily, forecasts)
    equal({k: v for k, v in parameters.items() if k != "sha256"}, expected)
    return expected


def forecast_reference(candidate_id, origin, catalog, daily, forecasts, parameters=None):
    p = protocol()
    spec = next((r for r in p["candidates"] if r["id"] == candidate_id), None)
    require(spec is not None)
    origin = date.fromisoformat(str(origin))
    items = items_at(catalog, origin)
    original = forecast(forecasts, items, origin)
    result = {i: list(v) for i, v in original.items()}
    family = spec["family"]
    if origin < date.fromisoformat(p["effective_from"]) or family == "identity":
        return result
    if family == "stress":
        return {i: [x * spec["alpha"] for x in v] for i, v in result.items()}
    if family.startswith("bias_"):
        for item in items:
            factors = [parameters["global_factor"]] * 2
            if family == "bias_block":
                factors = parameters["block_factors"]
            elif family == "bias_level_block":
                factors = parameters["level_block_factors"][parameters["route_levels"][route(item)]]
            result[item["item_id"]] = [x * factors[h // 7] for h, x in enumerate(original[item["item_id"]])]
    elif family == "risk":
        for item in items:
            i = item["item_id"]
            last = 0.0
            for h in range(14):
                bound = math.fsum(original[i][:h + 1]) + parameters["scales"][str(i)] * max(parameters["risk_quantiles"][str(spec["quantile"])][h], 0)
                current = max(last, bound)
                result[i][h] = current - last
                last = current
    else:
        window = spec["window_days"]
        first = origin - timedelta(days=window - 1)
        past = history(daily, items, first, origin)
        for r in sorted({route(item) for item in items}):
            members = [i["item_id"] for i in items if route(i) == r]
            days = [first + timedelta(days=n) for n in range(window)]
            totals = {i: math.fsum(past[(str(d), i)] for d in days) for i in members}
            total = math.fsum(totals.values())
            if total == 0:
                continue
            if family == "item_share":
                for h in range(14):
                    amount = math.fsum(original[i][h] for i in members)
                    for i in members:
                        result[i][h] = amount * (original[i][h] / amount + totals[i] / total) / 2 if amount else original[i][h]
            else:
                weekday = [math.fsum(past[(str(d), i)] for d in days if d.weekday() == w for i in members) / total for w in range(7)]
                for i in members:
                    for h in range(14):
                        block = h // 7 * 7
                        weekly = math.fsum(original[i][block:block + 7])
                        result[i][h] = (original[i][h] + weekly * weekday[(origin + timedelta(days=h + 1)).weekday()]) / 2
    require(all(math.isfinite(x) and x >= 0 for v in result.values() for x in v))
    return result


def projection_reference(origin, on_hand, demands, receipts):
    stock, first, rows = float(on_hand), None, []
    for h in range(14):
        target = origin + timedelta(days=h + 1)
        stock = stock + receipts.get(target, 0) - demands[h]
        if stock < 0:
            stock = 0.0
        if first is None and stock == 0:
            first = target
        rows.append(dict(date=str(target), closing_forecast=stock, receipts_qty=receipts.get(target, 0)))
    if on_hand == 0:
        state, first, lead = "already_depleted", origin, 0
    else:
        lead = (first - origin).days if first else None
        state = "not_within_horizon" if lead is None else "early" if lead >= 7 else "urgent"
    return dict(state=state, predicted_depletion_date=str(first) if first else None, lead_days=lead, projection=rows)


def verify_candidate(candidate_id, snapshot, baseline, parameters, actual, calibration_inputs=None):
    before = digest(dict(snapshot=snapshot, baseline=baseline, parameters=parameters))
    require(actual["candidate_id"] == candidate_id and actual["fixed_input_sha256"] == digest(baseline))
    if parameters is not None:
        require(calibration_inputs is not None)
        expected_parameters = verify_parameters(calibration_inputs["catalog"], calibration_inputs["daily"],
                                                calibration_inputs["forecasts"], parameters)
    else:
        expected_parameters = None
    forecasts, projections, alarms = [], [], []
    values = {}
    for row in sorted(baseline["ledger"], key=lambda r: r["date"]):
        day = row["date"]
        origin = date.fromisoformat(day)
        if day not in values:
            values[day] = forecast_reference(candidate_id, day, snapshot["catalog"], snapshot["daily"], snapshot["forecasts"], expected_parameters)
        forecasts.append(dict(as_of_date=day, item_id=row["item_id"], forecast=values[day][row["item_id"]]))
    equal(actual["forecasts"], forecasts)
    # Verify projection from the serialized forecast after checking its independent
    # value. This avoids changing an exact-zero event because of summation order.
    for row, exported in zip(sorted(baseline["ledger"], key=lambda r: r["date"]), actual["forecasts"], strict=True):
        day = row["date"]
        origin = date.fromisoformat(day)
        vector = exported["forecast"]
        receipts = defaultdict(int)
        for order in baseline["orders"]:
            eta = date.fromisoformat(order["eta"])
            if order["item_id"] == row["item_id"] and origin < eta <= origin + timedelta(days=14) and (order["is_initial"] or order["ordered_on"] < day):
                receipts[eta] += order["ordered_qty"]
        path = projection_reference(origin, row["closing_qty"], vector, receipts)
        projections.append(dict(date=day, item_id=row["item_id"], **path))
        alarms.append(dict(date=day, item_id=row["item_id"], origin_on_hand=row["closing_qty"],
                           predicted_depletion_date=path["predicted_depletion_date"] if path["state"] != "already_depleted" else None))
    period = snapshot["period"]
    cases, metrics = score_events(dict(baseline, alarms=alarms), date.fromisoformat(period["score_start"]), date.fromisoformat(period["end"]))
    kind = next(c["kind"] for c in protocol()["candidates"] if c["id"] == candidate_id)
    expected = dict(candidate_id=candidate_id, kind=kind, fixed_input_sha256=digest(baseline), forecasts=actual["forecasts"],
                    projections=projections, alarms=alarms, cases=cases, metrics=metrics)
    equal(actual, expected)
    require(before == digest(dict(snapshot=snapshot, baseline=baseline, parameters=parameters)))
    return dict(status="verified_synthetic_candidate", candidate_id=candidate_id, projection_paths=len(projections))
