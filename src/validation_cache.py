"""Explicit import of historical validation evidence, never test metrics."""
from __future__ import annotations

import copy
from pathlib import Path
import shutil

import pandas as pd

from src.common import sha256, validate_run, write_json


def import_validation(source, destination, cfg, source_sha256, daily, top):
    source, destination = Path(source), Path(destination)
    manifest = validate_run(source)
    if manifest['source_sha256'] != source_sha256:
        raise ValueError('Historical validation uses a different source')
    current, historical = copy.deepcopy(cfg), copy.deepcopy(manifest['config'])
    for config in (current, historical):
        config.pop('config_version', None)
        for name in ('context_enabled', 'distribution_enabled', 'count_enabled', 'cohort_enabled', 'countmonth_enabled'):
            config.get('tuning', {}).pop(name, None)
    if current != historical:
        raise ValueError('Historical validation configuration differs')
    old_daily = pd.read_csv(source / 'daily_sales.csv', parse_dates=['date'])
    pd.testing.assert_frame_equal(old_daily, daily.reset_index(drop=True), check_dtype=False)
    pd.testing.assert_frame_equal(pd.read_csv(source / 'top_routes.csv'), top.reset_index(drop=True), check_dtype=False)
    metrics = pd.read_csv(source / 'validation_metrics.csv')
    if not metrics.split.eq('validation').all():
        raise ValueError('Only validation metrics may be imported')
    imported_families = []
    for family in ('context','distribution','count','cohort','countmonth'):
        if metrics.model.str.startswith(family+'_').any():
            if not cfg.get('tuning',{}).get(family+'_enabled'):
                raise ValueError('Historical validation includes a disabled model family')
            imported_families.append(family)
    names = [name for name in manifest['files'] if name.endswith('_validation_predictions.csv')
             or name in ('sarima_log.csv','lightgbm_log.csv','tuning_log.csv','calendar_log.csv',
                         'context_log.csv','distribution_log.csv','count_log.csv','cohort_log.csv','countmonth_log.csv')]
    for name in names:
        if Path(name).name != name:
            raise ValueError('Invalid historical validation artifact path')
        shutil.copy2(source / name, destination / name)
    logs = pd.read_csv(source / 'sarima_log.csv')
    failed = {((r.destination_country, r.carrier),r.model)
              for r in logs.loc[logs.status.eq('failed')].itertuples(index=False)}
    evidence = {'source_run': source.name, 'manifest_sha256': sha256(source / 'manifest.json'),
                'historical_code_sha256': manifest['code_sha256'],
                'metrics_sha256': manifest['files']['validation_metrics.csv'],
                'mode': 'historical validation evidence imported, not freshly re-executed',
                'test_metrics_imported': False,
                'imported_model_families': imported_families,
                'copied_files': {name:manifest['files'][name] for name in names}}
    write_json(destination / 'validation_import.json', evidence)
    return metrics, failed, evidence
