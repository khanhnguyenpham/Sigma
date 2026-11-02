"""Preview configuration changes against an explicitly selected frozen plan."""
from copy import deepcopy

from sqlalchemy import select
from core.errors import DomainError
from core.hashes import digest
from core.http import record
from core.run_context import required_run
from modules.catalog.models import Item, Warehouse, Supplier, ProviderProductNotice
from modules.catalog.provider import (provider_event_values, validate_provider_change,
                                      resolve_provider_scope, trade_state)
from modules.catalog.provider_service import (provider_catalog, check_version, create_provider_notice,
                                              append_provider_notice_event)
from modules.catalog.supply import validate_supply_change
from modules.catalog.supply_service import supply_rows, create_supply_change
from modules.catalog.trade_service import require_trade_schema, lock_trade_scope, provider_notices


def impact_data(session, draft, ids):
    empty = dict(run_id=None, as_of_date=None, config_sha256=None, inventory_items=0,
                 scope_items=len(ids), inventory_complete=False, stock_qty=None,
                 sellable_qty=None, blocked_qty=None, pending_qty=None,
                 incoming_on_or_after_effective_qty=None, quantity_basis="not_available",
                 rights_quantities_available=False)
    if draft.impact_run_id is None:
        return empty, {}
    run = required_run(session, draft.impact_run_id, complete=True)
    if run.kind not in {"stock_projection", "policy_replay", "alert_replay"}:
        raise DomainError("parent_mismatch", "Impact preview requires an inventory plan", 409)
    day = draft.impact_as_of_date or draft.known_on
    from modules.reporting.schemas import Filters
    from modules.reporting.service import dataset
    rows, _ = dataset(session, run, "inventory_daily", Filters(date_from=day, date_to=day), paginate=False)
    lots, _ = dataset(session, run, "replenishments", Filters(as_of_date=day), paginate=False)
    known = min(day, run.period_end or run.as_of_date)
    windows = {}
    for row in rows + lots:
        if row["item_id"] in ids and row["window_origin"] <= known:
            windows[row["item_id"]] = max(windows.get(row["item_id"], row["window_origin"]), row["window_origin"])
    inventory = {r["item_id"]: r for r in rows if r["item_id"] in ids and r["window_origin"] == windows.get(r["item_id"])}
    incoming = [r for r in lots if r["item_id"] in ids and r["window_origin"] == windows.get(r["item_id"])
                and r["ordered_on"] <= known and r["eta"] > known]
    per_item = {}
    for item in ids:
        row = inventory.get(item)
        per_item[item] = dict(stock_qty=row["closing_qty"] if row else None,
            frozen_recommended_qty=row["recommended_qty"] if row else None,
            pending_qty=sum(r["ordered_qty"] for r in incoming if r["item_id"] == item) if row else None,
            incoming_on_or_after_effective_qty=sum(r["ordered_qty"] for r in incoming
                if r["item_id"] == item and r["eta"] >= draft.effective_on) if row else None)
    complete = len(inventory) == len(ids)
    return dict(empty, run_id=str(run.id), as_of_date=day, config_sha256=run.config_sha256,
        inventory_items=len(inventory), inventory_complete=complete,
        stock_qty=sum(r["closing_qty"] for r in inventory.values()) if complete else None,
        pending_qty=sum(r["ordered_qty"] for r in incoming) if complete else None,
        incoming_on_or_after_effective_qty=sum(r["ordered_qty"] for r in incoming if r["eta"] >= draft.effective_on) if complete else None,
        known_orders_through=known,
        quantity_basis="frozen_plan_at_selected_date", rights_quantities_available=False), per_item


def rights_view(state):
    return {**{k: state[k] for k in ("internal_status", "provider_status", "internal_reason",
                                      "replenishment_allowed", "sales_allowed")},
            "provider_reasons": [r["reason"] for r in state["provider_blockers"]]}


