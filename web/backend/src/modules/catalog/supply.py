"""Pure supply timeline rules. No live reads or changes to inventory policy."""
from datetime import date, timedelta
from core.errors import DomainError


def day(value):
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise DomainError("invalid_input", "A UTC calendar date is required")


def supply_state(changes, item_id, decision_origin, target_date=None):
    """Resolve a frozen prefix; an announced future stop applies on its target day."""
    origin = day(decision_origin)
    target = origin if target_date is None else day(target_date)
    if target < origin:
        raise DomainError("invalid_input", "Target cannot precede decision origin")
    visible = sorted((r for r in changes if r["item_id"] == item_id and day(r["known_on"]) <= origin),
                     key=lambda r: r["version"])
    stop = None
    for row in visible:
        if row["action"] == "stop":
            stop = row
        elif row["action"] in {"cancel_stop", "resume"}:
            if stop is None or row["target_change_id"] != stop["id"]:
                raise DomainError("invalid_supply_history", "Supply target does not match active stop", 409)
            stop = None
        else:
            raise DomainError("invalid_supply_history", "Unknown supply action", 409)
    status = "active" if stop is None else "scheduled_stop" if target < day(stop["effective_on"]) else "stopped"
    return dict(supply_status=status, replenishment_allowed=status != "stopped",
                stop_change_id=stop["id"] if stop else None,
                stop_on=day(stop["effective_on"]) if stop else None,
                version=visible[-1]["version"] if visible else 0)


def validate_supply_change(changes, *, item_id, action, known_on, effective_on, target_change_id=None,
                           minimum_notice_days=7):
    """Validate a proposed append before the persistence service writes it."""
    known, effective = day(known_on), day(effective_on)
    rows = [r for r in changes if r["item_id"] == item_id]
    if rows and known < max(day(r["known_on"]) for r in rows):
        raise DomainError("supply_conflict", "Supply dates cannot move backwards", 409)
    if action not in {"stop", "cancel_stop", "resume"}:
        raise DomainError("invalid_input", "Unknown supply action")
    if minimum_notice_days not in (0, 7):
        raise DomainError("invalid_input", "Unsupported internal supply rules")
    if action == "stop":
        # Existing API/profile stays notice7 until the trade snapshot and worker cutover.
        if target_change_id is not None or effective - known < timedelta(days=minimum_notice_days):
            raise DomainError("invalid_input", "Stop date precedes the permitted internal effective date")
    elif target_change_id is None or effective != known:
        raise DomainError("invalid_input", "Cancel/resume requires a target and takes effect on known_on")
    state = supply_state(rows, item_id, known)
    if action == "stop":
        valid = state["supply_status"] == "active"
    else:
        valid = (state["stop_change_id"] == target_change_id and
                 state["supply_status"] == ("scheduled_stop" if action == "cancel_stop" else "stopped"))
    if not valid:
        raise DomainError("supply_conflict", "Supply transition is not allowed", 409)
