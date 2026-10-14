import numpy as np
import pandas as pd
import pytest
from src.evaluation import score

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
