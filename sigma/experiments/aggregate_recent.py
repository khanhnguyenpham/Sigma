"""Registered shorter training histories for direct totals; validation lock first."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, write_csv, write_json
from sigma.forecasting.aggregate import (model_job, validate_aggregate, metric_table,
    select, allocate_days)
from sigma.verification.aggregate import read_predictions


def candidate_settings(parent_settings, name, spec):
    if spec['kind'] != 'lgbm' or spec['training_window_days'] < 90:
        raise ValueError('Invalid recent-history candidate')
    settings = deepcopy(parent_settings)
    settings['training_window_days'] = spec['training_window_days']
    settings['models'] = {name: {k: v for k, v in spec.items() if k != 'training_window_days'}}
    return settings


def run_candidate(daily, top, cfg, settings, spec, window, name, split, routes):
    return model_job(daily, top, cfg, candidate_settings(settings, name, spec),
        window, name, split, routes)


def check_run_id(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid local run ID')


def check_sources(parent, protocol):
    validate_aggregate(parent)
    if sha256(parent / 'summary.json') != protocol['parent_summary_sha256']:
        raise ValueError('Parent forecast changed')
    if sha256(ROOT / protocol['config']['source']) != protocol['source_sha256']:
        raise ValueError('Source data changed')
    if sha256(ROOT / protocol['research_config_path']) != protocol['config_sha256']:
        raise ValueError('Research configuration changed')
    for path, digest in protocol['implementation_modules_sha256'].items():
        if sha256(ROOT / path) != digest:
            raise ValueError('Implementation changed after registration')


def workers(daily, top, cfg, settings, options, window, split, choices, out):
    frames, logs = [], []
    with ProcessPoolExecutor(max_workers=options['workers']) as pool:
        from sigma.experiments.aggregate_recent import run_candidate as worker
        tasks = {}
        for name, spec in options['models'].items():
            routes = top if choices is None else [key for key, value in choices.items() if value == name]
            if routes:
                tasks[pool.submit(worker, daily, top, cfg, settings, spec, window, name, split, routes)] = name
        for job in as_completed(tasks):
            name = tasks[job]
            frame, log = job.result()
            if not np.isfinite(frame.forecast_qty).all():
                raise ValueError('Registered candidate failed; no pointwise omission')
            write_csv(out / 'checkpoints' / f'{split}_{window}_{name}.csv', frame)
            frames.append(frame); logs.append(log)
            print(f'{split} {window}d: {name} complete', flush=True)
    return frames, logs


def validation(run_id, config='data/configs/aggregate-recent.json'):
    check_run_id(run_id)
    options = json.loads((ROOT / config).read_text(encoding='utf-8'))
    parent = ROOT / 'outputs' / options['parent_run']
    info = validate_aggregate(parent)
    original = json.loads((parent / 'protocol.json').read_text(encoding='utf-8'))
    cfg, settings = original['config'], original['settings']
    out = ROOT / 'outputs' / run_id; out.mkdir(exist_ok=False)
    modules = dict(original['implementation_modules_sha256'])
    modules['sigma/experiments/aggregate_recent.py'] = sha256(__file__)
    protocol = {**original, 'registered_at_utc': datetime.now(timezone.utc).isoformat(),
        'parent_run': options['parent_run'], 'parent_summary_sha256': sha256(parent / 'summary.json'),
        'research_config_path': config, 'config_sha256': sha256(ROOT / config),
        'recent_training': options, 'implementation_modules_sha256': modules}
    write_json(out / 'protocol.json', protocol)
    for name in ['daily_sales.csv', 'top_routes.csv']:
        (out / name).write_bytes((parent / name).read_bytes())
    daily = pd.read_csv(parent / 'daily_sales.csv', parse_dates=['date'], float_precision='round_trip')
    top = list(pd.read_csv(parent / 'top_routes.csv')[ROUTE].itertuples(index=False, name=None))
    base = pd.read_csv(parent / 'selected_models.csv')
    # Only original validation champions are retained as controls. The parent
    # test file is not parsed during this stage.
    validation_frame = read_predictions(parent / 'validation_predictions.csv').merge(
        base[['window_days'] + ROUTE + ['model']], on=['window_days'] + ROUTE + ['model'], validate='many_to_one')
    frames, logs = [validation_frame], []
    for window in options['windows']:
        new, fit_logs = workers(daily, top, cfg, settings, options, window, 'validation', None, out)
        frames.extend(new); logs.extend(fit_logs)
    predictions = pd.concat(frames, ignore_index=True)
    selected = select(predictions, cfg)
    write_csv(out / 'validation_predictions.csv', predictions)
    write_csv(out / 'validation_metrics.csv', metric_table(predictions, cfg))
    write_csv(out / 'selected_models.csv', selected)
    write_csv(out / 'new_fit_log.csv', pd.concat(logs, ignore_index=True))
    write_json(out / 'selection_lock.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'selection_sha256': sha256(out / 'selected_models.csv'), 'test_used_for_ranking': False,
        'basis': options['selection']})
    check_sources(parent, protocol)
    changed = selected.loc[selected.model.isin(options['models'])]
    result = {'status': 'validation_locked', 'selection_count': len(selected),
        'recent_choices': len(changed), 'registered_new_candidates': len(options['models']),
        'source_sha256': info['source_sha256'], 'test_evaluated': False}
    write_json(out / 'validation_summary.json', result)
    print(json.dumps(result), flush=True)
    return result


def test(run_id):
    check_run_id(run_id)
    out = ROOT / 'outputs' / run_id
    if (out / 'summary.json').exists() or (out / 'test_started.json').exists():
        raise FileExistsError('Never repeat test or overwrite evidence')
    protocol = json.loads((out / 'protocol.json').read_text(encoding='utf-8'))
    parent = ROOT / 'outputs' / protocol['parent_run']
    check_sources(parent, protocol)
    cfg, settings, options = protocol['config'], protocol['settings'], protocol['recent_training']
    choices = pd.read_csv(out / 'selected_models.csv')
    lock = json.loads((out / 'selection_lock.json').read_text())
    if lock['test_used_for_ranking'] or lock['selection_sha256'] != sha256(out / 'selected_models.csv'):
        raise ValueError('Invalid selection lock')
    write_json(out / 'test_started.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'selection_sha256': lock['selection_sha256']})
    daily = pd.read_csv(parent / 'daily_sales.csv', parse_dates=['date'], float_precision='round_trip')
    top = pd.read_csv(parent / 'top_routes.csv')
    top_keys = list(top[ROUTE].itertuples(index=False, name=None))
    outputs, fit_logs = {}, [pd.read_csv(parent / 'fit_log.csv'), pd.read_csv(out / 'new_fit_log.csv')]
    for split in ['test', 'future']:
        inherited = read_predictions(parent / f'{split}_predictions.csv')
        controls = choices.loc[~choices.model.isin(options['models']), ['window_days'] + ROUTE + ['model']]
        parts = [inherited.merge(controls, on=['window_days'] + ROUTE + ['model'], validate='many_to_one')]
        for window in settings['windows']:
            write_json(out / f'{split}_{window}d_execution.json',
                {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'selection_sha256': lock['selection_sha256']})
            if window not in options['windows']:
                continue
            chosen = choices.loc[choices.window_days.eq(window)]
            wanted = dict(zip(chosen[ROUTE].itertuples(index=False, name=None), chosen.model))
            frames, logs = workers(daily, top_keys, cfg, settings, options, window, split, wanted, out)
            parts.extend(frames); fit_logs.extend(logs)
        outputs[split] = pd.concat(parts, ignore_index=True)
        write_csv(out / f'{split}_predictions.csv', outputs[split])
    metrics = metric_table(outputs['test'], cfg)
    write_csv(out / 'test_metrics.csv', metrics)
    write_csv(out / 'fit_log.csv', pd.concat(fit_logs, ignore_index=True))
    write_csv(out / 'daily_allocation.csv', allocate_days(pd.concat(list(outputs.values()), ignore_index=True), daily))
    primary = metrics.merge(top[ROUTE], on=ROUTE, validate='many_to_one').loc[lambda x: x.cadence.eq('daily_origins')]
    write_csv(out / 'top10_results.csv', primary)
    check_sources(parent, protocol)
    results = [{'window_days': int(h), 'routes_below_20_pct': int(p.passes_20_pct.sum()),
        'mean_mape_positive_pct': float(p.mape_positive_pct.mean()), 'minimum_coverage': float(p.coverage.min()),
        'pairs_per_route': int(p.n_expected.iloc[0])} for h, p in primary.groupby('window_days')]
    summary = {'kind': 'consecutive_day_aggregate', 'status': 'complete', 'run_id': run_id,
        'source_sha256': protocol['source_sha256'], 'parent_run': protocol['parent_run'], 'result': results,
        'top_routes': len(top), 'all_routes': daily[ROUTE].drop_duplicates().shape[0],
        'test_independent': False, 'daily_R05_acceptance_replaced': False,
        'files': {p.relative_to(out).as_posix(): sha256(p) for p in out.rglob('*') if p.is_file()}}
    write_json(out / 'summary.json', summary)
    print(json.dumps(results), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--phase', required=True, choices=['validation', 'test'])
    parser.add_argument('--config', default='data/configs/aggregate-recent.json')
    args = parser.parse_args()
    validation(args.run_id, args.config) if args.phase == 'validation' else test(args.run_id)
