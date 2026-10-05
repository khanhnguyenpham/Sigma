"""Hand-computed calibrated mixtures and causal phase/policy integration."""
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from sigma.forecasting.combine import calibrated_blend_values


def test_calibrated_combination_preserves_quantity_and_convex_weights():
    key = (('Fake', 'A'), 1)
    assert calibrated_blend_values([{key: 7.}, {key: 21.}], {key: .5}, [.5, .5]) == {key: 12.25}
    assert calibrated_blend_values([{key: 0.}, {key: 0.}], {key: 1.5}, [.25, .75]) == {key: 0.}
    for values, factors, weights in [([{key: 7.}, {}], {key: 1.}, [.5, .5]),
        ([{key: 7.}, {key: 21.}], {key: 2.}, [.5, .5]),
        ([{key: 7.}, {key: 21.}], {key: 1.}, [.5, .6]),
        ([{key: -1.}, {key: 21.}], {key: 1.}, [.5, .5])]:
        with pytest.raises(ValueError):
            calibrated_blend_values(values, factors, weights)


def test_calibrated_combination_phase_uses_only_completed_teacher_labels(tmp_path, monkeypatch):
    import sigma.forecasting.weekly as weekly_forecast
    settings = json.loads((ROOT / 'config.weekly.json').read_text())
    settings['models'] = {'a': {'kind': 'lgbm', 'units': 'raw', 'value': 7.},
        'b': {'kind': 'linear_week', 'units': 'raw', 'value': 21.},
        'mix': {'kind': 'calibrated_blend', 'components': ['a', 'b'], 'parent': 'a',
            'history_days': 28, 'prior_weeks': 0, 'weights': [.5, .5]}}
    class FixedModel:
        def __init__(self, value):
            self.value = value
        def predict(self, x):
            return np.full(len(x), self.value)
    monkeypatch.setattr(weekly_forecast, 'fit', lambda prepared, cutoff, spec, *rest:
        (FixedModel(spec['value']), {'max_label_end': cutoff, 'training_pairs': 1}))
    daily = pd.DataFrame({'date': pd.date_range('2024-01-01', '2025-07-14'),
        'destination_country': 'Fake', 'carrier': 'A', 'sales_qty': 2., 'order_count': 1})
    before = weekly_forecast.phase(daily, {}, settings, '2025-07-01', '2025-07-14', 'validation', tmp_path)
    mixed = before.loc[before.model.eq('mix')]
    np.testing.assert_allclose(mixed.forecast_qty_7d, 15.75, atol=1e-8, rtol=0)
    np.testing.assert_allclose(mixed.component_calibration_factor, 1.5, atol=1e-8, rtol=0)
    changed = daily.copy(); changed.loc[changed.date.gt('2025-06-30'), 'sales_qty'] = 999999.
    after = weekly_forecast.phase(changed, {}, settings, '2025-07-01', '2025-07-14', 'validation', tmp_path)
    np.testing.assert_allclose(after.loc[after.model.eq('mix') & after.as_of_date.le('2025-07-06'), 'forecast_qty_7d'],
        mixed.loc[mixed.as_of_date.le('2025-07-06'), 'forecast_qty_7d'], atol=1e-8, rtol=0)


def test_calibrated_combination_full_tail_respects_teacher_and_quantity(monkeypatch):
    import sigma.inventory.policy as weekly_policy
    from test_weekly_policy import fixture
    args = list(fixture())
    args[-1]['models'] = {'a': {'kind': 'lgbm', 'value': 7.}, 'b': {'kind': 'linear_week', 'value': 35.},
        'base': {'kind': 'calibrated_blend', 'components': ['a', 'b'], 'parent': 'a',
            'history_days': 28, 'prior_weeks': 0, 'weights': [.5, .5]}}
    monkeypatch.setattr(weekly_policy, 'fit', lambda prepared, cutoff, spec, *rest:
        (None, {'max_label_end': cutoff, 'training_pairs': 1}))
    monkeypatch.setattr(weekly_policy, 'predict_batch', lambda model, prepared, origin, spec:
        {key: spec['value'] for key in prepared})
    forecast, logs = weekly_policy.full_policy_forecast(*args)
    np.testing.assert_allclose(forecast.loc[forecast.basis.eq('causal_tail_forecast'), 'forecast_qty'], 3.25, atol=1e-8, rtol=0)
    assert logs.loc[logs.role.eq('head'), 'max_label_end'].le(logs.loc[logs.role.eq('head'), 'fit_cutoff']).all()
