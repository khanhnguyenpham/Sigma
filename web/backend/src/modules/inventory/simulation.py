from core.run_context import source_data_id

"""Transaction replay and projection on frozen policy/forecast snapshots."""
from datetime import date, datetime, timedelta, timezone
import math, json, hashlib
import numpy as np
import pandas as pd
from sqlalchemy import select, text
from core.errors import DomainError
from modules.runs.models import Run
from modules.forecasting.models import DailySales, ItemForecast
from modules.purchasing.models import Replenishment
from modules.inventory.service import PolicyValues, recommend, fulfill_day, eta
from modules.alerts.service import project, replay_metrics
from modules.runs.service import progress
from core.serialization import clean_json
from src.data import audit_orders
from modules.forecasting.m2_adapter import configuration


def policy_at(policies, item, day):
    rows = [
        p
        for p in policies
        if p["item_id"] == item
        and p["effective_from"] <= day.isoformat()
        and (p["effective_to"] is None or day.isoformat() < p["effective_to"])
    ]
    if len(rows) != 1:
        raise DomainError(
            "missing_partner_config", "Expected one frozen policy", item_id=item
        )
    return rows[0]


def pure_window(
    matrix, sales_events, catalog, forecasts, policies, scenario, kind, origin, end
):
    known = [i for i in catalog if date.fromisoformat(i["first_seen_date"]) <= origin]
    ids = [i["item_id"] for i in known]
    history = matrix.reindex(pd.date_range(origin - timedelta(days=27), origin))[ids]
    if len(history) != 28 or not np.isfinite(history.to_numpy(float)).all():
        raise DomainError(
            "insufficient_history", "Initial stock needs 28 observed days"
        )
    if kind == "policy_replay":
        later = {i["item_id"] for i in catalog if i["item_id"] not in ids}
        if any(item in later and origin < day <= end for day, item in sales_events):
            raise DomainError(
                "missing_allocation_basis",
                "New item appears inside replay; initialization needs a new causal window",
            )
    stock = {
        i: math.ceil(float(history[i].mean()) * scenario["cover_days"]) for i in ids
    }
    sequences = {i: 0 for i in ids}
    orders = []
    orders_by_item = {i: [] for i in ids}
    events = []
    ledger = []
    alerts = []

    def add_order(record):
        orders.append(record)
        orders_by_item[record["item_id"]].append(record)

    for item in ids:
        events.append(
            dict(
                window_origin=origin,
                item_id=item,
                event_at=datetime.combine(
                    origin, datetime.max.time(), tzinfo=timezone.utc
                ),
                event_sequence=0,
                event_kind="initial_stock",
                source_sequence=None,
                order_reference=None,
                quantity=stock[item],
                fulfilled_qty=0,
                shortage_qty=0,
                balance_after=stock[item],
                is_simulated=True,
            )
        )
    for lot in scenario.get("receipts_initial", []):
        if lot["item_id"] not in stock:
            continue
        ordered = date.fromisoformat(lot["ordered_on"])
        arrival = date.fromisoformat(lot["eta"])
        if ordered > origin:
            raise DomainError("invalid_input", "Initial lot was not known at origin")
        if arrival > origin:
            p = policy_at(policies, lot["item_id"], origin)
            add_order(
                dict(
                    window_origin=origin,
                    item_id=lot["item_id"],
                    policy_id=p["id"],
                    order_key="initial:" + lot["lot_key"],
                    ordered_on=ordered,
                    eta=arrival,
                    ordered_qty=lot["ordered_qty"],
                    received_qty=0,
                    status="ordered",
                    is_initial=True,
                    is_simulated=True,
                )
            )
    actual_depletion = {i: None for i in ids}
    initial_zero = {i: stock[i] == 0 for i in ids}
    days = (
        [origin]
        if kind == "stock_projection"
        else [origin + timedelta(days=h) for h in range((end - origin).days + 1)]
    )
    for day in days:
        for item in ids:
            opening = stock[item]
            received = 0
            arrivals = [
                o
                for o in orders_by_item[item]
                if o["status"] == "ordered" and o["eta"] == day
            ]
            for lot in arrivals:
                stock[item] += lot["ordered_qty"]
                received += lot["ordered_qty"]
                lot["received_qty"] = lot["ordered_qty"]
                lot["status"] = "received"
                sequences[item] += 1
                events.append(
                    dict(
                        window_origin=origin,
                        item_id=item,
                        event_at=datetime.combine(
                            day, datetime.min.time(), tzinfo=timezone.utc
                        ),
                        event_sequence=sequences[item],
                        event_kind="receipt",
                        source_sequence=None,
                        order_reference=(origin, lot["order_key"]),
                        quantity=lot["ordered_qty"],
                        fulfilled_qty=0,
                        shortage_qty=0,
                        balance_after=stock[item],
                        is_simulated=True,
                    )
                )
            demands = sales_events.get((day, item), []) if day > origin else []
            fulfilled = fulfill_day(opening, received, [r["quantity"] for r in demands])
            stock[item] = fulfilled["closing_qty"]
            for demand, event in zip(demands, fulfilled["events"], strict=True):
                sequences[item] += 1
                events.append(
                    dict(
                        window_origin=origin,
                        item_id=item,
                        event_at=demand["event_at"],
                        event_sequence=sequences[item],
                        event_kind="sale",
                        source_sequence=demand["source_sequence"],
                        order_reference=None,
                        **event,
                        is_simulated=True,
                    )
                )
            if (
                day > origin
                and not initial_zero[item]
                and stock[item] == 0
                and actual_depletion[item] is None
            ):
                actual_depletion[item] = day
            decision_origin = origin if kind == "alert_replay" else day
            vector = forecasts.get((decision_origin, item))
            if vector is None:
                raise DomainError(
                    "insufficient_forecast", "Missing item H14 vector", item_id=item
                )
            p = policy_at(policies, item, decision_origin)
            values = PolicyValues(
                p["configured_rop_floor"],
                p["moq"],
                float(p["safety_days"]) * scenario["safety_multiplier"],
            )
            pending = sum(
                o["ordered_qty"]
                for o in orders_by_item[item]
                if o["status"] == "ordered"
            )
            decision = recommend(vector, stock[item], pending, values)
            ledger.append(
                dict(
                    window_origin=origin,
                    item_id=item,
                    date=day,
                    policy_id=p["id"],
                    forecast_as_of_date=decision_origin,
                    opening_qty=opening,
                    receipts_qty=received,
                    sales_qty=fulfilled["sales_qty"],
                    fulfilled_qty=fulfilled["fulfilled_qty"],
                    shortage_qty=fulfilled["shortage_qty"],
                    closing_qty=stock[item],
                    ss=decision["ss"],
                    rop_forecast=decision["rop_forecast"],
                    rop=decision["rop"],
                    target_stock=decision["target_stock"],
                    pending_qty=pending,
                    inventory_position=decision["inventory_position"],
                    needs_replenishment=decision["needs_replenishment"],
                    recommended_qty=decision["recommended_qty"],
                    config_status="complete",
                    is_simulated=True,
                )
            )
            if kind != "alert_replay" or day == origin:
                receipts = {}
                for lot in orders_by_item[item]:
                    if lot["item_id"] == item and lot["status"] == "ordered":
                        receipts[lot["eta"]] = (
                            receipts.get(lot["eta"], 0) + lot["ordered_qty"]
                        )
                projection = project(day, stock[item], vector, receipts)
                explanation = dict(
                    origin_on_hand=stock[item],
                    forecast14=list(map(float, vector)),
                    receipts=[
                        dict(eta=d.isoformat(), quantity=q)
                        for d, q in sorted(receipts.items())
                    ],
                    policy=p,
                    thresholds=decision,
                    projection=projection["projection"],
                    basis="known_receipts_before_new_recommendation",
                )
                alerts.append(
                    dict(
                        window_origin=origin,
                        item_id=item,
                        as_of_date=day,
                        alert_type="depletion",
                        state=projection["state"],
                        predicted_depletion_date=projection["predicted_depletion_date"],
                        actual_depletion_date=None,
                        lead_days=projection["lead_days"],
                        is_evaluable=False,
                        evaluation_class=None,
                        exclusion_reason=None,
                        explanation=explanation,
                        is_simulated=True,
                    )
                )
                if decision["needs_replenishment"]:
                    alerts.append(
                        dict(
                            window_origin=origin,
                            item_id=item,
                            as_of_date=day,
                            alert_type="below_rop",
                            state=decision["state"],
                            predicted_depletion_date=None,
                            actual_depletion_date=None,
                            lead_days=None,
                            is_evaluable=False,
                            evaluation_class=None,
                            exclusion_reason=None,
                            explanation=dict(policy=p, thresholds=decision),
                            is_simulated=True,
                        )
                    )
            if kind == "policy_replay" and decision["recommended_qty"] > 0:
                add_order(
                    dict(
                        window_origin=origin,
                        item_id=item,
                        policy_id=p["id"],
                        order_key=f"policy:{item}:{day.isoformat()}",
                        ordered_on=day,
                        eta=eta(day),
                        ordered_qty=decision["recommended_qty"],
                        received_qty=0,
                        status="ordered",
                        is_initial=False,
                        is_simulated=True,
                    )
                )
    cases = []
    if kind == "alert_replay":
        for row in alerts:
            if row["alert_type"] != "depletion":
                continue
            item = row["item_id"]
            actual = actual_depletion[item]
            predicted = (
                row["predicted_depletion_date"]
                if row["state"] != "already_depleted"
                else None
            )
            row["actual_depletion_date"] = actual
            row["is_evaluable"] = not initial_zero[item]
            row["exclusion_reason"] = (
                "already_depleted_at_origin" if initial_zero[item] else None
            )
            row["evaluation_class"] = (
                None
                if initial_zero[item]
                else "TP"
                if predicted and actual
                else "FP"
                if predicted
                else "FN"
                if actual
                else "TN"
            )
            cases.append(
                dict(
                    as_of_date=origin,
                    predicted_depletion_date=predicted,
                    actual_depletion_date=actual,
                    already_depleted=initial_zero[item],
                )
            )
    observed = [r for r in ledger if r["date"] > origin]
    sales_total = sum(r["sales_qty"] for r in observed)
    fulfill = sum(r["fulfilled_qty"] for r in observed)
    summary = dict(
        sales_qty=sales_total,
        fulfilled_qty=fulfill,
        shortage_qty=sales_total - fulfill,
        fill_rate=fulfill / sales_total if sales_total else None,
        mean_closing=sum(r["closing_qty"] for r in observed) / len(observed)
        if observed
        else None,
        order_count=len(orders),
        ordered_qty=sum(o["ordered_qty"] for o in orders),
        items=len(ids),
        already_depleted_count=sum(initial_zero.values()),
    )
    return dict(
        ledger=ledger,
        events=events,
        orders=orders,
        alerts=alerts,
        cases=cases,
        summary=summary,
    )


