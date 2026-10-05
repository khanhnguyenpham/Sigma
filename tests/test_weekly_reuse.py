"""Reject changed data/protocol/candidates or tampered validation artifacts."""
import copy
import json

import pandas as pd
import pytest

from src.common import sha256, write_json
from sigma.forecasting.reuse import validation_cache


def parent(tmp_path):
    cfg = {'validation_end': '2025-09-30', 'target_definition_version': 'fake-sales-v1'}
    settings = {'weekly_version': 'v1', 'training_window_days': 365,
        'selection': 'validation_h1_7_positive_week_mape_then_mae_then_model',
        'models': {'a': {'kind': 'mean', 'window': 7}}}
    folder = tmp_path / 'parent'; folder.mkdir()
    names = ['selected_weekly_models.csv', 'top_routes.csv', 'weekly_forecast.csv', 'daily_allocation.csv',
        'daily_sales.csv', 'test_weekly_predictions.csv', 'test_weekly_metrics.csv',
        'validation_weekly_metrics.csv', 'selected_test_weekly_metrics.csv']
    for name in names:
        (folder / name).write_text('fake\n', encoding='utf-8')
    frame = pd.DataFrame({'model': ['a'], 'as_of_date': ['2025-06-30'],
        'window_start': ['2025-07-01'], 'window_end': ['2025-07-07'], 'split': ['validation'], 'forecast_qty_7d': [14.]})
    frame.to_csv(folder / 'validation_weekly_predictions.csv', index=False)
    write_json(folder / 'protocol.json', {'base_config': cfg, 'weekly_config': settings})
    write_json(folder / 'summary.json', {'status': 'complete', 'kind': 'weekly_quantity_run', 'source_sha256': 'fake_digest',
        'selection_sha256': sha256(folder / 'selected_weekly_models.csv'),
        'files': {p.name: sha256(p) for p in folder.iterdir()}})
    extended = copy.deepcopy(settings)
    extended['weekly_version'] = 'v2'
    extended['models']['b'] = {'kind': 'mean', 'window': 28}
    return folder, cfg, extended


def test_validation_extension_preserves_exact_pairs_and_records_parent(tmp_path):
    folder, cfg, settings = parent(tmp_path)
    frame, logs, provenance = validation_cache(folder, cfg, settings, 'fake_digest')
    assert frame.forecast_qty_7d.tolist() == [14.]
    assert all(log.empty for log in logs.values())
    assert provenance['models_reused'] == provenance['prediction_pairs_reused'] == 1
    assert provenance['selection_recomputed_on_combined_validation'] and not provenance['test_predictions_reused']


@pytest.mark.parametrize('changed', ['source', 'target', 'window', 'selection', 'candidate'])
def test_validation_cache_rejects_semantic_changes(tmp_path, changed):
    folder, cfg, settings = parent(tmp_path)
    digest = 'fake_digest'
    if changed == 'source':
        digest = 'changed_digest'
    elif changed == 'target':
        cfg['target_definition_version'] = 'activation'
    elif changed == 'candidate':
        settings['models']['a']['window'] = 90
    else:
        settings['training_window_days' if changed == 'window' else 'selection'] = 'changed'
    with pytest.raises(ValueError):
        validation_cache(folder, cfg, settings, digest)


def test_validation_cache_detects_modified_predictions(tmp_path):
    folder, cfg, settings = parent(tmp_path)
    with (folder / 'validation_weekly_predictions.csv').open('a') as stream:
        stream.write('tampered\n')
    with pytest.raises(ValueError, match='changed'):
        validation_cache(folder, cfg, settings, 'fake_digest')


def test_refactor_can_reuse_same_validation_without_claiming_fresh_test(tmp_path):
    folder, cfg, settings = parent(tmp_path)
    del settings['models']['b']
    _, _, provenance = validation_cache(folder, cfg, settings, 'fake_digest')
    assert provenance['models_reused'] == 1 and not provenance['test_predictions_reused']
