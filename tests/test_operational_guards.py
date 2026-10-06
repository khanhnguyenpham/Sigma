from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from src.common import sha256
from src.inventory import AllocationPlan, allocation, run_policy
from src.models import ensure_forecast_origin, forecast_at
from tests.test_inventory import policy_fixture
from tests.test_context_models import fixture_daily


def test_forecast_cannot_shift_stale_actuals_into_a_future_origin():
    daily=fixture_daily();top=pd.DataFrame([('A','a')],columns=['destination_country','carrier'])
    selected=top.assign(model='context_180_mape',fallback_model='ma7')
    cfg={'horizon':14,'validation_end':'2024-03-19'}
    with pytest.raises(ValueError,match='observed route-day'):
        forecast_at(daily,selected,top,'2024-05-01',cfg)
    with pytest.raises(ValueError,match='closed UTC calendar day'):
        ensure_forecast_origin(daily,'2024-03-20T08:00:00Z')
    assert ensure_forecast_origin(daily,'2024-03-20T00:00:00Z')==pd.Timestamp('2024-03-20')


def test_missing_actual_or_route_is_not_a_zero_origin():
    daily=fixture_daily();origin=pd.Timestamp('2024-03-20')
    daily['actual_available']=True
    daily.loc[daily.date.eq(origin)&daily.carrier.eq('a'),'actual_available']=False
    daily.loc[daily.date.eq(origin)&daily.carrier.eq('a'),'sales_qty']=0.
    with pytest.raises(ValueError,match='unavailable actual'):
        ensure_forecast_origin(daily,origin)
    daily.loc[daily.date.eq(origin),'actual_available']=True
    daily.loc[daily.date.eq(origin)&daily.carrier.eq('a'),'sales_qty']=np.nan
    with pytest.raises(ValueError,match='missing actual'):
        ensure_forecast_origin(daily,origin)
    daily=daily.loc[~(daily.date.eq(origin)&daily.carrier.eq('a'))]
    with pytest.raises(ValueError,match='coverage'):
        ensure_forecast_origin(daily,origin)


def test_shared_allocation_reproduces_policies_and_rejects_stale_inputs(cfg):
    matrix,forecasts=policy_fixture(cfg)
    plan=AllocationPlan(matrix,forecasts,cfg)
    base={'name':'base','demand_multiplier':1.,'receipt_fraction':.5,'receipt_delay_days':2}
    for cover in [0,3,14]:
        changed=deepcopy(cfg);changed['inventory']['initial_cover_days']=cover
        expected,expected_rec,expected_issue=run_policy(matrix,forecasts,changed,base)
        actual,actual_rec,actual_issue=run_policy(matrix,forecasts,changed,base,allocation_plan=plan)
        pd.testing.assert_frame_equal(actual,expected);pd.testing.assert_frame_equal(actual_rec,expected_rec)
        pd.testing.assert_frame_equal(actual_issue,expected_issue)
    altered=matrix.copy();altered.iloc[-1,0]=999
    with pytest.raises(ValueError,match='differs'):
        run_policy(altered,forecasts,cfg,base,allocation_plan=plan)
    changed=deepcopy(cfg);changed['inventory']['allocation_window_days']+=1
    with pytest.raises(ValueError,match='differs'):
        run_policy(matrix,forecasts,changed,base,allocation_plan=plan)
    altered=forecasts.copy();altered.iloc[0,altered.columns.get_loc('forecast_qty')]=999
    with pytest.raises(ValueError,match='differs'):
        run_policy(matrix,altered,cfg,base,allocation_plan=plan)


def test_duplicate_horizon_or_negative_allocation_is_not_silently_accepted(cfg):
    matrix,forecasts=policy_fixture(cfg);origin=pd.Timestamp('2025-09-30')
    group=forecasts.loc[forecasts.as_of_date.eq(origin)].copy()
    group.iloc[0,group.columns.get_loc('horizon_day')]=2
    with pytest.raises(ValueError,match='Incomplete'):
        allocation(matrix,group,origin,cfg)
    group=forecasts.loc[forecasts.as_of_date.eq(origin)].copy();group['forecast_qty']=-1.
    with pytest.raises(ValueError,match='Incomplete'):
        allocation(matrix,group,origin,cfg)


def test_demo_sources_are_isolated_and_failed_resume_never_overwrites_or_restores(cfg,tmp_path,monkeypatch):
    from src import pipeline as run
    monkeypatch.setattr(run,'ROOT',tmp_path)
    cfg.update(observation_start='2024-01-01',observation_end='2024-01-24',
        train_end='2024-01-10',validation_start='2024-01-11',validation_end='2024-01-20',
        test_start='2024-01-21',test_end='2024-01-24',forecast_origin='2024-01-24',demo_origin='2024-01-22')
    config=tmp_path/'config.json';config.write_text(json.dumps(cfg),encoding='utf-8')
    first=run.execute(str(config),stage='audit',run_id='first',demo=True,baseline_only=True)
    source=first/'synthetic_orders.csv';source_hash=sha256(source);manifest_hash=sha256(first/'manifest.json')
    cfg['seed']+=1;config.write_text(json.dumps(cfg),encoding='utf-8')
    second=run.execute(str(config),stage='audit',run_id='second',demo=True,baseline_only=True)
    assert (second/'synthetic_orders.csv').is_file() and sha256(source)==source_hash
    assert json.loads((second/'manifest.json').read_text())['source_relative_path']=='outputs/second/synthetic_orders.csv'
    with pytest.raises(ValueError,match='same input'):
        run.execute(str(config),stage='audit',run_id='first',demo=True,baseline_only=True,resume=True)
    assert sha256(source)==source_hash and sha256(first/'manifest.json')==manifest_hash
    source.unlink()  # Disposable fake fixture; resume must not recreate it.
    with pytest.raises(ValueError,match='source is missing'):
        run.execute(str(config),stage='audit',run_id='first',demo=True,baseline_only=True,resume=True)
    assert not source.exists() and sha256(first/'manifest.json')==manifest_hash


def test_missing_manifest_or_nonempty_run_folder_cannot_be_overwritten(cfg,tmp_path,monkeypatch):
    from src import pipeline as run
    monkeypatch.setattr(run,'ROOT',tmp_path)
    config=tmp_path/'config.json';config.write_text(json.dumps(cfg),encoding='utf-8')
    folder=tmp_path/'outputs'/'orphan';folder.mkdir(parents=True);marker=folder/'marker.txt';marker.write_text('preserve')
    with pytest.raises(ValueError,match='Run exists'):
        run.execute(str(config),stage='audit',run_id='orphan',demo=True,baseline_only=True)
    with pytest.raises(ValueError,match='original manifest'):
        run.execute(str(config),stage='audit',run_id='orphan',demo=True,baseline_only=True,resume=True)
    assert marker.read_text()=='preserve'
