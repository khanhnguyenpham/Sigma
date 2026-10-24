"""Read-only purchasing workbench over frozen M3 inventory and receipt runs."""

import csv
import io
from typing import Annotated, Literal
import uuid
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import Field
from sigma_m3.api.workspace import WorkspaceFilters
from sigma_m3.api.results import Filters, context, dataset
from sigma_m3.core.errors import DomainError
from sigma_m3.services.forecast import clean_json
from sigma_m3.core.run_context import required_run

router = APIRouter(prefix="/api/v1/runs")


class PurchasingFilters(WorkspaceFilters):
    view: Literal["recommendations", "incoming", "history"] = "recommendations"
    search: str = Field(default="", max_length=80)
    sort: Literal["quantity_desc", "quantity_asc", "eta_asc", "ordered_desc"] = (
        "quantity_desc"
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


def purchasing_data(session, key, filters):
    run = required_run(session, key, complete=True)
    if run.kind not in {"stock_projection", "policy_replay", "alert_replay"}:
        raise DomainError("parent_mismatch", "Choose an inventory plan", 409)
    day = filters.as_of_date
    base = Filters(
        **filters.model_dump(
            include={"warehouse_id", "item_id", "supplier_id", "product_type"}
        )
    )
    inventory, _ = dataset(
        session,
        run,
        "inventory_daily",
        base.model_copy(update={"date_from": day, "date_to": day}),
        paginate=False,
    )
    lots, _ = dataset(session, run, "replenishments", base, paginate=False)
    recorded_end = (
        run.as_of_date
        if run.kind == "stock_projection"
        else run.period_end or run.as_of_date
    )
    known_on = min(day, recorded_end)
    words = filters.search.casefold().split()

    def matches(row):
        haystack = " ".join(
            str(row.get(k, ""))
            for k in ["sku", "product_type", "carrier", "destination_country"]
        ).casefold()
        return all(word in haystack for word in words)

    inventory = [row for row in inventory if matches(row)]
    recommendations = [
        {**row, "operational_status": "low_stock"}
        for row in inventory
        if row["needs_replenishment"] and row["recommended_qty"] > 0
    ]
    history = []
    for row in lots:
        if row["ordered_on"] > known_on or not matches(row):
            continue
        # Final replay status must not expose a later receipt at an earlier date.
        received = row["eta"] <= known_on and row["received_qty"] > 0
        history.append(
            {
                **row,
                "status": "received" if received else "ordered",
                "received_qty": row["received_qty"] if received else 0,
            }
        )
    incoming = [row for row in history if row["eta"] > known_on]
    summary = dict(
        inventory_available=bool(inventory),
        recommended_items=len(recommendations),
        recommended_units=sum(row["recommended_qty"] for row in recommendations),
        incoming_lots=len(incoming),
        pending_units=sum(row["ordered_qty"] for row in incoming),
        historical_lots=len(history),
    )
    rows = {
        "recommendations": recommendations,
        "incoming": incoming,
        "history": history,
    }[filters.view]
    quantity = "recommended_qty" if filters.view == "recommendations" else "ordered_qty"
    eta = "eta_if_ordered" if filters.view == "recommendations" else "eta"
    if filters.sort == "ordered_desc":
        if filters.view == "recommendations":
            raise DomainError(
                "invalid_input", "Order-date sorting requires receipt lots"
            )
        rows.sort(key=lambda row: (row["ordered_on"], row["id"]), reverse=True)
    elif filters.sort == "eta_asc":
        rows.sort(
            key=lambda row: (
                row.get(eta) is None,
                str(row.get(eta)),
                row["item_id"],
                row["id"],
            )
        )
    else:
        direction = -1 if filters.sort == "quantity_desc" else 1
        rows.sort(
            key=lambda row: (direction * row[quantity], row["item_id"], row["id"])
        )
    return dict(
        context={
            **context(run),
            "view_date": day.isoformat(),
            "known_orders_through": known_on.isoformat(),
            "view": filters.view,
            "search": filters.search,
            "sort": filters.sort,
        },
        summary=summary,
        items=rows,
        total=len(rows),
    )


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
