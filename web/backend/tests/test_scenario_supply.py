"""Scenario isolation, reset by a new version and reversible deletion with frozen runs."""
from copy import deepcopy
from datetime import timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from core.errors import DomainError
from main import create_app
from modules.runs.models import Run
from modules.runs.trade_verification import verify_trade_snapshot
from test_postgres_api import settings,D,request
from test_configurable_inventory import worker_fixture
from test_trade_api import create_notice,save_internal,internal_body
from worker import serve


def scene(c,code,schedule=None,base=None):
    body=dict(name=code,code=code,settings=dict(cover_days=7,safety_multiplier=1,
        receipts_declared=True,receipts_initial=[],policy_overrides=[]))
    if schedule is not None:body['settings']['supply_schedule']=schedule
    if base:body['base_scenario_id']=base
    response=c.post('/api/v1/scenarios',json=body);assert response.status_code==201,response.text
    return response.json()


def run_body(source,forecast,scenario,kind='stock_projection'):
    body=dict(kind=kind,source_import_run_id=str(source),forecast_run_id=str(forecast),scenario_id=scenario,
        as_of_date=str(D),trade_lifecycle_profile='internal_provider_trade_v2',scenario_supply_profile='scenario_supply_v1')
    if kind.endswith('replay'):body.update(period_start=str(D+timedelta(days=1)),period_end=str(D+timedelta(days=14)))
    return body


@pytest.mark.parametrize('kind',['stock_projection','policy_replay','alert_replay'])
def test_scenario_stops_are_independent_resettable_and_ignore_global_history(pg,tmp_path,kind):
    _,sessions=pg;source,forecast,item=worker_fixture(sessions,tmp_path);cfg=settings(tmp_path)
    with TestClient(create_app(cfg)) as c:
        assert c.post('/api/v1/supplier-item-policies',json=request(item,1).model_dump(mode='json')).status_code==201
        save_internal(c,item,internal_body())
        create_notice(c,dict(action='stop',supplier_id=1,expected_version=0,known_on=str(D),effective_on=str(D),
            reason='Global history must not leak',scope_definition=dict(products=[dict(sku='DEMO-ESIM-01',product_type='eSIM')])))
        stop=dict(item_id=item,known_on=str(D),effective_on=str(D),reason='Only this scenario')
        normal=scene(c,'normal')
        internal=scene(c,'internal',dict(internal_stops=[stop]))
        provider=scene(c,'provider',dict(provider_stops=[stop]))
        results={}
        for scenario,expected in ((normal,('active','clear',True,True)),(internal,('stopped','clear',False,True)),(provider,('active','stopped',False,False))):
            response=c.post('/api/v1/runs',json=run_body(source,forecast,scenario['id'],kind),headers={'Idempotency-Key':scenario['code']})
            assert response.status_code==202,response.text
            key=uuid.UUID(response.json()['run_id']);assert serve(cfg,once=True)==key
            with sessions() as s:
                stored=s.get(Run,key);log=cfg.output_root/str(key)/'failure.private.log'
                assert stored.status=='complete',log.read_text(encoding='utf-8') if log.exists() else stored.error_code
                assert verify_trade_snapshot(stored)
                results[scenario['code']]=(key,deepcopy(stored.config_snapshot),stored.config_sha256)
            row=c.get(f'/api/v1/runs/{key}/inventory?as_of_date={D}').json()['items'][0]
            assert tuple(row[k] for k in ('internal_status','provider_status','replenishment_allowed','sales_allowed'))==expected
            assert c.get(f'/api/v1/runs/{key}').json()['scenario_supply_profile']=='scenario_supply_v1'
            if kind == 'policy_replay':
                evaluation = c.get(f'/api/v1/runs/{key}/policy-alert-evaluation')
                assert evaluation.status_code == 200
                diagnostic = evaluation.json()['diagnostic']
                if scenario['code'] == 'provider':
                    assert diagnostic['blocked_sales_item_days'] == 15
                    assert diagnostic['event_denominator'] == 0 and diagnostic['recall'] is None
                elif scenario['code'] == 'internal':
                    assert diagnostic['blocked_sales_item_days'] == 0
                    assert diagnostic['event_denominator'] == 1
            elif kind == 'alert_replay':
                evaluation = c.get(f'/api/v1/runs/{key}/alert-opportunities')
                assert evaluation.status_code == 200
                assert evaluation.json()['diagnostic']['excluded_count'] == int(scenario['code'] == 'provider')
        reset=scene(c,'internal',dict(internal_stops=[],provider_stops=[]),internal['id'])
        assert reset['version']==2
        response=c.post('/api/v1/runs',json=run_body(source,forecast,reset['id'],kind),headers={'Idempotency-Key':'reset'})
        key=uuid.UUID(response.json()['run_id']);serve(cfg,once=True)
        row=c.get(f'/api/v1/runs/{key}/inventory?as_of_date={D}').json()['items'][0]
        assert row['internal_status']=='active' and row['provider_status']=='clear'
        with sessions() as s:
            for old,snapshot,checksum in results.values():
                assert s.get(Run,old).config_snapshot==snapshot and s.get(Run,old).config_sha256==checksum
            frozen=s.get(Run,results['internal'][0]);frozen.config_snapshot=deepcopy(frozen.config_snapshot)
            frozen.config_snapshot['internal_supply_snapshot']=[]
            with pytest.raises(DomainError):verify_trade_snapshot(frozen)


