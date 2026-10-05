"""Separate route levels, empty annual history and causal local estimation."""
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from sigma.forecasting.weekly import prepare, fit, predict_batch
from sigma.forecasting.local import WeeklyLocal


def fixture(estimator):
    settings = json.loads((ROOT / 'config.weekly.json').read_text())
    spec = {'kind': 'local_week', 'estimator': estimator, 'objective': 'regression_l1',
        'units': 'ratio', 'annual_features': True, 'leaves': 7, 'harmonics': 2, 'alpha': .01}
    settings['models'] = {'local': spec}
    cfg = {'seed': 42, 'lightgbm_threads': 1}
    dates = pd.date_range('2024-01-01', '2025-09-30')
    daily = pd.concat([pd.DataFrame({'date': dates, 'destination_country': 'Fake',
        'carrier': carrier, 'sales_qty': amount, 'order_count': 1})
        for carrier, amount in [('A', 2.), ('B', 5.), ('C', 0.)]], ignore_index=True)
    return cfg, settings, spec, daily


@pytest.mark.parametrize('estimator', ['boosted_median', 'annual_median'])
def test_local_routes_restore_distinct_quantity_and_handle_empty_history(estimator):
    cfg, settings, spec, daily = fixture(estimator)
    prepared = prepare(daily, settings); origin = pd.Timestamp('2024-06-30')
    model, log = fit(prepared, origin, spec, cfg, settings)
    predicted = predict_batch(model, prepared, origin, spec)
    assert log['max_label_end'] <= origin
    for key, quantity in predicted.items():
        np.testing.assert_allclose(quantity, {'A': 14., 'B': 35., 'C': 0.}[key[0][1]], rtol=0, atol=1e-7)


@pytest.mark.parametrize('estimator', ['boosted_median', 'annual_median'])
def test_local_fits_imputation_and_predictions_ignore_future(estimator):
    cfg, settings, spec, daily = fixture(estimator)
    origin = pd.Timestamp('2025-06-30')
    daily.sales_qty += np.arange(len(daily)) % 8
    changed = daily.copy()
    changed.loc[changed.date.gt(origin), ['sales_qty', 'order_count']] = 999999.
    a, b = prepare(daily, settings), prepare(changed, settings)
    ma, la = fit(a, origin, spec, cfg, settings); mb, lb = fit(b, origin, spec, cfg, settings)
    assert la == lb
    assert predict_batch(ma, a, origin, spec) == predict_batch(mb, b, origin, spec)
    if estimator == 'annual_median':
        for route in ma.models:
            np.testing.assert_array_equal(ma.models[route][0].statistics_, mb.models[route][0].statistics_)


def test_local_predict_rejects_missing_route_and_unknown_estimator():
    cfg, settings, spec, daily = fixture('boosted_median')
    prepared = prepare(daily, settings); origin = pd.Timestamp('2025-06-30')
    model, _ = fit(prepared, origin, spec, cfg, settings)
    x = next(iter(prepared.values()))['x'].iloc[:1].assign(route_index=999)
    with pytest.raises(ValueError, match='No trained'):
        model.predict(x)
    with pytest.raises(ValueError, match='Unknown'):
        WeeklyLocal({**spec, 'estimator': 'unknown'}, cfg, settings).inputs(x)
