"""Full continuous simulated inventory driven by a locked weekly model run."""
import argparse
import copy
import csv
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, code_hash, validate_run, write_csv, write_json
from src.data import audit_orders
from src.inventory import (item_matrix, AllocationPlan, run_policy, replay_alerts,
    simulation_metrics, alert_opportunity_summary)
from src.transactions import EVENT_COLUMNS, prepare_transactions
from sigma.verification.weekly import validate_weekly
from sigma.provenance import implementation_hashes
from sigma.forecasting.weekly import (prepare, checked_series, fit, predict_batch,
    baseline_total, allocate_daily, blend_values)
from sigma.forecasting.calibration import fit_factors
from sigma.forecasting.mix import fit_mix, mixed_values
from sigma.forecasting.combine import calibrated_blend_values


def full_policy_forecast(predictions, latest, daily, choices, cfg, settings):
    """Complete tail origins without requiring future actual labels to exist."""
    prepared, groups = prepare(daily, settings), checked_series(daily)
    first = pd.Timestamp(cfg['test_start']) - pd.Timedelta(days=1)
    end = pd.Timestamp(cfg['test_end'])
    if pd.Timestamp(cfg['forecast_origin']) != end:
        raise ValueError('Policy endpoint must match the parent forecast origin')
    if predictions.duplicated(ROUTE + ['as_of_date', 'week_block']).any():
        raise ValueError('Duplicate locked weekly policy predictions')
    observed = {(r.destination_country, r.carrier, r.as_of_date, r.week_block): r.forecast_qty_7d
        for r in predictions.itertuples()}
    future = {(r.destination_country, r.carrier, r.week_block): r.forecast_qty_7d
        for r in latest.itertuples()}
    if set(choices) != set(groups) or set(future) != {(k[0], k[1], b) for k in groups for b in (1, 2)}:
        raise ValueError('Policy route coverage differs from the parent lock')
    fits, predictions_cache, heads, logs, teacher_fits, teacher_predictions = {}, {}, {}, [], {}, {}

    def teacher_fit(prepared, cutoff, spec, cfg, settings):
        model, log = fit(prepared, cutoff, spec, cfg, settings)
        if log['max_label_end'] > cutoff:
            raise ValueError('Policy teacher used future labels')
        logs.append({'role': 'teacher', 'model': 'calibration_parent', 'fit_cutoff': cutoff, **log})
        return model, log

    rows = []
    for origin in pd.date_range(first, end):
        cutoff = first + pd.Timedelta(days=((origin - first).days // settings['refit_days']) * settings['refit_days'])
        for key, group in groups.items():
            ident = choices[key]
            spec = settings['models'][ident]
            for block in (1, 2):
                stored = (key[0], key[1], origin, block)
                if origin == end:
                    value, basis = future[(key[0], key[1], block)], 'parent_future_forecast'
                elif stored in observed:
                    value, basis = observed[stored], 'parent_test_forecast'
                elif spec['kind'] in ('mean', 'weighted_median'):
                    value, basis = baseline_total(group, origin, spec), 'causal_tail_forecast'
                else:
                    components = (spec['components'] if spec['kind'] in ('blend', 'adaptive_mix', 'calibrated_blend')
                        else [spec['parent']] if spec['kind'] == 'calibrated' else [ident])
                    values = []
                    for component in components:
                        c_spec = settings['models'][component]
                        fkey = (component, cutoff)
                        if fkey not in fits:
                            model, log = fit(prepared, cutoff, c_spec, cfg, settings)
                            if log['max_label_end'] > cutoff:
                                raise ValueError('Tail policy model used future labels')
                            fits[fkey] = model
                            logs.append({'role': 'tail_model', 'model': component, 'fit_cutoff': cutoff, **log})
                        pkey = (component, cutoff, origin)
                        if pkey not in predictions_cache:
                            predictions_cache[pkey] = predict_batch(fits[fkey], prepared, origin, c_spec)
                        values.append(predictions_cache[pkey])
                    value = (blend_values(values, spec['weights'])[(key, block)]
                        if spec['kind'] == 'blend' else values[0][(key, block)])
                    if spec['kind'] in ('calibrated', 'calibrated_blend'):
                        hkey = (ident, cutoff)
                        if hkey not in heads:
                            heads[hkey], head_logs = fit_factors(prepared, cutoff, spec, cfg, settings,
                                teacher_fits, teacher_predictions, teacher_fit, predict_batch)
                            logs.extend([{'role': 'head', 'model': ident, 'fit_cutoff': cutoff,
                                'max_label_end': row['max_head_label_end'], 'training_pairs': row['nonoverlapping_head_weeks']}
                                for row in head_logs])
                        if spec['kind'] == 'calibrated':
                            value *= heads[hkey][(key, block)]
                        else:
                            value = calibrated_blend_values(values, heads[hkey], spec['weights'])[(key, block)]
                    if spec['kind'] == 'adaptive_mix':
                        hkey = (ident, cutoff)
                        if hkey not in heads:
                            heads[hkey], mix_logs = fit_mix(prepared, cutoff, spec, cfg, settings,
                                teacher_fits, teacher_predictions, teacher_fit, predict_batch)
                            logs.extend([{'role': 'mix', 'model': ident, 'fit_cutoff': cutoff,
                                'max_label_end': row['max_mix_label_end'], 'training_pairs': row['completed_nonoverlapping_weeks']}
                                for row in mix_logs])
                        value = mixed_values(values, heads[hkey])[(key, block)]
                    basis = 'causal_tail_forecast'
                if not np.isfinite(value) or value < 0:
                    raise ValueError('Invalid full-horizon policy quantity')
                dates, quantities = allocate_daily(value, group, origin, block, settings['allocation_history_days'])
                for h, (date, quantity) in enumerate(zip(dates, quantities), 1 + 7 * (block - 1)):
                    rows.append({**dict(zip(ROUTE, key)), 'model': ident, 'as_of_date': origin,
                        'target_date': date, 'horizon_day': h, 'week_block': block, 'forecast_qty': quantity,
                        'weekly_total_qty': value, 'basis': basis, 'fit_cutoff': cutoff if basis == 'causal_tail_forecast' else pd.NaT,
                        'actual_qty': np.nan, 'is_daily_allocation': True})
    frame = pd.DataFrame(rows)
    if frame.duplicated(ROUTE + ['as_of_date', 'horizon_day']).any():
        raise ValueError('Duplicate policy origin/horizon')
    if not frame.groupby(ROUTE + ['as_of_date']).size().eq(cfg['horizon']).all():
        raise ValueError('Missing full policy horizon')
    return frame, pd.DataFrame(logs)


def scenarios(cfg):
    result = [(copy.deepcopy(cfg), copy.deepcopy(s)) for s in cfg['stress_scenarios']]
    base = cfg['stress_scenarios'][0]
    for cover in [3, 14]:
        modified = copy.deepcopy(cfg)
        modified['inventory']['initial_cover_days'] = cover
        result.append((modified, {**base, 'name': f'sensitivity_cover_{cover}'}))
    for lead in [1, 7]:
        modified = copy.deepcopy(cfg)
        for params in modified['inventory']['partners'].values():
            params['lead_time_days'] = lead
        result.append((modified, {**base, 'name': f'sensitivity_lead_{lead}'}))
    for factor in [.5, 1.5]:
        modified = copy.deepcopy(cfg)
        for params in modified['inventory']['partners'].values():
            params['safety_days'] *= factor
        result.append((modified, {**base, 'name': f'sensitivity_safety_{factor}'}))
    return result


def validate_policy(folder):
    folder = folder.resolve()
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    if summary.get('kind') != 'weekly_continuous_inventory_run' or summary.get('status') != 'complete':
        raise ValueError('Not a completed continuous weekly policy run')
    required = {'protocol.json', 'policy_forecast.csv', 'inventory_ledger.csv', 'inventory_events.csv',
        'inventory_recommendations.csv', 'scenario_configs.json', 'alerts.csv', 'simulation_metrics.csv'}
    if not required.issubset(summary['files']):
        raise ValueError('Missing weekly policy artifacts')
    for name, expected in summary['files'].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha256(path) != expected:
            raise ValueError('Weekly policy artifact changed')
    return summary


def execute(run_id, weekly_run, daily_run='sigma_scaled_v11'):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [run_id, weekly_run, daily_run]):
        raise ValueError('Invalid local run id')
    wdir, ddir = ROOT / 'outputs' / weekly_run, ROOT / 'outputs' / daily_run
    weekly, parent = validate_weekly(wdir), validate_run(ddir)
    wp = json.loads((wdir / 'protocol.json').read_text(encoding='utf-8'))
    cfg, settings = parent['config'], wp['weekly_config']
    for key in ['target_definition_version', 'sales_statuses', 'observation_start', 'observation_end',
        'train_end', 'validation_start', 'validation_end', 'test_start', 'test_end', 'horizon', 'forecast_origin']:
        if cfg[key] != wp['base_config'][key]:
            raise ValueError('Policy parent protocols differ')
    source = ROOT / parent['source_relative_path']
    if sha256(source) != weekly['source_sha256'] or sha256(source) != parent['source_sha256']:
        raise ValueError('Policy parent source differs')
    out = ROOT / 'outputs' / run_id
    out.mkdir(exist_ok=False)
    code_files = ['sigma/inventory/policy.py', 'sigma/forecasting/weekly.py', 'sigma/forecasting/macro.py', 'sigma/forecasting/calibration.py', 'sigma/forecasting/linear.py', 'sigma/forecasting/mix.py', 'sigma/forecasting/local.py', 'sigma/forecasting/reuse.py', 'sigma/forecasting/combine.py']
    protocol = {'kind': 'registered_before_policy_run', 'source_sha256': sha256(source),
        'weekly_run': weekly_run, 'weekly_summary_sha256': sha256(wdir / 'summary.json'),
        'daily_run': daily_run, 'daily_manifest_sha256': sha256(ddir / 'manifest.json'),
        'core_code_sha256': code_hash(), 'modules': {name: sha256(ROOT / name) for name in code_files},
        'implementation_modules_sha256': implementation_hashes('forecasting', 'inventory'),
        'config': cfg, 'stock_debit': 'chronological order reservation, customer D+7 is not a second debit',
        'tail_rule': 'same locked parent choice; anchored 7-day refit, labels<=fit cutoff; weekday history<=origin',
        'policy_start': cfg['test_start'], 'policy_end': cfg['test_end'], 'supplier_policy_changed': False,
        'initial_stock_changed': False, 'selection_changed': False, 'actual_inventory_provided': False}
    write_json(out / 'protocol.json', protocol)
    sales, _ = audit_orders(source, cfg)
    matrix = item_matrix(sales, cfg)
    daily = pd.read_csv(wdir / 'daily_sales.csv', parse_dates=['date'])
    selected = pd.read_csv(wdir / 'selected_weekly_models.csv')
    choices = dict(zip(map(tuple, selected[ROUTE].to_numpy()), selected.model))
    old = pd.read_csv(wdir / 'test_weekly_predictions.csv', parse_dates=['as_of_date'])
    latest = pd.read_csv(wdir / 'weekly_forecast.csv', parse_dates=['as_of_date'])
    forecast, fitlog = full_policy_forecast(old, latest, daily, choices, cfg, settings)
    write_csv(out / 'policy_forecast.csv', forecast)
    write_csv(out / 'tail_fit_log.csv', fitlog)
    print('Full H14 forecast for every decision origin prepared', flush=True)
    plan = AllocationPlan(matrix, forecast, cfg)
    alerts = replay_alerts(matrix, forecast, cfg)
    transactions = prepare_transactions(sales, cfg)
    variants = scenarios(cfg)
    summaries, issues = [], []
    ledger_rows, recommendation_rows = 0, 0
    with (out / 'inventory_events.csv.tmp').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=EVENT_COLUMNS)
        writer.writeheader()
        for index, (modified, stress) in enumerate(variants):
            ledger, rec, issue = run_policy(matrix, forecast, modified, stress,
                lambda s: print(s, flush=True), transactions=transactions, event_writer=writer, allocation_plan=plan)
            mode = 'w' if index == 0 else 'a'
            ledger.to_csv(out / 'inventory_ledger.csv.tmp', mode=mode, header=index == 0, index=False)
            rec.to_csv(out / 'inventory_recommendations.csv.tmp', mode=mode, header=index == 0, index=False)
            summaries.append(simulation_metrics(ledger, alerts).iloc[:1])
            issues.append(issue)
            ledger_rows += len(ledger); recommendation_rows += len(rec)
    for name in ['inventory_events', 'inventory_ledger', 'inventory_recommendations']:
        (out / f'{name}.csv.tmp').replace(out / f'{name}.csv')
    write_csv(out / 'alerts.csv', alerts)
    write_json(out / 'alert_opportunity_diagnostic.json', alert_opportunity_summary(alerts))
    write_csv(out / 'inventory_issues.csv', pd.concat(issues, ignore_index=True))
    replay = simulation_metrics(ledger, alerts).iloc[-1:]
    metrics = pd.concat(summaries + [replay], ignore_index=True)
    write_csv(out / 'simulation_metrics.csv', metrics)
    write_json(out / 'scenario_configs.json', [{'scenario': stress, 'inventory': modified['inventory']} for modified, stress in variants])
    validate_weekly(wdir); validate_run(ddir)
    if (sha256(source) != protocol['source_sha256'] or code_hash() != protocol['core_code_sha256']
            or implementation_hashes('forecasting', 'inventory') != protocol['implementation_modules_sha256']
        or any(sha256(ROOT / name) != digest for name, digest in protocol['modules'].items())):
        raise ValueError('Source or policy code changed during run')
    summary = {'status': 'complete', 'kind': 'weekly_continuous_inventory_run', 'run_id': run_id,
        'weekly_run': weekly_run, 'daily_run': daily_run, 'source_sha256': sha256(source),
        'scenarios': len(variants), 'policy_origins': forecast.as_of_date.nunique(), 'forecast_rows': len(forecast),
        'ledger_rows': ledger_rows, 'recommendation_rows': recommendation_rows,
        'full_weekly_continuous_policy_run': True, 'early_event_rate': float(replay.early_event_rate.iloc[0]),
        'base_fill_rate': float(metrics.loc[metrics.scenario_id.eq('base'), 'fill_rate'].iloc[0]),
        'project_fully_accepted': False, 'files': {p.name: sha256(p) for p in out.iterdir() if p.is_file()}}
    write_json(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'files'}), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--weekly-run', required=True)
    parser.add_argument('--daily-run', default='sigma_scaled_v11')
    args = parser.parse_args()
    execute(args.run_id, args.weekly_run, args.daily_run)
