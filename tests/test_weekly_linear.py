"""Causal scaler/model, quantity restoration and missing route rejection."""
import json
import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from sigma.forecasting.weekly import prepare, fit, predict_batch


def config():
    settings = json.loads((ROOT / 'data/configs/config.weekly.json').read_text())
    spec = {'kind': 'linear_week', 'objective': 'regression_l1', 'units': 'ratio', 'harmonics': 2, 'alpha': .01}
    settings['models'] = {'linear': spec}
    cfg = {'seed': 42, 'lightgbm_threads': 1}
    return cfg, settings, spec


def daily():
    dates = pd.date_range('2024-01-01', '2025-09-30')
    return pd.DataFrame({'date': dates, 'destination_country': 'Fake', 'carrier': 'A',
        'sales_qty': 2., 'order_count': 1})


def test_weekly_linear_restores_quantity_and_all_zero_is_zero():
    cfg, settings, spec = config()
    for amount in [0., 2.]:
        data = daily().assign(sales_qty=amount)
        prepared = prepare(data, settings)
        origin = pd.Timestamp('2025-06-30')
        model, log = fit(prepared, origin, spec, cfg, settings)
        assert log['max_label_end'] <= origin
        np.testing.assert_allclose(list(predict_batch(model, prepared, origin, spec).values()), amount * 7, rtol=0, atol=1e-8)


def test_weekly_linear_scaler_fit_and_predictions_ignore_future_mutation():
    cfg, settings, spec = config()
    data = daily(); origin = pd.Timestamp('2025-06-30')
    data['sales_qty'] += np.arange(len(data)) % 9
    changed = data.copy()
    changed.loc[changed.date.gt(origin), ['sales_qty', 'order_count']] = 999999.
    a, b = prepare(data, settings), prepare(changed, settings)
    ma, la = fit(a, origin, spec, cfg, settings)
    mb, lb = fit(b, origin, spec, cfg, settings)
    assert la == lb
    assert predict_batch(ma, a, origin, spec) == predict_batch(mb, b, origin, spec)
    for route in ma.models:
        np.testing.assert_array_equal(ma.models[route][0].mean_, mb.models[route][0].mean_)
    with pytest.raises(ValueError, match='No trained'):
        x = a[(('Fake', 'A'), 1)]['x'].iloc[:1].assign(route_index=999)
        ma.predict(x)
