"""Per-route Prophet variants for daily quantity or end-dated rolling totals."""
import logging
import os
import pandas as pd
from src.common import ROOT

ROUTE_MODEL = True


def fit(history, spec, cfg, settings, parameters=None):
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache' / 'matplotlib'))
    from prophet import Prophet
    logging.getLogger('cmdstanpy').disabled = True
    logging.getLogger('prophet').setLevel(logging.ERROR)
    options = {key: value for key, value in spec.items() if key not in ('training_window_days', 'targets')}
    options.setdefault('yearly_seasonality', 3)
    state = Prophet(**options, daily_seasonality=False,
                    uncertainty_samples=0, n_changepoints=10)
    state.fit(pd.DataFrame({'ds': history.index, 'y': history.to_numpy()}), seed=cfg['seed'])
    return state, None, []


def update(state, history, spec):
    # Coefficients remain fixed between scheduled refits.
    return state


def predict(state, dates, spec):
    return state.predict(pd.DataFrame({'ds': dates})).yhat.to_numpy()
