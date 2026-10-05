import numpy as np
import pandas as pd
import pytest

from src.hierarchical_models import fit_hierarchical, predict_hierarchical, route_shares


def fixture():
    dates = pd.date_range('2024-01-01', periods=110)
    sales = pd.DataFrame([{'date': day, 'destination_country': 'Synthetic', 'carrier': carrier,
                          'quantity': 1 + i % 2}
                         for i, day in enumerate(dates) for carrier in ['a', 'b'] for _ in range(1 + i % 4)])
    daily = sales.groupby(['date', 'destination_country', 'carrier']).quantity.agg(sales_qty='sum', order_count='count').reset_index()
    keys = [('Synthetic', 'a'), ('Synthetic', 'b')]
    return daily, sales, keys, {'horizon': 14, 'refit_days': 7}


@pytest.mark.parametrize('model', ['hiercount_365_share90', 'hiercount_all_share180'])
def test_hierarchical_future_mutation_does_not_change_forecast(model):
    daily, sales, keys, cfg = fixture(); origin = pd.Timestamp('2024-03-19')
    state = fit_hierarchical(daily, sales, keys, origin, model, cfg)
    before = predict_hierarchical(state, daily, keys, origin, cfg)
    daily.loc[daily.date.gt(origin), ['sales_qty', 'order_count']] = 1e6
    sales.loc[sales.date.gt(origin), 'quantity'] = 1e6
    changed = fit_hierarchical(daily, sales, keys, origin, model, cfg)
    after = predict_hierarchical(changed, daily, keys, origin, cfg)
    for key in keys: np.testing.assert_array_equal(before[key], after[key])
    assert state['distributions'] == changed['distributions']


def test_hierarchical_shares_preserve_aggregate_and_handle_unseen_month():
    # Known 3:1 proportions; July has not yet occurred in this snapshot.
    past = pd.DataFrame([{'date': day, 'destination_country': 'Synthetic', 'carrier': carrier, 'order_count': count}
                         for day in pd.date_range('2024-01-01', periods=20) for carrier, count in [('a', 3), ('b', 1)]])
    shares = route_shares(past, pd.Timestamp('2024-01-20'), 90, pd.to_datetime(['2024-01-21', '2024-07-01']))
    np.testing.assert_allclose(shares[('Synthetic', 'a')], [.75, .75], atol=1e-12)
    np.testing.assert_allclose(shares[('Synthetic', 'b')], [.25, .25], atol=1e-12)
    np.testing.assert_allclose(sum(shares.values()), [1, 1], atol=1e-12)


def test_hierarchical_missing_counts_rejected_and_all_zero_is_zero():
    daily, sales, keys, cfg = fixture(); origin = pd.Timestamp('2024-03-19')
    changed = daily.copy(); changed.loc[0, 'order_count'] = np.nan
    with pytest.raises(ValueError, match='Incomplete'): fit_hierarchical(changed, sales, keys, origin, 'hiercount_365_share90', cfg)
    changed = daily.assign(actual_available=True); changed.loc[0, 'actual_available'] = False
    with pytest.raises(ValueError, match='Missing actual'): fit_hierarchical(changed, sales, keys, origin, 'hiercount_365_share90', cfg)
    changed = daily.assign(order_count=0, sales_qty=0)
    state = fit_hierarchical(changed, sales.iloc[:0], keys, origin, 'hiercount_365_share90', cfg)
    assert all((vector == 0).all() for vector in predict_hierarchical(state, changed, keys, origin, cfg).values())
    with pytest.raises(ValueError, match='fitted after'): predict_hierarchical(state, daily, keys, origin-pd.Timedelta(days=1), cfg)


def test_hierarchical_selected_backtest_and_forecast_dispatch():
    from src.models import selected_backtest, forecast_at
    daily, sales, keys, cfg = fixture()
    top = pd.DataFrame(keys, columns=['destination_country', 'carrier'])
    selected = top.assign(model='hiercount_all_share180', fallback_model='ma7')
    cfg.update(test_start='2024-03-20', test_end='2024-03-21', validation_end='2024-03-19')
    predictions, logs = selected_backtest(daily, selected, top, cfg, sales=sales)
    assert len(predictions) == 56 and predictions.model.eq('selected').all()
    assert predictions.loc[predictions.target_date.gt(cfg['test_end']), 'actual_qty'].isna().all()
    assert logs.max_label_date.le(pd.Timestamp('2024-03-19')).all()
    forecast = forecast_at(daily, selected, top, '2024-03-19', cfg, sales=sales)
    assert len(forecast) == 28 and forecast.forecast_qty.ge(0).all()
