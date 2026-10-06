"""New estimators, causal scaling/calibration and month-bounded evaluation."""
import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from M2.models.common import active_variants, effective_settings
from M2.models.registry import load_settings
from M2.models.families import ts_job, monthly_metrics
from M2.models.LightGBM.model import prepare_daily, daily_inputs, daily_lgbm_fit, phase
from M2.models.verify import reconcile_calibration, reconcile_metrics
from M2.models.tests.test_model_families import fixture


def test_registered_budget_target_specific_variants_and_per_variant_settings():
    settings=load_settings(ROOT/'M2/models/model_families.json')
    assert sum(len(active_variants(settings,f,t)) for f in settings['models'] for t in ('daily','direct_7d'))==50
    assert len(settings['models']['LightGBM'])==10
    assert all(s.get('kind')!='calibrated' for s in active_variants(settings,'LightGBM','daily').values())
    changed=effective_settings(settings,{'training_window_days':180,'n_estimators':300,'min_child_samples':50})
    assert (changed['training_window_days'],changed['n_estimators'],changed['min_child_samples'])==(180,300,50)
    assert settings['training_window_days']==365 and settings['n_estimators']==150


@pytest.mark.parametrize('family,model',[
    ('SARIMA','arima_101'),('SARIMA','arima_111'),
    ('SARIMA','sarima_100_100_7_window180'),('SARIMA','sarimax_annual_100_100_7_window540'),
    ('Prophet','prophet_no_annual_weekly_w365'),('Prophet','prophet_no_annual_no_weekly_w365'),
    ('Prophet','prophet_annual3_weekly_w540'),('Prophet','prophet_annual3_no_weekly_w540')])
@pytest.mark.parametrize('target',['daily','direct_7d'])
def test_new_ts_variants_ignore_future(family,model,target):
    series,cfg,settings=fixture()
    cfg['validation_end']=cfg['validation_start']
    origin=pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    altered=series.copy(); altered.loc[altered.index>origin]=999999.
    spec=settings['models'][family][model]
    a,log=ts_job(series,('Fake','A'),family,target,model,spec,cfg,settings,'validation')
    b,_=ts_job(altered,('Fake','A'),family,target,model,spec,cfg,settings,'validation')
    assert np.isfinite(a.forecast_qty).all(),log.to_dict('records')
    np.testing.assert_allclose(a.forecast_qty,b.forecast_qty,rtol=0,atol=1e-8)
    assert log.loc[log.status.eq('ok'),'max_label_end'].max()<=origin


def daily_frame(series):
    return pd.DataFrame({'date':series.index,'sales_qty':series.to_numpy(),'order_count':series.to_numpy(),
                         'destination_country':'Fake','carrier':'A'})


def test_daily_ratio_uses_past_scale_and_restores_original_quantity():
    series,cfg,settings=fixture(); series[:]=20.
    cutoff=pd.Timestamp('2024-06-30');spec=settings['models']['LightGBM']['lgbm_annual_ratio7']
    prepared=prepare_daily({('Fake','A'):series})
    table=prepared[(('Fake','A'),7)];idx=np.flatnonzero(table['origins']==cutoff)
    assert table['scale'][idx].item()==20.
    assert daily_inputs(table,spec,idx).lag0.item()==1.
    cfg['validation_end']=cfg['validation_start']
    small={**settings,'models':{'LightGBM':{'ratio':spec}}}
    a,_=phase(daily_frame(series),{('Fake','A'):series},cfg,small,'daily','validation')
    np.testing.assert_allclose(a.forecast_qty,20.,rtol=0,atol=1e-8)
    altered=series.copy(); altered.loc[altered.index>cutoff]=999999.
    b,_=phase(daily_frame(altered),{('Fake','A'):altered},cfg,small,'daily','validation')
    np.testing.assert_array_equal(a.forecast_qty,b.forecast_qty)


