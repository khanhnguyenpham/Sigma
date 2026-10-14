"""Causal multiplicative head for the fixed LG U+ configuration."""
import numpy as np

def relative_factor(predicted, actual, prior_weeks):
    predicted, actual = np.asarray(predicted, float), np.asarray(actual, float)
    if (predicted.shape != actual.shape or not np.isfinite(predicted).all()
            or not np.isfinite(actual).all() or (predicted < 0).any() or (actual < 0).any()
            or prior_weeks < 0):
        raise ValueError('Invalid calibration history')
    usable = (predicted > 0) & (actual > 0)
    if not usable.any():
        return 1.
    ratios = actual[usable] / predicted[usable]
    weights = predicted[usable] / actual[usable]
    if prior_weeks:
        ratios = np.append(ratios, 1.)
        weights = np.append(weights, prior_weeks * weights.mean())
    order = np.argsort(ratios, kind='stable')
    ratios, weights = ratios[order], weights[order]
    factor = ratios[np.searchsorted(np.cumsum(weights), weights.sum() / 2)]
    return float(np.clip(factor, .5, 1.5))
