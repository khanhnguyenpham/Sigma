"""Independent raw-label, coverage, metric and daily-versus-weekly comparison."""
from __future__ import annotations

import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, write_csv, write_json, validate_run


def validate_weekly(folder):
    folder = folder.resolve()
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    if summary.get('status') != 'complete' or summary.get('kind') != 'weekly_quantity_run':
        raise ValueError('Not a complete weekly run')
    required = {'protocol.json', 'selected_weekly_models.csv', 'top_routes.csv', 'weekly_forecast.csv',
        'daily_allocation.csv', 'daily_sales.csv', 'test_weekly_predictions.csv',
        'validation_weekly_predictions.csv', 'test_weekly_metrics.csv', 'validation_weekly_metrics.csv',
        'selected_test_weekly_metrics.csv'}
    if not required.issubset(summary['files']):
        raise ValueError('Missing weekly artifacts')
    for name, expected in summary['files'].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha256(path) != expected:
            raise ValueError('Weekly artifact missing or changed')
    if sha256(folder / 'selected_weekly_models.csv') != summary['selection_sha256']:
        raise ValueError('Weekly selection lock changed')
    return summary


def manual_metric(g):
    y, p = g.actual_qty_7d.to_numpy(float), g.forecast_qty_7d.to_numpy(float)
    error = p - y
    positive = y > 0
    return {'mape_positive_week_pct': float(np.mean(np.abs(error[positive]) / y[positive]) * 100) if positive.any() else np.nan,
        'mae_week_qty': float(np.mean(np.abs(error))),
        'wape_pct': float(np.abs(error).sum() / y.sum() * 100) if y.sum() else np.nan,
        'bias_pct': float(error.sum() / y.sum() * 100) if y.sum() else np.nan}


