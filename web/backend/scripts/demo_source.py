"""Prepare a new private demo CSV; never mutate the registered original source."""
import hashlib
import json
from pathlib import Path
import shutil
import uuid

import pandas as pd
from core.settings import PROJECT_ROOT
from modules.forecasting.demo_source import signatures
from src.common import sha256
from src.data import audit_orders, SOURCE_COLUMNS


def export_source(settings, original, expected_sha=None):
    if settings.mode != "demo" or settings.source_root.exists():
        raise ValueError("Export needs demo mode and a new source directory")
    original = Path(original).resolve()
    expected_sha = expected_sha or json.loads((PROJECT_ROOT / "data/configs/m2-final.json").read_text())["source_sha256"]
    if sha256(original) != expected_sha:
        raise ValueError("Original source differs from the registered protocol")
    cfg = json.loads((PROJECT_ROOT / "data/configs/config.json").read_text())
    before, audit = audit_orders(original, cfg)  # Conflicting duplicates must fail before redaction.
    raw = pd.read_csv(original, dtype=str, keep_default_na=False, encoding="utf-8-sig")[SOURCE_COLUMNS]
    for column in SOURCE_COLUMNS:
        raw[column] = raw[column].str.strip()
    unique = raw.drop_duplicates("order_id").copy()
    unique["timestamp"] = pd.to_datetime(unique.order_datetime, format="mixed", utc=True)
    unique = unique.sort_values(["timestamp", "order_id"], kind="mergesort")
    days = unique.timestamp.dt.floor("D")
    rank = unique.groupby(days, sort=False).cumcount() + 1
    unique["demo_time"] = days + pd.to_timedelta(rank, unit="us")
    if not unique.demo_time.dt.floor("D").equals(days):
        raise ValueError("Too many demo transactions in one UTC day")
    mapping = dict(zip(unique.order_id, [f"DEMO-{n:010}" for n in range(1, len(unique)+1)]))
    dates = dict(zip(unique.order_id, unique.demo_time.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")))
    raw["order_datetime"] = raw.order_id.map(dates)
    raw["order_id"] = raw.order_id.map(mapping)
    raw["activation_datetime"] = ""
    for column in ("unit_price_vnd", "unit_cost_vnd", "gross_revenue_vnd", "data_gb"):
        raw[column] = "0"
    for column in ("region", "plan_type", "sales_channel", "payment_method", "customer_type"):
        raw[column] = "demo"
    raw["customer_id"] = "DEMO_CUSTOMER"
    raw["validity_days"] = "1"
    staging = settings.source_root.with_name(".source-" + str(uuid.uuid4()))
    if not staging.resolve().is_relative_to(settings.demo_root):
        raise ValueError("Demo export escaped its isolated root")
    (staging / "data").mkdir(parents=True, exist_ok=False)
    try:
        path = staging / "data/sigma_sim_data_orders.csv"
        raw.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        after, result = audit_orders(path, cfg)
        if signatures(before) != signatures(after):
            raise ValueError("Demo changed quantities, order counts or transaction ordering")
        for key in ("rows_raw", "rows_after_dedup", "duplicate_rows_removed", "sales_rows", "sales_quantity", "routes"):
            if audit[key] != result[key]:
                raise ValueError("Demo changed source cohort or deduplication")
        if result["invalid_money_rows"] or result["revenue_mismatch_rows"] or sha256(original) != expected_sha:
            raise ValueError("Demo source validation failed")
        manifest = dict(version=1, anonymized=True, money_policy="zero",
            source_file="data/sigma_sim_data_orders.csv", source_sha256=sha256(path),
            parent_source_sha256=expected_sha, **signatures(after),
            rows=len(raw), sales_rows=result["sales_rows"], sales_quantity=result["sales_quantity"],
            duplicate_rows=result["duplicate_rows_removed"],
            transformations=["new_sequential_order_ids", "constant_customer", "activation_removed",
                "synthetic_intra_day_times_order_preserved", "zero_monetary_fields", "unused_attributes_replaced"])
        (staging / "demo-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        staging.rename(settings.source_root)
        return manifest
    finally:
        if staging.exists():
            assert staging.resolve().is_relative_to(settings.demo_root)
            shutil.rmtree(staging)
