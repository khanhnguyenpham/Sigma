"""Hand-calculated trade cases, real synthetic worker and independent tamper checks."""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
import csv
import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from core.errors import DomainError
from core.hashes import digest
from main import create_app
from modules.catalog.trade_service import TRADE_RULES
from modules.inventory.trade import project_trade, limit_order
from modules.inventory.simulation import pure_window
from modules.inventory.models import InventoryDaily, InventoryEvent
from modules.alerts.models import Alert
from modules.purchasing.models import Replenishment
from modules.runs.models import Run
from modules.runs.verification import verify_run
from modules.runs.trade_verification import verify_trade_snapshot
from test_simulation import inputs, ORIGIN
from test_postgres_api import D, request, settings
from test_configurable_inventory import worker_fixture
from test_trade_api import create_notice, save_follow, save_internal, internal_body, follow_body
from worker import serve

PROFILE = 'internal_provider_trade_v2'


def snapshot(known=ORIGIN, effective=ORIGIN, resume=None):
    event = dict(id=1, notice_id=1, version=1, action='stop', known_on=str(known), effective_on=str(effective),
        target_event_id=None, reason='Synthetic provider', source_description='Declared simulation', source_ref=None, is_assumed=True)
    notice = dict(id=1, supplier_id=1, item_ids=[1], events=[event])
    if resume:
        notice['events'].append(dict(event, id=2, version=2, action='resume_supply',
            known_on=str(resume[0]), effective_on=str(resume[1]), target_event_id=1))
    return dict(trade_lifecycle_profile=PROFILE, trade_rules=TRADE_RULES,
        internal_supply_snapshot=[], provider_notice_snapshot=[notice])


@pytest.mark.parametrize('kind', ['stock_projection', 'policy_replay', 'alert_replay'])
def test_provider_stop_keeps_stock_receives_lot_and_blocks_source(kind):
    args = list(inputs())
    args[5]['cover_days'] = 1
    args[5]['receipts_initial'] = [dict(item_id=1, lot_key='old', ordered_on=str(ORIGIN-timedelta(days=3)),
        eta=str(ORIGIN+timedelta(days=4)), ordered_qty=5)]
    result = pure_window(*args, kind, ORIGIN, ORIGIN+timedelta(days=14), trade_snapshot=snapshot())
    assert all(r['recommended_qty'] == 0 and not r['needs_replenishment'] for r in result['ledger'])
    path = result['alerts'][0]['explanation']['projection']
    assert path[0]['closing_total'] == path[0]['closing_blocked'] == 10
    assert path[0]['projected_sales_qty'] == path[0]['unserved_stock_qty'] == 0
    assert path[0]['sales_blocked_qty'] == 10 and path[3]['closing_blocked'] == 15
    assert result['alerts'][0]['explanation']['needs_supplier_action']
    if kind != 'stock_projection':
        assert result['summary']['source_sales_qty'] == result['summary']['actual_blocked_qty'] == 140
        assert result['summary']['scenario_sales_qty'] == 0 and result['summary']['fill_allowed'] is None
        assert result['ledger'][-1]['closing_qty'] == 15
        assert len([e for e in result['events'] if e['event_kind'] == 'receipt']) == 1
        assert len([e for e in result['events'] if e['event_kind'] == 'sale_blocked']) == 14
    if kind == 'policy_replay':
        received = next(a['explanation'] for a in result['alerts'] if a['alert_type'] == 'depletion' and a['as_of_date'] == ORIGIN+timedelta(days=4))
        assert received['needs_supplier_action'] # Received blocked stock still needs handling.
    if kind == 'alert_replay':
        assert not result['cases'][0]['is_evaluable'] and not result['threshold_cases'][0]['is_evaluable']
        assert len(result['summary']['metric_exclusions'][0]['blocked_dates']) == 15


def test_internal_stop_keeps_sales_and_resume_provider_does_not_resume_internal():
    snap = snapshot(resume=(ORIGIN, ORIGIN+timedelta(days=2)))
    snap['internal_supply_snapshot'] = [dict(id=1, item_id=1, version=1, action='stop',
        known_on=str(ORIGIN), effective_on=str(ORIGIN), target_change_id=None, reason='Internal')]
    result = pure_window(*inputs(), 'policy_replay', ORIGIN, ORIGIN+timedelta(days=14), trade_snapshot=snap)
    rows = result['ledger']
    assert rows[1]['actual_blocked_qty'] == 10 and rows[2]['sales_qty'] == 10
    assert all(r['recommended_qty'] == 0 for r in rows)
    snap['provider_notice_snapshot'] = []
    internal = pure_window(*inputs(), 'policy_replay', ORIGIN, ORIGIN+timedelta(days=14), trade_snapshot=snap)
    assert internal['summary']['scenario_sales_qty'] == 140 and internal['summary']['actual_blocked_qty'] == 0


