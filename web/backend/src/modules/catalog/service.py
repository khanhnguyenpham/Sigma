from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from collections import defaultdict
from core.errors import DomainError
from core.http import listing
from core.run_context import required_run, snapshot_maps
from modules.catalog.models import Warehouse, Item, Supplier, ItemSupplyChange
from modules.catalog.supply import supply_state
from modules.catalog.supply_service import supply_rows, supply_schema_ready, require_supply_schema
from modules.configuration.models import Policy
from core.http import record
from modules.catalog.locations import display_warehouse


def list_warehouses(sessions, page, page_size, country, run_id):
    if run_id:
        with sessions() as s:
            run = required_run(s, run_id, complete=True)
            rows = list(warehouse_labels(s, snapshot_maps(s, run)[0]).values())
            if country:
                rows = [r for r in rows if r["destination_country"] == country]
            return dict(
                items=rows[(page - 1) * page_size : page * page_size],
                total=len(rows),
                page=page,
                page_size=page_size,
            )
    return listing(
        sessions,
        Warehouse,
        page,
        page_size,
        [Warehouse.destination_country == country] if country else [],
    )


def warehouse_labels(session, warehouses):
    """Keep frozen locations and expose the current warehouse name separately."""
    current = dict(session.execute(select(Warehouse.id, Warehouse.city).where(Warehouse.id.in_(warehouses))).all())
    return {key: {**display_warehouse(w), "display_city": current.get(key, display_warehouse(w)["city"])}
            for key, w in warehouses.items()}


def get_warehouse(session, key):
    row = session.get(Warehouse, key)
    if row is None:
        raise DomainError("not_found", "Warehouse does not exist", 404)
    return record(row)


def list_products(sessions, page=1, page_size=50, warehouse_id=None, product_type=None, search=None, item_id=None,
                  as_of_date=None, supply_status=None, internal_status=None, provider_status=None,
                  replenishment_allowed=None, sales_allowed=None):
    new_filters = any(v is not None for v in (internal_status, provider_status, replenishment_allowed, sales_allowed))
    if (supply_status or new_filters) and as_of_date is None:
        raise DomainError("invalid_input", "Status and rights filtering require as_of_date")
    latest = (select(Policy.id).where(Policy.item_id == Item.id)
              .order_by(Policy.version.desc()).limit(1).correlate(Item).scalar_subquery())
    query = (select(Item, Warehouse, Supplier.id, Policy)
             .join(Warehouse, Warehouse.id == Item.warehouse_id)
             .join(Supplier, Supplier.carrier == Warehouse.carrier)
             .outerjoin(Policy, Policy.id == latest))
    if warehouse_id:
        query = query.where(Item.warehouse_id == warehouse_id)
    if product_type:
        query = query.where(Item.product_type == product_type)
    if search:
        query = query.where(Item.sku.icontains(search, autoescape=True))
    if item_id:
        query = query.where(Item.id == item_id)
    from modules.catalog.trade_service import trade_schema_ready, require_trade_schema, live_rights
    with sessions() as session:
        ready = supply_schema_ready(session)
        trade_ready = trade_schema_ready(session)
        if new_filters:
            require_trade_schema(session)
        if as_of_date is not None:
            require_supply_schema(session)
        if supply_status:
            stop, resolution = aliased(ItemSupplyChange), aliased(ItemSupplyChange)
            resolved = select(resolution.id).where(resolution.target_change_id == stop.id,
                resolution.known_on <= as_of_date).correlate(stop).exists()
            pending = select(stop.id).where(stop.item_id == Item.id, stop.action == "stop",
                stop.known_on <= as_of_date, ~resolved)
            if supply_status == "stopped":
                pending = pending.where(stop.effective_on <= as_of_date)
            elif supply_status == "scheduled_stop":
                pending = pending.where(stop.effective_on > as_of_date)
            predicate = pending.correlate(Item).exists()
            query = query.where(~predicate if supply_status == "active" else predicate)
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        query = query.order_by(Item.id)
        if not new_filters:
            query = query.offset((page-1)*page_size).limit(page_size)
        rows = session.execute(query).all()
        ids = [r[0].id for r in rows]
        histories = defaultdict(list)
        flat = supply_rows(session, ids) if ready else []
        for change in flat:
            histories[change["item_id"]].append(change)
        rights = live_rights(session, ids, as_of_date, histories=flat) if trade_ready else {}
        output = []
        for item, warehouse, supplier, policy in rows:
            history = histories[item.id]
            state = supply_state(history, item.id, as_of_date) if as_of_date else None
            info = rights.get(item.id, dict(internal_status=state["supply_status"] if state else None,
                provider_status=None, replenishment_allowed=None, sales_allowed=None,
                provider_blockers=[], provider_restrictions=[], provider_notice_ids=[], provider_versions={}))
            if any(value is not None and info[field] != value for field, value in (
                ("internal_status", internal_status), ("provider_status", provider_status),
                ("replenishment_allowed", replenishment_allowed), ("sales_allowed", sales_allowed))):
                continue
            output.append({**record(item), **info, "trade_schema_ready": trade_ready,
                "supply_status": state["supply_status"] if state else None,
                "stop_on": state["stop_on"] if state else None,
                "supply_version": (history[-1]["version"] if history else 0) if ready else None,
                "supply_schema_ready": ready, "item_id": item.id, "warehouse": record(warehouse),
                "city": warehouse.city, "destination_country": warehouse.destination_country,
                "carrier": warehouse.carrier, "supplier_id": supplier, "policy": record(policy) if policy else None})
        if new_filters:
            total = len(output)
            output = output[(page-1)*page_size:page*page_size]
        return dict(items=output, total=total, page=page, page_size=page_size)


