"""Baselines, bounded SARIMA search and conditional pooled/direct LightGBM."""
from __future__ import annotations

import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product

import numpy as np
import pandas as pd

from src.common import BASELINES, ROUTE
from src.calendar_models import fit_calendar, predict_calendar
from src.seasonal_models import distribution_forecast, SEASONAL_SPECS
from src.context_models import CONTEXT_SPECS, context_rolling, fit_context, prepare_context, context_features
from src.count_models import fit_count, predict_count, count_rolling
from src.cohort_models import COHORT_SPECS, fit_cohort, predict_cohort, cohort_rolling


def sarima_specs():
    return {f"sarima_{p}{d}{q}_{P}{D}{Q}_7": (order, seasonal)
            for order, seasonal in product([(1, 0, 0), (1, 1, 1)], [(0, 0, 0, 7), (1, 0, 0, 7), (0, 1, 1, 7)])
            for p, d, q in [order] for P, D, Q, _ in [seasonal]}


def baseline(history, model, horizon):
    history = np.asarray(history, dtype=float)
    if len(history) < 7 or not np.isfinite(history).all():
        raise ValueError("Baseline needs at least seven complete observed days")
    if model == "naive":
        return np.repeat(history[-1], horizon)
    if model == "ma7":
        return np.repeat(history[-7:].mean(), horizon)
    if model == "seasonal_naive7":
        return np.resize(history[-7:], horizon)
    raise ValueError("Unknown baseline")


def weighted_positive_median(values):
    """Constant minimizer of positive-day training MAPE; zero still scored separately."""
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Invalid robust model history")
    positive = np.sort(values[values > 0])
    if not len(positive):
        return 0.0
    weights = 1.0 / positive
    return float(positive[np.searchsorted(np.cumsum(weights), weights.sum() / 2)])


def robust_forecast(history, model, targets):
    _, window, weekday = model.split("_")
    window, weekday = int(window), int(weekday)
    observed = history.iloc[-window:] if window else history
    global_value = weighted_positive_median(observed.to_numpy())
    output = []
    for target in targets:
        value = global_value
        if weekday:
            same_day = observed.loc[observed.index.dayofweek == target.dayofweek]
            count = int(same_day.gt(0).sum())
            if count:
                local = weighted_positive_median(same_day.to_numpy())
                # Fixed prior strength, declared before the new validation search.
                weight = count / (count + 20)
                value = weight * local + (1 - weight) * global_value
        output.append(value)
    return np.asarray(output)


def robust_validation(daily, top, cfg):
    series_map = series_by_route(daily)
    frames, logs = [], []
    for keys in map(tuple, top[ROUTE].to_numpy()):
        for window in cfg["tuning"]["robust_windows"]:
            for weekday in [0, 1]:
                model = f"robust_{window}_{weekday}"
                frame, log = rolling_route(series_map[keys], keys, model,
                                           cfg["validation_start"], cfg["validation_end"], cfg)
                frame["split"] = np.where(frame.target_date.le(pd.Timestamp(cfg["validation_end"])), "validation", "outside_validation")
                frames.append(frame); logs.append(log)
    return pd.concat(frames, ignore_index=True), pd.concat(logs, ignore_index=True)


def distribution_validation(daily, top, cfg):
    series_map = series_by_route(daily)
    frames, logs = [], []
    for keys in map(tuple, top[ROUTE].to_numpy()):
        for model in SEASONAL_SPECS:
            frame, log = rolling_route(series_map[keys], keys, model,
                cfg['validation_start'], cfg['validation_end'], cfg)
            frame['split'] = np.where(frame.target_date.le(pd.Timestamp(cfg['validation_end'])),
                                      'validation', 'outside_validation')
            frames.append(frame); logs.append(log)
    return pd.concat(frames, ignore_index=True), pd.concat(logs, ignore_index=True)


def fit_sarima(history, model, cfg, start_params=None):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    order, seasonal = sarima_specs()[model]
    trend = "c" if order[1] + seasonal[1] == 0 else "n"
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = SARIMAX(np.asarray(history, dtype=float), order=order, seasonal_order=seasonal,
                         trend=trend, enforce_stationarity=False, enforce_invertibility=False).fit(
                             disp=False, maxiter=cfg["sarima_maxiter"], start_params=start_params)
    if not result.mle_retvals.get("converged", False):
        raise RuntimeError("SARIMA did not converge")
    return result, sorted({type(w.message).__name__ for w in captured})


