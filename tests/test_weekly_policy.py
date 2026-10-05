"""Complete-tail coverage, parent quantity conservation and causal refit clocks."""
import copy
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from sigma.inventory.policy import full_policy_forecast, scenarios


def fixture():
    cfg = json.loads((ROOT / 'config.json').read_text())
    cfg.update(test_start='2025-07-01', test_end='2025-07-14', forecast_origin='2025-07-14')
    settings = json.loads((ROOT / 'config.weekly.json').read_text())
    settings['models'] = {'base': {'kind': 'mean', 'window': 28}}
    data = pd.DataFrame({'date': pd.date_range('2024-01-01', '2025-07-14'),
        'destination_country': 'Fake', 'carrier': 'A', 'sales_qty': 3., 'order_count': 1})
    prior = pd.DataFrame({'destination_country': 'Fake', 'carrier': 'A',
        'as_of_date': pd.Timestamp('2025-06-30'), 'week_block': [1, 2], 'forecast_qty_7d': [7., 14.]})
    latest = prior.assign(as_of_date=pd.Timestamp('2025-07-14'), forecast_qty_7d=[28., 35.])
    return prior, latest, data, {('Fake', 'A'): 'base'}, cfg, settings


def test_full_policy_tail_has_h14_including_after_observation_end():
    result, _ = full_policy_forecast(*fixture())
    assert len(result) == 15 * 14
    assert result.target_date.max() == pd.Timestamp('2025-07-28')
    assert result.actual_qty.isna().all()
    first = result.loc[result.as_of_date.eq('2025-06-30')]
    np.testing.assert_allclose(first.forecast_qty, [1.] * 7 + [2.] * 7, rtol=0, atol=1e-8)
    tail = result.loc[result.as_of_date.eq('2025-07-01')]
    np.testing.assert_allclose(tail.forecast_qty, 3., rtol=0, atol=1e-8)
    latest = result.loc[result.as_of_date.eq('2025-07-14')]
    np.testing.assert_allclose(latest.forecast_qty, [4.] * 7 + [5.] * 7, rtol=0, atol=1e-8)


def test_policy_tail_forecast_uses_only_history_through_origin():
    args = list(fixture())
    before, _ = full_policy_forecast(*args)
    args[2].loc[args[2].date.gt('2025-07-03'), ['sales_qty', 'order_count']] = 999999.
    after, _ = full_policy_forecast(*args)
    pd.testing.assert_frame_equal(before.loc[before.as_of_date.le('2025-07-03')],
        after.loc[after.as_of_date.le('2025-07-03')])
    args[0] = pd.concat([args[0], args[0].iloc[:1]])
    with pytest.raises(ValueError, match='Duplicate'):
        full_policy_forecast(*args)


def test_tail_refits_anchor_to_parent_start_and_block_future_fit(monkeypatch):
    import sigma.inventory.policy as weekly_policy
    args = list(fixture())
    args[-1]['models']['base'] = {'kind': 'lgbm'}
    seen = []
    def fake_fit(prepared, cutoff, *rest):
        seen.append(cutoff)
        return None, {'max_label_end': cutoff, 'training_pairs': 1}
    monkeypatch.setattr(weekly_policy, 'fit', fake_fit)
    monkeypatch.setattr(weekly_policy, 'predict_batch', lambda model, prepared, origin, spec: {key: 21. for key in prepared})
    full_policy_forecast(*args)
    assert seen == [pd.Timestamp('2025-06-30'), pd.Timestamp('2025-07-07')]
    monkeypatch.setattr(weekly_policy, 'fit', lambda prepared, cutoff, *rest:
        (None, {'max_label_end': cutoff + pd.Timedelta(days=1), 'training_pairs': 1}))
    with pytest.raises(ValueError, match='future labels'):
        full_policy_forecast(*args)


def test_policy_sensitivity_keeps_parent_config_and_other_axes():
    cfg = fixture()[-2]
    cfg['inventory']['partners'] = {'P': {'lead_time_days': 3, 'review_days': 1, 'safety_days': 2, 'moq': 1}}
    before = copy.deepcopy(cfg)
    result = scenarios(cfg)
    assert cfg == before and len(result) == 13
    cover_cfg = next(c for c, s in result if s['name'] == 'sensitivity_cover_14')
    lead_cfg = next(c for c, s in result if s['name'] == 'sensitivity_lead_7')
    assert cover_cfg['inventory']['partners'] == cfg['inventory']['partners']
    assert lead_cfg['inventory']['initial_cover_days'] == cfg['inventory']['initial_cover_days']


def test_adaptive_mixture_tail_uses_completed_teacher_weeks(monkeypatch):
    import sigma.inventory.policy as weekly_policy
    args = list(fixture())
    args[-1]['models'] = {'a': {'kind': 'lgbm', 'value': 7.},
        'b': {'kind': 'linear_week', 'value': 35.},
        'base': {'kind': 'adaptive_mix', 'components': ['a', 'b'], 'history_days': 28, 'prior_weeks': 4}}
    monkeypatch.setattr(weekly_policy, 'fit', lambda prepared, cutoff, spec, *rest:
        (None, {'max_label_end': cutoff, 'training_pairs': 1}))
    monkeypatch.setattr(weekly_policy, 'predict_batch', lambda model, prepared, origin, spec:
        {key: spec['value'] for key in prepared})
    forecast, log = full_policy_forecast(*args)
    np.testing.assert_allclose(forecast.loc[forecast.basis.eq('causal_tail_forecast'), 'forecast_qty'], 3., rtol=0, atol=1e-8)
    assert log.loc[log.role.eq('mix'), 'max_label_end'].le(log.loc[log.role.eq('mix'), 'fit_cutoff']).all()
