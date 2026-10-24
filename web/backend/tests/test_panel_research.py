import numpy as np
import pandas as pd
import pytest
from M3.research import daily_panel as panel
from test_daily_research import synthetic
from M3.research.daily_validation import evaluate_frame


def market():
    first = synthetic()
    first["order_count"] = np.ceil(first.sales_qty / 2).astype(int)
    other = first.assign(carrier="Other", sales_qty=first.sales_qty * 2)
    other["order_count"] = np.ceil(other.sales_qty / 3).astype(int)
    return pd.concat([first, other], ignore_index=True)


def test_market_and_annual_features_ignore_all_future_sales_and_counts():
    data = market()
    cutoff = pd.Timestamp("2025-06-30")
    top = {("Example", "Synthetic")}
    before = panel.enrich(data, top)
    changed = data.copy()
    changed.loc[changed.date.gt(cutoff), ["sales_qty", "order_count"]] = 999999
    after = panel.enrich(changed, top)
    pd.testing.assert_frame_equal(
        before.loc[before.as_of_date.le(cutoff), panel.FEATURES],
        after.loc[after.as_of_date.le(cutoff), panel.FEATURES],
    )
    assert before.loc[before.target_date.lt("2024-12-30"), "annual364"].isna().all()
    assert before.loc[before.target_date.ge("2025-01-01"), "annual366"].notna().all()


def test_missing_market_day_and_impossible_counts_are_blocked():
    data = market()
    top = {("Example", "Synthetic")}
    with pytest.raises(ValueError, match="complete observed"):
        panel.enrich(data.drop(index=0), top)
    bad = data.copy()
    bad.loc[bad.sales_qty.gt(0), "order_count"] = 0
    with pytest.raises(ValueError, match="complete observed"):
        panel.enrich(bad, top)


def test_evaluator_rejects_target_features_and_test_labels():
    frame = pd.DataFrame(
        {
            "as_of_date": [pd.Timestamp("2025-09-30")],
            "target_date": [pd.Timestamp("2025-10-01")],
            "horizon": [1],
            "actual_qty": [9],
        }
    )
    with pytest.raises(ValueError, match="Target values"):
        evaluate_frame(frame, ["actual_qty"], panel.PROTOCOL)
    with pytest.raises(ValueError, match="validation boundary"):
        evaluate_frame(frame, ["horizon"], panel.PROTOCOL)
