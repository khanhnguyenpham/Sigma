"""Frozen supply read models and full-scope exports, synthetic data only."""
from copy import deepcopy
from datetime import timedelta
import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from core.hashes import digest
from main import create_app
from modules.alerts.models import Alert
from modules.catalog.models import ItemSupplyChange
from modules.runs.models import Run
from test_postgres_api import settings, D
from test_configurable_inventory import worker_fixture, enqueue_fixture
from test_workspace_api import workspace_fixture
from worker import serve


def complete_plan(sessions,tmp_path,kind):
    source,forecast,item=worker_fixture(sessions,tmp_path)
    client=TestClient(create_app(settings(tmp_path)))
    result=client.post(f'/api/v1/products/{item}/supply-changes',json=dict(action='stop',
        known_on=str(D-timedelta(days=7)),effective_on=str(D),reason='Synthetic notice',expected_version=0))
    assert result.status_code==201,result.text
    key=enqueue_fixture(client,source,forecast,item,'days','fixed',kind)
    assert serve(settings(tmp_path),once=True)==key
    with sessions() as s:
        row=s.get(Run,key);assert row.status=='complete',row.error_code
    return client,key,item


@pytest.mark.parametrize('kind',['stock_projection','policy_replay','alert_replay'])
def test_sell_through_api_export_and_frozen_context(pg,tmp_path,kind):
    _,sessions=pg;c,key,item=complete_plan(sessions,tmp_path,kind)
    with c:
        base=f'/api/v1/runs/{key}'
        result=c.get(base+'/sell-through?page_size=3');assert result.status_code==200,result.text
        data=result.json();assert data['total']==14 and len(data['items'])==3
        assert data['context']['run_id']==str(key) and data['context']['projection_as_of_date']==str(D)
        first=data['items'][0]
        assert first['item_id']==item and first['supply_status']=='stopped' and first['replenishment_allowed'] is False
        assert first['forecast_demand_qty']==first['projected_sales_qty']+first['unserved_demand_qty']
        assert c.get(base+'/sell-through?page=2&page_size=3').json()['items'][0]['horizon_day']==4
        query=f'?as_of_date={D}&warehouse_id=1&item_id={item}&supplier_id=1&product_type=eSIM&date_from={D+timedelta(days=2)}&date_to={D+timedelta(days=5)}'
        filtered=c.get(base+'/sell-through'+query).json();assert filtered['total']==4
        exported=c.get(base+'/exports/sell_through'+query+'&page=3&page_size=1')
        rows=list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))));assert len(rows)==4
        assert [r['target_date'] for r in rows]==[r['target_date'] for r in filtered['items']]
        assert all(r['run_id']==str(key) and r['config_sha256'] for r in rows)
        assert c.get(base+'/sell-through?warehouse_id=999').json()['total']==0
        assert c.get(base+'/sell-through?state=low_stock').status_code==422
        assert c.get(base+f'/sell-through?date_from={D+timedelta(days=5)}&date_to={D}').status_code==422
        assert c.get(base+'/sell-through?aggregate=route_day&page_size=1').json()['total']==14
        assert c.get(base+'/sell-through?aggregate=route_day&page_size=1').json()['items'][0]['projected_sales_qty']==first['projected_sales_qty']
        inventory=c.get(base+f'/inventory?date_from={D}&date_to={D}').json()['items'][0]
        assert inventory['supply_status']=='stopped' and inventory['replenishment_block_reason']=='supply_stopped'
        signals=c.get(base+f'/alerts?as_of_date={D}').json()['items']
        assert signals and all(r['replenishment_allowed'] is False for r in signals)
        workspace=c.get(base+f'/workspace?as_of_date={D}').json()
        assert workspace['summary']['supply_stopped_items']==1 and workspace['summary']['healthy_items']==0
        assert workspace['summary']['recommended_units']==0
        assert workspace['attention']==[]
        purchasing=c.get(base+f'/purchasing?as_of_date={D}').json()
        assert purchasing['summary']['recommended_items']==0
        incoming=c.get(base+f'/purchasing?as_of_date={D}&view=incoming').json()
        assert incoming['items'] and incoming['items'][0]['supply_status']=='stopped'
        if kind!='stock_projection':
            for offset,state in [(3,'waiting_receipts'),(4,'selling_remaining'),(5,'sold_out')]:
                on=D+timedelta(days=offset)
                actual=c.get(base+f'/inventory?date_from={on}&date_to={on}').json()['items'][0]
                assert actual['sell_through_state']==state
        # Unknown orders must not be exposed by an as-of lot read.
        assert all(r['ordered_on']<=str(D) for r in c.get(base+f'/replenishments?as_of_date={D}').json()['items'])
        # A later live resume must not change a frozen plan's output.
        before=deepcopy(data)
        with sessions() as s:stop=s.scalar(select(ItemSupplyChange))
        assert c.post(f'/api/v1/products/{item}/supply-changes',json=dict(action='resume',known_on=str(D),effective_on=str(D),target_change_id=stop.id,reason='Synthetic resume',expected_version=1)).status_code==201
        assert c.get(base+'/sell-through?page_size=3').json()==before


