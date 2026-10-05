import numpy as np
import pandas as pd
import pytest

from weekly_calibration import relative_factor, fit_factors


def test_weekly_calibration_factor_minimizes_relative_error_with_bounded_prior():
    assert relative_factor([20, 20, 20], [10, 10, 10], 0) == .5
    assert relative_factor([10, 10], [30, 30], 0) == 1.5
    assert relative_factor([20, 20], [10, 10], 8) == 1.
    assert relative_factor([0, 0], [0, 10], 0) == 1.
    with pytest.raises(ValueError):
        relative_factor([20, 20], [10, -1], 0)
    with pytest.raises(ValueError):
        relative_factor([20, np.nan], [10, 10], 0)


def test_weekly_calibration_labels_after_cutoff_never_affect_factors():
    cutoff = pd.Timestamp('2025-06-30')
    origins = pd.date_range('2025-05-01', '2025-07-31')
    key = (('Fake', 'A'), 1)
    table = {'origins': origins, 'ends': origins + pd.Timedelta(days=7),
        'y': np.full(len(origins), 10.)}
    prepared = {key: table}
    seen = []
    def fake_fit(prepared, past, spec, cfg, settings):
        seen.append(past)
        return None, {'max_label_end': past}
    def fake_predict(model, prepared, past, spec):
        return {key: 20.}
    spec = {'parent': 'fake', 'history_days': 28, 'prior_weeks': 0}
    settings = {'models': {'fake': {'kind': 'lgbm'}}}
    a, logs = fit_factors(prepared, cutoff, spec, {}, settings, {}, {}, fake_fit, fake_predict)
    changed = {key: {**table, 'y': table['y'].copy()}}
    changed[key]['y'][table['ends'] > cutoff] = 99999.
    b, _ = fit_factors(changed, cutoff, spec, {}, settings, {}, {}, fake_fit, fake_predict)
    assert a == b == {key: .5}
    assert max(seen) <= cutoff - pd.Timedelta(days=7)
    assert logs[0]['max_head_label_end'] <= cutoff


def test_weekly_calibration_blocks_teacher_future_fit():
    key = (('Fake', 'A'), 1); origins = pd.date_range('2025-05-01', '2025-07-31')
    prepared = {key: {'origins': origins, 'ends': origins + pd.Timedelta(days=7), 'y': np.ones(len(origins))}}
    def bad_fit(prepared, past, spec, cfg, settings):
        return None, {'max_label_end': past + pd.Timedelta(days=1)}
    with pytest.raises(ValueError, match='after its forecast origin'):
        fit_factors(prepared, pd.Timestamp('2025-06-30'), {'parent': 'fake', 'history_days': 28, 'prior_weeks': 0},
            {}, {'models': {'fake': {'kind': 'lgbm'}}}, {}, {}, bad_fit, lambda *args: {key: 1.})
