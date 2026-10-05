"""Direct seven-day quantity forecasting, isolated from sealed daily runs.

Select on July-September validation before scoring the previously viewed test.
Weekly error is a distinct metric and cannot certify daily R05.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json
from src.data import audit_orders, daily_sales, route_top
from weekly_macro import MACRO_FEATURES, MACRO_AMOUNTS, prepare_macro, macro_inputs
from weekly_calibration import fit_factors

FEATURES = ['route_index', 'block', 'origin_weekday', 'start_month', 'year_sin',
            'year_cos', 'elapsed_days', 'sum7', 'sum14', 'sum28', 'sum90',
            'previous7', 'std28', 'positive_share28', 'orders28', 'basket28']
AMOUNTS = ['sum7', 'sum14', 'sum28', 'sum90', 'previous7', 'std28']
CATEGORIES = ['route_index', 'block', 'origin_weekday', 'start_month']
ANNUAL_FEATURES = ['prior_year_week7', 'prior_year_mean28_week', 'prior_year_mean90_week']


def checked_series(daily):
    """No missing days may silently become zero or partial weekly labels."""
    result = {}
    for key, group in daily.groupby(ROUTE, sort=True):
        group = group.sort_values('date').set_index('date')
        expected = pd.date_range(group.index.min(), group.index.max())
        if not group.index.equals(expected) or not group.index.is_unique:
            raise ValueError('Incomplete or duplicate daily history')
        values = group[['sales_qty', 'order_count']].to_numpy(float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError('Missing or negative observed history')
        result[key] = group
    return result


def prepare(daily, settings):
    result = {}
    macro = prepare_macro(daily) if any(spec.get('macro_features') for spec in settings['models'].values()) else None
    for route_index, (key, group) in enumerate(checked_series(daily).items()):
        y, orders = group.sales_qty.astype(float), group.order_count.astype(float)
        origins = y.index[settings['minimum_history_days'] - 1:]
        sums = {w: y.rolling(w, min_periods=w).sum() for w in (7, 14, 28, 90)}
        for block in settings['blocks']:
            starts = origins + pd.Timedelta(days=1 + 7 * (block - 1))
            ends = starts + pd.Timedelta(days=6)
            angle = 2 * np.pi * starts.dayofyear.to_numpy() / 365.25
            x = pd.DataFrame({'route_index': route_index, 'block': block,
                'origin_weekday': origins.dayofweek, 'start_month': starts.month,
                'year_sin': np.sin(angle), 'year_cos': np.cos(angle),
                'elapsed_days': (origins - pd.Timestamp('2024-01-01')).days,
                **{f'sum{w}': values.reindex(origins).to_numpy() for w, values in sums.items()},
                'previous7': sums[7].shift(7).reindex(origins).to_numpy(),
                'std28': y.rolling(28).std().reindex(origins).to_numpy(),
                'positive_share28': y.gt(0).rolling(28).mean().reindex(origins).to_numpy(),
                'orders28': orders.rolling(28).sum().reindex(origins).to_numpy(),
                'basket28': (sums[28] / orders.rolling(28).sum().clip(lower=1)).reindex(origins).to_numpy()})
            prior = ends - pd.DateOffset(years=1)
            if (prior + pd.Timedelta(days=45) > origins).any():
                raise ValueError('Prior-year feature window exceeds origin')
            x[ANNUAL_FEATURES[0]] = sums[7].reindex(prior).to_numpy()
            x[ANNUAL_FEATURES[1]] = (y.rolling(28, center=True, min_periods=28).mean() * 7).reindex(prior).to_numpy()
            x[ANNUAL_FEATURES[2]] = (y.rolling(90, center=True, min_periods=90).mean() * 7).reindex(prior).to_numpy()
            if macro is not None:
                extra = macro_inputs(macro, key[0], y, origins, ends)
                x[MACRO_FEATURES] = extra.to_numpy()
            names = FEATURES + ANNUAL_FEATURES + (MACRO_FEATURES if macro is not None else [])
            result[(key, block)] = {'x': x[names], 'origins': origins,
                'starts': starts, 'ends': ends,
                'y': sums[7].reindex(ends).to_numpy(float),
                'scale': np.maximum(sums[90].reindex(origins).to_numpy() * 7 / 90, 1.)}
    return result


def inputs(table, spec, indices):
    names = FEATURES + (ANNUAL_FEATURES if spec.get('annual_features', False) else [])
    if spec.get('macro_features', False):
        names += MACRO_FEATURES
    x = table['x'].iloc[indices][names].copy()
    if spec.get('units') == 'ratio':
        amount_names = AMOUNTS + (ANNUAL_FEATURES if spec.get('annual_features', False) else [])
        if spec.get('macro_features', False):
            amount_names += MACRO_AMOUNTS
        x[amount_names] = x[amount_names].div(table['scale'][indices], axis=0)
    return x


def fit(prepared, cutoff, spec, cfg, settings):
    xs, ys, scales, label_ends = [], [], [], []
    for table in prepared.values():
        mask = ((table['ends'] <= cutoff)
                & (table['ends'] >= cutoff - pd.Timedelta(days=settings['training_window_days'] - 1)))
        idx = np.flatnonzero(mask)
        if len(idx):
            xs.append(inputs(table, spec, idx)); ys.append(table['y'][idx])
            scales.append(table['scale'][idx]); label_ends.append(table['ends'][idx].max())
    if not xs:
        raise ValueError('No fully observed weekly training labels')
    x, y = pd.concat(xs, ignore_index=True), np.concatenate(ys)
    if not np.isfinite(y).all() or (y < 0).any() or max(label_ends) > cutoff:
        raise ValueError('Invalid weekly training labels')
    if spec['units'] == 'ratio':
        y = y / np.concatenate(scales)
    if spec['objective'] == 'regression_l1':
        weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
    else:
        weights = np.ones_like(y)
    if not np.any(y > 0):
        from sklearn.dummy import DummyRegressor
        model = DummyRegressor(strategy='constant', constant=0.).fit(x, y)
    else:
        model = LGBMRegressor(objective=spec['objective'], num_leaves=spec['leaves'],
            n_estimators=settings['n_estimators'], learning_rate=settings['learning_rate'],
            min_child_samples=settings['min_child_samples'], reg_lambda=settings['reg_lambda'],
            n_jobs=cfg['lightgbm_threads'], random_state=cfg['seed'], deterministic=True,
            force_col_wise=True, verbosity=-1)
        model.fit(x, y, sample_weight=weights, categorical_feature=CATEGORIES)
    return model, {'max_label_end': max(label_ends), 'training_pairs': len(y)}


def baseline_total(group, origin, spec):
    y = group.loc[:origin].sales_qty.astype(float)
    if spec['kind'] == 'mean':
        if len(y) < spec['window']:
            raise ValueError('Insufficient baseline history')
        return float(y.iloc[-spec['window']:].mean() * 7)
    totals = y.rolling(7, min_periods=7).sum().iloc[-spec['window']:].dropna().to_numpy()
    positive = np.sort(totals[totals > 0])
    if not len(positive):
        return 0.
    weights = 1 / positive
    return float(positive[np.searchsorted(np.cumsum(weights), weights.sum() / 2)])


def predict_one(model, table, origin, spec):
    idx = np.flatnonzero(table['origins'] == origin)
    if len(idx) != 1:
        raise ValueError('Missing or duplicate forecast origin')
    value = float(model.predict(inputs(table, spec, idx))[0])
    if spec['units'] == 'ratio':
        value *= table['scale'][idx[0]]
    if not np.isfinite(value):
        raise ValueError('Nonfinite forecast')
    return max(0., value)


def predict_batch(model, prepared, origin, spec):
    keys, xs, scales = [], [], []
    for key, table in prepared.items():
        indices = np.flatnonzero(table['origins'] == origin)
        if len(indices) != 1:
            raise ValueError('Missing or duplicate forecast origin')
        keys.append(key); xs.append(inputs(table, spec, indices))
        scales.append(table['scale'][indices[0]])
    values = np.asarray(model.predict(pd.concat(xs, ignore_index=True)), dtype=float)
    if spec['units'] == 'ratio':
        values *= np.asarray(scales)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite batch forecast')
    return dict(zip(keys, np.maximum(values, 0)))


def blend_values(component_values, weights):
    weights = np.asarray(weights, dtype=float)
    if (len(weights) != len(component_values) or not np.isfinite(weights).all()
            or (weights < 0).any() or not np.isclose(weights.sum(), 1., atol=1e-12, rtol=0)):
        raise ValueError('Blend requires nonnegative weights summing to one')
    keys = set(component_values[0])
    if any(set(values) != keys for values in component_values):
        raise ValueError('Blend components have incomplete coverage')
    return {key: float(sum(weight * values[key] for weight, values in zip(weights, component_values)))
            for key in component_values[0]}


def phase(daily, cfg, settings, start, end, name, out, choices=None):
    prepared, groups = prepare(daily, settings), checked_series(daily)
    origins = pd.date_range(pd.Timestamp(start) - pd.Timedelta(days=1), pd.Timestamp(end) - pd.Timedelta(days=1))
    rows, logs, head_logs, fit_cache, predict_cache = [], [], [], {}, {}
    identifiers = sorted(set(choices.values())) if choices else list(settings['models'])
    for ident in identifiers:
        spec = settings['models'][ident]
        state = None
        for i, origin in enumerate(origins):
            components = (spec['components'] if spec['kind'] == 'blend'
                          else [spec['parent']] if spec['kind'] == 'calibrated' else [ident])
            if spec['kind'] in ('lgbm', 'blend', 'calibrated'):
                if i % settings['refit_days'] == 0:
                    state = []
                    for component in components:
                        component_spec = settings['models'][component]
                        if component_spec['kind'] != 'lgbm':
                            raise ValueError('Weekly blend components must be direct LightGBM models')
                        cache_key = (component, origin)
                        if cache_key not in fit_cache:
                            fit_cache[cache_key] = fit(prepared, origin, component_spec, cfg, settings)
                        model, log = fit_cache[cache_key]
                        state.append((model, component_spec))
                        logs.append({'model': ident, 'component': component, 'fit_cutoff': origin, **log})
                    if spec['kind'] == 'calibrated':
                        factors, head_log = fit_factors(prepared, origin, spec, cfg, settings,
                            fit_cache, predict_cache, fit, predict_batch)
                        head_logs.extend([{'model': ident, **row} for row in head_log])
                values = []
                for component, (model, component_spec) in zip(components, state):
                    prediction_key = (component, origin)
                    if prediction_key not in predict_cache:
                        predict_cache[prediction_key] = predict_batch(model, prepared, origin, component_spec)
                    values.append(predict_cache[prediction_key])
                predicted = blend_values(values, spec['weights']) if spec['kind'] == 'blend' else values[0]
                base_prediction = predicted.copy()
                if spec['kind'] == 'calibrated':
                    predicted = {key: value * factors[key] for key, value in predicted.items()}
            for (key, block), table in prepared.items():
                if choices and choices[key] != ident:
                    continue
                start_date = origin + pd.Timedelta(days=1 + 7 * (block - 1))
                end_date = start_date + pd.Timedelta(days=6)
                if end_date > pd.Timestamp(end):
                    continue  # Only complete seven-day windows belong to this split.
                idx = np.flatnonzero(table['origins'] == origin)[0]
                actual = table['y'][idx]
                if not np.isfinite(actual):
                    raise ValueError('Missing complete-week actual')
                value = (predicted[(key, block)] if spec['kind'] in ('lgbm', 'blend', 'calibrated')
                         else baseline_total(groups[key], origin, spec))
                rows.append({**dict(zip(ROUTE, key)), 'model': ident, 'as_of_date': origin,
                    'window_start': start_date, 'window_end': end_date, 'week_block': block,
                    'forecast_qty_7d': value, 'actual_qty_7d': actual, 'split': name,
                    'weekly_cadence': i % 7 == 0,
                    'base_forecast_qty_7d': base_prediction[(key, block)] if spec['kind'] == 'calibrated' else value,
                    'calibration_factor': factors[(key, block)] if spec['kind'] == 'calibrated' else 1.})
        print(f'{name}: completed {ident}', flush=True)
    frame = pd.DataFrame(rows)
    write_csv(out / f'{name}_weekly_predictions.csv', frame)
    write_csv(out / f'{name}_fit_log.csv', pd.DataFrame(logs))
    write_csv(out / f'{name}_head_log.csv', pd.DataFrame(head_logs))
    write_csv(out / f'{name}_weekly_metrics.csv', metrics(frame, start, end))
    return frame


def metrics(frame, start, end):
    rows = []
    for cadence in ('daily_origins', 'seven_day_origins'):
        subset = frame if cadence == 'daily_origins' else frame.loc[frame.weekly_cadence.eq(True)]
        for keys, g in subset.groupby(ROUTE + ['model', 'week_block'], sort=True):
            country, carrier, model, block = keys
            actual, pred = g.actual_qty_7d.to_numpy(float), g.forecast_qty_7d.to_numpy(float)
            if g.duplicated(['as_of_date']).any() or not np.isfinite(actual).all() or not np.isfinite(pred).all():
                raise ValueError('Incomplete or duplicate metric pairs')
            positive = actual > 0
            expected = max(0, (pd.Timestamp(end) - pd.Timestamp(start)).days + 1 - (7 * block - 1))
            if cadence == 'seven_day_origins':
                expected = (expected + 6) // 7
            error = pred - actual
            rows.append({'destination_country': country, 'carrier': carrier, 'model': model,
                'week_block': block, 'cadence': cadence, 'pairs': len(g), 'expected_pairs': expected,
                'coverage': len(g) / expected if expected else np.nan,
                'positive_windows': int(positive.sum()), 'zero_windows': int((~positive).sum()),
                'mape_positive_week_pct': float(np.mean(np.abs(error[positive]) / actual[positive]) * 100) if positive.any() else np.nan,
                'mae_week_qty': float(np.mean(np.abs(error))),
                'wape_pct': float(np.abs(error).sum() / actual.sum() * 100) if actual.sum() else np.nan,
                'bias_pct': float(error.sum() / actual.sum() * 100) if actual.sum() else np.nan})
    return pd.DataFrame(rows)


def allocate_daily(total, group, origin, block, history_days=90):
    """Causal weekday profile; these are allocations, not seven daily models."""
    history = group.loc[:origin].iloc[-history_days:].sales_qty
    means = history.groupby(history.index.dayofweek).mean().reindex(range(7), fill_value=0.).to_numpy()
    dates = pd.date_range(origin + pd.Timedelta(days=1 + 7 * (block - 1)), periods=7)
    weights = means[dates.dayofweek]
    weights = weights / weights.sum() if weights.sum() > 0 else np.full(7, 1 / 7)
    allocated = total * weights
    allocated[-1] += total - allocated.sum()
    return dates, allocated


def run_weekly(run_id, weekly_config='config.weekly.json'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run id')
    settings_path = (ROOT / weekly_config).resolve()
    if not settings_path.is_relative_to(ROOT):
        raise ValueError('Configuration must be local')
    settings = json.loads(settings_path.read_text(encoding='utf-8'))
    if settings['blocks'] != [1, 2] or settings['daily_acceptance_replaced']:
        raise ValueError('Weekly protocol must retain daily acceptance and two weekly blocks')
    cfg = read_config(settings['base_config'])
    out = (ROOT / cfg['output_root'] / run_id).resolve()
    source = (ROOT / cfg['source']).resolve()
    if not out.is_relative_to(ROOT) or not source.is_relative_to(ROOT):
        raise ValueError('Run/source must be local')
    out.mkdir(exist_ok=False)
    protocol = {'status': 'registered_before_fit', 'weekly_config': settings, 'base_config': cfg,
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sha256(source),
        'entrypoint_sha256': sha256(Path(__file__)), 'config_sha256': sha256(settings_path),
        'feature_module_sha256': {'weekly_macro.py': sha256(ROOT / 'weekly_macro.py')},
        'calibration_module_sha256': sha256(ROOT / 'weekly_calibration.py'),
        'target': 'Seven-day sum of unchanged UTC success quantity, never average or order count',
        'selection': 'Per-route validation daily-origin h1-7 weekly MAPE, then MAE, then lexical id; full coverage required',
        'test_limit': 'Existing test already viewed during daily experiments; this is retrospective evaluation, not independent acceptance',
        'metric_limit': 'Weekly MAPE does not prove the daily R05 requirement; no target/split/top10/threshold replaced',
        'origins': 'Daily rolling complete windows plus fixed seven-day cadence anchored to each split start minus one day',
        'availability': 'Final-status snapshot is retrospective; actual source availability at operational origins is unknown',
        'production_daily_modified': False}
    write_json(out / 'protocol.json', protocol)
    sales, audit = audit_orders(source, cfg)
    val_sales = sales.loc[sales.date.le(cfg['validation_end'])]
    val_daily = daily_sales(val_sales, cfg).loc[lambda f: f.date.le(cfg['validation_end'])].copy()
    top = route_top(val_daily, cfg)
    write_csv(out / 'top_routes.csv', top)
    val = phase(val_daily, cfg, settings, cfg['validation_start'], cfg['validation_end'], 'validation', out)
    vm = metrics(val, cfg['validation_start'], cfg['validation_end'])
    eligible = vm.loc[vm.week_block.eq(1) & vm.cadence.eq('daily_origins') & vm.coverage.eq(1) & vm.mape_positive_week_pct.notna()]
    selected = eligible.sort_values(['mape_positive_week_pct', 'mae_week_qty', 'model']).drop_duplicates(ROUTE)
    if len(selected) != len(checked_series(val_daily)):
        raise ValueError('Not every route has a fully covered selectable model')
    selected = selected[ROUTE + ['model', 'mape_positive_week_pct', 'mae_week_qty']].copy()
    selected['selection_cutoff'] = cfg['validation_end']
    selected['is_top10'] = list(map(lambda k: k in set(map(tuple, top[ROUTE].to_numpy())), selected[ROUTE].itertuples(index=False, name=None)))
    write_csv(out / 'selected_weekly_models.csv', selected)
    lock_hash = sha256(out / 'selected_weekly_models.csv')
    choices = dict(zip(map(tuple, selected[ROUTE].to_numpy()), selected.model))
    # Test aggregation and labels are first prepared after the validation lock.
    daily = daily_sales(sales, cfg)
    test = phase(daily, cfg, settings, cfg['test_start'], cfg['test_end'], 'test', out, choices)
    if sha256(out / 'selected_weekly_models.csv') != lock_hash:
        raise ValueError('Selection changed after test')
    prepared, groups = prepare(daily, settings), checked_series(daily)
    origin = pd.Timestamp(cfg['forecast_origin'])
    future, allocation, fits = [], [], {}
    future_fit_cache, future_predict_cache, future_head_cache, future_head_logs = {}, {}, {}, []
    for key, ident in choices.items():
        spec = settings['models'][ident]
        components = (spec['components'] if spec['kind'] == 'blend'
                      else [spec['parent']] if spec['kind'] == 'calibrated' else [ident])
        if spec['kind'] in ('lgbm', 'blend', 'calibrated'):
            for component in components:
                if component not in fits:
                    component_spec = settings['models'][component]
                    if component_spec['kind'] != 'lgbm':
                        raise ValueError('Weekly blend components must be direct LightGBM models')
                    fits[component] = fit(prepared, origin, component_spec, cfg, settings)[0]
            if spec['kind'] == 'calibrated' and ident not in future_head_cache:
                future_head_cache[ident], head_log = fit_factors(prepared, origin, spec, cfg, settings,
                    future_fit_cache, future_predict_cache, fit, predict_batch)
                future_head_logs.extend([{'model': ident, **row} for row in head_log])
        for block in settings['blocks']:
            if spec['kind'] in ('lgbm', 'blend', 'calibrated'):
                values = [{(key, block): predict_one(fits[component], prepared[(key, block)], origin, settings['models'][component])}
                          for component in components]
                value = blend_values(values, spec['weights'])[(key, block)] if spec['kind'] == 'blend' else values[0][(key, block)]
                if spec['kind'] == 'calibrated':
                    value *= future_head_cache[ident][(key, block)]
            else:
                value = baseline_total(groups[key], origin, spec)
            dates, allocated = allocate_daily(value, groups[key], origin, block, settings['allocation_history_days'])
            future.append({**dict(zip(ROUTE, key)), 'model': ident, 'as_of_date': origin,
                'window_start': dates[0], 'window_end': dates[-1], 'week_block': block,
                'forecast_qty_7d': value, 'actual_qty_7d': np.nan})
            for h, (date, qty) in enumerate(zip(dates, allocated), 1 + 7 * (block - 1)):
                allocation.append({**dict(zip(ROUTE, key)), 'model': ident, 'as_of_date': origin,
                    'target_date': date, 'horizon_day': h, 'week_block': block, 'forecast_qty': qty,
                    'is_daily_allocation': True, 'actual_qty': np.nan})
    write_csv(out / 'weekly_forecast.csv', pd.DataFrame(future))
    write_csv(out / 'daily_allocation.csv', pd.DataFrame(allocation))
    write_csv(out / 'daily_sales.csv', daily)
    write_csv(out / 'future_head_log.csv', pd.DataFrame(future_head_logs))
    tm = metrics(test, cfg['test_start'], cfg['test_end'])
    result = selected[ROUTE + ['model', 'is_top10']].merge(tm, on=ROUTE + ['model'], validate='one_to_many')
    write_csv(out / 'selected_test_weekly_metrics.csv', result)
    primary = result.loc[result.is_top10 & result.week_block.eq(1) & result.cadence.eq('daily_origins')]
    summary = {'status': 'complete', 'kind': 'weekly_quantity_run', 'weekly_version': settings['weekly_version'],
        'run_id': run_id, 'selection_sha256': lock_hash, 'source_sha256': protocol['source_sha256'],
        'raw_unchanged': sha256(source) == protocol['source_sha256'],
        'top10_test_weekly_passed': int(primary.mape_positive_week_pct.le(20).sum()),
        'top10_test_weekly_min_mape': float(primary.mape_positive_week_pct.min()),
        'top10_test_weekly_max_mape': float(primary.mape_positive_week_pct.max()),
        'top10_test_weekly_mean_mape': float(primary.mape_positive_week_pct.mean()),
        'test_weekly_full_coverage': bool(result.coverage.eq(1).all()),
        'daily_R05_met': False, 'test_is_independent': False, 'production_daily_modified': False,
        'routes': len(choices), 'forecast_windows': len(future), 'daily_allocation_rows': len(allocation),
        'source_audit_rows': audit['rows_raw'],
        'files': {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()}}
    if (sha256(Path(__file__)) != protocol['entrypoint_sha256']
            or sha256(settings_path) != protocol['config_sha256']
            or sha256(ROOT / 'weekly_macro.py') != protocol['feature_module_sha256']['weekly_macro.py']
            or sha256(ROOT / 'weekly_calibration.py') != protocol['calibration_module_sha256']
            or not summary['raw_unchanged']):
        raise ValueError('Input, configuration or model code changed during weekly run')
    write_json(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'files'}, ensure_ascii=False), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--config', default='config.weekly.json')
    args = parser.parse_args()
    run_weekly(args.run_id, args.config)
