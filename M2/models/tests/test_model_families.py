"""Hand-calculated windows, real estimator leakage checks and selection lock rules."""
import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from M2.models.families import (target_history, prediction_rows, aggregate_daily,
    prepare_daily, daily_lgbm_fit, ts_job, metrics, select)
from M2.models.registry import load_settings
from sigma.forecasting.weekly import prepare, fit, predict_batch


def fixture():
    settings = load_settings(ROOT/'M2/models/model_families.json')
    settings.update(training_window_days=150, minimum_history_days=30, n_estimators=12)
    dates = pd.date_range('2024-01-01', periods=220)
    values = np.random.default_rng(42).poisson(8+2*np.sin(np.arange(220)*2*np.pi/7)).astype(float)
    series = pd.Series(values,index=dates)
    cfg = {'seed':42, 'lightgbm_threads':1, 'mape_limit_pct':20,
        'validation_start':'2024-07-01', 'validation_end':'2024-07-09'}
    return series, cfg, settings


def test_end_dated_total_and_future_are_not_next_step_or_partial_labels():
    series = pd.Series(np.arange(1,41,dtype=float),index=pd.date_range('2024-01-01',periods=40))
    origin = pd.Timestamp('2024-01-20')
    hist = target_history(series,'direct_7d',origin,{'training_window_days':365,'minimum_history_days':7})
    assert hist.iloc[-1] == sum(range(14,21)) == 119
    rows = prediction_rows(series,('Fake','A'),'SARIMA','direct_7d','x','validation',origin,
                           pd.Timestamp('2024-01-30'),[168,217])
    assert rows[0]['actual_qty'] == sum(range(21,28)) == 168
    assert rows[0]['target_date'] == pd.Timestamp('2024-01-27')
    assert rows[0]['window_start'] == pd.Timestamp('2024-01-21')
    assert np.isnan(rows[1]['actual_qty'])  # seven days must all be within the split
    future = prediction_rows(series,('Fake','A'),'Prophet','daily','x','future',series.index.max(),series.index.max(),np.ones(14))
    assert all(np.isnan(row['actual_qty']) for row in future)


@pytest.mark.parametrize('target',['daily','direct_7d'])
@pytest.mark.parametrize('family',['SARIMA','Prophet'])
def test_real_ts_fit_cannot_see_values_after_origin(family,target):
    series,cfg,settings = fixture()
    cfg['validation_end'] = cfg['validation_start']
    altered = series.copy()
    origin = pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    altered.loc[altered.index>origin] = 999999.
    model = next(iter(settings['models'][family]))
    spec = settings['models'][family][model]
    a, log = ts_job(series,('Fake','A'),family,target,model,spec,cfg,settings,'validation')
    b, _ = ts_job(altered,('Fake','A'),family,target,model,spec,cfg,settings,'validation')
    assert np.isfinite(a.forecast_qty).all(), log.to_dict('records')
    np.testing.assert_allclose(a.forecast_qty,b.forecast_qty,rtol=0,atol=1e-8)
    fits = log.loc[log.status.eq('ok')]
    assert (fits.max_label_end<=fits.fit_cutoff).all()


@pytest.mark.parametrize('target',['daily','direct_7d'])
def test_real_lgbm_labels_and_features_ignore_future(target):
    series,cfg,settings = fixture()
    cutoff = pd.Timestamp('2024-06-30')
    altered=series.copy(); altered.loc[altered.index>cutoff]=999999.
    key=('Fake','A')
    spec=settings['models']['LightGBM']['lgbm_annual_l1']
    if target=='daily':
        a,b=prepare_daily({key:series}),prepare_daily({key:altered})
        m,log=daily_lgbm_fit(a,cutoff,spec,cfg,settings)
        n,other=daily_lgbm_fit(b,cutoff,spec,cfg,settings)
        names=['year_sin','year_cos']
        from src.models import FEATURES
        x=a[(key,7)]['x'].loc[a[(key,7)]['origins']==cutoff,FEATURES+names]
        np.testing.assert_array_equal(m.predict(x),n.predict(x))
    else:
        def frame(y):
            return pd.DataFrame({'date':y.index,'sales_qty':y.to_numpy(),'order_count':y.to_numpy(),
                                 'destination_country':key[0],'carrier':key[1]})
        spec={**spec,'kind':'lgbm','units':'raw'}
        week={**settings,'blocks':[1,2],'models':{'x':spec}}
        a,b=prepare(frame(series),week),prepare(frame(altered),week)
        m,log=fit(a,cutoff,spec,cfg,week); n,other=fit(b,cutoff,spec,cfg,week)
        assert predict_batch(m,a,cutoff,spec)==predict_batch(n,b,cutoff,spec)
    assert log==other and log['max_label_end']<=cutoff


def test_sum_day_alignment_selection_rejects_test_and_incomplete_candidates():
    series,cfg,settings=fixture()
    cfg['validation_end']='2024-07-14'
    origin=pd.Timestamp('2024-06-30')
    rows=prediction_rows(series,('Fake','A'),'LightGBM','daily','a','validation',origin,
                         pd.Timestamp('2024-07-14'),np.arange(1,15))
    frame=pd.DataFrame(rows)
    summed=aggregate_daily(frame)
    assert summed.forecast_qty.tolist()==[28.,77.]
    assert summed.window_start.tolist()==[pd.Timestamp('2024-07-01'),pd.Timestamp('2024-07-08')]
    better=frame.copy(); better['model']='incomplete'; better['forecast_qty']=better.actual_qty
    better.loc[better.index[-1],'forecast_qty']=np.nan  # failure in secondary block also invalidates candidate
    candidates=pd.concat([frame,better],ignore_index=True)
    table=metrics(candidates,cfg)
    assert select(table,candidates,cfg).model.tolist()==['a']
    table['split']='test'
    with pytest.raises(ValueError,match='validation'):
        select(table,candidates,cfg)


def test_independent_verifier_accepts_hand_metrics_and_detects_changed_wape():
    from M2.models.verify import reconcile_metrics
    dates=pd.date_range('2025-07-01',periods=3)
    frame=pd.DataFrame({'destination_country':'Fake','carrier':'A','family':'SARIMA',
        'target':'daily','model':'x','split':'validation','block':1,
        'as_of_date':pd.Timestamp('2025-06-30'),'target_date':dates,
        'actual_qty':[0.,10.,20.],'forecast_qty':[5.,12.,16.]})
    row={'destination_country':'Fake','carrier':'A','family':'SARIMA','target':'daily','model':'x',
        'split':'validation','block':1,'cadence':'daily_origins','mape_positive_pct':20.,
        'mae':11/3,'wape_pct':110/3,'bias':1.,'coverage':1.,'positive_share':2/3,
        'n_expected':3,'n_labeled_pairs':3,'n_scored_pairs':3,'n_positive_pairs':2,
        'n_zero_pairs':1,'unique_target_days':3,'passes_20_pct':True}
    table=pd.DataFrame([row])
    cfg={'validation_start':'2025-07-01','validation_end':'2025-09-30','mape_limit_pct':20.}
    assert reconcile_metrics(frame,table,cfg)==1
    table.loc[0,'wape_pct']=999.
    with pytest.raises(AssertionError):
        reconcile_metrics(frame,table,cfg)