@pytest.mark.parametrize('target',['daily','direct_7d'])
def test_lightgbm_new_budget_and_window_take_effect(target):
    series,cfg,settings=fixture();cfg['validation_end']=cfg['validation_start']
    spec={**settings['models']['LightGBM']['lgbm_annual_ratio7'],'n_estimators':17,'min_child_samples':5,'training_window_days':100}
    cutoff=pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    if target=='daily':
        model,log=daily_lgbm_fit(prepare_daily({('Fake','A'):series}),cutoff,spec,cfg,settings)
    else:
        from sigma.forecasting.weekly import prepare
        from M2.models.LightGBM.model import weekly_fit
        spec={**spec,'kind':'lgbm'}
        weekly={**settings,'blocks':[1,2],'models':{'ratio':spec}}
        model,log=weekly_fit(prepare(daily_frame(series),weekly),cutoff,spec,cfg,weekly)
    assert model.get_params()['n_estimators']==17 and model.get_params()['min_child_samples']==5
    assert log['max_label_end']<=cutoff and log['training_pairs']>0


def test_calibration_teacher_and_head_are_causal_and_tampering_is_detected():
    series,cfg,settings=fixture()
    parent='lgbm_annual_ratio7';child='lgbm_cal_ratio7_56_p4'
    specs={name:settings['models']['LightGBM'][name] for name in (parent,child)}
    small={**settings,'minimum_history_days':90,'models':{'LightGBM':specs}}
    groups={('Fake','A'):series}
    a,log=phase(daily_frame(series),groups,cfg,small,'direct_7d','validation')
    assert reconcile_calibration(log,a,groups,specs)==4
    labels=series.rolling(7,min_periods=7).sum()
    expected=labels.reindex(a.target_date).to_numpy(copy=True)
    expected[a.target_date.gt(pd.Timestamp(cfg['validation_end'])).to_numpy()]=np.nan
    np.testing.assert_allclose(a.actual_qty,expected,rtol=0,atol=0,equal_nan=True)
    cfg['validation_end']=cfg['validation_start']
    a,log=phase(daily_frame(series),groups,cfg,small,'direct_7d','validation')
    origin=pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    altered=series.copy();altered.loc[altered.index>origin]=999999.
    b,other=phase(daily_frame(altered),{('Fake','A'):altered},cfg,small,'direct_7d','validation')
    np.testing.assert_allclose(a.forecast_qty,b.forecast_qty,rtol=0,atol=1e-8)
    pd.testing.assert_frame_equal(log,other)
    corrupt=log.copy();corrupt.loc[corrupt.status.eq('calibration'),'factor']=999.
    with pytest.raises(AssertionError):
        reconcile_calibration(corrupt,a,groups,specs)
    corrupt=log.copy();corrupt.loc[corrupt.status.eq('teacher'),'max_label_end']=pd.Timestamp('2025-01-01')
    with pytest.raises(AssertionError):
        reconcile_calibration(corrupt,a,groups,specs)


def test_monthly_metrics_keep_windows_within_month_and_global_cadence():
    cfg={'validation_start':'2025-07-01','validation_end':'2025-09-30','mape_limit_pct':20.}
    origins=pd.date_range('2025-06-30','2025-09-29')
    frame=pd.DataFrame({'destination_country':'Fake','carrier':'A','family':'SARIMA','target':'direct_7d',
        'model':'x','split':'validation','block':1,'as_of_date':origins,'target_date':origins+pd.Timedelta(days=7),
        'actual_qty':10.,'forecast_qty':12.})
    table=monthly_metrics(frame,cfg)
    assert set(table.month)=={'2025-07','2025-08','2025-09'}
    august=table.loc[table.month.eq('2025-08')&table.cadence.eq('nonoverlapping_7d')].iloc[0]
    assert august.n_expected==3 and august.mape_positive_pct==pytest.approx(20.)
    for month,part in table.groupby('month'):
        period=pd.Period(month,freq='M')
        scoped=frame.loc[frame.as_of_date.ge(period.start_time-pd.Timedelta(days=1))&frame.as_of_date.lt(period.end_time.normalize())]
        assert reconcile_metrics(scoped,part,{**cfg,'validation_end':period.end_time.normalize()})==2
