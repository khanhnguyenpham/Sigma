"""Pooled LightGBM for daily quantity and direct seven-day totals."""
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from src.models import FEATURES
from M2.models.common import (annual, prediction_rows, COLUMNS, active_variants,
                             effective_settings)
from sigma.forecasting.calibration import fit_factors

ROUTE_MODEL = False
AMOUNTS = ['lag0', 'lag1', 'lag6', 'lag13', 'mean7', 'mean28', 'std28']

def prepare_daily(groups):
    """Reuse the daily feature contract; attach labels and their actual end dates."""
    result = {}
    for route_index, (key, series) in enumerate(sorted(groups.items())):
        values = series.to_numpy()
        rolling = pd.Series(values)
        means7, means28 = rolling.rolling(7).mean().to_numpy(), rolling.rolling(28).mean().to_numpy()
        std28 = rolling.rolling(28).std(ddof=0).to_numpy()
        scales90 = rolling.rolling(90, min_periods=90).mean().clip(lower=1).to_numpy()
        for h in range(1, 15):
            idx = np.arange(27, len(values))
            origins, ends = series.index[idx], series.index[idx] + pd.Timedelta(days=h)
            x = pd.DataFrame(np.column_stack([np.full(len(idx), route_index), np.full(len(idx), h),
                values[idx], values[idx-1], values[idx-6], values[idx-13], means7[idx], means28[idx], std28[idx],
                ends.dayofweek, ends.month, ends.dayofyear]), columns=FEATURES)
            x[['year_sin', 'year_cos']] = annual(ends)
            result[(key, h)] = {'x': x, 'origins': origins, 'ends': ends,
                               'y': series.reindex(ends).to_numpy(), 'scale': scales90[idx]}
    return result



def daily_inputs(table, spec, indices):
    names = FEATURES + (['year_sin', 'year_cos'] if spec.get('annual_features') else [])
    x = table['x'].iloc[indices][names].copy()
    if spec.get('units') == 'ratio':
        scale = table['scale'][indices]
        if not np.isfinite(scale).all() or (scale < 1).any():
            raise ValueError('Daily ratio requires 90 observed days')
        x[AMOUNTS] = x[AMOUNTS].div(scale, axis=0)
    return x


def daily_lgbm_fit(prepared, cutoff, spec, cfg, settings):
    settings = effective_settings(settings, spec)
    xs, ys, ends = [], [], []
    for table in prepared.values():
        mask = (table['ends'] <= cutoff) & (table['ends'] >= cutoff - pd.Timedelta(days=settings['training_window_days']-1))
        if spec.get('units') == 'ratio':
            mask &= np.isfinite(table['scale'])
        idx = np.flatnonzero(mask)
        if len(idx):
            xs.append(daily_inputs(table, spec, idx))
            y = table['y'][idx]
            ys.append(y/table['scale'][idx] if spec.get('units') == 'ratio' else y)
            ends.append(table['ends'][idx].max())
    if not xs:
        raise ValueError('No complete daily training labels')
    x, y = pd.concat(xs, ignore_index=True), np.concatenate(ys)
    if not np.isfinite(y).all() or max(ends) > cutoff:
        raise ValueError('Invalid or future daily labels')
    weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0) if spec['objective'] == 'regression_l1' else np.ones_like(y)
    model = LGBMRegressor(objective=spec['objective'], num_leaves=spec['leaves'],
        n_estimators=settings['n_estimators'], learning_rate=settings['learning_rate'],
        min_child_samples=settings['min_child_samples'], reg_lambda=settings['reg_lambda'],
        n_jobs=cfg['lightgbm_threads'], random_state=cfg['seed'], deterministic=True, force_col_wise=True, verbosity=-1)
    model.fit(x, y, sample_weight=weights, categorical_feature=['route_index', 'horizon_day', 'target_weekday', 'target_month'])
    return model, {'max_label_end': max(ends), 'training_pairs': len(y)}



def weekly_fit(prepared, cutoff, spec, cfg, settings):
    from sigma.forecasting.weekly import fit
    return fit(prepared, cutoff, spec, cfg, effective_settings(settings, spec))


