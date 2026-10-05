"""Replay past teachers and independently score the convex mixing objective."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, write_json
from sigma.verification.weekly import validate_weekly
from sigma.forecasting.weekly import prepare, fit, predict_batch


def objective_check(first, second, actual, prior, weight):
    p0, p1, y = (np.asarray(v, float) for v in [first, second, actual])
    valid = (y > 0) & (p0 != p1)
    if not valid.any():
        assert weight == .5
        return
    p0, p1, y = p0[valid], p1[valid], y[valid]
    prior_strength = prior * np.mean(np.abs(p0 - p1) / y)
    candidates = np.unique(np.clip(np.r_[0, .5, 1, (y - p1) / (p0 - p1)], 0, 1))
    def loss(w):
        return np.sum(np.abs(w * p0 + (1 - w) * p1 - y) / y) + prior_strength * abs(w - .5)
    assert 0 <= weight <= 1
    np.testing.assert_allclose(loss(weight), min(loss(w) for w in candidates), rtol=0, atol=1e-8)


def verify(run_id, output_id, previous_run='sigma_weekly_linear_v6'):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in [run_id, output_id, previous_run]):
        raise ValueError('Invalid local id')
    folder = ROOT / 'outputs' / run_id
    summary = validate_weekly(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    cfg, settings = protocol['base_config'], protocol['weekly_config']
    source = ROOT / cfg['source']
    assert sha256(source) == summary['source_sha256']
    raw = pd.read_csv(source, usecols=ROUTE + ['order_datetime', 'quantity', 'order_status', 'order_id'])
    raw['date'] = pd.to_datetime(raw.order_datetime, utc=True).dt.tz_localize(None).dt.normalize()
    raw = raw.loc[raw.order_status.isin(cfg['sales_statuses'])]
    routes = sorted(set(raw[ROUTE].itertuples(index=False, name=None)))
    grid = pd.MultiIndex.from_tuples([(date, *key) for key in routes
        for date in pd.date_range(cfg['observation_start'], cfg['observation_end'])], names=['date'] + ROUTE)
    daily = raw.groupby(['date'] + ROUTE).agg(sales_qty=('quantity', 'sum'),
        order_count=('order_id', 'nunique')).reindex(grid, fill_value=0).reset_index()
    checks, mixture_rows = 0, 0
    for phase in ['validation', 'test', 'future']:
        path = folder / f'{phase}_mix_log.csv'
        if path.stat().st_size <= 3:
            continue
        prepared = prepare(daily.loc[daily.date.le(cfg['validation_end'])] if phase == 'validation' else daily, settings)
        logs = pd.read_csv(path, parse_dates=['mix_fit_cutoff', 'max_mix_label_end'])
        assert not logs.duplicated(ROUTE + ['model', 'week_block', 'mix_fit_cutoff']).any()
        assert logs.max_mix_label_end.le(logs.mix_fit_cutoff).all() and logs.first_weight.between(0, 1).all()
        cache = {}
        for (ident, cutoff), group in logs.groupby(['model', 'mix_fit_cutoff'], sort=True):
            spec = settings['models'][ident]
            history = {key: ([], [], [], []) for key in prepared}
            for past in pd.date_range(cutoff - pd.Timedelta(days=spec['history_days']), cutoff - pd.Timedelta(days=7), freq='7D'):
                values = []
                for component in spec['components']:
                    key = (component, past)
                    if key not in cache:
                        model, fit_log = fit(prepared, past, settings['models'][component], cfg, settings)
                        assert fit_log['max_label_end'] <= past
                        cache[key] = predict_batch(model, prepared, past, settings['models'][component])
                    values.append(cache[key])
                for key, table in prepared.items():
                    idx = np.flatnonzero(table['origins'] == past)
                    assert len(idx) == 1
                    i = idx[0]
                    if table['ends'][i] <= cutoff:
                        p0, p1, y, ends = history[key]
                        p0.append(values[0][key]); p1.append(values[1][key])
                        y.append(table['y'][i]); ends.append(table['ends'][i])
            for row in group.itertuples():
                p0, p1, y, ends = history[((row.destination_country, row.carrier), row.week_block)]
                assert len(ends) == row.completed_nonoverlapping_weeks and max(ends) == row.max_mix_label_end <= cutoff
                objective_check(p0, p1, y, spec['prior_weeks'], row.first_weight)
                checks += 1
            print(f'{phase}: verified {ident} at {cutoff.date()}', flush=True)
        frame = pd.read_csv(folder / ('weekly_forecast.csv' if phase == 'future' else f'{phase}_weekly_predictions.csv'), parse_dates=['as_of_date'])
        mixed = frame.loc[frame.mixture_first_weight.notna()].copy()
        assert mixed.mixture_first_weight.between(0, 1).all()
        np.testing.assert_allclose(mixed.forecast_qty_7d, mixed.mixture_first_weight * mixed.mixture_first_qty
            + (1 - mixed.mixture_first_weight) * mixed.mixture_second_qty, atol=1e-8, rtol=0)
        if phase == 'future':
            mixed['mix_fit_cutoff'] = mixed.as_of_date
        else:
            start = pd.Timestamp(cfg[f'{phase}_start']) - pd.Timedelta(days=1)
            mixed['mix_fit_cutoff'] = start + pd.to_timedelta(((mixed.as_of_date - start).dt.days // settings['refit_days']) * settings['refit_days'], unit='D')
        aligned = mixed.merge(logs, on=ROUTE + ['model', 'week_block', 'mix_fit_cutoff'], validate='many_to_one')
        assert len(aligned) == len(mixed)
        np.testing.assert_allclose(aligned.mixture_first_weight, aligned.first_weight, atol=1e-8, rtol=0)
        mixture_rows += len(mixed)
        if phase == 'validation':
            for ident, g in mixed.groupby('model'):
                for column, parent in zip(['mixture_first_qty', 'mixture_second_qty'], settings['models'][ident]['components']):
                    candidate = frame.loc[frame.model.eq(parent), ROUTE + ['as_of_date', 'week_block', 'forecast_qty_7d']]
                    aligned = g.merge(candidate, on=ROUTE + ['as_of_date', 'week_block'], suffixes=('', '_parent'), validate='one_to_one')
                    assert len(aligned) == len(g)
                    np.testing.assert_allclose(aligned[column], aligned.forecast_qty_7d_parent, atol=1e-8, rtol=0)
    old_folder = ROOT / 'outputs' / previous_run
    old_summary = validate_weekly(old_folder)
    old = pd.read_csv(old_folder / 'validation_weekly_predictions.csv')
    new = pd.read_csv(folder / 'validation_weekly_predictions.csv')
    aligned = old.merge(new, on=ROUTE + ['model', 'as_of_date', 'week_block'], suffixes=('_old', '_new'), validate='one_to_one')
    assert len(aligned) == len(old)
    np.testing.assert_allclose(aligned.forecast_qty_7d_old, aligned.forecast_qty_7d_new, atol=1e-8, rtol=0)
    validate_weekly(folder); validate_weekly(old_folder)
    assert sha256(source) == summary['source_sha256'] == old_summary['source_sha256']
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    result = {'status': 'verified', 'mix_weights_checked': checks, 'mixture_quantity_rows_checked': mixture_rows,
        'teacher_labels_at_or_before_their_origin': True, 'mixture_labels_completed_at_fit': True,
        'independent_convex_objective_matches': True, 'previous_validation_pairs_unchanged': len(aligned),
        'source_unchanged': True, 'weekly_summary_sha256': sha256(folder / 'summary.json'),
        'project_fully_accepted': False, 'test_is_independent': False}
    write_json(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    parser.add_argument('--previous-run', default='sigma_weekly_linear_v6')
    args = parser.parse_args()
    verify(args.run_id, args.output_id, args.previous_run)
