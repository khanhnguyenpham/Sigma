"""Forecast read models; all predictions are the verified published arrays."""

from datetime import timedelta
import numpy as np
import pandas as pd
from sigma_public.metrics import score
from .bundle import records
from .views import filter_rows
from .state import day, integer, PublicError


def forecasts(bundle, name, q):
    origin = str(day(q.get("as_of_date")))
    if origin not in bundle.origin_index:
        raise PublicError(
            "Mốc này không có dự báo trong gói công khai.", "insufficient_forecast"
        )
    if name == "routes":
        frame = bundle.frames["weekly"].copy()
        frame = frame[frame.as_of_date == origin]
        frame["warehouse_id"] = [
            bundle.route_ids[tuple(r)]
            for r in frame[["destination_country", "carrier"]].to_numpy()
        ]
        if q.get("warehouse_id"):
            frame = frame[frame.warehouse_id == integer(q["warehouse_id"], 1, 46)]
        if q.get("block"):
            frame = frame[frame.block == integer(q["block"], 1, 2)]
        return records(frame)
    if q.get("aggregate") != "route_day":
        raise PublicError(
            "Trực tuyến phục vụ ngày phân bổ theo tuyến/mặt hàng trong UI."
        )
    chosen = filter_rows(bundle.catalog_rows, q)
    chosen = [r for r in chosen if r["first_seen_date"] <= origin]
    rows = []
    by_route = {}
    for row in chosen:
        by_route.setdefault(row["warehouse_id"], []).append(row)
    for route, items in sorted(by_route.items()):
        info = items[0]
        vector = np.sum(
            [bundle.vector(origin, row["item_id"]) for row in items], axis=0
        )
        for h, qty in enumerate(vector, 1):
            target = str(day(origin) + timedelta(days=h))
            if q.get("item_id") or q.get("product_type"):
                actuals = [
                    bundle.item_actual.get((row["item_id"], target)) for row in items
                ]
                actual = (
                    sum(actuals)
                    if all(value is not None for value in actuals)
                    else None
                )
            else:
                actual = bundle.route_actual.get(
                    (info["destination_country"], info["carrier"], target)
                )
            rows.append(
                dict(
                    warehouse_id=route,
                    destination_country=info["destination_country"],
                    carrier=info["carrier"],
                    as_of_date=origin,
                    target_date=target,
                    horizon_day=h,
                    block=(h - 1) // 7 + 1,
                    forecast_qty=float(qty),
                    actual_qty=actual,
                    actual_available=actual is not None,
                    granularity="allocated_daily",
                )
            )
    return sorted(
        rows, key=lambda r: (r["as_of_date"], r["target_date"], r["warehouse_id"])
    )


def daily_metrics(bundle):
    if hasattr(bundle, "daily_scores"):
        return bundle.daily_scores
    result = []
    for (country, carrier), items in bundle.catalog.groupby(
        ["destination_country", "carrier"]
    ):
        vectors = bundle.cube[:, items.item_key.to_numpy(int), :].sum(axis=1)
        for split, start, end in [
            ("validation", "2025-07-01", "2025-09-30"),
            ("test", "2025-10-01", "2025-12-31"),
        ]:
            for block in [1, 2]:
                pairs = []
                for n, origin in enumerate(bundle.origins):
                    a = day(str(origin)) + timedelta(days=(block - 1) * 7 + 1)
                    b = a + timedelta(days=6)
                    if not start <= str(a) or not str(b) <= end:
                        continue
                    for h in range((block - 1) * 7, block * 7):
                        target = str(day(str(origin)) + timedelta(days=h + 1))
                        pairs.append(
                            dict(
                                target_date=target,
                                forecast_qty=float(vectors[n, h]),
                                actual_qty=bundle.route_actual.get(
                                    (country, carrier, target)
                                ),
                            )
                        )
                if pairs:
                    result.append(
                        dict(
                            destination_country=country,
                            carrier=carrier,
                            warehouse_id=bundle.route_ids[(country, carrier)],
                            block=block,
                            split=split,
                            cadence="daily_origins",
                            granularity="allocated_daily",
                            **score(pd.DataFrame(pairs)),
                        )
                    )
    bundle.daily_scores = result
    return result


def metrics(bundle, q):
    rows = (
        daily_metrics(bundle)
        if q.get("granularity") == "allocated_daily"
        else records(bundle.frames["weekly_metrics"])
    )
    for row in rows:
        row["warehouse_id"] = bundle.route_ids[
            (row["destination_country"], row["carrier"])
        ]
    for key in ["split", "cadence", "granularity"]:
        if q.get(key):
            rows = [row for row in rows if row.get(key) == q[key]]
    for key, maximum in [("block", 2), ("warehouse_id", 46)]:
        if q.get(key):
            rows = [row for row in rows if row.get(key) == integer(q[key], 1, maximum)]
    return rows
