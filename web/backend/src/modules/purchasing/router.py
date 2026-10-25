"""Read-only purchasing workbench over frozen M3 inventory and receipt runs."""

import csv
import io
from typing import Annotated
import uuid
from fastapi import APIRouter, Query, Request
from modules.reporting.router import result_response
from fastapi.responses import StreamingResponse
from core.serialization import clean_json
from modules.purchasing.schemas import PurchasingFilters
from modules.reporting.schemas import Filters
from modules.purchasing.service import purchasing_data

router = APIRouter(prefix="/api/v1/runs")


@router.get("/{key}/purchasing")
def purchasing(
    request: Request, key: uuid.UUID, filters: Annotated[PurchasingFilters, Query()]
):
    with request.app.state.sessions() as session:
        result = purchasing_data(session, key, filters)
        start = (filters.page - 1) * filters.page_size
        result["items"] = result["items"][start : start + filters.page_size]
        return clean_json(
            {**result, "page": filters.page, "page_size": filters.page_size}
        )


@router.get("/{key}/purchasing/export")
def export(
    request: Request, key: uuid.UUID, filters: Annotated[PurchasingFilters, Query()]
):
    with request.app.state.sessions() as session:
        result = purchasing_data(session, key, filters)
    metadata = {**result["context"], "run_status": result["context"]["status"]}
    rows = result["items"]
    fields = sorted(set(metadata) | {k for row in rows for k in row})

    def lines():
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        yield "\ufeff" + stream.getvalue()
        stream.seek(0)
        stream.truncate(0)
        for row in rows:
            values = {**metadata, **row}
            for field, value in values.items():
                if isinstance(value, str) and value.startswith(
                    ("=", "+", "-", "@", "\t", "\r")
                ):
                    values[field] = "'" + value
            writer.writerow(values)
            yield stream.getvalue()
            stream.seek(0)
            stream.truncate(0)

    return StreamingResponse(
        lines(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="sigma_purchasing_{filters.view}_{key}_{filters.as_of_date}.csv"'
        },
    )


@router.get("/{key}/replenishments")
def replenishments(
    key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]
):
    return result_response(request, key, "replenishments", filters)