def list_items(sessions, page, page_size, warehouse_id, product_type, run_id, search):
    if run_id:
        with sessions() as s:
            run = required_run(s, run_id, complete=True)
            rows = [{**v, "id": k} for k, v in snapshot_maps(s, run)[1].items()]
            if warehouse_id:
                rows = [r for r in rows if r["warehouse_id"] == warehouse_id]
            if product_type:
                rows = [r for r in rows if r["product_type"] == product_type]
            if search:
                rows = [r for r in rows if search.casefold() in r["sku"].casefold()]
            return dict(
                items=rows[(page - 1) * page_size : page * page_size],
                total=len(rows),
                page=page,
                page_size=page_size,
            )
    filters = []
    if warehouse_id:
        filters.append(Item.warehouse_id == warehouse_id)
    if product_type:
        filters.append(Item.product_type == product_type)
    if search:
        filters.append(Item.sku.icontains(search, autoescape=True))
    return listing(sessions, Item, page, page_size, filters)


def update_warehouse(session, key, request):
    row = session.scalar(
        select(Warehouse).where(Warehouse.id == key).with_for_update()
    )
    if row is None:
        raise DomainError("not_found", "Warehouse does not exist", 404)
    if row.version != request.expected_version:
        raise DomainError("version_conflict", "Warehouse changed; reload", 409)
    row.city = request.city
    row.version += 1
    session.flush()
    return row


def rename_seed_cities(session, apply=False):
    """Preview/apply the declared seed correction without modifying frozen runs."""
    warehouses = session.scalars(select(Warehouse).order_by(Warehouse.id).with_for_update()).all()
    names = []
    changes = []
    for warehouse in warehouses:
        row = {col.name: getattr(warehouse, col.name) for col in Warehouse.__table__.columns}
        renamed = display_warehouse(row) if warehouse.assumption_source == "route_city_seed_v1" else row
        names.append(renamed["city"].strip().casefold())
        if renamed["city"] != warehouse.city:
            changes.append(warehouse.id)
            if apply:
                warehouse.city = renamed["city"]
                warehouse.assumption_source = "route_city_seed_v2"
                warehouse.version += 1
    if len(set(names)) != len(names):
        raise ValueError("Warehouse locations still repeat; declare distinct locations before applying")
    session.flush()
    return {"warehouses": len(warehouses), "distinct_locations": len(set(names)),
            "renamed": len(changes), "applied": apply}
