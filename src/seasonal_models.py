"""Causal calendar-neighbour sales distributions; no future observations."""
from __future__ import annotations

import numpy as np
import pandas as pd


SEASONAL_SPECS = {f"distribution_{band}_{recent}": (band, recent)
                  for band in (14, 28, 56) for recent in (0, 28)}


def positive_mape_action(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    keep = (values > 0) & (weights > 0)
    if not keep.any():
        return 0.0
    y, w = values[keep], weights[keep] / values[keep]
    order = np.argsort(y)
    y, w = y[order], w[order]
    return float(y[np.searchsorted(np.cumsum(w), w.sum() / 2)])


def calendar_weights(dates, target, bandwidth):
    # Calendar is known at the origin; observed values are supplied separately.
    phase = dates.dayofyear.to_numpy() / np.where(dates.is_leap_year, 366., 365.)
    target = pd.Timestamp(target)
    target_phase = target.dayofyear / (366. if target.is_leap_year else 365.)
    distance = np.abs(phase - target_phase)
    distance = np.minimum(distance, 1 - distance) * 365.25
    return np.exp(-.5 * (distance / bandwidth) ** 2)


def distribution_forecast(history, model_id, targets):
    bandwidth, recent = SEASONAL_SPECS[model_id]
    values = history.to_numpy(dtype=float)
    if len(history) < 56 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Distribution model needs complete nonnegative history")
    trend = 1.0
    if recent:
        # Estimate current level relative to the previous year's matching season.
        past = history.iloc[:-recent]
        if len(past) >= 365:
            expected = np.mean([np.average(past.to_numpy(), weights=calendar_weights(past.index, date, bandwidth))
                                for date in history.index[-recent:]])
            if expected > 0:
                trend = np.clip(history.iloc[-recent:].mean() / expected, .5, 2.)
    return np.asarray([positive_mape_action(values, calendar_weights(history.index, day, bandwidth)) * trend
                       for day in targets])
