"""Independent full-policy balances, pending-order clocks and parent lineage."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ITEM, ROUTE, code_hash, sha256, validate_run, write_json
from src.data import audit_orders
from src.transactions import verify_events
from sigma.verification.weekly import validate_weekly
from sigma.inventory.policy import validate_policy


def verify(run_id, output_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [run_id, output_id]):
        raise ValueError('Invalid local id')
    folder = ROOT / 'outputs' / run_id
    summary = validate_policy(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    cfg = protocol['config']
    wdir, ddir = ROOT / 'outputs' / summary['weekly_run'], ROOT / 'outputs' / summary['daily_run']
    weekly, daily = validate_weekly(wdir), validate_run(ddir)
    assert code_hash() == protocol['core_code_sha256']
    assert sha256(wdir / 'summary.json') == protocol['weekly_summary_sha256']
    assert sha256(ddir / 'manifest.json') == protocol['daily_manifest_sha256']
    source = ROOT / daily['source_relative_path']
    assert sha256(source) == summary['source_sha256'] == weekly['source_sha256'] == daily['source_sha256']
    sales, _ = audit_orders(source, cfg)
    raw = pd.read_csv(source, usecols=ITEM + ['order_datetime', 'order_status', 'quantity'])
    raw['date'] = pd.to_datetime(raw.order_datetime, utc=True).dt.tz_localize(None).dt.normalize()
    raw = raw.loc[raw.order_status.isin(cfg['sales_statuses'])]
    matrix = raw.groupby(['date'] + ITEM).quantity.sum().unstack(ITEM, fill_value=0).reindex(
        pd.date_range(cfg['observation_start'], cfg['observation_end']), fill_value=0)
    forecast = pd.read_csv(folder / 'policy_forecast.csv', parse_dates=['as_of_date', 'target_date', 'fit_cutoff'])
    first = pd.Timestamp(cfg['test_start']) - pd.Timedelta(days=1)
    origins = pd.date_range(first, cfg['test_end'])
    selected = pd.read_csv(wdir / 'selected_weekly_models.csv')
    choices = dict(zip(map(tuple, selected[ROUTE].to_numpy()), selected.model))
    assert not forecast.duplicated(ROUTE + ['as_of_date', 'horizon_day']).any()
    assert len(forecast) == len(choices) * len(origins) * cfg['horizon']
    assert forecast.actual_qty.isna().all() and np.isfinite(forecast.forecast_qty).all() and forecast.forecast_qty.ge(0).all()
    assert (forecast.target_date == forecast.as_of_date + pd.to_timedelta(forecast.horizon_day, unit='D')).all()
    assert forecast.groupby(ROUTE + ['as_of_date']).size().eq(cfg['horizon']).all()
    assert set(forecast.as_of_date) == set(origins)
    for key, group in forecast.groupby(ROUTE):
        assert group.model.eq(choices[key]).all()
    tail = forecast.loc[forecast.basis.eq('causal_tail_forecast')]
    assert tail.fit_cutoff.notna().all() and tail.fit_cutoff.le(tail.as_of_date).all()
    logs = pd.read_csv(folder / 'tail_fit_log.csv', parse_dates=['fit_cutoff', 'max_label_end'])
    assert logs.max_label_end.le(logs.fit_cutoff).all()
    totals = forecast.groupby(ROUTE + ['as_of_date', 'week_block']).agg(
        total=('forecast_qty', 'sum'), expected=('weekly_total_qty', 'first'), n=('horizon_day', 'size')).reset_index()
    assert totals.n.eq(7).all()
    np.testing.assert_allclose(totals.total, totals.expected, atol=1e-8, rtol=0)
    parent_predictions = pd.read_csv(wdir / 'test_weekly_predictions.csv', parse_dates=['as_of_date'])
    paired = totals.merge(parent_predictions, on=ROUTE + ['as_of_date', 'week_block'], validate='one_to_one')
    assert len(paired) == len(parent_predictions)
    np.testing.assert_allclose(paired.total, paired.forecast_qty_7d, atol=1e-8, rtol=0)
    latest = pd.read_csv(wdir / 'weekly_forecast.csv')
    last = totals.loc[totals.as_of_date.eq(cfg['forecast_origin'])].merge(latest, on=ROUTE + ['week_block'], validate='one_to_one')
    assert len(last) == len(latest)
    np.testing.assert_allclose(last.total, last.forecast_qty_7d, atol=1e-8, rtol=0)
    # Independently derive SKU shares and threshold quantities from raw histories.
    thresholds = []
    for (country, carrier, origin), group in forecast.groupby(ROUTE + ['as_of_date'], sort=True):
        keys = [key for key in matrix if key[:2] == (country, carrier) and matrix.loc[:origin, key].sum() > 0]
        for window in [cfg['inventory']['allocation_window_days'], cfg['inventory']['allocation_fallback_days']]:
            shares = matrix.loc[origin - pd.Timedelta(days=window - 1):origin, keys].sum()
            if shares.sum() > 0:
                break
        shares = shares / shares.sum()
        route_vector = group.sort_values('horizon_day').forecast_qty.to_numpy()
        for key in keys:
            vector = route_vector * shares[key]
            thresholds.append({**dict(zip(ITEM, key)), 'as_of_date': origin, 'mean14': vector.mean(),
                **{f'sum{h}': vector[:h].sum() for h in [1, 2, 3, 4, 7, 8]}})
    thresholds = pd.DataFrame(thresholds)
    variants = json.loads((folder / 'scenario_configs.json').read_text(encoding='utf-8'))
    variants = {v['scenario']['name']: v for v in variants}
    rec = pd.read_csv(folder / 'inventory_recommendations.csv', parse_dates=['as_of_date', 'eta'], low_memory=False)
    assert not rec.duplicated(ITEM + ['scenario_id', 'as_of_date']).any()
    for name, frame in rec.groupby('scenario_id', sort=False):
        variant = variants[name]
        params = variant['inventory']['partners']
        view = frame.merge(thresholds, on=ITEM + ['as_of_date'], validate='many_to_one')
        assert len(view) == len(frame)
        for partner, g in view.groupby('partner_id'):
            p = params[partner]
            ss = np.ceil(p['safety_days'] * g.mean14)
            rop = np.ceil(g[f"sum{p['lead_time_days']}"] + ss)
            target = np.ceil(g[f"sum{p['lead_time_days'] + p['review_days']}"] + ss)
            np.testing.assert_array_equal(g.SS, ss)
            np.testing.assert_array_equal(g.ROP, rop)
            np.testing.assert_array_equal(g.S, target)
            np.testing.assert_array_equal(g.needs_replenishment, g.on_hand < rop)
            quantity = np.where(g.needs_replenishment, np.ceil(np.maximum(0, target - g.IP)), 0)
            quantity = np.where(quantity > 0, np.maximum(quantity, p['moq']), 0)
            np.testing.assert_array_equal(g.Q, quantity)
            positive = g.Q.gt(0)
            assert g.loc[~positive, 'eta'].isna().all()
            assert (g.loc[positive, 'eta'] == g.loc[positive, 'as_of_date'] + pd.Timedelta(days=p['lead_time_days'])).all()
    # A separate order/arrival event matrix checks all outstanding quantities.
    groups = pd.MultiIndex.from_frame(rec[['scenario_id'] + ITEM])
    codes, unique = pd.factorize(groups, sort=True)
    n_days = (pd.Timestamp(cfg['test_end']) - pd.Timestamp(cfg['test_start'])).days + 1
    day = (rec.as_of_date - pd.Timestamp(cfg['test_start'])).dt.days.to_numpy()
    placed = np.zeros((len(unique), n_days + 20), dtype=np.int64)
    removed = np.zeros_like(placed)
    quantity = rec.Q.to_numpy(np.int64)
    np.add.at(placed, (codes, day), quantity)
    lead = np.array([variants[n]['inventory']['partners'][p]['lead_time_days'] for n, p in zip(rec.scenario_id, rec.partner_id)], dtype=int)
    delay = rec.scenario_id.map({n: v['scenario']['receipt_delay_days'] for n, v in variants.items()}).to_numpy(int)
    np.add.at(removed, (codes, day + lead + delay), quantity)
    pending = np.cumsum(placed, axis=1) - placed - np.cumsum(removed, axis=1)
    for row in cfg['inventory']['initial_receipts']:
        item = tuple(row[f] for f in ITEM)
        for i, key in enumerate(unique):
            if key[1:] == item:
                valid_days = pd.date_range(cfg['test_start'], periods=n_days) < pd.Timestamp(row['eta'])
                pending[i, :n_days] += valid_days * row['quantity']
    np.testing.assert_array_equal(rec.IP.to_numpy() - rec.on_hand.to_numpy(), pending[codes, day])
    expected_sales = int(raw.loc[raw.date.between(cfg['test_start'], cfg['test_end'])].quantity.sum())
    totals_by_scenario, fulfillment, closing_sum, ledger_rows = {}, {}, {}, 0
    for chunk in pd.read_csv(folder / 'inventory_ledger.csv', chunksize=50000):
        values = chunk[['opening', 'receipts', 'historical_sales', 'scenario_demand', 'fulfilled', 'shortage', 'closing']].to_numpy()
        assert np.isfinite(values).all() and (values >= 0).all() and (values == np.floor(values)).all()
        np.testing.assert_array_equal(chunk.closing, chunk.opening + chunk.receipts - chunk.fulfilled)
        np.testing.assert_array_equal(chunk.scenario_demand, chunk.fulfilled + chunk.shortage)
        for name, g in chunk.groupby('scenario_id'):
            totals_by_scenario[name] = totals_by_scenario.get(name, 0) + int(g.historical_sales.sum())
            old = fulfillment.get(name, np.zeros(3))
            fulfillment[name] = old + g[['scenario_demand', 'fulfilled', 'shortage']].sum().to_numpy()
            closing_sum[name] = closing_sum.get(name, 0) + g.closing.sum()
        ledger_rows += len(chunk)
    assert all(value == expected_sales for value in totals_by_scenario.values()) and set(totals_by_scenario) == set(variants)
    events = verify_events(folder / 'inventory_events.csv', folder / 'inventory_ledger.csv', sales, cfg)
    metrics = pd.read_csv(folder / 'simulation_metrics.csv')
    for name, (demand, filled, shortage) in fulfillment.items():
        row = metrics.loc[metrics.scenario_id.eq(name)].iloc[0]
        np.testing.assert_allclose([row.demand, row.shortage, row.fill_rate, row.mean_closing_on_hand],
            [demand, shortage, filled / demand if demand else np.nan, closing_sum[name] / n_days], atol=1e-8, rtol=0)
    alerts = pd.read_csv(folder / 'alerts.csv', parse_dates=['actual_depletion_date'])
    original = pd.read_csv(ddir / 'alerts.csv', parse_dates=['actual_depletion_date'])
    joined = alerts.merge(original, on='event_id', suffixes=('', '_daily'), validate='one_to_one')
    assert len(joined) == len(alerts) == len(original)
    assert joined.actual_depletion_date.equals(joined.actual_depletion_date_daily)
    assert joined.already_empty.equals(joined.already_empty_daily)
    np.testing.assert_array_equal(alerts.reported_early, alerts.tp & alerts.actual_days.ge(7))
    np.testing.assert_allclose(summary['early_event_rate'], alerts.reported_early.sum() / (alerts.tp.sum() + alerts.fn.sum()), atol=1e-8, rtol=0)
    validate_policy(folder); validate_weekly(wdir); validate_run(ddir)
    assert sha256(source) == summary['source_sha256']
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    result = {'status': 'verified', 'ledger_rows': ledger_rows, 'recommendations': len(rec), 'forecast_rows': len(forecast),
        'all_decision_origins_have_h14': True, 'tail_labels_causal': True, 'parent_choices_and_predictions_unchanged': True,
        'raw_sku_thresholds_match': True, 'outstanding_order_event_matrix_matches': True,
        'scenarios': len(variants), 'same_replay_event_denominator': True,
        'daily_sealed_files_unchanged': len(daily['files']), 'source_unchanged': True,
        'policy_summary_sha256': sha256(folder / 'summary.json'), 'project_fully_accepted': False, **events}
    write_json(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    args = parser.parse_args()
    verify(args.run_id, args.output_id)
