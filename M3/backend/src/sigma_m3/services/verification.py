
"""Independent reconciliation of persisted forecasts, ledgers and replay denominators."""
from sigma_m3.services.runs import source_data_id
import hashlib, json, math
import numpy as np
import pandas as pd
from sqlalchemy import text
from sigma_m3.models import Run
from sigma_m3.errors import DomainError
from sigma_m3.services.runs import digest
from sigma_m3.services.forecast import clean_json


def verify_run(settings, sessions, key, allow_running=False):
    with sessions() as s:
        run = s.get(Run, key)
        if run is None:
            raise DomainError("not_found", "Run does not exist", 404)
        if run.status != "complete" and not (allow_running and run.status == "running"):
            raise DomainError(
                "run_not_complete", "Cannot verify incomplete results", 409
            )
        snap = run.config_snapshot
        if run.status == "complete" and digest(snap) != run.config_sha256:
            raise DomainError("verification_failed", "Config checksum differs")
        root = settings.output_root / str(key)
        for name, checksum in run.artifact_manifest.items():
            path = (root / name).resolve()
            if (
                not path.is_relative_to(root.resolve())
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != checksum
            ):
                raise DomainError("verification_failed", "Artifact checksum differs")
        if run.kind == "source_import":
            totals = s.execute(
                text(
                    "SELECT count(*),sum(sales_qty),bool_and(actual_available) FROM daily_sales WHERE source_import_run_id=:id"
                ),
                {"id": source_data_id(run)},
            ).one()
            if totals[1] != run.result_summary["sales_quantity"] or not totals[2]:
                raise DomainError("verification_failed", "Source totals differ")
            result = dict(
                status="verified",
                kind=run.kind,
                daily_rows=totals[0],
                sales_quantity=int(totals[1]),
            )
        elif run.kind == "forecast":
            result = verify_forecast(s, run, root)
        else:
            result = verify_inventory(s, run, settings)
    if not allow_running:
        output = settings.output_root.parent / (str(key) + "_verification.json")
        output.write_text(
            json.dumps(clean_json(result), indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
    return result


def verify_forecast(s, run, root):
    key = run.id
    source = s.get(Run, run.source_import_run_id)
    source_days = pd.read_sql(
        text(
            "SELECT item_id,date,sales_qty FROM daily_sales WHERE source_import_run_id=:id"
        ),
        s.connection(),
        params={"id": source_data_id(source)},
        parse_dates=["date"],
    )
    matrix = source_days.pivot(index="date", columns="item_id", values="sales_qty")
    catalog = run.config_snapshot["catalog_snapshot"]
    warehouses = run.config_snapshot["warehouse_snapshot"]
    route_ids = {(w["destination_country"], w["carrier"]): w["id"] for w in warehouses}
    item_route = {
        i["item_id"]: route_ids[(i["destination_country"], i["carrier"])]
        for i in catalog
    }
    route_series = {
        wid: matrix[[i for i in matrix.columns if item_route[i] == wid]].sum(axis=1)
        for wid in route_ids.values()
    }
    routes = pd.read_sql(
        text("SELECT * FROM route_forecasts WHERE run_id=:id"),
        s.connection(),
        params={"id": key},
        parse_dates=["as_of_date", "window_start", "target_date"],
    )
    if len(routes) != run.result_summary.get("route_forecast_rows", len(routes)):
        raise DomainError("verification_failed", "Route count differs")
    if (
        len(set(routes.warehouse_id)) != 46
        or routes.groupby("as_of_date").size().ne(92).any()
    ):
        raise DomainError("verification_failed", "Incomplete 46-route origin")
    actual_count = 0
    for row in routes.itertuples():
        actual = route_series[row.warehouse_id].loc[row.window_start : row.target_date]
        available = len(actual) == 7
        if (
            available != row.actual_available
            or (available and float(actual.sum()) != row.actual_qty)
            or (not available and pd.notna(row.actual_qty))
        ):
            raise DomainError(
                "verification_failed", "Weekly actual availability or quantity differs"
            )
        actual_count += 1
    sums = pd.read_sql(
        text("""SELECT i.warehouse_id,f.as_of_date,((f.horizon_day-1)/7+1) AS block,SUM(f.forecast_qty) AS allocated
        FROM item_forecasts f JOIN items i ON i.id=f.item_id WHERE f.run_id=:id GROUP BY i.warehouse_id,f.as_of_date,((f.horizon_day-1)/7+1)"""),
        s.connection(),
        params={"id": key},
        parse_dates=["as_of_date"],
    )
    joined = routes.merge(
        sums, on=["warehouse_id", "as_of_date", "block"], validate="one_to_one"
    )
    if len(joined) != len(routes) or not np.allclose(
        joined.forecast_qty, joined.allocated, atol=1e-8, rtol=0
    ):
        raise DomainError(
            "verification_failed", "Allocation does not conserve weekly totals"
        )
    cache = {}
    items_checked = 0
    total_by_key = {
        (r.warehouse_id, r.as_of_date, r.block): r.forecast_qty
        for r in routes.itertuples()
    }
    known_by_route = {
        wid: [i for i in catalog if item_route[i["item_id"]] == wid]
        for wid in route_ids.values()
    }
    for chunk in pd.read_sql(
        text(
            "SELECT item_id,as_of_date,target_date,horizon_day,forecast_qty,item_share,weekday_weight,share_window_days,actual_qty,actual_available FROM item_forecasts WHERE run_id=:id ORDER BY as_of_date,item_id,horizon_day"
        ),
        s.connection(),
        params={"id": key},
        parse_dates=["as_of_date", "target_date"],
        chunksize=50000,
    ):
        for r in chunk.itertuples():
            wid = item_route[r.item_id]
            ck = (wid, r.as_of_date)
            if ck not in cache:
                eligible = [
                    i
                    for i in known_by_route[wid]
                    if pd.Timestamp(i["first_seen_date"]) <= r.as_of_date
                ]
                ids = [i["item_id"] for i in eligible]
                prior = matrix.loc[
                    r.as_of_date - pd.Timedelta(days=89) : r.as_of_date, ids
                ]
                if len(prior) != 90:
                    raise DomainError(
                        "verification_failed", "Allocation history incomplete"
                    )
                route = prior.sum(axis=1)
                weight = (
                    route.groupby(route.index.weekday)
                    .sum()
                    .reindex(range(7), fill_value=0)
                    .to_numpy(float)
                )
                weight = weight / weight.sum() if weight.sum() else np.full(7, 1 / 7)
                share = prior.tail(30).sum()
                window = 30
                if not share.sum():
                    share = prior.sum()
                    window = 90
                if not share.sum():
                    raise DomainError(
                        "verification_failed",
                        "Missing allocation basis was filled silently",
                    )
                cache[ck] = (dict((share / share.sum()).items()), weight, window)
            shares, weights, window = cache[ck]
            if r.item_id not in shares:
                raise DomainError(
                    "verification_failed", "Future item leaked into allocation"
                )
            total = total_by_key[(wid, r.as_of_date, 1 if r.horizon_day <= 7 else 2)]
            expected = total * shares[r.item_id] * weights[r.target_date.weekday()]
            if (
                abs(expected - r.forecast_qty) > 1e-8
                or abs(r.item_share - shares[r.item_id]) > 1e-12
                or abs(r.weekday_weight - weights[r.target_date.weekday()]) > 1e-12
                or r.share_window_days != window
            ):
                raise DomainError(
                    "verification_failed", "Independent allocation arithmetic differs"
                )
            available = r.target_date in matrix.index
            if (
                available != r.actual_available
                or available
                and int(matrix.at[r.target_date, r.item_id]) != r.actual_qty
            ):
                raise DomainError("verification_failed", "Item actual differs")
            items_checked += 1
    selection_checked = 0
    fit_rows = 0
    if run.config_snapshot["request"]["mode"] == "replay":
        lock = json.loads((root / "selection_lock.json").read_text())
        if (
            hashlib.sha256((root / "selection_lock.json").read_bytes()).hexdigest()
            != run.selection_sha256
        ):
            raise DomainError("verification_failed", "Selection lock checksum differs")
        candidates = pd.read_csv(root / "validation_candidate_metrics.csv")
        candidates = candidates.loc[
            candidates.block.eq(1)
            & candidates.cadence.eq("daily_origins")
            & candidates.coverage.eq(1)
        ].copy()
        candidates["rank_mape"] = candidates.mape_positive_pct.fillna(float("inf"))
        for choice in lock["selections"]:
            part = candidates.loc[
                candidates.destination_country.eq(choice["destination_country"])
                & candidates.carrier.eq(choice["carrier"])
            ]
            winner = part.sort_values(["rank_mape", "mae", "model"]).iloc[0]
            if winner.model != choice["model"] or winner.family != choice["family"]:
                raise DomainError(
                    "verification_failed", "Selection differs from validation ranking"
                )
            selection_checked += 1
    for path in root.glob("*_fitlog.csv"):
        log = pd.read_csv(path)
        for label, cutoff in [
            ("max_label_end", "fit_cutoff"),
            ("max_head_label_end", "as_of_date"),
            ("head_label_end", "fit_cutoff"),
        ]:
            if label in log and cutoff in log:
                valid = log[label].notna() & log[cutoff].notna()
                if (
                    pd.to_datetime(log.loc[valid, label])
                    > pd.to_datetime(log.loc[valid, cutoff])
                ).any():
                    raise DomainError(
                        "verification_failed", "Training labels exceed their cutoff"
                    )
        fit_rows += len(log)
    return dict(
        status="verified",
        kind="forecast",
        routes=46,
        weekly_labels_checked=actual_count,
        allocation_groups_checked=len(joined),
        item_forecasts_checked=items_checked,
        validation_selections_checked=selection_checked,
        fit_log_rows_checked=fit_rows,
        selection_sha256=run.selection_sha256,
        causal_item_eligibility=True,
    )


def verify_inventory(s, run, settings):
    params = {"id": run.id}
    ledger = pd.read_sql(
        text(
            "SELECT * FROM inventory_daily WHERE run_id=:id ORDER BY window_origin,item_id,date"
        ),
        s.connection(),
        params=params,
        parse_dates=["window_origin", "date", "forecast_as_of_date"],
    )
    events = pd.read_sql(
        text(
            "SELECT * FROM inventory_events WHERE run_id=:id ORDER BY window_origin,item_id,event_sequence"
        ),
        s.connection(),
        params=params,
        parse_dates=["window_origin", "event_at"],
    )
    orders = pd.read_sql(
        text("SELECT * FROM replenishment_orders WHERE run_id=:id"),
        s.connection(),
        params=params,
        parse_dates=["window_origin", "ordered_on", "eta"],
    )
    alerts = pd.read_sql(
        text("SELECT * FROM alerts WHERE run_id=:id"),
        s.connection(),
        params=params,
        parse_dates=[
            "window_origin",
            "as_of_date",
            "predicted_depletion_date",
            "actual_depletion_date",
        ],
    )
    source = s.get(Run, run.source_import_run_id)
    daily = pd.read_sql(
        text(
            "SELECT item_id,date,sales_qty FROM daily_sales WHERE source_import_run_id=:id"
        ),
        s.connection(),
        params={"id": source_data_id(source)},
        parse_dates=["date"],
    )
    matrix = daily.pivot(index="date", columns="item_id", values="sales_qty")
    fc = pd.read_sql(
        text(
            "SELECT item_id,as_of_date,horizon_day,forecast_qty FROM item_forecasts WHERE run_id=:id AND as_of_date=ANY(:origins)"
        ),
        s.connection(),
        params={
            "id": run.forecast_run_id,
            "origins": [d.date() for d in ledger.forecast_as_of_date.unique()],
        },
        parse_dates=["as_of_date"],
    )
    vectors = {
        (d, int(i)): p.sort_values("horizon_day").forecast_qty.to_numpy()
        for (d, i), p in fc.groupby(["as_of_date", "item_id"])
    }
    policies = {p["id"]: p for p in run.config_snapshot["policies"]}
    scenario = run.config_snapshot["scenario"]["settings"]
    order_groups = {
        (w, int(i)): g for (w, i), g in orders.groupby(["window_origin", "item_id"])
    }
    empty_orders = orders.iloc[:0]
    if len(orders):
        if not (orders.eta - orders.ordered_on).dt.days.eq(7).all():
            raise DomainError("verification_failed", "ETA differs from D+7")
        received = (
            events.loc[events.event_kind.eq("receipt")]
            .groupby("replenishment_order_id")
            .agg(count=("id", "size"), qty=("quantity", "sum"))
        )
        for order in orders.itertuples():
            if order.status == "received":
                if (
                    order.id not in received.index
                    or received.at[order.id, "count"] != 1
                    or received.at[order.id, "qty"] != order.ordered_qty
                ):
                    raise DomainError(
                        "verification_failed", "Receipt count/quantity differs"
                    )
            elif order.id in received.index:
                raise DomainError(
                    "verification_failed", "Pending order already received"
                )
    threshold_count = 0
    for (window, item), group in ledger.groupby(["window_origin", "item_id"]):
        initial = math.ceil(
            float(matrix.loc[window - pd.Timedelta(days=27) : window, item].mean())
            * scenario["cover_days"]
        )
        if group.iloc[0].closing_qty != initial:
            raise DomainError(
                "verification_failed", "Initial stock used the wrong cutoff"
            )
        lots = order_groups.get((window, int(item)), empty_orders)
        lot_rows = list(lots.itertuples())
        previous = initial
        for r in group.itertuples():
            if (
                r.opening_qty != previous
                or r.closing_qty != r.opening_qty + r.receipts_qty - r.fulfilled_qty
                or r.sales_qty != r.fulfilled_qty + r.shortage_qty
                or r.closing_qty < 0
            ):
                raise DomainError("verification_failed", "Daily balance differs")
            if r.date > window and int(matrix.at[r.date, item]) != r.sales_qty:
                raise DomainError(
                    "verification_failed",
                    "Sales was replaced by fulfillment or dropped",
                )
            pending = sum(
                o.ordered_qty
                for o in lot_rows
                if o.eta > r.date and (o.is_initial or o.ordered_on < r.date)
            )
            f = vectors[(r.forecast_as_of_date, int(item))]
            p = policies[r.policy_id]
            ss = math.ceil(
                float(p["safety_days"])
                * scenario["safety_multiplier"]
                * float(f.mean())
            )
            rf = math.ceil(float(f[:7].sum()) + ss)
            rop = max(rf, p["configured_rop_floor"])
            target = rop + math.ceil(float(f[7]))
            ip = r.closing_qty + int(pending)
            raw = max(0, target - ip) if r.closing_qty < rop else 0
            q = max(math.ceil(raw), p["moq"]) if raw else 0
            if (
                r.ss,
                r.rop_forecast,
                r.rop,
                r.target_stock,
                r.pending_qty,
                r.inventory_position,
                bool(r.needs_replenishment),
                r.recommended_qty,
            ) != (ss, rf, rop, target, int(pending), ip, r.closing_qty < rop, q):
                raise DomainError(
                    "verification_failed", "Independent policy thresholds differ"
                )
            own = [o for o in lot_rows if o.ordered_on == r.date and not o.is_initial]
            if run.kind == "policy_replay" and (
                (q > 0 and (len(own) != 1 or own[0].ordered_qty != q))
                or (q == 0 and len(own))
            ):
                raise DomainError(
                    "verification_failed", "Order differs from recommendation"
                )
            previous = r.closing_qty
            threshold_count += 1
    event_balance_count = 0
    from sigma_m3.services.m2_adapter import configuration
    from src.data import audit_orders

    cfg, _, _ = configuration()
    raw_sales, audit = audit_orders(settings.order_source("orders_snapshot"), cfg)
    if audit["source_sha256_before"] != source.source_sha256:
        raise DomainError("verification_failed", "Raw source hash differs")
    routes = {
        (i["destination_country"], i["carrier"], i["sku"], i["product_type"]): i[
            "item_id"
        ]
        for i in run.config_snapshot["catalog_snapshot"]
    }
    raw_events = {
        n: (
            r.order_datetime,
            routes[(r.destination_country, r.carrier, r.sku, r.product_type)],
            int(r.quantity),
        )
        for n, r in enumerate(
            raw_sales.sort_values(
                ["order_datetime", "order_id"], kind="mergesort"
            ).itertuples(index=False),
            1,
        )
    }
    for (window, item), group in events.groupby(["window_origin", "item_id"]):
        balance = 0
        seen = set()
        last_time = None
        for r in group.itertuples():
            if last_time is not None and r.event_at < last_time:
                raise DomainError("verification_failed", "Events are not chronological")
            last_time = r.event_at
            if r.event_kind == "initial_stock":
                balance += r.quantity
            elif r.event_kind == "receipt":
                balance += r.quantity
            else:
                if r.source_sequence in seen or raw_events.get(r.source_sequence) != (
                    r.event_at,
                    int(item),
                    r.quantity,
                ):
                    raise DomainError(
                        "verification_failed",
                        "Sale timestamp/order sequence/quantity differs from the source",
                    )
                seen.add(r.source_sequence)
                fulfilled = min(balance, r.quantity)
                if (
                    fulfilled != r.fulfilled_qty
                    or r.quantity - r.fulfilled_qty != r.shortage_qty
                ):
                    raise DomainError(
                        "verification_failed", "Event fulfillment order differs"
                    )
                balance -= r.fulfilled_qty
            if balance != r.balance_after:
                raise DomainError("verification_failed", "Event balance differs")
            event_balance_count += 1
    observed_events = events.loc[events.event_kind.ne("initial_stock")].copy()
    observed_events["date"] = (
        observed_events.event_at.dt.tz_convert("UTC")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    event_totals = (
        observed_events.assign(
            sales_qty=lambda f: np.where(f.event_kind.eq("sale"), f.quantity, 0),
            receipts_qty=lambda f: np.where(f.event_kind.eq("receipt"), f.quantity, 0),
        )
        .groupby(["window_origin", "item_id", "date"])[
            ["sales_qty", "receipts_qty", "fulfilled_qty", "shortage_qty"]
        ]
        .sum()
    )
    for r in ledger.itertuples():
        totals = (
            event_totals.loc[(r.window_origin, r.item_id, r.date)].tolist()
            if (r.window_origin, r.item_id, r.date) in event_totals.index
            else [0, 0, 0, 0]
        )
        if totals != [r.sales_qty, r.receipts_qty, r.fulfilled_qty, r.shortage_qty]:
            raise DomainError(
                "verification_failed",
                "Event totals do not reconcile to the daily ledger",
            )
    first_depleted = {
        (w, int(i)): g.loc[g.date.gt(w) & g.closing_qty.eq(0), "date"].min()
        for (w, i), g in ledger.groupby(["window_origin", "item_id"])
    }
    confusion = dict(TP=0, FP=0, FN=0, TN=0)
    early = denominator = excluded = 0
    for row in alerts.loc[alerts.alert_type.eq("depletion")].itertuples():
        exp = row.explanation
        balance = float(exp["origin_on_hand"])
        predicted = row.as_of_date if balance == 0 else None
        receipts = {pd.Timestamp(r["eta"]): r["quantity"] for r in exp["receipts"]}
        f = vectors[(row.as_of_date, int(row.item_id))]
        np.testing.assert_allclose(exp["forecast14"], f, atol=1e-8, rtol=0)
        for h, quantity in enumerate(f, 1):
            d = row.as_of_date + pd.Timedelta(days=h)
            balance = max(0, balance + receipts.get(d, 0) - quantity)
            if predicted is None and balance == 0:
                predicted = d
        if (pd.isna(row.predicted_depletion_date) and predicted is not None) or (
            pd.notna(row.predicted_depletion_date)
            and row.predicted_depletion_date != predicted
        ):
            raise DomainError("verification_failed", "Projected depletion differs")
        if run.kind == "alert_replay":
            if row.state == "already_depleted":
                excluded += 1
                continue
            actual = first_depleted[(row.window_origin, int(row.item_id))]
            if (
                pd.isna(actual) != pd.isna(row.actual_depletion_date)
                or pd.notna(actual)
                and actual != row.actual_depletion_date
            ):
                raise DomainError(
                    "verification_failed", "Actual first depletion differs"
                )
            label = (
                "TP"
                if predicted is not None and pd.notna(actual)
                else "FP"
                if predicted is not None
                else "FN"
                if pd.notna(actual)
                else "TN"
            )
            if row.evaluation_class != label:
                raise DomainError("verification_failed", "Confusion class differs")
            confusion[label] += 1
            if pd.notna(actual):
                denominator += 1
                early += int(
                    predicted is not None and (actual - row.as_of_date).days >= 7
                )
    if run.kind == "alert_replay":
        m = run.result_summary.get("alert_metrics", {})
        if m and (
            any(m[k] != v for k, v in confusion.items())
            or m["early_numerator"] != early
            or m["event_denominator"] != denominator
            or m["excluded_count"] != excluded
        ):
            raise DomainError("verification_failed", "Alert metric denominator differs")
    return dict(
        status="verified",
        kind=run.kind,
        thresholds_checked=threshold_count,
        events_checked=event_balance_count,
        orders_checked=len(orders),
        alerts_checked=len(alerts),
        confusion=confusion if run.kind == "alert_replay" else None,
        early_numerator=early,
        event_denominator=denominator,
        excluded_count=excluded,
    )