def series_by_route(daily):
    return {keys: g.sort_values("date").set_index("date").sales_qty.astype(float) for keys, g in daily.groupby(ROUTE, sort=True)}


def rolling_route(series, keys, model, start, end, cfg, fallback_model=None):
    rows, logs = [], []
    state = None
    parameters = None
    candidate_failed = False
    origins = pd.date_range(pd.Timestamp(start) - pd.Timedelta(days=1), pd.Timestamp(end) - pd.Timedelta(days=1))
    for index, origin in enumerate(origins):
        history = series.loc[:origin].to_numpy()
        effective = model
        warning_types = []
        try:
            if candidate_failed:
                pred = np.repeat(np.nan, cfg["horizon"])
                raise StopIteration
            if model in BASELINES:
                pred = baseline(history, model, cfg["horizon"])
            elif model in SEASONAL_SPECS:
                pred = distribution_forecast(series.loc[:origin], model,
                    pd.date_range(origin + pd.Timedelta(days=1), periods=cfg["horizon"]))
            elif model.startswith("calendar_"):
                if index % cfg["refit_days"] == 0 or state is None:
                    state = fit_calendar(series.loc[:origin], model)
                pred = predict_calendar(state, pd.date_range(origin + pd.Timedelta(days=1), periods=cfg["horizon"]))
            elif model.startswith("robust_"):
                if index % cfg["refit_days"] == 0 or state is None:
                    state = series.loc[:origin].copy()
                pred = robust_forecast(state, model, pd.date_range(origin + pd.Timedelta(days=1), periods=cfg["horizon"]))
            else:
                if not np.isfinite(history).all():
                    raise ValueError("Missing history")
                if index % cfg["refit_days"] == 0 or state is None:
                    state, warning_types = fit_sarima(history, model, cfg, parameters)
                    parameters = state.params
                else:
                    state = state.extend(np.asarray([history[-1]]))
                pred = np.asarray(state.forecast(cfg["horizon"]), dtype=float)
                if not np.isfinite(pred).all():
                    raise RuntimeError("Non-finite SARIMA forecast")
            negatives = int((pred < 0).sum())
            pred = np.maximum(pred, 0)
            if index % cfg["refit_days"] == 0 or negatives or warning_types:
                logs.append({**dict(zip(ROUTE, keys)), "origin": origin, "model": model,
                             "status": "ok", "warnings": ",".join(warning_types), "negative_clips": negatives})
        except StopIteration:
            pass
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as error:
            logs.append({**dict(zip(ROUTE, keys)), "origin": origin, "model": model,
                         "status": "failed", "error_type": type(error).__name__, "negative_clips": 0})
            state = None
            if fallback_model is None:
                pred = np.repeat(np.nan, cfg["horizon"])
                if model not in BASELINES:
                    candidate_failed = True
            else:
                pred = baseline(history, fallback_model, cfg["horizon"])
                effective = fallback_model
        for h, forecast in enumerate(pred, 1):
            target = origin + pd.Timedelta(days=h)
            rows.append({**dict(zip(ROUTE, keys)), "as_of_date": origin, "target_date": target,
                         "forecast_date": target, "horizon_day": h, "model": model,
                         "effective_model": effective, "forecast_qty": forecast,
                         "actual_qty": series.get(target, np.nan) if target <= pd.Timestamp(end) else np.nan})
    return pd.DataFrame(rows), pd.DataFrame(logs)


def baseline_backtest(daily, cfg, split="validation"):
    frames, logs = [], []
    for keys, series in series_by_route(daily).items():
        for model in BASELINES:
            frame, log = rolling_route(series, keys, model, cfg[f"{split}_start"], cfg[f"{split}_end"], cfg)
            frame["split"] = np.where(frame.target_date.le(pd.Timestamp(cfg[f"{split}_end"])), split, "outside_" + split)
            frames.append(frame); logs.append(log)
    return pd.concat(frames, ignore_index=True), pd.concat(logs, ignore_index=True)


def _sarima_job(series, keys, model, cfg):
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        return rolling_route(series, keys, model, cfg["validation_start"], cfg["validation_end"], cfg)


