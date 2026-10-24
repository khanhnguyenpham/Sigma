from sqlalchemy import select
from core.errors import DomainError
from core.http import listing
from core.run_context import required_run, snapshot_maps
from modules.catalog.models import Warehouse, Item


def list_warehouses(sessions, page, page_size, country, run_id):
    if run_id:
        with sessions() as s:
            run = required_run(s, run_id, complete=True)
            rows = list(snapshot_maps(s, run)[0].values())
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
