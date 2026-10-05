"""Fixed calendar-day commitments, causal backlog and unchanged sales units."""
import numpy as np
import pandas as pd
import pytest

from sigma.delivery.customer import commitments, projection, delivery_settings


def orders():
    return pd.DataFrame({'destination_country': ['Fake'] * 3, 'carrier': ['A'] * 3,
        'sku': ['S'] * 3, 'product_type': ['data'] * 3,
        'order_datetime': ['2025-06-27T12:30:00Z', '2025-06-30T23:00:00Z', '2025-07-01T00:00:00Z'],
        'quantity': [2, 3, 100]})


def allocation():
    return pd.DataFrame({'destination_country': ['Fake'] * 14, 'carrier': ['A'] * 14,
        'as_of_date': pd.Timestamp('2025-06-30'),
        'target_date': pd.date_range('2025-07-01', periods=14),
        'forecast_qty': np.arange(1., 15.)})


def test_fixed_seven_days_includes_weekend_and_conserves_quantity():
    result = commitments(orders())
    assert result.delivery_date.tolist() == list(pd.to_datetime(['2025-07-04', '2025-07-07', '2025-07-08']))
    assert result.commitment_qty.sum() == 105
    assert not {'order_id', 'customer_id'}.intersection(result.columns)
    assert result.customer_delay_days.eq(0).all()


def test_delivery_date_uses_utc_across_local_midnight():
    data = orders().iloc[[0]].copy()
    data['order_datetime'] = '2025-06-30T23:30:00-04:00'
    result = commitments(data)
    assert result.order_date.iloc[0] == pd.Timestamp('2025-07-01')
    assert result.delivery_date.iloc[0] == pd.Timestamp('2025-07-08')


def test_known_next_week_never_uses_future_orders():
    a = projection(orders(), allocation(), '2025-06-30')
    changed = orders(); changed.loc[2, 'quantity'] = 999999
    b = projection(changed, allocation(), '2025-06-30')
    pd.testing.assert_frame_equal(a, b)
    assert a.known_commitment_qty.sum() == 5
    assert len(a) == 21 and a.actual_delivered_qty.isna().all()
    assert a.order_date.notna().all() and (a.delivery_date - a.order_date).dt.days.eq(7).all()
    assert a.loc[a.delivery_horizon_day.le(7), 'planned_delivery_qty'].sum() == 5
    assert a.forecast_from_future_orders_qty.sum() == 105
    assert a.loc[a.delivery_date.eq('2025-07-08'), 'planned_delivery_qty'].iloc[0] == 1
    assert a.loc[a.delivery_date.eq('2025-07-21'), 'planned_delivery_qty'].iloc[0] == 14


@pytest.mark.parametrize('problem', ['missing_day', 'stale_origin', 'negative', 'duplicate'])
def test_delivery_projection_rejects_invalid_forecast(problem):
    data = allocation()
    if problem == 'missing_day':
        data = data.drop(index=4)
    elif problem == 'stale_origin':
        data.loc[4, 'as_of_date'] = pd.Timestamp('2025-06-29')
    elif problem == 'negative':
        data.loc[4, 'forecast_qty'] = -1
    else:
        data = pd.concat([data, data.iloc[[4]]])
    with pytest.raises(ValueError):
        projection(orders(), data, '2025-06-30')


def test_customer_setting_does_not_change_supplier_lead_time():
    cfg = delivery_settings()
    assert cfg['customer_delivery_days'] == 7 and cfg['customer_delay_days'] == 0
    assert cfg['supplier_lead_time_modified'] is False
