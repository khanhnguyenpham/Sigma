"""Frozen trade API/CSV parity, scope totals and historical compatibility."""
from copy import deepcopy
from datetime import timedelta
import csv,io,json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from core.hashes import digest
from main import create_app
from modules.runs.models import Run
from modules.alerts.models import Alert
from modules.catalog.models import Item
from modules.configuration.models import Policy
from modules.inventory.models import InventoryDaily
from modules.catalog.trade_service import TRADE_PROFILE
from test_postgres_api import settings,D
from test_configurable_inventory import worker_fixture
from test_trade_simulation import enqueue_trade
from test_trade_api import create_notice,save_internal,internal_body,save_follow,follow_body
from test_workspace_api import workspace_fixture
from worker import serve


def plan(sessions,tmp_path,kind='policy_replay',*,internal=True):
    source,forecast,item=worker_fixture(sessions,tmp_path)
    client=TestClient(create_app(settings(tmp_path)))
    saved,_=create_notice(client,dict(action='stop',supplier_id=1,expected_version=0,known_on=str(D),effective_on=str(D),
        reason='=Declared provider simulation',source_description='@Hypothetical source',scope_definition=dict(products=[dict(
            sku='DEMO-ESIM-01',product_type='eSIM')])))
    if internal:save_internal(client,item,internal_body(reason='=Internal simulation'))
    key=enqueue_trade(client,source,forecast,item,kind)
    assert serve(settings(tmp_path),once=True)==key
    with sessions() as s:
        run=s.get(Run,key);log=settings(tmp_path).output_root/str(key)/'failure.private.log'
        assert run.status=='complete',log.read_text() if log.exists() else run.error_code
    return client,key,item,saved


def csv_rows(response):
    assert response.status_code==200,response.text
    return list(csv.DictReader(io.StringIO(response.text.lstrip('\ufeff'))))


@pytest.mark.parametrize('kind',['stock_projection','policy_replay','alert_replay'])
def test_trade_inventory_projection_workspace_purchasing_and_exports(pg,tmp_path,kind):
    _,sessions=pg;c,key,item,_=plan(sessions,tmp_path,kind)
    with c:
        root=f'/api/v1/runs/{key}'
        inventory=c.get(root+f'/inventory?as_of_date={D}&page_size=1').json()
        row=inventory['items'][0]
        assert row['internal_status']==row['provider_status']=='stopped'
        assert not row['replenishment_allowed'] and not row['sales_allowed']
        assert row['total_qty']==row['blocked_qty']==21 and row['sellable_qty']==0
        assert row['q_policy']==row['q_final']==0 and row['cap_reason']=='provider_blocked'
        assert row['quantity_diagnostics_available'] and row['needs_supplier_action']
        assert inventory['context']['trade_lifecycle_profile']==TRADE_PROFILE
        assert inventory['context']['config_sha256'] and inventory['context']['units']=='quantity'
        query=f'?as_of_date={D}&internal_status=stopped&provider_status=stopped&sales_allowed=false&supplier_id=1&window_origin={D}'
        data=c.get(root+'/sell-through'+query+'&page_size=1').json()
        assert data['total']==14 and len(data['items'])==1
        projected=data['items'][0]
        assert projected['forecast_input_qty']==projected['sales_blocked_qty']==2
        assert projected['projected_sales_qty']==projected['unserved_stock_qty']==0
        exported=csv_rows(c.get(root+'/exports/sell_through'+query+'&page=10&page_size=1'))
        assert len(exported)==14 and exported[0]['target_date']==str(D+timedelta(days=1))
        assert all(r['trade_lifecycle_profile']==TRADE_PROFILE and r['config_sha256'] for r in exported)
        assert float(exported[3]['closing_blocked'])==41
        aggregate=c.get(root+'/sell-through'+query+'&aggregate=route_day&page_size=1').json()
        assert aggregate['total']==14 and aggregate['items'][0]['provider_blocked_items']==1
        assert aggregate['items'][0]['affected_items']==1
        assert aggregate['items'][0]['provider_notice_ids'] and aggregate['items'][0]['provider_sources']
        signals=c.get(root+f'/alerts?as_of_date={D}&sales_allowed=false')
        assert signals.status_code==200,signals.text
        assert all(r['provider_status']=='stopped' and r['replenishment_block_reasons']==['internal_stopped','provider_blocked'] for r in signals.json()['items'])
        workspace=c.get(root+f'/workspace?as_of_date={D}').json()
        for field in ['internal_stopped_items','provider_blocked_items','blocked_stock_items','affected_items']:
            assert workspace['summary'][field]==1
        assert workspace['summary']['healthy_items']==0 and workspace['summary']['blocked_units']==21
        assert workspace['attention']==[]
        lots=c.get(root+f'/purchasing?as_of_date={D}&view=incoming').json()
        assert lots['summary']['affected_items']==1 and lots['items'][0]['needs_supplier_action']
        assert lots['items'][0]['eta']==str(D+timedelta(days=4)) and not lots['items'][0]['sales_allowed_at_eta']
        lot_csv=csv_rows(c.get(root+f'/purchasing/export?as_of_date={D}&view=incoming'))
        assert len(lot_csv)==1 and json.loads(lot_csv[0]['provider_notice_ids'])==lots['items'][0]['provider_notice_ids']
        inv_csv=csv_rows(c.get(root+f'/exports/inventory_daily?as_of_date={D}'))
        assert inv_csv[0]['internal_reason'].startswith("'=") and json.loads(inv_csv[0]['provider_reasons'])[0].startswith('=')
        if kind!='stock_projection':
            at=D+timedelta(days=4)
            recorded=c.get(root+f'/inventory?as_of_date={at}').json()['items'][0]
            assert recorded['receipts_qty']==20 and recorded['total_qty']==recorded['blocked_qty']==41
            assert recorded['source_sales_qty']==recorded['actual_blocked_qty']==10 and recorded['scenario_sales_qty']==0
            assert recorded['needs_supplier_action']
            history=c.get(root+f'/purchasing?as_of_date={at}&view=history').json()['items'][0]
            assert history['status']=='received' and history['needs_supplier_action'] and history['stock_impact_available']
            if kind=='alert_replay':
                assert not recorded['quantity_diagnostics_available'] and recorded['q_policy'] is None
            raw=c.get(root+f'/metrics?granularity=policy' if kind=='policy_replay' else root+'/metrics?granularity=alert').json()['items'][0]
            assert raw['source_sales_qty']==raw['actual_blocked_qty']==140 and raw['scenario_sales_qty']==0 and raw['fill_allowed'] is None


