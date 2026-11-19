from datetime import date, timedelta, datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from modules.operations.planning import calculate, calculate_threshold
from modules.operations.models import StockDocument, StockBalance
from modules.forecasting.models import ItemForecast
from modules.runs.models import Run
from modules.configuration.models import Policy
from test_auth import auth_app, login
from test_operations import setup_catalog, post, draft, confirm, movement

D = date(2026, 11, 15)
def vector(origin=D, days=14):
    return {origin+timedelta(days=i): 2 for i in range(1, days+1)}

def test_fixed_lot_uses_only_timely_incoming_and_flags_early_shortage():
    result = calculate(3, {D+timedelta(days=12):20}, vector(),7,2,0,15,D)
    assert result['rop']==18 and result['safety_stock']==4
    assert result['pending_qty']==20 and result['eligible_pending_qty']==0
    assert result['recommended_qty']==15 and result['shortage_before_new_eta']
    assert len(result['projection'])==14

def test_overdue_is_not_assumed_received_or_automatically_reordered():
    result = calculate(0,{D:10},vector(),7,2,0,15,D)
    assert result['decision']=='review_overdue' and result['recommended_qty'] is None
    assert result['projection'][0]['receipts_qty']==0

@pytest.mark.parametrize('lead',[14,30,365])
def test_short_forecast_never_padded_for_long_supplier_lead(lead):
    result = calculate(1,{},vector(),lead,2,0,15,D)
    assert result['reason']=='forecast_horizon_short' and result['recommended_qty'] is None

def test_gap_and_zero_demand_are_not_confused():
    forecast = vector(); forecast.pop(D+timedelta(days=3))
    assert calculate(0,{},forecast,7,0,0,15,D)['reason']=='forecast_incomplete'
    result = calculate(100,{},dict.fromkeys(vector(),0),7,0,0,15,D)
    assert result['rop']==0 and result['recommended_qty']==0

def test_yesterday_forecast_remaining13_days_without_copying_day14():
    result = calculate(10,{},vector(days=13),7,2,0,15,D)
    assert result['available_days']==13 and len(result['projection'])==13
    assert calculate(10,{},vector(days=13),13,2,0,15,D)['recommended_qty'] is None

def seed_forecast(sessions, item, supplier, origin):
    with sessions.begin() as session:
        base = dict(as_of_date=origin,observation_end=origin,target_version='synthetic',config_version='test',assumption_version='test',
            code_revision='test',config_snapshot={})
        source=Run(kind='source_import',status='complete',request_key=str(uuid.uuid4()),**base)
        session.add(source); session.flush()
        forecast=Run(kind='forecast',status='complete',source_import_run_id=source.id,request_key=str(uuid.uuid4()),**base)
        session.add(forecast); session.flush()
        for h in range(1,15):
            session.add(ItemForecast(run_id=forecast.id,item_id=item,as_of_date=origin,target_date=origin+timedelta(days=h),
                horizon_day=h,forecast_qty=2,actual_available=False,item_share=1,weekday_weight=1/7,share_window_days=30,allocation_basis='synthetic'))
        session.add(Policy(item_id=item,supplier_id=supplier,version=1,effective_from=origin,
            configured_rop_floor=0,fixed_order_qty=15,safety_days=2,is_assumed=True,assumption_source='synthetic'))
        return forecast.id

def test_network_plan_reads_real_balance_pending_and_supplier_default_without_writes(auth_app):
    app,sessions=auth_app
    today=datetime.now(timezone.utc).date()
    with TestClient(app) as client:
        client.headers.update(login(client)); warehouse,item,supplier=setup_catalog(client)
        assert post(client,'/counts',movement(warehouse,item,3)).status_code==201
        second=post(client,'/warehouses',{'code':'SECOND','name':'Second location','country':'Vietnam'}).json()['id']
        assert post(client,'/counts',movement(second,item,6,reference='SECOND-COUNT')).status_code==201
        order=confirm(client,draft(client,warehouse,item,supplier))
        run=seed_forecast(sessions,item,supplier,today)
        response=client.get('/api/v1/operations/recommendations',params={'forecast_run_id':str(run)})
        assert response.status_code==200,response.text
        row=response.json()['items'][0]
        assert row['on_hand_qty']==9 and row['pending_qty']==10
        assert row['recommended_qty']==0 and row['rop']==18
        assert client.patch(f'/api/v1/operations/suppliers/{supplier}/settings',json={'lead_time_days':30,'expected_version':0,'reason':'New agreement'}).status_code==200
        row=client.get('/api/v1/operations/recommendations').json()['items'][0]
        assert row['reason']=='forecast_horizon_short' and row['recommended_qty'] is None
        assert client.get(f'/api/v1/operations/orders/{order["id"]}').json()['lead_time_days']==7
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(StockDocument))==2
        assert session.scalar(select(func.sum(StockBalance.on_hand_qty)))==9

def test_threshold_fallback_orders_one_lot_at_or_below_floor_and_counts_only_timely_receipts():
    origin = D
    assert calculate_threshold(5, {}, 7, 5, 20, origin)['recommended_qty'] == 20
    covered = calculate_threshold(6, {}, 7, 5, 20, origin)
    assert covered['decision'] == 'covered' and covered['recommended_qty'] == 0 and covered['reason'] == 'fixed_threshold_policy'
    timely = calculate_threshold(2, {origin + timedelta(days=3): 10, origin + timedelta(days=9): 50}, 7, 5, 20, origin)
    assert timely['inventory_position'] == 12 and timely['pending_qty'] == 60 and timely['recommended_qty'] == 0
    overdue = calculate_threshold(0, {origin: 4}, 7, 5, 20, origin)
    assert overdue['decision'] == 'review_overdue' and overdue['recommended_qty'] is None
    assert calculate_threshold(0, {}, 7, 5, None, origin)['reason'] == 'quantity_out_of_range'


def test_missing_forecast_falls_back_to_threshold_and_supplier_cannot_access_global_stock(auth_app):
    app,sessions=auth_app
    with TestClient(app) as client:
        assert client.get('/api/v1/operations/recommendations').status_code==401
        client.headers.update(login(client)); warehouse,item,supplier=setup_catalog(client)
        row=client.get('/api/v1/operations/recommendations').json()['items'][0]
        assert row['basis']=='threshold' and row['reason']=='fixed_policy_missing' and row['recommended_qty'] is None
        assert post(client,'/counts',movement(warehouse,item,3)).status_code==201
        with sessions.begin() as session:
            session.add(Policy(item_id=item,supplier_id=supplier,version=1,effective_from=datetime.now(timezone.utc).date()-timedelta(days=1),
                configured_rop_floor=4,fixed_order_qty=15,safety_days=2,is_assumed=True,assumption_source='synthetic'))
        row=client.get('/api/v1/operations/recommendations').json()['items'][0]
        assert (row['basis'],row['reason'],row['decision'],row['rop'],row['recommended_qty'])==('threshold','fixed_threshold_policy','order',4,15)
    with TestClient(app) as client:
        login(client,'partner-a')
        assert client.get('/api/v1/operations/recommendations').status_code==403