def sarima_validation(daily, top, cfg, progress=lambda message: None):
    all_series = series_by_route(daily)
    frames, logs = [], []
    jobs = [(keys, model) for keys in map(tuple, top[ROUTE].to_numpy()) for model in sarima_specs()]
    with ProcessPoolExecutor(max_workers=cfg.get("sarima_workers", 1)) as pool:
        futures = {pool.submit(_sarima_job, all_series[keys], keys, model, cfg): (keys, model) for keys, model in jobs}
        for i, future in enumerate(as_completed(futures), 1):
            frame, log = future.result()
            progress(f"SARIMA validation configuration {i}/{len(jobs)} complete")
            frame["split"] = np.where(frame.target_date.le(pd.Timestamp(cfg["validation_end"])), "validation", "outside_validation")
            frames.append(frame); logs.append(log)
    predictions = pd.concat(frames, ignore_index=True).sort_values(ROUTE + ["model", "as_of_date", "horizon_day"]).reset_index(drop=True)
    log = pd.concat(logs, ignore_index=True).sort_values(ROUTE + ["model", "origin"]).reset_index(drop=True)
    return predictions, log


FEATURES = ["route_index", "horizon_day", "lag0", "lag1", "lag6", "lag13", "mean7", "mean28", "std28", "target_weekday", "target_month", "target_dayofyear"]


def feature_row(values, route_index, origin, horizon):
    values = np.asarray(values, dtype=float)
    if len(values) < 28 or not np.isfinite(values[-28:]).all():
        raise ValueError("Incomplete feature history")
    target = pd.Timestamp(origin) + pd.Timedelta(days=horizon)
    return [route_index, horizon, values[-1], values[-2], values[-7], values[-14],
            values[-7:].mean(), values[-28:].mean(), values[-28:].std(),
            target.dayofweek, target.month, target.dayofyear]


def training_matrix(series_map, cutoff, horizon):
    x, y = [], []
    for route_index, (_, series) in enumerate(sorted(series_map.items())):
        observed = series.loc[:pd.Timestamp(cutoff)]
        values = observed.to_numpy()
        roll = pd.Series(values)
        means7 = roll.rolling(7).mean().to_numpy()
        means28 = roll.rolling(28).mean().to_numpy()
        std28 = roll.rolling(28).std(ddof=0).to_numpy()
        for h in range(1, horizon + 1):
            indices = np.arange(27, len(observed) - h)
            if not len(indices):
                continue
            targets = observed.index[indices] + pd.Timedelta(days=h)
            features = np.column_stack([
                np.full(len(indices), route_index), np.full(len(indices), h), values[indices],
                values[indices - 1], values[indices - 6], values[indices - 13],
                means7[indices], means28[indices], std28[indices],
                targets.dayofweek, targets.month, targets.dayofyear,
            ])
            labels = values[indices + h]
            valid = np.isfinite(features).all(axis=1) & np.isfinite(labels)
            x.append(features[valid]); y.append(labels[valid])
    return (np.concatenate(x), np.concatenate(y)) if x else (np.empty((0, len(FEATURES))), np.empty(0))


def selected_backtest(daily, selected, top, cfg, progress=lambda message: None, sales=None):
    frames, logs = [], []
    series_map = series_by_route(daily)
    for row in selected.itertuples(index=False):
        keys = (row.destination_country, row.carrier)
        if row.model.startswith(("lgbm_", "context_", "count_", 'countmonth_', 'cohort_')):
            continue
        progress(f"Test locked model {row.model}")
        frame, log = rolling_route(series_map[keys], keys, row.model, cfg["test_start"], cfg["test_end"], cfg, row.fallback_model)
        frame["requested_model"] = row.model
        frame["model"] = "selected"
        frame["split"] = np.where(frame.target_date.le(pd.Timestamp(cfg["test_end"])), "test", "outside_test")
        frames.append(frame); logs.append(log)
    ids = sorted(set(selected.loc[selected.model.str.startswith("lgbm_"), "model"]))
    if ids:
        frame, log = lgbm_rolling(daily, top, cfg, ids, "test", progress)
        keep = selected[ROUTE + ["model"]]
        frame = frame.merge(keep, on=ROUTE + ["model"], how="inner", validate="many_to_one")
        frame["requested_model"] = frame.model
        frame["model"] = "selected"
        frames.append(frame); logs.append(log)
    ids = sorted(set(selected.loc[selected.model.str.startswith('context_'), 'model']))
    if ids:
        frame, log = context_rolling(daily, top, cfg, ids, 'test', progress)
        frame = frame.merge(selected[ROUTE + ['model']], on=ROUTE + ['model'], how='inner', validate='many_to_one')
        frame['requested_model'] = frame.model
        frame['model'] = 'selected'
        frames.append(frame); logs.append(log)
    ids = sorted(set(selected.loc[selected.model.str.startswith(('count_', 'countmonth_')), 'model']))
    if ids:
        frame, log = count_rolling(daily,sales,top,cfg,ids,'test',progress)
        frame = frame.merge(selected[ROUTE + ['model']],on=ROUTE + ['model'],how='inner',validate='many_to_one')
        frame['requested_model'] = frame.model
        frame['model'] = 'selected'
        frames.append(frame); logs.append(log)
    ids = sorted(set(selected.loc[selected.model.str.startswith('cohort_'), 'model']))
    if ids:
        frame, log = cohort_rolling(daily, sales, top, cfg, ids, 'test', progress)
        frame = frame.merge(selected[ROUTE + ['model']], on=ROUTE + ['model'], how='inner', validate='many_to_one')
        frame['requested_model'] = frame.model
        frame['model'] = 'selected'
        frames.append(frame); logs.append(log)
    return pd.concat(frames, ignore_index=True), pd.concat(logs, ignore_index=True)


