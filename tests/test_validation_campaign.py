"""Research isolation, origin causality, historical analogues and unit checks."""
import numpy as np
import pandas as pd
import pytest

from validation_campaign import features, fit, predict, model_inputs, choose_inner, SPECS


def example_daily():
    dates = pd.date_range('2024-01-01', '2025-09-30')
    frames = []
    for i, carrier in enumerate(('A', 'B')):
        frames.append(pd.DataFrame({'date': dates, 'destination_country': 'Fake',
            'carrier': carrier, 'sales_qty': np.arange(len(dates), dtype=float) + 10 + i,
            'order_count': np.full(len(dates), 3 + i)}))
    return pd.concat(frames, ignore_index=True)


def test_campaign_annual_features_ignore_future_and_align_leap_year():
    daily = example_daily(); keys = [('Fake', 'A'), ('Fake', 'B')]
    origin = pd.Timestamp('2025-02-28')
    prepared = features(daily, keys)
    altered = daily.copy()
    altered.loc[altered.date.gt(origin), ['sales_qty', 'order_count']] = 999999.
    changed = features(altered, keys)
    for key in prepared:
        a, b = prepared[key], changed[key]
        mask = a['origins'] <= origin
        pd.testing.assert_frame_equal(a['x'].loc[mask], b['x'].loc[mask])
        np.testing.assert_array_equal(a['scale'][mask], b['scale'][mask])
    table = prepared[(('Fake', 'A'), 1)]
    row = table['x'].iloc[np.flatnonzero(table['origins'] == origin)[0]]
    # Mar 1 2025 maps to Mar 1 2024 (60 days from Jan 1 in leap year),
    # not to Mar 2 obtained by blindly subtracting 365 days.
    assert row.prior_year_qty == 70.
    assert row.prior_year_mean15 == 70.
    assert row.prior_year_mean57 == 70.
    assert row.prior_year_country_mean15 == 141.


def test_campaign_training_does_not_consume_future_labels():
    daily = example_daily(); keys = [('Fake', 'A')]
    cutoff = pd.Timestamp('2025-04-30')
    spec = {**SPECS['ablation_annual_ratio_l7'], 'n_estimators': 12}
    prepared = features(daily, keys)
    model, last_label, n = fit(prepared, cutoff, spec, {'seed': 42, 'lightgbm_threads': 1})
    changed = daily.copy()
    changed.loc[changed.date.gt(cutoff), ['sales_qty', 'order_count']] = 1e6
    altered = features(changed, keys)
    second, last_second, n_second = fit(altered, cutoff, spec, {'seed': 42, 'lightgbm_threads': 1})
    assert last_label == last_second == cutoff and n == n_second
    a = predict(model, prepared, cutoff, spec)[1]
    b = predict(second, altered, cutoff, spec)[1]
    np.testing.assert_array_equal(a, b)


def test_campaign_ratio_forecasts_return_to_quantity_units():
    daily = example_daily(); prepared = features(daily, [('Fake', 'A')])
    spec = SPECS['ablation_history_ratio_l7']
    origin = pd.Timestamp('2025-04-30')
    table = prepared[(('Fake', 'A'), 1)]
    idx = np.flatnonzero(table['origins'] == origin)[0]
    # Trailing90 mean of a linear sequence equals the midpoint's quantity.
    scale = table['scale'][idx]
    expected = (daily.loc[daily.carrier.eq('A') & daily.date.between(origin-pd.Timedelta(days=89), origin)].sales_qty.mean())
    assert scale == expected
    x = model_inputs(table, spec, [idx])
    assert x.lag0.iloc[0] * scale == table['x'].lag0.iloc[idx]
    class One:
        def predict(self, x):
            return np.ones(len(x))
    _, values, clips = predict(One(), prepared, origin, spec)
    assert clips == 0
    np.testing.assert_allclose(values, np.full(14, expected))


def test_campaign_inner_selector_refuses_validation_and_test():
    for split in ('validation', 'test'):
        with pytest.raises(ValueError, match='inner train'):
            choose_inner(pd.DataFrame({'split': [split]}))
