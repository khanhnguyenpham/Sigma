"""Shared Prophet replay and final seven-day evaluation."""
import numpy as np
import pandas as pd
from src.common import ROUTE
from src.evaluation import score
from M2.models.common import target_history, prediction_rows, COLUMNS, effective_settings
from M2.models.registry import REGISTRY

def ts_job(series, keys, family, target, model_id, spec, cfg, settings, split):
    """One route/candidate; failure is visible and invalidates selection coverage."""
    from threadpoolctl import threadpool_limits
    family_module = REGISTRY[family]
    settings = effective_settings(settings, spec)
    start = pd.Timestamp(cfg[f'{split}_start']) if split != 'future' else series.index.max() + pd.Timedelta(days=1)
    end = pd.Timestamp(cfg[f'{split}_end']) if split != 'future' else series.index.max()
    origins = pd.date_range(start - pd.Timedelta(days=1), end - pd.Timedelta(days=1)) if split != 'future' else [end]
    rows, logs, state, params, failed = [], [], None, None, False
    fit_cutoff = None
    with threadpool_limits(limits=1):
        for i, origin in enumerate(origins):
            values = np.full(14, np.nan)
            try:
                if failed:
                    raise StopIteration
                dates = pd.date_range(origin + pd.Timedelta(days=1), periods=14)
                history = target_history(series, target, origin, settings)
                if i % settings['refit_days'] == 0:
                    fit_cutoff = origin
                    state, params, warning_names = family_module.fit(history, spec, cfg, settings, params)
                    logs.append({**dict(zip(ROUTE, keys)), 'family': family, 'target': target, 'model': model_id,
                        'split': split, 'fit_cutoff': origin, 'max_label_end': history.index.max(),
                        'training_pairs': len(history), 'status': 'ok', 'warnings': ','.join(warning_names)})
                else:
                    state = family_module.update(state, history, spec)
                values = family_module.predict(state, dates, spec)
                if not np.isfinite(values).all():
                    raise RuntimeError('Nonfinite forecast')
                if (values < 0).any():
                    logs.append({**dict(zip(ROUTE, keys)), 'family': family, 'target': target, 'model': model_id,
                        'split': split, 'fit_cutoff': fit_cutoff, 'as_of_date': origin,
                        'status': 'negative_clipped', 'negative_clips': int((values < 0).sum())})
                values = np.maximum(values, 0.)
            except StopIteration:
                pass
            except (ValueError, RuntimeError, np.linalg.LinAlgError, OverflowError) as error:
                failed = True
                logs.append({**dict(zip(ROUTE, keys)), 'family': family, 'target': target, 'model': model_id,
                    'split': split, 'fit_cutoff': origin, 'status': 'failed', 'error_type': type(error).__name__})
                values = np.full(14, np.nan)
            selected = values[[6, 13]]
            rows.extend(prediction_rows(series, keys, family, target, model_id, split, origin, end, selected))
    return pd.DataFrame(rows, columns=COLUMNS), pd.DataFrame(logs)

def metrics(predictions, cfg, cadence_anchor=None):
    rows = []
    keys = ['family', 'target', 'split', 'model'] + ROUTE + ['block']
    for key, frame in predictions.groupby(keys, sort=True):
        split = key[2]
        end = pd.Timestamp(cfg[f'{split}_end'])
        labeled = frame.loc[frame.target_date.le(end)]
        for cadence in ('daily_origins', 'nonoverlapping_7d'):
            subset = labeled
            if cadence == 'nonoverlapping_7d':
                anchor = pd.Timestamp(cadence_anchor or cfg[f'{split}_start']) - pd.Timedelta(days=1)
                subset = subset.loc[(subset.as_of_date - anchor).dt.days.mod(7).eq(0)]
            if len(subset):
                row = {**dict(zip(keys, key)), 'cadence': cadence, **score(subset)}
                row['passes_20_pct'] = bool(row['coverage'] == 1 and row['mape_positive_pct'] <= cfg['mape_limit_pct'])
                rows.append(row)
    return pd.DataFrame(rows)

def monthly_metrics(predictions, cfg):
    """Full target windows inside each month; cadence stays anchored to validation."""
    if not predictions.split.eq('validation').all():
        raise ValueError('Monthly stability requires validation only')
    parts = []
    for month in pd.period_range(cfg['validation_start'], cfg['validation_end'], freq='M'):
        start, end = max(month.start_time, pd.Timestamp(cfg['validation_start'])), min(month.end_time.normalize(), pd.Timestamp(cfg['validation_end']))
        frame = predictions.loc[predictions.as_of_date.ge(start-pd.Timedelta(days=1)) & predictions.as_of_date.lt(end)].copy()
        table = metrics(frame, {**cfg, 'validation_end': end}, cadence_anchor=cfg['validation_start'])
        table['month'] = str(month)
        parts.append(table)
    return pd.concat(parts, ignore_index=True)