def simulate_run(settings, sessions, key):
    with sessions() as s:
        run = s.get(Run, key)
        source = s.get(Run, run.source_import_run_id)
        forecast_parent = s.get(Run, run.forecast_run_id)
        snapshot = run.config_snapshot
        catalog = snapshot["catalog_snapshot"]
        policies = snapshot["policies"]
        scenario = snapshot["scenario"]["settings"]
        kind = run.kind
        origin = run.as_of_date
        end = run.period_end if kind != "stock_projection" else origin
        if end and end > source.observation_end:
            raise DomainError(
                "insufficient_history",
                "Replay requires observed sales throughout the period",
            )
        daily = pd.read_sql(
            select(
                DailySales.item_id,
                DailySales.date,
                DailySales.sales_qty,
                DailySales.actual_available,
            ).where(DailySales.source_import_run_id == source_data_id(source)),
            s.connection(),
            parse_dates=["date"],
        )
        needed_origins = (
            [origin]
            if kind == "stock_projection"
            else [
                origin + timedelta(days=i)
                for i in range(0, (end - origin).days + 1, 14)
            ]
            if kind == "alert_replay"
            else [origin + timedelta(days=i) for i in range((end - origin).days + 1)]
        )
        fc = pd.read_sql(
            select(
                ItemForecast.item_id,
                ItemForecast.as_of_date,
                ItemForecast.horizon_day,
                ItemForecast.forecast_qty,
            ).where(
                ItemForecast.run_id == forecast_parent.id,
                ItemForecast.as_of_date.in_(needed_origins),
            ),
            s.connection(),
            parse_dates=["as_of_date"],
        )
    if not daily.actual_available.all():
        raise DomainError("insufficient_history", "Observed daily history has gaps")
    matrix = daily.pivot(index="date", columns="item_id", values="sales_qty")
    vectors = {}
    for (as_of, item), part in fc.groupby(["as_of_date", "item_id"]):
        part = part.sort_values("horizon_day")
        if part.horizon_day.tolist() != list(range(1, 15)):
            raise DomainError(
                "insufficient_forecast",
                "Forecast vector is incomplete",
                item_id=int(item),
            )
        vectors[(as_of.date(), int(item))] = part.forecast_qty.to_numpy()
    cfg, _, _ = configuration()
    sales, audit = audit_orders(settings.order_source("orders_snapshot"), cfg)
    if audit["source_sha256_before"] != source.source_sha256:
        raise DomainError("parent_mismatch", "Source changed since import")
    item_map = {
        (i["destination_country"], i["carrier"], i["sku"], i["product_type"]): i[
            "item_id"
        ]
        for i in catalog
    }
    ordered = sales.sort_values(["order_datetime", "order_id"], kind="mergesort")
    grouped = {}
    for sequence, r in enumerate(ordered.itertuples(index=False), 1):
        day = r.date.date()
        if day <= origin or day > end:
            continue
        item = item_map[(r.destination_country, r.carrier, r.sku, r.product_type)]
        grouped.setdefault((day, item), []).append(
            dict(
                event_at=r.order_datetime.to_pydatetime(),
                source_sequence=sequence,
                quantity=int(r.quantity),
            )
        )
    windows = []
    if kind == "alert_replay":
        day = origin
        while day + timedelta(days=14) <= end:
            windows.append((day, day + timedelta(days=14)))
            day += timedelta(days=14)
    else:
        windows = [(origin, end)]
    combined = {name: [] for name in ["ledger", "events", "orders", "alerts", "cases"]}
    summaries = []
    for idx, (start, finish) in enumerate(windows, 1):
        progress(
            sessions,
            key,
            "simulation",
            completed_windows=idx - 1,
            total_windows=len(windows),
        )
        result = pure_window(
            matrix, grouped, catalog, vectors, policies, scenario, kind, start, finish
        )
        for name in combined:
            combined[name].extend(result[name])
        summaries.append(result["summary"])
    if not windows:
        raise DomainError("insufficient_history", "No complete 14-day alert window")
    with sessions.begin() as s:
        order_map = {}
        for offset in range(0, len(combined["orders"]), 1000):
            batch = [
                dict(run_id=key, **o)
                for o in combined["orders"][offset : offset + 1000]
            ]
            for row in s.execute(
                Replenishment.__table__.insert().returning(
                    Replenishment.id,
                    Replenishment.window_origin,
                    Replenishment.order_key,
                ),
                batch,
            ):
                order_map[(row.window_origin, row.order_key)] = row.id
        raw = s.connection().connection.driver_connection
        for name, table in [
            ("ledger", "inventory_daily"),
            ("events", "inventory_events"),
            ("alerts", "alerts"),
        ]:
            records = combined[name]
            if not records:
                continue
            if name == "events":
                for row in records:
                    row["replenishment_order_id"] = (
                        order_map[row.pop("order_reference")]
                        if row["order_reference"]
                        else None
                    )
                    row.pop("order_reference", None)
            columns = ["run_id", *records[0].keys()]
            with (
                raw.cursor() as cursor,
                cursor.copy(
                    "COPY " + table + " (" + ",".join(columns) + ") FROM STDIN"
                ) as copy,
            ):
                from psycopg.types.json import Jsonb

                for row in records:
                    copy.write_row(
                        [
                            key,
                            *[
                                Jsonb(clean_json(v))
                                if isinstance(v, (dict, list))
                                else v
                                for v in row.values()
                            ],
                        ]
                    )
        bad = s.scalar(
            text(
                "SELECT count(*) FROM inventory_daily WHERE run_id=:run AND (closing_qty<>opening_qty+receipts_qty-fulfilled_qty OR sales_qty<>fulfilled_qty+shortage_qty OR closing_qty<0)"
            ),
            {"run": key},
        )
        if bad:
            raise DomainError("inventory_mismatch", "Ledger balance failed")
    observed = [r for r in combined["ledger"] if r["date"] > r["window_origin"]]
    total = sum(r["sales_qty"] for r in observed)
    fulfilled = sum(r["fulfilled_qty"] for r in observed)
    summary = dict(
        phase="verified",
        kind=kind,
        ledger_rows=len(combined["ledger"]),
        event_rows=len(combined["events"]),
        order_count=len(combined["orders"]),
        alert_rows=len(combined["alerts"]),
        windows=len(windows),
        items=len({r["item_id"] for r in combined["ledger"]}),
        sales_qty=total,
        fulfilled_qty=fulfilled,
        shortage_qty=total - fulfilled,
        fill_rate=fulfilled / total if total else None,
        mean_closing=sum(r["closing_qty"] for r in observed) / len(observed)
        if observed
        else None,
        ordered_qty=sum(o["ordered_qty"] for o in combined["orders"]),
        is_simulated=True,
        alert_metrics=replay_metrics(combined["cases"])
        if kind == "alert_replay"
        else None,
        excluded_tail_days=(end - windows[-1][1]).days if kind == "alert_replay" else 0,
        metrics=[
            dict(
                granularity="alert" if kind == "alert_replay" else "policy",
                **(
                    replay_metrics(combined["cases"])
                    if kind == "alert_replay"
                    else dict(
                        sales_qty=total,
                        fulfilled_qty=fulfilled,
                        shortage_qty=total - fulfilled,
                        fill_rate=fulfilled / total if total else None,
                    )
                ),
            )
        ],
    )
    folder = settings.output_root / str(key)
    folder.mkdir(parents=True, exist_ok=False)
    payload = json.dumps(
        clean_json(summary), sort_keys=True, indent=2, allow_nan=False
    ).encode()
    (folder / "simulation_summary.json").write_bytes(payload)
    with sessions.begin() as s:
        s.get(Run, key).artifact_manifest = {
            "simulation_summary.json": hashlib.sha256(payload).hexdigest()
        }
    return summary
