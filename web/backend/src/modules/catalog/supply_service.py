"""Supply history persistence. All writers serialize on the existing item row."""
from sqlalchemy import select, inspect
from core.errors import DomainError
from core.http import record
from modules.catalog.models import Item, ItemSupplyChange
from modules.catalog.supply import supply_state, validate_supply_change


def supply_schema_ready(session):
    return inspect(session.connection()).has_table("item_supply_changes")


def require_supply_schema(session):
    if not supply_schema_ready(session):
        raise DomainError("supply_schema_required", "Supply history requires the planned database upgrade", 503)


def supply_rows(session, ids, cutoff=None):
    query = select(ItemSupplyChange).where(ItemSupplyChange.item_id.in_(ids))
    if cutoff is not None:
        query = query.where(ItemSupplyChange.known_on <= cutoff)
    return [record(row) for row in session.scalars(query.order_by(ItemSupplyChange.item_id, ItemSupplyChange.version))]


def create_supply_change(session, item_id, request, *, minimum_notice_days=7):
    item = session.scalar(select(Item).where(Item.id == item_id).with_for_update())
    if item is None:
        raise DomainError("not_found", "Product does not exist", 404)
    require_supply_schema(session)
    history = supply_rows(session, [item_id])
    version = history[-1]["version"] if history else 0
    if request.expected_version != version:
        raise DomainError("version_conflict", "Supply history changed; reload before saving", 409)
    values = request.model_dump(include={"action", "known_on", "effective_on", "target_change_id"})
    validate_supply_change(history, item_id=item_id, minimum_notice_days=minimum_notice_days, **values)
    row = ItemSupplyChange(item_id=item_id, version=version + 1, reason=request.reason, **values)
    session.add(row)
    session.flush()
    history.append(record(row))
    return {**record(row), "supply_version": row.version,
            "state": supply_state(history, item_id, request.known_on)}


def list_supply_changes(session, item_id, page, page_size, as_of_date=None):
    if session.get(Item, item_id) is None:
        raise DomainError("not_found", "Product does not exist", 404)
    require_supply_schema(session)
    history = supply_rows(session, [item_id])
    version = history[-1]["version"] if history else 0
    return dict(items=list(reversed(history))[(page-1)*page_size:page*page_size], total=len(history),
                page=page, page_size=page_size, supply_version=version, as_of_date=as_of_date,
                state=supply_state(history, item_id, as_of_date) if as_of_date else None)
