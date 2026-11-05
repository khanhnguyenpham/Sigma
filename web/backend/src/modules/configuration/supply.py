"""Compile versioned scenario stops into the existing frozen trade contract."""
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from core.errors import DomainError
from modules.catalog.models import Item, Warehouse, Supplier
from modules.catalog.provider import resolve_provider_scope, provider_event_values
from modules.catalog.provider_service import provider_catalog
from modules.catalog.trade_service import TRADE_PROFILE, TRADE_RULES
from modules.configuration.schemas import SupplySchedule

SCENARIO_SUPPLY_PROFILE = "scenario_supply_v1"


def freeze_scenario_supply(session, settings, cutoff, ids=None):
    schedule = SupplySchedule.model_validate(settings.get("supply_schedule") or {})
    internal, notices, products = [], [], set()
    for index, stop in enumerate(schedule.internal_stops, 1):
        if session.get(Item, stop.item_id) is None:
            raise DomainError("not_found", "Scenario stop contains an unknown product", 404)
        if stop.known_on <= cutoff and (ids is None or stop.item_id in ids):
            internal.append(dict(id=index, item_id=stop.item_id, version=1, action="stop", target_change_id=None,
                **stop.model_dump(exclude={"item_id"}), is_assumed=True,
                assumption_source="user_declared_supply_simulation_v1"))
    for index, stop in enumerate(schedule.provider_stops, 1):
        product = session.execute(select(Item, Supplier.id).join(Warehouse, Warehouse.id == Item.warehouse_id)
            .join(Supplier, Supplier.carrier == Warehouse.carrier).where(Item.id == stop.item_id)).one_or_none()
        if product is None:
            raise DomainError("not_found", "Scenario stop contains an unknown supplier product", 404)
        item, supplier = product
        identity = (supplier, item.sku, item.product_type)
        if identity in products:
            raise DomainError("invalid_input", "Duplicate supplier product stop in this scenario")
        products.add(identity)
        catalog = provider_catalog(session, supplier)
        scope, members = resolve_provider_scope(catalog, supplier, dict(products=[dict(sku=item.sku, product_type=item.product_type)]))
        if stop.known_on <= cutoff and (ids is None or set(members) & ids):
            event = provider_event_values(action="stop", **stop.model_dump(exclude={"item_id"}))
            notices.append(dict(id=index, supplier_id=supplier, scope_definition=scope, item_ids=members,
                item_snapshot=[r for r in catalog if r["id"] in members],
                events=[dict(id=index, notice_id=index, version=1, is_assumed=True, **event)]))
    return jsonable_encoder(dict(scenario_supply_profile=SCENARIO_SUPPLY_PROFILE,
        trade_lifecycle_profile=TRADE_PROFILE, trade_rules=TRADE_RULES,
        internal_supply_snapshot=internal, provider_notice_snapshot=notices))