def provider_preview(session, draft, *, write=False, fingerprint=None):
    require_trade_schema(session)
    root = None
    if draft.action == "stop":
        supplier_id = draft.supplier_id
    else:
        root = session.get(ProviderProductNotice, draft.notice_id)
        if root is None:
            raise DomainError("not_found", "Provider notice does not exist", 404)
        supplier_id = root.supplier_id
    # Lock supplier first; membership/catalog and all provider writers share this lock.
    supplier = session.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update(read=not write))
    if supplier is None:
        raise DomainError("not_found", "Supplier does not exist", 404)
    catalog = provider_catalog(session, supplier_id)
    if root is None:
        scope, ids = resolve_provider_scope(catalog, supplier_id, draft.scope_definition.model_dump())
        history = []
    else:
        scope = root.scope_definition
        selected = provider_notices(session, notice_id=root.id)[0]
        ids, history = selected["item_ids"], selected["events"]
    lock_trade_scope(session, [supplier_id], ids, read=not write, notice_id=root.id if root else None)
    catalog = provider_catalog(session, supplier_id)
    if not ids or (root is not None and not history):
        raise DomainError("invalid_provider_history", "Provider scope or history is incomplete", 409)
    check_version(draft.expected_version, history[-1]["version"] if history else 0)
    values = provider_event_values(action=draft.action, known_on=draft.known_on, effective_on=draft.effective_on,
        target_event_id=getattr(draft, "target_event_id", None), reason=draft.reason,
        source_description=draft.source_description, source_ref=draft.source_ref)
    if ((draft.action == "cancel_stop" and draft.effective_on != draft.known_on)
        or (draft.action == "resume_supply" and draft.effective_on < draft.known_on)):
        raise DomainError("invalid_input", "Invalid provider action dates")
    validate_provider_change(history, **{k: values[k] for k in ("action", "known_on", "effective_on", "target_event_id")})
    histories = supply_rows(session, ids)
    notices = provider_notices(session, ids)
    impact, quantities = impact_data(session, draft, ids)
    payload = draft.model_dump(mode="json", exclude={"preview_fingerprint", "scope_definition"})
    payload["scope_definition"] = scope
    checksum = digest(dict(payload=payload, members=ids, catalog=[r for r in catalog if r["id"] in ids],
                           internal=histories, notices=notices, impact=impact))
    if write and checksum != fingerprint:
        raise DomainError("preview_stale", "Scope, configuration or impact plan changed; review preview again", 409)
    after = deepcopy(notices)
    proposed = dict(id=-1, notice_id=root.id if root else -1, version=len(history)+1, **values)
    if root:
        next(n for n in after if n["id"] == root.id)["events"].append(proposed)
    else:
        after.append(dict(id=-1, supplier_id=supplier_id, item_ids=ids, events=[proposed]))
    target = max(draft.known_on, draft.effective_on)
    rows = []
    for item in ids:
        before_rights = rights_view(trade_state(histories, notices, item, draft.known_on, target))
        after_rights = rights_view(trade_state(histories, after, item, draft.known_on, target))
        rows.append(dict(next(r for r in catalog if r["id"] == item), item_id=item, before=before_rights,
                         after=after_rights, **quantities.get(item, dict(stock_qty=None, pending_qty=None,
                             incoming_on_or_after_effective_qty=None, frozen_recommended_qty=None)),
                         recommended_qty_after=0 if not after_rights["replenishment_allowed"] else None))
    result = dict(notice_id=root.id if root else None, supplier_id=supplier_id, scope_definition=scope,
        expected_version=draft.expected_version, preview_fingerprint=checksum, rights_on=target,
        scope_items=len(ids), scope_warehouses=len({r["warehouse_id"] for r in rows}), impact=impact,
        changed_rights_items=sum(r["before"] != r["after"] for r in rows),
        action=draft.action, items=rows, total=len(rows),
        quantity_limit_status="not_calculated_until_trade_projection",
        is_assumed=True, existing_lots_kept=True)
    if write:
        if root:
            saved = append_provider_notice_event(session, root.id, expected_version=draft.expected_version, **values)
        else:
            saved = create_provider_notice(session, supplier_id=supplier_id, scope_definition=scope,
                expected_version=draft.expected_version, expected_item_ids=ids, **values)
        return {**saved, "scope_items": len(ids), "scope_warehouses": result["scope_warehouses"]}
    return result


def internal_preview(session, item_id, draft, *, write=False):
    require_trade_schema(session)
    info = session.execute(select(Item, Warehouse, Supplier.id)
        .join(Warehouse, Warehouse.id == Item.warehouse_id)
        .join(Supplier, Supplier.carrier == Warehouse.carrier).where(Item.id == item_id)).one_or_none()
    if info is None:
        raise DomainError("not_found", "Product does not exist", 404)
    item, warehouse, supplier_id = info
    lock_trade_scope(session, [supplier_id], [item_id], read=not write)
    histories = supply_rows(session, [item_id])
    check_version(draft.expected_version, histories[-1]["version"] if histories else 0)
    values = draft.model_dump(include={"action", "known_on", "effective_on", "target_change_id"})
    validate_supply_change(histories, item_id=item_id, minimum_notice_days=0, **values)
    notices = provider_notices(session, [item_id])
    impact, quantities = impact_data(session, draft, [item_id])
    payload = draft.model_dump(mode="json", exclude={"preview_fingerprint"})
    checksum = digest(dict(payload=payload, item=record(item), warehouse=record(warehouse),
                           history=histories, notices=notices, impact=impact))
    if write and checksum != draft.preview_fingerprint:
        raise DomainError("preview_stale", "Configuration or impact plan changed; review preview again", 409)
    target = max(draft.known_on, draft.effective_on)
    after = histories + [dict(id=-1, item_id=item_id, version=len(histories)+1, reason=draft.reason, **values)]
    result = dict(item_id=item_id, warehouse=record(warehouse), expected_version=draft.expected_version,
        preview_fingerprint=checksum, rights_on=target, impact=impact,
        before=rights_view(trade_state(histories, notices, item_id, draft.known_on, target)),
        after=rights_view(trade_state(after, notices, item_id, draft.known_on, target)),
        existing_lots_kept=True, sells_permitted_stock=True,
        **quantities.get(item_id, dict(stock_qty=None, pending_qty=None, incoming_on_or_after_effective_qty=None,
                                     frozen_recommended_qty=None)))
    if write:
        return create_supply_change(session, item_id, draft, minimum_notice_days=0)
    return result
