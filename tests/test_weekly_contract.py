"""Independent cutoff, quantity, pooling and missingness checks for final code."""
import numpy as np
import pandas as pd
import pytest

from M2.models.weekly import prepare, checked_series, fit, inputs, predict_batch, ANNUAL_FEATURES
from M2.models.common import target_history
from M2.models.calibration import relative_factor
from tests.test_final_parity import synthetic_bundle


def test_pooled_features_labels_and_fit_ignore_future():
    daily, cfg, settings, _ = synthetic_bundle()
    cutoff = pd.Timestamp('2025-09-30')
    changed = daily.copy()
    changed.loc[changed.date.gt(cutoff), ['sales_qty', 'order_count']] = 99999.
    settings = {**settings, 'blocks': [1, 2]}
    before, after = prepare(daily, settings), prepare(changed, settings)
    spec = {'kind': 'lgbm', 'units': 'ratio', **settings['models']['LightGBM']['lgbm_annual_ratio7']}
    for key, table in before.items():
        indices = np.flatnonzero(table['origins'] <= cutoff)
        pd.testing.assert_frame_equal(inputs(table, spec, indices), inputs(after[key], spec, indices))
        idx = np.flatnonzero(table['origins'] == pd.Timestamp('2025-02-28'))[0]
        start = pd.Timestamp('2025-02-28') + pd.Timedelta(days=1 + 7*(key[1]-1))
        part = daily.loc[daily.destination_country.eq(key[0][0]) & daily.carrier.eq(key[0][1])]
        assert table['y'][idx] == part.loc[part.date.between(start, start+pd.Timedelta(days=6)), 'sales_qty'].sum()
        # D+7 on 07/03/2025 uses the seven-day sum ending 07/03/2024.
        if key[1] == 1:
            expected = part.loc[part.date.between('2024-03-01', '2024-03-07'), 'sales_qty'].sum()
            assert table['x'].iloc[idx][ANNUAL_FEATURES[0]] == expected
        assert np.isnan(table['y'][-1])
    a, loga = fit(before, cutoff, spec, cfg, settings)
    b, logb = fit(after, cutoff, spec, cfg, settings)
    assert loga == logb
    assert loga == {'max_label_end': cutoff, 'training_pairs': 10*2*365}
    np.testing.assert_array_equal(list(predict_batch(a, before, cutoff, spec).values()),
                                  list(predict_batch(b, after, cutoff, spec).values()))


@pytest.mark.parametrize('problem', ['missing_day', 'missing_value', 'negative', 'duplicate'])
def test_incomplete_daily_history_is_blocked(problem):
    daily, _, _, _ = synthetic_bundle()
    if problem == 'missing_day': daily = daily.drop(index=150)
    elif problem == 'missing_value': daily.loc[150, 'sales_qty'] = np.nan
    elif problem == 'negative': daily.loc[150, 'sales_qty'] = -1
    else: daily = pd.concat([daily, daily.iloc[[150]]])
    with pytest.raises(ValueError): checked_series(daily)


def test_prophet_history_is_completed_rolling7_and_window540():
    series = pd.Series(np.arange(731.), index=pd.date_range('2024-01-01', periods=731))
    cutoff = pd.Timestamp('2025-09-30')
    history = target_history(series, 'direct_7d', cutoff,
        {'training_window_days': 540, 'minimum_history_days': 90})
    assert len(history) == 540 and history.index.max() == cutoff
    assert history.iloc[-1] == series.loc['2025-09-24':'2025-09-30'].sum()
    series.loc[series.index > cutoff] = 99999.
    pd.testing.assert_series_equal(history, target_history(series, 'direct_7d', cutoff,
        {'training_window_days': 540, 'minimum_history_days': 90}))


def test_multiplicative_head_prior_clip_and_invalid_history():
    assert relative_factor([10, 10], [20, 20], 0) == 1.5
    assert relative_factor([10, 10], [20, 20], 4) == 1.
    assert relative_factor([0], [0], 4) == 1.
    with pytest.raises(ValueError): relative_factor([10], [-1], 4)


def test_all_zero_pooled_history_stays_zero():
    daily, cfg, settings, _ = synthetic_bundle()
    daily[['sales_qty', 'order_count']] = 0.
    prepared = prepare(daily, {**settings, 'blocks': [1, 2]})
    spec = {'kind': 'lgbm', 'units': 'raw', **settings['models']['LightGBM']['lgbm_poisson']}
    model, _ = fit(prepared, pd.Timestamp('2025-09-30'), spec, cfg, settings)
    assert set(predict_batch(model, prepared, pd.Timestamp('2025-09-30'), spec).values()) == {0.}