def ensure_forecast_origin(daily, origin):
    origin = pd.Timestamp(origin)
    if origin.tzinfo is not None:
        origin = origin.tz_convert('UTC').tz_localize(None)
    if pd.isna(origin) or origin != origin.normalize():
        raise ValueError('Forecast origin must be a closed UTC calendar day')
    current = daily.loc[daily.date.eq(origin)]
    routes = daily[ROUTE].drop_duplicates()
    if len(current) != len(routes) or current.duplicated(ROUTE).any():
        raise ValueError('Forecast origin has no complete observed route-day coverage')
    if not np.isfinite(current.sales_qty).all():
        raise ValueError('Forecast origin has missing actual sales')
    if 'actual_available' in current and not current.actual_available.eq(True).all():
        raise ValueError('Forecast origin has unavailable actual sales')
    return origin


def forecast_at(daily, selected, top, origin, cfg, progress=lambda message: None, sales=None):
    origin = ensure_forecast_origin(daily, origin)
    if origin < pd.Timestamp(cfg["validation_end"]):
        raise ValueError("Locked selection cannot forecast before its validation cutoff")
    series_map = series_by_route(daily)
    top_series = {keys: series_map[keys] for keys in sorted(map(tuple, top[ROUTE].to_numpy()))}
    fitted_lgbm = {}
    fitted_context = {}
    contexts = None
    count_forecasts = {}
    cohort_forecasts = {}
    rows = []
    for row in selected.itertuples(index=False):
        keys = (row.destination_country, row.carrier)
        values = series_map[keys].loc[:origin].to_numpy()
        effective = row.model
        if row.model in BASELINES:
            pred = baseline(values, row.model, cfg["horizon"])
        elif row.model in SEASONAL_SPECS:
            pred = distribution_forecast(series_map[keys].loc[:origin], row.model,
                pd.date_range(origin + pd.Timedelta(days=1), periods=cfg["horizon"]))
        elif row.model.startswith("calendar_"):
            state = fit_calendar(series_map[keys].loc[:origin], row.model)
            pred = predict_calendar(state, pd.date_range(origin + pd.Timedelta(days=1), periods=cfg["horizon"]))
        elif row.model.startswith("robust_"):
            pred = robust_forecast(series_map[keys].loc[:origin], row.model,
                                   pd.date_range(origin + pd.Timedelta(days=1), periods=cfg["horizon"]))
        elif row.model.startswith("sarima_"):
            try:
                fit, _ = fit_sarima(values, row.model, cfg)
                pred = np.asarray(fit.forecast(cfg["horizon"]))
                if not np.isfinite(pred).all():
                    raise RuntimeError("Non-finite forecast")
            except (ValueError, RuntimeError, np.linalg.LinAlgError):
                pred = baseline(values, row.fallback_model, cfg["horizon"])
                effective = row.fallback_model
        elif row.model.startswith('cohort_'):
            if row.model not in cohort_forecasts:
                specs = {name: (window, loss) for name, window, loss in COHORT_SPECS}
                window, loss = specs[row.model]
                model = fit_cohort(daily, sales, list(top_series), origin, window, loss, cfg)
                cohort_forecasts[row.model] = predict_cohort(model, daily, sales, list(top_series), origin, cfg)
            pred = cohort_forecasts[row.model][keys]
        elif row.model.startswith(('count_', 'countmonth_')):
            if row.model not in count_forecasts:
                state = fit_count(daily,sales,list(top_series),origin,row.model,cfg)
                count_forecasts[row.model] = predict_count(state,daily,list(top_series),origin,cfg)
            pred = count_forecasts[row.model][keys]
        elif row.model.startswith('context_'):
            if contexts is None:
                contexts = prepare_context(daily, list(top_series), origin)
            if row.model not in fitted_context:
                specs = {name:(window,loss) for name,window,loss in CONTEXT_SPECS}
                window,loss = specs[row.model]
                fitted_context[row.model] = fit_context(daily, list(top_series), origin, window, loss, cfg)
            context = contexts[keys]
            x = pd.concat([context_features(context,[len(context['values'])-1],h)
                           for h in range(1,cfg['horizon']+1)],ignore_index=True)
            pred = fitted_context[row.model].predict(x)
        else:
            if row.model not in fitted_lgbm:
                progress(f"Forecast {origin.date()}: fit {row.model}")
                fitted_lgbm[row.model] = fit_lgbm(top_series, origin, row.model, cfg)
            index = sorted(top_series).index(keys)
            x = [feature_row(values, index, origin, h) for h in range(1, cfg["horizon"] + 1)]
            fit = fitted_lgbm[row.model]
            pred = np.zeros(cfg["horizon"]) if fit is None else fit.predict(pd.DataFrame(x, columns=FEATURES))
        for h, forecast in enumerate(pred, 1):
            target = origin + pd.Timedelta(days=h)
            rows.append({**dict(zip(ROUTE, keys)), "as_of_date": origin, "target_date": target,
                         "forecast_date": target, "horizon_day": h, "model": row.model,
                         "effective_model": effective, "forecast_qty": max(0, float(forecast)),
                         "actual_qty": series_map[keys].get(target, np.nan)})
    return pd.DataFrame(rows)


