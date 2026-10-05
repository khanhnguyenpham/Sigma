"""Registered tree budgets affect real estimators and retain causal quantities."""
import numpy as np
import pandas as pd
import pytest

from sigma.forecasting.boosting import estimator_count, validate_budgets
from sigma.forecasting.weekly import prepare, fit, predict_batch
from test_weekly_forecast import settings, sample


@pytest.mark.parametrize('value', [True, 0, -1, 2.5, '300', 2001, None])
def test_invalid_budget_cannot_be_silently_ignored(value):
    with pytest.raises(ValueError, match='n_estimators'):
        validate_budgets({**settings(), 'models': {'bad': {'kind': 'lgbm', 'n_estimators': value}}})


def test_override_requires_boosted_model_and_old_default_is_preserved():
    cfg = settings()
    assert estimator_count({}, cfg) == 10
    with pytest.raises(ValueError, match='boosted'):
        validate_budgets({**cfg, 'models': {'bad': {'kind': 'mean', 'n_estimators': 300}}})


@pytest.mark.parametrize('kind', ['lgbm', 'local_week'])
def test_real_booster_budget_and_future_mutation(kind):
    cfg = settings()
    spec = {**cfg['models']['week_lgbm_l1_ratio'], 'kind': kind,
            'estimator': 'boosted_median', 'n_estimators': 23}
    cfg['models'] = {'candidate': spec}
    cutoff = pd.Timestamp('2025-04-30')
    daily = sample()
    changed = daily.copy()
    changed.loc[changed.date.gt(cutoff), ['sales_qty', 'order_count']] = 999999
    a, b = prepare(daily, cfg), prepare(changed, cfg)
    model, log = fit(a, cutoff, spec, {'seed': 42, 'lightgbm_threads': 1}, cfg)
    altered, other_log = fit(b, cutoff, spec, {'seed': 42, 'lightgbm_threads': 1}, cfg)
    estimators = [model] if kind == 'lgbm' else list(model.models.values())
    assert all(m.get_params()['n_estimators'] == 23 and m.n_estimators_ == 23 for m in estimators)
    assert log == other_log and log['max_label_end'] <= cutoff
    prediction = predict_batch(model, a, cutoff, spec)
    assert prediction == predict_batch(altered, b, cutoff, spec)
    assert all(np.isfinite(v) and v >= 0 for v in prediction.values())
