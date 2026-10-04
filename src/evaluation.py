"""Time-based scoring and validation-only selection; zero is not missing."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import BASELINES, ROUTE


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


def metric_table(predictions):
    records = []
    for keys, group in predictions.groupby(["split", "model"] + ROUTE, dropna=False, sort=True):
        meta = dict(zip(["split", "model"] + ROUTE, keys))
        subsets = [("h1_7", group[group.horizon_day <= 7]), ("h8_14", group[group.horizon_day > 7])]
        subsets += [(f"h{h}", group[group.horizon_day == h]) for h in sorted(group.horizon_day.unique())]
        for label, selected in subsets:
            if not selected.empty:
                records.append({**meta, "horizon_group": label, **score(selected)})
    return pd.DataFrame(records)


def select_models(metrics, top, cfg, invalid_candidates=None):
    if not metrics.split.eq("validation").all():
        raise ValueError("Model selection accepts validation metrics only")
    invalid_candidates = invalid_candidates or set()
    primary = metrics.loc[metrics.horizon_group.eq("h1_7")].copy()
    top_keys = set(map(tuple, top[ROUTE].to_numpy()))
    selected = []
    for keys, group in primary.groupby(ROUTE, sort=True):
        group = group.loc[~group.model.map(lambda model: (keys, model) in invalid_candidates)]
        group = group.loc[group.coverage.eq(1) & group.mae.notna()]
        fallback = group.loc[group.model.isin(BASELINES)].sort_values(["mae", "model"])
        if fallback.empty:
            raise ValueError("No complete baseline available for selection")
        if keys in top_keys:
            passing = group.loc[group.mape_positive_pct.le(cfg["mape_limit_pct"])]
            candidates = passing.sort_values(["mae", "model"]) if len(passing) else group.sort_values(["mape_positive_pct", "mae", "model"], na_position="last")
        else:
            candidates = fallback
        best = candidates.iloc[0]
        selected.append({**dict(zip(ROUTE, keys)), "model": best.model,
                         "fallback_model": fallback.iloc[0].model,
                         "selection_split": "validation", "selection_cutoff": cfg["validation_end"],
                         "validation_mape_positive_pct": best.mape_positive_pct,
                         "validation_mae": best.mae,
                         "is_top10": keys in top_keys,
                         "validation_target_met": bool(best.mape_positive_pct <= cfg["mape_limit_pct"]) if keys in top_keys else None,
                         "tie_rule": "metric then lexical model id; tolerance recorded in config"})
    return pd.DataFrame(selected)


def acceptance(metrics, top, cfg):
    test = metrics.loc[metrics.split.eq("test") & metrics.horizon_group.eq("h1_7") & metrics.model.eq("selected")]
    table = top.merge(test, on=ROUTE, how="left", validate="one_to_one")
    table["accuracy_passed"] = table.mape_positive_pct.le(cfg["mape_limit_pct"]) & table.coverage.eq(1)
    table["criterion"] = "Each train top10: positive-day MAPE <=20%, full eligible pair coverage, h1-7"
    return table