def verify(run_id, output_id, daily_run='sigma_scaled_v11'):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in [run_id, output_id, daily_run]):
        raise ValueError('Invalid local id')
    folder = ROOT / 'outputs' / run_id
    summary = validate_weekly(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    cfg = protocol['base_config']
    source = (ROOT / cfg['source']).resolve()
    if not source.is_relative_to(ROOT) or sha256(source) != summary['source_sha256']:
        raise ValueError('Raw source changed')
    # Independent quantity/day aggregation: no source identifiers read or exported.
    raw = pd.read_csv(source, usecols=ROUTE + ['quantity', 'order_datetime', 'order_status'])
    raw['date'] = pd.to_datetime(raw.order_datetime, utc=True).dt.tz_localize(None).dt.normalize()
    sales = raw.loc[raw.order_status.isin(cfg['sales_statuses'])]
    dates = pd.date_range(cfg['observation_start'], cfg['observation_end'])
    groups = {key: g.groupby('date').quantity.sum().reindex(dates, fill_value=0).astype(float)
              for key, g in sales.groupby(ROUTE, sort=True)}
    top = sales.loc[sales.date.le(cfg['train_end'])].groupby(ROUTE, as_index=False).quantity.sum()
    top = top.sort_values(['quantity'] + ROUTE, ascending=[False, True, True]).head(cfg['top_n'])
    stored_top = pd.read_csv(folder / 'top_routes.csv')
    assert list(map(tuple, top[ROUTE].to_numpy())) == list(map(tuple, stored_top[ROUTE].to_numpy()))
    selected = pd.read_csv(folder / 'selected_weekly_models.csv')
    inspected_pairs = 0
    frames = {}
    for phase in ['validation', 'test']:
        frame = pd.read_csv(folder / f'{phase}_weekly_predictions.csv',
            parse_dates=['as_of_date', 'window_start', 'window_end'])
        frames[phase] = frame
        assert not frame.duplicated(ROUTE + ['model', 'as_of_date', 'week_block']).any()
        choices = dict(zip(map(tuple, selected[ROUTE].to_numpy()), selected.model))
        expected_groups = {(key[0], key[1], model, block) for key in groups
            for model in (protocol['weekly_config']['models'] if phase == 'validation' else [choices[key]])
            for block in (1, 2)}
        assert set(frame[ROUTE + ['model', 'week_block']].itertuples(index=False, name=None)) == expected_groups
        stored_metrics = pd.read_csv(folder / f'{phase}_weekly_metrics.csv')
        for keys, g in frame.groupby(ROUTE + ['model', 'week_block']):
            country, carrier, model, block = keys
            y = groups[(country, carrier)]
            expected_origins = pd.date_range(pd.Timestamp(cfg[f'{phase}_start']) - pd.Timedelta(days=1),
                pd.Timestamp(cfg[f'{phase}_end']) - pd.Timedelta(days=7 * block))
            assert g.as_of_date.tolist() == expected_origins.tolist()
            assert (g.window_start == g.as_of_date + pd.Timedelta(days=1 + 7 * (block - 1))).all()
            assert (g.window_end == g.window_start + pd.Timedelta(days=6)).all()
            expected = np.array([y.loc[start:end].sum() for start, end in zip(g.window_start, g.window_end)])
            np.testing.assert_array_equal(g.actual_qty_7d.to_numpy(), expected)
            assert np.isfinite(g.forecast_qty_7d).all() and g.forecast_qty_7d.ge(0).all()
            inspected_pairs += len(g)
            for cadence in ['daily_origins', 'seven_day_origins']:
                subset = g if cadence == 'daily_origins' else g.loc[g.weekly_cadence.eq(True)]
                row = stored_metrics.loc[stored_metrics.destination_country.eq(country)
                    & stored_metrics.carrier.eq(carrier) & stored_metrics.model.eq(model)
                    & stored_metrics.week_block.eq(block) & stored_metrics.cadence.eq(cadence)]
                assert len(row) == 1 and row.iloc[0].coverage == 1.
                for name, value in manual_metric(subset).items():
                    np.testing.assert_allclose(row.iloc[0][name], value, atol=1e-8, rtol=0, equal_nan=True)
        fit_path = folder / f'{phase}_fit_log.csv'
        if fit_path.stat().st_size > 3:
            fitlog = pd.read_csv(fit_path, parse_dates=['fit_cutoff', 'max_label_end'])
            assert fitlog.max_label_end.le(fitlog.fit_cutoff).all()
    vm = pd.read_csv(folder / 'validation_weekly_metrics.csv')
    winner = vm.loc[vm.week_block.eq(1) & vm.cadence.eq('daily_origins') & vm.coverage.eq(1)]
    winner = winner.sort_values(['mape_positive_week_pct', 'mae_week_qty', 'model']).drop_duplicates(ROUTE)
    assert dict(zip(map(tuple, winner[ROUTE].to_numpy()), winner.model)) == dict(zip(map(tuple, selected[ROUTE].to_numpy()), selected.model))
    forecast = pd.read_csv(folder / 'weekly_forecast.csv', parse_dates=['as_of_date', 'window_start', 'window_end'])
    allocation = pd.read_csv(folder / 'daily_allocation.csv', parse_dates=['as_of_date', 'target_date'])
    assert forecast.actual_qty_7d.isna().all() and allocation.actual_qty.isna().all()
    for row in forecast.itertuples():
        a = allocation.loc[allocation.destination_country.eq(row.destination_country)
            & allocation.carrier.eq(row.carrier) & allocation.week_block.eq(row.week_block)].sort_values('target_date')
        assert len(a) == 7
        np.testing.assert_allclose(a.forecast_qty.sum(), row.forecast_qty_7d, atol=1e-8, rtol=0)
        history = groups[(row.destination_country, row.carrier)].loc[:row.as_of_date].iloc[-90:]
        means = history.groupby(history.index.dayofweek).mean().reindex(range(7), fill_value=0)
        weights = means.reindex(pd.DatetimeIndex(a.target_date).dayofweek).to_numpy()
        weights = weights / weights.sum() if weights.sum() else np.repeat(1/7, 7)
        np.testing.assert_allclose(a.forecast_qty, weights * row.forecast_qty_7d, atol=1e-8, rtol=0)
    # Matched windows: compare direct weekly forecast with sums of daily forecasts.
    daily_folder = ROOT / 'outputs' / daily_run
    sealed = validate_run(daily_folder)
    old = pd.read_csv(daily_folder / 'predictions.csv', parse_dates=['as_of_date', 'target_date'])
    old = old.loc[old.split.eq('test') & old.model.eq('selected')].copy()
    old['week_block'] = ((old.horizon_day - 1) // 7 + 1).astype(int)
    comparisons, daily_diagnostic = [], []
    for keys, g in frames['test'].groupby(ROUTE + ['week_block']):
        country, carrier, block = keys
        y = groups[(country, carrier)]
        for name in ['direct_weekly', 'sum_daily_v11', 'sum_daily_naive', 'sum_daily_ma7', 'sum_daily_ma28']:
            candidate = g.copy()
            if name == 'sum_daily_v11':
                d = old.loc[old.destination_country.eq(country) & old.carrier.eq(carrier) & old.week_block.eq(block)]
                complete = d.groupby('as_of_date').filter(lambda f: len(f) == 7)
                totals = complete.groupby('as_of_date').forecast_qty.sum()
                candidate['forecast_qty_7d'] = totals.reindex(g.as_of_date).to_numpy()
            elif name.startswith('sum_daily_'):
                window = {'sum_daily_naive': 1, 'sum_daily_ma7': 7, 'sum_daily_ma28': 28}[name]
                candidate['forecast_qty_7d'] = [float(y.loc[:origin].iloc[-window:].mean() * 7) for origin in g.as_of_date]
            if not np.isfinite(candidate.forecast_qty_7d).all():
                raise ValueError('Daily comparison has missing matched windows')
            for cadence in ['daily_origins', 'seven_day_origins']:
                subset = candidate if cadence == 'daily_origins' else candidate.loc[candidate.weekly_cadence.eq(True)]
                comparisons.append({**dict(zip(ROUTE, keys[:2])), 'week_block': block, 'cadence': cadence,
                    'method': name, 'pairs': len(subset), **manual_metric(subset)})
        # Score allocated days honestly, without certifying daily R05 from weekly totals.
        errors, positive_errors, total_y = [], [], 0.
        for row in g.itertuples():
            future_dates = pd.date_range(row.window_start, row.window_end)
            history = y.loc[:row.as_of_date].iloc[-90:]
            means = history.groupby(history.index.dayofweek).mean().reindex(range(7), fill_value=0)
            weights = means.reindex(future_dates.dayofweek).to_numpy()
            weights = weights / weights.sum() if weights.sum() else np.repeat(1/7, 7)
            actual = y.reindex(future_dates).to_numpy()
            error = weights * row.forecast_qty_7d - actual
            errors.extend(np.abs(error)); positive_errors.extend((np.abs(error[actual > 0]) / actual[actual > 0]).tolist())
            total_y += actual.sum()
        daily_diagnostic.append({**dict(zip(ROUTE, keys[:2])), 'week_block': block,
            'mape_positive_day_pct': np.mean(positive_errors) * 100 if positive_errors else np.nan,
            'mae_day_qty': np.mean(errors), 'wape_pct': np.sum(errors) / total_y * 100 if total_y else np.nan,
            'daily_pairs': len(errors), 'daily_acceptance_evaluated': False,
            'limit': 'Complete-week windows only: diagnostic differs from full daily R05 pair grid'})
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    write_csv(out / 'weekly_comparison.csv', pd.DataFrame(comparisons))
    write_csv(out / 'daily_allocation_diagnostic.csv', pd.DataFrame(daily_diagnostic))
    validate_run(daily_folder)
    validate_weekly(folder)
    evidence = {'status': 'verified', 'raw_labels_match': True, 'weekly_metric_manual_match': True,
        'all_complete_windows_covered': True, 'fit_labels_at_or_before_cutoff': True,
        'selection_matches_validation': True, 'future_actuals_missing': True,
        'daily_allocation_conserves_each_week': True, 'pairs_checked': inspected_pairs,
        'daily_sealed_files_unchanged': len(sealed['files']),
        'weekly_summary_sha256': sha256(folder / 'summary.json'),
        'source_unchanged': sha256(source) == summary['source_sha256'],
        'daily_R05_met': False, 'test_is_independent': False}
    evidence['files'] = {p.name: sha256(p) for p in out.iterdir() if p.is_file()}
    write_json(out / 'summary.json', evidence)
    print(json.dumps(evidence), flush=True)
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    parser.add_argument('--daily-run', default='sigma_scaled_v11')
    args = parser.parse_args()
    verify(args.run_id, args.output_id, args.daily_run)
