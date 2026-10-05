"""Fixed customer delivery commitments from known orders and causal sales forecasts.

Customer D+7 does not change replenishment lead time, sales labels or accuracy.
Only aggregate commitments are exported; source identifiers remain local.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common import ROOT, ITEM, ROUTE, read_config, sha256, write_csv, write_json, validate_run
from src.data import audit_orders
from verify_weekly import validate_weekly


def delivery_settings(path='config.delivery.json'):
    path = (ROOT / path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Delivery config must be local')
    settings = json.loads(path.read_text(encoding='utf-8'))
    if (settings['customer_delivery_days'] != 7 or settings['customer_delay_days'] != 0
            or settings['scope'] != 'customer_order_to_customer_delivery_only'
            or settings['supplier_lead_time_modified'] is not False):
        raise ValueError('Customer delivery must be fixed D+7 with no supplier-policy change')
    return settings


def commitments(sales):
    dates = pd.to_datetime(sales.order_datetime, utc=True, errors='raise').dt.tz_convert(None).dt.normalize()
    quantity = sales.quantity.to_numpy(float)
    if (not np.isfinite(quantity).all() or (quantity <= 0).any()
            or not np.equal(quantity, np.floor(quantity)).all()):
        raise ValueError('Invalid commitment quantity')
    frame = sales[ITEM].copy()
    frame['order_date'] = dates
    frame['delivery_date'] = dates + pd.Timedelta(days=7)
    frame['commitment_qty'] = quantity.astype('int64')
    result = frame.groupby(ITEM + ['order_date', 'delivery_date'], as_index=False).commitment_qty.sum()
    result['is_assumed_delivery'] = True
    result['customer_delay_days'] = 0
    if int(result.commitment_qty.sum()) != int(sales.quantity.sum()):
        raise ValueError('Delivery quantities are not conserved')
    return result


def projection(sales, allocation, origin):
    origin = pd.Timestamp(origin)
    if origin.tzinfo is not None or origin != origin.normalize():
        raise ValueError('Origin must be a UTC date with no time component')
    forecast = allocation.copy()
    forecast['target_date'] = pd.to_datetime(forecast.target_date)
    forecast['as_of_date'] = pd.to_datetime(forecast.as_of_date)
    if (not forecast.as_of_date.eq(origin).all()
            or forecast.duplicated(ROUTE + ['target_date']).any()
            or not np.isfinite(forecast.forecast_qty).all() or forecast.forecast_qty.lt(0).any()):
        raise ValueError('Invalid or stale daily allocation')
    keys = forecast[ROUTE].drop_duplicates().sort_values(ROUTE)
    expected_dates = pd.date_range(origin + pd.Timedelta(days=1), periods=14)
    for _, group in forecast.groupby(ROUTE):
        if group.target_date.sort_values().tolist() != expected_dates.tolist():
            raise ValueError('Incomplete H14 daily allocation')
    dates = pd.to_datetime(sales.order_datetime, utc=True).dt.tz_convert(None).dt.normalize()
    # Unknown future orders cannot enter the first week of commitments.
    observed = commitments(sales.loc[dates.le(origin)])
    backlog = observed.loc[observed.delivery_date.gt(origin)]
    if not set(map(tuple, backlog[ROUTE].to_numpy())).issubset(set(map(tuple, keys.to_numpy()))):
        raise ValueError('Known backlog route missing from forecast')
    known = backlog.groupby(ROUTE + ['delivery_date'], as_index=False).commitment_qty.sum()
    grid = keys.merge(pd.DataFrame({'delivery_date': pd.date_range(origin + pd.Timedelta(days=1), periods=21)}), how='cross')
    result = grid.merge(known, on=ROUTE + ['delivery_date'], how='left', validate='one_to_one')
    result['known_commitment_qty'] = result.commitment_qty.fillna(0).astype('int64')
    result = result.drop(columns='commitment_qty')
    future = forecast[ROUTE + ['target_date', 'forecast_qty']].rename(columns={'target_date': 'order_date'})
    future['delivery_date'] = future.order_date + pd.Timedelta(days=7)
    future = future.rename(columns={'forecast_qty': 'forecast_from_future_orders_qty'})
    result = result.merge(future, on=ROUTE + ['delivery_date'], how='left', validate='one_to_one')
    result['order_date'] = result.delivery_date - pd.Timedelta(days=7)
    result['delivery_horizon_day'] = (result.delivery_date - origin).dt.days
    known_week = result.delivery_horizon_day.le(7)
    if result.loc[~known_week, 'forecast_from_future_orders_qty'].isna().any():
        raise ValueError('Missing forecast for future-order deliveries')
    result.loc[known_week, 'forecast_from_future_orders_qty'] = 0.
    result['planned_delivery_qty'] = result.known_commitment_qty + result.forecast_from_future_orders_qty
    result['basis'] = np.where(known_week, 'known_orders_D_plus_7', 'forecast_orders_D_plus_7')
    result['as_of_date'] = origin
    result['customer_delivery_days'] = 7
    result['customer_delay_days'] = 0
    result['is_assumed_delivery'] = True
    result['actual_delivered_qty'] = np.nan  # No observed delivery events were provided.
    if not np.isclose(result.forecast_from_future_orders_qty.sum(), forecast.forecast_qty.sum(), atol=1e-8, rtol=0):
        raise ValueError('Future forecast quantities are not conserved')
    if result.known_commitment_qty.sum() != backlog.commitment_qty.sum():
        raise ValueError('Known commitments are not conserved')
    return result.sort_values(ROUTE + ['delivery_date']).reset_index(drop=True)


def validate_delivery(folder):
    folder = folder.resolve()
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    if summary.get('status') != 'complete' or summary.get('kind') != 'fixed_customer_delivery_run':
        raise ValueError('Not a complete customer-delivery run')
    required = {'protocol.json', 'delivery_commitments.csv', 'delivery_projection.csv'}
    if not required.issubset(summary['files']):
        raise ValueError('Missing delivery artifacts')
    for name, expected in summary['files'].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha256(path) != expected:
            raise ValueError('Delivery artifact missing or changed')
    return summary


def execute(run_id, config='config.delivery.json', weekly_run=None, daily_run=None):
    settings = delivery_settings(config)
    weekly_run = weekly_run or settings['weekly_run']
    daily_run = daily_run or settings['daily_run']
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in [run_id, weekly_run, daily_run]):
        raise ValueError('Invalid local run id')
    cfg = read_config(settings['base_config'])
    source = (ROOT / cfg['source']).resolve()
    root = (ROOT / cfg['output_root']).resolve()
    if not root.is_relative_to(ROOT) or not source.is_relative_to(ROOT):
        raise ValueError('Run and source must be local')
    weekly_folder, daily_folder = root / weekly_run, root / daily_run
    weekly = validate_weekly(weekly_folder)
    daily = validate_run(daily_folder)
    weekly_protocol = json.loads((weekly_folder / 'protocol.json').read_text(encoding='utf-8'))
    keys = ['target_definition_version', 'sales_statuses', 'observation_start', 'observation_end',
            'train_end', 'validation_start', 'validation_end', 'test_start', 'test_end', 'horizon', 'forecast_origin']
    if any(cfg[key] != parent[key] for parent in [weekly_protocol['base_config'], daily['config']] for key in keys):
        raise ValueError('Parent runs use a different target or forecasting protocol')
    source_hash = sha256(source)
    if source_hash != weekly['source_sha256'] or source_hash != daily['source_sha256']:
        raise ValueError('Cannot combine runs from different sources')
    out = root / run_id
    out.mkdir(exist_ok=False)
    protocol = {'settings': settings, 'base_config': cfg, 'weekly_run': weekly_run, 'daily_run': daily_run,
        'weekly_summary_sha256': sha256(weekly_folder / 'summary.json'),
        'daily_manifest_sha256': sha256(daily_folder / 'manifest.json'), 'source_sha256': source_hash,
        'entrypoint_sha256': sha256(ROOT / 'delivery.py'),
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'acceptance_limit': 'Known next-week delivery commitments are not predictions of unknown future sales.',
        'inventory_limit': 'Planned delivery dates do not prove stock availability; existing shortage warnings still apply.',
        'source_kind': settings['source_description']}
    write_json(out / 'protocol.json', protocol)
    sales, audit = audit_orders(source, cfg)
    observed = commitments(sales)
    allocation = pd.read_csv(weekly_folder / 'daily_allocation.csv')
    origin = pd.Timestamp(cfg['forecast_origin'])
    view = projection(sales, allocation, origin)
    write_csv(out / 'delivery_commitments.csv', observed)
    write_csv(out / 'delivery_projection.csv', view)
    validate_weekly(weekly_folder)
    validate_run(daily_folder)
    if sha256(source) != source_hash:
        raise ValueError('Source changed during customer-delivery projection')
    summary = {'status': 'complete', 'kind': 'fixed_customer_delivery_run', 'run_id': run_id,
        'created_at_utc': protocol['created_at_utc'], 'as_of_date': origin.isoformat(),
        'customer_delivery_days': 7, 'customer_delay_days': 0, 'supplier_lead_time_modified': False,
        'source_kind': settings['source_description'], 'source_sha256': source_hash,
        'raw_unchanged': sha256(source) == source_hash, 'order_rows_audited': audit['rows_raw'],
        'historical_commitment_qty': int(observed.commitment_qty.sum()),
        'known_next7_commitment_qty': int(view.known_commitment_qty.sum()),
        'forecast_next14_orders_qty': float(view.forecast_from_future_orders_qty.sum()),
        'delivery_projection_rows': len(view), 'customer_delivery_horizon_days': 21,
        'weekly_run': weekly_run, 'daily_run': daily_run,
        'actual_delivery_provided': False, 'daily_R05_met': False, 'project_fully_accepted': False,
        'files': {p.name: sha256(p) for p in out.iterdir() if p.is_file()}}
    write_json(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'files'}, ensure_ascii=False))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--config', default='config.delivery.json')
    parser.add_argument('--weekly-run')
    parser.add_argument('--daily-run')
    args = parser.parse_args()
    execute(args.run_id, args.config, args.weekly_run, args.daily_run)