def phase(daily, groups, cfg, settings, target, split, choices=None):
    from sigma.forecasting.weekly import prepare, predict_batch
    models = active_variants(settings, 'LightGBM', target)
    week = {**settings, 'blocks': [1, 2], 'models': {name: {'kind': 'lgbm', 'units': 'raw', **spec} for name, spec in models.items()}}
    prepared = prepare_daily(groups) if target == 'daily' else prepare(daily, week)
    start = pd.Timestamp(cfg[f'{split}_start']) if split != 'future' else daily.date.max() + pd.Timedelta(days=1)
    end = pd.Timestamp(cfg[f'{split}_end']) if split != 'future' else daily.date.max()
    origins = pd.date_range(start-pd.Timedelta(days=1), end-pd.Timedelta(days=1)) if split != 'future' else [end]
    rows, logs, fit_cache, predict_cache = [], [], {}, {}
    identifiers = sorted(set(choices.values())) if choices else list(models)
    for model_id in identifiers:
        spec = models[model_id]
        weekly_spec = week['models'][model_id]
        parent = spec.get('parent', model_id)
        parent_spec = week['models'][parent]
        calibrated = spec.get('kind') == 'calibrated'
        for i, origin in enumerate(origins):
            if i % settings['refit_days'] == 0:
                if target == 'daily':
                    model, log = daily_lgbm_fit(prepared, origin, spec, cfg, settings)
                else:
                    cache_key = (parent, origin)
                    if cache_key not in fit_cache:
                        fit_cache[cache_key] = weekly_fit(prepared, origin, parent_spec, cfg, week)
                    model, log = fit_cache[cache_key]
                    if calibrated:
                        head_cutoff = origin
                        factors, head_logs = fit_factors(prepared, origin, weekly_spec, cfg, week,
                            fit_cache, predict_cache, weekly_fit, predict_batch)
                        for head in head_logs:
                            logs.append({'family': 'LightGBM', 'target': target, 'model': model_id,
                                'split': split, 'status': 'calibration', 'fit_cutoff': origin, **head})
                        for past in pd.date_range(origin-pd.Timedelta(days=spec['history_days']), origin-pd.Timedelta(days=7), freq='7D'):
                            teacher_log = fit_cache[(parent, past)][1]
                            logs.append({'family': 'LightGBM', 'target': target, 'model': model_id,
                                'split': split, 'status': 'teacher', 'fit_cutoff': origin,
                                'teacher_origin': past, 'parent': parent, **teacher_log})
                            for pair, table in prepared.items():
                                idx = np.flatnonzero(table['origins']==past)[0]
                                label_end = table['ends'][idx]
                                if label_end <= origin:
                                    logs.append({'family': 'LightGBM', 'target': target, 'model': model_id,
                                        'split': split, 'status': 'calibration_pair', 'fit_cutoff': origin,
                                        'destination_country': pair[0][0], 'carrier': pair[0][1], 'week_block': pair[1],
                                        'teacher_origin': past, 'max_label_end': teacher_log['max_label_end'],
                                        'head_label_end': label_end, 'forecast_qty': predict_cache[(parent,past)][pair],
                                        'actual_qty': table['y'][idx]})
                logs.append({'family': 'LightGBM', 'target': target, 'model': model_id, 'split': split,
                             'fit_cutoff': origin, 'status': 'ok', **log})
            if target == 'daily':
                batch, pairs = [], []
                for key_h, table in prepared.items():
                    idx = np.flatnonzero(table['origins'] == origin)
                    if len(idx) != 1:
                        raise ValueError('Missing daily origin')
                    batch.append(daily_inputs(table, spec, idx)); pairs.append(key_h)
                forecast = np.asarray(model.predict(pd.concat(batch, ignore_index=True)))
                if not np.isfinite(forecast).all():
                    raise ValueError('Nonfinite LightGBM forecast')
                if spec.get('units') == 'ratio':
                    forecast *= np.array([prepared[pair]['scale'][np.flatnonzero(prepared[pair]['origins']==origin)[0]] for pair in pairs])
                predicted = dict(zip(pairs, np.maximum(forecast, 0)))
            else:
                predicted = predict_batch(model, prepared, origin, parent_spec)
                if calibrated:
                    for pair, value in predicted.items():
                        if choices and choices[pair[0]] != model_id:
                            continue
                        logs.append({'family': 'LightGBM', 'target': target, 'model': model_id,
                            'split': split, 'status': 'calibration_applied', 'fit_cutoff': head_cutoff,
                            'as_of_date': origin, 'destination_country': pair[0][0], 'carrier': pair[0][1],
                            'week_block': pair[1], 'factor': factors[pair], 'parent_forecast_qty': value,
                            'corrected_forecast_qty': value*factors[pair]})
                    predicted = {pair: value*factors[pair] for pair, value in predicted.items()}
            for key, series in sorted(groups.items()):
                if choices and choices[key] != model_id:
                    continue
                indices = range(1, 15) if target == 'daily' else (1, 2)
                values = [predicted[(key, index)] for index in indices]
                rows.extend(prediction_rows(series, key, 'LightGBM', target, model_id, split, origin, end, values))
        print(f'LightGBM {target} {split}: {model_id}', flush=True)
    return pd.DataFrame(rows, columns=COLUMNS), pd.DataFrame(logs)
