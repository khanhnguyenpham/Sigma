"""Operational read model. Every total follows the same frozen run/date/filter."""

from datetime import date
from typing import Annotated, Literal
import uuid
from fastapi import APIRouter, Query, Request
from pydantic import Field
from core.schemas import DTO
from core.errors import DomainError
from core.run_context import required_run
from api.results import Filters, context, dataset
from services.forecast import clean_json

router = APIRouter(prefix="/api/v1/runs")


class WorkspaceFilters(DTO):
    as_of_date: date
    warehouse_id: int | None = Field(default=None, gt=0)
    item_id: int | None = Field(default=None, gt=0)
    supplier_id: int | None = Field(default=None, gt=0)
    product_type: Literal["eSIM", "physical_SIM"] | None = None


@router.get("/{key}/workspace")
def workspace(
    request: Request, key: uuid.UUID, filters: Annotated[WorkspaceFilters, Query()]
):
    with request.app.state.sessions() as session:
        run = required_run(session, key, complete=True)
        if run.kind not in {"stock_projection", "policy_replay", "alert_replay"}:
            raise DomainError(
                "parent_mismatch", "Choose an inventory plan to view operations", 409
            )
        base = Filters(**filters.model_dump(exclude={"as_of_date"}))
        day = filters.as_of_date
        inventory, _ = dataset(
            session,
            run,
            "inventory_daily",
            base.model_copy(update={"date_from": day, "date_to": day}),
            paginate=False,
        )
        signals, _ = dataset(
            session,
            run,
            "alerts",
            base.model_copy(update={"as_of_date": day}),
            paginate=False,
        )
        lots, _ = dataset(session, run, "replenishments", base, paginate=False)
        # Replay rows cover their recorded period. A stock projection knows only
        # its origin; never infer actual receipts beyond that snapshot.
        recorded_end = (
            run.as_of_date
            if run.kind == "stock_projection"
            else run.period_end or run.as_of_date
        )
        known_on = min(day, recorded_end)
        incoming = [r for r in lots if r["ordered_on"] <= known_on < r["eta"]]
        low = [r for r in inventory if r.get("needs_replenishment")]
        action = sorted(
            [r for r in low if (r.get("recommended_qty") or 0) > 0],
            key=lambda r: (-(r.get("recommended_qty") or 0), r["item_id"]),
        )
        urgent = {
            r["item_id"]
            for r in signals
            if r["alert_type"] == "depletion"
            and r["state"] in {"urgent", "already_depleted"}
        }
        routes = {}
        for row in inventory:
            route = (row["destination_country"], row["carrier"])
            routes[route] = routes.get(route, 0) + row["closing_qty"]
        totals = dict(
            inventory_available=bool(inventory),
            item_count=len(inventory),
            on_hand_units=sum(r["closing_qty"] for r in inventory)
            if inventory
            else None,
            low_stock_items=len(low),
            replenish_items=len(action),
            urgent_items=len(urgent),
            incoming_lots=len(incoming),
            pending_units=sum(r["ordered_qty"] for r in incoming),
            recommended_units=sum(r["recommended_qty"] for r in action),
            healthy_items=sum(r.get("needs_replenishment") is False for r in inventory),
            route_count=len(routes),
        )
        route_stock = [
            dict(destination_country=k[0], carrier=k[1], closing_qty=v)
            for k, v in sorted(routes.items(), key=lambda pair: (-pair[1], pair[0]))
        ]
        return clean_json(
            dict(
                context={
                    **context(run),
                    "view_date": day.isoformat(),
                    "known_orders_through": known_on.isoformat(),
                },
                summary=totals,
                attention=action[:6],
                incoming=sorted(incoming, key=lambda r: (r["eta"], r["item_id"]))[:5],
                route_stock=route_stock[:8],
            )
        )
