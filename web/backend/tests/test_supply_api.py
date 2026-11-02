"""Step 3 on synthetic data and sigma_m3_test only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from alembic import command
from alembic.config import Config
from pathlib import Path

from main import create_app
from core.errors import DomainError
from core.hashes import digest
from modules.catalog.models import Item, ItemSupplyChange
from modules.catalog.schemas import SupplyChangeCreate
from modules.catalog.supply import supply_state
from modules.catalog.supply_service import create_supply_change
from modules.configuration.service import create_policy
from modules.runs.models import Run
from test_postgres_api import seed, settings, request, D
from test_results_api import result_fixture
from test_policy_persistence import scenario_body


def body(version=0, **changes):
    return {**dict(action="stop", known_on=str(D), effective_on=str(D+timedelta(days=7)),
                   reason=" Synthetic notice ", expected_version=version), **changes}


def test_http_history_cycles_and_latest_version_at_past_date(pg, tmp_path):
    _,sessions=pg
    item,_,_=seed(sessions)
    path=f"/api/v1/products/{item}/supply-changes"
    with TestClient(create_app(settings(tmp_path))) as c:
        assert c.get(path).json()["state"] is None
        first=c.post(path,json=body());assert first.status_code==201,first.text
        stop=first.json();assert stop["reason"]=="Synthetic notice"
        assert c.post(path,json=body()).status_code==409
        assert c.get(path+"?page_size=1").json()["supply_version"]==1
        assert c.get(f"/api/v1/products/{item}").json()["supply_status"] is None
        assert c.get(f"/api/v1/products/{item}?as_of_date={D-timedelta(days=1)}").json()["supply_version"]==1
        assert c.get(f"/api/v1/products/{item}?as_of_date={D+timedelta(days=7)}").json()["supply_status"]=="stopped"
        cancel=body(1,action="cancel_stop",target_change_id=stop["id"],known_on=str(D+timedelta(days=6)),effective_on=str(D+timedelta(days=6)))
        assert c.post(path,json=cancel).status_code==201
        again=c.post(path,json=body(2,known_on=str(D+timedelta(days=6)),effective_on=str(D+timedelta(days=13)))).json()
        resume=body(3,action="resume",target_change_id=again["id"],known_on=str(D+timedelta(days=13)),effective_on=str(D+timedelta(days=13)))
        assert c.post(path,json=resume).status_code==201
        history=c.get(path+f"?page_size=1&page=2&as_of_date={D}").json()
        assert history["total"]==4 and history["items"][0]["version"]==3
        assert history["state"]["supply_status"]=="scheduled_stop"
        assert history["supply_version"]==4


@pytest.mark.parametrize("change", [dict(effective_on=str(D)),dict(effective_on=str(D+timedelta(days=6))),
    dict(reason="\t\n"),dict(reason="x"*1001),dict(expected_version=True),dict(expected_version=-1),
    dict(known_on="9999-12-31",effective_on="9999-12-31"),dict(target_change_id=1),dict(action="resume"),dict(extra="private-sentinel"),dict(action="unknown")])
def test_invalid_payload_and_missing_items(pg,tmp_path,change):
    _,sessions=pg;item,_,_=seed(sessions)
    with TestClient(create_app(settings(tmp_path))) as c:
        response=c.post(f"/api/v1/products/{item}/supply-changes",json=body(**change))
        assert response.status_code==422,response.text
        assert "private-sentinel" not in response.text
        assert c.get("/api/v1/products/999/supply-changes").status_code==404
        assert c.post("/api/v1/products/999/supply-changes",json=body()).status_code==404


def test_filters_precede_count_and_pagination_and_match_timeline(pg,tmp_path):
    _,sessions=pg;item,_,_=seed(sessions)
    with sessions.begin() as s:
        other=Item(warehouse_id=1,sku="SECOND",product_type="physical_SIM",first_seen_date=D)
        s.add(other);s.flush();other_id=other.id
    with TestClient(create_app(settings(tmp_path))) as c:
        first=c.post(f"/api/v1/products/{item}/supply-changes",json=body()).json()
        url="/api/v1/products"
        assert c.get(url+"?supply_status=stopped").status_code==422
        assert c.get(url+f"?as_of_date={D}&supply_status=invalid").status_code==422
        for offset in [-1,0,6,7,8]:
            on=D+timedelta(days=offset)
            state=supply_state([first],item,on)["supply_status"]
            result=c.get(url+f"?as_of_date={on}&supply_status={state}&page_size=1").json()
            assert result["total"]==(2 if state=="active" else 1)
            assert result["items"][0]["id"]==item
        result=c.get(url+f"?as_of_date={D}&supply_status=active&page_size=1").json()
        assert result["total"]==1 and result["items"][0]["id"]==other_id
        c.post(f"/api/v1/products/{item}/supply-changes",json=body(1,action="cancel_stop",target_change_id=first["id"],known_on=str(D+timedelta(days=1)),effective_on=str(D+timedelta(days=1))))
        assert c.get(url+f"?as_of_date={D+timedelta(days=1)}&supply_status=active").json()["total"]==2
        assert c.get(url+f"?as_of_date={D}&supply_status=scheduled_stop").json()["total"]==1


def test_concurrent_appends_and_transition_conflicts(pg):
    _,sessions=pg;item,_,_=seed(sessions)
    def save(_):
        try:
            with sessions.begin() as s:create_supply_change(s,item,SupplyChangeCreate(**body()))
            return "created"
        except DomainError as e:return e.code
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(save,range(2)))==["created","version_conflict"]
    with sessions.begin() as s:
        history=s.scalars(select(ItemSupplyChange)).all();assert len(history)==1
        with pytest.raises(DomainError) as e:create_supply_change(s,item,SupplyChangeCreate(**body(1)))
        assert e.value.status==409


def test_snapshot_is_frozen_causal_and_retry_does_not_refreeze(pg,tmp_path):
    _,sessions=pg;source,forecast,item=result_fixture(sessions)
    with sessions.begin() as s:create_policy(s,request(item,1))
    with sessions() as s:before={r.id:(deepcopy(r.config_snapshot),r.config_sha256) for r in s.scalars(select(Run))}
    with TestClient(create_app(settings(tmp_path))) as c:
        path=f"/api/v1/products/{item}/supply-changes"
        first=c.post(path,json=body()).json()
        scenario=c.post('/api/v1/scenarios',json=scenario_body([])).json()
        args=dict(kind="stock_projection",as_of_date=str(D),source_import_run_id=str(source),forecast_run_id=str(forecast),scenario_id=scenario['id'])
        r=c.post('/api/v1/runs',json=args,headers={'Idempotency-Key':'supply-freeze'});assert r.status_code==202,r.text
        import uuid
        key=uuid.UUID(r.json()['run_id'])
        with sessions() as s:
            row=s.get(Run,key);frozen=deepcopy(row.config_snapshot);checksum=row.config_sha256
        assert frozen['supply_lifecycle_profile']=='notice7_sellthrough_v1'
        assert [r['id'] for r in frozen['supply_lifecycle_snapshot']]==[first['id']]
        assert digest(frozen)==checksum
        c.post(path,json=body(1,action="cancel_stop",target_change_id=first['id'],known_on=str(D+timedelta(days=1)),effective_on=str(D+timedelta(days=1))))
        assert c.post('/api/v1/runs',json=args,headers={'Idempotency-Key':'supply-freeze'}).json()['run_id']==str(key)
        with sessions() as s:
            assert s.get(Run,key).config_snapshot==frozen and s.get(Run,key).config_sha256==checksum
            assert {r.id:(r.config_snapshot,r.config_sha256) for r in s.scalars(select(Run).where(Run.id.in_(before)))}==before
        # The cancellation known tomorrow is absent from a fresh origin-D snapshot too.
        fresh=c.post('/api/v1/runs',json=args,headers={'Idempotency-Key':'supply-freeze-new'})
        with sessions() as s:assert len(s.get(Run,uuid.UUID(fresh.json()['run_id'])).config_snapshot['supply_lifecycle_snapshot'])==1
        from worker import process_one
        process_one(settings(tmp_path),sessions)
        with sessions() as s:assert s.get(Run,key).error_code=="stage_not_implemented"


def test_legacy_schema_keeps_product_read_and_rejects_new_features(pg,tmp_path):
    engine,sessions=pg;item,_,_=seed(sessions)
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    cfg.attributes['database_url']=engine.url.render_as_string(hide_password=False)
    command.downgrade(cfg,'0006_fixed_days')
    try:
        with TestClient(create_app(settings(tmp_path))) as c:
            assert c.get('/api/v1/products').json()['items'][0]['supply_schema_ready'] is False
            assert c.get(f'/api/v1/products/{item}?as_of_date={D}').status_code==503
            assert c.post(f'/api/v1/products/{item}/supply-changes',json=body()).status_code==503
    finally:command.upgrade(cfg,'head')


@pytest.mark.parametrize("kind,count",[("stock_projection",0),("policy_replay",1),("alert_replay",0)])
def test_replay_snapshot_uses_last_decision_origin_not_end_of_horizon(pg,tmp_path,kind,count):
    _,sessions=pg;source,forecast,item=result_fixture(sessions)
    with sessions.begin() as s:create_policy(s,request(item,1))
    known=D+timedelta(days=15)
    with TestClient(create_app(settings(tmp_path))) as c:
        c.post(f'/api/v1/products/{item}/supply-changes',json=body(known_on=str(known),effective_on=str(known+timedelta(days=7))))
        scenario=c.post('/api/v1/scenarios',json=scenario_body([])).json()
        args=dict(kind=kind,as_of_date=str(D),source_import_run_id=str(source),forecast_run_id=str(forecast),scenario_id=scenario['id'])
        if kind!='stock_projection':args.update(period_start=str(D+timedelta(days=1)),period_end=str(D+timedelta(days=30)))
        result=c.post('/api/v1/runs',json=args,headers={'Idempotency-Key':'cutoff'})
        assert result.status_code==202,result.text
        import uuid
        with sessions() as s:snapshot=s.get(Run,uuid.UUID(result.json()['run_id'])).config_snapshot
        assert len(snapshot['supply_lifecycle_snapshot'])==count
        if count:
            assert supply_state(snapshot['supply_lifecycle_snapshot'],item,D)['supply_status']=='active'
            assert supply_state(snapshot['supply_lifecycle_snapshot'],item,known)['supply_status']=='scheduled_stop'


@pytest.mark.parametrize("change", [
    dict(action="cancel_stop",target_change_id=999),
    dict(action="cancel_stop",known_on=str(D+timedelta(days=7))),
    dict(action="resume",known_on=str(D+timedelta(days=6))),
    dict(action="stop",known_on=str(D-timedelta(days=1))),
])
def test_business_conflicts_do_not_append(pg,tmp_path,change):
    _,sessions=pg;item,_,_=seed(sessions)
    with TestClient(create_app(settings(tmp_path))) as c:
        path=f'/api/v1/products/{item}/supply-changes'
        first=c.post(path,json=body()).json()
        known=change.get('known_on',str(D))
        args=body(1,action=change['action'],known_on=known,
                  effective_on=str(D+timedelta(days=7)) if change['action']=='stop' else known,
                  target_change_id=first['id'] if change['action']!='stop' else None)
        args.update(change)
        assert c.post(path,json=args).status_code==409
        assert c.get(path).json()['total']==1
