"""Business-only snapshot projection. Never serialize arbitrary configuration."""
import re

POLICY_FIELDS = (
    "id", "item_id", "supplier_id", "version", "effective_from", "effective_to",
    "configured_rop_floor", "fixed_order_qty", "moq", "safety_days", "warning_horizon_days",
    "safety_mode", "safety_lookback_days", "safety_factor", "rop_mode",
)
ITEM_FIELDS = ("sku", "product_type", "destination_country", "carrier")


def pick(value, fields):
    return {key: value[key] for key in fields if key in value}


def snapshot_view(run, page=1, page_size=25):
    snapshot = run.config_snapshot or {}
    raw_reference = snapshot.get('runtime_code_reference')
    reference = None
    if isinstance(raw_reference,dict) and raw_reference.get('mode')=='immutable-release-v1':
        version=raw_reference.get('version')
        if isinstance(version,str) and len(version)<=64 and re.fullmatch(r'(?:[a-f0-9]{40}|v\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)',version):
            reference={'mode':'immutable-release-v1','version':version}
    scenario = snapshot.get("scenario") or {}
    settings = scenario.get("settings") or {}
    catalog = {row["item_id"]: row for row in snapshot.get("catalog_snapshot", [])}
    receiving = {row["item_id"]: row.get("receiving_warehouse_id")
                 for row in snapshot.get("receiving_warehouse_snapshot", [])}
    policies = snapshot.get("policies") or []
    rows = []
    for policy in policies[(page - 1) * page_size:page * page_size]:
        row = pick(policy, POLICY_FIELDS)
        row.update(pick(catalog.get(policy.get("item_id"), {}), ITEM_FIELDS))
        row["receiving_warehouse_id"] = receiving.get(policy.get("item_id"))
        rows.append(row)
    schedule = settings.get("supply_schedule") or {}
    return {
        "run": {"id": run.id, "kind": run.kind, "status": run.status,
                "as_of_date": run.as_of_date, "period_start": run.period_start,
                "period_end": run.period_end, "source_import_run_id": run.source_import_run_id,
                "forecast_run_id": run.forecast_run_id, "created_at": run.created_at},
        "versions": {"runtime_code_reference": reference, "config": run.config_version, "assumption": run.assumption_version,
                     "target": run.target_version,
                     "inventory_policy": snapshot.get("inventory_policy_profile"),
                     "receiving_warehouse": snapshot.get("receiving_warehouse_profile")},
        "scenario": pick(scenario, ("id", "name", "code", "version")),
        "parameters": {**pick(snapshot, ("lead_time_days", "review_days", "horizon_days")),
                       **pick(settings, ("cover_days", "safety_multiplier")),
                       "initial_stock_history_days": 28,
                       "supplier_lead_times": snapshot.get("supplier_lead_times"),
                       "zero_sales_fallback_days": snapshot.get("initial_stock_fallback_days")},
        "policies": {"items": rows, "total": len(policies), "page": page, "page_size": page_size},
        "policy_overrides": [pick(row, ("item_id", "configured_rop_floor", "fixed_order_qty", "moq", "safety_days", "warning_horizon_days", "safety_mode", "safety_lookback_days", "safety_factor", "rop_mode"))
                             for row in settings.get("policy_overrides", [])],
        "receipts_initial": [pick(row, ("item_id", "ordered_on", "eta", "ordered_qty", "lot_key"))
                             for row in settings.get("receipts_initial", [])],
        "supply_schedule": {kind: [pick(row, ("item_id", "known_on", "effective_on", "reason"))
                                   for row in schedule.get(kind, [])]
                            for kind in ("internal_stops", "provider_stops")},
    }
