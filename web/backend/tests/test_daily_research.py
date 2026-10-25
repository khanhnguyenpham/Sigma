"""Protect validation-only research from future leakage and calendar gaps."""

import numpy as np
import pandas as pd
import pytest
from web.backend.research.daily_validation import examples, fit_rows, FEATURES, weighted_median


def synthetic():
    dates = pd.date_range("2024-01-01", "2025-09-30")
    return pd.DataFrame(
        dict(
            date=dates,
            destination_country="Example",
            carrier="Synthetic",
            sales_qty=np.arange(len(dates)) % 17,
            actual_available=True,
        )
    )


def test_research_future_mutation_cannot_change_features_or_fitting_labels():
    daily = synthetic()
    cutoff = pd.Timestamp("2025-06-30")
    before = examples(daily)
    changed = daily.copy()
    changed.loc[changed.date.gt(cutoff), "sales_qty"] = 99999
    after = examples(changed)
    pd.testing.assert_frame_equal(
        before.loc[before.as_of_date.le(cutoff), FEATURES],
        after.loc[after.as_of_date.le(cutoff), FEATURES],
    )
    pd.testing.assert_frame_equal(fit_rows(before, cutoff), fit_rows(after, cutoff))
    assert fit_rows(before, cutoff).target_date.max() <= cutoff


def test_mape_empirical_median_preserves_zero_semantics():
    assert weighted_median([0, 1, 1, 20]) == 1
    assert weighted_median([0, 0]) == 0
    frame = examples(synthetic())
    # Every available target, including zeros, remains in the evaluation frame.
    assert frame.actual_qty.eq(0).any()
    assert frame.horizon.max() == 14
    for changed in (
        synthetic().drop(index=100),
        synthetic().assign(actual_available=False),
    ):
        with pytest.raises(ValueError, match="complete observed"):
            examples(changed)
