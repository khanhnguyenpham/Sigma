"""Shared target windows and forecast row contract for M2 models."""
import numpy as np
import pandas as pd
from src.common import ROUTE

TARGETS = ('daily', 'direct_7d')
COLUMNS = ROUTE + ['family', 'target', 'model', 'split', 'as_of_date', 'target_date',
                   'window_start', 'horizon_day', 'block', 'forecast_qty', 'actual_qty']


def active_variants(settings, family, target):
    return {name: spec for name, spec in settings['models'][family].items()
            if target in spec.get('targets', TARGETS)}


def effective_settings(settings, spec):
    keys = ('training_window_days', 'n_estimators', 'min_child_samples')
    return {**settings, **{key: spec[key] for key in keys if key in spec}}

def annual(dates):
    angle = 2 * np.pi * pd.DatetimeIndex(dates).dayofyear.to_numpy() / 365.25
    return np.column_stack([np.sin(angle), np.cos(angle)])



def target_history(series, target, origin, settings):
    observed = series.loc[:origin]
    if target == 'direct_7d':
        observed = observed.rolling(7, min_periods=7).sum().dropna()
    elif target != 'daily':
        raise ValueError('Unknown target')
    observed = observed.iloc[-settings['training_window_days']:]
    if len(observed) < settings['minimum_history_days'] or not np.isfinite(observed).all():
        raise ValueError('Incomplete training history')
    return observed



def prediction_rows(series, keys, family, target, model, split, origin, end, predictions):
    result = []
    horizons = range(1, 15) if target == 'daily' else (7, 14)
    for h, value in zip(horizons, predictions, strict=True):
        finish = origin + pd.Timedelta(days=h)
        start = finish if target == 'daily' else finish - pd.Timedelta(days=6)
        actual = np.nan
        if finish <= end and start >= series.index.min():
            observed = series.loc[start:finish]
            expected = 1 if target == 'daily' else 7
            if len(observed) == expected and np.isfinite(observed).all():
                actual = float(observed.sum())
        result.append(dict(zip(COLUMNS, [*keys, family, target, model, split, origin,
            finish, start, h, 1 if h <= 7 else 2, float(value), actual])))
    return result
