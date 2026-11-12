"""Freeze policies/catalog into a run; readers never reinterpret old runs with live config."""

from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import undefer
from modules.configuration.models import Policy
from modules.configuration.schemas import POLICY_DEFAULTS
from modules.catalog.models import Item, Warehouse, Supplier
from core.errors import DomainError
from fastapi.encoders import jsonable_encoder
from modules.catalog.supply_service import require_supply_schema, supply_rows
from modules.catalog.trade_service import trade_schema_ready, require_trade_schema, lock_trade_scope, provider_notices, freeze_trade
from modules.catalog.receiving import receiving_schema_ready, RECEIVING_PROFILE


def freeze_inventory(session, request, source, scenario):
    catalog = source.config_snapshot["catalog_snapshot"]
    if request.kind == "alert_replay":
        dates = []
        day = request.as_of_date
        while day + timedelta(days=14) <= request.period_end:
            dates.append(day)
            day += timedelta(days=14)
    elif request.kind == "policy_replay":
        dates = [
            request.as_of_date + timedelta(days=i)
            for i in range((request.period_end - request.as_of_date).days + 1)
        ]
    else:
        dates = [request.as_of_date]
    if not dates:
        raise DomainError(
            "insufficient_history", "No complete replay window in this period"
        )
    ids = {
        i["item_id"] for i in catalog if i["first_seen_date"] <= max(dates).isoformat()
    }
    trade_ready = trade_schema_ready(session)
    if request.trade_lifecycle_profile:
        require_trade_schema(session)
    if trade_ready:
        supplier_ids = list(session.scalars(select(Supplier.id).join(Warehouse, Warehouse.carrier == Supplier.carrier)
            .join(Item, Item.warehouse_id == Warehouse.id).where(Item.id.in_(ids)).distinct()))
        lock_trade_scope(session, supplier_ids, ids, read=True)
    rows = session.scalars(
        select(Policy).where(
            Policy.item_id.in_(ids), Policy.effective_from <= max(dates)
        )
    ).all()
    policies = []
    overrides = {o["item_id"]: o for o in scenario.settings.get("policy_overrides", [])}
    if any({"safety_mode", "rop_mode", "safety_lookback_days", "safety_factor"} & o.keys() for o in overrides.values()):
        raise DomainError("invalid_input", "Only the minimum ROP and sales-day safety stock can be configured")
    if any("moq" in o or "fixed_order_qty" in o for o in overrides.values()):
        raise DomainError(
            "missing_contract_quantity",
            "Order quantity must be configured on the item policy, not the scenario",
        )
    if (any("receiving_warehouse_id" in o for o in overrides.values()) or "receiving_warehouse_id" in scenario.settings
        or any("receiving_warehouse_id" in lot for lot in scenario.settings.get("receipts_initial", []))):
        raise DomainError("invalid_input", "Scenarios use each product's saved receiving warehouse")
    for p in rows:
        record = {
            name: getattr(p, name)
            for name in [
                "id",
                "item_id",
                "supplier_id",
                "version",
                "effective_from",
                "effective_to",
                "configured_rop_floor",
                "moq",
                "fixed_order_qty",
                "safety_days",
                "is_assumed",
                "assumption_source",
                *POLICY_DEFAULTS,
            ]
        }
        record["effective_from"] = p.effective_from.isoformat()
        record["effective_to"] = p.effective_to.isoformat() if p.effective_to else None
        record["safety_days"] = float(p.safety_days)
        if p.item_id in overrides:
            record.update(
                {
                    k: v
                    for k, v in overrides[p.item_id].items()
                    if v is not None and k != "item_id"
                }
            )
            record["safety_days"] = float(record["safety_days"])
            record["scenario_override"] = True
        record.update(safety_mode="days", rop_mode="forecast")
        policies.append(record)
    for item in catalog:
        for day in dates:
            if item["first_seen_date"] > day.isoformat():
                continue
            effective = [
                p
                for p in policies
                if p["item_id"] == item["item_id"]
                and p["effective_from"] <= day.isoformat()
                and (p["effective_to"] is None or day.isoformat() < p["effective_to"])
            ]
            if len(effective) != 1:
                raise DomainError(
                    "missing_partner_config",
                    "Exactly one effective policy is required",
                    item_id=item["item_id"],
                )
            if effective[0]["fixed_order_qty"] is None:
                raise DomainError(
                    "missing_contract_quantity",
                    "Configure the fixed quantity per order before creating a new run",
                    item_id=item["item_id"],
                )
    supplier_carriers = dict(session.execute(select(Supplier.id, Supplier.carrier)).all())
    if any(p["supplier_id"] not in supplier_carriers for p in policies):
        raise DomainError(
            "missing_partner_config", "Scenario contains an unknown supplier"
        )
    item_carriers = {i["item_id"]: i["carrier"] for i in catalog}
    if any(supplier_carriers[p["supplier_id"]] != item_carriers[p["item_id"]] for p in policies):
        raise DomainError("supplier_carrier_mismatch", "Supplier must be the item's carrier", 422)
    for lot in scenario.settings.get("receipts_initial", []):
        if (
            lot["item_id"] not in ids
            or lot["ordered_on"] > request.as_of_date.isoformat()
        ):
            raise DomainError(
                "invalid_input", "Initial receipts must be known at the run origin"
            )
    receiving = {}
    item_query = select(Item).where(Item.id.in_(ids)).order_by(Item.id)
    if receiving_schema_ready(session):
        live_items = session.scalars(item_query.options(undefer(Item.receiving_warehouse_id), undefer(Item.receiving_version))
            .with_for_update(read=True).execution_options(populate_existing=True)).all()
        if {i.id for i in live_items} != ids:
            raise DomainError("catalog_mismatch", "A source product is missing from the catalog", 409)
        receiving = dict(receiving_warehouse_profile=RECEIVING_PROFILE, receiving_warehouse_snapshot=[
            dict(item_id=i.id, source_warehouse_id=i.warehouse_id,
                 receiving_warehouse_id=i.receiving_warehouse_id or i.warehouse_id,
                 receiving_version=i.receiving_version) for i in live_items])
    else:
        live_items = session.scalars(item_query).all()
    warehouse_ids = {i.warehouse_id for i in live_items}
    warehouse_ids.update(r["receiving_warehouse_id"] for r in receiving.get("receiving_warehouse_snapshot", []))
    warehouse_ids.update(w["id"] for w in source.config_snapshot.get("warehouse_snapshot", []))
    warehouses = [
        {
            name: getattr(w, name)
            for name in [
                "id",
                "code",
                "destination_country",
                "carrier",
                "city",
                "is_assumed",
                "version",
            ]
        }
        for w in session.scalars(
            select(Warehouse).where(Warehouse.id.in_(warehouse_ids)).order_by(Warehouse.id).with_for_update(read=True)
                .execution_options(populate_existing=True)
        )
    ]
    require_supply_schema(session)
    supply_history = jsonable_encoder(supply_rows(session, ids, max(dates)))
    if request.scenario_supply_profile:
        from modules.configuration.supply import freeze_scenario_supply
        lifecycle = freeze_scenario_supply(session, scenario.settings, max(dates), ids)
    elif request.trade_lifecycle_profile:
        lifecycle = freeze_trade(session, ids, max(dates))
    else:
        if trade_ready and (provider_notices(session, ids, max(dates)) or any(
            row["action"] == "stop" and
            (date.fromisoformat(row["effective_on"])-date.fromisoformat(row["known_on"])).days < 7
            for row in supply_history
        )):
            raise DomainError("trade_profile_required", "Create a plan with the trade lifecycle profile for these restrictions", 409)
        lifecycle = dict(supply_lifecycle_profile="notice7_sellthrough_v1", supply_lifecycle_snapshot=supply_history)
    return dict(
        **lifecycle,
        **receiving,
        inventory_policy_profile="forecast_floor_days_ss_v1",
        initial_stock_fallback_days=90,
        policies=policies,
        policy_ids=sorted({p["id"] for p in policies}),
        catalog_snapshot=catalog,
        warehouse_snapshot=warehouses,
        scenario={
            "id": scenario.id,
            "version": scenario.version,
            "name": scenario.name,
            "code": scenario.code,
            "settings": scenario.settings,
        },
    )
