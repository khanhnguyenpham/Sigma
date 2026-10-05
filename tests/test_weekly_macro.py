import numpy as np
import pandas as pd

from weekly_macro import prepare_macro, macro_inputs


def sample():
    dates = pd.date_range('2024-01-01', '2025-09-30')
    return pd.concat([pd.DataFrame({'date': dates, 'destination_country': country,
        'carrier': carrier, 'sales_qty': qty}) for country, carrier, qty in
        [('Fake', 'A', 2.), ('Fake', 'B', 6.), ('Other', 'A', 12.)]], ignore_index=True)


def test_weekly_macro_country_global_and_share_are_quantity_units():
    daily = sample(); origin = pd.DatetimeIndex(['2025-06-30'])
    ends = origin + pd.Timedelta(days=7)
    route = daily.loc[daily.destination_country.eq('Fake') & daily.carrier.eq('A')].set_index('date').sales_qty
    x = macro_inputs(prepare_macro(daily), 'Fake', route, origin, ends).iloc[0]
    assert x.country_week7 == 56. and x.global_week7 == 140.
    assert x.country_mean90_week == 56. and x.global_mean28_week == 140.
    assert x.route_country_share90 == .25
    assert x.country_prior_year_week7 == 56. and x.global_prior_year_week7 == 140.


def test_weekly_macro_features_ignore_future_routes_quantities():
    daily = sample(); origins = pd.date_range('2025-04-01', '2025-06-30')
    route = daily.loc[daily.destination_country.eq('Fake') & daily.carrier.eq('A')].set_index('date').sales_qty
    ends = origins + pd.Timedelta(days=14)
    a = macro_inputs(prepare_macro(daily), 'Fake', route, origins, ends)
    changed = daily.copy(); changed.loc[changed.date.gt(origins.max()), 'sales_qty'] = 999999.
    b = macro_inputs(prepare_macro(changed), 'Fake', route, origins, ends)
    pd.testing.assert_frame_equal(a, b)
    np.testing.assert_array_less(a.route_country_share90.to_numpy(), np.ones(len(a)))
