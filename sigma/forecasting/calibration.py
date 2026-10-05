"""Weekly relative-error calibration from fully observed historical forecasts."""
import numpy as np
import pandas as pd


def relative_factor(predicted, actual, prior_weeks):
    predicted, actual = np.asarray(predicted, float), np.asarray(actual, float)
    if (predicted.shape != actual.shape or not np.isfinite(predicted).all()
            or not np.isfinite(actual).all() or (predicted < 0).any() or (actual < 0).any()
            or prior_weeks < 0):
        raise ValueError('Invalid calibration history')
    usable = (predicted > 0) & (actual > 0)
    if not usable.any():
        return 1.
    ratios = actual[usable] / predicted[usable]
    weights = predicted[usable] / actual[usable]
    if prior_weeks:
        ratios = np.append(ratios, 1.)
        weights = np.append(weights, prior_weeks * weights.mean())
    order = np.argsort(ratios, kind='stable')
    ratios, weights = ratios[order], weights[order]
    factor = ratios[np.searchsorted(np.cumsum(weights), weights.sum() / 2)]
    return float(np.clip(factor, .5, 1.5))


def fit_factors(prepared, cutoff, spec, cfg, settings, fit_cache, predict_cache,
                fit_function, predict_function):
    parent = spec['parent']
    parent_spec = settings['models'][parent]
    if parent_spec['kind'] != 'lgbm':
        raise ValueError('Calibration parent must be a direct weekly LightGBM')
    past_origins = pd.date_range(cutoff - pd.Timedelta(days=spec['history_days']),
                                cutoff - pd.Timedelta(days=7), freq='7D')
    histories = {key: ([], [], []) for key in prepared}
    for past in past_origins:
        cache_key = (parent, past)
        if cache_key not in fit_cache:
            fit_cache[cache_key] = fit_function(prepared, past, parent_spec, cfg, settings)
        model, fit_log = fit_cache[cache_key]
        if fit_log['max_label_end'] > past:
            raise ValueError('Calibration teacher fitted after its forecast origin')
        if cache_key not in predict_cache:
            predict_cache[cache_key] = predict_function(model, prepared, past, parent_spec)
        for key, table in prepared.items():
            idx = np.flatnonzero(table['origins'] == past)
            if len(idx) != 1:
                raise ValueError('Calibration historical origin is missing')
            idx = idx[0]
            end = table['ends'][idx]
            if end > cutoff:
                continue  # The second block is not yet observed for some origins.
            p, y, labels = histories[key]
            p.append(predict_cache[cache_key][key]); y.append(table['y'][idx]); labels.append(end)
    factors, logs = {}, []
    for key, (p, y, labels) in histories.items():
        if not labels or max(labels) > cutoff:
            raise ValueError('No fully observed causal calibration weeks')
        factors[key] = relative_factor(p, y, spec['prior_weeks'])
        logs.append({'destination_country': key[0][0], 'carrier': key[0][1], 'week_block': key[1],
            'head_fit_cutoff': cutoff, 'max_head_label_end': max(labels),
            'nonoverlapping_head_weeks': len(labels), 'factor': factors[key]})
    return factors, logs
