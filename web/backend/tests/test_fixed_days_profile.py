"""The current policy has no selectable modes; historical snapshots stay sealed."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from pydantic import ValidationError
from sqlalchemy import text

from core.hashes import digest
from core.run_context import snapshot_maps
from models import Base
from modules.configuration.models import Scenario
from modules.configuration.schemas import PolicyCreate, PolicyOverride
from modules.configuration.service import create_policy
from modules.inventory.service import PolicyValues, recommend
from modules.runs.models import Run
from modules.runs.schemas import RunCreate
from modules.runs.service import enqueue
from test_postgres_api import D, request, seed


@pytest.mark.parametrize('field,value', [('rop_mode','forecast'),('safety_mode','days'),
                                         ('safety_lookback_days',28),('safety_factor',1)])
def test_retired_fields_rejected_even_when_their_previous_values_were_valid(field,value):
    with pytest.raises(ValidationError):
        PolicyCreate.model_validate({**request(1,1).model_dump(),field:value})
    with pytest.raises(ValidationError):
        PolicyOverride.model_validate({'item_id':1,field:value})


def test_fixed_rop_is_independent_of_ss_and_forecast_and_remains_strict():
    policy=PolicyValues(20,None,2,rop_mode='fixed',safety_mode='days',fixed_order_qty=25)
    low=recommend([2]*14,19,0,policy)
    high=recommend([100]*14,19,0,policy)
    assert low['rop']==high['rop']==20
    assert (low['ss'],high['ss'])==(4,200)
    assert low['recommended_qty']==high['recommended_qty']==25
    assert recommend([100]*14,20,0,policy)['recommended_qty']==0


@pytest.mark.parametrize('floor,safety,forecast,ss,rop', [
    (10,2,2,4,18), (30,2,2,4,30), (18,2,2,4,18),
    (10,10,2,20,34), (10,0,0,0,10), (0,0,0,0,0),
    (0,1.5,0.5,1,5),
])
def test_forecast_floor_rop_uses_ss_and_respects_the_configured_minimum(floor,safety,forecast,ss,rop):
    policy=PolicyValues(floor,None,safety,rop_mode='forecast',fixed_order_qty=25)
    row=recommend([forecast]*14,0,0,policy)
    assert (row['ss'],row['rop'])==(ss,rop)
    assert recommend([forecast]*14,rop,0,policy)['recommended_qty']==0
    if rop:
        assert recommend([forecast]*14,rop-1,0,policy)['recommended_qty']==25
        assert recommend([forecast]*14,rop-1,row['target_stock'],policy)['recommended_qty']==0
        assert recommend([forecast]*14,rop-1,0,policy,replenishment_allowed=False)['recommended_qty']==0


def test_increasing_ss_changes_the_new_replenishment_decision():
    policy=PolicyValues(10,None,2,fixed_order_qty=25)
    assert recommend([2]*14,20,0,policy)['recommended_qty']==0  # ROP 18.
    row=recommend([2]*14,20,0,replace(policy,safety_days=4))
    assert (row['ss'],row['rop'],row['recommended_qty'])==(8,22,25)


def test_mode_migration_preserves_numeric_policy_and_sealed_runs_and_cleans_editable_overrides(pg):
    engine,sessions=pg
    item,supplier,_=seed(sessions)
    with sessions.begin() as session:
        policy=create_policy(session,request(item,supplier))
        policy_id=policy.id
        run,_=enqueue(session,RunCreate(kind='source_import',source_key='orders_snapshot',as_of_date=D),'legacy-migration')
        run.status='complete'
        run.config_snapshot={**run.config_snapshot,'policies':[dict(id=policy_id,item_id=item,safety_days=2,
            safety_mode='volatility',safety_factor=3,rop_mode='forecast')]}
        run.config_sha256=digest(run.config_snapshot)
        key=run.id
        session.add(Scenario(code='legacy-settings',version=1,name='Synthetic',assumption_version='synthetic',settings=dict(
            cover_days=7,safety_multiplier=1,receipts_initial=[],receipts_declared=True,
            policy_overrides=[dict(item_id=item,safety_days=0,configured_rop_floor=0,warning_horizon_days=14,
                                   safety_mode='volatility',safety_factor=3,rop_mode='forecast')]
        )))
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    cfg.attributes['database_url']=engine.url.render_as_string(hide_password=False)
    command.downgrade(cfg,'0005_carrier')
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE supplier_item_policies SET safety_mode='volatility',rop_mode='forecast',safety_factor=3"))
            frozen=connection.scalar(text('SELECT to_jsonb(r) FROM runs r'))
            numeric=connection.scalar(text("SELECT to_jsonb(p)-ARRAY['safety_mode','rop_mode','safety_lookback_days','safety_factor'] FROM supplier_item_policies p"))
        command.upgrade(cfg,'head'); command.upgrade(cfg,'head')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT to_jsonb(r) FROM runs r'))==frozen
            assert connection.scalar(text('SELECT to_jsonb(p) FROM supplier_item_policies p'))==numeric
            assert connection.scalar(text("SELECT settings->'policy_overrides' FROM scenarios"))==[
                dict(item_id=item,safety_days=0,configured_rop_floor=0,warning_horizon_days=14)]
            assert compare_metadata(MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True}),Base.metadata)==[]
        with sessions() as session:
            row=session.get(Run,key)
            original=deepcopy(row.config_snapshot)
            assert snapshot_maps(session,row)[2][policy_id]['safety_mode']=='volatility'
            assert row.config_snapshot==original and row.config_sha256==digest(original)
    finally:
        command.upgrade(cfg,'head')
