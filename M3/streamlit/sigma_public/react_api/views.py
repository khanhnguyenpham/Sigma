"""Read models over the public release and immutable per-session plan snapshots."""

from copy import deepcopy
import json
from .bundle import records, clean
from .state import PublicError, day, integer


def run_for(bundle, state, key):
    row = next((r for r in state["runs"] + bundle.runs if r["id"] == key), None)
    if not row:
        raise PublicError(
            "Không tìm thấy phương án trong bộ công khai/phiên này.", "not_found", 404
        )
    return row


def context(bundle, run):
    return {
        **{
            k: run.get(k)
            for k in [
                "id",
                "kind",
                "status",
                "as_of_date",
                "observation_end",
                "source_import_run_id",
                "forecast_run_id",
                "scenario_id",
                "config_version",
                "target_version",
                "assumption_version",
            ]
        },
        "run_id": run["id"],
        "is_simulated": run["kind"] != "forecast",
        "release_version": bundle.meta["version"],
        "source_sha256": bundle.meta["source_sha256"],
        "persistence": "current_session_only",
        "test_independent": False,
    }


def paginate(rows, q, ctx=None):
    page = integer(q.get("page", "1"), 1, 100000)
    size = integer(q.get("page_size", "50"), 1, 100)
    start = (page - 1) * size
    return clean(
        dict(
            items=rows[start : start + size],
            total=len(rows),
            page=page,
            page_size=size,
            context=ctx or {},
        )
    )


def filter_rows(rows, q):
    result = rows
    for field in ["warehouse_id", "item_id", "supplier_id"]:
        if q.get(field):
            number = integer(q[field], 1, 1000000)
            result = [r for r in result if r.get(field) == number]
    if q.get("product_type"):
        if q["product_type"] not in ["eSIM", "physical_SIM"]:
            raise PublicError("Loại sản phẩm không hợp lệ.")
        result = [r for r in result if r.get("product_type") == q["product_type"]]
    return result


def raw_rows(bundle, state, run, name):
    if run["id"] in state["plans"]:
        return deepcopy(state["plans"][run["id"]][name])
    rows = records(bundle.frame(name, run["id"]))
    for row in rows:
        row["policy_version"] = None
        if name == "alerts":
            raw = row.pop("projection_json", None)
            row["explanation"] = (
                {"projection": json.loads(raw)} if isinstance(raw, str) and raw else {}
            )
    return rows


def dataset(bundle, state, run, name, q):
    if run["kind"] not in {"stock_projection", "policy_replay", "alert_replay"}:
        raise PublicError("Kế hoạch chưa có dữ liệu tồn kho.", "parent_mismatch", 409)
    rows = filter_rows(raw_rows(bundle, state, run, name), q)
    date_field = {
        "inventory": "date",
        "alerts": "as_of_date",
        "receipts": "ordered_on",
    }[name]
    if q.get("date_from"):
        start = str(day(q["date_from"]))
        rows = [r for r in rows if r[date_field] >= start]
    if q.get("date_to"):
        end = str(day(q["date_to"]))
        rows = [r for r in rows if r[date_field] <= end]
    if q.get("as_of_date") and name == "alerts":
        origin = str(day(q["as_of_date"]))
        rows = [r for r in rows if r["as_of_date"] == origin]
    status = q.get("state")
    if status:
        if name == "alerts":
            rows = [r for r in rows if r["state"] == status]
        elif name == "inventory":
            rows = [
                r
                for r in rows
                if r["needs_replenishment"]
                and (
                    r["recommended_qty"] == 0
                    if status == "pending_covers"
                    else r["recommended_qty"] > 0
                )
            ]
        else:
            raise PublicError("Không hỗ trợ lọc trạng thái này.")
    return sorted(rows, key=lambda r: (r[date_field], r["item_id"], r["id"]))


