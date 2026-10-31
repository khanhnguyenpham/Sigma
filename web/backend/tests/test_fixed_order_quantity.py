"""Fixed lot decisions and legacy protection; no company contract data."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError

from core.errors import DomainError
from models import Base
from main import create_app
from modules.configuration.models import Policy, Scenario
from modules.configuration.schemas import PolicyCreate, PolicyOverride
from modules.configuration.service import create_policy
from modules.inventory.service import PolicyValues, recommend
from modules.inventory.simulation import pure_window
from modules.runs.models import Run
from test_postgres_api import seed, request, settings, D
from test_results_api import result_fixture
from test_simulation import inputs, ORIGIN


@pytest.mark.parametrize('closing,pending,expected', [
    (80,0,25), (99,0,25), (0,0,25), (100,0,0), (101,0,0), (80,40,0), (80,29,25),
])
def test_fixed_quantity_does_not_scale_with_need_or_moq(closing,pending,expected):
    policy=PolicyValues(100,None,2,fixed_order_qty=25)
    result=recommend([10]*14,closing,pending,policy)
    assert result['recommended_qty']==expected
    assert result['needs_replenishment']==(closing<100)


@pytest.mark.parametrize('value',[0,-1,True,1.5,2**63])
def test_fixed_quantity_validates_native_integer_at_both_boundaries(value):
    with pytest.raises(DomainError):
        PolicyValues(100,None,2,fixed_order_qty=value)
    with pytest.raises(ValidationError):
        PolicyCreate.model_validate({**request(1,1).model_dump(),'fixed_order_qty':value})


def test_new_requests_require_quantity_and_scenarios_cannot_change_it():
    body=request(1,1).model_dump()
    assert 'moq' not in body
    body.pop('fixed_order_qty')
    for extra in [{},{'moq':100}]:
        with pytest.raises(ValidationError):PolicyCreate.model_validate({**body,**extra})
    for key in ['moq','fixed_order_qty']:
        with pytest.raises(ValidationError):PolicyOverride.model_validate({'item_id':1,key:100})
    with pytest.raises(DomainError):PolicyValues(100,10,2,fixed_order_qty=25)


def test_legacy_snapshot_keeps_variable_quantity_but_fixed_replay_uses_one_lot():
    args=list(inputs());legacy=deepcopy(args)
    old=pure_window(*legacy,'policy_replay',ORIGIN,ORIGIN+timedelta(days=14))
    args[4][0].update(moq=None,fixed_order_qty=7)
    fixed=pure_window(*args,'policy_replay',ORIGIN,ORIGIN+timedelta(days=14))
    assert fixed['orders'] and {r['ordered_qty'] for r in fixed['orders']}=={7}
    assert any(r['ordered_qty']!=7 for r in old['orders'])
    assert pure_window(*legacy,'policy_replay',ORIGIN,ORIGIN+timedelta(days=14))==old
    assert 'fixed_order_qty' not in legacy[4][0]


def test_new_run_rejects_legacy_quantity_and_stored_scenario_override(pg,tmp_path):
    _,sessions=pg
    source,forecast,item=result_fixture(sessions)
    with sessions.begin() as s:
        old=Policy(item_id=item,supplier_id=1,version=1,effective_from=D,
            configured_rop_floor=100,moq=50,safety_days=2,assumption_source='synthetic_legacy')
        scenario=Scenario(code='fixed',name='Synthetic',version=1,assumption_version='synthetic',settings=dict(
            cover_days=7,safety_multiplier=1,policy_overrides=[],receipts_initial=[],receipts_declared=True))
        s.add_all([old,scenario]);s.flush();scenario_id=scenario.id;policy_id=old.id
    with TestClient(create_app(settings(tmp_path))) as c:
        body=dict(kind='stock_projection',source_import_run_id=str(source),forecast_run_id=str(forecast),
            scenario_id=scenario_id,as_of_date=str(D))
        response=c.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'missing-fixed'})
        assert response.status_code>=400 and response.json()['error']['code']=='missing_contract_quantity'
        with sessions.begin() as s:
            p=s.get(Policy,policy_id);assert p.moq==50 and p.fixed_order_qty is None
            p.moq=None;p.fixed_order_qty=30
            scenario=s.get(Scenario,scenario_id)
            scenario.settings={**scenario.settings,'policy_overrides':[dict(item_id=item,moq=999)]}
        response=c.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'old-scenario'})
        assert response.status_code>=400 and response.json()['error']['code']=='missing_contract_quantity'
        with sessions.begin() as s:
            scenario=s.get(Scenario,scenario_id);scenario.settings={**scenario.settings,'policy_overrides':[]}
        response=c.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'configured-fixed'})
        assert response.status_code==202
        with sessions() as s:
            run=s.scalar(select(Run).where(Run.request_key=='configured-fixed'))
            assert run.config_snapshot['policies'][0]['fixed_order_qty']==30
            assert run.config_snapshot['policies'][0]['moq'] is None


def test_migration_preserves_legacy_rows_and_refuses_lossy_downgrade(pg):
    engine,sessions=pg
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    cfg.attributes['database_url']=engine.url.render_as_string(hide_password=False)
    command.downgrade(cfg,'0003_threshold')
    try:
        from test_postgres_api import seed_legacy
        item,supplier,_=seed_legacy(sessions)
        with engine.begin() as c:
            c.execute(text("INSERT INTO supplier_item_policies(item_id,supplier_id,version,effective_from,configured_rop_floor,moq,safety_days,is_assumed,assumption_source) VALUES (:item,:supplier,1,:day,100,50,2,true,'synthetic_legacy')"),dict(item=item,supplier=supplier,day=D))
            before=c.scalar(text('SELECT to_jsonb(t) FROM supplier_item_policies t'))
        command.upgrade(cfg,'head');command.upgrade(cfg,'head')
        with engine.connect() as c:
            assert c.scalar(text("SELECT to_jsonb(t)-'fixed_order_qty' FROM supplier_item_policies t"))==before
            assert c.scalar(text('SELECT fixed_order_qty FROM supplier_item_policies')) is None
            assert compare_metadata(MigrationContext.configure(c,opts={'compare_type':True,'compare_server_default':True}),Base.metadata)==[]
        with sessions.begin() as s:
            policy=create_policy(s,request(item,supplier,1,D+timedelta(days=1)));key=policy.id
        for values in [dict(fixed_order_qty=0),dict(fixed_order_qty=None),dict(moq=10)]:
            with pytest.raises(IntegrityError),sessions.begin() as s:
                s.execute(Policy.__table__.update().where(Policy.id==key).values(**values))
        with pytest.raises(IntegrityError):command.downgrade(cfg,'0003_threshold')
        with engine.connect() as c:
            assert c.scalar(text('SELECT version_num FROM alembic_version'))=='0005_carrier'
            assert c.scalar(text('SELECT fixed_order_qty FROM supplier_item_policies WHERE id=:key'),dict(key=key))==50
    finally:command.upgrade(cfg,'head')