@pytest.mark.parametrize('offset,stock,demand,q,expected,budget,reason', [
    (7,0,4,10,0,None,'eta_at_or_after_provider_stop'),
    (6,0,4,10,0,None,'eta_at_or_after_provider_stop'),
    (10,0,4,10,10,12,None), (10,6,2,10,0,6,'fixed_lot_exceeds_sellable_budget'),
    (10,0,4,12,12,12,None), (10,0,4,13,0,12,'fixed_lot_exceeds_sellable_budget'),
    (16,0,4,10,0,None,'insufficient_forecast_coverage'),
    (15,0,1,8,8,8,None),
])
def test_whole_lot_cap_eta_budget_and_exact_coverage(offset, stock, demand, q, expected, budget, reason):
    snap = snapshot(effective=ORIGIN+timedelta(days=offset))
    path = project_trade(snap, 1, ORIGIN, ORIGIN, stock, [demand]*14, {})['projection']
    result = limit_order(snap, 1, ORIGIN, ORIGIN, q, path)
    assert (result['q_final'], result['sellable_budget'], result['cap_reason']) == (expected,budget,reason)
    # Pending stock consumes the budget; the candidate Q never appears in the baseline.
    if offset == 10 and stock == 0 and demand == 4:
        pending = project_trade(snap, 1, ORIGIN, ORIGIN, 0, [4]*14, {ORIGIN+timedelta(days=7):10})['projection']
        assert limit_order(snap,1,ORIGIN,ORIGIN,q,pending)['sellable_budget'] == 2


def test_late_known_and_future_resume_fixed_vs_rolling_cutoff_and_overlap():
    snap = snapshot(known=ORIGIN+timedelta(days=5), effective=ORIGIN+timedelta(days=2),
                    resume=(ORIGIN+timedelta(days=6), ORIGIN+timedelta(days=8)))
    policy = pure_window(*inputs(),'policy_replay',ORIGIN,ORIGIN+timedelta(days=14),trade_snapshot=snap)
    alert = pure_window(*inputs(),'alert_replay',ORIGIN,ORIGIN+timedelta(days=14),trade_snapshot=snap)
    assert policy['summary']['actual_blocked_qty'] == 30 and alert['summary']['actual_blocked_qty'] == 0
    assert [r['actual_blocked_qty'] for r in policy['ledger'][4:9]] == [0,10,10,10,0]
    assert alert['summary']['metric_exclusions'] == []
    snap = snapshot(resume=(ORIGIN, ORIGIN+timedelta(days=4)))
    second = deepcopy(snap['provider_notice_snapshot'][0]); second['id'] = 2; second['events'] = second['events'][:1]
    second['events'][0].update(id=3, notice_id=2)
    snap['provider_notice_snapshot'].append(second)
    path = project_trade(snap,1,ORIGIN,ORIGIN,10,[4]*14,{})['projection']
    assert path[4]['sales_allowed'] is False and path[4]['closing_total'] == 10
    snap['provider_notice_snapshot'][1]['item_ids'] = [999]
    assert project_trade(snap,1,ORIGIN,ORIGIN,10,[4]*14,{})['projection'][4]['sales_allowed']


def test_unrestricted_trade_parity_and_projection_hand_case():
    snap = snapshot(); snap['provider_notice_snapshot'] = []
    for kind in ['stock_projection','policy_replay','alert_replay']:
        before = pure_window(*inputs(),kind,ORIGIN,ORIGIN+timedelta(days=14))
        after = pure_window(*inputs(),kind,ORIGIN,ORIGIN+timedelta(days=14),trade_snapshot=snap)
        assert before['ledger'] == [{k:v for k,v in r.items() if k not in {'source_sales_qty','actual_blocked_qty'}} for r in after['ledger']]
        assert before['orders'] == after['orders'] and before['cases'] == after['cases'] and before['threshold_cases'] == after['threshold_cases']
    path = project_trade(snap,1,ORIGIN,ORIGIN,10,[4]*14,{})['projection']
    assert [r['projected_sales_qty'] for r in path[:4]] == [4,4,2,0]
    assert [r['unserved_stock_qty'] for r in path[:4]] == [0,0,2,4]


