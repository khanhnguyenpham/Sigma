"""Forecast order arrivals and convert historical basket sizes to sales actions."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import ROUTE
from src.calendar_models import calendar_features
from src.context_models import fit_context, prepare_context, context_features

COUNT_SPECS = {'count_calendar_365': (365, 'calendar'),
               'count_calendar_all': (0, 'calendar'),
               'count_context_180': (180, 'context'),
               'count_context_365': (365, 'context')}
MONTHLY_COUNT_SPECS = {'countmonth_365': (365, 'monthly'), 'countmonth_all': (0, 'monthly')}


def monthly_calendar(dates):
    dates = pd.DatetimeIndex(dates)
    return np.column_stack([(dates.dayofweek == day).astype(float) for day in range(7)]
        + [(dates.month == month).astype(float) for month in range(1, 13)]
        + [(dates - pd.Timestamp('2024-01-01')).days / 365.25])


def count_action(rates, size_probabilities):
    """Positive-day MAPE action, not post-forecast rounding of a mean.

    The compound Poisson PMF follows the generating-function recursion.
    Its truncation is checked; an inadequate tail raises rather than biases loss.
    """
    rates = np.asarray(rates, dtype=float)
    if not np.isfinite(rates).all() or (rates < 0).any():
        raise ValueError('Invalid arrival intensity')
    if (not size_probabilities or any(int(j) != j or j < 1 or j > 100 or not np.isfinite(p) or p < 0
                                      for j,p in size_probabilities.items())
            or not np.isclose(sum(size_probabilities.values()), 1)):
        raise ValueError('Invalid historical quantity distribution')
    pmf = np.zeros((len(rates), 201))
    pmf[:,0] = np.exp(-rates)
    for n in range(1,201):
        pmf[:,n] = rates/n * sum(j*p*pmf[:,n-j] for j,p in size_probabilities.items() if j <= n)
    if not np.allclose(pmf.sum(axis=1), 1, atol=1e-8, rtol=0):
        raise ValueError('Count distribution truncation is material')
    weights = pmf[:,1:] / np.arange(1,201)
    result = 1 + np.argmax(weights.cumsum(axis=1) >= weights.sum(axis=1)[:,None]/2, axis=1)
    return np.where(rates > 0, result, 0).astype(float)


def trend_calendar(dates):
    return np.column_stack([calendar_features(dates,2),
        (pd.DatetimeIndex(dates)-pd.Timestamp('2024-01-01')).days/365.25])


def count_daily(daily):
    counts = daily.copy()
    counts['sales_qty'] = counts.order_count.astype(float)
    return counts


def fit_count(daily, sales, keys, origin, model_id, cfg):
    from sklearn.linear_model import PoissonRegressor
    from sklearn.dummy import DummyRegressor
    if sales is None:
        raise ValueError('Count model requires audited sales to estimate historical basket sizes')
    window,kind = (COUNT_SPECS | MONTHLY_COUNT_SPECS)[model_id]
    origin = pd.Timestamp(origin)
    past = sales.loc[sales.date.le(origin)]
    distributions = {key:g.quantity.value_counts(normalize=True).to_dict() for key,g in past.groupby(ROUTE)}
    counts = count_daily(daily.loc[daily.date.le(origin)])
    if kind == 'context':
        model = fit_context(counts,keys,origin,window,'poisson',cfg)
    else:
        model = {}
        for key in keys:
            observed = counts.loc[counts.destination_country.eq(key[0]) & counts.carrier.eq(key[1])].set_index('date').sales_qty.sort_index()
            if window:
                observed = observed.iloc[-window:]
            if not len(observed) or not np.isfinite(observed).all() or observed.lt(0).any():
                raise ValueError('Incomplete order count history')
            estimator = PoissonRegressor(alpha=.1,max_iter=1000) if observed.gt(0).any() else DummyRegressor(strategy='constant',constant=0)
            features = monthly_calendar(observed.index) if kind == 'monthly' else trend_calendar(observed.index)
            model[key] = estimator.fit(features,observed)
    return {'model':model, 'kind':kind, 'distributions':distributions, 'fit_cutoff':origin}


def predict_count(state, daily, keys, origin, cfg):
    origin = pd.Timestamp(origin)
    if origin < state['fit_cutoff']:
        raise ValueError('Count model was fitted after this origin')
    contexts = prepare_context(count_daily(daily),keys,origin) if state['kind'] == 'context' else None
    targets = pd.date_range(origin+pd.Timedelta(days=1),periods=cfg['horizon'])
    result = {}
    for key in keys:
        distribution = state['distributions'].get(key)
        if distribution is None:
            result[key] = np.zeros(cfg['horizon'])
            continue
        if state['kind'] == 'context':
            ctx = contexts[key]
            features = pd.concat([context_features(ctx,[len(ctx['values'])-1],h)
                                  for h in range(1,cfg['horizon']+1)],ignore_index=True)
            rates = state['model'].predict(features)
        else:
            features = monthly_calendar(targets) if state['kind'] == 'monthly' else trend_calendar(targets)
            rates = state['model'][key].predict(features)
        result[key] = count_action(rates,distribution)
    return result


def count_rolling(daily, sales, top, cfg, model_ids, split, progress=print):
    if split not in ('validation','test') or not set(model_ids).issubset(COUNT_SPECS | MONTHLY_COUNT_SPECS):
        raise ValueError('Invalid count evaluation')
    observed = daily.loc[daily.date.le(cfg[f'{split}_end'])].copy()
    keys = sorted(map(tuple,top[ROUTE].to_numpy()))
    actuals = observed.set_index(['date']+ROUTE).sales_qty.to_dict()
    origins = pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1),
                            pd.Timestamp(cfg[f'{split}_end'])-pd.Timedelta(days=1))
    rows,logs = [],[]
    for model_id in model_ids:
        for i,origin in enumerate(origins):
            if i%cfg['refit_days'] == 0:
                progress(f'{model_id}: {split} fit {origin.date()}')
                state = fit_count(observed,sales,keys,origin,model_id,cfg)
                logs.append({'model':model_id,'fit_cutoff':origin,'max_label_date':origin,'status':'ok','negative_clips':0})
            forecasts = predict_count(state,observed,keys,origin,cfg)
            for key,vector in forecasts.items():
                for h,forecast in enumerate(vector,1):
                    target = origin+pd.Timedelta(days=h)
                    rows.append({**dict(zip(ROUTE,key)),'as_of_date':origin,'target_date':target,
                        'forecast_date':target,'horizon_day':h,'model':model_id,'effective_model':model_id,
                        'forecast_qty':forecast,'actual_qty':actuals.get((target,*key),np.nan),
                        'split':split if target<=pd.Timestamp(cfg[f'{split}_end']) else 'outside_'+split})
    return pd.DataFrame(rows),pd.DataFrame(logs)