def test_metrics_filters_select_whole_windows_and_keep_exclusions(pg,tmp_path):
    _,sessions=pg;c,key,item,_=plan(sessions,tmp_path,'alert_replay',internal=False)
    with c:
        root=f'/api/v1/runs/{key}'
        for suffix in ['',f'&item_id={item}',f'&as_of_date={D}&provider_status=stopped',f'&date_from={D}&date_to={D}&sales_allowed=false']:
            response=c.get(root+'/metrics?granularity=alert'+suffix)
            assert response.status_code==200,response.text
            row=response.json()['items'][0]
            assert row['event_denominator']==0 and row['excluded_count']==row['excluded_item_windows']==1
            assert row['source_sales_qty']==140 and row['scenario_sales_qty']==0 and row['actual_blocked_qty']==140
            assert len(row['metric_exclusions'][0]['blocked_dates'])==15
        no_origin=c.get(root+f'/metrics?as_of_date={D+timedelta(days=1)}&granularity=threshold').json()
        assert no_origin['items']==[] and no_origin['total']==0
        rows=csv_rows(c.get(root+'/exports/metrics?granularity=alert&sales_allowed=false&page_size=1&page=20'))
        assert len(rows)==1 and rows[0]['source_sales_qty']=='140'
        assert json.loads(rows[0]['metric_exclusions'])[0]['item_id']==item
        assert c.get(root+'/metrics?granularity=allocated_daily&sales_allowed=false').status_code==422
        assert c.get(root+'/metrics?granularity=allocated_daily&item_id=1').status_code==422


def test_scoped_unrestricted_metrics_match_stored_tp_fn_and_denominators(pg,tmp_path):
    _,sessions=pg;source,forecast,item=worker_fixture(sessions,tmp_path)
    with TestClient(create_app(settings(tmp_path))) as c:
        key=enqueue_trade(c,source,forecast,item,'alert_replay')
        serve(settings(tmp_path),once=True)
        with sessions() as s:
            run=s.get(Run,key);assert run.status=='complete',run.error_code
            metrics=deepcopy(run.result_summary['metrics'])
        root=f'/api/v1/runs/{key}'
        for expected in metrics:
            response=c.get(root+f"/metrics?item_id={item}&granularity={expected['granularity']}")
            assert response.status_code==200,response.text
            actual=response.json()['items'][0]
            assert {k:actual[k] for k in expected}==expected
            assert actual['source_sales_qty']==actual['scenario_sales_qty']==140
            assert actual['actual_blocked_qty']==0 and actual['metric_exclusions']==[]


