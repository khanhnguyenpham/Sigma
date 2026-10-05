"""Adaptive convex mixtures learned only from completed historical weeks."""
import numpy as np
import pandas as pd


def optimal_weight(first, second, actual, prior_weeks):
    first, second, actual = (np.asarray(value, float) for value in [first, second, actual])
    if (first.shape != second.shape or first.shape != actual.shape or prior_weeks < 0
        or not all(np.isfinite(value).all() and (value >= 0).all() for value in [first, second, actual])):
        raise ValueError('Invalid weekly mixture history')
    difference = first - second
    valid = (actual > 0) & (difference != 0)
    if not valid.any():
        return .5
    points = (actual[valid] - second[valid]) / difference[valid]
    weights = np.abs(difference[valid]) / actual[valid]
    if prior_weeks:
        points = np.append(points, .5)
        weights = np.append(weights, prior_weeks * weights.mean())
    order = np.argsort(points, kind='stable')
    return float(np.clip(points[order][np.searchsorted(np.cumsum(weights[order]), weights.sum() / 2)], 0, 1))


def fit_mix(prepared, cutoff, spec, cfg, settings, fit_cache, predict_cache, fit_function, predict_function):
    if len(spec['components']) != 2 or any(settings['models'][c]['kind'] not in ('lgbm', 'linear_week') for c in spec['components']):
        raise ValueError('Weekly adaptive mixture needs two direct models')
    history = {key: ([], [], [], []) for key in prepared}
    for past in pd.date_range(cutoff - pd.Timedelta(days=spec['history_days']), cutoff - pd.Timedelta(days=7), freq='7D'):
        values = []
        for component in spec['components']:
            key = (component, past)
            parent = settings['models'][component]
            if key not in fit_cache:
                fit_cache[key] = fit_function(prepared, past, parent, cfg, settings)
            model, log = fit_cache[key]
            if log['max_label_end'] > past:
                raise ValueError('Weekly mixture teacher used future labels')
            if key not in predict_cache:
                predict_cache[key] = predict_function(model, prepared, past, parent)
            values.append(predict_cache[key])
        for key, table in prepared.items():
            indices = np.flatnonzero(table['origins'] == past)
            if len(indices) != 1:
                raise ValueError('Missing weekly mixture historical origin')
            i = indices[0]
            if table['ends'][i] <= cutoff:
                p0, p1, y, ends = history[key]
                p0.append(values[0][key]); p1.append(values[1][key])
                y.append(table['y'][i]); ends.append(table['ends'][i])
    weights, logs = {}, []
    for key, (p0, p1, actual, ends) in history.items():
        if not ends or max(ends) > cutoff:
            raise ValueError('No completed weekly mixture labels')
        weights[key] = optimal_weight(p0, p1, actual, spec['prior_weeks'])
        logs.append({'destination_country': key[0][0], 'carrier': key[0][1], 'week_block': key[1],
            'mix_fit_cutoff': cutoff, 'max_mix_label_end': max(ends), 'completed_nonoverlapping_weeks': len(ends),
            'first_weight': weights[key]})
    return weights, logs


def mixed_values(values, weights):
    if len(values) != 2 or set(values[0]) != set(values[1]) or set(values[0]) != set(weights):
        raise ValueError('Mixture route coverage differs')
    if any(not np.isfinite(w) or not 0 <= w <= 1 for w in weights.values()):
        raise ValueError('Invalid weekly mixture weight')
    return {key: weights[key] * values[0][key] + (1 - weights[key]) * values[1][key] for key in weights}