def test_fixed_origin_forecast_is_not_repeated_beyond_its_targets():
    snap = snapshot(effective=ORIGIN+timedelta(days=15))
    decision_day = ORIGIN+timedelta(days=5)
    path = project_trade(snap,1,decision_day,ORIGIN,0,list(range(1,15)),{})['projection']
    assert [r['forecast_input_qty'] for r in path] == list(range(6,15))
    assert path[-1]['date'] == str(ORIGIN+timedelta(days=14))
    assert limit_order(snap,1,ORIGIN,decision_day,10,path)['sellable_budget'] == 39
    snap['provider_notice_snapshot'][0]['events'][0]['effective_on'] = str(ORIGIN+timedelta(days=16))
    assert limit_order(snap,1,ORIGIN,decision_day,10,path)['cap_reason'] == 'insufficient_forecast_coverage'


def valid_frozen_run():
    snap = snapshot()
    snap.update(catalog_snapshot=[dict(item_id=1,sku='DEMO',product_type='eSIM',destination_country='Demo',carrier='DemoNet',first_seen_date='2024-01-01')],
        warehouse_snapshot=[dict(id=1,destination_country='Demo',carrier='DemoNet')],policies=[dict(item_id=1,supplier_id=1)])
    snap['provider_notice_snapshot'][0].update(scope_definition=dict(products=[dict(sku='DEMO',product_type='eSIM',destination_countries=['Demo'],warehouse_ids=[1])]),
        item_snapshot=[dict(id=1,supplier_id=1,warehouse_id=1,sku='DEMO',product_type='eSIM',destination_country='Demo',carrier='DemoNet')])
    return SimpleNamespace(kind='stock_projection',as_of_date=ORIGIN,config_snapshot=snap)


@pytest.mark.parametrize('mutation', ['missing_rules','wrong_rules','dual_profile','member','sku','market','warehouse','supplier','known_after_cutoff','version','target','source','assumed','unknown_profile'])
def test_independent_snapshot_validation_rejects_scope_history_and_rules(mutation):
    run = valid_frozen_run(); assert verify_trade_snapshot(run)
    snap=run.config_snapshot;n=snap['provider_notice_snapshot'][0];event=n['events'][0]
    if mutation=='missing_rules':snap.pop('trade_rules')
    elif mutation=='wrong_rules':snap['trade_rules']={**TRADE_RULES,'coverage_required':False}
    elif mutation=='dual_profile':snap['supply_lifecycle_profile']='notice7_sellthrough_v1'
    elif mutation=='member':n['item_ids']=[999]
    elif mutation=='sku':n['item_snapshot'][0]['sku']='WRONG'
    elif mutation=='market':n['scope_definition']['products'][0]['destination_countries']=['Elsewhere']
    elif mutation=='warehouse':n['item_snapshot'][0]['warehouse_id']=99
    elif mutation=='supplier':n['item_snapshot'][0]['supplier_id']=99
    elif mutation=='known_after_cutoff':event['known_on']=str(ORIGIN+timedelta(days=1))
    elif mutation=='version':event['version']=2
    elif mutation=='target':event['target_event_id']=3
    elif mutation=='source':event['source_description']=' '
    elif mutation=='assumed':event['is_assumed']=False
    else:snap['trade_lifecycle_profile']='unknown'
    with pytest.raises(DomainError):verify_trade_snapshot(run)


def enqueue_trade(client, source, forecast, item, kind, *, fixed_qty=5, cover=7, old_lot=True, period_days=14):
    policy = request(item,1).model_dump(mode='json'); policy.update(configured_rop_floor=10,fixed_order_qty=fixed_qty)
    assert client.post('/api/v1/supplier-item-policies',json=policy).status_code == 201
    response = client.post('/api/v1/scenarios',json=dict(name='Trade synthetic',code='trade',settings=dict(
        cover_days=cover,safety_multiplier=1.5,receipts_declared=True,policy_overrides=[],receipts_initial=[dict(
            item_id=item,ordered_on=str(D-timedelta(days=3)),eta=str(D+timedelta(days=4)),ordered_qty=20,lot_key='old')] if old_lot else [])))
    assert response.status_code == 201, response.text
    scenario = response.json()
    body = dict(kind=kind,as_of_date=str(D),source_import_run_id=str(source),forecast_run_id=str(forecast),scenario_id=scenario['id'],trade_lifecycle_profile=PROFILE)
    if kind.endswith('replay'):
        body.update(period_start=str(D+timedelta(days=1)),period_end=str(D+timedelta(days=period_days)))
    response = client.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'trade-worker'})
    assert response.status_code == 202, response.text
    return uuid.UUID(response.json()['run_id'])


