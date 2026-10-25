"""R05 total-30 read model. No HTTP filesystem paths or model selection."""

import csv
import io
import json
import uuid
from typing import Annotated
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from modules.reporting.schemas import MonthlyFilters, SummaryFilters
from modules.reporting.service import context
from core.run_context import snapshot_maps
from core.run_context import required_run
from core.serialization import clean_json
from modules.reporting.monthly import load_package, benchmark_summary, ROUTE
from core.errors import DomainError

router = APIRouter(prefix="/api/v1/runs")


def package(session, request, key):
    run = required_run(session, key, complete=True)
    source = required_run(
        session, run.source_import_run_id or run.id, "source_import", complete=True
    )
    package_id, manifest, frames = load_package(request.app.state.settings, source)
    metadata = dict(
        context(run),
        benchmark_package_id=package_id,
        benchmark_run_id=manifest["benchmark_run_id"],
        source_sha256=manifest["source_sha256"],
        benchmark_source_import_run_id=manifest["source_import_run_id"],
        benchmark_summary_sha256=manifest["summary_sha256"],
        selection_sha256=manifest["selection_sha256"],
        acceptance_version=manifest["acceptance"]["version"],
        decision="M05",
        window_days=30,
        test_independent=False,
        evaluation_limit=manifest["evaluation_limit"],
        inventory_relationship=manifest["inventory_relationship"],
        verified_at_utc=manifest["verified_at_utc"],
    )
    warehouses, _, _ = snapshot_maps(session, source)
    routes = {
        (w["destination_country"], w["carrier"]): k for k, w in warehouses.items()
    }
    return metadata, frames, routes


def records(frames, routes, filters, name):
    frame = frames[name + ".csv"].copy()
    frame["warehouse_id"] = [routes.get(tuple(r)) for r in frame[ROUTE].to_numpy()]
    if frame.warehouse_id.isna().any():
        raise DomainError(
            "monthly_invalid", "Benchmark route missing from frozen source", 409
        )
    if filters.warehouse_id:
        frame = frame[frame.warehouse_id == filters.warehouse_id]
    if filters.top10_only:
        frame = frame[frame.is_top10]
    if filters.split:
        frame = frame[frame.split == filters.split]
    if name == "forecasts" and filters.as_of_date:
        frame = frame[frame.as_of_date == str(filters.as_of_date)]
    if name == "metrics":
        frame = frame[frame.cadence == filters.cadence]
    return clean_json(frame.to_dict("records"))


def result(request, key, filters, name):
    with request.app.state.sessions() as session:
        metadata, frames, routes = package(session, request, key)
        rows = records(frames, routes, filters, name)
    start = (filters.page - 1) * filters.page_size
    return dict(
        context=metadata,
        items=rows[start : start + filters.page_size],
        total=len(rows),
        page=filters.page,
        page_size=filters.page_size,
    )


@router.get("/{key}/monthly-forecasts")
def forecasts(
    request: Request, key: uuid.UUID, filters: Annotated[MonthlyFilters, Query()]
):
    return result(request, key, filters, "forecasts")


@router.get("/{key}/monthly-metrics")
def metrics(
    request: Request, key: uuid.UUID, filters: Annotated[MonthlyFilters, Query()]
):
    return result(request, key, filters, "metrics")


@router.get("/{key}/monthly-summary")
def summary(
    request: Request, key: uuid.UUID, filters: Annotated[SummaryFilters, Query()]
):
    with request.app.state.sessions() as session:
        metadata, frames, _ = package(session, request, key)
        return clean_json(
            dict(
                context=metadata,
                summary=benchmark_summary(
                    frames["metrics.csv"], frames["baselines.csv"]
                ),
            )
        )


def export(request, key, filters, name):
    with request.app.state.sessions() as session:
        metadata, frames, routes = package(session, request, key)
        rows = records(frames, routes, filters, name)
    fields = sorted(set(metadata) | {k for row in rows for k in row})
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        values = {**metadata, **row}
        for k, value in values.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str) and value.startswith(
                ("=", "+", "-", "@", "\t", "\r")
            ):
                value = "'" + value
            values[k] = value
        writer.writerow(values)
    return Response(
        "\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="sigma_monthly_{name}_{key}.csv"'
        },
    )


@router.get("/{key}/exports/monthly_forecasts")
def export_forecasts(
    request: Request, key: uuid.UUID, filters: Annotated[MonthlyFilters, Query()]
):
    return export(request, key, filters, "forecasts")


@router.get("/{key}/exports/monthly_metrics")
def export_metrics(
    request: Request, key: uuid.UUID, filters: Annotated[MonthlyFilters, Query()]
):
    return export(request, key, filters, "metrics")
