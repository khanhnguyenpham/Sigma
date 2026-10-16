from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from sigma.experiments.aggregate_calibration import specifications, factor_at, adjust, completed_labels


@pytest.fixture
def options():
    return json.loads((ROOT / 'data/configs/aggregate-calibration.json').read_text())


def residual_history(n=60):
    ends = pd.date_range('2025-06-01', periods=n)
    return pd.DataFrame({'as_of_date': ends-pd.Timedelta(days=30), 'target_date': ends,
        'forecast_qty': 90., 'actual_qty': 100.})


def test_registered_pool_has_thirteen_candidates_and_identity(options):
    specs = specifications(options)
    assert len(specs) == 13 and specs['identity']['estimator'] == 'identity'


@pytest.mark.parametrize('estimator', ['sum_ratio', 'mape_median'])
def test_future_incomplete_window_cannot_change_factor(options, estimator):
    history = residual_history()
    origin = pd.Timestamp('2025-07-01')
    spec = {'estimator': estimator, 'lookback_days': 28, 'shrinkage': 1.}
    expected = factor_at(history, origin, spec, options)
    mutated = history.copy()
    mutated.loc[mutated.target_date.gt(origin), ['actual_qty', 'forecast_qty']] = [999999., 1.]
    assert factor_at(mutated, origin, spec, options) == expected
    assert expected[0] == pytest.approx(100 / 90)
    assert expected[1] == 28 and expected[2] == origin


def test_mape_optimal_factor_is_weighted_median_not_average(options):
    opts = deepcopy(options); opts['minimum_completed_windows'] = 2; opts['factor_bounds'] = [.25, 2.]
    frame = residual_history(2).assign(forecast_qty=[20., 100.], actual_qty=[10., 100.])
    factor, count, last = factor_at(frame, '2025-06-02',
        {'estimator': 'mape_median', 'lookback_days': 28, 'shrinkage': 1.}, opts)
    assert factor == .5 and count == 2 and last == pd.Timestamp('2025-06-02')


def test_zero_label_and_no_completed_history_are_not_fabricated(options):
    frame = residual_history().assign(actual_qty=0.)
    spec = {'estimator': 'sum_ratio', 'lookback_days': 28, 'shrinkage': 1.}
    f, n, last = factor_at(frame, '2025-07-01', spec, options)
    assert f == 1 and n == 0 and pd.isna(last)
    f, n, _ = factor_at(residual_history(), '2025-05-01', spec, options)
    assert f == 1 and n == 0


def test_adjust_keeps_zero_and_missing_evaluation_labels(options):
    frame = residual_history(2).assign(destination_country='Synthetic', carrier='Synthetic',
        window_days=30, split='validation', model='base', actual_qty=[0., np.nan])
    result, audit = adjust(frame, residual_history(), {'estimator': 'identity'}, options, 'base__identity')
    assert len(result) == 2 and result.actual_qty.iloc[0] == 0 and pd.isna(result.actual_qty.iloc[1])
    assert result.forecast_qty.eq(90).all() and audit.factor.eq(1).all()


def test_completed_labels_align_thirty_days_and_future_mutation(options):
    daily = pd.DataFrame({'date': pd.date_range('2025-01-01', periods=90),
        'destination_country': 'Synthetic', 'carrier': 'Synthetic', 'sales_qty': np.arange(90)+1})
    frame = pd.DataFrame({'destination_country': 'Synthetic', 'carrier': 'Synthetic',
        'window_days': 30, 'as_of_date': pd.to_datetime(['2025-01-31', '2025-02-01']),
        'target_date': pd.to_datetime(['2025-03-02', '2025-03-03']), 'forecast_qty': [100., 100.], 'actual_qty': [np.nan, np.nan]})
    result = completed_labels(frame, daily)
    assert result.actual_qty.iloc[0] == daily.loc[daily.date.between('2025-02-01', '2025-03-02'), 'sales_qty'].sum()
    assert result.actual_qty.iloc[1] == daily.loc[daily.date.between('2025-02-02', '2025-03-03'), 'sales_qty'].sum()
    spec = {'estimator': 'sum_ratio', 'lookback_days': 84, 'shrinkage': 1.}
    origin = pd.Timestamp('2025-03-02')
    changed = daily.copy(); changed.loc[changed.date.gt(origin), 'sales_qty'] *= 100
    assert factor_at(result, origin, spec, options) == factor_at(completed_labels(frame, changed), origin, spec, options)


def test_nonfinite_past_forecast_rejected(options):
    history = residual_history(); history.loc[0, 'forecast_qty'] = np.inf
    with pytest.raises(ValueError, match='Invalid historical'):
        factor_at(history, '2025-06-15', {'estimator': 'sum_ratio', 'lookback_days': 28, 'shrinkage': .5}, options)
