"""Transactional provider history. No HTTP routes or simulation writes."""
from sqlalchemy import inspect, select

from core.errors import DomainError
from core.http import record
from modules.catalog.models import (Supplier, Warehouse, Item, ProviderProductNotice,
                                    ProviderProductNoticeItem, ProviderProductNoticeEvent)
from modules.catalog.provider import provider_event_values, validate_provider_change, resolve_provider_scope


def require_provider_schema(session):
    inspector = inspect(session.connection())
    if not all(inspector.has_table(name) for name in (
        "provider_product_notices", "provider_product_notice_items", "provider_product_notice_events"
    )):
        raise DomainError("trade_schema_required", "Provider history requires the trade lifecycle upgrade", 503)


def provider_catalog(session, supplier_id):
    return [dict(r) for r in session.execute(
        select(Item.id, Item.warehouse_id, Item.sku, Item.product_type, Warehouse.destination_country,
               Warehouse.carrier, Warehouse.version.label("warehouse_version"),
               Supplier.id.label("supplier_id"))
        .join(Warehouse, Warehouse.id == Item.warehouse_id)
        .join(Supplier, Supplier.carrier == Warehouse.carrier)
        .where(Supplier.id == supplier_id).order_by(Item.id)
    ).mappings()]


def check_version(expected, actual):
    if type(expected) is not int or expected < 0:
        raise DomainError("invalid_input", "A nonnegative expected version is required")
    if expected != actual:
        raise DomainError("version_conflict", "Provider history changed; reload before saving", 409)


def create_provider_notice(session, *, supplier_id, scope_definition, expected_version, expected_item_ids=None, **event):
    require_provider_schema(session)
    if type(supplier_id) is not int or supplier_id < 1:
        raise DomainError("invalid_input", "A supplier is required")
    supplier = session.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if supplier is None:
        raise DomainError("not_found", "Supplier does not exist", 404)
    check_version(expected_version, 0)
    scope, members = resolve_provider_scope(provider_catalog(session, supplier_id), supplier_id, scope_definition)
    if expected_item_ids is not None and sorted(expected_item_ids) != members:
        raise DomainError("preview_stale", "Affected products changed; review the scope again", 409)
    list(session.scalars(select(Item).where(Item.id.in_(members)).order_by(Item.id).with_for_update()))
    values = provider_event_values(**event)
    validate_provider_change([], **{k: values[k] for k in ("action", "known_on", "effective_on", "target_event_id")})
    root = ProviderProductNotice(supplier_id=supplier_id, scope_definition=scope)
    session.add(root)
    session.flush()
    session.add_all(ProviderProductNoticeItem(notice_id=root.id, item_id=i) for i in members)
    row = ProviderProductNoticeEvent(notice_id=root.id, version=1, **values)
    session.add(row)
    session.flush()
    return dict(notice_id=root.id, item_ids=members, event=record(row), version=1)


def append_provider_notice_event(session, notice_id, *, expected_version, **event):
    require_provider_schema(session)
    if type(notice_id) is not int or notice_id < 1:
        raise DomainError("invalid_input", "A notice ID is required")
    root = session.get(ProviderProductNotice, notice_id)
    if root is None:
        raise DomainError("not_found", "Provider notice does not exist", 404)
    session.scalar(select(Supplier).where(Supplier.id == root.supplier_id).with_for_update())
    session.scalar(select(ProviderProductNotice).where(ProviderProductNotice.id == notice_id).with_for_update())
    members = list(session.scalars(select(ProviderProductNoticeItem.item_id)
                                   .where(ProviderProductNoticeItem.notice_id == notice_id)
                                   .order_by(ProviderProductNoticeItem.item_id)))
    list(session.scalars(select(Item).where(Item.id.in_(members)).order_by(Item.id).with_for_update()))
    history = [record(r) for r in session.scalars(select(ProviderProductNoticeEvent)
               .where(ProviderProductNoticeEvent.notice_id == notice_id).order_by(ProviderProductNoticeEvent.version))]
    check_version(expected_version, history[-1]["version"] if history else 0)
    values = provider_event_values(**event)
    validate_provider_change(history, **{k: values[k] for k in ("action", "known_on", "effective_on", "target_event_id")})
    row = ProviderProductNoticeEvent(notice_id=notice_id, version=len(history) + 1, **values)
    session.add(row)
    session.flush()
    return dict(notice_id=notice_id, item_ids=members, event=record(row), version=row.version)