@pytest.mark.parametrize('kind',['stock_projection','policy_replay','alert_replay'])
def test_real_worker_verification_and_tamper_rejection(pg,tmp_path,kind):
    _, sessions = pg
    source, forecast, item = worker_fixture(sessions,tmp_path); cfg=settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        scope=dict(products=[dict(sku='DEMO-ESIM-01',product_type='eSIM')])
        saved,_=create_notice(client,dict(action='stop',supplier_id=1,scope_definition=scope,known_on=str(D),effective_on=str(D+timedelta(days=3)),
            reason='Synthetic stop',source_description='Hypothetical only',expected_version=0))
        save_follow(client,follow_body(saved,known_on=str(D+timedelta(days=4)),effective_on=str(D+timedelta(days=8))))
        save_internal(client,item,internal_body())
        with sessions() as s:
            parents=[(r.config_sha256,digest(r.config_snapshot),r.source_sha256) for r in (s.get(Run,source),s.get(Run,forecast))]
        key=enqueue_trade(client,source,forecast,item,kind)
        serve(cfg,once=True)
        with sessions() as s:
            run=s.get(Run,key)
            diagnostic=cfg.output_root/str(key)/'failure.private.log'
            assert run.status=='complete', diagnostic.read_text() if diagnostic.exists() else run.error_code
            summary=deepcopy(run.result_summary)
            assert summary['actual_blocked_qty']==(0 if kind=='stock_projection' else 50 if kind=='policy_replay' else 120)
            assert summary['verification']['status']=='verified'
            assert parents==[(r.config_sha256,digest(r.config_snapshot),r.source_sha256) for r in (s.get(Run,source),s.get(Run,forecast))]
            alert=s.scalar(select(Alert).where(Alert.run_id==key,Alert.alert_type=='depletion').order_by(Alert.as_of_date))
            aid, original=alert.id,deepcopy(alert.explanation)
            assert all(o.is_initial for o in s.scalars(select(Replenishment).where(Replenishment.run_id==key)))
            assert verify_trade_snapshot(run)
        verify_run(cfg,sessions,key)
        response=client.get(f'/api/v1/runs/{key}/inventory')
        assert response.status_code==200, response.text # Trade reader opened in phase 5.
        for field,value in [('closing_blocked',999),('sales_blocked_qty',999),('sales_allowed',True),('unserved_stock_qty',999)]:
            with sessions.begin() as s:
                exp=deepcopy(original);exp['projection'][3][field]=value;s.get(Alert,aid).explanation=exp
            with pytest.raises(DomainError):verify_run(cfg,sessions,key)
        with sessions.begin() as s:s.get(Alert,aid).explanation=original
        for field,value in [('q_policy',999),('cap_reason','forged'),('sellable_budget',999),('replenishment_allowed',True)]:
            with sessions.begin() as s:
                exp=deepcopy(original);exp[field]=value;s.get(Alert,aid).explanation=exp
            with pytest.raises(DomainError):verify_run(cfg,sessions,key)
        with sessions.begin() as s:s.get(Alert,aid).explanation=original
        for field,value in [('actual_blocked_qty',999),('excluded_item_windows',999),('fill_allowed',0.123)]:
            with sessions.begin() as s:s.get(Run,key).result_summary={**summary,field:value}
            with pytest.raises(DomainError):verify_run(cfg,sessions,key)
        with sessions.begin() as s:s.get(Run,key).result_summary=summary
        verify_run(cfg,sessions,key)
        if kind != 'stock_projection':
            with sessions.begin() as s:
                event=s.scalar(select(InventoryEvent).where(InventoryEvent.run_id==key,InventoryEvent.event_kind=='receipt'))
                event_id, original_at=event.id,event.event_at
                event.event_at+=timedelta(days=1)
            with pytest.raises(DomainError):verify_run(cfg,sessions,key)
            with sessions.begin() as s:s.get(InventoryEvent,event_id).event_at=original_at
            with sessions.begin() as s:
                row=s.scalar(select(InventoryDaily).where(InventoryDaily.run_id==key,InventoryDaily.actual_blocked_qty>0))
                row_id=row.id;row.source_sales_qty+=1;row.actual_blocked_qty+=1
            with pytest.raises(DomainError):verify_run(cfg,sessions,key)
            with sessions.begin() as s:
                row=s.get(InventoryDaily,row_id);row.source_sales_qty-=1;row.actual_blocked_qty-=1
            verify_run(cfg,sessions,key)


