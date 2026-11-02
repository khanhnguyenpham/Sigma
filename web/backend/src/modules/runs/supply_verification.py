"""Supply reconciliation independent of catalog resolver and projection producer."""
from datetime import date, timedelta
from core.errors import DomainError


def fail():
    raise DomainError("verification_failed", "Frozen supply history or sell-through differs")


def verify_supply_snapshot(run):
    snap = run.config_snapshot
    profile = snap.get("supply_lifecycle_profile")
    if profile is None:
        if snap.get("supply_lifecycle_snapshot"):
            fail()
        return None
    if profile != "notice7_sellthrough_v1" or not isinstance(snap.get("supply_lifecycle_snapshot"), list):
        fail()
    cutoff = run.as_of_date
    if run.kind == "policy_replay":
        cutoff = run.period_end
    elif run.kind == "alert_replay":
        while cutoff + timedelta(days=28) <= run.period_end:
            cutoff += timedelta(days=14)
    catalog = {i["item_id"] for i in snap["catalog_snapshot"] if i["first_seen_date"] <= cutoff.isoformat()}
    histories, ids = {}, set()
    try:
        for row in snap["supply_lifecycle_snapshot"]:
            item = row["item_id"]
            if item not in catalog or type(row["id"]) is not int or row["id"] <= 0 or row["id"] in ids:
                fail()
            ids.add(row["id"])
            histories.setdefault(item, []).append(row)
        for history in histories.values():
            history.sort(key=lambda r: r["version"])
            previous, stop = date.min, None
            for version, row in enumerate(history, 1):
                known, effective = date.fromisoformat(row["known_on"]), date.fromisoformat(row["effective_on"])
                if (type(row["version"]) is not int or row["version"] != version or not previous <= known <= cutoff
                    or row["is_assumed"] is not True or row["assumption_source"] != "user_declared_supply_simulation_v1"
                    or not row["reason"].strip() or len(row["reason"]) > 1000):
                    fail()
                if row["action"] == "stop":
                    if stop or row["target_change_id"] is not None or (effective-known).days < 7:
                        fail()
                    stop = row
                else:
                    if stop is None or row["target_change_id"] != stop["id"] or effective != known:
                        fail()
                    stopped = known >= date.fromisoformat(stop["effective_on"])
                    if row["action"] != ("resume" if stopped else "cancel_stop"):
                        fail()
                    stop = None
                previous = known
    except (KeyError, TypeError, ValueError, AttributeError):
        fail()
    return histories


def supply_metadata(histories, item, origin, target, stock, pending, rop):
    if histories is None:
        return {}
    stop = None
    for row in histories.get(item, []):
        if row["known_on"] > origin.date().isoformat():
            continue
        stop = row if row["action"] == "stop" else None
    status = "active" if stop is None else "scheduled_stop" if target.date().isoformat() < stop["effective_on"] else "stopped"
    allowed = status != "stopped"
    return dict(supply_status=status, replenishment_allowed=allowed,
                replenishment_block_reason=None if allowed else "supply_stopped",
                stock_below_rop=stock < rop,
                sell_through_state=("selling_remaining" if stock > 0 else "waiting_receipts" if pending else "sold_out")
                    if not allowed else None)


def projection_path(histories, item, origin, stock, forecast, receipts):
    path = []
    for h, demand in enumerate(forecast, 1):
        target = origin + timedelta(days=h)
        received = receipts.get(target, 0)
        available = float(stock) + received
        sales = min(float(demand), available)
        stock = max(0.0, available-float(demand))
        row = dict(date=target.date().isoformat(), closing_forecast=stock, receipts_qty=received)
        if histories is not None:
            info = supply_metadata(histories, item, origin, target, stock, 0, 0)
            row.update(forecast_demand_qty=float(demand), projected_sales_qty=sales,
                       unserved_demand_qty=float(demand)-sales,
                       supply_status=info["supply_status"], replenishment_allowed=info["replenishment_allowed"])
        path.append(row)
    return path
