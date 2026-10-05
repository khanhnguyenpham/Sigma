"""Direct quantity MAPE candidates, with optional past-only feature scaling."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.count_models import monthly_calendar

MONTHLY_LAD_SPECS = {'monthlad_0_0p001': False, 'scaledmonthlad_0_0p001': True}


def fit_monthly_lad(history, origin, model_id):
    from sklearn.linear_model import QuantileRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.dummy import DummyRegressor
    origin = pd.Timestamp(origin)
    if model_id not in MONTHLY_LAD_SPECS:
        raise ValueError('Unknown monthly L1 model')
    past = history.loc[:origin]
    y = past.to_numpy(dtype=float)
    if not len(y) or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError('Monthly L1 requires complete nonnegative quantity history')
    x = monthly_calendar(past.index)
    if not y.any():
        estimator = DummyRegressor(strategy='constant', constant=0).fit(x,y)
    else:
        weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
        estimator = QuantileRegressor(quantile=.5, alpha=.001, solver='highs')
        if MONTHLY_LAD_SPECS[model_id]:
            estimator = make_pipeline(StandardScaler(), estimator)
            estimator.fit(x, y, quantileregressor__sample_weight=weights)
        else:
            estimator.fit(x, y, sample_weight=weights)
    return {'estimator': estimator, 'fit_cutoff': origin, 'training_rows': len(past)}


def predict_monthly_lad(state, targets):
    targets = pd.DatetimeIndex(targets)
    if not len(targets) or targets.min() <= state['fit_cutoff']:
        raise ValueError('Monthly L1 targets must follow the fit cutoff')
    predicted = np.asarray(state['estimator'].predict(monthly_calendar(targets)), dtype=float)
    if not np.isfinite(predicted).all():
        raise ValueError('Nonfinite monthly L1 forecast')
    # Caller clips/counts negative predictions, preserving the common protocol.
    return predicted
