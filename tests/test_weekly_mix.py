"""Hand-calculated mixing objective and causal teacher/label guards."""
import numpy as np
import pandas as pd
import pytest

from sigma.forecasting.mix import optimal_weight, fit_mix, mixed_values


def test_mix_weight_minimizes_hand_calculated_relative_loss():
    assert optimal_weight([20, 20], [10, 10], [15, 15], 0) == .5
    assert optimal_weight([20, 20], [10, 10], [10, 10], 0) == 0
    assert optimal_weight([20, 20], [10, 10], [10, 10], 4) == .5
    assert optimal_weight([20], [10], [30], 0) == 1
    assert optimal_weight([0], [0], [0], 0) == .5
    key = (('Fake', 'A'), 1)
    assert mixed_values([{key: 20.}, {key: 10.}], {key: .5}) == {key: 15.}
    with pytest.raises(ValueError):
        mixed_values([{key: 20.}, {}], {key: .5})


def test_mixture_uses_only_completed_past_weeks():
    origin = pd.Timestamp('2025-06-30')
    dates = pd.date_range('2025-04-01', '2025-07-31')
    key = (('Fake', 'A'), 1)
    data = {key: {'origins': dates, 'ends': dates + pd.Timedelta(days=7), 'y': np.full(len(dates), 15.)}}
    settings = {'models': {'a': {'kind': 'lgbm'}, 'b': {'kind': 'linear_week'}}}
    spec = {'components': ['a', 'b'], 'history_days': 28, 'prior_weeks': 0}
    def fake_fit(prepared, cutoff, parent, *rest):
        return parent['kind'], {'max_label_end': cutoff}
    def fake_predict(model, prepared, cutoff, parent):
        return {key: 20. if model == 'lgbm' else 10.}
    before, log = fit_mix(data, origin, spec, {}, settings, {}, {}, fake_fit, fake_predict)
    data[key]['y'][data[key]['ends'] > origin] = 999999.
    after, _ = fit_mix(data, origin, spec, {}, settings, {}, {}, fake_fit, fake_predict)
    assert before == after == {key: .5} and log[0]['max_mix_label_end'] <= origin
    with pytest.raises(ValueError, match='future labels'):
        fit_mix(data, origin, spec, {}, settings, {}, {},
            lambda prepared, cutoff, *rest: (None, {'max_label_end': cutoff + pd.Timedelta(days=1)}), fake_predict)


def test_adaptive_mixture_phase_dispatch_preserves_component_units(tmp_path, monkeypatch):
    import json
    import sigma.forecasting.weekly as weekly_forecast
    from src.common import ROOT
    settings = json.loads((ROOT / 'data/configs/config.weekly.json').read_text())
    settings['models'] = {'a': {'kind': 'lgbm', 'units': 'raw', 'value': 7.},
        'b': {'kind': 'linear_week', 'units': 'raw', 'value': 21.},
        'mix': {'kind': 'adaptive_mix', 'components': ['a', 'b'], 'history_days': 28, 'prior_weeks': 0}}
    class FixedModel:
        def __init__(self, value):
            self.value = value
        def predict(self, x):
            return np.full(len(x), self.value)
    monkeypatch.setattr(weekly_forecast, 'fit', lambda prepared, cutoff, spec, *rest:
        (FixedModel(spec['value']), {'max_label_end': cutoff, 'training_pairs': 1}))
    daily = pd.DataFrame({'date': pd.date_range('2024-01-01', '2025-07-14'),
        'destination_country': 'Fake', 'carrier': 'A', 'sales_qty': 2., 'order_count': 1})
    result = weekly_forecast.phase(daily, {}, settings, '2025-07-01', '2025-07-14', 'validation', tmp_path)
    mixed = result.loc[result.model.eq('mix')]
    assert len(mixed) == 9
    np.testing.assert_allclose(mixed.forecast_qty_7d, 14., rtol=0, atol=1e-8)
    np.testing.assert_allclose(mixed.mixture_first_qty, 7., rtol=0, atol=1e-8)
    np.testing.assert_allclose(mixed.mixture_second_qty, 21., rtol=0, atol=1e-8)
    np.testing.assert_allclose(mixed.mixture_first_weight, .5, rtol=0, atol=1e-8)
