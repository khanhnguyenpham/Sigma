"""Freeze policies/catalog into a run; readers never reinterpret old runs with live config."""

from datetime import timedelta
from sqlalchemy import select
from modules.configuration.models import Policy
from modules.configuration.schemas import POLICY_DEFAULTS
from modules.catalog.models import Item, Warehouse, Supplier
from core.errors import DomainError


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
    rows = session.scalars(
        select(Policy).where(
            Policy.item_id.in_(ids), Policy.effective_from <= max(dates)
        )
    ).all()
    policies = []
    overrides = {o["item_id"]: o for o in scenario.settings.get("policy_overrides", [])}
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
    supplier_ids = set(session.scalars(select(Supplier.id)))
    if any(p["supplier_id"] not in supplier_ids for p in policies):
        raise DomainError(
            "missing_partner_config", "Scenario contains an unknown supplier"
        )
    for lot in scenario.settings.get("receipts_initial", []):
        if (
            lot["item_id"] not in ids
            or lot["ordered_on"] > request.as_of_date.isoformat()
        ):
            raise DomainError(
                "invalid_input", "Initial receipts must be known at the run origin"
            )
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
            select(Warehouse).where(
                Warehouse.id.in_(
                    {
                        i.warehouse_id
                        for i in session.scalars(select(Item).where(Item.id.in_(ids)))
                    }
                )
            )
        )
    ]
    return dict(
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
