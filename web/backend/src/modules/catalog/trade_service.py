"""Batch reads, consistent configuration locks and frozen trade snapshots."""
from collections import defaultdict

from sqlalchemy import inspect, select
from fastapi.encoders import jsonable_encoder
from core.errors import DomainError
from core.http import record
from modules.catalog.models import (Supplier, Warehouse, Item, ProviderProductNotice,
                                    ProviderProductNoticeItem, ProviderProductNoticeEvent)
from modules.catalog.provider import trade_state
from modules.catalog.supply_service import supply_rows

TRADE_PROFILE = "internal_provider_trade_v2"
TRADE_RULES = dict(version=2, calendar="UTC", policy_cutoff="rolling_day", alert_cutoff="window_origin",
                   stock_cutoff="as_of_date", order_limit="full_fixed_lot", coverage_required=True,
                   actual_blocking="known_effective_provider_only", metric_exclusion="whole_item_window")


def trade_schema_ready(session):
    inspector = inspect(session.connection())
    return all(inspector.has_table(t) for t in (
        "provider_product_notices", "provider_product_notice_items", "provider_product_notice_events"
    )) and {"source_sales_qty", "actual_blocked_qty"} <= {c["name"] for c in inspector.get_columns("inventory_daily")}


def require_trade_schema(session):
    if not trade_schema_ready(session):
        raise DomainError("trade_schema_required", "Trade lifecycle requires the database upgrade", 503)


def lock_trade_scope(session, supplier_ids, item_ids, *, read=False, notice_id=None):
    # All application writers serialize in Supplier -> Notice -> Item order.
    list(session.scalars(select(Supplier).where(Supplier.id.in_(supplier_ids)).order_by(Supplier.id).with_for_update(read=read)))
    if notice_id is not None:
        session.scalar(select(ProviderProductNotice).where(ProviderProductNotice.id == notice_id).with_for_update(read=read))
    list(session.scalars(select(Item).where(Item.id.in_(item_ids)).order_by(Item.id).with_for_update(read=read)
                         .execution_options(populate_existing=True)))
    warehouse_ids = select(Item.warehouse_id).where(Item.id.in_(item_ids))
    list(session.scalars(select(Warehouse).where(Warehouse.id.in_(warehouse_ids)).order_by(Warehouse.id).with_for_update(read=True)
                         .execution_options(populate_existing=True)))


def provider_notices(session, item_ids=None, cutoff=None, notice_id=None):
    query = select(ProviderProductNotice)
    if item_ids is not None:
        query = query.where(ProviderProductNotice.id.in_(select(ProviderProductNoticeItem.notice_id)
                             .where(ProviderProductNoticeItem.item_id.in_(item_ids))))
    if notice_id is not None:
        query = query.where(ProviderProductNotice.id == notice_id)
    roots = session.scalars(query.order_by(ProviderProductNotice.id)).all()
    ids = [r.id for r in roots]
    members, events = defaultdict(list), defaultdict(list)
    for nid, iid in session.execute(select(ProviderProductNoticeItem.notice_id, ProviderProductNoticeItem.item_id)
            .where(ProviderProductNoticeItem.notice_id.in_(ids)).order_by(ProviderProductNoticeItem.item_id)):
        members[nid].append(iid)
    event_query = select(ProviderProductNoticeEvent).where(ProviderProductNoticeEvent.notice_id.in_(ids))
    if cutoff is not None:
        event_query = event_query.where(ProviderProductNoticeEvent.known_on <= cutoff)
    for row in session.scalars(event_query.order_by(ProviderProductNoticeEvent.notice_id, ProviderProductNoticeEvent.version)):
        events[row.notice_id].append(record(row))
    return [{**record(r), "item_ids": members[r.id], "events": events[r.id]}
            for r in roots if cutoff is None or events[r.id]]


def live_rights(session, item_ids, as_of_date, histories=None, notices=None):
    histories = supply_rows(session, item_ids) if histories is None else histories
    notices = provider_notices(session, item_ids) if notices is None else notices
    by_item = defaultdict(list)
    for row in histories:
        by_item[row["item_id"]].append(row)
    result = {}
    for item in item_ids:
        relevant = [n for n in notices if item in n["item_ids"]]
        state = trade_state(by_item[item], relevant, item, as_of_date) if as_of_date else dict(
            internal_status=None, internal_reason=None, provider_status=None, provider_blockers=[],
            provider_restrictions=[], replenishment_allowed=None, sales_allowed=None)
        state.update(internal_version=by_item[item][-1]["version"] if by_item[item] else 0,
            provider_notice_ids=[n["id"] for n in relevant],
            provider_versions={n["id"]: n["events"][-1]["version"] if n["events"] else 0 for n in relevant})
        result[item] = state
    return result


def freeze_trade(session, ids, cutoff):
    require_trade_schema(session)
    from modules.catalog.provider_service import provider_catalog
    from modules.catalog.provider import resolve_provider_scope
    notices = provider_notices(session, ids, cutoff)
    catalogs = {}
    for notice in notices:
        sid = notice["supplier_id"]
        if sid not in catalogs:
            catalogs[sid] = provider_catalog(session, sid)
        _, members = resolve_provider_scope(catalogs[sid], sid, notice["scope_definition"])
        if members != notice["item_ids"]:
            raise DomainError("provider_scope_incomplete", "Provider scope changed; declare the missing coverage before planning", 409)
        notice["item_snapshot"] = [r for r in catalogs[sid] if r["id"] in members]
    return jsonable_encoder(dict(trade_lifecycle_profile=TRADE_PROFILE, trade_rules=TRADE_RULES,
        internal_supply_snapshot=supply_rows(session, ids, cutoff),
        provider_notice_snapshot=notices))
