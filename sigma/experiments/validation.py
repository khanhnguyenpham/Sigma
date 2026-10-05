"""Isolated, preregistered sales-forecast ablation; never reads the test split.

Run outputs are private. This research entry point does not change production
selection, config, forecasts or any sealed run. May-June is an inner tuning
slice of train, not a replacement for the official July-September validation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime, timezone
import json

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json
from src.data import audit_orders, daily_sales, route_top
from src.context_models import prepare_context, context_features, CONTEXT_FEATURES
from src.evaluation import metric_table


SPECS = {
    f"ablation_{family}_{units}_l{leaves}": {
        "family": family, "units": units, "leaves": leaves,
        "window": 365, "n_estimators": 200, "learning_rate": .03,
        "min_child_samples": 150, "reg_lambda": 10.,
    }
    for family in ("calendar", "history", "annual")
    for units in ("raw", "ratio") for leaves in (7, 31)
}
CALENDAR = ['route_index', 'horizon_day', 'target_weekday', 'target_month',
            'target_elapsed_days', 'year_sin', 'year_cos']
ANNUAL = ['prior_year_qty', 'prior_year_mean15', 'prior_year_mean57',
          'prior_year_country_mean15', 'prior_year_global_mean15']
COUNTS = ['order_mean7', 'order_mean28', 'order_mean90', 'basket_mean28',
          'positive_share28', 'positive_share90']
CATEGORICAL = ['route_index', 'target_weekday', 'target_month']
INNER_START = pd.Timestamp('2025-05-01')
INNER_END = pd.Timestamp('2025-06-30')


def features(daily, keys):
    """Precompute trailing features; prior-year windows end before each origin.

    The frame may contain later dates for efficient indexing. No operation
    that produces an origin's inputs consumes observations after that origin.
    Native missing values represent unavailable prior-year history.
    """
    contexts = prepare_context(daily, keys, daily.date.max())
    wide = daily.pivot(index='date', columns=ROUTE, values='sales_qty').sort_index()
    countries = {c: wide.loc[:, wide.columns.get_level_values(0) == c].sum(axis=1)
                 for c in wide.columns.get_level_values(0).unique()}
    total = wide.sum(axis=1)
    result = {}
    for key, ctx in contexts.items():
        dates, y = ctx['dates'], ctx['values']
        counts = daily.loc[daily.destination_country.eq(key[0]) & daily.carrier.eq(key[1])]
        counts = counts.set_index('date').order_count.reindex(dates).astype(float)
        if not np.isfinite(counts).all() or (counts < 0).any():
            raise ValueError('Incomplete nonnegative order-count history')
        qty = pd.Series(y, index=dates)
        trailing = pd.DataFrame({
            **{f'order_mean{w}': counts.rolling(w, min_periods=min(28, w)).mean()
               for w in (7, 28, 90)},
            'basket_mean28': qty.rolling(28).sum() / counts.rolling(28).sum().clip(lower=1),
            **{f'positive_share{w}': qty.gt(0).rolling(w, min_periods=28).mean()
               for w in (28, 90)},
        }).to_numpy()
        for horizon in range(1, 15):
            indices = np.arange(55, len(y))
            x = context_features(ctx, indices, horizon)
            x[COUNTS] = trailing[indices]
            targets = dates[indices] + pd.Timedelta(days=horizon)
            prior = targets - pd.DateOffset(years=1)
            if (prior + pd.Timedelta(days=28) > dates[indices]).any():
                raise ValueError('Prior-year window exceeds origin')
            # Centered historical windows are available a year later, including
            # leap-day alignment. Complete prior windows are required.
            x[ANNUAL[0]] = qty.reindex(prior).to_numpy()
            for name, series, width in [(ANNUAL[1], qty, 15), (ANNUAL[2], qty, 57),
                    (ANNUAL[3], countries[key[0]], 15), (ANNUAL[4], total, 15)]:
                x[name] = series.rolling(width, center=True, min_periods=width).mean().reindex(prior).to_numpy()
            scale = np.maximum(ctx['rolling'][90][indices], 1.)
            result[(key, horizon)] = {
                'x': x, 'origins': dates[indices], 'targets': targets,
                'y': qty.reindex(targets).to_numpy(float), 'scale': scale,
            }
    return result


def model_inputs(table, spec, indices=None):
    if spec['family'] == 'calendar':
        names = CALENDAR
    else:
        names = CONTEXT_FEATURES + COUNTS
        if spec['family'] == 'annual':
            names = names + ANNUAL
    x = table['x'].loc[:, names]
    scale = table['scale']
    if indices is not None:
        x = x.iloc[indices]
        scale = scale[indices]
    x = x.copy()
    if spec['units'] == 'ratio':
        # Both labels and dimensioned route inputs use the origin's trailing
        # quantity scale. Forecasts are restored to original quantity units.
        route_amounts = {'lag0', 'lag1', 'lag7', 'lag14', 'mean7', 'mean28',
            'mean56', 'mean90', 'std28', 'weekday_last', 'weekday_previous',
            'prior_year_qty', 'prior_year_mean15', 'prior_year_mean57'}
        for name in route_amounts.intersection(names):
            x[name] = x[name].to_numpy() / scale
    return x


def fit(prepared, cutoff, spec, cfg):
    xs, ys, scales, label_dates = [], [], [], []
    for table in prepared.values():
        eligible = ((table['targets'] <= cutoff)
                    & (table['targets'] >= cutoff - pd.Timedelta(days=spec['window'] - 1)))
        if not eligible.any():
            continue
        xs.append(model_inputs(table, spec, np.flatnonzero(eligible)))
        ys.append(table['y'][eligible]); scales.append(table['scale'][eligible])
        label_dates.append(table['targets'][eligible].max())
    if not xs or max(label_dates) > cutoff:
        raise ValueError('No causal labels at cutoff')
    x, y = pd.concat(xs, ignore_index=True), np.concatenate(ys)
    if not np.isfinite(y).all() or (y < 0).any():
        raise ValueError('Missing or negative training labels')
    if spec['units'] == 'ratio':
        y = y / np.concatenate(scales)
    weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
    if not weights.any():
        from sklearn.dummy import DummyRegressor
        model = DummyRegressor(strategy='constant', constant=0).fit(x, y)
    else:
        model = LGBMRegressor(objective='regression_l1', num_leaves=spec['leaves'],
            n_estimators=spec['n_estimators'], learning_rate=spec['learning_rate'],
            min_child_samples=spec['min_child_samples'], reg_lambda=spec['reg_lambda'],
            random_state=cfg['seed'], n_jobs=cfg['lightgbm_threads'],
            deterministic=True, force_col_wise=True, verbosity=-1)
        model.fit(x, y, sample_weight=weights, categorical_feature=CATEGORICAL)
    return model, max(label_dates), len(y)


def predict(model, prepared, origin, spec):
    xs, scales, metadata = [], [], []
    for (key, horizon), table in prepared.items():
        indices = np.flatnonzero(table['origins'] == origin)
        if len(indices) != 1:
            raise ValueError('Missing or duplicated origin')
        idx = indices[0]
        xs.append(model_inputs(table, spec, [idx]))
        scales.append(table['scale'][idx]); metadata.append((key, horizon, table['y'][idx]))
    raw = model.predict(pd.concat(xs, ignore_index=True))
    if spec['units'] == 'ratio':
        raw = raw * np.asarray(scales)
    return metadata, np.maximum(raw, 0), int((raw < 0).sum())


def run_phase(prepared, cfg, start, end, phase, out):
    origins = pd.date_range(start - pd.Timedelta(days=1), end - pd.Timedelta(days=1))
    rows, logs = [], []
    for ident, spec in SPECS.items():
        for i, origin in enumerate(origins):
            if i % cfg['refit_days'] == 0:
                model, last_label, n = fit(prepared, origin, spec, cfg)
                logs.append({'phase': phase, 'model': ident, 'fit_cutoff': origin,
                             'max_label_date': last_label, 'training_pairs': n})
                print(f'{phase}: {ident}, fit {origin.date()}', flush=True)
            meta, pred, clips = predict(model, prepared, origin, spec)
            if i % cfg['refit_days'] == 0:
                logs[-1]['negative_clips_first_origin'] = clips
            for (key, h, actual), value in zip(meta, pred):
                target = origin + pd.Timedelta(days=h)
                rows.append({**dict(zip(ROUTE, key)), 'model': ident,
                    'as_of_date': origin, 'target_date': target, 'horizon_day': h,
                    'forecast_qty': float(value),
                    'actual_qty': float(actual) if target <= end else np.nan,
                    'split': phase if target <= end else 'outside_' + phase})
    predictions = pd.DataFrame(rows)
    metrics = metric_table(predictions.loc[predictions.split.eq(phase)])
    write_csv(out / f'{phase}_predictions.csv', predictions)
    write_csv(out / f'{phase}_metrics.csv', metrics)
    write_csv(out / f'{phase}_fit_log.csv', pd.DataFrame(logs))
    primary = metrics.loc[metrics.horizon_group.eq('h1_7')]
    if not primary.coverage.eq(1).all():
        raise ValueError('Incomplete phase coverage')
    return primary


def choose_inner(primary):
    if not primary.split.eq('inner_train').all():
        raise ValueError('Selection accepts the inner train slice only')
    return primary.sort_values(['mape_positive_pct', 'mae', 'model']).drop_duplicates(ROUTE)


def run_campaign(output_id, config_path='config.json'):
    cfg = read_config(config_path)
    if (cfg['train_end'] != '2025-06-30' or cfg['validation_start'] != '2025-07-01'
            or cfg['validation_end'] != '2025-09-30' or cfg['horizon'] != 14):
        raise ValueError('Campaign requires the unchanged project split and H14')
    if Path(output_id).name != output_id or output_id in ('', '.', '..'):
        raise ValueError('Output id must be a single directory name')
    out = ROOT / cfg['output_root'] / output_id
    out.mkdir(exist_ok=False)
    source = ROOT / cfg['source']
    protocol = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'registered_before_fit': True, 'models': SPECS, 'source_sha256': sha256(source),
        'entrypoint_sha256': sha256(Path(__file__)), 'config_sha256': sha256(ROOT / config_path),
        'seed': cfg['seed'], 'refit_days': cfg['refit_days'],
        'inner_tuning': 'Daily origins May-June 2025, inside train; labels never exceed fit cutoff.',
        'routes': 'Top10 by quantity to April 30 for inner fit; final train top10 must match as a guard, never retroactively change inner keys.',
        'outer_validation': 'July-September official validation; choices locked from inner train before its forecasts are scored.',
        'metric': 'Unchanged sales quantity, positive-day MAPE h1-7, h8-14 separately; zeros remain in evaluation.',
        'ratio_units': 'Origin trailing90 quantity mean clipped at1; inverse normalized-label weight matches relative error in quantity units.',
        'annual_features': 'Target calendar date one year earlier, quantity, +/-7 and +/-28 means, country/global +/-7 means; every input date <= origin.',
        'availability': 'Retrospective final-status snapshot limitation remains; no claimed operational reconstruction.',
        'test': 'Raw snapshot audited, then sales filtered before daily aggregation/features/ranking/fit/scoring; test sales never used. Existing viewed test is not independent.',
        'production': 'Unmodified; findings alone do not satisfy R05 or replace v11.',
        'packages': {'lightgbm': __import__('importlib.metadata', fromlist=['version']).version('lightgbm'),
                     'numpy': np.__version__, 'pandas': pd.__version__},
    }
    write_json(out / 'protocol.json', protocol)
    sales, _ = audit_orders(source, cfg)
    # Read the supplied snapshot for audit, but no test record enters features,
    # daily aggregation, ranking, fitting, scoring, or tuning.
    sales = sales.loc[sales.date.le(cfg['validation_end'])]
    daily = daily_sales(sales, cfg)
    daily = daily.loc[daily.date.le(cfg['validation_end'])].copy()
    early = route_top(daily, {**cfg, 'train_end': '2025-04-30'})
    top = route_top(daily, cfg)
    keys = sorted(map(tuple, early[ROUTE].to_numpy()))
    if set(keys) != set(map(tuple, top[ROUTE].to_numpy())):
        raise ValueError('Top10 membership changed; cannot claim this inner protocol covers the final top10')
    write_csv(out / 'top_routes.csv', top)
    prepared = features(daily, keys)
    # Input causality check, independent from model fit: change all route data
    # after the origin and compare every available horizon input, including
    # centered prior-year windows and scales.
    cutoff = INNER_START - pd.Timedelta(days=1)
    changed = daily.copy()
    changed.loc[changed.date.gt(cutoff), ['sales_qty', 'order_count']] = 1e6
    altered = features(changed, keys)
    for key in prepared:
        before, after = prepared[key], altered[key]
        mask = before['origins'] <= cutoff
        pd.testing.assert_frame_equal(before['x'].loc[mask], after['x'].loc[mask])
        np.testing.assert_array_equal(before['scale'][mask], after['scale'][mask])
    write_json(out / 'causal_check.json', {'all_features_through_inner_start_unchanged': True,
                                         'routes': len(keys), 'horizons': 14})
    inner = run_phase(prepared, cfg, INNER_START, INNER_END, 'inner_train', out)
    locked = choose_inner(inner)
    lock_columns = ROUTE + ['model', 'mape_positive_pct', 'mae']
    write_csv(out / 'inner_selected_models.csv', locked[lock_columns])
    lock_sha = sha256(out / 'inner_selected_models.csv')
    outer = run_phase(prepared, cfg, pd.Timestamp(cfg['validation_start']),
                      pd.Timestamp(cfg['validation_end']), 'validation', out)
    if sha256(out / 'inner_selected_models.csv') != lock_sha:
        raise ValueError('Inner selection changed after outer scoring')
    locked_result = locked[ROUTE + ['model']].merge(outer, on=ROUTE + ['model'], validate='one_to_one')
    write_csv(out / 'locked_outer_metrics.csv', locked_result)
    summary = {
        'status': 'complete', 'production_modified': False, 'test_used': False,
        'inner_selected_sha256': lock_sha, 'protocol_sha256': sha256(out / 'protocol.json'),
        'raw_unchanged': sha256(source) == protocol['source_sha256'],
        'new_candidates': len(SPECS), 'routes': len(top),
        'locked_outer_passed': int(locked_result.mape_positive_pct.le(20).sum()),
        'locked_outer_mean_mape': float(locked_result.mape_positive_pct.mean()),
        'locked_outer_min_mape': float(locked_result.mape_positive_pct.min()),
        'locked_outer_max_mape': float(locked_result.mape_positive_pct.max()),
        'best_outer_any_candidate_passed': int(outer.groupby(ROUTE).mape_positive_pct.min().le(20).sum()),
        'all_inner_primary_full_coverage': bool(inner.coverage.eq(1).all()),
        'all_outer_primary_full_coverage': bool(outer.coverage.eq(1).all()),
        'limitations': 'Repeated validation experimentation is not independent acceptance; 20% on test remains unproven.',
    }
    summary['files'] = {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()}
    write_json(out / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-id', required=True)
    parser.add_argument('--config', default='config.json')
    args = parser.parse_args()
    run_campaign(args.output_id, args.config)
