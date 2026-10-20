from datetime import date, timedelta
import csv, io, uuid
from typing import Annotated, Literal
import numpy as np
import pandas as pd
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import Field
from sqlalchemy import select, func, text
from sigma_m3.schemas import DTO
from sigma_m3.models import (
    Run,
    Item,
    DailySales,
    RouteForecast,
    ItemForecast,
    InventoryDaily,
    Replenishment,
    Alert,
)
from sigma_m3.services.runs import required_run, source_data_id
from sigma_m3.services.forecast import clean_json
from sigma_m3.errors import DomainError
from src.evaluation import score
from sigma_m3.services.alerts import opportunity_breakdown

router = APIRouter(prefix="/api/v1/runs")
_ALLOCATED_METRICS = {}


class Filters(DTO):
    split: Literal["validation", "test", "future"] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    warehouse_id: int | None = Field(default=None, gt=0)
    item_id: int | None = Field(default=None, gt=0)
    supplier_id: int | None = Field(default=None, gt=0)
    product_type: Literal["eSIM", "physical_SIM"] | None = None
    date_from: date | None = None
    date_to: date | None = None
    as_of_date: date | None = None
    block: int | None = Field(default=None, ge=1, le=2)
    state: str | None = None
    granularity: Literal["weekly", "allocated_daily", "alert", "policy"] | None = None
    cadence: Literal["daily_origins", "nonoverlapping_7d"] | None = None
    aggregate: Literal["route_day"] | None = None


class WholeRun(DTO):
    """Diagnostic denominators must not silently change with table filters."""


def context(row):
    return dict(
        run_id=str(row.id),
        kind=row.kind,
        status=row.status,
        source_import_run_id=str(row.source_import_run_id)
        if row.source_import_run_id
        else None,
        forecast_run_id=str(row.forecast_run_id) if row.forecast_run_id else None,
        as_of_date=row.as_of_date.isoformat(),
        observation_end=row.observation_end.isoformat(),
        scenario_id=row.scenario_id,
        config_version=row.config_version,
        target_version=row.target_version,
        assumption_version=row.assumption_version,
        is_simulated=row.kind in {"policy_replay", "alert_replay", "stock_projection"},
        evaluation_limit="Historical snapshot; inventory simulated; no independent holdout.",
    )


def snapshot_maps(session, run):
    snap = run.config_snapshot
    if "catalog_snapshot" not in snap and run.source_import_run_id:
        snap = {**session.get(Run, run.source_import_run_id).config_snapshot, **snap}
    warehouses = {w["id"]: w for w in snap.get("warehouse_snapshot", [])}
    routes = {
        (w["destination_country"], w["carrier"]): w["id"] for w in warehouses.values()
    }
    items = {
        i["item_id"]: {
            **i,
            "warehouse_id": routes[(i["destination_country"], i["carrier"])],
        }
        for i in snap.get("catalog_snapshot", [])
    }
    policies = {p["id"]: p for p in snap.get("policies", [])}
    return warehouses, items, policies


def permitted_items(items, policies, filters, as_of):
    selected = set(items)
    if filters.item_id:
        selected &= {filters.item_id}
    if filters.warehouse_id:
        selected = {
            i for i in selected if items[i]["warehouse_id"] == filters.warehouse_id
        }
    if filters.product_type:
        selected = {
            i for i in selected if items[i]["product_type"] == filters.product_type
        }
    if filters.supplier_id:
        if not policies:
            raise DomainError(
                "invalid_input",
                "Supplier filter requires an inventory run with frozen policies",
            )
        selected &= {
            p["item_id"]
            for p in policies.values()
            if p["supplier_id"] == filters.supplier_id
            and p["effective_from"] <= as_of.isoformat()
            and (p["effective_to"] is None or p["effective_to"] > as_of.isoformat())
        }
    return selected


MODELS = {
    "route_forecasts": RouteForecast,
    "item_forecasts": ItemForecast,
    "inventory_daily": InventoryDaily,
    "replenishments": Replenishment,
    "alerts": Alert,
}


