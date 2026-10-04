"""Causal order-composition candidates; customer identifiers stay out of features."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import ROUTE
from src.context_models import prepare_context, context_features

COHORT_SPECS = [('cohort_180_mape', 180, 'mape'), ('cohort_365_mape', 365, 'mape'),
                ('cohort_180_poisson', 180, 'poisson'), ('cohort_365_poisson', 365, 'poisson')]
COMPOSITION_FEATURES = ['order_mean7', 'order_mean28', 'order_mean90',
    'first_seen_mean7', 'first_seen_mean28', 'first_seen_mean90',
    'source_labeled_new_share28', 'unit_price_mean28', 'esim_share28',
    'basket_mean28', 'validity_due_proxy']


def prepare_cohort(daily, sales, keys, cutoff):
    if sales is None:
        raise ValueError('Cohort model requires audited sales')
    contexts = prepare_context(daily, keys, cutoff)
    # Filter before deriving first-seen state, composition or validity proxies.
    observed = sales.loc[sales.date.le(pd.Timestamp(cutoff))].copy()
    observed['unit_price_vnd'] = pd.to_numeric(observed.unit_price_vnd, errors='coerce')
    observed['validity_days'] = pd.to_numeric(observed.validity_days, errors='coerce')
    observed = observed.sort_values(['order_datetime', 'order_id'], kind='stable')
    observed['first_seen'] = (~observed.customer_id.duplicated()
                              & observed.customer_id.notna() & observed.customer_id.ne(''))
    observed['labeled_new'] = observed.customer_type.eq('new')
    observed['esim'] = observed.product_type.eq('eSIM')
    observed['unknown_price'] = ~np.isfinite(observed.unit_price_vnd) | observed.unit_price_vnd.lt(0)
    if 'money_valid' in observed:
        observed['unknown_price'] |= ~observed.money_valid
    observed.loc[observed.unknown_price, 'unit_price_vnd'] = np.nan
    validity = observed.validity_days
    observed['known_validity'] = np.isfinite(validity) & validity.ge(1) & validity.eq(np.floor(validity))
    for key, ctx in contexts.items():
        part = observed.loc[observed.destination_country.eq(key[0]) & observed.carrier.eq(key[1])]
        group = part.groupby('date')
        dates = ctx['dates']
        counts = group.size().reindex(dates, fill_value=0).astype(float)
        first = group.first_seen.sum().reindex(dates, fill_value=0).astype(float)
        amount = group.quantity.sum().reindex(dates, fill_value=0).astype(float)
        labelled = group.labeled_new.sum().reindex(dates, fill_value=0).astype(float)
        esim = group.esim.sum().reindex(dates, fill_value=0).astype(float)
        prices = group.unit_price_vnd.sum().reindex(dates, fill_value=0).astype(float)
        denominator = counts.rolling(28, min_periods=1).sum().clip(lower=1)
        bad_prices = group.unknown_price.sum().reindex(dates, fill_value=0).rolling(28, min_periods=1).sum()
        mean_price = (prices.rolling(28, min_periods=1).sum() / denominator).where(bad_prices.eq(0))
        ctx['composition'] = np.column_stack([
            *[counts.rolling(w, min_periods=1).mean() for w in [7, 28, 90]],
            *[first.rolling(w, min_periods=1).mean() for w in [7, 28, 90]],
            labelled.rolling(28, min_periods=1).sum() / denominator, mean_price,
            esim.rolling(28, min_periods=1).sum() / denominator,
            amount.rolling(28, min_periods=1).sum() / denominator])
        ctx['validities'] = {int(v): g.groupby('date').quantity.sum().reindex(dates, fill_value=0).to_numpy(float)
                            for v, g in part.loc[part.known_validity].groupby('validity_days')}
        unknown_days = part.loc[~part.known_validity, 'date']
        ctx['unknown_validity_start'] = unknown_days.min() if len(unknown_days) else None
    return contexts


def cohort_features(ctx, indices, horizon):
    indices = np.asarray(indices, dtype=int)
    base = context_features(ctx, indices, horizon)
    due = np.zeros(len(indices))
    for validity, amount in ctx['validities'].items():
        if validity < horizon:
            continue  # Such target-day purchases would be after the origin.
        prior = indices - validity + horizon
        valid = prior >= 0
        due[valid] += amount[prior[valid]]
    if ctx['unknown_validity_start'] is not None:
        due[ctx['dates'][indices] >= ctx['unknown_validity_start']] = np.nan
    side = np.column_stack([ctx['composition'][indices], due])
    return pd.concat([base, pd.DataFrame(side, columns=COMPOSITION_FEATURES)], axis=1)


def cohort_training(daily, sales, keys, cutoff, window, horizon):
    contexts = prepare_cohort(daily, sales, keys, cutoff)
    xs, ys = [], []
    start = pd.Timestamp(cutoff) - pd.Timedelta(days=window - 1)
    for ctx in contexts.values():
        for h in range(1, horizon + 1):
            indices = np.arange(55, len(ctx['values']) - h)
            indices = indices[ctx['dates'][indices + h] >= start]
            if not len(indices):
                continue
            if ctx['dates'][indices[-1] + h] > pd.Timestamp(cutoff):
                raise ValueError('Cohort label exceeds fit cutoff')
            xs.append(cohort_features(ctx, indices, h)); ys.append(ctx['values'][indices + h])
    if not xs:
        raise ValueError('No cohort training labels')
    return pd.concat(xs, ignore_index=True), np.concatenate(ys)


def fit_cohort(daily, sales, keys, cutoff, window, loss, cfg):
    from lightgbm import LGBMRegressor
    from sklearn.dummy import DummyRegressor
    if loss not in ('mape', 'poisson'):
        raise ValueError('Invalid cohort loss')
    x, y = cohort_training(daily, sales, keys, cutoff, window, cfg['horizon'])
    if not (y > 0).any():
        return DummyRegressor(strategy='constant', constant=0).fit(x, y)
    weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0) if loss == 'mape' else None
    model = LGBMRegressor(objective='regression_l1' if loss == 'mape' else 'poisson',
        num_leaves=31, min_child_samples=100, n_estimators=300, learning_rate=.05,
        random_state=cfg['seed'], n_jobs=cfg['lightgbm_threads'], deterministic=True,
        force_col_wise=True, verbosity=-1)
    return model.fit(x, y, sample_weight=weights,
                     categorical_feature=['route_index', 'target_weekday', 'target_month'])


def predict_cohort(model, daily, sales, keys, origin, cfg):
    contexts = prepare_cohort(daily, sales, keys, origin)
    xs, meta = [], []
    for key, ctx in contexts.items():
        for h in range(1, cfg['horizon'] + 1):
            xs.append(cohort_features(ctx, [len(ctx['values']) - 1], h)); meta.append((key, h))
    values = np.maximum(model.predict(pd.concat(xs, ignore_index=True)), 0)
    return {key: np.array([pred for (route, _), pred in zip(meta, values) if route == key])
            for key in contexts}


def cohort_rolling(daily, sales, top, cfg, model_ids, split, progress=print):
    specs = {name: (window, loss) for name, window, loss in COHORT_SPECS}
    if split not in ('validation', 'test') or not set(model_ids).issubset(specs):
        raise ValueError('Invalid cohort evaluation')
    observed = daily.loc[daily.date.le(cfg[f'{split}_end'])].copy()
    actuals = observed.set_index(['date'] + ROUTE).sales_qty.to_dict()
    keys = sorted(map(tuple, top[ROUTE].to_numpy()))
    origins = pd.date_range(pd.Timestamp(cfg[f'{split}_start']) - pd.Timedelta(days=1),
                            pd.Timestamp(cfg[f'{split}_end']) - pd.Timedelta(days=1))
    rows, logs = [], []
    for ident in model_ids:
        window, loss = specs[ident]
        for i, origin in enumerate(origins):
            if i % cfg['refit_days'] == 0:
                progress(f'{ident}: {split} fit {origin.date()}')
                model = fit_cohort(observed, sales, keys, origin, window, loss, cfg)
                logs.append({'model': ident, 'fit_cutoff': origin, 'max_label_date': origin,
                             'status': 'ok', 'negative_clips': 0})
            forecasts = predict_cohort(model, observed, sales, keys, origin, cfg)
            for key, vector in forecasts.items():
                for h, pred in enumerate(vector, 1):
                    target = origin + pd.Timedelta(days=h)
                    rows.append({**dict(zip(ROUTE, key)), 'as_of_date': origin, 'target_date': target,
                        'forecast_date': target, 'horizon_day': h, 'model': ident, 'effective_model': ident,
                        'forecast_qty': float(pred), 'actual_qty': actuals.get((target, *key), np.nan),
                        'split': split if target <= pd.Timestamp(cfg[f'{split}_end']) else 'outside_' + split})
    return pd.DataFrame(rows), pd.DataFrame(logs)
