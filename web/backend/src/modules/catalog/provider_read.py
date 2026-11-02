"""Live management reads; run results do not call these functions."""
from sqlalchemy import select
from core.errors import DomainError
from modules.catalog.models import Item, Warehouse
from modules.catalog.provider import provider_notice_state
from modules.catalog.trade_service import require_trade_schema, provider_notices, live_rights


def notice_members(session, ids):
    return [dict(r) for r in session.execute(select(Item.id, Item.warehouse_id, Item.sku, Item.product_type,
        Warehouse.destination_country, Warehouse.carrier, Warehouse.city)
        .join(Warehouse, Warehouse.id == Item.warehouse_id).where(Item.id.in_(ids)).order_by(Item.id)).mappings()]


def notice_view(root, members, as_of_date):
    state = provider_notice_state(root["events"], as_of_date) if as_of_date else None
    return {**{k: v for k, v in root.items() if k not in {"item_ids", "events"}},
            "latest_version": root["events"][-1]["version"] if root["events"] else 0,
            "latest_action": root["events"][-1]["action"] if root["events"] else None,
            "latest_known_on": root["events"][-1]["known_on"] if root["events"] else None,
            "scope_items": len(root["item_ids"]), "scope_warehouses": len({r["warehouse_id"] for r in members}),
            "as_of_date": as_of_date, "state": state,
            "reason": root["events"][0]["reason"] if root["events"] else None,
            "source_description": root["events"][0]["source_description"] if root["events"] else None,
            "source_ref": root["events"][0]["source_ref"] if root["events"] else None, "is_assumed": True}


def list_notices(session, *, page=1, page_size=50, supplier_id=None, item_id=None, warehouse_id=None,
                 sku=None, product_type=None, destination_country=None, status=None, as_of_date=None, search=None):
    require_trade_schema(session)
    if status is not None and as_of_date is None:
        raise DomainError("invalid_input", "Status filtering requires as_of_date")
    roots = provider_notices(session, [item_id] if item_id else None)
    all_ids = {i for root in roots for i in root["item_ids"]}
    members = notice_members(session, all_ids)
    output = []
    # ponytail: management history fits in memory; move status predicates to SQL if volume outgrows it.
    for root in roots:
        if supplier_id is not None and root["supplier_id"] != supplier_id:
            continue
        selected = [m for m in members if m["id"] in root["item_ids"]]
        matched = [m for m in selected if (item_id is None or m["id"] == item_id)
            and (warehouse_id is None or m["warehouse_id"] == warehouse_id)
            and (sku is None or m["sku"] == sku) and (product_type is None or m["product_type"] == product_type)
            and (destination_country is None or m["destination_country"] == destination_country)]
        if not matched:
            continue
        row = notice_view(root, selected, as_of_date)
        if status is not None and row["state"]["provider_status"] != status:
            continue
        if search and search.casefold() not in " ".join(
            [row["reason"] or "", row["source_description"] or ""] + [m["sku"] for m in matched]).casefold():
            continue
        output.append(row)
    output.reverse()
    return dict(items=output[(page-1)*page_size:page*page_size], total=len(output), page=page, page_size=page_size)


def get_notice(session, notice_id, as_of_date=None):
    require_trade_schema(session)
    roots = provider_notices(session, notice_id=notice_id)
    if not roots:
        raise DomainError("not_found", "Provider notice does not exist", 404)
    root = roots[0]
    return notice_view(root, notice_members(session, root["item_ids"]), as_of_date), root


def get_notice_items(session, notice_id, as_of_date, page, page_size):
    header, root = get_notice(session, notice_id, as_of_date)
    rows = notice_members(session, root["item_ids"])
    rights = live_rights(session, root["item_ids"], as_of_date)
    return dict(items=[dict(row, item_id=row["id"], **rights[row["id"]])
                      for row in rows[(page-1)*page_size:page*page_size]],
                total=len(rows), page=page, page_size=page_size, notice=header)
