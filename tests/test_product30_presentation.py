import numpy as np
import pandas as pd
import pytest

from sigma.ui.product30_support import (complete_actual, demand_chart_data,
    ranked_recommendations, ledger_timeline, timeline_metrics, scenario_comparison,
    item_parameters, number)


def daily_fixture():
    return pd.DataFrame([{'destination_country':'Synthetic','carrier':carrier,'date':date,'sales_qty':qty}
        for carrier,qty in [('One',2),('Two',3)] for date in pd.date_range('2025-01-01',periods=6)])


def test_actual_requires_complete_routes_and_days():
    daily=daily_fixture()
    assert complete_actual(daily,'2025-01-02','2025-01-04')==15
    assert complete_actual(daily,'2025-01-04','2025-01-08') is None
    assert complete_actual(daily.drop(index=2),'2025-01-01','2025-01-06') is None
    with pytest.raises(ValueError):
        complete_actual(pd.concat([daily.iloc[:5],daily.iloc[[0]],daily.iloc[6:]]),'2025-01-01','2025-01-06')


def test_plot_keeps_unobserved_future_missing_and_total_allocation():
    daily=daily_fixture()
    forecast=pd.DataFrame({'target_date':pd.to_datetime(['2025-01-07','2025-01-08']), 'forecast_qty':[4.,8.]})
    result=demand_chart_data(daily,forecast,'2025-01-06')
    observed=result.loc[result.series.eq('Số bán đã quan sát')]
    allocated=result.loc[result.series.eq('Phân bổ từ dự báo tổng')]
    assert observed.date.max()==pd.Timestamp('2025-01-06')
    assert allocated.quantity.sum()==12 and allocated.date.min()==pd.Timestamp('2025-01-07')


def test_priority_keeps_policy_quantities_and_moves_empty_first():
    frame=pd.DataFrame({'destination_country':['Synthetic']*3,'carrier':['One']*3,
        'sku':['A','B','C'],'product_type':['eSIM']*3,'on_hand':[20,0,2],
        'Q':[100,0,3],'needs_replenishment':[True,True,True],
        'depletion_state':['early','already_empty','urgent']})
    result=ranked_recommendations(frame)
    assert result.sku.tolist()==['B','C','A']
    assert dict(zip(result.sku,result.Q))==dict(zip(frame.sku,frame.Q))


def test_chunked_timeline_conserves_demand_service_stock_and_scenario_scope(tmp_path):
    rows=[]
    for scene,shortage in [('base',0),('partial_receipt',1)]:
        for date in pd.date_range('2025-01-01',periods=2):
            for carrier in ['One','Two']:
                for sku in ['A','B']:
                    rows.append({'scenario_id':scene,'date':date,'destination_country':'Synthetic',
                        'carrier':carrier,'sku':sku,'scenario_demand':2,'fulfilled':2-shortage,'shortage':shortage,'closing':3})
    path=tmp_path/'synthetic.csv';pd.DataFrame(rows).to_csv(path,index=False)
    timeline=ledger_timeline(path,chunksize=3)
    metrics=scenario_comparison(timeline_metrics(timeline))
    base=metrics.loc[metrics.scenario_id.eq('base')].iloc[0]
    partial=metrics.loc[metrics.scenario_id.eq('partial_receipt')].iloc[0]
    assert base.demand==16 and base.fill_rate==1 and base.mean_closing_on_hand==12
    assert partial.demand==16 and partial.shortage==8 and partial.fill_rate==.5
    assert partial.fill_change_pp==-50 and partial.shortage_change==8
    filtered=timeline_metrics(timeline.loc[timeline.carrier.eq('One')])
    assert filtered.demand.eq(8).all() and filtered.mean_closing_on_hand.eq(6).all()


def test_sensitivity_uses_its_own_partner_parameters():
    configs=[{'scenario':{'name':'base'},'inventory':{'partners':{'Synthetic':{'lead_time_days':3}}}},
        {'scenario':{'name':'sensitivity_lead_7'},'inventory':{'partners':{'Synthetic':{'lead_time_days':7}}}}]
    assert item_parameters(configs,{'scenario_id':'sensitivity_lead_7','partner_id':'Synthetic'})['lead_time_days']==7


@pytest.mark.parametrize('value,decimals,expected',[(6027.503,1,'6.027,5'),(None,0,'—'),(np.nan,2,'—')])
def test_vietnamese_numbers_keep_unknown_separate_from_zero(value,decimals,expected):
    assert number(value,decimals)==expected
