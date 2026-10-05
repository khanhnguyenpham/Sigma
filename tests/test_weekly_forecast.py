"""Independent weekly arithmetic, missingness and cutoff checks using fake data."""
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from weekly_forecast import prepare, checked_series, fit, predict_one, allocate_daily, metrics
from verify_weekly import validate_weekly
from src.common import sha256


def settings():
    value = json.loads((ROOT / 'config.weekly.json').read_text())
    value['n_estimators'] = 10
    value['min_child_samples'] = 5
    return value


def sample():
    dates = pd.date_range('2024-01-01', '2025-09-30')
    return pd.DataFrame({'date': dates, 'destination_country': 'Fake', 'carrier': 'A',
        'sales_qty': np.arange(len(dates), dtype=float) % 17 + 1,
        'order_count': np.ones(len(dates))})


def test_weekly_labels_are_exact_next_seven_day_sums_not_means():
    daily = sample(); origin = pd.Timestamp('2025-02-28')
    prepared = prepare(daily, settings())
    for block in (1, 2):
        table = prepared[(('Fake', 'A'), block)]
        idx = np.flatnonzero(table['origins'] == origin)[0]
        start = origin + pd.Timedelta(days=1 + 7 * (block - 1))
        expected = daily.loc[daily.date.between(start, start + pd.Timedelta(days=6)), 'sales_qty'].sum()
        assert table['y'][idx] == expected
    last = prepared[(('Fake', 'A'), 1)]
    assert np.isnan(last['y'][-1])  # Not-yet-observed is not zero.


def test_weekly_features_and_fit_ignore_every_future_sale():
    daily = sample(); cutoff = pd.Timestamp('2025-04-30'); cfg = {'seed': 42, 'lightgbm_threads': 1}
    changed = daily.copy()
    changed.loc[changed.date.gt(cutoff), ['sales_qty', 'order_count']] = 99999.
    before, after = prepare(daily, settings()), prepare(changed, settings())
    spec = settings()['models']['week_lgbm_l1_ratio']
    a, loga = fit(before, cutoff, spec, cfg, settings())
    b, logb = fit(after, cutoff, spec, cfg, settings())
    assert loga == logb and loga['max_label_end'] <= cutoff
    for key in before:
        mask = before[key]['origins'] <= cutoff
        pd.testing.assert_frame_equal(before[key]['x'].loc[mask], after[key]['x'].loc[mask])
        assert predict_one(a, before[key], cutoff, spec) == predict_one(b, after[key], cutoff, spec)


@pytest.mark.parametrize('problem', ['missing_day', 'missing_value', 'negative', 'duplicate'])
def test_weekly_incomplete_history_is_blocked(problem):
    daily = sample()
    if problem == 'missing_day':
        daily = daily.drop(index=150)
    elif problem == 'missing_value':
        daily.loc[150, 'sales_qty'] = np.nan
    elif problem == 'negative':
        daily.loc[150, 'sales_qty'] = -1
    else:
        daily = pd.concat([daily, daily.iloc[[150]]])
    with pytest.raises(ValueError):
        checked_series(daily)


def test_daily_allocation_conserves_week_and_never_reads_future():
    daily = sample(); origin = pd.Timestamp('2025-04-30')
    group = checked_series(daily)[('Fake', 'A')]
    dates, values = allocate_daily(73.25, group, origin, 2)
    group.loc[group.index > origin, 'sales_qty'] = 99999
    _, changed = allocate_daily(73.25, group, origin, 2)
    np.testing.assert_array_equal(values, changed)
    assert values.sum() == 73.25 and (values >= 0).all()
    assert dates[0] == pd.Timestamp('2025-05-08') and dates[-1] == pd.Timestamp('2025-05-14')
    group.loc[:, 'sales_qty'] = 0
    _, uniform = allocate_daily(70, group, origin, 1)
    np.testing.assert_allclose(uniform, 10)


def test_weekly_metrics_keep_zero_windows_and_show_incomplete_coverage():
    frame = pd.DataFrame({'destination_country': ['Fake'] * 2, 'carrier': ['A'] * 2,
        'model': ['fake'] * 2, 'week_block': [1, 1], 'as_of_date': pd.to_datetime(['2025-06-30', '2025-07-01']),
        'actual_qty_7d': [0., 10.], 'forecast_qty_7d': [5., 8.], 'weekly_cadence': [True, False]})
    result = metrics(frame, '2025-07-01', '2025-07-14')
    row = result.loc[result.cadence.eq('daily_origins')].iloc[0]
    assert row.mape_positive_week_pct == pytest.approx(20)
    assert row.mae_week_qty == 3.5 and row.wape_pct == 70.
    assert row.zero_windows == 1 and row.positive_windows == 1
    assert row.coverage == 2 / 8
    with pytest.raises(ValueError):
        metrics(pd.concat([frame, frame]), '2025-07-01', '2025-07-14')


def test_weekly_dashboard_rejects_tampered_artifacts(tmp_path):
    names = ['protocol.json', 'selected_weekly_models.csv', 'top_routes.csv', 'weekly_forecast.csv',
        'daily_allocation.csv', 'daily_sales.csv', 'test_weekly_predictions.csv',
        'validation_weekly_predictions.csv', 'test_weekly_metrics.csv', 'validation_weekly_metrics.csv',
        'selected_test_weekly_metrics.csv']
    for name in names:
        (tmp_path / name).write_text('fake fixture')
    summary = {'status': 'complete', 'kind': 'weekly_quantity_run',
        'selection_sha256': sha256(tmp_path / 'selected_weekly_models.csv'),
        'files': {name: sha256(tmp_path / name) for name in names}}
    (tmp_path / 'summary.json').write_text(json.dumps(summary))
    assert validate_weekly(tmp_path)['status'] == 'complete'
    (tmp_path / 'weekly_forecast.csv').write_text('modified')
    with pytest.raises(ValueError, match='changed'):
        validate_weekly(tmp_path)


def test_weekly_dashboard_rejects_parent_path_in_manifest(tmp_path):
    names = ['protocol.json', 'selected_weekly_models.csv', 'top_routes.csv', 'weekly_forecast.csv',
        'daily_allocation.csv', 'daily_sales.csv', 'test_weekly_predictions.csv',
        'validation_weekly_predictions.csv', 'test_weekly_metrics.csv', 'validation_weekly_metrics.csv',
        'selected_test_weekly_metrics.csv']
    for name in names:
        (tmp_path / name).write_text('fake fixture')
    outside = tmp_path.parent / 'outside_weekly.txt'
    outside.write_text('must not be accepted')
    summary = {'status': 'complete', 'kind': 'weekly_quantity_run',
        'selection_sha256': sha256(tmp_path / 'selected_weekly_models.csv'),
        'files': {name: sha256(tmp_path / name) for name in names}}
    summary['files']['../outside_weekly.txt'] = sha256(outside)
    (tmp_path / 'summary.json').write_text(json.dumps(summary))
    with pytest.raises(ValueError):
        validate_weekly(tmp_path)
