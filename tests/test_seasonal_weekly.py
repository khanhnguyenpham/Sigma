"""Independent median examples, calendar seam and causal weekly memory."""
import numpy as np
import pandas as pd
import pytest

from sigma.experiments.seasonal_weekly import SeasonalMemory, calendar_distance, weighted_median
from sigma.forecasting.weekly import prepare
from test_weekly_local import fixture


def test_weighted_median_optimizes_relative_error_not_mean():
    assert weighted_median([2, 4, 8], [.5, .25, .125]) == 2
    assert weighted_median([0, 0], [0, 0]) == 0
    with pytest.raises(ValueError):
        weighted_median([1], [-1])


def test_calendar_wraps_at_year_boundary():
    angle = 2 * np.pi / 365.25
    np.testing.assert_allclose(calendar_distance(np.sin(-angle), np.cos(-angle), np.sin(angle), np.cos(angle)), 2., atol=1e-10)
    np.testing.assert_allclose(calendar_distance(0, 1, 0, -1), 365.25 / 2)


@pytest.mark.parametrize('units', ['raw', 'ratio'])
@pytest.mark.parametrize('half_life', [None, 90])
def test_known_quantities_and_future_do_not_change_memory(units, half_life):
    _, settings, _, daily = fixture('boosted_median')
    spec = {'units': units, 'bandwidth_days': 28, 'half_life_days': half_life}
    origin = pd.Timestamp('2025-06-30')
    changed = daily.copy()
    changed.loc[changed.date.gt(origin), ['sales_qty', 'order_count']] = 999999.
    a, b = prepare(daily, settings), prepare(changed, settings)
    ma = SeasonalMemory(spec).fit(a, origin, 365)
    mb = SeasonalMemory(spec).fit(b, origin, 365)
    assert ma.max_label_end == mb.max_label_end == origin
    pred = ma.predict(a, origin)
    assert pred == mb.predict(b, origin)
    for (key, block), value in pred.items():
        np.testing.assert_allclose(value, {'A': 14., 'B': 35., 'C': 0.}[key[1]], atol=1e-8)
    with pytest.raises(ValueError, match='predates'):
        ma.predict(a, origin - pd.Timedelta(days=1))


@pytest.mark.parametrize('bad', [0, -1, float('nan')])
def test_invalid_calendar_bandwidth_rejected(bad):
    with pytest.raises(ValueError, match='settings'):
        SeasonalMemory({'units': 'ratio', 'bandwidth_days': bad, 'half_life_days': None})
