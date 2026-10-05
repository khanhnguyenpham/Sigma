"""Fixed convex combinations after historical calibration of one component."""
import numpy as np


def calibrated_blend_values(values, factors, weights):
    weights = np.asarray(weights, float)
    if (len(values) != 2 or len(weights) != 2 or not np.isfinite(weights).all()
        or (weights < 0).any() or not np.isclose(weights.sum(), 1., atol=1e-12, rtol=0)):
        raise ValueError('Calibrated combination needs two convex weights')
    if set(values[0]) != set(values[1]) or set(factors) != set(values[0]):
        raise ValueError('Calibrated combination route coverage differs')
    if any(not np.isfinite(f) or not .5 <= f <= 1.5 for f in factors.values()):
        raise ValueError('Invalid historical calibration factor')
    if any(not np.isfinite(v) or v < 0 for parent in values for v in parent.values()):
        raise ValueError('Invalid combination component quantity')
    return {key: weights[0] * values[0][key] * factors[key] + weights[1] * values[1][key] for key in factors}