def fit_lgbm(series_map, cutoff, model_id, cfg):
    from lightgbm import LGBMRegressor
    parts = model_id.split("_")
    mape_loss = len(parts) == 4 and parts[1] == "mape"
    leaves, minimum = parts[-2:]
    x, y = training_matrix(series_map, cutoff, cfg["horizon"])
    if not len(y):
        raise ValueError("No complete LightGBM labels before fit cutoff")
    if not y.any():
        return None
    model = LGBMRegressor(objective="regression_l1" if mape_loss else "poisson", num_leaves=int(leaves), min_child_samples=int(minimum),
                          n_estimators=300, learning_rate=0.05, random_state=cfg["seed"],
                          n_jobs=cfg["lightgbm_threads"], deterministic=True, force_col_wise=True, verbosity=-1)
    if mape_loss:
        # Exact positive-day MAPE training weights; does not remove zeros from evaluation.
        weights = np.divide(1.0, y, out=np.zeros_like(y), where=y > 0)
        model.fit(pd.DataFrame(x, columns=FEATURES), y, sample_weight=weights)
    else:
        model.fit(pd.DataFrame(x, columns=FEATURES), y)
    return model


def lgbm_rolling(daily, top, cfg, model_ids, split, progress=lambda message: None):
    all_series = series_by_route(daily)
    series_map = {keys: all_series[keys] for keys in sorted(map(tuple, top[ROUTE].to_numpy()))}
    rows, logs = [], []
    origins = pd.date_range(pd.Timestamp(cfg[f"{split}_start"]) - pd.Timedelta(days=1), pd.Timestamp(cfg[f"{split}_end"]) - pd.Timedelta(days=1))
    for model_id in model_ids:
        model = None
        for i, origin in enumerate(origins):
            if i % cfg["refit_days"] == 0:
                progress(f"LightGBM {split} {model_id}, fit cutoff {origin.date()}")
                model = fit_lgbm(series_map, origin, model_id, cfg)
                logs.append({"model": model_id, "origin": origin, "status": "ok", "fit_cutoff": origin})
            for route_index, (keys, series) in enumerate(sorted(series_map.items())):
                x = [feature_row(series.loc[:origin].to_numpy(), route_index, origin, h) for h in range(1, cfg["horizon"] + 1)]
                pred = np.zeros(cfg["horizon"]) if model is None else model.predict(pd.DataFrame(x, columns=FEATURES))
                for h, forecast in enumerate(pred, 1):
                    target = origin + pd.Timedelta(days=h)
                    rows.append({**dict(zip(ROUTE, keys)), "as_of_date": origin, "target_date": target,
                                     "forecast_date": target, "horizon_day": h, "model": model_id,
                                     "effective_model": model_id, "forecast_qty": max(0, forecast),
                                     "actual_qty": series.get(target, np.nan) if target <= pd.Timestamp(cfg[f"{split}_end"]) else np.nan,
                                     "split": split if target <= pd.Timestamp(cfg[f"{split}_end"]) else "outside_" + split})
    return pd.DataFrame(rows), pd.DataFrame(logs)
