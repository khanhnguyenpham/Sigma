"""Direct quantity totals over registered consecutive-day windows.

The label at origin D is sum(y[D+1:D+window]); rolling totals in the
training data END at their timestamp. No day-of-month or partial-window
substitution. Legacy H14/weekly runs are never modified.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
import logging
import platform
from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json
from src.data import audit_orders, daily_sales, route_top
from src.evaluation import score
from sigma.forecasting.weekly import checked_series

BASE_FEATURES = ['route_index', 'origin_weekday', 'end_month', 'year_sin', 'year_cos',
    'elapsed_days', 'sum7', 'sum14', 'sum28', 'sum56', 'sum90', 'previous14',
    'std28', 'positive_share28', 'orders28', 'basket28']
ANNUAL = ['prior_year_total', 'prior_year_mean28', 'prior_year_mean90']
AMOUNTS = ['sum7', 'sum14', 'sum28', 'sum56', 'sum90', 'previous14', 'std28']
KEY = ['window_days'] + ROUTE + ['as_of_date']


def load_settings(path='data/configs/aggregate.json'):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    settings = json.loads(path.read_text(encoding='utf-8'))
    if not settings['windows'] or any(type(h) is not int or h < 1 or h > 90 for h in settings['windows']):
        raise ValueError('Invalid consecutive-day windows')
    if len(set(settings['windows'])) != len(settings['windows']):
        raise ValueError('Duplicate window')
    for field in ['minimum_history_days', 'training_window_days', 'refit_days', 'workers']:
        if type(settings[field]) is not int or settings[field] < 1:
            raise ValueError('Invalid aggregate settings')
    if settings['minimum_history_days'] < 90 or settings['workers'] > 3:
        raise ValueError('Insufficient history or worker budget')
    if not set(settings['non_top10_models']).issubset(settings['models']):
        raise ValueError('Unknown baseline')
    return path, settings


def prepare(daily, window, settings):
    result = {}
    for route_index, (key, group) in enumerate(checked_series(daily).items()):
        y = group.sales_qty.astype(float)
        origins = y.index[settings['minimum_history_days'] - 1:]
        ends = origins + pd.Timedelta(days=window)
        sums = {w: y.rolling(w, min_periods=w).sum() for w in [7, 14, 28, 56, 90, window]}
        angle = 2 * np.pi * ends.dayofyear.to_numpy() / 365.25
        x = pd.DataFrame({'route_index': route_index, 'origin_weekday': origins.dayofweek,
            'end_month': ends.month, 'year_sin': np.sin(angle), 'year_cos': np.cos(angle),
            'elapsed_days': (origins - pd.Timestamp('2024-01-01')).days,
            **{f'sum{w}': sums[w].reindex(origins).to_numpy() for w in [7, 14, 28, 56, 90]},
            'previous14': sums[14].shift(14).reindex(origins).to_numpy(),
            'std28': y.rolling(28).std(ddof=0).reindex(origins).to_numpy(),
            'positive_share28': y.gt(0).rolling(28).mean().reindex(origins).to_numpy(),
            'orders28': group.order_count.rolling(28).sum().reindex(origins).to_numpy(),
            'basket28': (sums[28] / group.order_count.rolling(28).sum().clip(lower=1)).reindex(origins).to_numpy()})
        prior = ends - pd.DateOffset(years=1)
        if (prior + pd.Timedelta(days=45) > origins).any():
            raise ValueError('Annual feature reaches beyond origin')
        x[ANNUAL[0]] = sums[window].reindex(prior).to_numpy()
        x[ANNUAL[1]] = (y.rolling(28, center=True).mean() * window).reindex(prior).to_numpy()
        x[ANNUAL[2]] = (y.rolling(90, center=True).mean() * window).reindex(prior).to_numpy()
        result[key] = {'x': x[BASE_FEATURES + ANNUAL], 'origins': origins, 'ends': ends,
            'y': sums[window].reindex(ends).to_numpy(),
            'scale': (y.rolling(90).mean() * window).clip(lower=1).reindex(origins).to_numpy()}
    return result


def inputs(table, indices, spec):
    names = BASE_FEATURES + (ANNUAL if spec.get('annual') else [])
    x = table['x'].iloc[indices][names].copy()
    if spec['units'] == 'ratio':
        x[AMOUNTS + (ANNUAL if spec.get('annual') else [])] = x[
            AMOUNTS + (ANNUAL if spec.get('annual') else [])].div(table['scale'][indices], axis=0)
    return x


def fit_lgbm(prepared, cutoff, spec, cfg, settings):
    xs, ys, scales, ends = [], [], [], []
    for table in prepared.values():
        ix = np.flatnonzero((table['ends'] <= cutoff) &
            (table['ends'] >= cutoff - pd.Timedelta(days=settings['training_window_days'] - 1)))
        if len(ix):
            xs.append(inputs(table, ix, spec)); ys.append(table['y'][ix]); scales.append(table['scale'][ix])
            ends.append(table['ends'][ix].max())
    if not xs:
        raise ValueError('No complete training labels')
    x, y = pd.concat(xs, ignore_index=True), np.concatenate(ys)
    if not np.isfinite(y).all() or (y < 0).any() or max(ends) > cutoff:
        raise ValueError('Invalid or future training labels')
    if spec['units'] == 'ratio':
        y = y / np.concatenate(scales)
    weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0) if spec['objective'] == 'regression_l1' else np.ones_like(y)
    if not np.any(y > 0):
        from sklearn.dummy import DummyRegressor
        model = DummyRegressor(strategy='constant', constant=0.).fit(x, y)
    else:
        options = settings['lightgbm']
        model = LGBMRegressor(objective=spec['objective'], num_leaves=spec['leaves'],
            n_estimators=options['trees'], learning_rate=options['learning_rate'],
            min_child_samples=options['min_child_samples'], reg_lambda=options['reg_lambda'],
            n_jobs=options['threads'], random_state=cfg['seed'], deterministic=True,
            force_col_wise=True, verbosity=-1)
        model.fit(x, y, sample_weight=weights, categorical_feature=['route_index', 'origin_weekday', 'end_month'])
    return model, {'fit_cutoff': cutoff, 'max_label_end': max(ends), 'training_pairs': len(y)}


def predict_lgbm(model, prepared, origin, spec):
    xs, scales, keys = [], [], []
    for key, table in prepared.items():
        ix = np.flatnonzero(table['origins'] == origin)
        if len(ix) != 1:
            raise ValueError('Unavailable forecast origin')
        xs.append(inputs(table, ix, spec)); scales.append(table['scale'][ix[0]]); keys.append(key)
    values = model.predict(pd.concat(xs, ignore_index=True))
    if spec['units'] == 'ratio':
        values = values * np.array(scales)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite model forecast')
    return dict(zip(keys, np.maximum(values, 0)))


def baseline(group, origin, window, spec):
    y = group.loc[:origin].sales_qty.astype(float)
    if spec['kind'] == 'mean':
        return float(y.tail(spec['history_days']).mean() * window)
    totals = y.rolling(window, min_periods=window).sum().tail(spec['history_days']).dropna().to_numpy()
    positive = np.sort(totals[totals > 0])
    if not len(positive):
        return 0.
    weights = 1. / positive
    return float(positive[np.searchsorted(weights.cumsum(), weights.sum() / 2)])


def origins_for(cfg, split):
    if split == 'future':
        return pd.DatetimeIndex([pd.Timestamp(cfg['forecast_origin'])])
    return pd.date_range(pd.Timestamp(cfg[f'{split}_start']) - pd.Timedelta(days=1),
                         pd.Timestamp(cfg[f'{split}_end']) - pd.Timedelta(days=1))


def row(group, route, model, split, origin, window, value, phase_end, fit_cutoff=None):
    dates = pd.date_range(origin + pd.Timedelta(days=1), periods=window)
    actual = group.sales_qty.reindex(dates)
    # Never expose an actual from the next split in an incomplete label.
    complete = dates[-1] <= phase_end and actual.notna().all() and split != 'future'
    return {**dict(zip(ROUTE, route)), 'window_days': window, 'model': model, 'split': split,
        'as_of_date': origin, 'window_start': dates[0], 'target_date': dates[-1],
        'forecast_qty': value, 'actual_qty': float(actual.sum()) if complete else np.nan,
        'fit_cutoff': fit_cutoff}


def model_job(daily, top_routes, cfg, settings, window, name, split, wanted_routes):
    """Canonical importable worker, bounded to one candidate/window/phase."""
    from threadpoolctl import threadpool_limits
    spec = settings['models'][name]
    groups = checked_series(daily)
    wanted_routes = {tuple(k) for k in wanted_routes}
    origins = origins_for(cfg, split)
    phase_end = pd.Timestamp(cfg['forecast_origin'] if split == 'future' else cfg[f'{split}_end'])
    records, logs = [], []
    with threadpool_limits(limits=1):
        if spec['kind'] == 'lgbm':
            top_daily = daily.merge(pd.DataFrame(top_routes, columns=ROUTE), on=ROUTE, validate='many_to_one')
            prepared = prepare(top_daily, window, settings)
            for i, origin in enumerate(origins):
                if i % settings['refit_days'] == 0:
                    model, info = fit_lgbm(prepared, origin, spec, cfg, settings)
                    logs.append({'model': name, 'window_days': window, 'split': split, 'status': 'ok', **info})
                    cutoff = origin
                predicted = predict_lgbm(model, prepared, origin, spec)
                for key in sorted(wanted_routes):
                    records.append(row(groups[key], key, name, split, origin, window, predicted[key], phase_end, cutoff))
        elif spec['kind'] in ('mean', 'weighted_median'):
            for origin in origins:
                for key in sorted(wanted_routes):
                    records.append(row(groups[key], key, name, split, origin, window,
                        baseline(groups[key], origin, window, spec), phase_end, origin))
        else:
            # Isolate a failed route/candidate while preserving all expected rows.
            for key in sorted(wanted_routes):
                y = groups[key].sales_qty.astype(float)
                state, failed, last_origin, cutoff = None, False, None, None
                for i, origin in enumerate(origins):
                    value = np.nan
                    history = y.loc[:origin].rolling(window, min_periods=window).sum().dropna().tail(settings['training_window_days'])
                    try:
                        if failed:
                            raise StopIteration
                        if i % settings['refit_days'] == 0:
                            cutoff = origin
                            if spec['kind'] == 'prophet':
                                from M2.models.Prophet.model import fit
                                options = {k: v for k, v in spec.items() if k != 'kind'}
                                state, _, _ = fit(history, options, cfg, settings)
                            else:
                                from statsmodels.tsa.statespace.sarimax import SARIMAX
                                with warnings.catch_warnings():
                                    warnings.simplefilter('ignore')
                                    state = SARIMAX(np.log1p(history), order=tuple(spec['order']),
                                        seasonal_order=tuple(spec['seasonal_order']), trend='c').fit(disp=False, maxiter=spec['maxiter'])
                                if not state.mle_retvals.get('converged', False):
                                    raise ValueError('SARIMA did not converge')
                            logs.append({**dict(zip(ROUTE, key)), 'model': name, 'window_days': window,
                                'split': split, 'fit_cutoff': cutoff, 'max_label_end': history.index.max(),
                                'training_pairs': len(history), 'status': 'ok'})
                        elif spec['kind'] == 'sarima':
                            update = history.loc[history.index > last_origin]
                            state = state.append(np.log1p(update), refit=False)
                        if spec['kind'] == 'prophet':
                            value = float(state.predict(pd.DataFrame({'ds': [origin + pd.Timedelta(days=window)]})).yhat.iloc[0])
                        else:
                            value = float(np.expm1(np.asarray(state.forecast(window))[-1]))
                        if not np.isfinite(value):
                            raise ValueError('Nonfinite time series forecast')
                        value = max(value, 0.)
                    except StopIteration:
                        pass
                    except (ValueError, RuntimeError, OSError, np.linalg.LinAlgError, OverflowError) as error:
                        failed = True
                        logs.append({**dict(zip(ROUTE, key)), 'model': name, 'window_days': window,
                            'split': split, 'fit_cutoff': origin, 'status': 'failed', 'error_type': type(error).__name__})
                    last_origin = origin
                    records.append(row(groups[key], key, name, split, origin, window, value, phase_end, cutoff))
    return pd.DataFrame(records), pd.DataFrame(logs)


def phase(daily, top, cfg, settings, window, split, choices=None, output=None):
    all_routes = sorted(map(tuple, daily[ROUTE].drop_duplicates().to_numpy()))
    top_routes = sorted(map(tuple, top[ROUTE].to_numpy()))
    jobs = {}
    for name in settings['models']:
        routes = [k for k in all_routes if (choices is None and (k in top_routes or name in settings['non_top10_models']))
                  or (choices is not None and choices.get(k) == name)]
        if routes:
            jobs[name] = routes
    frames, logs = [], []
    from sigma.forecasting.aggregate import model_job as worker
    with ProcessPoolExecutor(max_workers=settings['workers']) as pool:
        futures = {pool.submit(worker, daily, top_routes, cfg, settings, window, name, split, routes): name
                   for name, routes in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            frame, log = future.result()
            if output is not None:
                write_csv(output / 'checkpoints' / f'{split}_{window}d_{name}.csv', frame)
            frames.append(frame); logs.append(log)
            failures = int(log.status.eq('failed').sum()) if len(log) else 0
            print(f'{window}d {split}: {name} finished; failed route candidates={failures}', flush=True)
    return pd.concat(frames, ignore_index=True), pd.concat(logs, ignore_index=True)


def metric_table(predictions, cfg):
    rows = []
    keys = ['window_days', 'split', 'model'] + ROUTE
    for key, part in predictions.groupby(keys, sort=True):
        window, split = int(key[0]), key[1]
        end = pd.Timestamp(cfg[f'{split}_end'])
        eligible = part.loc[part.target_date.le(end)]
        anchor = pd.Timestamp(cfg[f'{split}_start']) - pd.Timedelta(days=1)
        expected = max(0, (end - anchor).days - window + 1)
        for cadence in ['daily_origins', f'nonoverlapping_{window}d']:
            view = eligible if cadence == 'daily_origins' else eligible.loc[(eligible.as_of_date-anchor).dt.days.mod(window).eq(0)]
            count = expected if cadence == 'daily_origins' else (expected-1)//window+1 if expected else 0
            metrics = score(view, expected_pairs=count)
            rows.append({**dict(zip(keys, key)), 'cadence': cadence, **metrics,
                'passes_20_pct': bool(metrics['coverage'] == 1 and metrics['mape_positive_pct'] <= cfg['mape_limit_pct'])})
    return pd.DataFrame(rows)


def select(validation, cfg):
    if set(validation.split) != {'validation'}:
        raise ValueError('Only validation may select models')
    table = metric_table(validation, cfg)
    complete = validation.groupby(['window_days'] + ROUTE + ['model']).forecast_qty.agg(lambda x: bool(np.isfinite(x).all()))
    table = table.loc[table.cadence.eq('daily_origins') & table.coverage.eq(1) & table.mape_positive_pct.notna()]
    rows = []
    for key, part in table.groupby(['window_days'] + ROUTE, sort=True):
        part = part.loc[part.model.map(lambda m: complete.loc[(*key, m)])]
        if part.empty:
            raise ValueError('Route has no complete candidate')
        best = part.sort_values(['mape_positive_pct', 'mae', 'model']).iloc[0]
        rows.append({**dict(zip(['window_days'] + ROUTE, key)), 'model': best.model,
            'selection_split': 'validation', 'selection_cutoff': cfg['validation_end'],
            'validation_mape_positive_pct': best.mape_positive_pct, 'validation_mae': best.mae})
    return pd.DataFrame(rows)


def allocate_days(predictions, daily, history_days=90):
    groups = checked_series(daily)
    records = []
    for r in predictions.itertuples():
        key = (r.destination_country, r.carrier)
        y = groups[key].loc[r.as_of_date-pd.Timedelta(days=history_days-1):r.as_of_date].sales_qty
        dates = pd.date_range(r.window_start, periods=int(r.window_days))
        means = y.groupby(y.index.dayofweek).mean().reindex(range(7), fill_value=0)
        # Missing weekday history is an input error; all-zero observed history is explicit.
        if y.empty or not np.isfinite(means).all():
            raise ValueError('No weekday allocation history')
        weights = means.reindex(dates.dayofweek).to_numpy(float)
        weights = weights / weights.sum() if weights.sum() > 0 else np.full(len(dates), 1/len(dates))
        values = float(r.forecast_qty) * weights
        values[-1] += float(r.forecast_qty) - values.sum()
        if not np.isfinite(values).all() or (values < -1e-10).any():
            raise ValueError('Invalid daily allocation')
        for h, (date, quantity) in enumerate(zip(dates, values), 1):
            records.append({**dict(zip(ROUTE, key)), 'window_days': r.window_days, 'as_of_date': r.as_of_date,
                'target_date': date, 'horizon_day': h, 'model': r.model, 'forecast_qty': quantity,
                'aggregate_total_qty': r.forecast_qty, 'is_daily_allocation': True, 'actual_qty': np.nan})
    return pd.DataFrame(records)


def validate_aggregate(folder):
    folder = Path(folder).resolve()
    info = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    if info.get('kind') != 'consecutive_day_aggregate' or info.get('status') != 'complete':
        raise ValueError('Not a complete aggregate forecast')
    required = {'protocol.json', 'daily_sales.csv', 'top_routes.csv', 'selected_models.csv', 'selection_lock.json',
        'test_predictions.csv', 'future_predictions.csv', 'daily_allocation.csv', 'test_metrics.csv'}
    if not required.issubset(info['files']):
        raise ValueError('Missing aggregate artifacts')
    for name, digest in info['files'].items():
        p = (folder/name).resolve()
        if not p.is_relative_to(folder) or not p.is_file() or sha256(p) != digest:
            raise ValueError('Changed or missing aggregate artifact')
    return info


def execute(run_id, config='data/configs/aggregate.json'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run ID')
    path, settings = load_settings(config)
    cfg = read_config(settings['base_config'])
    source = ROOT/cfg['source']; digest = sha256(source)
    out = ROOT/'outputs'/run_id; out.mkdir(exist_ok=False)
    protocol = {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': digest,
        'settings': settings, 'config': cfg, 'config_sha256': sha256(path),
        'implementation_sha256': sha256(__file__), 'top10_rule': 'train quantity only',
        'label': 'quantity sum over complete consecutive UTC days D+1..D+window',
        'test_independent': False, 'daily_R05_acceptance_replaced': False}
    implementation = ['sigma/forecasting/aggregate.py', 'src/common.py', 'src/data.py',
                      'src/evaluation.py', 'M2/models/Prophet/model.py']
    protocol['implementation_modules_sha256'] = {name: sha256(ROOT/name) for name in implementation}
    protocol['python'] = platform.python_version()
    protocol['packages'] = {name: importlib.metadata.version(name) for name in
                           ['numpy', 'pandas', 'lightgbm', 'statsmodels', 'prophet']}
    write_json(out/'protocol.json', protocol)
    try:
        sales, audit = audit_orders(source, cfg)
        daily = daily_sales(sales, cfg); top = route_top(daily, cfg)
        write_json(out/'data_audit.json', audit); write_csv(out/'daily_sales.csv', daily); write_csv(out/'top_routes.csv', top)
        selections, val_frames, test_frames, future_frames, logs = [], [], [], [], []
        for window in settings['windows']:
            frame, log = phase(daily, top, cfg, settings, window, 'validation', output=out)
            val_frames.append(frame); logs.append(log)
            selected = select(frame, cfg); selections.append(selected)
        selected = pd.concat(selections, ignore_index=True)
        write_csv(out/'selected_models.csv', selected)
        write_json(out/'selection_lock.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'selection_sha256': sha256(out/'selected_models.csv'), 'basis': settings['selection'], 'test_used_for_ranking': False})
        write_csv(out/'validation_predictions.csv', pd.concat(val_frames, ignore_index=True))
        write_csv(out/'validation_metrics.csv', metric_table(pd.concat(val_frames, ignore_index=True), cfg))
        print('7/30-day choices locked from validation; starting retrospective test', flush=True)
        for window in settings['windows']:
            view = selected.loc[selected.window_days.eq(window)]
            choices = dict(zip(map(tuple, view[ROUTE].to_numpy()), view.model))
            for split, dest in [('test', test_frames), ('future', future_frames)]:
                write_json(out/f'{split}_{window}d_execution.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
                    'selection_sha256': sha256(out/'selected_models.csv')})
                frame, log = phase(daily, top, cfg, settings, window, split, choices, out)
                if not np.isfinite(frame.forecast_qty).all():
                    raise ValueError('Selected model failed; no silent fallback')
                dest.append(frame); logs.append(log)
        test, future = pd.concat(test_frames, ignore_index=True), pd.concat(future_frames, ignore_index=True)
        write_csv(out/'test_predictions.csv', test); write_csv(out/'future_predictions.csv', future)
        write_csv(out/'fit_log.csv', pd.concat(logs, ignore_index=True))
        metrics = metric_table(test, cfg); write_csv(out/'test_metrics.csv', metrics)
        allocation = allocate_days(pd.concat([test, future], ignore_index=True), daily)
        write_csv(out/'daily_allocation.csv', allocation)
        primary = metrics.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
        primary = primary.loc[primary.cadence.eq('daily_origins')]
        write_csv(out/'top10_results.csv', primary)
        if (sha256(source) != digest or sha256(path) != protocol['config_sha256']
                or any(sha256(ROOT/name) != value for name, value in protocol['implementation_modules_sha256'].items())):
            raise ValueError('Source or implementation changed during run')
        result = [{'window_days': int(h), 'routes_below_20_pct': int(part.passes_20_pct.sum()),
            'mean_mape_positive_pct': float(part.mape_positive_pct.mean()), 'minimum_coverage': float(part.coverage.min()),
            'pairs_per_route': int(part.n_expected.iloc[0])} for h, part in primary.groupby('window_days')]
        summary = {'kind': 'consecutive_day_aggregate', 'status': 'complete', 'run_id': run_id,
            'source_sha256': digest, 'result': result, 'top_routes': len(top), 'all_routes': daily[ROUTE].drop_duplicates().shape[0],
            'test_independent': False, 'daily_R05_acceptance_replaced': False,
            'files': {p.relative_to(out).as_posix(): sha256(p) for p in out.rglob('*') if p.is_file()}}
        write_json(out/'summary.json', summary)
        print(json.dumps(result), flush=True)
        return summary
    except BaseException as error:
        write_json(out/'failed.json', {'status': 'failed', 'error_type': type(error).__name__, 'source_sha256': digest})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True); parser.add_argument('--config', default='data/configs/aggregate.json')
    args = parser.parse_args(); execute(args.run_id, args.config)
