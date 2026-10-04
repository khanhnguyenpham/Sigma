"""Read-only order audit; derived sales preserve valid shocks and raw hashes."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from src.common import DataQualityError, ITEM, ROUTE, sha256

SOURCE_COLUMNS = [
    "order_id", "order_datetime", "activation_datetime", "product_type", "destination_country",
    "region", "carrier", "sku", "plan_type", "data_gb", "validity_days", "quantity",
    "unit_price_vnd", "unit_cost_vnd", "gross_revenue_vnd", "sales_channel", "payment_method",
    "customer_id", "customer_type", "order_status",
]


def audit_orders(path, cfg):
    path = Path(path)
    original_hash = sha256(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
        if len(set(header)) != len(header) or set(header) != set(SOURCE_COLUMNS):
            raise DataQualityError("Source schema differs from the 20-column contract")
        if any(len(row) != len(header) for row in reader):
            raise DataQualityError("CSV contains rows with missing/extra fields")
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if raw.empty:
        raise DataQualityError("Source contains no orders")
    frame = raw.copy()
    missing = {}
    whitespace = {}
    for col in SOURCE_COLUMNS:
        trimmed = frame[col].str.strip()
        missing[col] = int(trimmed.eq("").sum())
        whitespace[col] = int(frame[col].ne(trimmed).sum())
        frame[col] = trimmed
    blocking = {}
    for col in ["order_id", "order_datetime", "quantity", "order_status"] + ITEM:
        if missing[col]:
            blocking[f"missing_{col}"] = missing[col]
    timezone_known = frame.order_datetime.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True)
    order_dt = pd.to_datetime(frame.order_datetime.where(timezone_known), format="mixed", utc=True, errors="coerce")
    if order_dt.isna().any():
        blocking["invalid_or_naive_order_datetime"] = int(order_dt.isna().sum())
    integer_text = frame.quantity.str.fullmatch(r"\+?\d+")
    quantity = pd.to_numeric(frame.quantity.where(integer_text), errors="coerce")
    invalid_qty = quantity.isna() | quantity.le(0) | quantity.gt(np.iinfo(np.int64).max)
    if invalid_qty.any():
        blocking["invalid_quantity"] = int(invalid_qty.sum())
    unknown = ~frame.order_status.isin(cfg["known_statuses"])
    if unknown.any():
        blocking["unknown_order_status"] = int(unknown.sum())
    # Compare original content, not a lossy normalization, for conflicting IDs.
    signatures = pd.util.hash_pandas_object(raw[SOURCE_COLUMNS], index=False)
    distinct = signatures.groupby(frame.order_id).nunique()
    conflicts = distinct[distinct > 1].index
    if len(conflicts):
        blocking["conflicting_duplicate_groups"] = len(conflicts)
    # Normalization must not silently merge distinct raw route/item keys.
    normalized = frame[ITEM].agg("\x1f".join, axis=1)
    raw_key = raw[ITEM].agg("\x1f".join, axis=1)
    key_collisions = raw_key.groupby(normalized).nunique().gt(1)
    if key_collisions.any():
        blocking["normalized_item_key_collisions"] = int(key_collisions.sum())
    activation_known = frame.activation_datetime.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True)
    activation = pd.to_datetime(frame.activation_datetime.where(activation_known), format="mixed", utc=True, errors="coerce")
    audit = {
        "source_sha256_before": original_hash, "source_bytes": path.stat().st_size,
        "rows_raw": len(frame), "columns": SOURCE_COLUMNS, "missing": missing,
        "normalization": {"rule": "trim surrounding whitespace; collisions block", "counts": whitespace},
        "blocking_errors": blocking, "status_row_counts": frame.order_status.value_counts().to_dict(),
        "activation_missing": int(frame.activation_datetime.eq("").sum()),
        "activation_invalid": int((frame.activation_datetime.ne("") & activation.isna()).sum()),
        "activation_before_order": int((activation < order_dt).sum()),
        "target_definition": cfg["sales_statuses"], "target_definition_version": cfg["target_definition_version"],
        "target_status": "user-approved-experiment-not-mentor-confirmed",
    }
    if blocking:
        raise DataQualityError("Blocking data errors: " + ", ".join(f"{key}={count}" for key, count in sorted(blocking.items())))
    frame["quantity"] = quantity.astype("int64")
    frame["order_datetime"] = order_dt
    frame["date"] = order_dt.dt.tz_convert(None).dt.normalize()
    if frame.date.min() < pd.Timestamp(cfg["observation_start"]) or frame.date.max() > pd.Timestamp(cfg["observation_end"]):
        raise DataQualityError("Orders outside configured observation coverage")
    money_invalid = pd.Series(False, index=frame.index)
    for col in ["unit_price_vnd", "unit_cost_vnd", "gross_revenue_vnd"]:
        val = pd.to_numeric(frame[col].where(frame[col].str.fullmatch(r"\+?\d+")), errors="coerce")
        money_invalid |= val.isna() | val.lt(0)
        frame[col] = val
    mismatch = frame.gross_revenue_vnd.ne(frame.quantity * frame.unit_price_vnd) & ~money_invalid
    frame["money_valid"] = ~money_invalid & ~mismatch
    audit["invalid_money_rows"] = int(money_invalid.sum())
    audit["revenue_mismatch_rows"] = int(mismatch.sum())
    duplicate = frame.order_id.duplicated(keep="first")
    audit["duplicate_rows_removed"] = int(duplicate.sum())
    audit["quantity_before_dedup"] = int(frame.quantity.sum())
    audit["quantity_removed_dedup"] = int(frame.loc[duplicate, "quantity"].sum())
    frame = frame.loc[~duplicate].copy()
    audit["rows_after_dedup"] = len(frame)
    audit["quantity_after_dedup"] = int(frame.quantity.sum())
    sales = frame.loc[frame.order_status.isin(cfg["sales_statuses"])].copy()
    audit["sales_rows"] = len(sales)
    audit["sales_quantity"] = int(sales.quantity.sum())
    audit["routes"] = len(frame[ROUTE].drop_duplicates())
    audit["source_sha256_after"] = sha256(path)
    if audit["source_sha256_after"] != original_hash:
        raise DataQualityError("Source changed during audit")
    return sales, audit


def daily_sales(sales, cfg, routes=None, missing_days=None):
    routes = sales[ROUTE].drop_duplicates().sort_values(ROUTE) if routes is None else routes[ROUTE].drop_duplicates()
    days = pd.date_range(cfg["observation_start"], cfg["observation_end"], freq="D")
    grid = pd.DataFrame({"date": days}).merge(routes, how="cross")
    grouped = sales.groupby(["date"] + ROUTE, sort=True)
    observed = grouped.agg(sales_qty=("quantity", "sum"), order_count=("order_id", "nunique"),
                           gross_revenue_vnd=("gross_revenue_vnd", "sum"), money_valid=("money_valid", "all")).reset_index()
    observed.loc[~observed.money_valid, "gross_revenue_vnd"] = np.nan
    daily = grid.merge(observed, on=["date"] + ROUTE, how="left", validate="one_to_one")
    absent = daily.sales_qty.isna()
    daily.loc[absent, ["sales_qty", "order_count", "gross_revenue_vnd"]] = 0
    daily["actual_available"] = True
    # Explicit externally declared missing source days are not zero-sale days.
    if missing_days:
        affected = daily.date.isin(pd.to_datetime(missing_days))
        daily.loc[affected, ["sales_qty", "order_count", "gross_revenue_vnd"]] = np.nan
        daily.loc[affected, "actual_available"] = False
    daily["target_definition_version"] = cfg["target_definition_version"]
    if not missing_days and int(daily.sales_qty.sum()) != int(sales.quantity.sum()):
        raise DataQualityError("Daily quantity does not conserve audited sales")
    return daily.sort_values(ROUTE + ["date"]).reset_index(drop=True)


def route_top(daily, cfg):
    train = daily.loc[daily.date.le(pd.Timestamp(cfg["train_end"]))]
    ranked = train.groupby(ROUTE).sales_qty.sum(min_count=1).reset_index(name="train_quantity")
    ranked = ranked.sort_values(["train_quantity"] + ROUTE, ascending=[False, True, True], kind="stable")
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    return ranked.head(cfg["top_n"]).reset_index(drop=True)


def observed_anomalies(daily, cfg):
    """After-observation diagnostics; history excludes the day being flagged."""
    params = cfg["anomalies"]
    frames = []
    for _, group in daily.groupby(ROUTE, sort=True):
        group = group.sort_values("date").copy()
        for column in ["sales_qty", "gross_revenue_vnd"]:
            series = group[column].astype(float)
            history = series.shift(1)
            median = history.rolling(params["history_days"], min_periods=params["minimum_history_days"]).median()
            mad = history.rolling(params["history_days"], min_periods=params["minimum_history_days"]).apply(lambda x: np.median(np.abs(x - np.median(x))), raw=True)
            delta = series - median
            robust_z = delta.abs() / (1.4826 * mad).clip(lower=1.0)
            relative = delta / median.replace(0, np.nan)
            flag = median.notna() & series.notna() & ((robust_z >= params["robust_z_threshold"]) | (relative.abs() >= params["relative_change_threshold"]))
            selected = group.loc[flag, ["date"] + ROUTE].copy()
            selected["indicator"] = column
            selected["observed_value"] = series[flag]
            selected["past_median"] = median[flag]
            selected["relative_change"] = relative[flag]
            selected["kind"] = np.where(delta[flag] < 0, "drop", "surge")
            selected["timing"] = "after_observation_not_advance_prediction"
            frames.append(selected)
    return pd.concat(frames, ignore_index=True)