def dataset(session, run, name, filters, paginate=True):
    warehouses, items, policies = snapshot_maps(session, run)
    if filters.date_from and filters.date_to and filters.date_to < filters.date_from:
        raise DomainError("invalid_input", "Date interval is reversed")
    selected = permitted_items(
        items, policies, filters, filters.as_of_date or run.as_of_date
    )
    model = MODELS[name]
    if name in {"route_forecasts", "item_forecasts"} and run.kind != "forecast":
        raise DomainError("parent_mismatch", "This run has no forecast dataset", 409)
    if name in {"inventory_daily", "replenishments", "alerts"} and run.kind not in {
        "policy_replay",
        "alert_replay",
        "stock_projection",
    }:
        raise DomainError("parent_mismatch", "This run has no inventory dataset", 409)
    query = select(model).where(model.run_id == run.id)
    if model is RouteForecast:
        if filters.item_id or filters.product_type:
            raise DomainError(
                "invalid_input",
                "Item/type filtering requires allocated daily forecasts",
            )
        if filters.warehouse_id:
            query = query.where(model.warehouse_id == filters.warehouse_id)
        date_col = model.target_date
    else:
        query = query.where(model.item_id.in_(selected))
        date_col = (
            model.target_date
            if model is ItemForecast
            else model.date
            if model is InventoryDaily
            else model.ordered_on
            if model is Replenishment
            else model.as_of_date
        )
    if filters.as_of_date and hasattr(model, "as_of_date"):
        query = query.where(model.as_of_date == filters.as_of_date)
    if filters.block and model is RouteForecast:
        query = query.where(model.block == filters.block)
    if filters.date_from:
        query = query.where(date_col >= filters.date_from)
    if filters.date_to:
        query = query.where(date_col <= filters.date_to)
    if filters.state:
        if model is Alert:
            query = query.where(model.state == filters.state)
        elif model is InventoryDaily:
            query = query.where(model.needs_replenishment.is_(True))
            query = query.where(
                model.recommended_qty == 0
                if filters.state == "pending_covers"
                else model.recommended_qty > 0
            )
        else:
            raise DomainError(
                "invalid_input", "State filter is not supported for this dataset"
            )
    if filters.aggregate == "route_day":
        if model is not ItemForecast:
            raise DomainError(
                "invalid_input", "route_day aggregation needs item forecasts"
            )
        grouped = query.with_only_columns(
            Item.warehouse_id,
            model.as_of_date,
            model.target_date,
            model.horizon_day,
            func.sum(model.forecast_qty).label("forecast_qty"),
            func.sum(model.actual_qty).label("actual_qty"),
            func.bool_and(model.actual_available).label("actual_available"),
        )
        grouped = grouped.join(Item, Item.id == model.item_id).group_by(
            Item.warehouse_id, model.as_of_date, model.target_date, model.horizon_day
        )
        # Actual values for full routes come from all source items, not just items known at forecast origin.
        rows = (
            session.execute(
                grouped.order_by(model.as_of_date, model.target_date, Item.warehouse_id)
            )
            .mappings()
            .all()
        )
        source = required_run(
            session, run.source_import_run_id, "source_import", complete=True
        )
        actual_query = (
            select(
                Item.warehouse_id,
                DailySales.date,
                func.sum(DailySales.sales_qty),
                func.bool_and(DailySales.actual_available),
            )
            .join(Item, Item.id == DailySales.item_id)
            .where(
                DailySales.source_import_run_id == source_data_id(source),
                DailySales.item_id.in_(selected),
            )
            .group_by(Item.warehouse_id, DailySales.date)
        )
        actuals = {
            (w, d): (q, available)
            for w, d, q, available in session.execute(actual_query)
        }
        records = []
        for row in rows:
            r = dict(row)
            r.update(warehouses.get(r["warehouse_id"], {}))
            r.pop("id", None)
            actual, available = actuals.get(
                (r["warehouse_id"], r["target_date"]), (None, False)
            )
            r["actual_available"] = available
            r["actual_qty"] = actual if available else None
            r["block"] = (r["horizon_day"] - 1) // 7 + 1
            r["granularity"] = "allocated_daily"
            records.append(r)
        total = len(records)
        if paginate:
            records = records[
                (filters.page - 1) * filters.page_size : filters.page
                * filters.page_size
            ]
        return records, total
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(
        date_col,
        getattr(
            model, "item_id", model.warehouse_id if model is RouteForecast else model.id
        ),
        model.id,
    )
    if paginate:
        query = query.offset((filters.page - 1) * filters.page_size).limit(
            filters.page_size
        )
    output = []
    for row in session.scalars(query):
        r = {col.name: getattr(row, col.name) for col in row.__table__.columns}
        r.pop("run_id", None)
        if "item_id" in r:
            info = items[r["item_id"]]
            r.update(
                {
                    k: info[k]
                    for k in [
                        "warehouse_id",
                        "sku",
                        "product_type",
                        "destination_country",
                        "carrier",
                    ]
                }
            )
        w = warehouses.get(r.get("warehouse_id"))
        r["city"] = w["city"] if w else None
        if w:
            r.update(destination_country=w["destination_country"], carrier=w["carrier"])
        p = policies.get(r.get("policy_id"))
        if p:
            r.update(
                supplier_id=p["supplier_id"],
                configured_rop_floor=p["configured_rop_floor"],
                moq=p["moq"],
                safety_days=float(p["safety_days"]),
                policy_version=p["version"],
            )
        if model is InventoryDaily:
            r["eta_if_ordered"] = (
                r["date"] + timedelta(days=7) if r["recommended_qty"] else None
            )
        output.append(r)
    return output, total


