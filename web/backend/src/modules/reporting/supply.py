"""Supply read models use only the run snapshot and stored projection."""
from collections import defaultdict
from datetime import date
from sqlalchemy import select
from core.errors import DomainError
from modules.alerts.models import Alert
from modules.catalog.supply import supply_state


def frozen_history(run):
    profile = run.config_snapshot.get("supply_lifecycle_profile")
    if profile is None:
        return None
    rows = run.config_snapshot.get("supply_lifecycle_snapshot")
    if profile != "notice7_sellthrough_v1" or not isinstance(rows, list):
        raise DomainError("invalid_supply_history", "Unsupported frozen supply history", 409)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["item_id"]].append(row)
    return grouped


def supply_fields(run, histories, row, view_date=None):
    result = dict(supply_status=None, replenishment_allowed=True, replenishment_block_reason=None,
                  stock_below_rop=None, sell_through_state=None)
    if histories is None:
        return result
    if "closing_qty" in row:
        result["stock_below_rop"] = row["closing_qty"] < row["rop"] if row.get("rop") is not None else None
    target = row.get("date") or row.get("as_of_date") or view_date or row["ordered_on"]
    origin = (row["window_origin"] if run.kind == "alert_replay" else
              run.as_of_date if run.kind == "stock_projection" else row.get("forecast_as_of_date") or target)
    if "ordered_on" in row:
        if view_date is None:
            target = max(target, row["window_origin"])
        origin = min(origin, target, run.period_end or run.as_of_date)
    state = supply_state(histories.get(row["item_id"], []), row["item_id"], origin, target)
    result.update(supply_status=state["supply_status"], replenishment_allowed=state["replenishment_allowed"],
                  replenishment_block_reason=None if state["replenishment_allowed"] else "supply_stopped")
    if "closing_qty" in row and not state["replenishment_allowed"]:
        result["sell_through_state"] = ("selling_remaining" if row["closing_qty"] > 0 else
                                         "waiting_receipts" if row["pending_qty"] else "sold_out")
    if "explanation" in row:
        for name in ("stock_below_rop", "sell_through_state"):
            result[name] = row["explanation"].get(name)
    return result


def operational_rows(inventory, lots):
    """At a replay boundary show the newest window once per item."""
    latest = {}
    for row in inventory:
        if row["item_id"] not in latest or row["window_origin"] > latest[row["item_id"]]["window_origin"]:
            latest[row["item_id"]] = row
    lots = [r for r in lots if r["item_id"] not in latest or
            r["window_origin"] == latest[r["item_id"]]["window_origin"]]
    return list(latest.values()), lots


def sell_through_data(session, run, filters, items, warehouses, selected, paginate):
    if run.kind not in {"stock_projection", "policy_replay", "alert_replay"}:
        raise DomainError("parent_mismatch", "Sell-through requires an inventory plan", 409)
    if frozen_history(run) is None:
        raise DomainError("feature_not_in_run", "Create a new plan to view sell-through", 409)
    if any(getattr(filters, name) is not None for name in
           ("split", "block", "state", "alert_type", "granularity", "cadence")):
        raise DomainError("invalid_input", "Unsupported sell-through filter")
    origin = filters.as_of_date or run.as_of_date
    query = select(Alert).where(Alert.run_id == run.id, Alert.alert_type == "depletion",
                                Alert.as_of_date == origin, Alert.item_id.in_(selected)).order_by(Alert.item_id)
    rows = []
    # ponytail: materialize one H14 origin; use SQL JSON expansion if catalog size outgrows memory.
    for alert in session.scalars(query):
        path = alert.explanation.get("projection", [])
        required = {"forecast_demand_qty", "projected_sales_qty", "unserved_demand_qty", "supply_status", "replenishment_allowed"}
        if not isinstance(path, list) or len(path) != 14 or any(not isinstance(day, dict) or not required <= set(day) for day in path):
            raise DomainError("feature_not_in_run", "Create a new plan to view sell-through", 409)
        item = items[alert.item_id]
        warehouse = warehouses[item["warehouse_id"]]
        for horizon, projected in enumerate(path, 1):
            target = date.fromisoformat(projected["date"])
            if (filters.date_from and target < filters.date_from) or (filters.date_to and target > filters.date_to):
                continue
            rows.append(dict(item, city=warehouse["city"], display_city=warehouse["display_city"],
                as_of_date=origin, target_date=target, horizon_day=horizon,
                **{k:v for k,v in projected.items() if k != "date"}))
    if filters.aggregate == "route_day":
        groups = {}
        for row in rows:
            key = (row["warehouse_id"], row["target_date"])
            group = groups.setdefault(key, dict(warehouse_id=row["warehouse_id"], city=row["city"],
                display_city=row["display_city"], destination_country=row["destination_country"], carrier=row["carrier"],
                as_of_date=origin, target_date=row["target_date"], horizon_day=row["horizon_day"], item_count=0,
                stopped_items=0, **{k:0 for k in ("forecast_demand_qty", "projected_sales_qty", "unserved_demand_qty", "closing_forecast", "receipts_qty")}))
            group["item_count"] += 1
            group["stopped_items"] += row["supply_status"] == "stopped"
            for name in ("forecast_demand_qty", "projected_sales_qty", "unserved_demand_qty", "closing_forecast", "receipts_qty"):
                group[name] += row[name]
        rows = list(groups.values())
    rows.sort(key=lambda r:(r["target_date"],r["warehouse_id"],r.get("item_id",0)))
    total = len(rows)
    return (rows[(filters.page-1)*filters.page_size:filters.page*filters.page_size] if paginate else rows), total