def test_live_resume_does_not_change_results_and_reads_do_not_write(pg,tmp_path):
    _,sessions=pg;c,key,item,saved=plan(sessions,tmp_path)
    paths=['inventory','sell-through','alerts','metrics',f'workspace?as_of_date={D}',f'purchasing?as_of_date={D}&view=incoming']
    with c:
        root=f'/api/v1/runs/{key}/'
        before={p:c.get(root+p).json() for p in paths}
        with sessions() as s:
            snapshot=(deepcopy(s.get(Run,key).config_snapshot),deepcopy(s.get(Run,key).result_summary),s.get(Run,key).artifact_manifest)
            stored={t:s.execute(text(f'SELECT row_to_json(r)::text FROM {t} r WHERE run_id=:key ORDER BY id'),{'key':key}).scalars().all()
                for t in ('inventory_daily','inventory_events','alerts','replenishment_orders')}
        save_follow(c,follow_body(saved))
        assert {p:c.get(root+p).json() for p in paths}==before
        with sessions() as s:
            assert snapshot==(s.get(Run,key).config_snapshot,s.get(Run,key).result_summary,s.get(Run,key).artifact_manifest)
            assert stored=={t:s.execute(text(f'SELECT row_to_json(r)::text FROM {t} r WHERE run_id=:key ORDER BY id'),{'key':key}).scalars().all()
                for t in stored}


@pytest.mark.parametrize('query',['provider_status=bogus','internal_status=clear','sales_allowed=maybe','window_origin=wrong','unexpected=1'])
def test_trade_filter_validation_is_explicit(pg,tmp_path,query):
    _,sessions=pg;key,_,_=workspace_fixture(sessions)
    with TestClient(create_app(settings(tmp_path))) as c:
        assert c.get(f'/api/v1/runs/{key}/inventory?{query}').status_code==422


def test_legacy_feature_availability_and_new_filters_never_assume_rights(pg,tmp_path):
    _,sessions=pg;key,_,_=workspace_fixture(sessions)
    with TestClient(create_app(settings(tmp_path))) as c:
        root=f'/api/v1/runs/{key}'
        row=c.get(root+'/inventory').json()['items'][0]
        assert 'sales_allowed' not in row and 'source_sales_qty' not in row and 'blocked_qty' not in row
        for endpoint in ['inventory','alerts','replenishments','sell-through']:
            response=c.get(root+'/'+endpoint+'?sales_allowed=false')
            assert response.status_code==409 and response.json()['error']['code']=='feature_not_in_run'


def test_full_scope_aggregate_and_csv_cross_batch_preserve_stored_values(pg,tmp_path):
    _,sessions=pg;c,key,item,_=plan(sessions,tmp_path,'stock_projection')
    with sessions.begin() as s:
        run=s.get(Run,key);snapshot=deepcopy(run.config_snapshot)
        original=s.scalar(select(Alert).where(Alert.run_id==key,Alert.alert_type=='depletion'))
        for n in range(359):
            product=Item(warehouse_id=1,sku=f'SYN-READ-{n}',product_type='eSIM',first_seen_date=D)
            s.add(product);s.flush()
            snapshot['catalog_snapshot'].append(dict(snapshot['catalog_snapshot'][0],item_id=product.id,sku=product.sku))
            snapshot['receiving_warehouse_snapshot'].append(dict(snapshot['receiving_warehouse_snapshot'][0],item_id=product.id))
            notice=snapshot['provider_notice_snapshot'][0]
            notice['item_ids'].append(product.id)
            notice['item_snapshot'].append(dict(notice['item_snapshot'][0],id=product.id,sku=product.sku))
            notice['scope_definition']['products'].append(dict(notice['scope_definition']['products'][0],sku=product.sku))
            snapshot['internal_supply_snapshot'].append(dict(snapshot['internal_supply_snapshot'][0],id=n+2,item_id=product.id))
            attrs={col.name:getattr(original,col.name) for col in Alert.__table__.columns if col.name not in {'id','created_at'}}
            exp=deepcopy(original.explanation)
            for row in exp['projection']:row['internal_stop_change_id']=n+2
            s.add(Alert(**dict(attrs,item_id=product.id,explanation=exp)))
        run.config_snapshot=snapshot;run.config_sha256=digest(snapshot)
    with c:
        root=f'/api/v1/runs/{key}'
        result=c.get(root+'/sell-through?provider_status=stopped&page_size=1').json()
        assert result['total']==5040 and len(result['items'])==1
        aggregate=c.get(root+'/sell-through?provider_status=stopped&aggregate=route_day&page_size=1').json()
        assert aggregate['total']==14 and aggregate['items'][0]['item_count']==360
        assert aggregate['items'][0]['sales_blocked_qty']==720 and aggregate['items'][0]['projected_sales_qty']==0
        rows=csv_rows(c.get(root+'/exports/sell_through?provider_status=stopped&page=40&page_size=1'))
        assert len(rows)==5040 and len({(r['item_id'],r['target_date']) for r in rows})==5040
        # No producer may run in a read: a stored diagnostic value is returned verbatim.
        with sessions.begin() as s:
            row=s.get(Alert,original.id);exp=deepcopy(row.explanation);exp['projection'][0]['projected_sales_qty']=123.5;row.explanation=exp
        assert c.get(root+f'/sell-through?item_id={item}&page_size=1').json()['items'][0]['projected_sales_qty']==123.5


