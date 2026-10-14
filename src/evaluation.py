"""Quantity metrics; positive-only MAPE, zero and missing remain distinct."""
import numpy as np
import pandas as pd

def score(frame, expected_pairs=None):
    actual = pd.to_numeric(frame.actual_qty, errors="coerce").to_numpy(dtype=float)
    forecast = pd.to_numeric(frame.forecast_qty, errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(actual) & np.isfinite(forecast)
    if (actual[valid] < 0).any():
        raise ValueError("Negative actual quantity")
    a, f = actual[valid], forecast[valid]
    positive = a > 0
    error = f - a
    expected = len(frame) if expected_pairs is None else expected_pairs
    return {
        "mape_positive_pct": float(np.mean(np.abs(error[positive]) / a[positive]) * 100) if positive.any() else np.nan,
        "mae": float(np.mean(np.abs(error))) if len(a) else np.nan,
        "wape_pct": float(np.sum(np.abs(error)) / np.sum(a) * 100) if np.sum(a) > 0 else np.nan,
        "bias": float(np.mean(error)) if len(a) else np.nan,
        "n_expected": expected, "n_labeled_pairs": int(np.isfinite(actual).sum()),
        "n_scored_pairs": len(a), "n_positive_pairs": int(positive.sum()),
        "n_zero_pairs": int((a == 0).sum()),
        "coverage": len(a) / expected if expected else np.nan,
        "positive_share": float(positive.mean()) if len(a) else np.nan,
        "unique_target_days": int(frame.loc[valid, "target_date"].nunique()) if "target_date" in frame else 0,
    }
