"""Operational read model. Every total follows the same frozen run/date/filter."""

from typing import Annotated
import uuid
from fastapi import APIRouter, Query, Request
from modules.reporting.router import result_response
from modules.inventory.schemas import WorkspaceFilters
from core.errors import DomainError
from core.run_context import required_run
from modules.reporting.schemas import Filters
from modules.reporting.service import context, dataset
from core.serialization import clean_json
from modules.reporting.supply import operational_rows
from modules.reporting.trade import is_trade, counters, matches, RIGHT_FILTERS, validate_filters

router = APIRouter(prefix="/api/v1/runs")


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
        base = Filters(**filters.model_dump())
        validate_filters(run,base)
        if is_trade(run):base=base.model_copy(update={k:None for k in RIGHT_FILTERS})
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
        inventory, lots = operational_rows(inventory, lots)
        if is_trade(run):
            keys={(r['window_origin'],r['item_id']) for r in inventory}
            inventory=[r for r in inventory if matches(r,filters)]
            lots=[r for r in lots if matches(r,filters)]
            signals=[r for r in signals if matches(r,filters) and (r['window_origin'],r['item_id']) in keys]
        incoming = [r for r in lots if r["ordered_on"] <= known_on < r["eta"]]
        low = [r for r in inventory if r.get("stock_below_rop") is True or r.get("needs_replenishment")]
        action = sorted(
            [r for r in low if r.get("replenishment_allowed", True) and (r.get("recommended_qty") or 0) > 0],
            key=lambda r: (-(r.get("recommended_qty") or 0), r["item_id"]),
        )
        urgent = {
            r["item_id"]
            for r in signals
            if r["alert_type"] == "depletion"
            and r["state"] in {"urgent", "already_depleted"}
        }
        projected = {r["item_id"] for r in signals if r["alert_type"] == "projected_below_rop"}
        warnings = {r["item_id"] for r in signals if r["state"] != "not_within_horizon"}
        routes = {}
        warehouse_stock = {}
        for row in inventory:
            route = (row["destination_country"], row["carrier"])
            routes[route] = routes.get(route, 0) + row["closing_qty"]
            stock = warehouse_stock.setdefault(row["warehouse_id"], dict(
                warehouse_id=row["warehouse_id"], city=row["city"],
                destination_country=row["destination_country"], carrier=row["carrier"],
                item_count=0, on_hand_units=0, low_stock_items=0,
                replenish_items=0, recommended_units=0, supply_stopped_items=0,
            ))
            stock["item_count"] += 1
            stock["on_hand_units"] += row["closing_qty"]
            stock["low_stock_items"] += bool(row.get("stock_below_rop") or row.get("needs_replenishment"))
            stock["replenish_items"] += (row.get("recommended_qty") or 0) > 0
            stock["recommended_units"] += row.get("recommended_qty") or 0
            stock["supply_stopped_items"] += row.get("supply_status")=="stopped"
        totals = dict(
            inventory_available=bool(inventory),
            item_count=len(inventory),
            on_hand_units=sum(r["closing_qty"] for r in inventory)
            if inventory
            else None,
            low_stock_items=len(low),
            replenish_items=len(action),
            urgent_items=len(urgent),
            projected_below_rop_items=len(projected),
            warning_items=len(warnings),
            incoming_lots=len(incoming),
            pending_units=sum(r["ordered_qty"] for r in incoming),
            recommended_units=sum(r["recommended_qty"] for r in action),
            healthy_items=sum(r.get("needs_replenishment") is False and r.get("replenishment_allowed",True) and r.get("stock_below_rop") is not True and not r.get('cap_reason') for r in inventory),
            supply_stopped_items=sum(r.get("supply_status")=="stopped" for r in inventory),
            route_count=len(routes),
        )
        route_stock = [
            dict(destination_country=k[0], carrier=k[1], closing_qty=v)
            for k, v in sorted(routes.items(), key=lambda pair: (-pair[1], pair[0]))
        ]
        if is_trade(run):
            totals.update(counters(inventory))
            for stock in warehouse_stock.values():
                stock.update(counters([r for r in inventory if r['warehouse_id']==stock['warehouse_id']]))
            for stock in route_stock:
                stock.update(counters([r for r in inventory if (r['destination_country'],r['carrier'])==(stock['destination_country'],stock['carrier'])]))
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
                warehouse_stock=sorted(warehouse_stock.values(), key=lambda w: w["warehouse_id"]),
            )
        )


@router.get("/{key}/inventory")
def inventory(key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]):
    return result_response(request, key, "inventory_daily", filters)
