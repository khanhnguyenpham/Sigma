"""HTTP result tables, diagnostics and streaming CSV exports."""
import csv, io, uuid
from typing import Annotated
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from core.run_context import required_run
from core.errors import DomainError
from modules.reporting.schemas import Filters
from modules.reporting.service import context, dataset, metric_records

router = APIRouter(prefix="/api/v1/runs")

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
