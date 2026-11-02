"""Supply-aware worker, hand cases and independent tamper detection."""
from copy import deepcopy
from datetime import timedelta
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from core.errors import DomainError
from main import create_app
from modules.alerts.service import project
from modules.alerts.models import Alert
from modules.inventory.simulation import pure_window
from modules.inventory.models import InventoryDaily
from modules.purchasing.models import Replenishment
from modules.runs.models import Run
from modules.runs.verification import verify_run
from modules.runs.supply_verification import verify_supply_snapshot
from test_simulation import inputs, ORIGIN
from test_configurable_inventory import worker_fixture, enqueue_fixture
from test_postgres_api import settings, D
from worker import serve


def notice(origin=ORIGIN, **changes):
    return {**dict(id=1,item_id=1,version=1,action="stop",known_on=str(origin-timedelta(days=7)),
                   effective_on=str(origin),target_change_id=None),**changes}


@pytest.mark.parametrize("kind",["stock_projection","policy_replay","alert_replay"])
def test_stopped_keeps_actuals_receipts_and_metrics(kind):
    args=list(inputs())
    args[5]["receipts_initial"]=[dict(item_id=1,lot_key="old",ordered_on=str(ORIGIN-timedelta(days=3)),
                                    eta=str(ORIGIN+timedelta(days=4)),ordered_qty=20)]
    end=ORIGIN+timedelta(days=14)
    result=pure_window(*args,kind,ORIGIN,end,[notice()])
    assert all(r["recommended_qty"]==0 and r["needs_replenishment"] is False for r in result["ledger"])
    assert all(o["is_initial"] for o in result["orders"])
    if kind!="stock_projection":
        assert sum(r["receipts_qty"] for r in result["ledger"])==20
        assert sum(r["sales_qty"] for r in result["ledger"])==140
        assert sum(r["fulfilled_qty"]+r["shortage_qty"] for r in result["ledger"])==140
        assert len([e for e in result["events"] if e["event_kind"]=="receipt"])==1
    if kind=="alert_replay":
        assert len(result["cases"])==1 and len(result["threshold_cases"])==1
    exp=next(a["explanation"] for a in result["alerts"] if a["alert_type"]=="depletion")
    assert exp["replenishment_allowed"] is False
    assert exp["stock_below_rop"] is True
    assert exp["forecast14"]==[10.0]*14


def test_announcement_stop_resume_and_alert_origin_cutoff():
    history=[notice(known_on=str(ORIGIN),effective_on=str(ORIGIN+timedelta(days=7))),
        dict(id=2,item_id=1,version=2,action="resume",known_on=str(ORIGIN+timedelta(days=9)),
             effective_on=str(ORIGIN+timedelta(days=9)),target_change_id=1)]
    policy=pure_window(*inputs(),"policy_replay",ORIGIN,ORIGIN+timedelta(days=14),history)
    rows={r["date"]:r for r in policy["ledger"]}
    assert any(o["ordered_on"]<ORIGIN+timedelta(days=7) for o in policy["orders"])
    assert all(rows[ORIGIN+timedelta(days=h)]["recommended_qty"]==0 for h in (7,8))
    assert rows[ORIGIN+timedelta(days=9)]["recommended_qty"]>0
    alert=pure_window(*inputs(),"alert_replay",ORIGIN,ORIGIN+timedelta(days=14),history)
    assert all(r["recommended_qty"]==0 for r in alert["ledger"] if r["date"]>=ORIGIN+timedelta(days=7))
    projected=alert["alerts"][0]["explanation"]["projection"]
    assert projected[5]["supply_status"]=="scheduled_stop"
    assert projected[6]["supply_status"]==projected[9]["supply_status"]=="stopped"


def test_sell_through_hand_case_and_late_receipt():
    path=project(ORIGIN,10,[4]*14,{},sell_through=True)["projection"]
    assert [r["projected_sales_qty"] for r in path[:4]]==[4,4,2,0]
    assert [r["unserved_demand_qty"] for r in path[:4]]==[0,0,2,4]
    assert path[2]["closing_forecast"]==0
    arrival=ORIGIN+timedelta(days=3)
    path=project(ORIGIN,0,[4]*14,{arrival:6},sell_through=True)["projection"]
    assert [r["projected_sales_qty"] for r in path[:5]]==[0,0,4,2,0]


