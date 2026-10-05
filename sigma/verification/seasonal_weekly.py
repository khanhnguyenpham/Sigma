"""Independently reconcile validation research labels, scores and causal memory."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, validate_run, write_json
from sigma.experiments.seasonal_weekly import SPECS, SeasonalMemory
from sigma.forecasting.weekly import prepare


def verify(run_id, output_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in [run_id, output_id]):
        raise ValueError('Invalid verification identifier')
    folder = ROOT / 'outputs' / run_id
    result = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    assert result['status'] == 'complete' and result['kind'] == 'validation_only_seasonal_research'
    assert result['test_scored'] is False and result['production_modified'] is False
    assert protocol['candidates'] == SPECS
    for name, digest in result['files'].items():
        assert (folder / name).resolve().is_relative_to(folder)
        assert sha256(folder / name) == digest
    wdir = ROOT / 'outputs' / protocol['weekly_parent']
    ddir = ROOT / 'outputs' / protocol['daily_parent']
    assert sha256(wdir / 'summary.json') == protocol['weekly_parent_sha256']
    assert sha256(ddir / 'manifest.json') == protocol['daily_parent_sha256']
    assert sha256(ROOT / 'sigma/experiments/seasonal_weekly.py') == protocol['entrypoint_sha256']
    for name, digest in protocol['dependencies_sha256'].items():
        assert sha256(ROOT / name) == digest
    day = validate_run(ddir)
    wp = json.loads((wdir / 'protocol.json').read_text(encoding='utf-8'))
    parent = json.loads((wdir / 'summary.json').read_text(encoding='utf-8'))
    cfg, settings = wp['base_config'], wp['weekly_config']
    source = (ROOT / cfg['source']).resolve()
    assert source.is_relative_to(ROOT)
    assert sha256(source) == protocol['source_sha256'] == day['source_sha256'] == parent['source_sha256']
    assert sha256(wdir / 'daily_sales.csv') == parent['files']['daily_sales.csv']
    daily = pd.read_csv(wdir / 'daily_sales.csv', parse_dates=['date'])
    daily = daily.loc[daily.date.le(cfg['validation_end'])].copy()
    groups = {key: g.set_index('date').sales_qty for key, g in daily.groupby(ROUTE)}
    frame = pd.read_csv(folder / 'validation_predictions.csv', parse_dates=['as_of_date', 'window_start', 'window_end'])
    scores = pd.read_csv(folder / 'validation_metrics.csv')
    assert set(frame.model) == set(SPECS) and frame.split.eq('validation').all()
    assert not frame.duplicated(ROUTE + ['model', 'week_block', 'as_of_date']).any()
    assert frame.window_end.le(pd.Timestamp(cfg['validation_end'])).all()
    assert np.isfinite(frame.forecast_qty_7d).all() and frame.forecast_qty_7d.ge(0).all()
    expected_labels = []
    for r in frame.itertuples():
        assert r.window_start == r.as_of_date + pd.Timedelta(days=1 + 7 * (r.week_block - 1))
        assert r.window_end == r.window_start + pd.Timedelta(days=6)
        series = groups[(r.destination_country, r.carrier)].loc[r.window_start:r.window_end]
        assert len(series) == 7
        expected_labels.append(series.sum())
    np.testing.assert_array_equal(frame.actual_qty_7d, expected_labels)
    checked_metrics = 0
    for r in scores.itertuples():
        subset = frame.loc[frame.destination_country.eq(r.destination_country) & frame.carrier.eq(r.carrier)
            & frame.model.eq(r.model) & frame.week_block.eq(r.week_block)].sort_values('as_of_date')
        count = (pd.Timestamp(cfg['validation_end']) - pd.Timestamp(cfg['validation_start'])).days + 2 - 7 * r.week_block
        origins = pd.date_range(pd.Timestamp(cfg['validation_start']) - pd.Timedelta(days=1), periods=count)
        if r.cadence == 'seven_day_origins':
            subset, origins = subset.loc[subset.weekly_cadence], origins[::7]
        assert list(subset.as_of_date) == list(origins)
        y, p = subset.actual_qty_7d.to_numpy(), subset.forecast_qty_7d.to_numpy()
        error = p - y
        assert r.pairs == r.expected_pairs == len(origins) and r.coverage == 1
        assert r.positive_windows == int((y > 0).sum()) and r.zero_windows == int((y == 0).sum())
        values = [np.abs(error[y > 0] / y[y > 0]).mean() * 100 if (y > 0).any() else np.nan,
            np.abs(error).mean(), np.abs(error).sum() / y.sum() * 100 if y.sum() else np.nan,
            error.sum() / y.sum() * 100 if y.sum() else np.nan]
        np.testing.assert_allclose([r.mape_positive_week_pct, r.mae_week_qty, r.wape_pct, r.bias_pct],
            values, rtol=0, atol=1e-8, equal_nan=True)
        checked_metrics += 1
    logs = pd.read_csv(folder / 'fit_log.csv', parse_dates=['fit_cutoff', 'max_label_end'])
    assert logs.max_label_end.le(logs.fit_cutoff).all()
    mutations = 0
    for origin in pd.to_datetime(['2025-06-30', '2025-08-25']):
        changed = daily.copy()
        changed.loc[changed.date.gt(origin), ['sales_qty', 'order_count']] = 999999.
        a, b = prepare(daily, settings), prepare(changed, settings)
        for spec in SPECS.values():
            ma = SeasonalMemory(spec).fit(a, origin, settings['training_window_days'])
            mb = SeasonalMemory(spec).fit(b, origin, settings['training_window_days'])
            assert ma.predict(a, origin) == mb.predict(b, origin)
            mutations += 1
    comparison = pd.read_csv(folder / 'validation_comparison.csv')
    original = pd.read_csv(wdir / 'selected_weekly_models.csv')
    for r in comparison.itertuples():
        old = original.loc[original.destination_country.eq(r.destination_country) & original.carrier.eq(r.carrier)].iloc[0]
        candidates = scores.loc[scores.destination_country.eq(r.destination_country) & scores.carrier.eq(r.carrier)
            & scores.week_block.eq(1) & scores.cadence.eq('daily_origins')].sort_values(['mape_positive_week_pct', 'mae_week_qty', 'model'])
        assert r.model_parent == old.model and r.model_research == candidates.iloc[0].model
        assert r.research_improves_validation == (r.mape_positive_week_pct_research < old.mape_positive_week_pct)
    assert sha256(source) == protocol['source_sha256']
    validate_run(ddir)
    verified = {'status': 'verified', 'run_id': run_id, 'research_summary_sha256': sha256(folder / 'summary.json'),
        'quantity_pairs_checked': len(frame), 'metric_groups_checked': checked_metrics,
        'future_mutation_checks': mutations, 'source_and_sealed_daily_unchanged': True,
        'test_scored': False, 'daily_R05_met': False}
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    write_json(out / 'summary.json', verified)
    print(json.dumps(verified), flush=True)
    return verified


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    args = parser.parse_args()
    verify(args.run_id, args.output_id)
