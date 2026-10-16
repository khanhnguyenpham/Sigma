"""Causal bias calibration of a sealed 7/30-day forecast; validation first.

This does not refit the parent or rank any candidate using test outcomes.
At origin D a calibration observation is available only if its whole label
ends by D. All earlier windows, including zero-demand windows, remain in
the evaluation; positive pairs alone define the MAPE factor estimate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, write_csv, write_json
from sigma.forecasting.aggregate import validate_aggregate, metric_table, select, allocate_days
from sigma.verification.aggregate import read_predictions


def specifications(settings):
    result = {'identity': {'estimator': 'identity'}}
    for estimator in settings['estimators']:
        if estimator not in {'sum_ratio', 'mape_median'}:
            raise ValueError('Unknown calibration estimator')
        for days in settings['lookback_days']:
            if type(days) is not int or days < 1:
                raise ValueError('Invalid calibration lookback')
            for shrink in settings['shrinkages']:
                if not 0 < shrink <= 1:
                    raise ValueError('Invalid calibration shrinkage')
                name = f'{estimator}_{days}_a{int(shrink * 100)}'
                result[name] = {'estimator': estimator, 'lookback_days': days, 'shrinkage': shrink}
    if settings['minimum_completed_windows'] < 1 or not 0 < settings['factor_bounds'][0] <= 1 <= settings['factor_bounds'][1]:
        raise ValueError('Invalid calibration support or bounds')
    return result


def factor_at(history, origin, spec, settings):
    """Return a bounded factor, support count and last fully observed target."""
    origin = pd.Timestamp(origin)
    if spec['estimator'] == 'identity':
        return 1., 0, pd.NaT
    eligible = history.loc[history.target_date.le(origin)
        & history.target_date.gt(origin - pd.Timedelta(days=spec['lookback_days']))]
    # Never silently remove an invalid model output. Zero labels have no
    # positive-MAPE ratio; they are still scored by MAE/WAPE/bias downstream.
    if not np.isfinite(eligible.forecast_qty).all() or eligible.forecast_qty.lt(0).any():
        raise ValueError('Invalid historical forecast')
    eligible = eligible.loc[eligible.actual_qty.gt(0) & eligible.forecast_qty.gt(0)]
    count = len(eligible)
    last = eligible.target_date.max()
    if count < settings['minimum_completed_windows']:
        return 1., count, last
    y = eligible.actual_qty.to_numpy(float)
    f = eligible.forecast_qty.to_numpy(float)
    if spec['estimator'] == 'sum_ratio':
        estimate = float(y.sum() / f.sum())
    else:
        ratios = y / f
        weights = f / y
        order = np.argsort(ratios, kind='stable')
        cumulative = weights[order].cumsum()
        estimate = float(ratios[order[np.searchsorted(cumulative, cumulative[-1] / 2)]])
    factor = 1 + spec['shrinkage'] * (estimate - 1)
    return float(np.clip(factor, *settings['factor_bounds'])), count, last


def completed_labels(predictions, daily):
    """Materialize past window labels; factor_at enforces availability per origin."""
    frame = predictions.copy()
    groups = {key: part.set_index('date').sales_qty for key, part in daily.groupby(ROUTE)}
    for (window, country, carrier), indices in frame.groupby(['window_days'] + ROUTE).groups.items():
        part = frame.loc[indices]
        y = groups[(country, carrier)]
        frame.loc[indices, 'actual_qty'] = y.rolling(int(window), min_periods=int(window)).sum().reindex(part.target_date).to_numpy()
    return frame


def adjust(frame, history, spec, settings, candidate):
    records, factors = [], []
    for r in frame.itertuples(index=False):
        scale, n, last = factor_at(history, r.as_of_date, spec, settings)
        record = r._asdict()
        record['forecast_qty'] = float(r.forecast_qty) * scale
        record['model'] = candidate
        records.append(record)
        factors.append({**{k: record[k] for k in ROUTE}, 'window_days': r.window_days,
            'split': r.split, 'as_of_date': r.as_of_date, 'candidate': candidate,
            'base_model': r.model, 'base_forecast_qty': float(r.forecast_qty),
            'factor': scale, 'support_positive_windows': n, 'max_calibration_target': last})
    return pd.DataFrame(records), pd.DataFrame(factors)


def seal(out, parent, protocol):
    for name, digest in protocol['implementation_modules_sha256'].items():
        if sha256(ROOT / name) != digest:
            raise ValueError('Calibration implementation changed after registration')
    validate_aggregate(parent)
    if sha256(parent / 'summary.json') != protocol['parent_summary_sha256']:
        raise ValueError('Calibration parent changed')


def validation(run_id, config='data/configs/aggregate-calibration.json'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run ID')
    path = ROOT / config
    options = json.loads(path.read_text(encoding='utf-8'))
    specs = specifications(options)
    parent = ROOT / 'outputs' / options['parent_run']
    parent_info = validate_aggregate(parent)
    original = json.loads((parent / 'protocol.json').read_text(encoding='utf-8'))
    cfg = original['config']
    out = ROOT / 'outputs' / run_id
    out.mkdir(exist_ok=False)
    modules = dict(original['implementation_modules_sha256'])
    modules['sigma/experiments/aggregate_calibration.py'] = sha256(__file__)
    settings = {**original['settings'], 'calibration': options}
    protocol = {**original, 'registered_at_utc': datetime.now(timezone.utc).isoformat(),
        'parent_run': options['parent_run'], 'parent_summary_sha256': sha256(parent / 'summary.json'),
        'config_sha256': sha256(path), 'settings': settings,
        'implementation_modules_sha256': modules, 'calibration_specifications': specs,
        'selection_basis': 'parent validation champion; causal calibration selected on validation only'}
    write_json(out / 'protocol.json', protocol)
    for name in ['daily_sales.csv', 'top_routes.csv']:
        (out / name).write_bytes((parent / name).read_bytes())
    daily = pd.read_csv(parent / 'daily_sales.csv', parse_dates=['date'], float_precision='round_trip')
    top = set(pd.read_csv(parent / 'top_routes.csv')[ROUTE].itertuples(index=False, name=None))
    base_choices = pd.read_csv(parent / 'selected_models.csv')
    all_val = read_predictions(parent / 'validation_predictions.csv')
    chosen = all_val.merge(base_choices[['window_days'] + ROUTE + ['model']], on=['window_days'] + ROUTE + ['model'], validate='many_to_one')
    history = completed_labels(chosen, daily)
    frames, audits = [], []
    for key, frame in chosen.groupby(['window_days'] + ROUTE, sort=True):
        hist = history.loc[history.window_days.eq(key[0]) & history.destination_country.eq(key[1]) & history.carrier.eq(key[2])]
        for name, spec in specs.items():
            if tuple(key[1:]) not in top and name != 'identity':
                continue
            adjusted, audit = adjust(frame, hist, spec, options, frame.model.iloc[0] + '__' + name)
            frames.append(adjusted); audits.append(audit)
    predictions = pd.concat(frames, ignore_index=True)
    selected = select(predictions, cfg)
    selected['base_model'] = selected.model.str.rsplit('__', n=1).str[0]
    selected['calibration_id'] = selected.model.str.rsplit('__', n=1).str[1]
    write_csv(out / 'validation_predictions.csv', predictions)
    write_csv(out / 'validation_metrics.csv', metric_table(predictions, cfg))
    write_csv(out / 'validation_factors.csv', pd.concat(audits, ignore_index=True))
    write_csv(out / 'selected_models.csv', selected)
    lock = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'selection_sha256': sha256(out / 'selected_models.csv'), 'test_used_for_ranking': False,
        'basis': options['selection']}
    write_json(out / 'selection_lock.json', lock)
    seal(out, parent, protocol)
    changed = selected.loc[~selected.calibration_id.eq('identity')]
    result = {'status': 'validation_locked', 'selection_count': len(selected),
        'calibrated_choices': len(changed), 'candidate_count': len(specs),
        'source_sha256': parent_info['source_sha256'], 'test_evaluated': False}
    write_json(out / 'validation_summary.json', result)
    print(json.dumps(result), flush=True)
    return result


def test(run_id):
    out = ROOT / 'outputs' / run_id
    if (out / 'summary.json').exists() or (out / 'test_started.json').exists():
        raise FileExistsError('Never repeat a test or overwrite a sealed run')
    protocol = json.loads((out / 'protocol.json').read_text(encoding='utf-8'))
    parent = ROOT / 'outputs' / protocol['parent_run']
    seal(out, parent, protocol)
    options = protocol['settings']['calibration']
    specs = protocol['calibration_specifications']
    cfg = protocol['config']
    choices = pd.read_csv(out / 'selected_models.csv')
    lock = json.loads((out / 'selection_lock.json').read_text())
    if lock['test_used_for_ranking'] or lock['selection_sha256'] != sha256(out / 'selected_models.csv'):
        raise ValueError('Invalid calibration selection lock')
    write_json(out / 'test_started.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'selection_sha256': lock['selection_sha256']})
    daily = pd.read_csv(parent / 'daily_sales.csv', parse_dates=['date'], float_precision='round_trip')
    base_choices = pd.read_csv(parent / 'selected_models.csv')
    val = read_predictions(parent / 'validation_predictions.csv').merge(
        base_choices[['window_days'] + ROUTE + ['model']], on=['window_days'] + ROUTE + ['model'], validate='many_to_one')
    base_test = read_predictions(parent / 'test_predictions.csv')
    future = read_predictions(parent / 'future_predictions.csv')
    history = completed_labels(pd.concat([val, base_test], ignore_index=True), daily)
    outputs, factors = {}, []
    for split, source in [('test', base_test), ('future', future)]:
        frames = []
        for window in protocol['settings']['windows']:
            write_json(out / f'{split}_{window}d_execution.json',
                {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'selection_sha256': lock['selection_sha256']})
        for r in choices.itertuples():
            mask = lambda x: x.window_days.eq(r.window_days) & x.destination_country.eq(r.destination_country) & x.carrier.eq(r.carrier)
            frame = source.loc[mask(source)]
            if set(frame.model) != {r.base_model}:
                raise ValueError('Different base model in parent phase')
            adjusted, audit = adjust(frame, history.loc[mask(history)], specs[r.calibration_id], options, r.model)
            frames.append(adjusted); factors.append(audit)
        outputs[split] = pd.concat(frames, ignore_index=True)
        write_csv(out / f'{split}_predictions.csv', outputs[split])
    metrics = metric_table(outputs['test'], cfg)
    write_csv(out / 'test_metrics.csv', metrics)
    write_csv(out / 'test_future_factors.csv', pd.concat(factors, ignore_index=True))
    write_csv(out / 'daily_allocation.csv', allocate_days(pd.concat(list(outputs.values()), ignore_index=True), daily))
    # Native model fitting belongs to the parent, fully identified by its seal.
    (out / 'fit_log.csv').write_bytes((parent / 'fit_log.csv').read_bytes())
    top = pd.read_csv(parent / 'top_routes.csv')
    primary = metrics.merge(top[ROUTE], on=ROUTE, validate='many_to_one').loc[lambda x: x.cadence.eq('daily_origins')]
    write_csv(out / 'top10_results.csv', primary)
    seal(out, parent, protocol)
    results = [{'window_days': int(h), 'routes_below_20_pct': int(p.passes_20_pct.sum()),
        'mean_mape_positive_pct': float(p.mape_positive_pct.mean()), 'minimum_coverage': float(p.coverage.min()),
        'pairs_per_route': int(p.n_expected.iloc[0])} for h, p in primary.groupby('window_days')]
    info = {'kind': 'consecutive_day_aggregate', 'status': 'complete', 'run_id': run_id,
        'source_sha256': protocol['source_sha256'], 'parent_run': protocol['parent_run'],
        'result': results, 'top_routes': len(top), 'all_routes': daily[ROUTE].drop_duplicates().shape[0],
        'test_independent': False, 'daily_R05_acceptance_replaced': False,
        'files': {p.relative_to(out).as_posix(): sha256(p) for p in out.rglob('*') if p.is_file()}}
    write_json(out / 'summary.json', info)
    print(json.dumps(results), flush=True)
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--phase', required=True, choices=['validation', 'test'])
    parser.add_argument('--config', default='data/configs/aggregate-calibration.json')
    args = parser.parse_args()
    validation(args.run_id, args.config) if args.phase == 'validation' else test(args.run_id)