def test_delete_completed_scenario_preserves_results_and_restore_reenables_runs(pg,tmp_path):
    _,sessions=pg;source,forecast,item=worker_fixture(sessions,tmp_path);cfg=settings(tmp_path)
    with TestClient(create_app(cfg)) as c:
        c.post('/api/v1/supplier-item-policies',json=request(item,1).model_dump(mode='json'))
        scenario=scene(c,'trash',{})
        body=run_body(source,forecast,scenario['id'])
        response=c.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'complete'})
        key=uuid.UUID(response.json()['run_id']);serve(cfg,once=True)
        path=f'/api/v1/runs/{key}'
        before=(c.get(path).json(),c.get(path+f'/exports/inventory_daily?as_of_date={D}').content)
        assert before[0]['status']=='complete'
        assert c.delete(f'/api/v1/scenarios/{scenario["id"]}').status_code==200
        assert scenario['id'] not in [r['id'] for r in c.get('/api/v1/scenarios').json()['items']]
        assert scenario['id'] in [r['id'] for r in c.get('/api/v1/scenarios?include_deleted=true').json()['items']]
        assert str(key) not in [r['id'] for r in c.get('/api/v1/runs').json()['items']]
        assert c.get(f'/api/v1/runs?scenario_id={scenario["id"]}').json()['total']==1
        assert (c.get(path).json(),c.get(path+f'/exports/inventory_daily?as_of_date={D}').content)==before
        blocked=c.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'deleted'})
        assert blocked.status_code==409 and blocked.json()['error']['code']=='scenario_deleted'
        assert c.post(f'/api/v1/scenarios/{scenario["id"]}/restore').status_code==200
        accepted=c.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'restored'})
        assert accepted.status_code==202
        rejected=c.delete(f'/api/v1/scenarios/{scenario["id"]}')
        assert rejected.status_code==409 and rejected.json()['error']['code']=='scenario_busy'


def test_scenario_stop_input_rejects_unknown_products_dates_and_duplicate_scopes(pg,tmp_path):
    _,sessions=pg;_,_,item=worker_fixture(sessions,tmp_path)
    with TestClient(create_app(settings(tmp_path))) as c:
        stop=dict(item_id=item,known_on=str(D),effective_on=str(D),reason='Declared scenario stop')
        base=dict(name='Invalid',code='invalid',settings=dict(cover_days=7,safety_multiplier=1,receipts_declared=True,
            policy_overrides=[],receipts_initial=[]))
        for schedule,expected in ((dict(internal_stops=[dict(stop,item_id=999999)]),404),
            (dict(internal_stops=[dict(stop,effective_on=str(D-timedelta(days=1)))]),422),
            (dict(internal_stops=[stop,stop]),422)):
            response=c.post('/api/v1/scenarios',json={**base,'settings':{**base['settings'],'supply_schedule':schedule}})
            assert response.status_code==expected,response.text


def test_retry_of_legacy_trade_run_uses_the_scenario_schedule(pg,tmp_path):
    _,sessions=pg;source,forecast,item=worker_fixture(sessions,tmp_path)
    with TestClient(create_app(settings(tmp_path))) as c:
        c.post('/api/v1/supplier-item-policies',json=request(item,1).model_dump(mode='json'))
        scenario=scene(c,'retry',{})
        body=run_body(source,forecast,scenario['id']);body.pop('scenario_supply_profile')
        response=c.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'old'})
        key=uuid.UUID(response.json()['run_id'])
        with sessions.begin() as s:s.get(Run,key).status='failed'
        retry=c.post(f'/api/v1/runs/{key}/retry',headers={'Idempotency-Key':'retry'})
        assert retry.status_code==202,retry.text
        with sessions() as s:
            run=s.get(Run,uuid.UUID(retry.json()['run_id']))
            assert run.config_snapshot['scenario_supply_profile']=='scenario_supply_v1'
            assert run.config_snapshot['internal_supply_snapshot']==run.config_snapshot['provider_notice_snapshot']==[]
