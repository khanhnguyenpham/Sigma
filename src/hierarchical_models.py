"""Causal aggregate arrivals and historical route-share allocation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import ROUTE
from src.count_models import monthly_calendar, count_action

HIERARCHICAL_SPECS = {'hiercount_365_share90': (365, 90), 'hiercount_all_share180': (0, 180)}


def observed_counts(daily, origin):
    past = daily.loc[daily.date.le(pd.Timestamp(origin))].copy()
    if not len(past) or not np.isfinite(past.order_count).all() or past.order_count.lt(0).any():
        raise ValueError('Incomplete aggregate count history')
    if 'actual_available' in past and not past.actual_available.all():
        raise ValueError('Missing actual in aggregate count history')
    if past.duplicated(['date'] + ROUTE).any():
        raise ValueError('Duplicate aggregate count input')
    return past


def fit_hierarchical(daily, sales, keys, origin, model_id, cfg):
    from sklearn.linear_model import PoissonRegressor
    from sklearn.dummy import DummyRegressor
    if sales is None:
        raise ValueError('Hierarchical arrivals require audited sales')
    window, share_days = HIERARCHICAL_SPECS[model_id]
    origin = pd.Timestamp(origin)
    past = observed_counts(daily, origin)
    total = past.groupby('date').order_count.sum().sort_index()
    if window:
        total = total.iloc[-window:]
    model = PoissonRegressor(alpha=.1, max_iter=1000) if total.gt(0).any() else DummyRegressor(strategy='constant', constant=0)
    model.fit(monthly_calendar(total.index), total)
    known_sales = sales.loc[sales.date.le(origin)]
    baskets = {key: group.quantity.value_counts(normalize=True).to_dict()
               for key, group in known_sales.groupby(ROUTE)}
    return {'model': model, 'distributions': baskets, 'fit_cutoff': origin, 'share_days': share_days}


def route_shares(past, origin, share_days, targets):
    recent = past.loc[past.date.gt(pd.Timestamp(origin) - pd.Timedelta(days=share_days))]
    counts = recent.groupby(ROUTE).order_count.sum()
    if counts.sum() <= 0:
        return {key: np.zeros(len(targets)) for key in counts.index}
    prior = counts / counts.sum()
    monthly = past.assign(month=past.date.dt.month).groupby(['month'] + ROUTE).order_count.sum()
    month_total = past.groupby(past.date.dt.month).order_count.sum()
    return {key: np.array([.5 * (monthly.get((day.month, *key), 0) + 100 * prior[key])
                    / (month_total.get(day.month, 0) + 100) + .5 * prior[key]
                    for day in targets]) for key in counts.index}


def predict_hierarchical(state, daily, keys, origin, cfg):
    origin = pd.Timestamp(origin)
    if origin < state['fit_cutoff']:
        raise ValueError('Hierarchical model was fitted after origin')
    past = observed_counts(daily, origin)
    targets = pd.date_range(origin + pd.Timedelta(days=1), periods=cfg['horizon'])
    aggregate = state['model'].predict(monthly_calendar(targets))
    shares = route_shares(past, origin, state['share_days'], targets)
    return {key: count_action(aggregate * shares.get(key, np.zeros(len(targets))), state['distributions'][key])
            if key in state['distributions'] else np.zeros(len(targets)) for key in keys}


def hierarchical_rolling(daily, sales, top, cfg, model_ids, split, progress=print):
    if split not in ('validation', 'test') or not set(model_ids).issubset(HIERARCHICAL_SPECS):
        raise ValueError('Invalid hierarchical evaluation')
    observed = daily.loc[daily.date.le(cfg[f'{split}_end'])].copy()
    keys = sorted(map(tuple, top[ROUTE].to_numpy()))
    actuals = observed.set_index(['date'] + ROUTE).sales_qty.to_dict()
    origins = pd.date_range(pd.Timestamp(cfg[f'{split}_start']) - pd.Timedelta(days=1),
                            pd.Timestamp(cfg[f'{split}_end']) - pd.Timedelta(days=1))
    rows, logs = [], []
    for model_id in model_ids:
        for i, origin in enumerate(origins):
            if i % cfg['refit_days'] == 0:
                progress(f'{model_id}: {split} fit {origin.date()}')
                state = fit_hierarchical(observed, sales, keys, origin, model_id, cfg)
                logs.append({'model': model_id, 'fit_cutoff': origin, 'max_label_date': origin, 'status': 'ok', 'negative_clips': 0})
            for key, vector in predict_hierarchical(state, observed, keys, origin, cfg).items():
                for h, value in enumerate(vector, 1):
                    target = origin + pd.Timedelta(days=h)
                    rows.append({**dict(zip(ROUTE, key)), 'as_of_date': origin, 'target_date': target,
                        'forecast_date': target, 'horizon_day': h, 'model': model_id, 'effective_model': model_id,
                        'forecast_qty': value, 'actual_qty': actuals.get((target, *key), np.nan),
                        'split': split if target <= pd.Timestamp(cfg[f'{split}_end']) else 'outside_' + split})
    return pd.DataFrame(rows), pd.DataFrame(logs)
