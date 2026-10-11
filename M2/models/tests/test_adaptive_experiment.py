"""Age weighting, estimator parity, causal heads and actual refit cadence."""
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from M2.models.adaptive_experiment import weighted_batch, phase, verify
from M2.models.focus_experiment import candidates, prepare_parent, phase as previous_phase
from M2.models.tests.test_focus_experiment import data


def experiment():
    return json.loads((ROOT/'data/configs/m2-adaptive.json').read_text(encoding='utf-8'))


def test_age_weights_preserve_population_total_and_half_life():
    exp = experiment(); assert len(candidates(exp)) == 21
    daily, cfg, settings = data(); prepared = prepare_parent(daily, settings, {'scale_days': 56})
    cutoff = pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    spec = {'units': 'ratio', **settings['models']['LightGBM']['lgbm_annual_ratio7'], 'half_life_days': 56}
    x, y, w, log = weighted_batch(prepared, cutoff, spec, settings)
    expected, age = [], []
    for table in prepared.values():
        for i, end in enumerate(table['ends']):
            if cutoff-pd.Timedelta(days=settings['training_window_days']-1) <= end <= cutoff:
                expected.append(table['y'][i]/table['scale'][i]); age.append((cutoff-end).days)
    np.testing.assert_array_equal(y, expected)
    base = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
    raw = base*np.power(2., -np.array(age)/56)
    np.testing.assert_allclose(w, raw*base.sum()/raw.sum(), atol=1e-12, rtol=0)
    assert len(x) == len(y) == log['training_pairs'] and min(age) >= 0
    assert w.sum() == pytest.approx(base.sum())
    with pytest.raises(ValueError): weighted_batch(prepared, cutoff, {**spec, 'half_life_days': -1}, settings)


def test_real_estimator_control_and_residual_parity():
    daily, cfg, settings = data(); exp = experiment()
    exp['parents'] = {'adapt56': exp['parents']['adapt56']}
    current, log = phase(daily, cfg, settings, exp, 'validation')
    previous, _ = previous_phase(daily, cfg, settings, exp, 'validation')
    keys = ['model', 'as_of_date', 'block']
    np.testing.assert_array_equal(current.sort_values(keys).forecast_qty, previous.sort_values(keys).forecast_qty)
    assert verify(log, exp, daily, cfg, settings, 'validation')['heads'] == 12


def test_age_weighted_forecast_and_teacher_ignore_future_orders():
    daily, cfg, settings = data(); exp = experiment()
    exp['parents'] = {'adapt56_age56': exp['parents']['adapt56_age56']}; exp['residual_parents'] = []
    first, log = phase(daily, cfg, settings, exp, 'validation')
    cutoff = pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    changed = daily.copy(); changed.loc[changed.date > cutoff, ['sales_qty', 'order_count']] = 999999
    second, other_log = phase(changed, cfg, settings, exp, 'validation')
    np.testing.assert_array_equal(first.forecast_qty, second.forecast_qty)
    pd.testing.assert_frame_equal(log, other_log, check_exact=True)
    assert verify(log, exp, daily, cfg, settings, 'validation')['weighted_fits'] > 0
    tampered = log.copy(); index = tampered.index[tampered.status.eq('fit')][0]
    tampered.loc[index, 'weight_sha256'] = 'tampered'
    with pytest.raises(AssertionError): verify(tampered, exp, daily, cfg, settings, 'validation')


def test_refit_schedule_and_selected_only_predictions_match():
    daily, cfg, settings = data(); exp = experiment()
    cfg['validation_end'] = str(pd.Timestamp(cfg['validation_start'])+pd.Timedelta(days=7))[:10]
    exp['parents'] = {k: v for k, v in exp['parents'].items() if k in ['adapt56_refit1', 'adapt56_age56_refit3']}
    exp['residual_parents'] = []
    combined, log = phase(daily, cfg, settings, exp, 'validation')
    check = verify(log, exp, daily, cfg, settings, 'validation')
    assert check['applications'] == 64
    for parent, interval in [('adapt56_refit1', 1), ('adapt56_age56_refit3', 3)]:
        applications = log.loc[log.status.eq('applied') & log.parent.eq(parent)]
        assert applications.fit_cutoff.nunique() == (8+interval-1)//interval
        name = parent+'_mul56p4'
        selected, _ = phase(daily, cfg, settings, exp, 'validation', [name])
        np.testing.assert_array_equal(selected.forecast_qty, combined.loc[combined.model.eq(name), 'forecast_qty'])
