"""Pooled LightGBM features, completed seven-day labels and quantity predictions."""
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from src.common import ROUTE

FEATURES = ['route_index', 'block', 'origin_weekday', 'start_month', 'year_sin',
            'year_cos', 'elapsed_days', 'sum7', 'sum14', 'sum28', 'sum90',
            'previous7', 'std28', 'positive_share28', 'orders28', 'basket28']
AMOUNTS = ['sum7', 'sum14', 'sum28', 'sum90', 'previous7', 'std28']
CATEGORIES = ['route_index', 'block', 'origin_weekday', 'start_month']
ANNUAL_FEATURES = ['prior_year_week7', 'prior_year_mean28_week', 'prior_year_mean90_week']


def checked_series(daily):
    """No missing days may silently become zero or partial weekly labels."""
    result = {}
    for key, group in daily.groupby(ROUTE, sort=True):
        group = group.sort_values('date').set_index('date')
        expected = pd.date_range(group.index.min(), group.index.max())
        if not group.index.equals(expected) or not group.index.is_unique:
            raise ValueError('Incomplete or duplicate daily history')
        values = group[['sales_qty', 'order_count']].to_numpy(float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError('Missing or negative observed history')
        result[key] = group
    return result

def prepare(daily, settings):
    result = {}
    for route_index, (key, group) in enumerate(checked_series(daily).items()):
        y, orders = group.sales_qty.astype(float), group.order_count.astype(float)
        origins = y.index[settings['minimum_history_days'] - 1:]
        sums = {w: y.rolling(w, min_periods=w).sum() for w in (7, 14, 28, 90)}
        for block in settings['blocks']:
            starts = origins + pd.Timedelta(days=1 + 7 * (block - 1))
            ends = starts + pd.Timedelta(days=6)
            angle = 2 * np.pi * starts.dayofyear.to_numpy() / 365.25
            x = pd.DataFrame({'route_index': route_index, 'block': block,
                'origin_weekday': origins.dayofweek, 'start_month': starts.month,
                'year_sin': np.sin(angle), 'year_cos': np.cos(angle),
                'elapsed_days': (origins - pd.Timestamp('2024-01-01')).days,
                **{f'sum{w}': values.reindex(origins).to_numpy() for w, values in sums.items()},
                'previous7': sums[7].shift(7).reindex(origins).to_numpy(),
                'std28': y.rolling(28).std().reindex(origins).to_numpy(),
                'positive_share28': y.gt(0).rolling(28).mean().reindex(origins).to_numpy(),
                'orders28': orders.rolling(28).sum().reindex(origins).to_numpy(),
                'basket28': (sums[28] / orders.rolling(28).sum().clip(lower=1)).reindex(origins).to_numpy()})
            prior = ends - pd.DateOffset(years=1)
            if (prior + pd.Timedelta(days=45) > origins).any():
                raise ValueError('Prior-year feature window exceeds origin')
            x[ANNUAL_FEATURES[0]] = sums[7].reindex(prior).to_numpy()
            x[ANNUAL_FEATURES[1]] = (y.rolling(28, center=True, min_periods=28).mean() * 7).reindex(prior).to_numpy()
            x[ANNUAL_FEATURES[2]] = (y.rolling(90, center=True, min_periods=90).mean() * 7).reindex(prior).to_numpy()
            names = FEATURES + ANNUAL_FEATURES
            result[(key, block)] = {'x': x[names], 'origins': origins,
                'starts': starts, 'ends': ends,
                'y': sums[7].reindex(ends).to_numpy(float),
                'scale': np.maximum(sums[90].reindex(origins).to_numpy() * 7 / 90, 1.)}
    return result

def inputs(table, spec, indices):
    names = FEATURES + (ANNUAL_FEATURES if spec.get('annual_features', False) else [])
    x = table['x'].iloc[indices][names].copy()
    if spec.get('units') == 'ratio':
        amount_names = AMOUNTS + (ANNUAL_FEATURES if spec.get('annual_features', False) else [])
        x[amount_names] = x[amount_names].div(table['scale'][indices], axis=0)
    return x

def fit(prepared, cutoff, spec, cfg, settings):
    xs, ys, scales, label_ends = [], [], [], []
    for table in prepared.values():
        mask = ((table['ends'] <= cutoff)
                & (table['ends'] >= cutoff - pd.Timedelta(days=settings['training_window_days'] - 1)))
        idx = np.flatnonzero(mask)
        if len(idx):
            xs.append(inputs(table, spec, idx)); ys.append(table['y'][idx])
            scales.append(table['scale'][idx]); label_ends.append(table['ends'][idx].max())
    if not xs:
        raise ValueError('No fully observed weekly training labels')
    x, y = pd.concat(xs, ignore_index=True), np.concatenate(ys)
    if not np.isfinite(y).all() or (y < 0).any() or max(label_ends) > cutoff:
        raise ValueError('Invalid weekly training labels')
    if spec['units'] == 'ratio':
        y = y / np.concatenate(scales)
    if spec['objective'] == 'regression_l1':
        weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
    else:
        weights = np.ones_like(y)
    if not np.any(y > 0):
        from sklearn.dummy import DummyRegressor
        model = DummyRegressor(strategy='constant', constant=0.).fit(x, y)
    else:
        model = LGBMRegressor(objective=spec['objective'], num_leaves=spec['leaves'],
            n_estimators=spec.get('n_estimators', settings['n_estimators']), learning_rate=settings['learning_rate'],
            min_child_samples=settings['min_child_samples'], reg_lambda=settings['reg_lambda'],
            n_jobs=cfg['lightgbm_threads'], random_state=cfg['seed'], deterministic=True,
            force_col_wise=True, verbosity=-1)
        model.fit(x, y, sample_weight=weights, categorical_feature=CATEGORIES)
    return model, {'max_label_end': max(label_ends), 'training_pairs': len(y)}

def predict_batch(model, prepared, origin, spec):
    keys, xs, scales = [], [], []
    for key, table in prepared.items():
        indices = np.flatnonzero(table['origins'] == origin)
        if len(indices) != 1:
            raise ValueError('Missing or duplicate forecast origin')
        keys.append(key); xs.append(inputs(table, spec, indices))
        scales.append(table['scale'][indices[0]])
    values = np.asarray(model.predict(pd.concat(xs, ignore_index=True)), dtype=float)
    if spec['units'] == 'ratio':
        values *= np.asarray(scales)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite batch forecast')
    return dict(zip(keys, np.maximum(values, 0)))
