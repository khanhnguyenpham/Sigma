"""Real-estimator causal checks, residual heads, and exact preservation of routes."""
import copy
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from sigma.forecasting.weekly import prepare
from M2.models.focus_experiment import (FOCUS, RECENT, candidates, prepare_parent, phase,
    residual_parameters, transform, verify_heads, combine_frozen, load_predictions)
from M2.models.calendar_experiment import reconcile_labels
from M2.models.LightGBM.model import phase as original_phase
from M2.models.tests.test_model_families import fixture


def data():
    series,cfg,settings=fixture()
    settings.update(minimum_history_days=90,n_estimators=7,min_child_samples=5)
    cfg['validation_end']=cfg['validation_start']
    frames=[]
    for country,carrier,factor in [('South Korea','LG U+',1),('South Korea','KT',1.2),('China','China Mobile',.8)]:
        frames.append(pd.DataFrame({'date':series.index,'sales_qty':series.to_numpy()*factor,
            'order_count':series.to_numpy(),'destination_country':country,'carrier':carrier}))
    return pd.concat(frames,ignore_index=True),cfg,settings


def experiment():
    return json.loads((ROOT/'data/configs/m2-focus.json').read_text(encoding='utf-8'))


def test_registered_budget_and_prepare_parity_causal_scales():
    exp=experiment(); assert len(candidates(exp))==35
    daily,cfg,settings=data()
    a=prepare_parent(daily,settings,{})
    b=prepare(daily,{**settings,'blocks':[1,2],'models':{}})
    for key in a:
        pd.testing.assert_frame_equal(a[key]['x'],b[key]['x'])
        np.testing.assert_array_equal(a[key]['scale'],b[key]['scale'])
    cutoff=pd.Timestamp('2024-06-30')
    recent=prepare_parent(daily,settings,exp['parents']['focus_recent28'])
    changed=daily.copy(); changed.loc[changed.date>cutoff,['sales_qty','order_count']]=999999
    other=prepare_parent(changed,settings,exp['parents']['focus_recent28'])
    for key,table in recent.items():
        mask=table['origins']<=cutoff
        pd.testing.assert_frame_equal(table['x'].loc[mask],other[key]['x'].loc[mask])
        np.testing.assert_array_equal(table['scale'][mask],other[key]['scale'][mask])
        assert set(RECENT).issubset(table['x'])
    observed=daily.loc[daily.carrier.eq('LG U+') & daily.date.between('2024-06-03','2024-06-30')].sales_qty.mean()*7
    table=recent[(FOCUS,1)]; idx=np.flatnonzero(table['origins']==cutoff)[0]
    assert table['scale'][idx]==pytest.approx(observed)


def test_residual_shrinkage_clipping_and_empty_positive_labels():
    head=experiment()['residual_heads']['add56p2']
    beta=residual_parameters([40,40,40],[60,60,60],50,head)
    assert 0<beta[0]<.4 and beta[1]==0
    assert transform(40,50,head,np.array([10,10]))==52.5
    assert transform(5,50,head,np.array([-10,0]))==0
    np.testing.assert_array_equal(residual_parameters([1,1],[0,0],1,head),[0,0])
    affine=experiment()['residual_heads']['affine56p4']
    assert np.isfinite(residual_parameters([0,0],[10,10],10,affine)).all()


def test_actual_phase_control_parity_future_mutation_and_heads():
    daily,cfg,settings=data(); exp=experiment()
    exp['parents']={k:v for k,v in exp['parents'].items() if k in ['focus_control','focus_recent28','focus_korea28']}
    exp['blend_parents']=['focus_recent28']; exp['blend_weights']=[.25]
    result,log=phase(daily,cfg,settings,exp,'validation')
    assert verify_heads(log,exp,daily)>0
    assert reconcile_labels(result,daily,cfg)==len(result)
    changed=daily.copy(); changed.loc[changed.date>'2024-06-30',['sales_qty','order_count']]=999999
    other,_=phase(changed,cfg,settings,exp,'validation')
    np.testing.assert_array_equal(result.forecast_qty,other.forecast_qty)
    groups={key:part.set_index('date').sales_qty for key,part in daily.groupby(['destination_country','carrier'])}
    small={**settings,'models':{'LightGBM':{k:settings['models']['LightGBM'][k] for k in ['lgbm_annual_ratio7','lgbm_cal_ratio7_56_p4']}}}
    baseline,_=original_phase(daily,groups,cfg,small,'direct_7d','validation')
    for name,old in [('focus_control_raw','lgbm_annual_ratio7'),('focus_control_mul56p4','lgbm_cal_ratio7_56_p4')]:
        np.testing.assert_allclose(result.loc[result.model.eq(name),'forecast_qty'],
            baseline.loc[baseline.carrier.eq('LG U+') & baseline.model.eq(old),'forecast_qty'],atol=1e-8,rtol=0)
    selected,_=phase(daily,cfg,settings,exp,'validation',['focus_recent28_blend25'])
    np.testing.assert_array_equal(selected.forecast_qty,result.loc[result.model.eq('focus_recent28_blend25'),'forecast_qty'])
    tampered=log.copy(); index=tampered.index[tampered.status.eq('head_pair')][0]
    tampered.loc[index,'actual_qty']+=1
    with pytest.raises(AssertionError): verify_heads(tampered,exp,daily)


def test_country_pool_ignores_other_countries_history():
    daily,cfg,settings=data(); exp=experiment()
    original,_=phase(daily,cfg,settings,exp,'validation',['focus_korea28_raw'])
    changed=daily.copy(); changed.loc[changed.destination_country.eq('China'),'sales_qty']*=1000
    other,_=phase(changed,cfg,settings,exp,'validation',['focus_korea28_raw'])
    np.testing.assert_array_equal(original.forecast_qty,other.forecast_qty)


def test_frozen_predictions_exact_round_trip_and_reject_partial_replacement(tmp_path):
    daily,cfg,settings=data(); exp=experiment()
    focus,_=phase(daily,cfg,settings,exp,'validation',['focus_control_raw'])
    others=focus.copy(); others['carrier']='KT'; others['forecast_qty']=[1.2345678901234567,98.76543210987654]
    reference=pd.concat([focus,others],ignore_index=True)
    new=focus.copy(); new['forecast_qty']*=1.1
    result=combine_frozen(reference,new)
    path=tmp_path/'predictions.csv'; result.to_csv(path,index=False)
    restored=load_predictions(path)
    pd.testing.assert_frame_equal(restored.loc[restored.carrier.eq('KT')].reset_index(drop=True),others,check_exact=True)
    with pytest.raises(AssertionError): combine_frozen(reference,new.iloc[:1])
    with pytest.raises(ValueError): combine_frozen(reference,others)
