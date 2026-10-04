import numpy as np
import pandas as pd
import pytest
from src.context_models import prepare_context,context_features,context_training

def fixture_daily():
    dates=pd.date_range('2024-01-01',periods=120)
    return pd.concat([pd.DataFrame({'date':dates,'destination_country':country,'carrier':carrier,
                         'sales_qty':np.arange(120,dtype=float)+offset})
                      for country,carrier,offset in [('A','a',1),('A','b',2),('B','c',3)]],ignore_index=True)

def test_context_training_cannot_see_other_routes_future():
    daily=fixture_daily();keys=[('A','a')];cutoff=pd.Timestamp('2024-03-20')
    x,y=context_training(daily,keys,cutoff,60,14)
    altered=daily.copy();altered.loc[altered.date.gt(cutoff),'sales_qty']=1e6
    x2,y2=context_training(altered,keys,cutoff,60,14)
    pd.testing.assert_frame_equal(x,x2);np.testing.assert_array_equal(y,y2)
    assert y.max()==80

def test_context_weekday_and_country_features_by_hand():
    daily=fixture_daily();ctx=prepare_context(daily,[('A','a')],'2024-03-20')[('A','a')]
    x=context_features(ctx,[79],3).iloc[0]
    # Wednesday origin, Saturday target. Latest observed Saturday is four days before.
    assert x.weekday_last==76
    assert x.weekday_previous==69
    assert x.lag0==80
    assert x.country_mean7==155
    assert x.global_mean7==234

def test_context_inference_future_changes_do_not_change_features():
    daily=fixture_daily();keys=[('A','a')];origin=pd.Timestamp('2024-03-20')
    ctx=prepare_context(daily,keys,origin)[keys[0]]
    x=context_features(ctx,[79],14)
    daily.loc[daily.date.gt(origin),'sales_qty']=np.nan
    new=prepare_context(daily,keys,origin)[keys[0]]
    pd.testing.assert_frame_equal(x,context_features(new,[79],14))


def test_training_features_align_with_origin_inference():
    daily=fixture_daily();key=('A','a');cutoff=pd.Timestamp('2024-04-29')
    x,y=context_training(daily,[key],cutoff,60,14)
    full=prepare_context(daily,[key],cutoff)[key]
    for h in [1,7,14]:
        target=pd.Timestamp('2024-04-20');origin=target-pd.Timedelta(days=h)
        idx=full['dates'].get_loc(origin)
        expected=context_features(prepare_context(daily,[key],origin)[key],[idx],h)
        selected=x.loc[x.horizon_day.eq(h)&x.target_elapsed_days.eq((target-pd.Timestamp('2024-01-01')).days)]
        pd.testing.assert_frame_equal(selected.reset_index(drop=True),expected)
        assert y[selected.index[0]]==111


@pytest.mark.parametrize('loss',['mape','poisson'])
def test_inactive_training_window_produces_finite_zero_forecast(loss):
    from src.context_models import fit_context
    daily=fixture_daily();daily['sales_qty']=0.
    keys=[('A','a')];cutoff=pd.Timestamp('2024-03-20')
    model=fit_context(daily,keys,cutoff,60,loss,{'horizon':14,'seed':42,'lightgbm_threads':1})
    context=prepare_context(daily,keys,cutoff)[keys[0]]
    prediction=model.predict(context_features(context,[79],14))
    np.testing.assert_array_equal(prediction,[0.])


def test_context_integrated_test_and_forecast_remain_causal():
    from src.models import selected_backtest, forecast_at
    daily=fixture_daily();top=pd.DataFrame({'destination_country':['A'],'carrier':['a']})
    selected=top.assign(model='context_180_mape',fallback_model='ma7')
    cfg={'horizon':14,'seed':42,'lightgbm_threads':1,'refit_days':7,
         'validation_end':'2024-03-19','test_start':'2024-03-20','test_end':'2024-03-21'}
    result,_=selected_backtest(daily,selected,top,cfg)
    assert len(result)==28 and result.model.eq('selected').all()
    assert result.loc[result.target_date.gt(cfg['test_end']),'actual_qty'].isna().all()
    first=forecast_at(daily,selected,top,'2024-03-19',cfg)
    daily.loc[daily.date.gt('2024-03-19'),'sales_qty']=1e6
    altered=forecast_at(daily,selected,top,'2024-03-19',cfg)
    np.testing.assert_array_equal(first.forecast_qty,altered.forecast_qty)
