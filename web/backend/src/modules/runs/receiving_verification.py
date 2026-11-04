"""Independent validation of receiving snapshots and persisted lot destinations."""
from datetime import date, timedelta
from core.errors import DomainError


def verify_receiving_snapshot(run, orders=None):
    snap = run.config_snapshot
    profile, rows = snap.get("receiving_warehouse_profile"), snap.get("receiving_warehouse_snapshot")
    if profile is None and rows is None:
        if orders is not None and "receiving_warehouse_id" in orders and orders.receiving_warehouse_id.notna().any():
            raise DomainError("verification_failed", "Legacy order contains an unversioned receiving location")
        return None
    try:
        if profile != "product_default_receiving_v1" or not isinstance(rows, list):
            raise ValueError
        cutoff = run.as_of_date
        if run.kind == "policy_replay":
            cutoff = run.period_end
        elif run.kind == "alert_replay":
            cutoff += timedelta(days=max(0, ((run.period_end-cutoff).days//14-1)*14))
        elif run.kind != "stock_projection":
            raise ValueError
        warehouses = {w["id"]: w for w in snap["warehouse_snapshot"]}
        routes = {(w["destination_country"], w["carrier"]): w["id"] for w in warehouses.values()}
        catalog = {i["item_id"]: i for i in snap["catalog_snapshot"]
                   if date.fromisoformat(i["first_seen_date"]) <= cutoff}
        mapping = {}
        for row in rows:
            if set(row) != {"item_id", "source_warehouse_id", "receiving_warehouse_id", "receiving_version"}:
                raise ValueError
            key, source, target, version = (row[k] for k in
                ("item_id", "source_warehouse_id", "receiving_warehouse_id", "receiving_version"))
            if any(type(v) is not int for v in (key, source, target, version)) or key in mapping:
                raise ValueError
            item = catalog[key]
            if (source != routes[(item["destination_country"], item["carrier"])] or target not in warehouses
                or target <= 0 or version < 0 or (version == 0 and target != source)):
                raise ValueError
            mapping[key] = target
        if set(mapping) != set(catalog):
            raise ValueError
        if orders is not None:
            if "receiving_warehouse_id" not in orders:
                raise ValueError
            for row in orders.itertuples():
                if row.receiving_warehouse_id != mapping[row.item_id]:
                    raise ValueError
        return mapping
    except (KeyError, TypeError, ValueError, AttributeError):
        raise DomainError("verification_failed", "Frozen receiving warehouses or order destinations differ") from None
