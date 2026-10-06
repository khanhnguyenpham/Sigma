"""Per-route SARIMA/SARIMAX, including log1p and annual regressors."""
import warnings
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
from M2.models.common import annual

ROUTE_MODEL = True


def fit(history, spec, cfg, settings, parameters=None):
    y = np.log1p(history) if spec.get('log1p') else history
    x = annual(history.index) if spec.get('annual_features') else None
    order, seasonal = tuple(spec['order']), tuple(spec['seasonal_order'])
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        estimator = SARIMAX(y.to_numpy(), exog=x, order=order, seasonal_order=seasonal,
            trend='c' if order[1] + seasonal[1] == 0 else 'n',
            enforce_stationarity=False, enforce_invertibility=False)
        state = estimator.fit(disp=False, maxiter=settings['sarima_maxiter'], start_params=parameters)
        if not state.mle_retvals.get('converged', False) and parameters is not None:
            state = estimator.fit(disp=False, maxiter=settings['sarima_maxiter'])
        warning_names = sorted({type(w.message).__name__ for w in captured})
    if not state.mle_retvals.get('converged', False):
        raise RuntimeError('SARIMA did not converge')
    return state, state.params, warning_names


def update(state, history, spec):
    last = history.iloc[-1]
    if spec.get('log1p'):
        last = np.log1p(last)
    return state.extend([last], exog=annual([history.index[-1]]) if spec.get('annual_features') else None)


def predict(state, dates, spec):
    values = np.asarray(state.forecast(len(dates), exog=annual(dates) if spec.get('annual_features') else None))
    return np.expm1(values) if spec.get('log1p') else values