def test_mixed_scope_filters_and_totals_precede_pagination(pg,tmp_path):
    _,sessions=pg;c,key,item,_=plan(sessions,tmp_path,'stock_projection')
    with sessions.begin() as s:
        run=s.get(Run,key);snap=deepcopy(run.config_snapshot)
        product=Item(warehouse_id=1,sku='OUTSIDE',product_type='eSIM',first_seen_date=D);s.add(product);s.flush()
        p=s.get(Policy,snap['policies'][0]['id'])
        attrs={col.name:getattr(p,col.name) for col in Policy.__table__.columns if col.name not in {'id','created_at'}}
        p2=Policy(**dict(attrs,item_id=product.id));s.add(p2);s.flush()
        snap['policies'].append(dict(snap['policies'][0],item_id=product.id,id=p2.id))
        snap['catalog_snapshot'].append(dict(snap['catalog_snapshot'][0],item_id=product.id,sku=product.sku))
        snap['receiving_warehouse_snapshot'].append(dict(snap['receiving_warehouse_snapshot'][0],item_id=product.id))
        first=s.scalar(select(InventoryDaily).where(InventoryDaily.run_id==key))
        attrs={col.name:getattr(first,col.name) for col in InventoryDaily.__table__.columns if col.name!='id'}
        s.add(InventoryDaily(**dict(attrs,item_id=product.id,policy_id=p2.id,pending_qty=0,inventory_position=21)))
        original=s.scalar(select(Alert).where(Alert.run_id==key,Alert.alert_type=='depletion'))
        exp=deepcopy(original.explanation);exp['policy']=snap['policies'][-1];exp['receipts']=[]
        exp.update(internal_status='active',provider_status='clear',replenishment_allowed=True,sales_allowed=True,
            internal_reason=None,internal_stop_change_id=None,internal_version=0,provider_blockers=[],provider_restrictions=[],
            cap_reason=None,provider_stop_on=None,blocked_qty=0,sellable_qty=21,needs_supplier_action=False)
        stock=21
        for row in exp['projection']:
            available=stock;sold=min(row['forecast_input_qty'],available);stock-=sold
            row.update(internal_status='active',provider_status='clear',replenishment_allowed=True,sales_allowed=True,
                internal_reason=None,internal_stop_change_id=None,internal_version=0,provider_blockers=[],provider_restrictions=[],
                available_total=available,sellable_qty=available,blocked_stock_before_sale=0,receipts_qty=0,
                projected_sales_qty=sold,sales_blocked_qty=0,unserved_stock_qty=row['forecast_input_qty']-sold,
                unserved_demand_qty=row['forecast_input_qty']-sold,closing_forecast=stock,closing_total=stock,closing_sellable=stock,closing_blocked=0)
        attrs={col.name:getattr(original,col.name) for col in Alert.__table__.columns if col.name not in {'id','created_at'}}
        s.add(Alert(**dict(attrs,item_id=product.id,explanation=exp)))
        run.config_snapshot=snap;run.config_sha256=digest(snap)
    with c:
        root=f'/api/v1/runs/{key}'
        response=c.get(root+f'/inventory?as_of_date={D}&page_size=1').json()
        assert response['total']==2 and len(response['items'])==1
        clear=c.get(root+f'/inventory?as_of_date={D}&internal_status=active&provider_status=clear&sales_allowed=true&sku=OUTSIDE&carrier=DemoCarrier&destination_country=DemoLand').json()
        assert clear['total']==1 and clear['items'][0]['item_id']==product.id
        assert clear['items'][0]['sellable_qty']==21 and clear['items'][0]['blocked_qty']==0
        assert c.get(root+'/inventory?sku=OUTSIDE&sales_allowed=false').json()['total']==0
        summary=c.get(root+f'/workspace?as_of_date={D}').json()['summary']
        assert clear['items'][0]['closing_qty']==21 < clear['items'][0]['rop']==26
        assert summary['item_count']==2 and summary['healthy_items']==0
        assert summary['low_stock_items']==2  # Raw low-stock diagnostics include the blocked item.
        assert summary['affected_items']==summary['provider_blocked_items']==summary['internal_stopped_items']==1
        assert summary['total_units']==42 and summary['sellable_units']==summary['blocked_units']==21
        route=c.get(root+'/sell-through?aggregate=route_day&page_size=1').json()['items'][0]
        assert route['item_count']==2 and route['forecast_input_qty']==4
        assert route['projected_sales_qty']==route['sales_blocked_qty']==2
        blocked=c.get(root+'/sell-through?sales_allowed=false&aggregate=route_day&page_size=1').json()['items'][0]
        assert blocked['item_count']==1 and blocked['projected_sales_qty']==0
        assert len(csv_rows(c.get(root+'/exports/sell_through?sales_allowed=true&page_size=1&page=20')))==14


