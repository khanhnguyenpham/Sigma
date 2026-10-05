"""Authenticate immutable validation predictions before extending candidates."""
import json

import pandas as pd

from src.common import sha256
from sigma.verification.weekly import validate_weekly


def validation_cache(folder, cfg, settings, source_digest):
    summary = validate_weekly(folder)
    previous = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    old = previous['weekly_config']
    if previous['base_config'] != cfg or summary['source_sha256'] != source_digest:
        raise ValueError('Cached validation source or base protocol differs')
    for name, value in old.items():
        if name == 'models' or name == 'weekly_version' or name.endswith(('_note', '_hypothesis')):
            continue
        if settings.get(name) != value:
            raise ValueError('Cached validation method differs')
    if any(settings['models'].get(name) != spec for name, spec in old['models'].items()):
        raise ValueError('Cached validation candidate changed or missing')
    predictions = pd.read_csv(folder / 'validation_weekly_predictions.csv',
        parse_dates=['as_of_date', 'window_start', 'window_end'])
    if (set(predictions.model) != set(old['models']) or not predictions.split.eq('validation').all()
        or not predictions.window_end.le(pd.Timestamp(cfg['validation_end'])).all()):
        raise ValueError('Cached validation has invalid candidates or dates')
    logs = {}
    for name in ['validation_fit_log.csv', 'validation_head_log.csv', 'validation_mix_log.csv']:
        path = folder / name
        logs[name] = pd.read_csv(path) if path.is_file() and path.stat().st_size > 3 else pd.DataFrame()
    provenance = {'run_id': folder.name, 'summary_sha256': sha256(folder / 'summary.json'),
        'prediction_sha256': sha256(folder / 'validation_weekly_predictions.csv'),
        'models_reused': len(old['models']), 'prediction_pairs_reused': len(predictions),
        'selection_recomputed_on_combined_validation': True, 'test_predictions_reused': False}
    return predictions, logs, provenance