def test_old_run_requires_new_plan_and_reads_do_not_backfill(pg,tmp_path):
    _,sessions=pg;key,parent,item=workspace_fixture(sessions)
    with sessions() as s:before=(deepcopy(s.get(Run,key).config_snapshot),s.get(Run,key).config_sha256)
    with TestClient(create_app(settings(tmp_path))) as c:
        base=f'/api/v1/runs/{key}'
        assert c.get(base+'/sell-through').json()['error']['code']=='feature_not_in_run'
        assert c.get(base+'/exports/sell_through').status_code==409
        assert c.get(f'/api/v1/runs/{parent}/sell-through').status_code==409
        assert c.get(base+f'/inventory?date_from={D}&date_to={D}').json()['items'][0]['supply_status'] is None
    with sessions() as s:assert (s.get(Run,key).config_snapshot,s.get(Run,key).config_sha256)==before


def test_route_totals_count_all_items_before_pagination_and_csv_batches(pg,tmp_path):
    _,sessions=pg;c,key,item=complete_plan(sessions,tmp_path,'stock_projection')
    # A large frozen synthetic catalog exercises export beyond its 5000-row batch.
    from modules.catalog.models import Item
    with sessions.begin() as s:
        run=s.get(Run,key);snapshot=deepcopy(run.config_snapshot)
        alert=s.scalar(select(Alert).where(Alert.run_id==key,Alert.alert_type=='depletion'))
        for n in range(359):
            row=Item(warehouse_id=1,sku=f'SYN-{n}',product_type='eSIM',first_seen_date=D)
            s.add(row);s.flush()
            snapshot['catalog_snapshot'].append({**snapshot['catalog_snapshot'][0],'item_id':row.id,'sku':row.sku})
            attrs={col.name:getattr(alert,col.name) for col in Alert.__table__.columns if col.name not in {'id','created_at'}}
            attrs.update(item_id=row.id,explanation=deepcopy(alert.explanation))
            s.add(Alert(**attrs))
        run.config_snapshot=snapshot;run.config_sha256=digest(snapshot)
    with c:
        base=f'/api/v1/runs/{key}'
        one=c.get(base+'/sell-through?page_size=1').json();assert one['total']==5040
        aggregate=c.get(base+'/sell-through?aggregate=route_day&page_size=1').json()
        assert aggregate['total']==14 and aggregate['items'][0]['item_count']==360
        assert aggregate['items'][0]['projected_sales_qty']==360*one['items'][0]['projected_sales_qty']
        result=c.get(base+'/exports/sell_through')
        rows=list(csv.DictReader(io.StringIO(result.text.lstrip('\ufeff'))));assert len(rows)==5040
        assert len({(r['item_id'],r['target_date']) for r in rows})==5040



def test_replay_boundary_selects_one_inventory_window_and_its_lots():
    from modules.reporting.supply import operational_rows
    old=dict(item_id=1,window_origin=D,closing_qty=0)
    new=dict(item_id=1,window_origin=D+timedelta(days=14),closing_qty=10)
    lots=[dict(item_id=1,window_origin=D),dict(item_id=1,window_origin=D+timedelta(days=14))]
    inventory,incoming=operational_rows([old,new],lots)
    assert inventory==[new] and incoming==[lots[1]]


def test_profile_without_stored_sell_through_requires_new_plan(pg,tmp_path):
    _,sessions=pg;key,_,_=workspace_fixture(sessions)
    with sessions.begin() as s:
        run=s.get(Run,key);snapshot=deepcopy(run.config_snapshot)
        snapshot.update(supply_lifecycle_profile='notice7_sellthrough_v1',supply_lifecycle_snapshot=[])
        run.config_snapshot=snapshot;run.config_sha256=digest(snapshot)
    with TestClient(create_app(settings(tmp_path))) as c:
        for path in (None,[],[{}]*14):
            with sessions.begin() as s:
                row=s.scalar(select(Alert).where(Alert.run_id==key,Alert.alert_type=='depletion'))
                row.explanation={'projection':path}
            response=c.get(f'/api/v1/runs/{key}/sell-through')
            assert response.status_code==409 and response.json()['error']['code']=='feature_not_in_run'
