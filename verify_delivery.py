"""Verify fixed D+7 commitments directly from the unchanged source and parents."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from delivery import validate_delivery
from src.common import ROOT, ITEM, ROUTE, sha256, validate_run, write_json
from verify_weekly import validate_weekly


def verify(run_id, output_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in [run_id, output_id]):
        raise ValueError('Invalid local id')
    folder = ROOT / 'outputs' / run_id
    summary = validate_delivery(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    source = (ROOT / protocol['base_config']['source']).resolve()
    if not source.is_relative_to(ROOT) or sha256(source) != summary['source_sha256']:
        raise ValueError('Source changed')
    raw = pd.read_csv(source, usecols=ITEM + ['order_datetime', 'quantity', 'order_status'])
    raw = raw.loc[raw.order_status.isin(protocol['base_config']['sales_statuses'])].copy()
    raw['order_date'] = pd.to_datetime(raw.order_datetime, utc=True).dt.tz_localize(None).dt.normalize()
    raw['delivery_date'] = raw.order_date + pd.Timedelta(days=7)
    group_keys = ITEM + ['order_date', 'delivery_date']
    expected = raw.groupby(group_keys).quantity.sum().sort_index()
    stored = pd.read_csv(folder / 'delivery_commitments.csv', parse_dates=['order_date', 'delivery_date'])
    assert not stored.duplicated(group_keys).any()
    pd.testing.assert_series_equal(stored.set_index(group_keys).commitment_qty.sort_index(),
        expected.rename('commitment_qty'), check_dtype=False)
    assert stored.customer_delay_days.eq(0).all()
    assert (stored.delivery_date - stored.order_date).dt.days.eq(7).all()
    view = pd.read_csv(folder / 'delivery_projection.csv', parse_dates=['as_of_date', 'delivery_date', 'order_date'])
    origin = pd.Timestamp(summary['as_of_date'])
    assert view.as_of_date.eq(origin).all() and view.actual_delivered_qty.isna().all()
    assert not view.duplicated(ROUTE + ['delivery_date']).any()
    known = raw.loc[raw.order_date.le(origin) & raw.delivery_date.gt(origin)]
    known = known.groupby(ROUTE + ['delivery_date']).quantity.sum()
    projected = view.set_index(ROUTE + ['delivery_date'])
    np.testing.assert_array_equal(projected.known_commitment_qty,
        known.reindex(projected.index, fill_value=0))
    weekly_folder = ROOT / 'outputs' / summary['weekly_run']
    weekly = validate_weekly(weekly_folder)
    assert sha256(weekly_folder / 'summary.json') == protocol['weekly_summary_sha256']
    allocation = pd.read_csv(weekly_folder / 'daily_allocation.csv', parse_dates=['target_date'])
    allocation['delivery_date'] = allocation.target_date + pd.Timedelta(days=7)
    forecast = allocation.set_index(ROUTE + ['delivery_date']).forecast_qty
    np.testing.assert_allclose(projected.forecast_from_future_orders_qty,
        forecast.reindex(projected.index, fill_value=0), atol=1e-8, rtol=0)
    for _, g in view.groupby(ROUTE):
        assert g.delivery_date.tolist() == pd.date_range(origin + pd.Timedelta(days=1), periods=21).tolist()
    np.testing.assert_allclose(view.planned_delivery_qty,
        view.known_commitment_qty + view.forecast_from_future_orders_qty, atol=1e-8, rtol=0)
    assert view.customer_delay_days.eq(0).all() and view.customer_delivery_days.eq(7).all()
    assert view.order_date.notna().all() and (view.delivery_date - view.order_date).dt.days.eq(7).all()
    assert view.loc[view.delivery_horizon_day.le(7)].basis.eq('known_orders_D_plus_7').all()
    assert view.loc[view.delivery_horizon_day.gt(7)].basis.eq('forecast_orders_D_plus_7').all()
    assert not any({'order_id', 'customer_id'}.intersection(frame.columns) for frame in [stored, view])
    daily_folder = ROOT / 'outputs' / summary['daily_run']
    daily = validate_run(daily_folder)
    assert sha256(daily_folder / 'manifest.json') == protocol['daily_manifest_sha256']
    assert weekly['source_sha256'] == daily['source_sha256'] == summary['source_sha256']
    result = {'status': 'verified', 'historical_commitment_rows': len(stored),
        'historical_quantity': int(stored.commitment_qty.sum()), 'projection_rows': len(view),
        'known_next7_quantity': int(view.known_commitment_qty.sum()),
        'fixed_seven_calendar_days': True, 'customer_delay_days': 0,
        'known_vs_forecast_reconciled': True, 'future_actuals_missing': True,
        'source_identifiers_exported': False, 'daily_sealed_files_unchanged': len(daily['files']),
        'source_unchanged': sha256(source) == summary['source_sha256'],
        'delivery_summary_sha256': sha256(folder / 'summary.json'),
        'daily_R05_met': False, 'project_fully_accepted': False}
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    write_json(out / 'summary.json', result)
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    args = parser.parse_args()
    verify(args.run_id, args.output_id)
