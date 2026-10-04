import numpy as np
import pandas as pd
import pytest
from scipy.stats import poisson
from src.count_models import count_action, fit_count, predict_count, count_rolling


def count_fixture():
    rows=[]
    for i,date in enumerate(pd.date_range('2024-01-01',periods=110)):
        for carrier in ['a','b']:
            for order in range(1+i%4):
                rows.append({'date':date,'destination_country':'Synthetic','carrier':carrier,
                             'quantity':1+(i+order)%2})
    sales=pd.DataFrame(rows)
    daily=sales.groupby(['date','destination_country','carrier']).quantity.agg(sales_qty='sum',order_count='count').reset_index()
    top=pd.DataFrame({'destination_country':['Synthetic']*2,'carrier':['a','b']})
    cfg={'horizon':14,'refit_days':7,'seed':42,'lightgbm_threads':1,
         'validation_start':'2024-03-20','validation_end':'2024-03-21'}
    return daily,sales,top,cfg


def test_arrival_action_matches_independent_poisson_loss_minimum():
    assert count_action([0],{1:1})[0]==0
    y=np.arange(1,201)
    for rate in [1.,3.,10.]:
        probabilities=poisson.pmf(y,rate)
        losses=[np.sum(probabilities*np.abs(y-value)/y) for value in y]
        action=count_action([rate],{1:1})[0]
        assert losses[int(action)-1]==pytest.approx(min(losses),abs=1e-12)


@pytest.mark.parametrize('model',['count_calendar_365','count_context_180'])
def test_arrival_model_and_quantity_distribution_exclude_future(model):
    daily,sales,top,cfg=count_fixture();origin=pd.Timestamp('2024-03-19')
    keys=list(top.itertuples(index=False,name=None))
    state=fit_count(daily,sales,keys,origin,model,cfg)
    before=predict_count(state,daily,keys,origin,cfg)
    daily.loc[daily.date.gt(origin),['order_count','sales_qty']]=1e6
    sales.loc[sales.date.gt(origin),'quantity']=1e6
    after_state=fit_count(daily,sales,keys,origin,model,cfg)
    after=predict_count(after_state,daily,keys,origin,cfg)
    for key in keys:np.testing.assert_array_equal(before[key],after[key])
    assert state['distributions']==after_state['distributions']


def test_arrival_validation_tail_has_no_future_labels():
    daily,sales,top,cfg=count_fixture()
    result,logs=count_rolling(daily,sales,top,cfg,['count_calendar_365'],'validation',lambda _:None)
    assert len(result)==56 and result.forecast_qty.ge(0).all()
    assert result.loc[result.target_date.gt(cfg['validation_end']),'actual_qty'].isna().all()
    assert logs.max_label_date.le(pd.Timestamp('2024-03-19')).all()


def test_arrival_distribution_rejects_invalid_or_material_tail():
    with pytest.raises(ValueError,match='Invalid historical'):
        count_action([1],{1:.5})
    with pytest.raises(ValueError,match='truncation'):
        count_action([100],{4:1})
