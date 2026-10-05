"""Validation-only seasonal memory, isolated from production and test scoring."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, validate_run, write_csv, write_json
from sigma.forecasting.weekly import checked_series, prepare, metrics


SPECS = {f'seasonal_{units}_b{width}': {'units': units,
    'bandwidth_days': width, 'half_life_days': None}
    for units in ('raw', 'ratio') for width in (28, 56)}
SPECS.update({f'seasonal_ratio_b{width}_recent90': {'units': 'ratio',
    'bandwidth_days': width, 'half_life_days': 90} for width in (28, 56)})


def weighted_median(values, weights):
    values, weights = np.asarray(values, float), np.asarray(weights, float)
    if (values.shape != weights.shape or not np.isfinite([values, weights]).all()
            or (values < 0).any() or (weights < 0).any()):
        raise ValueError('Invalid seasonal memory')
    active = weights > 0
    if not active.any():
        return 0.
    values, weights = values[active], weights[active]
    order = np.argsort(values, kind='stable')
    return float(values[order][np.searchsorted(np.cumsum(weights[order]), weights.sum() / 2)])


def calendar_distance(sin_a, cos_a, sin_b, cos_b):
    """Shortest circular distance, including the December/January seam."""
    cosine = np.clip(np.asarray(sin_a) * sin_b + np.asarray(cos_a) * cos_b, -1., 1.)
    return np.arccos(cosine) * 365.25 / (2 * np.pi)


class SeasonalMemory:
    def __init__(self, spec):
        self.spec = spec
        if (spec['units'] not in ('raw', 'ratio')
                or not np.isfinite(spec['bandwidth_days']) or spec['bandwidth_days'] <= 0
                or (spec['half_life_days'] is not None
                    and (not np.isfinite(spec['half_life_days']) or spec['half_life_days'] <= 0))):
            raise ValueError('Invalid seasonal settings')

    def fit(self, prepared, cutoff, training_days):
        self.cutoff, self.memory = pd.Timestamp(cutoff), {}
        maximum = []
        for key, table in prepared.items():
            idx = np.flatnonzero((table['ends'] <= self.cutoff)
                & (table['ends'] >= self.cutoff - pd.Timedelta(days=training_days - 1)))
            if not len(idx):
                raise ValueError('No fully observed seasonal labels')
            y = table['y'][idx].copy()
            if not np.isfinite(y).all() or (y < 0).any():
                raise ValueError('Invalid seasonal labels')
            if self.spec['units'] == 'ratio':
                y /= table['scale'][idx]
            weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
            if self.spec['half_life_days'] is not None:
                weights *= np.exp2(-(self.cutoff - table['ends'][idx]).days.to_numpy() / self.spec['half_life_days'])
            x = table['x'].iloc[idx]
            self.memory[key] = (x.year_sin.to_numpy(), x.year_cos.to_numpy(), y, weights)
            maximum.append(table['ends'][idx].max())
        self.max_label_end = max(maximum)
        return self

    def predict(self, prepared, origin):
        if pd.Timestamp(origin) < self.cutoff:
            raise ValueError('Prediction origin predates fit')
        result = {}
        for key, table in prepared.items():
            idx = np.flatnonzero(table['origins'] == pd.Timestamp(origin))
            if len(idx) != 1 or key not in self.memory:
                raise ValueError('Missing seasonal route or origin')
            x = table['x'].iloc[idx[0]]
            s, c, y, w = self.memory[key]
            distance = calendar_distance(s, c, x.year_sin, x.year_cos)
            value = weighted_median(y, w * np.exp(-.5 * (distance / self.spec['bandwidth_days']) ** 2))
            if self.spec['units'] == 'ratio':
                value *= table['scale'][idx[0]]
            result[key] = value
        return result


def evaluate(daily, settings, cfg):
    prepared = prepare(daily, settings)
    start, end = pd.Timestamp(cfg['validation_start']), pd.Timestamp(cfg['validation_end'])
    rows, logs = [], []
    for ident, spec in SPECS.items():
        for i, origin in enumerate(pd.date_range(start - pd.Timedelta(days=1), end - pd.Timedelta(days=1))):
            if i % settings['refit_days'] == 0:
                model = SeasonalMemory(spec).fit(prepared, origin, settings['training_window_days'])
                logs.append({'model': ident, 'fit_cutoff': origin, 'max_label_end': model.max_label_end})
            values = model.predict(prepared, origin)
            for (key, block), table in prepared.items():
                window_start = origin + pd.Timedelta(days=1 + 7 * (block - 1))
                window_end = window_start + pd.Timedelta(days=6)
                if window_end > end:
                    continue
                index = np.flatnonzero(table['origins'] == origin)[0]
                rows.append({**dict(zip(ROUTE, key)), 'model': ident, 'week_block': block,
                    'as_of_date': origin, 'window_start': window_start, 'window_end': window_end,
                    'forecast_qty_7d': values[(key, block)], 'actual_qty_7d': table['y'][index],
                    'split': 'validation', 'weekly_cadence': i % 7 == 0})
        print('validation: completed ' + ident, flush=True)
    frame = pd.DataFrame(rows)
    return frame, pd.DataFrame(logs), metrics(frame, start, end)


def dispersion(daily, top, cfg):
    """Variability and optimistic hindsight fit; never a predictive lower bound."""
    rows = []
    keys = set(top[ROUTE].itertuples(index=False, name=None))
    for key, g in daily.groupby(ROUTE):
        if key not in keys:
            continue
        for split, subset in [('train', g.loc[g.date.le(cfg['train_end'])]),
                ('validation', g.loc[g.date.between(cfg['validation_start'], cfg['validation_end'])])]:
            y = subset.set_index('date').sales_qty.astype(float)
            seven = y.rolling(7, min_periods=7).sum().dropna()
            fitted = pd.Series(index=y.index, dtype=float)
            for _, part in y.groupby([y.index.month, y.index.dayofweek]):
                weight = np.divide(1., part.to_numpy(), out=np.zeros(len(part)), where=part.to_numpy() > 0)
                fitted.loc[part.index] = weighted_median(part.to_numpy(), weight)
            positive = y > 0
            rows.append({**dict(zip(ROUTE, key)), 'split': split, 'observed_days': len(y),
                'positive_days': int(positive.sum()), 'mean_daily_qty': y.mean(),
                'daily_cv': y.std(ddof=0) / y.mean() if y.mean() else np.nan,
                'weekly_cv': seven.std(ddof=0) / seven.mean() if seven.mean() else np.nan,
                'daily_lag1_correlation': y.autocorr(1),
                'hindsight_month_weekday_mape_pct': 100 * ((y[positive] - fitted[positive]).abs() / y[positive]).mean(),
                'hindsight_is_predictive_lower_bound': False})
    return pd.DataFrame(rows)


def run(output_id, weekly_run='sigma_weekly_boost_v13', daily_run='sigma_scaled_v11'):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in [output_id, weekly_run, daily_run]):
        raise ValueError('Invalid research identifier')
    wdir, ddir = ROOT / 'outputs' / weekly_run, ROOT / 'outputs' / daily_run
    parent = json.loads((wdir / 'summary.json').read_text(encoding='utf-8'))
    protocol = json.loads((wdir / 'protocol.json').read_text(encoding='utf-8'))
    day = validate_run(ddir)
    cfg, settings = protocol['base_config'], protocol['weekly_config']
    source = (ROOT / cfg['source']).resolve()
    if not source.is_relative_to(ROOT) or not sha256(source) == parent['source_sha256'] == day['source_sha256']:
        raise ValueError('Research source differs')
    names = ['protocol.json', 'daily_sales.csv', 'top_routes.csv', 'selected_weekly_models.csv']
    if any(sha256(wdir / name) != parent['files'][name] for name in names):
        raise ValueError('Research parent artifact changed')
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    dependencies = ['sigma/forecasting/weekly.py', 'sigma/forecasting/macro.py', 'src/common.py']
    registered = {'status': 'registered_before_fit', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'candidates': SPECS, 'weekly_parent': weekly_run, 'daily_parent': daily_run,
        'weekly_parent_sha256': sha256(wdir / 'summary.json'), 'daily_parent_sha256': sha256(ddir / 'manifest.json'),
        'source_sha256': sha256(source), 'entrypoint_sha256': sha256(__file__),
        'dependencies_sha256': {name: sha256(ROOT / name) for name in dependencies},
        'training_window_days': settings['training_window_days'], 'refit_days': settings['refit_days'],
        'hypothesis': 'Smooth circular calendar memory may reduce local seasonal underfit; raw/causal-ratio and recency variants registered for every route.',
        'promotion_rule': 'Research only; compare fixed validation MAPE then MAE with locked parent. Never promote from test results.',
        'test_limit': 'Existing test previously viewed; no test targets used here. Reused validation is not independent.',
        'diagnostic_limit': 'CV/correlation/hindsight fit describe variability; they do not prove the threshold impossible.',
        'daily_R05_replaced': False, 'production_modified': False}
    write_json(out / 'protocol.json', registered)
    daily = pd.read_csv(wdir / 'daily_sales.csv', parse_dates=['date'])
    daily = daily.loc[daily.date.le(cfg['validation_end'])].copy()
    checked_series(daily)
    top = pd.read_csv(wdir / 'top_routes.csv')
    write_csv(out / 'dispersion.csv', dispersion(daily, top, cfg))
    frame, logs, scores = evaluate(daily, settings, cfg)
    write_csv(out / 'validation_predictions.csv', frame)
    write_csv(out / 'fit_log.csv', logs)
    write_csv(out / 'validation_metrics.csv', scores)
    original = pd.read_csv(wdir / 'selected_weekly_models.csv')
    eligible = scores.loc[scores.week_block.eq(1) & scores.cadence.eq('daily_origins') & scores.coverage.eq(1)]
    best = eligible.sort_values(['mape_positive_week_pct', 'mae_week_qty', 'model']).drop_duplicates(ROUTE)
    comparison = original.merge(best[ROUTE + ['model', 'mape_positive_week_pct', 'mae_week_qty']], on=ROUTE,
        suffixes=('_parent', '_research'), validate='one_to_one')
    comparison['research_improves_validation'] = comparison.mape_positive_week_pct_research < comparison.mape_positive_week_pct_parent
    write_csv(out / 'validation_comparison.csv', comparison)
    if not scores.coverage.eq(1).all() or not logs.max_label_end.le(logs.fit_cutoff).all():
        raise ValueError('Research coverage or causality failed')
    if sha256(source) != registered['source_sha256'] or sha256(__file__) != registered['entrypoint_sha256']:
        raise ValueError('Research source or implementation changed')
    if any(sha256(ROOT / name) != digest for name, digest in registered['dependencies_sha256'].items()):
        raise ValueError('Research dependency changed')
    validate_run(ddir)
    if sha256(wdir / 'summary.json') != registered['weekly_parent_sha256']:
        raise ValueError('Research parent changed')
    primary = comparison.loc[comparison.is_top10]
    result = {'status': 'complete', 'kind': 'validation_only_seasonal_research', 'run_id': output_id,
        'source_sha256': registered['source_sha256'], 'prediction_pairs': len(frame),
        'top10_research_validation_passed': int(primary.mape_positive_week_pct_research.le(20).sum()),
        'top10_validation_improved': int(primary.research_improves_validation.sum()),
        'routes_validation_improved': int(comparison.research_improves_validation.sum()),
        'full_coverage': True, 'no_future_labels': True, 'test_scored': False,
        'daily_R05_met': False, 'production_modified': False,
        'files': {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()}}
    write_json(out / 'summary.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-id', required=True)
    parser.add_argument('--weekly-run', default='sigma_weekly_boost_v13')
    parser.add_argument('--daily-run', default='sigma_scaled_v11')
    args = parser.parse_args()
    run(args.output_id, args.weekly_run, args.daily_run)
