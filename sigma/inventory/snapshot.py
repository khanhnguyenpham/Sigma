"""Apply locked weekly allocations to an explicit simulated stock snapshot."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ITEM, ROUTE, sha256, validate_run, write_csv, write_json
from src.data import audit_orders
from src.inventory import (item_matrix, allocation, replenishment, partner_params,
    project_depletion, replay_alerts, simulation_metrics, declared_receipts)
from sigma.forecasting.weekly import allocate_daily, checked_series
from sigma.verification.weekly import validate_weekly
from sigma.inventory.policy import validate_policy


def pending_orders(recommendations, cfg, origin):
    origin = pd.Timestamp(origin)
    pending = declared_receipts(cfg, pd.Timestamp(cfg['test_start']) - pd.Timedelta(days=1))
    pending = [r for r in pending if r['eta'] > origin]
    ordered = recommendations.loc[recommendations.scenario_id.eq('base')
        & recommendations.as_of_date.le(origin) & recommendations.Q.gt(0)
        & recommendations.eta.gt(origin)]
    if ordered.duplicated(ITEM + ['as_of_date']).any():
        raise ValueError('Duplicate simulated replenishment orders')
    for row in ordered.itertuples():
        pending.append({'key': tuple(getattr(row, f) for f in ITEM), 'quantity': int(row.Q), 'eta': row.eta})
    return pending


def snapshot_recommendations(matrix, forecast, ledger, prior, cfg, origin):
    origin = pd.Timestamp(origin)
    if not forecast.as_of_date.eq(origin).all():
        raise ValueError('Stale weekly snapshot forecast')
    stocks = ledger.loc[ledger.scenario_id.eq('base') & ledger.date.eq(origin)]
    if stocks.empty or stocks.duplicated(ITEM).any():
        raise ValueError('Missing or duplicate simulated stock snapshot')
    stocks = stocks.set_index(ITEM).closing.to_dict()
    pending = pending_orders(prior, cfg, origin)
    vectors, issues = allocation(matrix, forecast, origin, cfg)
    if issues or set(vectors) != set(stocks):
        raise ValueError('Weekly forecast and stock item coverage differ')
    rows = []
    for key, vector in vectors.items():
        partner, params = partner_params(key[1], cfg)
        receipts = [r for r in pending if r['key'] == key]
        decision = replenishment(stocks[key], vector, sum(r['quantity'] for r in receipts), params)
        depletion = project_depletion(stocks[key], vector, origin, receipts)
        rows.append({**dict(zip(ITEM, key)), 'as_of_date': origin, 'partner_id': partner, **decision,
            'pending_quantity': sum(r['quantity'] for r in receipts),
            'eta_if_ordered': origin + pd.Timedelta(days=int(params['lead_time_days'])) if decision['Q'] else None,
            'expected_depletion_date': depletion['date'], 'depletion_days': depletion['days'],
            'depletion_state': depletion['state'], 'is_simulated': True,
            'quantity_deducted_at': 'order reservation in parent simulated ledger; customer D+7 does not deduct twice',
            'decision_applied': False})
    return pd.DataFrame(rows)


def complete_replay_forecasts(predictions, daily, cfg):
    """Only full H14 blocks; fixed replay origins retain the original denominator."""
    groups = checked_series(daily)
    rows = []
    first = pd.Timestamp(cfg['test_start']) - pd.Timedelta(days=1)
    for origin in pd.date_range(first, cfg['test_end'], freq=f"{cfg['horizon']}D"):
        if origin + pd.Timedelta(days=cfg['horizon']) > pd.Timestamp(cfg['test_end']):
            continue
        for key, group in groups.items():
            view = predictions.loc[predictions.destination_country.eq(key[0])
                & predictions.carrier.eq(key[1]) & predictions.as_of_date.eq(origin)]
            if len(view) != 2 or set(view.week_block) != {1, 2}:
                raise ValueError('Missing complete weekly replay forecast')
            for row in view.itertuples():
                dates, quantities = allocate_daily(row.forecast_qty_7d, group, origin,
                    row.week_block, cfg.get('weekly_allocation_days', 90))
                rows.extend([{**dict(zip(ROUTE, key)), 'as_of_date': origin,
                    'target_date': date, 'horizon_day': i, 'forecast_qty': qty}
                    for i, (date, qty) in enumerate(zip(dates, quantities), 1 + 7 * (row.week_block - 1))])
    return pd.DataFrame(rows)


def validate_inventory(folder):
    folder = folder.resolve()
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    if summary.get('status') != 'complete' or summary.get('kind') != 'weekly_inventory_snapshot':
        raise ValueError('Not a completed weekly inventory snapshot')
    required = {'protocol.json', 'weekly_item_recommendations.csv', 'weekly_alert_replay.csv', 'weekly_inventory_metrics.csv'}
    if not required.issubset(summary['files']):
        raise ValueError('Missing weekly inventory evidence')
    for name, expected in summary['files'].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha256(path) != expected:
            raise ValueError('Inventory evidence changed')
    return summary


def stock_parent(policy_run, weekly_run, daily_run, cfg, source_digest):
    if policy_run is None:
        return ROOT / 'outputs' / daily_run, {'stock_source_run': daily_run, 'stock_policy_run': None,
            'stock_origin': 'base closing balances and pending orders of sealed daily simulated policy'}
    if not re.fullmatch(r'[A-Za-z0-9_-]+', policy_run):
        raise ValueError('Invalid stock policy run id')
    folder = ROOT / 'outputs' / policy_run
    info = validate_policy(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    if (info['weekly_run'] != weekly_run or info['daily_run'] != daily_run
            or info['source_sha256'] != source_digest or protocol['config'] != cfg):
        raise ValueError('Stock policy does not match forecast and base protocol')
    return folder, {'stock_source_run': policy_run, 'stock_policy_run': policy_run,
        'stock_policy_summary_sha256': sha256(folder / 'summary.json'),
        'stock_origin': 'base closing balances and pending orders of the matching continuous weekly policy'}


def execute(run_id, weekly_run, daily_run='sigma_scaled_v11', stock_policy_run=None):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [run_id, weekly_run, daily_run]):
        raise ValueError('Invalid local run id')
    out = ROOT / 'outputs' / run_id
    out.mkdir(exist_ok=False)
    wdir, ddir = ROOT / 'outputs' / weekly_run, ROOT / 'outputs' / daily_run
    w, d = validate_weekly(wdir), validate_run(ddir)
    cfg = d['config']
    wp = json.loads((wdir / 'protocol.json').read_text(encoding='utf-8'))
    for key in ['target_definition_version', 'sales_statuses', 'train_end', 'test_start', 'test_end', 'forecast_origin', 'horizon']:
        if cfg[key] != wp['base_config'][key]:
            raise ValueError('Parent protocols differ')
    source = ROOT / cfg['source']
    assert sha256(source) == w['source_sha256'] == d['source_sha256']
    stock_dir, stock_info = stock_parent(stock_policy_run, weekly_run, daily_run, cfg, sha256(source))
    origin = pd.Timestamp(cfg['forecast_origin'])
    protocol = {'source_sha256': sha256(source), 'entrypoint_sha256': sha256(__file__),
        'weekly_run': weekly_run, 'weekly_summary_sha256': sha256(wdir / 'summary.json'),
        'daily_run': daily_run, 'daily_manifest_sha256': sha256(ddir / 'manifest.json'),
        **stock_info,
        'customer_delivery_scope': 'D+7 customer handover; available stock deducted at order reservation, never twice',
        'inventory': cfg['inventory'], 'weekly_allocation_days': wp['weekly_config']['allocation_history_days'],
        'decision_applied': False, 'full_weekly_continuous_policy_run': False}
    write_json(out / 'protocol.json', protocol)
    sales, _ = audit_orders(source, cfg)
    matrix = item_matrix(sales, cfg)
    future = pd.read_csv(wdir / 'daily_allocation.csv', parse_dates=['as_of_date', 'target_date'])
    ledger = pd.read_csv(stock_dir / 'inventory_ledger.csv', parse_dates=['date'])
    prior = pd.read_csv(stock_dir / 'inventory_recommendations.csv',
        usecols=ITEM + ['as_of_date', 'eta', 'scenario_id', 'Q'], parse_dates=['as_of_date', 'eta'])
    recommendations = snapshot_recommendations(matrix, future, ledger, prior, cfg, origin)
    write_csv(out / 'weekly_item_recommendations.csv', recommendations)
    daily = pd.read_csv(wdir / 'daily_sales.csv', parse_dates=['date'])
    predictions = pd.read_csv(wdir / 'test_weekly_predictions.csv', parse_dates=['as_of_date'])
    replay_cfg = {**cfg, 'weekly_allocation_days': protocol['weekly_allocation_days']}
    table = complete_replay_forecasts(predictions, daily, replay_cfg)
    alerts = replay_alerts(matrix, table, cfg)
    # Same actual replay paths and initial policy, not a new easier sample.
    original = pd.read_csv(ddir / 'alerts.csv', parse_dates=['actual_depletion_date'])
    paired = alerts.merge(original, on=['event_id'], suffixes=('', '_daily'), validate='one_to_one')
    assert len(paired) == len(alerts) == len(original)
    assert paired.already_empty.equals(paired.already_empty_daily)
    assert paired.actual_depletion_date.equals(paired.actual_depletion_date_daily)
    metrics = simulation_metrics(ledger, alerts).iloc[-1:]
    write_csv(out / 'weekly_alert_replay.csv', alerts)
    write_csv(out / 'weekly_inventory_metrics.csv', metrics)
    validate_weekly(wdir); validate_run(ddir)
    _, final_stock = stock_parent(stock_policy_run, weekly_run, daily_run, cfg, sha256(source))
    if final_stock != stock_info:
        raise ValueError('Stock policy changed during snapshot creation')
    assert sha256(source) == protocol['source_sha256'] and sha256(__file__) == protocol['entrypoint_sha256']
    summary = {'status': 'complete', 'kind': 'weekly_inventory_snapshot', 'run_id': run_id,
        'weekly_run': weekly_run, 'daily_run': daily_run, 'as_of_date': origin.isoformat(),
        **stock_info,
        'source_sha256': protocol['source_sha256'], 'item_recommendations': len(recommendations),
        'replay_windows': len(alerts), 'unchanged_actual_event_denominator': True,
        'early_event_rate': float(metrics.early_event_rate.iloc[0]),
        'precision': float(metrics.precision.iloc[0]), 'recall': float(metrics.recall.iloc[0]),
        'full_weekly_continuous_policy_run': False, 'project_fully_accepted': False,
        'decision_applied': False, 'supplier_lead_time_modified': False,
        'files': {p.name: sha256(p) for p in out.iterdir() if p.is_file()}}
    write_json(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'files'}), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--weekly-run', required=True)
    parser.add_argument('--daily-run', default='sigma_scaled_v11')
    parser.add_argument('--stock-policy-run', help='Use matching weekly-policy balances instead of the daily simulated snapshot')
    args = parser.parse_args()
    execute(args.run_id, args.weekly_run, args.daily_run, args.stock_policy_run)
