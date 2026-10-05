"""Same units, positive-only MAPE and zero/missing/unequal pair safeguards."""
import numpy as np
import pytest
from sigma.analysis.comparison import score


def test_comparison_metric_preserves_zero_pairs_and_signed_bias():
    m = score([0, 10, 20], [5, 12, 16])
    assert m['pairs'] == 3 and m['positive_pairs'] == 2 and m['zero_pairs'] == 1
    assert m['mape_positive_pct'] == pytest.approx(20)
    assert m['mae_qty'] == pytest.approx(11 / 3)
    assert m['wape_pct'] == pytest.approx(110 / 3)
    assert m['bias_pct'] == pytest.approx(10)
    zeros = score([0], [2])
    assert np.isnan(zeros['mape_positive_pct']) and zeros['mae_qty'] == 2


@pytest.mark.parametrize('actual,forecast', [([1, 2], [1]), ([1], [np.nan]), ([], [])])
def test_comparison_rejects_missing_or_unmatched_pairs(actual, forecast):
    with pytest.raises(ValueError):
        score(actual, forecast)