def operational(bundle, state, run, q, purchasing=False):
    if run["kind"] not in {"stock_projection", "policy_replay", "alert_replay"}:
        raise PublicError("Chọn kế hoạch tồn kho tương thích.", "parent_mismatch", 409)
    origin = str(day(q.get("as_of_date")))
    iv = dataset(
        bundle,
        state,
        run,
        "inventory",
        {**q, "date_from": origin, "date_to": origin, "state": None},
    )
    signals = dataset(
        bundle, state, run, "alerts", {**q, "as_of_date": origin, "state": None}
    )
    lots = filter_rows(raw_rows(bundle, state, run, "receipts"), q)
    recorded = (
        run["as_of_date"] if run["kind"] == "stock_projection" else run["period_end"]
    )
    known = min(origin, recorded)
    words = q.get("search", "").casefold().split()
    if len(q.get("search", "")) > 80:
        raise PublicError("Tìm kiếm tối đa 80 ký tự.")

    def matches(row):
        text = " ".join(
            str(row.get(k, ""))
            for k in ["sku", "carrier", "destination_country", "product_type"]
        ).casefold()
        return all(word in text for word in words)

    iv = [r for r in iv if matches(r)]
    history = []
    for row in lots:
        if row["ordered_on"] > known or not matches(row):
            continue
        row["status"] = (
            "received" if row["eta"] <= known and row["received_qty"] > 0 else "ordered"
        )
        if row["status"] == "ordered":
            row["received_qty"] = 0
        history.append(row)
    incoming = [r for r in history if r["eta"] > known]
    low = [r for r in iv if r["needs_replenishment"]]
    action = sorted(
        [r for r in low if r["recommended_qty"] > 0],
        key=lambda r: (-r["recommended_qty"], r["item_id"]),
    )
    urgent = {
        r["item_id"]
        for r in signals
        if r["alert_type"] == "depletion"
        and r["state"] in ["urgent", "already_depleted"]
    }
    ctx = {**context(bundle, run), "view_date": origin, "known_orders_through": known}
    if purchasing:
        view = q.get("view", "recommendations")
        sort = q.get("sort", "quantity_desc")
        if view not in ["recommendations", "incoming", "history"]:
            raise PublicError("Danh sách không hợp lệ.")
        rows = {"recommendations": action, "incoming": incoming, "history": history}[
            view
        ]
        qty = "recommended_qty" if view == "recommendations" else "ordered_qty"
        eta = "eta_if_ordered" if view == "recommendations" else "eta"
        if sort == "eta_asc":
            rows = sorted(
                rows,
                key=lambda r: (
                    r.get(eta) is None,
                    str(r.get(eta)),
                    r["item_id"],
                    r["id"],
                ),
            )
        elif sort == "ordered_desc" and view != "recommendations":
            rows = sorted(rows, key=lambda r: (r["ordered_on"], r["id"]), reverse=True)
        elif sort in ["quantity_desc", "quantity_asc"]:
            rows = sorted(
                rows,
                key=lambda r: (
                    (-1 if sort == "quantity_desc" else 1) * r[qty],
                    r["item_id"],
                    r["id"],
                ),
            )
        else:
            raise PublicError("Cách sắp xếp không hợp lệ.")
        summary = dict(
            inventory_available=bool(iv),
            recommended_items=len(action),
            recommended_units=sum(r["recommended_qty"] for r in action),
            incoming_lots=len(incoming),
            pending_units=sum(r["ordered_qty"] for r in incoming),
            historical_lots=len(history),
        )
        return dict(
            context={**ctx, "view": view, "search": q.get("search", ""), "sort": sort},
            summary=summary,
            items=rows,
        )
    routes = {}
    for row in iv:
        route = (row["destination_country"], row["carrier"])
        routes[route] = routes.get(route, 0) + row["closing_qty"]
    stock = [
        dict(destination_country=key[0], carrier=key[1], closing_qty=value)
        for key, value in sorted(routes.items(), key=lambda pair: (-pair[1], pair[0]))
    ]
    summary = dict(
        inventory_available=bool(iv),
        item_count=len(iv),
        on_hand_units=sum(r["closing_qty"] for r in iv) if iv else None,
        low_stock_items=len(low) if iv else None,
        replenish_items=len(action) if iv else None,
        recommended_units=sum(r["recommended_qty"] for r in action) if iv else None,
        incoming_lots=len(incoming),
        pending_units=sum(r["ordered_qty"] for r in incoming),
        urgent_items=len(urgent),
        healthy_items=sum(not r["needs_replenishment"] for r in iv),
        route_count=len(routes),
    )
    return dict(
        context=ctx,
        summary=summary,
        attention=action[:6],
        incoming=sorted(incoming, key=lambda r: (r["eta"], r["item_id"]))[:5],
        route_stock=stock[:8],
    )


def monthly(bundle, run, name, q):
    if name == "monthly-summary":
        metric = bundle.frames["monthly_metrics"]
        top = metric[
            (metric.split == "test")
            & (metric.cadence == "daily_origins")
            & metric.is_top10
        ]
        valid = top[
            (top.n_positive_pairs > 0)
            & (top.coverage == 1)
            & (top.mape_positive_pct <= 20)
        ]
        baseline = [
            dict(
                model=key,
                mean_mape_positive_pct=g.mape_positive_pct.mean(),
                routes_below_20_pct=int((g.mape_positive_pct <= 20).sum()),
            )
            for key, g in bundle.frames["baselines"].groupby("model", sort=False)
        ]
        summary = dict(
            expected_top_routes=10,
            available_top_routes=len(top),
            routes_below_20_pct=len(valid),
            meets_r05=len(top) == 10 and len(valid) == 10,
            mean_mape_positive_pct=top.mape_positive_pct.mean(),
            minimum_coverage=top.coverage.min(),
            pairs_per_route=int(top.n_scored_pairs.min()),
            baselines=baseline,
        )
        return dict(
            context={
                **context(bundle, run),
                "benchmark_package_id": bundle.meta["benchmark_package_id"],
                "benchmark_run_id": "sigma_aggregate_focus_20261018",
                "acceptance_version": bundle.meta["acceptance"]["version"],
            },
            summary=summary,
        )
    frame = bundle.frames[
        "monthly_forecasts" if name == "monthly-forecasts" else "monthly_metrics"
    ].copy()
    frame["warehouse_id"] = [
        bundle.route_ids[tuple(r)]
        for r in frame[["destination_country", "carrier"]].to_numpy()
    ]
    if q.get("warehouse_id"):
        frame = frame[frame.warehouse_id == integer(q["warehouse_id"], 1, 46)]
    if q.get("top10_only", "true") == "true":
        frame = frame[frame.is_top10]
    if q.get("split"):
        frame = frame[frame.split == q["split"]]
    if name == "monthly-forecasts" and q.get("as_of_date"):
        frame = frame[frame.as_of_date == str(day(q["as_of_date"]))]
    if name == "monthly-metrics":
        frame = frame[frame.cadence == q.get("cadence", "daily_origins")]
    return dict(items=records(frame), context=context(bundle, run))
