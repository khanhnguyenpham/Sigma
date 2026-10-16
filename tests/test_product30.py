from copy import deepcopy

import numpy as np
import pandas as pd

from sigma.delivery.customer import projection
from sigma.inventory.product30 import business_signals
from src.inventory import run_policy, AllocationPlan
from src.inventory import replenishment


def test_customer_delivery_30day_forecast_has_37_days_and_known_first_week():
    origin=pd.Timestamp('2025-09-30')
    sales=pd.DataFrame({'destination_country':['Syntheticland'],'carrier':['Syntheticcarrier'],
        'sku':['SYN'],'product_type':['eSIM'],'order_datetime':['2025-09-30T23:00:00Z'],'quantity':[3]})
    forecast=pd.DataFrame({'destination_country':'Syntheticland','carrier':'Syntheticcarrier',
        'as_of_date':origin,'target_date':pd.date_range('2025-10-01',periods=30),'forecast_qty':2.})
    result=projection(sales,forecast,origin,horizon=30)
    assert len(result)==37 and result.actual_delivered_qty.isna().all()
    assert result.loc[result.delivery_horizon_day.le(7),'forecast_from_future_orders_qty'].sum()==0
    assert result.loc[result.delivery_date.eq('2025-10-07'),'known_commitment_qty'].iloc[0]==3
    assert result.forecast_from_future_orders_qty.sum()==60
    assert result.customer_delay_days.eq(0).all()


def test_revenue_drop_is_not_quantity_drop_and_missing_money_stays_missing():
    days=pd.date_range('2025-01-01',periods=50)
    daily=pd.DataFrame({'date':days,'destination_country':'Syntheticland','carrier':'Syntheticcarrier',
        'sales_qty':10.,'order_count':10,'gross_revenue_vnd':1000.})
    daily.loc[40,'gross_revenue_vnd']=400
    daily.loc[41,'gross_revenue_vnd']=np.nan
    result=business_signals(None,daily)
    assert result.loc[40,'revenue_drop_observed'] and not result.loc[40,'quantity_drop_observed']
    assert pd.isna(result.loc[41,'gross_revenue_vnd'])
    assert result.loc[40,'revenue_prior28_mean']==1000
    assert result.loc[40,'quantity_change_fraction']==0


def test_thirty_day_policy_keeps_strict_trigger_and_does_not_repeat_pending_order(cfg):
    cfg=deepcopy(cfg);cfg.update(observation_start='2025-09-01',observation_end='2025-10-03',
        test_start='2025-10-01',test_end='2025-10-03',forecast_origin='2025-10-03',horizon=30)
    key=('Syntheticland','Syntheticcarrier','SYN','eSIM')
    cfg['inventory'].update(initial_cover_days=2,partner_map={'Syntheticcarrier':'partner'},
        partners={'partner':{'lead_time_days':3,'review_days':1,'safety_days':2,'moq':1}},initial_receipts=[])
    days=pd.date_range(cfg['observation_start'],cfg['observation_end'])
    matrix=pd.DataFrame(np.ones((len(days),1)),index=days,columns=pd.MultiIndex.from_tuples([key]))
    forecasts=[]
    for origin in pd.date_range('2025-09-30','2025-10-03'):
        for h in range(1,31):
            forecasts.append({'destination_country':key[0],'carrier':key[1],'as_of_date':origin,
                'target_date':origin+pd.Timedelta(days=h),'horizon_day':h,'forecast_qty':1.})
    forecasts=pd.DataFrame(forecasts)
    stress={'name':'base','demand_multiplier':1.,'receipt_fraction':1.,'receipt_delay_days':0}
    ledger,recs,issues=run_policy(matrix,forecasts,cfg,stress,allocation_plan=AllocationPlan(matrix,forecasts,cfg))
    assert issues.empty and len(ledger)==3
    assert recs.iloc[0].Q==5 and recs.iloc[0].ROP==5
    assert recs.iloc[-1].Q==0 and recs.iloc[-1].IP==6
    assert recs.iloc[-1].needs_replenishment and recs.iloc[-1].status=='incoming_covers_order'
    assert ledger.shortage.sum()==1
    assert ledger.closing.eq(ledger.opening+ledger.receipts-ledger.fulfilled).all()


def test_csv_roundtrip_preserves_threshold_at_integer_boundary(tmp_path):
    value=np.nextafter(.5,1.)
    original=pd.DataFrame({'forecast_qty':[value]*30})
    path=tmp_path/'synthetic_allocation.csv';original.to_csv(path,index=False)
    loaded=pd.read_csv(path,float_precision='round_trip')
    np.testing.assert_array_equal(loaded.forecast_qty,original.forecast_qty)
    params={'lead_time_days':3,'review_days':1,'safety_days':2,'moq':1}
    assert replenishment(0,loaded.forecast_qty,0,params)==replenishment(0,original.forecast_qty,0,params)
