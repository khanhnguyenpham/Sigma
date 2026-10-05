import numpy as np
import pandas as pd
import pytest
from src.monthly_lad import fit_monthly_lad, predict_monthly_lad
from src.count_models import monthly_calendar


@pytest.mark.parametrize('model', ['monthlad_0_0p001','scaledmonthlad_0_0p001'])
def test_scaler_and_monthly_loss_use_only_origin_history(model):
    dates=pd.date_range('2024-01-01',periods=130)
    history=pd.Series(3+np.arange(130)%5,index=dates,dtype=float)
    origin=dates[99];targets=pd.date_range(origin+pd.Timedelta(days=1),periods=14)
    before=fit_monthly_lad(history,origin,model)
    changed=history.copy();changed.loc[changed.index>origin]=1e9
    after=fit_monthly_lad(changed,origin,model)
    np.testing.assert_allclose(predict_monthly_lad(before,targets),predict_monthly_lad(after,targets),atol=1e-12,rtol=0)
    assert before['training_rows']==100
    if model.startswith('scaled'):
        np.testing.assert_allclose(before['estimator'].named_steps['standardscaler'].mean_,
                                   monthly_calendar(dates[:100]).mean(axis=0),atol=1e-12,rtol=0)


def test_monthly_quantity_units_zero_missing_and_future_fit():
    dates=pd.date_range('2024-01-01',periods=100);targets=pd.date_range('2024-04-10',periods=14)
    history=pd.Series(30.,index=dates)
    state=fit_monthly_lad(history,dates[-1],'scaledmonthlad_0_0p001')
    np.testing.assert_allclose(predict_monthly_lad(state,targets),30,atol=1e-10)
    zero=fit_monthly_lad(history*0,dates[-1],'scaledmonthlad_0_0p001')
    np.testing.assert_array_equal(predict_monthly_lad(zero,targets),np.zeros(14))
    history.iloc[0]=np.nan
    with pytest.raises(ValueError,match='complete'):fit_monthly_lad(history,dates[-1],'scaledmonthlad_0_0p001')
    with pytest.raises(ValueError,match='follow'):predict_monthly_lad(state,dates[-5:])


def test_monthly_selected_dispatch_horizon_and_zero_day_evaluation():
    from src.models import rolling_route,selected_backtest,forecast_at
    days=pd.date_range('2024-01-01',periods=120);values=4+np.arange(120)%3;values[30]=0
    series=pd.Series(values,index=days,dtype=float)
    daily=pd.DataFrame({'date':days,'destination_country':'Synthetic','carrier':'fake','sales_qty':values})
    top=daily[['destination_country','carrier']].drop_duplicates();selected=top.assign(model='scaledmonthlad_0_0p001',fallback_model='ma7')
    cfg={'horizon':14,'refit_days':7,'validation_end':'2024-03-19','test_start':'2024-03-20','test_end':'2024-03-21'}
    predictions,_=selected_backtest(daily,selected,top,cfg)
    assert len(predictions)==28 and predictions.model.eq('selected').all()
    assert predictions.loc[predictions.target_date.gt(cfg['test_end']),'actual_qty'].isna().all()
    forecast=forecast_at(daily,selected,top,'2024-03-19',cfg)
    assert len(forecast)==14 and forecast.forecast_qty.ge(0).all()
