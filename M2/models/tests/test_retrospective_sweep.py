"""The exploratory sweep keeps weak-validation candidates and checks full coverage."""
import numpy as np
import pandas as pd
import pytest

from M2.models.common import prediction_rows
from M2.models.retrospective_sweep import leaderboard, validate_pairs
from M2.models.focus_experiment import FOCUS


def test_all_candidates_rank_on_test_even_when_validation_is_worse():
    table = pd.DataFrame({'pool': ['a', 'a', 'b'], 'model': ['strong_val', 'weak_val', 'boundary'],
        'block': 1, 'cadence': 'daily_origins', 'mape_positive_pct': [21., 19., 20.],
        'mae': [10., 12., 11.], 'coverage': 1.})
    catalog = pd.DataFrame({'pool': ['a', 'a', 'b'], 'model': ['strong_val', 'weak_val', 'boundary'],
        'validation_mape_positive_pct': [10., 15., 12.]})
    result = leaderboard(table, catalog)
    assert result.model.tolist() == ['weak_val', 'boundary', 'strong_val']
    assert result.below_20_pct.tolist() == [True, False, False]
    assert result.ranking_basis.eq('test_retrospective_exploration').all()
    with pytest.raises(pd.errors.MergeError): leaderboard(table, pd.concat([catalog, catalog.iloc[:1]]))


def test_missing_pairs_and_split_boundary_labels_are_rejected():
    dates = pd.date_range('2025-09-01', '2026-01-15')
    series = pd.Series(2., index=dates)
    daily = pd.DataFrame({'date': dates, 'destination_country': FOCUS[0], 'carrier': FOCUS[1],
                          'sales_qty': 2., 'order_count': 1.})
    cfg = {'test_start': '2025-10-01', 'test_end': '2025-10-14'}
    rows = []
    for origin in pd.date_range('2025-09-30', '2025-10-13'):
        rows.extend(prediction_rows(series, FOCUS, 'Research', 'direct_7d', 'weak_val', 'test',
                                   origin, pd.Timestamp(cfg['test_end']), [14., 14.]))
    frame = pd.DataFrame(rows)
    assert validate_pairs(frame, daily, cfg, ['weak_val']) == 28
    with pytest.raises(AssertionError, match='Missing or duplicate'): validate_pairs(frame.iloc[1:], daily, cfg, ['weak_val'])
    bad = frame.copy(); bad.loc[bad.actual_qty.isna(), 'actual_qty'] = 14.
    with pytest.raises(AssertionError): validate_pairs(bad, daily, cfg, ['weak_val'])
    assert frame.actual_qty.isna().any() and np.isfinite(frame.forecast_qty).all()