def result_response(request, key, name, filters):
    with request.app.state.sessions() as s:
        run = required_run(s, key, complete=True)
        if name in {"route_forecasts", "item_forecasts"} and run.kind != "forecast":
            run = (
                required_run(s, run.forecast_run_id, "forecast", complete=True)
                if run.forecast_run_id
                else run
            )
        records, total = dataset(s, run, name, filters)
        return dict(
            context=context(run),
            items=records,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )


@router.get("/{key}/forecasts/routes")
def routes(key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]):
    return result_response(request, key, "route_forecasts", filters)


@router.get("/{key}/forecasts/items")
def item_forecasts(
    key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]
):
    return result_response(request, key, "item_forecasts", filters)


@router.get("/{key}/inventory")
def inventory(key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]):
    return result_response(request, key, "inventory_daily", filters)


@router.get("/{key}/replenishments")
def replenishments(
    key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]
):
    return result_response(request, key, "replenishments", filters)


@router.get("/{key}/alerts")
def alerts(key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]):
    return result_response(request, key, "alerts", filters)


@router.get("/{key}/alert-opportunities")
def alert_opportunities(
    key: uuid.UUID, request: Request, filters: Annotated[WholeRun, Query()]
):
    with request.app.state.sessions() as session:
        run = required_run(session, key, "alert_replay", complete=True)
        cases = (
            session.execute(
                select(
                    Alert.as_of_date,
                    Alert.actual_depletion_date,
                    Alert.predicted_depletion_date,
                    Alert.is_evaluable,
                ).where(Alert.run_id == key, Alert.alert_type == "depletion")
            )
            .mappings()
            .all()
        )
        try:
            diagnostic = opportunity_breakdown(cases)
        except ValueError:
            raise DomainError(
                "verification_failed", "Invalid replay event window", 409
            ) from None
        official = run.result_summary.get("alert_metrics", {})
        if any(
            official.get(k) != diagnostic[v]
            for k, v in [
                ("early_numerator", "observed_early_numerator"),
                ("event_denominator", "event_denominator"),
                ("excluded_count", "excluded_count"),
            ]
        ):
            raise DomainError(
                "verification_failed",
                "Replay diagnostic differs from verified summary",
                409,
            )
        return dict(context=context(run), diagnostic=diagnostic)


def allocated_metrics(session, run):
    cache_key = (str(session.bind.url), str(run.id), run.config_sha256)
    if cache_key in _ALLOCATED_METRICS:
        return _ALLOCATED_METRICS[cache_key]
    sql = text("""SELECT i.warehouse_id,f.as_of_date,f.target_date,f.horizon_day,SUM(f.forecast_qty) AS forecast_qty
        FROM item_forecasts f JOIN items i ON i.id=f.item_id WHERE f.run_id=:run GROUP BY i.warehouse_id,f.as_of_date,f.target_date,f.horizon_day""")
    frame = pd.read_sql(
        sql,
        session.connection(),
        params={"run": run.id},
        parse_dates=["as_of_date", "target_date"],
    )
    source = required_run(
        session, run.source_import_run_id, "source_import", complete=True
    )
    actual = pd.read_sql(
        text("""SELECT i.warehouse_id,d.date,SUM(d.sales_qty) AS actual_qty,BOOL_AND(d.actual_available) AS actual_available
        FROM daily_sales d JOIN items i ON i.id=d.item_id WHERE d.source_import_run_id=:run GROUP BY i.warehouse_id,d.date"""),
        session.connection(),
        params={"run": source_data_id(source)},
        parse_dates=["date"],
    )
    frame = frame.merge(
        actual,
        left_on=["warehouse_id", "target_date"],
        right_on=["warehouse_id", "date"],
        how="left",
        validate="many_to_one",
    )
    frame["actual_qty"] = frame.actual_qty.where(frame.actual_available.eq(True))
    output = []
    for split, start, end in [
        ("validation", "2025-06-30", "2025-09-30"),
        ("test", "2025-09-30", "2025-12-31"),
    ]:
        period = frame.loc[
            frame.as_of_date.ge(start)
            & frame.as_of_date.lt(end)
            & frame.target_date.le(end)
        ].copy()
        period["block"] = np.where(period.horizon_day.le(7), 1, 2)
        for (warehouse, block), part in period.groupby(["warehouse_id", "block"]):
            for cadence in ["daily_origins", "nonoverlapping_7d"]:
                subset = (
                    part
                    if cadence == "daily_origins"
                    else part.loc[
                        (part.as_of_date - pd.Timestamp(start)).dt.days.mod(7).eq(0)
                    ]
                )
                if subset.empty:
                    continue
                output.append(
                    dict(
                        warehouse_id=int(warehouse),
                        block=int(block),
                        split=split,
                        cadence=cadence,
                        granularity="allocated_daily",
                        **score(subset),
                    )
                )
    warehouses, _, _ = snapshot_maps(session, run)
    result = clean_json(
        [
            {
                **r,
                "destination_country": warehouses[r["warehouse_id"]][
                    "destination_country"
                ],
                "carrier": warehouses[r["warehouse_id"]]["carrier"],
            }
            for r in output
        ]
    )
    if len(_ALLOCATED_METRICS) >= 4:
        _ALLOCATED_METRICS.pop(next(iter(_ALLOCATED_METRICS)))
    _ALLOCATED_METRICS[cache_key] = result
    return result


