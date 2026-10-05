"""Past country/global quantity context for direct weekly demand forecasts."""
import numpy as np
import pandas as pd

MACRO_FEATURES = ['country_week7', 'country_mean28_week', 'country_mean90_week',
                  'global_week7', 'global_mean28_week', 'global_mean90_week',
                  'route_country_share90', 'country_prior_year_week7', 'global_prior_year_week7']
MACRO_AMOUNTS = [name for name in MACRO_FEATURES if name != 'route_country_share90']


def prepare_macro(daily):
    values = daily.sales_qty.to_numpy(float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Invalid country/global quantity history')
    countries = {country: group.groupby('date').sales_qty.sum().sort_index()
                 for country, group in daily.groupby('destination_country')}
    total = daily.groupby('date').sales_qty.sum().sort_index()
    return {'countries': countries, 'global': total}


def macro_inputs(context, country, route_y, origins, ends):
    prior = ends - pd.DateOffset(years=1)
    if (prior > origins).any():
        raise ValueError('Country/global prior-year date exceeds origin')
    data = {}
    local = context['countries'][country]
    for prefix, series in [('country', local), ('global', context['global'])]:
        sums = series.rolling(7, min_periods=7).sum()
        data[prefix + '_week7'] = sums.reindex(origins).to_numpy()
        for window in (28, 90):
            data[f'{prefix}_mean{window}_week'] = (series.rolling(window, min_periods=window).mean() * 7).reindex(origins).to_numpy()
        data[prefix + '_prior_year_week7'] = sums.reindex(prior).to_numpy()
    share = route_y.rolling(90, min_periods=90).sum() / local.rolling(90, min_periods=90).sum().clip(lower=1)
    data['route_country_share90'] = share.reindex(origins).to_numpy()
    return pd.DataFrame(data)[MACRO_FEATURES]
