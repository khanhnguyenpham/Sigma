"""Five fixed pooled LightGBM configurations; refit every seven origins."""
import pandas as pd
from M2.models.common import prediction_rows, COLUMNS, active_variants, effective_settings
from M2.models.weekly import prepare, fit, predict_batch

def weekly_fit(prepared, cutoff, spec, cfg, settings):
    return fit(prepared, cutoff, spec, cfg, effective_settings(settings, spec))


def phase(daily, groups, cfg, settings, target, split, choices):
    if target != 'direct_7d':
        raise ValueError('Final M2 requires direct_7d')
    models = active_variants(settings, 'LightGBM', target)
    week = {**settings, 'blocks': [1, 2],
            'models': {name: {'kind': 'lgbm', 'units': 'raw', **spec} for name, spec in models.items()}}
    prepared = prepare(daily, week)
    start = pd.Timestamp(cfg[f'{split}_start']) if split != 'future' else daily.date.max() + pd.Timedelta(days=1)
    end = pd.Timestamp(cfg[f'{split}_end']) if split != 'future' else daily.date.max()
    origins = pd.date_range(start-pd.Timedelta(days=1), end-pd.Timedelta(days=1)) if split != 'future' else [end]
    rows, logs = [], []
    for model_id in sorted(set(choices.values())):
        spec = week['models'][model_id]
        for i, origin in enumerate(origins):
            if i % settings['refit_days'] == 0:
                model, log = weekly_fit(prepared, origin, spec, cfg, week)
                logs.append({'family': 'LightGBM', 'target': target, 'model': model_id,
                    'split': split, 'fit_cutoff': origin, 'status': 'ok', **log})
            predicted = predict_batch(model, prepared, origin, spec)
            for key, series in sorted(groups.items()):
                if choices[key] == model_id:
                    values = [predicted[(key, block)] for block in (1, 2)]
                    rows.extend(prediction_rows(series, key, 'LightGBM', target, model_id, split, origin, end, values))
        print(f'LightGBM {target} {split}: {model_id}', flush=True)
    return pd.DataFrame(rows, columns=COLUMNS), pd.DataFrame(logs)