def test_empty_timeline_legacy_parity_and_other_item():
    args=list(inputs());legacy=pure_window(*args,"policy_replay",ORIGIN,ORIGIN+timedelta(days=14))
    empty=pure_window(*args,"policy_replay",ORIGIN,ORIGIN+timedelta(days=14),[])
    assert legacy["ledger"]==empty["ledger"] and legacy["orders"]==empty["orders"]
    assert legacy["cases"]==empty["cases"] and legacy["threshold_cases"]==empty["threshold_cases"]
    assert legacy["summary"]=={k:v for k,v in empty["summary"].items() if k!="supply_stopped_decisions"}
    assert [{k:v for k,v in a.items() if k!="explanation"} for a in legacy["alerts"]]==[
        {k:v for k,v in a.items() if k!="explanation"} for a in empty["alerts"]]
    other=pure_window(*args,"policy_replay",ORIGIN,ORIGIN+timedelta(days=14),[notice(item_id=999)])
    assert other["ledger"]==empty["ledger"] and other["orders"]==empty["orders"]


@pytest.mark.parametrize("kind",["stock_projection","policy_replay","alert_replay"])
def test_worker_with_real_supply_api_and_independent_verification(pg,tmp_path,kind):
    _,sessions=pg;source,forecast,item=worker_fixture(sessions,tmp_path);cfg=settings(tmp_path)
    with TestClient(create_app(cfg)) as c:
        response=c.post(f'/api/v1/products/{item}/supply-changes',json=dict(action="stop",
            known_on=str(D-timedelta(days=7)),effective_on=str(D),reason="Synthetic stop",expected_version=0))
        assert response.status_code==201,response.text
        key=enqueue_fixture(c,source,forecast,item,'days','fixed',kind)
        assert serve(cfg,once=True)==key
        with sessions() as s:
            run=s.get(Run,key);assert run.status=="complete",run.error_code
            assert run.result_summary['supply_stopped_decisions']==(1 if kind=='stock_projection' else 15)
            assert verify_supply_snapshot(run) is not None
            ledger=s.scalars(select(InventoryDaily).where(InventoryDaily.run_id==key)).all()
            assert all(r.recommended_qty==0 and r.needs_replenishment is False for r in ledger)
            orders=s.scalars(select(Replenishment).where(Replenishment.run_id==key)).all()
            assert all(o.is_initial for o in orders)
            assert sum(o.received_qty for o in orders)==(0 if kind=='stock_projection' else 20)
            alert=s.scalar(select(Alert).where(Alert.run_id==key,Alert.alert_type=='depletion').order_by(Alert.as_of_date))
            alert_id=alert.id;original=deepcopy(alert.explanation)
            assert original['replenishment_block_reason']=='supply_stopped'
            assert len(original['projection'])==14
        verify_run(cfg,sessions,key)
        for field,value in [('projected_sales_qty',999),('unserved_demand_qty',999),('supply_status','active')]:
            with sessions.begin() as s:
                changed=deepcopy(original);changed['projection'][0][field]=value
                s.get(Alert,alert_id).explanation=changed
            with pytest.raises(DomainError,match='Sell-through'):verify_run(cfg,sessions,key)
        with sessions.begin() as s:s.get(Alert,alert_id).explanation=original
        with sessions.begin() as s:
            row=s.scalar(select(InventoryDaily).where(InventoryDaily.run_id==key).order_by(InventoryDaily.date))
            row.recommended_qty=5
        with pytest.raises(DomainError,match='thresholds'):verify_run(cfg,sessions,key)


@pytest.mark.parametrize("stock,pending,state",[(0,0,"sold_out"),(0,20,"waiting_receipts"),(10,0,"selling_remaining")])
def test_origin_sell_through_state(stock,pending,state):
    args=list(inputs());args[0].loc[:,1]=stock;args[5]['cover_days']=1
    if pending:
        args[5]['receipts_initial']=[dict(item_id=1,lot_key="late",ordered_on=str(ORIGIN-timedelta(days=1)),
                                        eta=str(ORIGIN+timedelta(days=6)),ordered_qty=pending)]
    result=pure_window(*args,'stock_projection',ORIGIN,ORIGIN,[notice()])
    assert result['alerts'][0]['explanation']['sell_through_state']==state


@pytest.mark.parametrize("change",[dict(action="unknown"),dict(version=2),dict(is_assumed=False),
    dict(known_on=str(ORIGIN+timedelta(days=1))),dict(effective_on=str(ORIGIN-timedelta(days=1))),
    dict(item_id=999),dict(reason=" "),dict(target_change_id=999)])
def test_independent_verifier_rejects_invalid_frozen_history(change):
    from types import SimpleNamespace
    row={**notice(),"is_assumed":True,"assumption_source":"user_declared_supply_simulation_v1","reason":"Synthetic",**change}
    run=SimpleNamespace(kind='stock_projection',as_of_date=ORIGIN,config_snapshot=dict(
        supply_lifecycle_profile='notice7_sellthrough_v1',supply_lifecycle_snapshot=[row],
        catalog_snapshot=[dict(item_id=1,first_seen_date='2024-01-01')]))
    with pytest.raises(DomainError):verify_supply_snapshot(run)
