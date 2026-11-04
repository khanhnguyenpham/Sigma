"""Product defaults and frozen receiving locations; source identities stay intact."""
from datetime import date, timedelta
from sqlalchemy import inspect, select
from sqlalchemy.orm import undefer
from core.errors import DomainError
from core.http import record
from modules.catalog.models import Item, Warehouse

RECEIVING_PROFILE = "product_default_receiving_v1"


def receiving_schema_ready(session):
    inspector = inspect(session.connection())
    return {"receiving_warehouse_id", "receiving_version"} <= {
        c["name"] for c in inspector.get_columns("items")
    } and "receiving_warehouse_id" in {c["name"] for c in inspector.get_columns("replenishment_orders")}


def product_receiving(session, items):
    ready = receiving_schema_ready(session)
    defaults = {item.id: (None, 0) for item in items}
    if ready:
        defaults.update({key: (warehouse, version) for key, warehouse, version in session.execute(
            select(Item.id, Item.receiving_warehouse_id, Item.receiving_version).where(Item.id.in_(defaults)))})
    ids = {configured or item.warehouse_id for item in items for configured, _ in [defaults[item.id]]}
    warehouses = {w.id: record(w) for w in session.scalars(select(Warehouse).where(Warehouse.id.in_(ids)))}
    return {item.id: dict(receiving_warehouse_id=defaults[item.id][0] or item.warehouse_id,
        receiving_version=defaults[item.id][1], receiving_source="configured" if defaults[item.id][0] else "inherited",
        receiving_warehouse=warehouses[defaults[item.id][0] or item.warehouse_id], receiving_schema_ready=ready)
        for item in items}


def update_receiving(session, item_id, request):
    if not receiving_schema_ready(session):
        raise DomainError("receiving_schema_required", "Receiving warehouses require the database upgrade", 503)
    item = session.scalar(select(Item).options(undefer(Item.receiving_warehouse_id), undefer(Item.receiving_version))
        .where(Item.id == item_id).with_for_update().execution_options(populate_existing=True))
    if item is None:
        raise DomainError("not_found", "Product does not exist", 404)
    if item.receiving_version != request.expected_version:
        raise DomainError("version_conflict", "Receiving warehouse changed; reload before saving", 409)
    warehouse = session.scalar(select(Warehouse).where(Warehouse.id == request.receiving_warehouse_id).with_for_update(read=True))
    if warehouse is None:
        raise DomainError("not_found", "Receiving warehouse does not exist", 404)
    if (item.receiving_warehouse_id or item.warehouse_id) != warehouse.id:
        item.receiving_warehouse_id = warehouse.id
        item.receiving_version += 1
        session.flush()
    return dict(item_id=item.id, **product_receiving(session, [item])[item.id])


def frozen_receiving(snapshot):
    profile = snapshot.get("receiving_warehouse_profile")
    rows = snapshot.get("receiving_warehouse_snapshot")
    if profile is None and rows is None:
        return {}
    if profile != RECEIVING_PROFILE or not isinstance(rows, list):
        raise DomainError("invalid_receiving_snapshot", "Unsupported receiving warehouse snapshot", 409)
    result = {}
    try:
        warehouses = {w["id"]: w for w in snapshot["warehouse_snapshot"]}
        routes = {(w["destination_country"], w["carrier"]): w["id"] for w in warehouses.values()}
        catalog = {i["item_id"]: i for i in snapshot["catalog_snapshot"]}
        for row in rows:
            if set(row) != {"item_id", "source_warehouse_id", "receiving_warehouse_id", "receiving_version"}:
                raise ValueError
            key, source, target, version = (row[k] for k in
                ("item_id", "source_warehouse_id", "receiving_warehouse_id", "receiving_version"))
            item = catalog[key]
            if (any(type(v) is not int for v in (key, source, target, version)) or key in result
                or target <= 0 or target not in warehouses or source != routes[(item["destination_country"], item["carrier"])]
                or version < 0 or (version == 0 and source != target)):
                raise ValueError
            result[key] = row
        request = snapshot["request"]
        cutoff = date.fromisoformat(request["as_of_date"])
        if request["kind"] == "policy_replay":
            cutoff = date.fromisoformat(request["period_end"])
        elif request["kind"] == "alert_replay":
            end = date.fromisoformat(request["period_end"])
            cutoff += timedelta(days=max(0, ((end-cutoff).days//14-1)*14))
        elif request["kind"] != "stock_projection":
            raise ValueError
        if set(result) != {key for key, item in catalog.items() if date.fromisoformat(item["first_seen_date"]) <= cutoff}:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise DomainError("invalid_receiving_snapshot", "Frozen receiving locations are inconsistent", 409) from None
    return result


def location_fields(item, warehouses):
    """Expose both roles without overwriting source country/carrier or warehouse_id."""
    if "receiving_warehouse_id" not in item:
        return {}
    warehouse = warehouses[item["receiving_warehouse_id"]]
    return dict(source_warehouse_id=item["warehouse_id"], receiving_warehouse_id=warehouse["id"],
        source_city=warehouses[item["warehouse_id"]]["city"],
        receiving_version=item["receiving_version"], receiving_city=warehouse["city"],
        receiving_display_city=warehouse.get("display_city", warehouse["city"]),
        receiving_destination_country=warehouse["destination_country"])
