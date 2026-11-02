"""Supply step 2: pure timeline and real test-database migration, no HTTP writes."""
from datetime import date, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from models import Base
from modules.catalog.models import Item, ItemSupplyChange
from modules.catalog.supply import supply_state, validate_supply_change
from core.errors import DomainError
from test_postgres_api import seed
from test_results_api import result_fixture

D = date(2025, 10, 1)


def stop(**changes):
    return dict(dict(id=1, item_id=1, version=1, action="stop", known_on=D,
                     effective_on=D+timedelta(days=7), target_change_id=None), **changes)


def event(action, known, **changes):
    return dict(dict(id=2, item_id=1, version=2, action=action, known_on=known,
                     effective_on=known, target_change_id=1), **changes)


@pytest.mark.parametrize("offset,status", [(-1,"active"),(0,"scheduled_stop"),(6,"scheduled_stop"),(7,"stopped"),(8,"stopped")])
def test_stop_boundary_and_other_item(offset, status):
    origin=D+timedelta(days=offset)
    state=supply_state([stop()],1,origin)
    assert state["supply_status"]==status
    assert state["replenishment_allowed"]==(status!="stopped")
    assert supply_state([stop()],2,origin)["supply_status"]=="active"


@pytest.mark.parametrize("offset,valid", [(0,False),(6,False),(7,True),(8,True)])
def test_notice_validation(offset, valid):
    args=dict(item_id=1,action="stop",known_on=D,effective_on=D+timedelta(days=offset))
    if valid:validate_supply_change([],**args)
    else:
        with pytest.raises(DomainError) as exc:validate_supply_change([],**args)
        assert exc.value.status==422


def test_frozen_cutoff_ignores_later_cancel_and_resume():
    cancel=event("cancel_stop",D+timedelta(days=3))
    assert supply_state([stop(),cancel],1,D,D+timedelta(days=8))["supply_status"]=="stopped"
    assert supply_state([stop(),cancel],1,D+timedelta(days=3))["supply_status"]=="active"
    resume=event("resume",D+timedelta(days=9))
    assert supply_state([resume,stop()],1,D+timedelta(days=8))["supply_status"]=="stopped"
    assert supply_state([resume,stop()],1,D+timedelta(days=9))["supply_status"]=="active"
    assert supply_state([stop()],1,D.isoformat(),(D+timedelta(days=7)).isoformat())["supply_status"]=="stopped"


@pytest.mark.parametrize("action,offset,target,valid", [
    ("cancel_stop",6,1,True),("cancel_stop",7,1,False),
    ("resume",6,1,False),("resume",7,1,True),
    ("resume",8,999,False),("stop",8,None,False),
])
def test_transition_boundaries(action,offset,target,valid):
    known=D+timedelta(days=offset)
    args=dict(item_id=1,action=action,known_on=known,
              effective_on=known+timedelta(days=7) if action=="stop" else known,target_change_id=target)
    if valid:validate_supply_change([stop()],**args)
    else:
        with pytest.raises(DomainError):validate_supply_change([stop()],**args)


def test_repeated_cycles_same_day_and_no_backdated_append():
    history=[stop(),event("cancel_stop",D+timedelta(days=2))]
    known=D+timedelta(days=2)
    validate_supply_change(history,item_id=1,action="stop",known_on=known,effective_on=known+timedelta(days=7))
    with pytest.raises(DomainError):
        validate_supply_change(history,item_id=1,action="stop",known_on=D,effective_on=D+timedelta(days=7))
    history.append(stop(id=3,version=3,known_on=known,effective_on=known+timedelta(days=7)))
    assert supply_state(history,1,known)["stop_change_id"]==3
    with pytest.raises(DomainError):supply_state(history,1,known,D)
    with pytest.raises(DomainError):supply_state(history,1,"invalid")


def test_database_constraints_and_item_target(pg):
    _,sessions=pg
    item,_,_=seed(sessions)
    with sessions.begin() as s:
        other=Item(warehouse_id=1,sku="OTHER",product_type="eSIM",first_seen_date=D)
        s.add(other);s.flush();other_id=other.id
        row=ItemSupplyChange(item_id=item,version=1,action="stop",known_on=D,
                             effective_on=D+timedelta(days=7),reason="Synthetic notice")
        s.add(row);s.flush();key=row.id
    base=dict(item_id=item,version=2,action="stop",known_on=D,effective_on=D+timedelta(days=7),reason="Synthetic")
    for change in [dict(version=0),dict(version=1),dict(action="invalid"),dict(reason=" "),dict(reason="\t\n"),dict(reason="x"*1001),
                   dict(effective_on=D-timedelta(days=1)),dict(target_change_id=key),
                   dict(is_assumed=False),dict(assumption_source="real"),
                   dict(item_id=other_id,action="resume",target_change_id=key,effective_on=D)]:
        with pytest.raises(IntegrityError),sessions.begin() as s:
            s.add(ItemSupplyChange(**{**base,**change}))
    with sessions() as s:
        row=s.get(ItemSupplyChange,key)
        assert row.is_assumed and row.assumption_source=="user_declared_supply_simulation_v1"
        assert row.created_at.tzinfo is not None


def test_migration_preserves_all_old_tables_and_blocks_loss(pg):
    engine,sessions=pg
    cfg=Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    cfg.attributes["database_url"]=engine.url.render_as_string(hide_password=False)
    result_fixture(sessions)
    old=sorted(name for name in Base.metadata.tables
               if name!="item_supply_changes" and not name.startswith("provider_product_notice"))
    def snapshot():
        with engine.connect() as c:
            return {name:c.execute(text(f'SELECT (to_jsonb(t)-ARRAY[\'source_sales_qty\',\'actual_blocked_qty\'])::text FROM "{name}" t ORDER BY 1')).scalars().all() for name in old}
    before=snapshot()
    command.downgrade(cfg,"0006_fixed_days")
    command.upgrade(cfg,"head");command.upgrade(cfg,"head")
    assert snapshot()==before
    with engine.connect() as c:
        assert compare_metadata(MigrationContext.configure(c,opts={"compare_type":True,"compare_server_default":True}),Base.metadata)==[]
    with sessions.begin() as s:
        item=s.scalar(select(Item.id))
        s.add(ItemSupplyChange(item_id=item,version=1,action="stop",known_on=D,effective_on=D+timedelta(days=7),reason="Synthetic"))
    with pytest.raises(RuntimeError,match="lose data"):command.downgrade(cfg,"0006_fixed_days")
    with sessions() as s:
        assert s.scalar(text("SELECT version_num FROM alembic_version"))=="0008_trade_lifecycle"
        assert s.scalar(select(ItemSupplyChange.id)) is not None
    assert snapshot()==before
