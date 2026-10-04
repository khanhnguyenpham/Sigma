from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from src.common import DataQualityError, sha256
from src.data import audit_orders, daily_sales, observed_anomalies, route_top


def test_success_without_activation_quantity_and_hash(cfg, order_rows, write_orders):
    path = write_orders(order_rows)
    before = sha256(path)
    sales, audit = audit_orders(path, cfg)
    assert sales.quantity.sum() == 3
    assert audit["activation_missing"] == 1
    assert before == sha256(path)
    daily = daily_sales(sales, cfg)
    assert len(daily) == 731
    assert daily.loc[daily.date.eq("2024-02-29"), "sales_qty"].item() == 3
    assert daily.sales_qty.sum() == 3


def test_offset_maps_to_next_utc_day(cfg, order_rows, write_orders):
    order_rows[0]["order_datetime"] = "2024-02-29T23:30:00-02:00"
    sales, _ = audit_orders(write_orders(order_rows), cfg)
    assert sales.date.iloc[0] == pd.Timestamp("2024-03-01")


@pytest.mark.parametrize("field,value", [("quantity", "0"), ("quantity", "1.5"), ("quantity", "-1"), ("order_datetime", "2024-01-01T00:00:00"), ("order_status", "mystery"), ("carrier", "")])
def test_invalid_target_blocks_without_private_values(cfg, order_rows, write_orders, field, value):
    order_rows[0][field] = value
    with pytest.raises(DataQualityError) as error:
        audit_orders(write_orders(order_rows), cfg)
    assert "synthetic-1" not in str(error.value)


def test_duplicate_same_and_conflicting(cfg, order_rows, write_orders):
    sales, audit = audit_orders(write_orders(order_rows * 2), cfg)
    assert sales.quantity.sum() == 3
    assert audit["duplicate_rows_removed"] == 1
    other = deepcopy(order_rows[0]); other["quantity"] = "4"
    with pytest.raises(DataQualityError, match="conflicting_duplicate"):
        audit_orders(write_orders(order_rows + [other]), cfg)


def test_bad_money_does_not_remove_valid_sales(cfg, order_rows, write_orders):
    order_rows[0]["gross_revenue_vnd"] = "999"
    sales, audit = audit_orders(write_orders(order_rows), cfg)
    assert sales.quantity.sum() == 3
    assert audit["revenue_mismatch_rows"] == 1
    daily = daily_sales(sales, cfg)
    assert np.isnan(daily.loc[daily.date.eq("2024-02-29"), "gross_revenue_vnd"].item())


def test_explicit_missing_day_not_zero(cfg, order_rows, write_orders):
    sales, _ = audit_orders(write_orders(order_rows), cfg)
    daily = daily_sales(sales, cfg, missing_days=["2024-03-01"])
    assert np.isnan(daily.loc[daily.date.eq("2024-03-01"), "sales_qty"].item())
    assert daily.loc[daily.date.eq("2024-03-02"), "sales_qty"].item() == 0


def test_top_train_and_anomaly_history_only(cfg):
    days = pd.date_range("2024-01-01", "2025-12-31")
    a = pd.DataFrame({"date": days, "destination_country": "A", "carrier": "C", "sales_qty": 10., "gross_revenue_vnd": 100.})
    b = a.copy(); b["destination_country"] = "B"; b["sales_qty"] = 1.
    b.loc[b.date.gt(cfg["train_end"]), "sales_qty"] = 10000
    assert route_top(pd.concat([a, b]), cfg).destination_country.iloc[0] == "A"
    shock = pd.Timestamp("2024-02-01")
    a.loc[a.date.eq(shock), "sales_qty"] = 0
    first = observed_anomalies(a, cfg)
    a.loc[a.date.gt(shock), "sales_qty"] = 9999
    second = observed_anomalies(a, cfg)
    pd.testing.assert_frame_equal(first[first.date.le(shock)].reset_index(drop=True), second[second.date.le(shock)].reset_index(drop=True))
    assert first.loc[first.date.eq(shock), "kind"].iloc[0] == "drop"
