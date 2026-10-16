from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from sigma.forecasting.aggregate import (prepare, row, metric_table, select,
    allocate_days, fit_lgbm, predict_lgbm, load_settings)


def history(n=620):
    days = pd.date_range('2024-01-01', periods=n)
    return pd.DataFrame({'date': days, 'destination_country': 'Syntheticland',
        'carrier': 'Syntheticcarrier', 'sales_qty': 3 + np.arange(n) % 7,
        'order_count': np.ones(n, dtype=int)})


@pytest.mark.parametrize('window', [7, 30])
def test_future_quantities_cannot_change_features_or_fit(window, cfg):
    _, settings = load_settings(); settings = deepcopy(settings)
    settings['lightgbm']['trees'] = 8
    settings['lightgbm']['min_child_samples'] = 10
    settings['lightgbm']['threads'] = 1
    daily = history(); origin = pd.Timestamp('2025-06-30')
    future = daily.copy(); future.loc[future.date.gt(origin), ['sales_qty', 'order_count']] *= 100
    a, b = prepare(daily, window, settings), prepare(future, window, settings)
    key = ('Syntheticland', 'Syntheticcarrier')
    mask = a[key]['origins'] <= origin
    pd.testing.assert_frame_equal(a[key]['x'].loc[mask], b[key]['x'].loc[mask])
    np.testing.assert_array_equal(a[key]['scale'][mask], b[key]['scale'][mask])
    spec = settings['models']['lgbm_annual_ratio7']
    model_a, log_a = fit_lgbm(a, origin, spec, cfg, settings)
    model_b, log_b = fit_lgbm(b, origin, spec, cfg, settings)
    assert log_a == log_b and log_a['max_label_end'] <= origin
    assert predict_lgbm(model_a, a, origin, spec) == predict_lgbm(model_b, b, origin, spec)


def test_month_total_is_next_thirty_days_not_next_day_rolling():
    daily = history(); _, settings = load_settings()
    key = ('Syntheticland', 'Syntheticcarrier')
    table = prepare(daily, 30, settings)[key]
    origin = pd.Timestamp('2025-06-30')
    i = np.flatnonzero(table['origins'] == origin)[0]
    expected = daily.loc[daily.date.between('2025-07-01', '2025-07-30'), 'sales_qty'].sum()
    assert table['y'][i] == expected
    assert table['ends'][i] == pd.Timestamp('2025-07-30')


def test_incomplete_validation_window_does_not_expose_test_label():
    daily = history(); group = daily.set_index('date')
    key = ('Syntheticland', 'Syntheticcarrier')
    a = row(group, key, 'fixed', 'validation', pd.Timestamp('2025-09-15'), 30, 100, pd.Timestamp('2025-09-30'))
    assert pd.isna(a['actual_qty'])
    b = row(group, key, 'fixed', 'future', pd.Timestamp('2025-06-30'), 30, 100, daily.date.max())
    assert pd.isna(b['actual_qty'])


@pytest.mark.parametrize('window,expected,nonoverlap', [(7, 86, 13), (30, 63, 3)])
def test_counts_from_calendar_and_missing_forecast_reduce_coverage(window, expected, nonoverlap, cfg):
    group = history(731).set_index('date'); key = ('Syntheticland', 'Syntheticcarrier')
    origins = pd.date_range('2025-09-30', '2025-12-30')
    frame = pd.DataFrame([row(group, key, 'fixed', 'test', o, window, 100, pd.Timestamp('2025-12-31')) for o in origins])
    metrics = metric_table(frame, cfg)
    assert list(metrics.n_expected) == [expected, nonoverlap]
    assert metrics.coverage.eq(1).all()
    frame.loc[0, 'forecast_qty'] = np.nan
    reduced = metric_table(frame, cfg)
    assert reduced.iloc[0].n_scored_pairs == expected-1
    assert reduced.iloc[0].coverage < 1


def test_hand_computed_metric_and_selection_reject_test(cfg):
    dates = pd.date_range('2025-06-30', '2025-09-29')
    rows = []
    for model, pred in [('good', 33.), ('bad', 60.)]:
        for origin in dates:
            rows.append({'window_days':30, 'destination_country':'Syntheticland', 'carrier':'Syntheticcarrier',
                'model':model,'split':'validation','as_of_date':origin,'target_date':origin+pd.Timedelta(days=30),
                'forecast_qty':pred,'actual_qty':30. if origin+pd.Timedelta(days=30)<=pd.Timestamp('2025-09-30') else np.nan})
    frame = pd.DataFrame(rows); m = metric_table(frame, cfg).iloc[2]
    assert m.mape_positive_pct == pytest.approx(10.)
    assert m.mae == 3 and m.wape_pct == pytest.approx(10.) and m.bias == 3
    assert select(frame, cfg).model.iloc[0] == 'good'
    with pytest.raises(ValueError, match='Only validation'):
        select(frame.assign(split='test'), cfg)


def test_allocations_conserve_both_windows_and_never_invent_actual():
    daily = history(731); key = ('Syntheticland', 'Syntheticcarrier'); group = daily.set_index('date')
    origin = pd.Timestamp('2025-09-30')
    preds = pd.DataFrame([row(group,key,'fixed','test',origin,w,float(w*9),pd.Timestamp('2025-12-31')) for w in [7,30]])
    out = allocate_days(preds, daily)
    assert len(out) == 37 and out.actual_qty.isna().all()
    assert out.groupby('window_days').forecast_qty.sum().to_dict() == {7:63.,30:270.}
    changed = daily.copy();changed.loc[changed.date.gt(origin),'sales_qty'] = 999
    pd.testing.assert_frame_equal(out, allocate_days(preds, changed))
