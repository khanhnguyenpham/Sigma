"""Provider product restrictions and combined rights on an explicit frozen scope."""
from urllib.parse import urlsplit

from core.errors import DomainError
from modules.catalog.supply import day, supply_state

SIMULATED_PROVIDER_SOURCE = "Mô phỏng kiểm thử luồng ngừng cung cấp."


def provider_event_values(*, action, known_on, effective_on, reason, source_description=SIMULATED_PROVIDER_SOURCE,
                          target_event_id=None, source_ref=None):
    values = dict(action=action, known_on=day(known_on), effective_on=day(effective_on),
                  target_event_id=target_event_id)
    for key, value in (("reason", reason), ("source_description", source_description)):
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 1000:
            raise DomainError("invalid_input", "Reason and declared source are required")
        values[key] = value.strip()
    if target_event_id is not None and (type(target_event_id) is not int or target_event_id < 1):
        raise DomainError("invalid_input", "A positive target event ID is required")
    if source_ref is not None:
        if not isinstance(source_ref, str) or not source_ref or len(source_ref) > 2048 or any(c.isspace() for c in source_ref):
            raise DomainError("invalid_input", "Invalid source reference")
        try:
            url = urlsplit(source_ref)
            valid = url.scheme in {"http", "https"} and url.hostname and not url.username and not url.password
        except ValueError:
            valid = False
        if not valid:
            raise DomainError("invalid_input", "Source link must use HTTP or HTTPS without credentials")
    values["source_ref"] = source_ref
    return values


def validate_provider_change(events, *, action, known_on, effective_on, target_event_id=None):
    known, effective = day(known_on), day(effective_on)
    rows = sorted(events, key=lambda r: r["version"])
    if action not in {"stop", "cancel_stop", "resume_supply"}:
        raise DomainError("invalid_input", "Unknown provider action")
    if not rows:
        if action != "stop" or target_event_id is not None:
            raise DomainError("provider_conflict", "A notice must start with a stop", 409)
        return
    if len(rows) != 1 or rows[0]["action"] != "stop" or rows[0]["version"] != 1:
        raise DomainError("provider_conflict", "This notice already has a follow-up event", 409)
    stop = rows[0]
    if known < day(stop["known_on"]):
        raise DomainError("provider_conflict", "Known dates cannot move backwards", 409)
    if action == "stop" or target_event_id != stop["id"]:
        raise DomainError("provider_conflict", "Follow-up must target this notice's stop", 409)
    if action == "cancel_stop":
        if effective != known or known >= day(stop["effective_on"]):
            raise DomainError("provider_conflict", "Only a not-yet-effective notice can be cancelled", 409)
    elif effective < known or known < day(stop["effective_on"]):
        raise DomainError("provider_conflict", "Resume requires an effective stop and cannot be backdated", 409)


def provider_notice_state(events, decision_origin, target_date=None):
    origin = day(decision_origin)
    target = origin if target_date is None else day(target_date)
    if target < origin:
        raise DomainError("invalid_input", "Target cannot precede decision origin")
    rows = sorted((r for r in events if day(r["known_on"]) <= origin), key=lambda r: r["version"])
    prefix = []
    for row in rows:
        if row["version"] != len(prefix) + 1:
            raise DomainError("invalid_provider_history", "Provider event versions are not contiguous", 409)
        validate_provider_change(prefix, action=row["action"], known_on=row["known_on"],
                                 effective_on=row["effective_on"], target_event_id=row["target_event_id"])
        prefix.append(row)
    stop = rows[0] if rows else None
    follow = rows[1] if len(rows) == 2 else None
    status = "clear"
    resume_on = None
    if stop and not (follow and follow["action"] == "cancel_stop"):
        if target < day(stop["effective_on"]):
            status = "scheduled_stop"
        else:
            status = "stopped"
            if follow:
                resume_on = day(follow["effective_on"])
                status = "clear" if target >= resume_on else "scheduled_resume"
    allowed = status not in {"stopped", "scheduled_resume"}
    return dict(provider_status=status, sales_allowed=allowed,
                stop_on=day(stop["effective_on"]) if stop else None, resume_on=resume_on,
                stop_event_id=stop["id"] if stop else None, version=rows[-1]["version"] if rows else 0,
                reason=stop.get("reason") if stop else None,
                source_description=stop.get("source_description") if stop else None)


