import numpy as np
import pandas as pd
import pytest

from src.evaluation import score, select_models
from src.models import baseline, feature_row, rolling_route, training_matrix, fit_lgbm


def test_baselines_by_hand():
    values = np.arange(1, 8)
    np.testing.assert_array_equal(baseline(values, "naive", 14), np.full(14, 7))
    np.testing.assert_array_equal(baseline(values, "ma7", 14), np.full(14, 4))
    np.testing.assert_array_equal(baseline(values, "seasonal_naive7", 14), np.tile(values, 2))


def test_metrics_zero_missing_bias():
    frame = pd.DataFrame({"actual_qty": [0, 10, 20, np.nan], "forecast_qty": [5, 12, 16, 100]})
    result = score(frame)
    assert result["mape_positive_pct"] == pytest.approx(20)
    assert result["mae"] == pytest.approx(11 / 3)
    assert result["wape_pct"] == pytest.approx(100 * 11 / 30)
    assert result["bias"] == pytest.approx(1)
    assert result["coverage"] == .75
    frame.actual_qty = 0
    result = score(frame)
    assert np.isnan(result["mape_positive_pct"])
    assert np.isnan(result["wape_pct"])


def test_future_change_does_not_affect_origin(cfg):
    series = pd.Series(np.arange(1, 101), index=pd.date_range("2024-01-01", periods=100))
    original, _ = rolling_route(series, ("A", "B"), "ma7", "2024-03-01", "2024-03-10", cfg)
    series.loc["2024-03-01":] = 999
    changed, _ = rolling_route(series, ("A", "B"), "ma7", "2024-03-01", "2024-03-10", cfg)
    np.testing.assert_array_equal(original.loc[original.as_of_date.eq("2024-02-29"), "forecast_qty"], changed.loc[changed.as_of_date.eq("2024-02-29"), "forecast_qty"])


def test_pooled_labels_and_features_exclude_future():
    series = pd.Series(np.arange(80.), index=pd.date_range("2024-01-01", periods=80))
    cutoff = "2024-02-15"
    x, y = training_matrix({("A", "B"): series}, cutoff, 14)
    assert y.max() == 45
    series.loc["2024-02-16":] = 9999
    x2, y2 = training_matrix({("A", "B"): series}, cutoff, 14)
    np.testing.assert_array_equal(x, x2); np.testing.assert_array_equal(y, y2)
    indices = np.where((x[:, 1] == 1) & (x[:, 2] == 27))[0]
    np.testing.assert_allclose(x[indices[0]], feature_row(np.arange(28.), 0, "2024-01-28", 1))


def test_selection_rejects_test_metrics(cfg):
    with pytest.raises(ValueError, match="validation"):
        select_models(pd.DataFrame({"split": ["test"]}), pd.DataFrame(), cfg)


def test_lightgbm_refits_deterministically_before_cutoff(cfg):
    series = pd.Series(np.tile([1., 2., 3., 4., 5., 6., 7.], 12), index=pd.date_range("2024-01-01", periods=84))
    mapping = {("A", "B"): series}
    first = fit_lgbm(mapping, "2024-02-29", "lgbm_15_20", cfg)
    series.loc["2024-03-01":] = 9999
    second = fit_lgbm(mapping, "2024-02-29", "lgbm_15_20", cfg)
    x = pd.DataFrame([feature_row(np.arange(1., 31.), 0, "2024-02-29", 3)], columns=first.feature_name_)
    np.testing.assert_allclose(first.predict(x), second.predict(x), atol=1e-8, rtol=0)


def test_validation_tail_actual_is_not_test_label(cfg):
    series = pd.Series(1., index=pd.date_range("2024-01-01", "2025-12-31"))
    frame, _ = rolling_route(series, ("A", "B"), "ma7", "2025-07-01", "2025-09-30", cfg)
    tail = frame.loc[frame.target_date.gt("2025-09-30")]
    assert len(tail) > 0 and tail.actual_qty.isna().all()
    assert frame.groupby("as_of_date").size().eq(14).all()


def test_weighted_median_minimizes_positive_training_percentage_loss():
    from src.models import weighted_positive_median
    values = np.array([0, 1, 2, 2, 9, 10], dtype=float)
    forecast = weighted_positive_median(values)
    positive = values[values > 0]
    loss = lambda f: np.mean(np.abs(positive - f) / positive)
    assert loss(forecast) == min(loss(f) for f in positive)
    assert weighted_positive_median([0, 0]) == 0


def test_robust_model_never_reads_future_and_scores_full_zero_coverage():
    from src.models import rolling_route
    cfg = {"horizon": 14, "refit_days": 7}
    dates = pd.date_range("2024-01-01", periods=80)
    history = pd.Series(np.tile([0, 1, 2, 3, 4, 5, 6], 12)[:80], index=dates)
    changed = history.copy()
    changed.loc[dates[60]:] = 9999
    a, _ = rolling_route(history, ("Synthetic", "Carrier"), "robust_28_1", dates[60], dates[65], cfg)
    b, _ = rolling_route(changed, ("Synthetic", "Carrier"), "robust_28_1", dates[60], dates[65], cfg)
    first = a.as_of_date.min()
    np.testing.assert_allclose(a.loc[a.as_of_date.eq(first), "forecast_qty"], b.loc[b.as_of_date.eq(first), "forecast_qty"])
    from src.evaluation import score
    actual = a.loc[a.target_date.le(dates[65])]
    assert score(actual)["coverage"] == 1
    assert score(actual)["n_zero_pairs"] > 0
