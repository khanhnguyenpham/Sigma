import numpy as np
import pandas as pd
import pytest

from src.cohort_models import prepare_cohort, cohort_features, cohort_training, fit_cohort, predict_cohort, cohort_rolling
from src.models import forecast_at, selected_backtest


KEY = ('Synthetic', 'a')


def fixture():
    dates = pd.date_range('2024-01-01', periods=110)
    sales = pd.DataFrame({'date': dates, 'order_datetime': dates.tz_localize('UTC'),
        'order_id': [f'fake-{i:03}' for i in range(110)],
        'customer_id': [f'fake-customer-{i % 5}' for i in range(110)],
        'customer_type': ['new' if i % 3 == 0 else 'returning' for i in range(110)],
        'product_type': 'eSIM', 'quantity': 1 + np.arange(110) % 3,
        'unit_price_vnd': '100', 'validity_days': '10', 'money_valid': True,
        'destination_country': KEY[0], 'carrier': KEY[1]})
    daily = sales[['date', 'destination_country', 'carrier', 'quantity']].rename(columns={'quantity': 'sales_qty'})
    daily['sales_qty'] = daily.sales_qty.astype(float)
    top = pd.DataFrame([KEY], columns=['destination_country', 'carrier'])
    cfg = {'horizon': 14, 'seed': 42, 'lightgbm_threads': 1, 'refit_days': 7,
           'validation_start': '2024-03-20', 'validation_end': '2024-03-21',
           'test_start': '2024-03-20', 'test_end': '2024-03-21'}
    return daily, sales, top, cfg


def test_first_seen_basket_price_and_known_validity_proxy_by_hand():
    daily, sales, _, _ = fixture()
    ctx = prepare_cohort(daily, sales, [KEY], '2024-03-20')[KEY]
    x = cohort_features(ctx, [79], 1).iloc[0]
    assert x.order_mean28 == 1
    assert x.first_seen_mean7 == 0  # All five fixture buyers already appeared in January.
    assert x.unit_price_mean28 == 100 and x.esim_share28 == 1
    assert x.basket_mean28 == pytest.approx(sales.loc[52:79, 'quantity'].mean())
    # Target i=80 has the order at i=70 due under the declared 10-day proxy.
    assert x.validity_due_proxy == 2
    # A 14-day target cannot use purchases after origin for a 10-day proxy.
    assert cohort_features(ctx, [79], 14).validity_due_proxy.iloc[0] == 0


def test_future_orders_and_other_route_sales_cannot_change_training_or_forecast():
    daily, sales, _, cfg = fixture(); origin = pd.Timestamp('2024-03-19')
    x, y = cohort_training(daily, sales, [KEY], origin, 60, 14)
    model = fit_cohort(daily, sales, [KEY], origin, 60, 'mape', cfg)
    expected = predict_cohort(model, daily, sales, [KEY], origin, cfg)
    daily.loc[daily.date.gt(origin), 'sales_qty'] = 1e6
    future = sales.date.gt(origin)
    sales.loc[future, 'quantity'] = 9999
    sales.loc[future, ['validity_days', 'unit_price_vnd']] = '9999'
    sales.loc[future, 'customer_id'] = 'fake-changed-future'
    sales.loc[future, 'customer_type'] = 'new'
    actual_x, actual_y = cohort_training(daily, sales, [KEY], origin, 60, 14)
    pd.testing.assert_frame_equal(x, actual_x); np.testing.assert_array_equal(y, actual_y)
    np.testing.assert_array_equal(expected[KEY], predict_cohort(model, daily, sales, [KEY], origin, cfg)[KEY])


