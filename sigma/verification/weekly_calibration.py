"""Replay historical teachers and independently reconstruct weekly head factors."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, write_json
from sigma.verification.weekly import validate_weekly
from sigma.forecasting.weekly import prepare, fit, predict_batch


def independent_factor(predicted, actual, prior):
    data = pd.DataFrame({'p': predicted, 'y': actual})
    if not np.isfinite(data.to_numpy()).all() or data.lt(0).any().any():
        raise ValueError('Invalid observed teacher quantities')
    data = data.loc[data.p.gt(0) & data.y.gt(0)]
    if data.empty:
        return 1.
    ratios = pd.DataFrame({'ratio': data.y / data.p, 'weight': data.p / data.y}).reset_index(drop=True)
    if prior:
        ratios.loc[len(ratios)] = [1., prior * ratios.weight.mean()]
    ratios = ratios.sort_values('ratio', kind='stable')
    return float(np.clip(ratios.loc[ratios.weight.cumsum().ge(ratios.weight.sum() / 2), 'ratio'].iloc[0], .5, 1.5))


def verify(run_id, output_id, previous_run='sigma_weekly_macro_v4'):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [run_id, output_id, previous_run]):
        raise ValueError('Invalid local run id')
    folder = ROOT / 'outputs' / run_id
    summary = validate_weekly(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    cfg, settings = protocol['base_config'], protocol['weekly_config']
    source = ROOT / cfg['source']
    assert sha256(source) == summary['source_sha256']
    # Read identifiers only to count unique orders; never log or export them.
    raw = pd.read_csv(source, usecols=ROUTE + ['order_id', 'quantity', 'order_datetime', 'order_status'])
    raw['date'] = pd.to_datetime(raw.order_datetime, utc=True).dt.tz_localize(None).dt.normalize()
    raw = raw.loc[raw.order_status.isin(cfg['sales_statuses'])]
    grid = pd.MultiIndex.from_tuples([(date, *key) for key in sorted(set(raw[ROUTE].itertuples(index=False, name=None)))
        for date in pd.date_range(cfg['observation_start'], cfg['observation_end'])], names=['date'] + ROUTE)
    daily = raw.groupby(['date'] + ROUTE).agg(sales_qty=('quantity', 'sum'), order_count=('order_id', 'nunique')).reindex(grid, fill_value=0).reset_index()
    checks = 0
    for phase in ['validation', 'test', 'future']:
        phase_daily = daily.loc[daily.date.le(cfg['validation_end'])] if phase == 'validation' else daily
        prepared = prepare(phase_daily, settings)
        cache = {}
        logs = pd.read_csv(folder / f'{phase}_head_log.csv', parse_dates=['head_fit_cutoff', 'max_head_label_end'])
        assert not logs.duplicated(ROUTE + ['model', 'week_block', 'head_fit_cutoff']).any()
        assert logs.max_head_label_end.le(logs.head_fit_cutoff).all()
        assert logs.factor.between(.5, 1.5).all()
        for (ident, cutoff), group in logs.groupby(['model', 'head_fit_cutoff'], sort=True):
            spec = settings['models'][ident]
            parent = spec['parent']
            histories = {key: ([], [], []) for key in prepared}
            for past in pd.date_range(cutoff - pd.Timedelta(days=spec['history_days']), cutoff - pd.Timedelta(days=7), freq='7D'):
                key = (parent, past)
                if key not in cache:
                    model, log = fit(prepared, past, settings['models'][parent], cfg, settings)
                    assert log['max_label_end'] <= past
                    cache[key] = predict_batch(model, prepared, past, settings['models'][parent])
                for item, table in prepared.items():
                    idx = np.flatnonzero(table['origins'] == past)
                    assert len(idx) == 1
                    idx = idx[0]
                    label_end = table['ends'][idx]
                    if label_end <= cutoff:
                        p, y, ends = histories[item]
                        p.append(cache[key][item])
                        y.append(table['y'][idx])
                        ends.append(label_end)
            for row in group.itertuples():
                item = ((row.destination_country, row.carrier), row.week_block)
                p, y, ends = histories[item]
                assert len(ends) == row.nonoverlapping_head_weeks
                assert max(ends) == row.max_head_label_end <= cutoff
                np.testing.assert_allclose(row.factor, independent_factor(p, y, spec['prior_weeks']), atol=1e-8, rtol=0)
                checks += 1
            print(f'{phase}: replayed {ident} at {cutoff.date()}', flush=True)
        if phase != 'future':
            frame = pd.read_csv(folder / f'{phase}_weekly_predictions.csv', parse_dates=['as_of_date'])
            np.testing.assert_allclose(frame.forecast_qty_7d, frame.base_forecast_qty_7d * frame.calibration_factor, atol=1e-8, rtol=0)
            assert frame.calibration_factor.between(.5, 1.5).all()
            for ident, spec in settings['models'].items():
                if spec['kind'] != 'calibrated':
                    continue
                head = frame.loc[frame.model.eq(ident)].copy()
                if head.empty:
                    continue
                start = pd.Timestamp(cfg[f'{phase}_start']) - pd.Timedelta(days=1)
                head['head_fit_cutoff'] = start + pd.to_timedelta(((head.as_of_date - start).dt.days // settings['refit_days']) * settings['refit_days'], unit='D')
                paired = head.merge(logs, on=ROUTE + ['model', 'week_block', 'head_fit_cutoff'], validate='many_to_one')
                assert len(paired) == len(head)
                np.testing.assert_allclose(paired.calibration_factor, paired.factor, atol=1e-8, rtol=0)
                if phase == 'validation':
                    parent = frame.loc[frame.model.eq(spec['parent']), ROUTE + ['as_of_date', 'week_block', 'forecast_qty_7d']]
                    paired = head.merge(parent, on=ROUTE + ['as_of_date', 'week_block'], suffixes=('', '_parent'), validate='one_to_one')
                    assert len(paired) == len(head)
                    np.testing.assert_allclose(paired.base_forecast_qty_7d, paired.forecast_qty_7d_parent, atol=1e-8, rtol=0)
    old_folder = ROOT / 'outputs' / previous_run
    old_summary = validate_weekly(old_folder)
    keys = ROUTE + ['model', 'as_of_date', 'week_block']
    old = pd.read_csv(old_folder / 'validation_weekly_predictions.csv')
    new = pd.read_csv(folder / 'validation_weekly_predictions.csv')
    merged = old.merge(new, on=keys, suffixes=('_old', '_new'), validate='one_to_one')
    assert len(merged) == len(old)
    np.testing.assert_allclose(merged.forecast_qty_7d_old, merged.forecast_qty_7d_new, atol=1e-8, rtol=0)
    validate_weekly(folder); validate_weekly(old_folder)
    assert sha256(source) == summary['source_sha256'] == old_summary['source_sha256']
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    result = {'status': 'verified', 'head_factor_checks': checks, 'teacher_labels_at_or_before_teacher_origin': True,
        'head_labels_at_or_before_head_cutoff': True, 'independent_weighted_median_match': True,
        'base_times_factor_matches': True, 'previous_validation_pairs_unchanged': len(merged),
        'source_unchanged': True, 'weekly_summary_sha256': sha256(folder / 'summary.json'),
        'verification_code_sha256': sha256(__file__), 'daily_R05_met': False, 'test_is_independent': False}
    write_json(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    parser.add_argument('--previous-run', default='sigma_weekly_macro_v4')
    args = parser.parse_args()
    verify(args.run_id, args.output_id, args.previous_run)