def trade_state(internal_changes, notices, item_id, decision_origin, target_date=None):
    internal = supply_state(internal_changes, item_id, decision_origin, target_date)
    restrictions = []
    for notice in sorted(notices, key=lambda r: r["id"]):
        if item_id not in notice["item_ids"]:
            continue
        state = provider_notice_state(notice["events"], decision_origin, target_date)
        if state["provider_status"] != "clear":
            restrictions.append(dict(notice_id=notice["id"], supplier_id=notice["supplier_id"], **state))
    blockers = [r for r in restrictions if not r["sales_allowed"]]
    status = ("stopped" if any(r["provider_status"] == "stopped" for r in blockers)
              else "scheduled_resume" if blockers else "scheduled_stop" if restrictions else "clear")
    stop = next((r for r in internal_changes if r["item_id"] == item_id and r["id"] == internal["stop_change_id"]), None)
    return dict(internal_status=internal["supply_status"], internal_reason=stop.get("reason") if stop else None,
                internal_stop_change_id=internal["stop_change_id"], internal_version=internal["version"],
                provider_status=status, provider_blockers=blockers, provider_restrictions=restrictions,
                sales_allowed=not blockers,
                replenishment_allowed=internal["replenishment_allowed"] and not blockers)


def resolve_provider_scope(catalog, supplier_id, scope_definition):
    """Expand product-wide requests; retain explicit scopes stored by older notices."""
    if type(supplier_id) is not int or supplier_id < 1:
        raise DomainError("invalid_input", "A supplier is required")
    if not isinstance(scope_definition, dict) or set(scope_definition) != {"products"}:
        raise DomainError("invalid_input", "An explicit products scope is required")
    products = scope_definition["products"]
    if not isinstance(products, list) or not products:
        raise DomainError("invalid_input", "The product scope cannot be empty")
    normalized, members = [], set()
    for product in products:
        if not isinstance(product, dict) or set(product) not in (
            {"sku", "product_type"}, {"sku", "product_type", "destination_countries", "warehouse_ids"}
        ):
            raise DomainError("invalid_input", "A product and type are required")
        sku, kind = product["sku"], product["product_type"]
        if (not isinstance(sku, str) or not sku.strip() or sku != sku.strip()
            or not isinstance(kind, str) or kind not in {"eSIM", "physical_SIM"}):
            raise DomainError("invalid_input", "Invalid product scope")
        if set(product) == {"sku", "product_type"}:
            matches = [r for r in catalog if r["supplier_id"] == supplier_id and r["sku"] == sku
                       and r["product_type"] == kind]
            if not matches:
                raise DomainError("invalid_input", "This supplier's product does not exist")
            product = dict(product, destination_countries=sorted({r["destination_country"] for r in matches}),
                           warehouse_ids=sorted({r["warehouse_id"] for r in matches}))
        countries, warehouses = product["destination_countries"], product["warehouse_ids"]
        if (not isinstance(sku, str) or not sku.strip() or sku != sku.strip()
            or not isinstance(kind, str) or kind not in {"eSIM", "physical_SIM"}
            or not isinstance(countries, list) or not countries
            or any(not isinstance(c, str) or not c.strip() or c != c.strip() for c in countries)
            or not isinstance(warehouses, list) or not warehouses
            or any(type(w) is not int or w < 1 for w in warehouses)):
            raise DomainError("invalid_input", "Invalid product scope")
        countries, warehouses = sorted(set(countries)), sorted(set(warehouses))
        matches = [r for r in catalog if r["supplier_id"] == supplier_id and r["sku"] == sku
                   and r["product_type"] == kind and r["destination_country"] in countries
                   and r["warehouse_id"] in warehouses]
        if {r["warehouse_id"] for r in matches} != set(warehouses) or {r["destination_country"] for r in matches} != set(countries):
            raise DomainError("invalid_input", "Every declared warehouse and market must contain this supplier's product")
        entry = dict(sku=sku, product_type=kind, destination_countries=countries, warehouse_ids=warehouses)
        if entry not in normalized:
            normalized.append(entry)
        members.update(r["id"] for r in matches)
    normalized.sort(key=lambda r: (r["sku"], r["product_type"], r["destination_countries"], r["warehouse_ids"]))
    return dict(products=normalized), sorted(members)