def test_boundary_selects_latest_window_before_operational_rights_filter(pg,tmp_path):
    _,sessions=pg;c,key,item,_=plan(sessions,tmp_path,'stock_projection',internal=False)
    at=D+timedelta(days=14)
    with sessions.begin() as s:
        run=s.get(Run,key);snap=deepcopy(run.config_snapshot)
        snap['provider_notice_snapshot'][0]['events'][0]['known_on']=str(D+timedelta(days=5))
        run.kind='alert_replay';run.period_start=D+timedelta(days=1);run.period_end=D+timedelta(days=28)
        run.config_snapshot=snap;run.config_sha256=digest(snap)
        original=s.scalar(select(InventoryDaily).where(InventoryDaily.run_id==key))
        attrs={col.name:getattr(original,col.name) for col in InventoryDaily.__table__.columns if col.name!='id'}
        s.add(InventoryDaily(**dict(attrs,date=at,pending_qty=0,inventory_position=21)))
        s.add(InventoryDaily(**dict(attrs,date=at,window_origin=at,forecast_as_of_date=at,
            opening_qty=41,closing_qty=41,pending_qty=0,inventory_position=41)))
    with c:
        root=f'/api/v1/runs/{key}'
        all_rows=c.get(root+f'/inventory?as_of_date={at}').json()
        assert all_rows['total']==2
        summary=c.get(root+f'/workspace?as_of_date={at}&sales_allowed=false').json()['summary']
        assert summary['item_count']==1 and summary['blocked_units']==41
        empty=c.get(root+f'/workspace?as_of_date={at}&sales_allowed=true').json()['summary']
        assert empty['item_count']==0 and empty['total_units'] is None
        assert c.get(root+f'/purchasing?as_of_date={at}&sales_allowed=true').json()['summary']['inventory_available'] is False
        old=c.get(root+f'/workspace?as_of_date={at}&window_origin={D}&sales_allowed=true').json()['summary']
        assert old['item_count']==1 and old['sellable_units']==21


def test_preview_uses_trade_stored_quantities_without_recalculating_proposal(pg,tmp_path):
    _,sessions=pg;c,key,item,_=plan(sessions,tmp_path,'stock_projection',internal=False)
    with c:
        response=c.post(f'/api/v1/products/{item}/internal-stop-preview',json=dict(internal_body(),impact_run_id=str(key),impact_as_of_date=str(D)))
        assert response.status_code==200,response.text
        data=response.json()
        assert data['impact']['rights_quantities_available']
        assert data['stock_qty']==data['blocked_qty']==data['impact']['blocked_qty']==21
        assert data['sellable_qty']==data['impact']['sellable_qty']==0
        assert data['frozen_cap_reason']=='provider_blocked'


@pytest.mark.parametrize('change',[{'trade_lifecycle_profile':'unknown'}, {'trade_rules':{}}, {'trade_lifecycle_profile':None}])
def test_malformed_trade_snapshot_does_not_fall_back_to_legacy(pg,tmp_path,change):
    _,sessions=pg;c,key,_,_=plan(sessions,tmp_path,'stock_projection')
    with sessions.begin() as s:
        run=s.get(Run,key);snap=deepcopy(run.config_snapshot);snap.update(change)
        run.config_snapshot=snap;run.config_sha256=digest(snap)
    with c:
        response=c.get(f'/api/v1/runs/{key}/inventory')
        assert response.status_code==409 and response.json()['error']['code']=='invalid_trade_history'
