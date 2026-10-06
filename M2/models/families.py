"""Matched daily/direct-seven-day experiments for registered model families."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, seal_manifest
from src.data import audit_orders, daily_sales, route_top
from src.evaluation import score
from src.models import baseline
from sigma.forecasting.weekly import checked_series
from M2.models.common import (annual, target_history, prediction_rows, TARGETS, COLUMNS,
                             active_variants, effective_settings)
from M2.models.LightGBM.model import prepare_daily, daily_lgbm_fit, phase as lgbm_phase
from M2.models.registry import REGISTRY, load_settings, implementation_hashes
from M2.models.reuse import checked_cache, validation_frames


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
            selected = values if target == 'daily' else values[[6, 13]]
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


def select(metrics_frame, predictions, cfg):
    if not metrics_frame.split.eq('validation').all():
        raise ValueError('Selection requires validation only')
    full = predictions.groupby(ROUTE + ['model']).forecast_qty.agg(lambda x: bool(np.isfinite(x).all()))
    candidates = metrics_frame.loc[metrics_frame.block.eq(1) & metrics_frame.cadence.eq('daily_origins')].copy()
    candidates = candidates.loc[candidates.apply(lambda r: full.loc[(r.destination_country, r.carrier, r.model)], axis=1)]
    candidates = candidates.loc[candidates.coverage.eq(1) & candidates.mape_positive_pct.notna()]
    rows = []
    for key, group in candidates.groupby(ROUTE, sort=True):
        best = group.sort_values(['mape_positive_pct', 'mae', 'model']).iloc[0]
        rows.append({**dict(zip(ROUTE, key)), 'family': best.family, 'target': best.target, 'model': best.model,
            'selection_split': 'validation', 'selection_cutoff': cfg['validation_end'],
            'validation_mape_positive_pct': best.mape_positive_pct, 'validation_mae': best.mae})
    expected = predictions[ROUTE].drop_duplicates()
    if len(rows) != len(expected):
        raise ValueError('At least one route has no complete candidate; inspect fit_log.csv')
    return pd.DataFrame(rows)


def phase(daily, groups, cfg, settings, family, target, split, folder, choices=None):
    if not REGISTRY[family].ROUTE_MODEL:
        return REGISTRY[family].phase(daily, groups, cfg, settings, target, split, choices)
    jobs = [(key, model) for key in sorted(groups) for model in active_variants(settings, family, target)
            if choices is None or choices[key] == model]
    frames, logs = [], []
    checkpoint = folder / 'candidate_predictions' / split
    checkpoint.mkdir(parents=True, exist_ok=True)
    # The shared CLI executes this module through runpy; Windows spawn needs
    # an importable canonical function, not a worker registered as __main__.
    from M2.models.families import ts_job as worker_job
    with ProcessPoolExecutor(max_workers=settings['workers']) as pool:
        futures = {pool.submit(worker_job, groups[key], key, family, target, model,
            settings['models'][family][model], cfg, settings, split): (key, model) for key, model in jobs}
        for number, future in enumerate(as_completed(futures), 1):
            key, model = futures[future]
            frame, log = future.result()
            write_csv(checkpoint / f'{model}_route{sorted(groups).index(key):02d}.csv', frame)
            frames.append(frame); logs.append(log)
            failures = int(log.status.eq('failed').sum()) if len(log) else 0
            print(f'{family} {target} {split}: {number}/{len(jobs)} jobs, failures={failures}', flush=True)
    return pd.concat(frames, ignore_index=True), pd.concat(logs, ignore_index=True)


def aggregate_daily(predictions):
    rows = []
    group_keys = ['family', 'split', 'model'] + ROUTE + ['as_of_date', 'block']
    for key, group in predictions.groupby(group_keys, sort=True):
        if len(group) != 7 or group.horizon_day.nunique() != 7:
            raise ValueError('Daily aggregation requires exactly seven forecasts')
        row = dict(zip(group_keys, key))
        row.update(target='sum_daily', window_start=group.target_date.min(), target_date=group.target_date.max(),
            horizon_day=7*row['block'], forecast_qty=group.forecast_qty.sum(min_count=7),
            actual_qty=group.actual_qty.sum(min_count=7))
        rows.append(row)
    return pd.DataFrame(rows, columns=COLUMNS)


def baseline_phase(groups, cfg, split):
    rows = []
    end = pd.Timestamp(cfg[f'{split}_end'])
    for key, series in groups.items():
        for origin in pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1), end-pd.Timedelta(days=1)):
            history = series.loc[:origin].to_numpy()
            for model_id in ('naive', 'ma7', 'seasonal_naive7'):
                values = baseline(history, model_id, 14)
                rows.extend(prediction_rows(series, key, 'Baseline', 'daily', model_id, split, origin, end, values))
            for window in (7, 28, 90):
                values = np.repeat(history[-window:].mean()*7, 2)
                rows.extend(prediction_rows(series, key, 'Baseline', 'direct_7d', f'mean{window}', split, origin, end, values))
    return pd.DataFrame(rows, columns=COLUMNS)


def run(run_id, config='M2/models/model_families.json', validation_cache_run=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run id')
    settings_path = (ROOT / config).resolve()
    if not settings_path.is_relative_to(ROOT):
        raise ValueError('Config must be local')
    settings = load_settings(settings_path)
    if not settings['models'] or not set(settings['models']).issubset(REGISTRY) or settings['daily_acceptance_replaced']:
        raise ValueError('Registered families and unchanged daily acceptance required')
    cfg = read_config(settings['base_config'])
    if cfg['horizon'] != 14 or cfg['refit_days'] != settings['refit_days'] or cfg['top_n'] != 10:
        raise ValueError('Expected H14, identical refit and top10 protocol')
    source = (ROOT / cfg['source']).resolve()
    artifact_root = (ROOT / settings['artifact_root']).resolve()
    out = (artifact_root / run_id).resolve()
    if (not source.is_relative_to(ROOT) or not artifact_root.is_relative_to(ROOT / 'M2' / 'artifacts')
            or not out.is_relative_to(artifact_root)):
        raise ValueError('Source/output must remain local')
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'status': 'running', 'run_id': run_id, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': sha256(source), 'config': cfg, 'settings': settings,
        'config_sha256': sha256(settings_path), 'implementation_modules_sha256': {
            **implementation_hashes(), 'M2/models/families.py': sha256(Path(__file__))},
        'packages': {name: importlib.metadata.version(name) for name in ['numpy','pandas','lightgbm','statsmodels','prophet','cmdstanpy']},
        'test_limit': 'Previously viewed test; retrospective research, not independent acceptance',
        'snapshot_limit': 'Final order-status snapshot; actual availability at past origins is unknown',
        'selection_rule': settings['selection'], 'scope': settings['scope'],
        'target_note': 'Direct rolling-total series is end-dated: predict S(D+7) and S(D+14), never S(D+1)',
        'log_note': 'log1p variant uses expm1 point forecasts; no unvalidated bias correction',
        'prophet_note': 'Yearly off/order3; windows365/540 registered, annual/trend decomposition may be unstable; no intraday seasonality',
        'production_modified': False}
    write_json(out/'manifest.json', manifest)
    write_json(out/'protocol.json', manifest)
    sales, audit = audit_orders(source, cfg)
    daily = daily_sales(sales, cfg)
    top = route_top(daily, cfg)
    daily = daily.merge(top[ROUTE], on=ROUTE, how='inner', validate='many_to_one')
    groups = {key: group.sales_qty.astype(float) for key, group in checked_series(daily).items()}
    write_json(out/'data_audit.json', audit); write_csv(out/'top_routes.csv', top); write_csv(out/'daily_sales.csv', daily)
    cache=None
    if validation_cache_run:
        cache,receipt=checked_cache(validation_cache_run,cfg,settings,daily)
        manifest['validation_cache']=receipt
        write_json(out/'protocol.json',manifest)
        print('Validated estimator-equivalent cache; rebuilding actual labels from fresh raw audit',flush=True)
    choices, validation_metrics, selections = {}, [], []
    for family in settings['models']:
        for target in TARGETS:
            folder = out/family/target
            folder.mkdir(parents=True)
            frame, log = (validation_frames(cache,groups,cfg,settings,family,target) if cache else
                          phase(daily, groups, cfg, settings, family, target, 'validation', folder))
            write_csv(folder/'validation_predictions.csv', frame); write_csv(folder/'validation_fit_log.csv', log)
            table = metrics(frame, cfg); write_csv(folder/'validation_metrics.csv', table)
            write_csv(folder/'validation_monthly_metrics.csv', monthly_metrics(frame, cfg))
            selection = select(table, frame, cfg); write_csv(folder/'selected_models.csv', selection)
            choices[(family, target)] = dict(zip(map(tuple, selection[ROUTE].to_numpy()), selection.model))
            selections.append(selection); validation_metrics.append(table)
    selected = pd.concat(selections, ignore_index=True)
    write_csv(out/'family_selected_models.csv', selected)
    overall = selected.sort_values(['validation_mape_positive_pct','validation_mae','family','model']).drop_duplicates(ROUTE+['target'])
    write_csv(out/'overall_selected_models.csv', overall)
    selection_hashes = {str(path.relative_to(out)): sha256(path) for path in [out/'family_selected_models.csv', out/'overall_selected_models.csv']}
    write_json(out/'selection_lock.json', {'locked_before_test': True, 'files': selection_hashes})
    test_frames, test_metrics = [], []
    for family in settings['models']:
        for target in TARGETS:
            folder = out/family/target
            frame, log = phase(daily, groups, cfg, settings, family, target, 'test', folder, choices[(family,target)])
            write_csv(folder/'test_predictions.csv', frame); write_csv(folder/'test_fit_log.csv', log)
            table = metrics(frame, cfg); write_csv(folder/'test_metrics.csv', table)
            future, future_log = phase(daily, groups, cfg, settings, family, target, 'future', folder, choices[(family,target)])
            write_csv(folder/'future_predictions.csv', future); write_csv(folder/'future_fit_log.csv', future_log)
            test_frames.append(frame); test_metrics.append(table)
    tests = pd.concat(test_frames, ignore_index=True)
    sums = aggregate_daily(tests.loc[tests.target.eq('daily')])
    write_csv(out/'summed_daily_predictions.csv', sums)
    comparison = pd.concat([*test_metrics, metrics(sums, cfg)], ignore_index=True)
    baseline_frames = pd.concat([baseline_phase(groups,cfg,split) for split in ('validation','test')], ignore_index=True)
    write_csv(out/'baseline_predictions.csv', baseline_frames)
    baseline_metrics = metrics(baseline_frames,cfg); write_csv(out/'baseline_metrics.csv', baseline_metrics)
    write_csv(out/'comparison_metrics.csv', comparison)
    all_validation = pd.concat(validation_metrics,ignore_index=True)
    write_csv(out/'validation_metrics.csv', all_validation)
    overall_test = tests.merge(overall[ROUTE+['family','target','model']], on=ROUTE+['family','target','model'], how='inner', validate='many_to_one')
    write_csv(out/'overall_test_predictions.csv', overall_test)
    write_csv(out/'overall_test_metrics.csv', metrics(overall_test,cfg))
    primary = comparison.loc[comparison.block.eq(1)&comparison.cadence.eq('daily_origins')]
    summaries = primary.groupby(['family','target'],sort=True).agg(mean_mape_pct=('mape_positive_pct','mean'),
        routes_le20=('passes_20_pct','sum'), routes=('carrier','size'), minimum_coverage=('coverage','min')).reset_index()
    write_csv(out/'summary.csv', summaries)
    for name, expected in selection_hashes.items():
        if sha256(out/name) != expected:
            raise RuntimeError('Selection changed after locking')
    if sha256(source) != manifest['source_sha256']:
        raise RuntimeError('Raw source changed')
    manifest.update(status='complete', finished_at_utc=datetime.now(timezone.utc).isoformat(),
                    selection_hashes=selection_hashes, summary=summaries.to_dict('records'))
    seal_manifest(out, manifest)
    print(f'Complete: {out}', flush=True)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--config', default='M2/models/model_families.json')
    parser.add_argument('--validation-cache-run', help='Sealed, estimator-equivalent validation forecasts; actuals are audited again')
    args = parser.parse_args()
    run(args.run_id, args.config, args.validation_cache_run)


if __name__ == '__main__':
    main()