@pytest.mark.parametrize('stop_day,fixed_qty,expected,reason', [
    (10,5,5,None),(10,20,0,'fixed_lot_exceeds_sellable_budget'),
    (7,5,0,'eta_at_or_after_provider_stop'),(16,5,0,'insufficient_forecast_coverage'),
])
def test_worker_whole_lot_cap_and_independent_budget(pg,tmp_path,stop_day,fixed_qty,expected,reason):
    _,sessions=pg
    source,forecast,item=worker_fixture(sessions,tmp_path);cfg=settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        create_notice(client,dict(action='stop',supplier_id=1,scope_definition=dict(products=[dict(
            sku='DEMO-ESIM-01',product_type='eSIM')]),
            known_on=str(D),effective_on=str(D+timedelta(days=stop_day)),reason='Synthetic cap',source_description='Simulation',expected_version=0))
        key=enqueue_trade(client,source,forecast,item,'policy_replay',fixed_qty=fixed_qty,cover=3,old_lot=False)
        serve(cfg,once=True)
        with sessions() as s:
            run=s.get(Run,key);log=cfg.output_root/str(key)/'failure.private.log'
            assert run.status=='complete',log.read_text() if log.exists() else run.error_code
            row=s.scalar(select(InventoryDaily).where(InventoryDaily.run_id==key,InventoryDaily.date==D))
            assert row.recommended_qty==expected
            alert=s.scalar(select(Alert).where(Alert.run_id==key,Alert.alert_type=='depletion',Alert.as_of_date==D))
            assert alert.explanation['cap_reason']==reason
            assert alert.explanation['q_policy']==fixed_qty
            assert alert.explanation['sellable_budget']==(12 if stop_day==10 else None)
        verify_run(cfg,sessions,key)


@pytest.mark.parametrize('kind',['stock_projection','policy_replay','alert_replay'])
def test_unrestricted_worker_has_baseline_metric_parity(pg,tmp_path,kind):
    _,sessions=pg
    source,forecast,item=worker_fixture(sessions,tmp_path);cfg=settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        key=enqueue_trade(client,source,forecast,item,kind)
        serve(cfg,once=True)
        with sessions() as s:
            run=s.get(Run,key);log=cfg.output_root/str(key)/'failure.private.log'
            assert run.status=='complete',log.read_text() if log.exists() else run.error_code
            assert run.result_summary['actual_blocked_qty']==0 and run.result_summary['metric_exclusions']==[]
            if kind=='alert_replay':
                assert run.result_summary['alert_metrics']['excluded_count']==0
        verify_run(cfg,sessions,key)


def test_two_alert_windows_keep_separate_knowledge_prefixes(pg,tmp_path):
    from modules.forecasting.models import DailySales
    _,sessions=pg
    source,forecast,item=worker_fixture(sessions,tmp_path);cfg=settings(tmp_path)
    path=tmp_path/'data/sigma_sim_data_orders.csv'
    with path.open(newline='',encoding='utf-8') as stream:
        reader=csv.DictReader(stream); rows=list(reader); fields=reader.fieldnames
    extra=[]
    for h in range(15,29):
        row=dict(rows[-1],order_id=f'SYN-WINDOW-{h}',order_datetime=str(D+timedelta(days=h))+'T12:00:00Z')
        extra.append(row)
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows+extra)
    with sessions.begin() as s:
        checksum=hashlib.sha256(path.read_bytes()).hexdigest()
        s.get(Run,source).source_sha256=s.get(Run,forecast).source_sha256=checksum
        s.add_all([DailySales(source_import_run_id=source,item_id=item,date=D+timedelta(days=h),sales_qty=10,order_count=1,actual_available=True) for h in range(15,29)])
    with TestClient(create_app(cfg)) as client:
        create_notice(client,dict(action='stop',supplier_id=1,scope_definition=dict(products=[dict(
            sku='DEMO-ESIM-01',product_type='eSIM')]),
            known_on=str(D+timedelta(days=5)),effective_on=str(D+timedelta(days=3)),reason='Synthetic late notice',source_description='Simulation',expected_version=0))
        key=enqueue_trade(client,source,forecast,item,'alert_replay',period_days=28)
        serve(cfg,once=True)
        with sessions() as s:
            run=s.get(Run,key);log=cfg.output_root/str(key)/'failure.private.log'
            assert run.status=='complete',log.read_text() if log.exists() else run.error_code
            summary=run.result_summary
            assert summary['windows']==2 and summary['excluded_item_windows']==1
            assert summary['source_sales_qty']==280 and summary['scenario_sales_qty']==summary['actual_blocked_qty']==140
            assert summary['metric_exclusions'][0]['window_origin']==str(D+timedelta(days=14))
            assert summary['alert_metrics']['excluded_count']==1
            # The first window starts at stock21 below forecast-derived ROP26;
            # the second is separately excluded by its known provider stop.
            assert summary['threshold_metrics']['excluded_count']==2
        verify_run(cfg,sessions,key)
