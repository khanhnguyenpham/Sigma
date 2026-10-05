"""Independent raw SKU shares, stock equation, thresholds and depletion replay."""
import argparse
import json
import math
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ITEM, ROUTE, sha256, validate_run, write_json
from verify_weekly import validate_weekly
from weekly_inventory import validate_inventory


def verify(run_id, output_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [run_id, output_id]):
        raise ValueError('Invalid local id')
    folder = ROOT / 'outputs' / run_id
    summary = validate_inventory(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    ddir, wdir = ROOT / 'outputs' / summary['daily_run'], ROOT / 'outputs' / summary['weekly_run']
    daily, weekly = validate_run(ddir), validate_weekly(wdir)
    cfg, origin = daily['config'], pd.Timestamp(summary['as_of_date'])
    assert sha256(ddir / 'manifest.json') == protocol['daily_manifest_sha256']
    assert sha256(wdir / 'summary.json') == protocol['weekly_summary_sha256']
    source = ROOT / cfg['source']
    assert sha256(source) == daily['source_sha256'] == weekly['source_sha256'] == summary['source_sha256']
    raw = pd.read_csv(source, usecols=ITEM + ['order_datetime', 'quantity', 'order_status'])
    raw['date'] = pd.to_datetime(raw.order_datetime, utc=True).dt.tz_localize(None).dt.normalize()
    raw = raw.loc[raw.order_status.isin(cfg['sales_statuses'])]
    item_series = {key: g.groupby('date').quantity.sum().reindex(pd.date_range(cfg['observation_start'], cfg['observation_end']), fill_value=0)
        for key, g in raw.groupby(ITEM)}
    parent_ledger = pd.read_csv(ddir / 'inventory_ledger.csv', usecols=ITEM + ['date', 'scenario_id', 'closing'], parse_dates=['date'])
    parent_stock = parent_ledger.loc[parent_ledger.date.eq(origin) & parent_ledger.scenario_id.eq('base')].set_index(ITEM).closing
    parent_orders = pd.read_csv(ddir / 'inventory_recommendations.csv', usecols=ITEM + ['as_of_date', 'eta', 'scenario_id', 'Q'], parse_dates=['as_of_date', 'eta'])
    pending = parent_orders.loc[parent_orders.scenario_id.eq('base') & parent_orders.as_of_date.le(origin)
        & parent_orders.eta.gt(origin) & parent_orders.Q.gt(0)]
    rec = pd.read_csv(folder / 'weekly_item_recommendations.csv', parse_dates=['expected_depletion_date', 'eta_if_ordered'])
    future = pd.read_csv(wdir / 'daily_allocation.csv')
    assert not rec.duplicated(ITEM).any() and len(rec) == len(parent_stock)
    for row in rec.itertuples():
        key = tuple(getattr(row, f) for f in ITEM)
        route_items = [k for k in item_series if k[:2] == key[:2] and item_series[k].loc[:origin].sum() > 0]
        totals = None
        for window in [cfg['inventory']['allocation_window_days'], cfg['inventory']['allocation_fallback_days']]:
            totals = {k: item_series[k].loc[origin - pd.Timedelta(days=window - 1):origin].sum() for k in route_items}
            if sum(totals.values()) > 0:
                break
        vector = future.loc[future.destination_country.eq(key[0]) & future.carrier.eq(key[1])].sort_values('horizon_day').forecast_qty.to_numpy() * totals[key] / sum(totals.values())
        assert len(vector) == 14
        partner = cfg['inventory']['partner_map'][key[1]]
        params = cfg['inventory']['partners'][partner]
        own_pending = pending.loc[(pending[ITEM] == pd.Series(dict(zip(ITEM, key)))).all(axis=1)]
        pending_qty = own_pending.Q.sum()
        initial = [r for r in cfg['inventory']['initial_receipts'] if tuple(r[f] for f in ITEM) == key and pd.Timestamp(r['eta']) > origin]
        pending_qty += sum(r['quantity'] for r in initial)
        stock = parent_stock.loc[key]
        safety = math.ceil(params['safety_days'] * vector.mean())
        rop = math.ceil(vector[:params['lead_time_days']].sum() + safety)
        target = math.ceil(vector[:params['lead_time_days'] + params['review_days']].sum() + safety)
        q = math.ceil(max(0, target - stock - pending_qty)) if stock < rop else 0
        q = max(q, params['moq']) if q else 0
        np.testing.assert_array_equal([row.on_hand, row.pending_quantity, row.SS, row.ROP, row.S, row.IP, row.Q],
            [stock, pending_qty, safety, rop, target, stock + pending_qty, q])
        assert row.needs_replenishment == (stock < rop) and not row.decision_applied
        day = None
        if stock > 0:
            for h, demand in enumerate(vector, 1):
                date = origin + pd.Timedelta(days=h)
                stock += own_pending.loc[own_pending.eta.eq(date)].Q.sum()
                stock += sum(r['quantity'] for r in initial if pd.Timestamp(r['eta']) == date)
                stock = max(0, stock - demand)
                if stock <= 1e-9:
                    day = date; break
        assert pd.isna(row.expected_depletion_date) if day is None else row.expected_depletion_date == day
    alerts = pd.read_csv(folder / 'weekly_alert_replay.csv', parse_dates=['as_of_date', 'actual_depletion_date'])
    assert not alerts.event_id.duplicated().any()
    for row in alerts.itertuples():
        key = tuple(getattr(row, f) for f in ITEM)
        history = item_series[key].loc[row.as_of_date - pd.Timedelta(days=cfg['inventory']['initial_window_days'] - 1):row.as_of_date]
        stock = math.ceil(cfg['inventory']['initial_cover_days'] * history.mean())
        assert row.already_empty == (stock <= 0)
        day = None
        if stock > 0:
            for date, demand in item_series[key].loc[row.as_of_date + pd.Timedelta(days=1):row.as_of_date + pd.Timedelta(days=14)].items():
                stock += sum(r['quantity'] for r in cfg['inventory']['initial_receipts']
                    if tuple(r[f] for f in ITEM) == key and pd.Timestamp(r['eta']) == date)
                stock = max(0, stock - demand)
                if stock == 0:
                    day = date; break
        assert pd.isna(row.actual_depletion_date) if day is None else row.actual_depletion_date == day
    tp, fp, fn = int(alerts.tp.sum()), int(alerts.fp.sum()), int(alerts.fn.sum())
    assert tp + fn == int((alerts.actual_days.notna() & ~alerts.already_empty).sum())
    np.testing.assert_allclose(summary['early_event_rate'], alerts.reported_early.sum() / (tp + fn), atol=1e-8, rtol=0)
    validate_run(ddir); validate_weekly(wdir); validate_inventory(folder)
    assert sha256(source) == summary['source_sha256']
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    result = {'status': 'verified', 'item_thresholds_and_orders_checked': len(rec), 'raw_actual_replay_windows_checked': len(alerts),
        'integer_quantity_conservation': True, 'strict_on_hand_trigger': True, 'customer_stock_not_deducted_twice': True,
        'actual_events': tp + fn, 'tp': tp, 'fp': fp, 'fn': fn,
        'daily_sealed_files_unchanged': len(daily['files']), 'source_unchanged': True,
        'inventory_summary_sha256': sha256(folder / 'summary.json'), 'project_fully_accepted': False}
    write_json(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    args = parser.parse_args()
    verify(args.run_id, args.output_id)
