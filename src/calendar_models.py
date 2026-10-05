"""Known-calendar regressions; fit labels stop at the declared origin."""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.common import ROUTE


def calendar_features(dates, harmonics):
    dates = pd.DatetimeIndex(dates)
    phase = 2 * np.pi * (dates.dayofyear.to_numpy() - 1) / 365.25
    columns = [(dates.dayofweek.to_numpy() == d).astype(float) for d in range(1, 7)]
    for j in range(1, harmonics + 1):
        columns.extend([np.sin(j * phase), np.cos(j * phase)])
    return np.column_stack(columns)


def calendar_specs(cfg):
    return [f"calendar_{window}_{k}_{str(alpha).replace('.', 'p')}_{loss}"
            for window in cfg["tuning"]["calendar_windows"]
            for k in cfg["tuning"]["calendar_harmonics"]
            for alpha, loss in [(0.001, "lad"), (0.01, "lad"), (0.1, "poisson")]]


def fit_calendar(history, model_id):
    from sklearn.linear_model import QuantileRegressor, PoissonRegressor
    from sklearn.dummy import DummyRegressor
    _, window, harmonics, alpha, loss = model_id.split("_")
    window, harmonics, alpha = int(window), int(harmonics), float(alpha.replace("p", "."))
    if window:
        history = history.iloc[-window:]
    x, y = calendar_features(history.index, harmonics), history.to_numpy(dtype=float)
    if not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("Calendar model needs complete nonnegative history")
    if not y.any():
        model = DummyRegressor(strategy="constant", constant=0).fit(x, y)
    elif loss == "lad":
        model = QuantileRegressor(quantile=0.5, alpha=alpha, solver="highs")
        weights = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
        model.fit(x, y, sample_weight=weights)
    elif loss == "poisson":
        model = PoissonRegressor(alpha=alpha, max_iter=1000).fit(x, y)
    else:
        raise ValueError("Unknown calendar loss")
    return model, harmonics


def predict_calendar(state, targets):
    model, harmonics = state
    return np.maximum(model.predict(calendar_features(targets, harmonics)), 0)


def calendar_validation(daily, top, cfg, progress=lambda message: None):
    from src.models import rolling_route, series_by_route
    series = series_by_route(daily)
    frames, logs = [], []
    for keys in map(tuple, top[ROUTE].to_numpy()):
        for model_id in calendar_specs(cfg):
            frame, log = rolling_route(series[keys], keys, model_id,
                                       cfg["validation_start"], cfg["validation_end"], cfg)
            frame["split"] = np.where(frame.target_date.le(pd.Timestamp(cfg["validation_end"])), "validation", "outside_validation")
            frames.append(frame); logs.append(log)
        progress("Calendar validation: one train top10 route complete")
    return pd.concat(frames, ignore_index=True), pd.concat(logs, ignore_index=True)