def test_training_order_features_equal_inference_at_same_origin():
    daily, sales, _, _ = fixture(); cutoff = pd.Timestamp('2024-04-19')
    x, y = cohort_training(daily, sales, [KEY], cutoff, 60, 14)
    for h in [1, 7, 14]:
        target = pd.Timestamp('2024-04-10'); origin = target - pd.Timedelta(days=h)
        ctx = prepare_cohort(daily, sales, [KEY], origin)[KEY]
        expected = cohort_features(ctx, [len(ctx['values']) - 1], h)
        selected = x.loc[x.horizon_day.eq(h) & x.target_elapsed_days.eq((target - pd.Timestamp('2024-01-01')).days)]
        pd.testing.assert_frame_equal(selected.reset_index(drop=True), expected)
        assert y[selected.index[0]] == daily.loc[daily.date.eq(target), 'sales_qty'].iloc[0]


def test_invalid_price_validity_and_unknown_customer_are_missing_covariates_not_lost_sales():
    daily, sales, _, cfg = fixture(); origin = pd.Timestamp('2024-03-19')
    sales.loc[sales.date.eq(origin), 'unit_price_vnd'] = 'invalid'
    sales.loc[sales.date.eq(origin), 'validity_days'] = '1.5'
    sales.loc[sales.date.eq(origin), 'money_valid'] = False
    sales.loc[sales.date.eq(origin), 'customer_id'] = ''
    ctx = prepare_cohort(daily, sales, [KEY], origin)[KEY]
    x = cohort_features(ctx, [len(ctx['values']) - 1], 1)
    assert x.unit_price_mean28.isna().all() and x.validity_due_proxy.isna().all()
    assert x.first_seen_mean7.iloc[0] == 0
    model = fit_cohort(daily, sales, [KEY], origin, 60, 'mape', cfg)
    assert np.isfinite(predict_cohort(model, daily, sales, [KEY], origin, cfg)[KEY]).all()
    assert len(daily) == 110 and len(sales) == 110


def test_activation_is_not_a_cohort_feature_or_sale_filter():
    daily, sales, _, _ = fixture()
    x, y = cohort_training(daily, sales, [KEY], '2024-03-20', 60, 14)
    sales['activation_datetime'] = '2099-01-01T00:00:00Z'
    changed_x, changed_y = cohort_training(daily, sales, [KEY], '2024-03-20', 60, 14)
    pd.testing.assert_frame_equal(x, changed_x); np.testing.assert_array_equal(y, changed_y)


@pytest.mark.parametrize('loss', ['mape', 'poisson'])
def test_all_zero_training_and_missing_audited_sales(loss):
    daily, sales, _, cfg = fixture(); daily['sales_qty'] = 0.
    model = fit_cohort(daily, sales, [KEY], '2024-03-19', 60, loss, cfg)
    np.testing.assert_array_equal(predict_cohort(model, daily, sales, [KEY], '2024-03-19', cfg)[KEY], np.zeros(14))
    with pytest.raises(ValueError, match='audited sales'):
        prepare_cohort(daily, None, [KEY], '2024-03-19')


def test_integrated_selected_test_and_forecast_have_no_future_labels_or_features():
    daily, sales, top, cfg = fixture()
    result, logs = cohort_rolling(daily, sales, top, cfg, ['cohort_365_mape'], 'validation', lambda _: None)
    assert len(result) == 28 and result.loc[result.target_date.gt(cfg['validation_end']), 'actual_qty'].isna().all()
    assert logs.max_label_date.le(pd.Timestamp('2024-03-19')).all()
    selected = top.assign(model='cohort_365_mape', fallback_model='ma7')
    backtest, _ = selected_backtest(daily, selected, top, cfg, sales=sales)
    assert len(backtest) == 28 and backtest.model.eq('selected').all()
    cfg['validation_end'] = '2024-03-19'
    before = forecast_at(daily, selected, top, '2024-03-19', cfg, sales=sales)
    daily.loc[daily.date.gt('2024-03-19'), 'sales_qty'] = 1e6
    sales.loc[sales.date.gt('2024-03-19'), 'customer_id'] = 'fake-future'
    after = forecast_at(daily, selected, top, '2024-03-19', cfg, sales=sales)
    np.testing.assert_array_equal(before.forecast_qty, after.forecast_qty)