def metric_records(session, run, filters):
    if filters.granularity == "allocated_daily":
        if run.kind != "forecast":
            run = required_run(session, run.forecast_run_id, "forecast", complete=True)
        records = allocated_metrics(session, run)
    else:
        records = run.result_summary.get("metrics", [])
        warehouses, _, _ = snapshot_maps(session, run)
        routes = {
            (w["destination_country"], w["carrier"]): w["id"]
            for w in warehouses.values()
        }
        records = [
            {
                **r,
                "warehouse_id": r.get("warehouse_id")
                or routes.get((r.get("destination_country"), r.get("carrier"))),
                "granularity": r.get("granularity", "weekly"),
            }
            for r in records
        ]
    for name in ["warehouse_id", "block", "cadence", "granularity", "split"]:
        value = getattr(filters, name)
        if value is not None:
            records = [r for r in records if r.get(name) == value]
    return records


@router.get("/{key}/metrics")
def metrics(key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]):
    with request.app.state.sessions() as s:
        run = required_run(s, key, complete=True)
        records = metric_records(s, run, filters)
        return dict(
            context=context(run),
            items=records[
                (filters.page - 1) * filters.page_size : filters.page
                * filters.page_size
            ],
            total=len(records),
            page=filters.page,
            page_size=filters.page_size,
        )


@router.get("/{key}/exports/{name}")
def exports(
    key: uuid.UUID, name: str, request: Request, filters: Annotated[Filters, Query()]
):
    allowed = {
        "route_forecasts": "route_forecasts",
        "item_forecasts": "item_forecasts",
        "inventory_daily": "inventory_daily",
        "replenishments": "replenishments",
        "alerts": "alerts",
        "metrics": "metrics",
    }
    if name not in allowed:
        raise DomainError("not_found", "Unknown export dataset", 404)
    with request.app.state.sessions() as s:
        run = required_run(s, key, complete=True)
        first = filters.model_copy(update={"page": 1, "page_size": 5000})
        rows = (
            metric_records(s, run, filters)
            if name == "metrics"
            else dataset(s, run, allowed[name], first)[0]
        )
        metadata = context(run)
        metadata.update(
            source_sha256=run.source_sha256,
            config_sha256=run.config_sha256,
            selection_sha256=run.selection_sha256,
        )

    def lines():
        fields = sorted({k for row in rows for k in row} | set(metadata))
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        yield "\ufeff" + stream.getvalue()
        stream.seek(0)
        stream.truncate(0)
        page = 1
        batch = rows
        while batch:
            for row in batch:
                values = {**metadata, **row}
                for k, v in values.items():
                    if isinstance(v, (dict, list)):
                        v = json.dumps(v, ensure_ascii=False, default=str)
                    if isinstance(v, str) and v.startswith(
                        ("=", "+", "-", "@", "\t", "\r")
                    ):
                        v = "'" + v
                    values[k] = v
                writer.writerow(values)
                yield stream.getvalue()
                stream.seek(0)
                stream.truncate(0)
            if name == "metrics" or len(batch) < 5000:
                break
            page += 1
            with request.app.state.sessions() as s:
                current = required_run(s, key, complete=True)
                batch = dataset(
                    s,
                    current,
                    allowed[name],
                    filters.model_copy(update={"page": page, "page_size": 5000}),
                )[0]

    import json

    return StreamingResponse(
        lines(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="sigma_{name}_{key}_{run.as_of_date}.csv"'
        },
    )
