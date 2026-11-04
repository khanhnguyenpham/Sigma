"""Trade lifecycle domain and migration checks on synthetic sigma_m3_test only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import select, text, func
from sqlalchemy.exc import IntegrityError

from core.errors import DomainError
from main import create_app
from models import Base
from modules.catalog.models import (Item, Warehouse, ItemSupplyChange, ProviderProductNotice,
                                    ProviderProductNoticeItem, ProviderProductNoticeEvent)
from modules.catalog.provider import (provider_event_values, validate_provider_change,
                                      provider_notice_state, trade_state, resolve_provider_scope)
from modules.catalog.provider_service import create_provider_notice, append_provider_notice_event
from modules.catalog.supply import validate_supply_change
from modules.inventory.models import InventoryDaily, InventoryEvent
from test_postgres_api import seed, settings
from test_results_api import result_fixture
from test_workspace_api import workspace_fixture

D = date(2025, 10, 31)


def event(**changes):
    return {**dict(id=1, version=1, action="stop", known_on=D, effective_on=D,
                   target_event_id=None, reason="Synthetic provider stop",
                   source_description="Declared simulation, no external evidence", source_ref=None), **changes}


def payload(**changes):
    return {k: v for k, v in event(**changes).items() if k not in {"id", "version"}}


def follow(action="resume_supply", **changes):
    return event(**{**dict(id=2, version=2, action=action, known_on=D+timedelta(days=2),
                           effective_on=D+timedelta(days=4), target_event_id=1), **changes})


def notice(key=1, members=(1, 2), events=None):
    return dict(id=key, supplier_id=1, item_ids=list(members), events=events or [event()])


@pytest.mark.parametrize("offset,valid", [(-1, False), (0, True), (1, True), (6, True), (7, True)])
def test_internal_same_day_business_rule_without_changing_legacy_api(offset, valid):
    args = dict(item_id=1, action="stop", known_on=D, effective_on=D+timedelta(days=offset))
    if valid:
        validate_supply_change([], **args, minimum_notice_days=0)
    else:
        with pytest.raises(DomainError):
            validate_supply_change([], **args, minimum_notice_days=0)
    if offset < 7:
        with pytest.raises(DomainError):
            validate_supply_change([], **args)


def test_provider_late_knowledge_and_future_target_do_not_rewrite_origins():
    stop = event(known_on=D+timedelta(days=2), effective_on=D-timedelta(days=3))
    validate_provider_change([], **{k: stop[k] for k in ("action", "known_on", "effective_on", "target_event_id")})
    assert provider_notice_state([stop], D, D+timedelta(days=10))["sales_allowed"]
    assert not provider_notice_state([stop], D+timedelta(days=2))["sales_allowed"]


def test_future_resume_is_not_an_immediate_unblock_and_cancel_has_own_meaning():
    stopped = [event(), follow()]
    assert not provider_notice_state(stopped, D, D+timedelta(days=8))["sales_allowed"]
    at_resume_notice = provider_notice_state(stopped, D+timedelta(days=2))
    assert at_resume_notice["provider_status"] == "scheduled_resume"
    assert not at_resume_notice["sales_allowed"]
    assert provider_notice_state(stopped, D+timedelta(days=2), D+timedelta(days=4))["sales_allowed"]
    future_stop = event(effective_on=D+timedelta(days=7))
    cancel = follow("cancel_stop", effective_on=D+timedelta(days=2))
    assert provider_notice_state([future_stop, cancel], D, D+timedelta(days=9))["provider_status"] == "stopped"
    assert provider_notice_state([future_stop, cancel], D+timedelta(days=2), D+timedelta(days=9))["sales_allowed"]


@pytest.mark.parametrize("change", [
    dict(action="cancel_stop", known_on=D, effective_on=D),
    dict(action="resume_supply", known_on=D-timedelta(days=1), effective_on=D),
    dict(action="resume_supply", known_on=D+timedelta(days=1), effective_on=D),
    dict(action="resume_supply", target_event_id=999),
    dict(action="resume"), dict(action="stop", target_event_id=None),
])
def test_invalid_provider_followups_are_rejected(change):
    args = payload(action="resume_supply", known_on=D+timedelta(days=1), target_event_id=1, **{})
    args.update(change)
    with pytest.raises(DomainError):
        validate_provider_change([event()], **{k: args[k] for k in ("action", "known_on", "effective_on", "target_event_id")})


def test_cannot_resume_before_stop_effective_or_append_a_second_followup():
    with pytest.raises(DomainError):
        validate_provider_change([event(effective_on=D+timedelta(days=7))],
                                 action="resume_supply", known_on=D, effective_on=D+timedelta(days=8), target_event_id=1)
    with pytest.raises(DomainError):
        validate_provider_change([event(), follow()], action="resume_supply",
                                 known_on=D+timedelta(days=5), effective_on=D+timedelta(days=5), target_event_id=1)


@pytest.mark.parametrize("change", [
    dict(reason=" "), dict(source_description="\t"), dict(source_ref="file:///private"),
    dict(source_ref="javascript:alert(1)"), dict(source_ref="https://user:secret@example.test"),
    dict(target_event_id=True), dict(reason="x"*1001),
])
def test_declared_source_reason_and_reference_validation(change):
    with pytest.raises(DomainError):
        provider_event_values(**payload(**change))


def test_no_fake_source_url_required():
    assert provider_event_values(**payload(reason="  Simulation  "))["reason"] == "Simulation"
    assert provider_event_values(**payload())["source_ref"] is None


def test_independent_restrictions_and_overlapping_notices():
    internal = dict(id=10, item_id=1, version=1, action="stop", known_on=D, effective_on=D,
                    target_change_id=None, reason="Internal decision")
    alone = trade_state([internal], [], 1, D)
    assert not alone["replenishment_allowed"] and alone["sales_allowed"]
    provider_only = trade_state([], [notice()], 1, D)
    assert not provider_only["replenishment_allowed"] and not provider_only["sales_allowed"]
    resume_internal = dict(internal, id=11, version=2, action="resume", target_change_id=10)
    still_blocked = trade_state([internal, resume_internal], [notice()], 1, D)
    assert not still_blocked["sales_allowed"] and not still_blocked["replenishment_allowed"]
    restored_provider = notice(events=[event(), follow()])
    still_internal = trade_state([internal], [restored_provider], 1, D+timedelta(days=4))
    assert still_internal["sales_allowed"] and not still_internal["replenishment_allowed"]
    overlap = trade_state([], [restored_provider, notice(2)], 1, D+timedelta(days=4))
    assert [r["notice_id"] for r in overlap["provider_blockers"]] == [2]
    assert trade_state([], [notice()], 3, D)["replenishment_allowed"]
    assert not trade_state([], [notice()], 2, D)["sales_allowed"]


def scope(warehouses=(1, 2), countries=("A", "B")):
    return dict(products=[dict(sku="PLAN", product_type="eSIM",
                              destination_countries=list(countries), warehouse_ids=list(warehouses))])


def test_scope_is_explicit_complete_and_does_not_expand_to_carrier_or_type():
    catalog = [dict(id=i, warehouse_id=w, sku=sku, product_type=kind, destination_country=c, supplier_id=s)
               for i, w, sku, kind, c, s in [(1,1,"PLAN","eSIM","A",1), (2,2,"PLAN","eSIM","B",1),
                   (3,1,"OTHER","eSIM","A",1), (4,2,"PLAN","physical_SIM","B",1),
                   (5,3,"PLAN","eSIM","C",2)]]
    normalized, members = resolve_provider_scope(catalog, 1, scope())
    assert members == [1, 2] and normalized == scope()
    for invalid in [scope((1,3)), scope((1,), ("A","B")), scope((1,2), ("A",)), dict(products=[]),
                    {"products": [{"carrier": "all"}]}, scope((True,), ("A",))]:
        with pytest.raises(DomainError):
            resolve_provider_scope(catalog, 1, invalid)
    duplicate = dict(products=[*scope()["products"], *scope()["products"]])
    assert resolve_provider_scope(catalog, 1, duplicate) == (scope(), [1, 2])


def seeded_scope(sessions):
    first, supplier, other_supplier = seed(sessions)
    with sessions.begin() as s:
        w = Warehouse(code="DEMO-W2", destination_country="OtherMarket", carrier="DemoCarrier",
                      city="Other City", assumption_source="synthetic_fixture")
        s.add(w); s.flush()
        second = Item(warehouse_id=w.id, sku="DEMO-ESIM-01", product_type="eSIM", first_seen_date=D)
        outside = Item(warehouse_id=w.id, sku="DEMO-ESIM-01", product_type="physical_SIM", first_seen_date=D)
        s.add_all([second, outside]); s.flush()
        product_scope = dict(products=[dict(sku="DEMO-ESIM-01", product_type="eSIM",
            destination_countries=["DemoLand", "OtherMarket"], warehouse_ids=[1, w.id])])
        return supplier, other_supplier, [first, second.id], outside.id, product_scope


def create(sessions, supplier, product_scope, **changes):
    with sessions.begin() as s:
        return create_provider_notice(s, supplier_id=supplier, scope_definition=product_scope,
                                      expected_version=0, **payload(**changes))


def test_atomic_membership_target_fk_source_and_expected_version(pg):
    _, sessions = pg
    supplier, other, members, outside, product_scope = seeded_scope(sessions)
    first = create(sessions, supplier, product_scope)
    second = create(sessions, supplier, product_scope)
    assert first["item_ids"] == members and outside not in members
    with pytest.raises(DomainError, match="scope"), sessions.begin() as s:
        create_provider_notice(s, supplier_id=supplier, scope_definition=product_scope, expected_version=0,
                               expected_item_ids=[members[0]], **payload())
    with pytest.raises(DomainError), sessions.begin() as s:
        create_provider_notice(s, supplier_id=other, scope_definition=product_scope, expected_version=0, **payload())
    with pytest.raises(DomainError), sessions.begin() as s:
        create_provider_notice(s, supplier_id=supplier, scope_definition=product_scope, expected_version=0,
                               **payload(source_description=" "))
    with sessions() as s:
        assert s.scalar(select(func.count()).select_from(ProviderProductNotice)) == 2
        assert s.scalar(select(func.count()).select_from(ProviderProductNoticeItem)) == 4
        assert s.get(ProviderProductNoticeEvent, first["event"]["id"]).created_at.tzinfo is not None
    for changes in [dict(target_event_id=second["event"]["id"]), dict(expected_version=0)]:
        args = dict(expected_version=1, **payload(action="resume_supply",
                    target_event_id=first["event"]["id"]))
        args.update(changes)
        with pytest.raises(DomainError), sessions.begin() as s:
            append_provider_notice_event(s, first["notice_id"], **args)
    with pytest.raises(IntegrityError), sessions.begin() as s:
        s.add(ProviderProductNoticeEvent(notice_id=first["notice_id"], version=2,
            **payload(action="resume_supply", target_event_id=second["event"]["id"])))
    for changes in [dict(is_assumed=False), dict(source_description=" "), dict(reason="\t"),
                    dict(version=3), dict(source_ref="file:///x")]:
        values = dict(notice_id=first["notice_id"], version=2,
                      **payload(action="resume_supply", target_event_id=first["event"]["id"]))
        values.update(changes)
        with pytest.raises(IntegrityError), sessions.begin() as s:
            s.add(ProviderProductNoticeEvent(**values))


def test_concurrent_notice_followups_have_one_winner(pg):
    _, sessions = pg
    supplier, _, _, _, product_scope = seeded_scope(sessions)
    first = create(sessions, supplier, product_scope)
    def append(_):
        try:
            with sessions.begin() as s:
                append_provider_notice_event(s, first["notice_id"], expected_version=1,
                    **payload(action="resume_supply", target_event_id=first["event"]["id"]))
            return "created"
        except DomainError as ex:
            return ex.code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(append, range(2))) == ["created", "version_conflict"]
    with sessions() as s:
        assert s.scalar(select(func.count()).select_from(ProviderProductNoticeEvent)) == 2


def migration_config(engine):
    cfg = Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    cfg.attributes["database_url"] = engine.url.render_as_string(hide_password=False)
    return cfg


def test_upgrade_with_existing_history_preserves_columns_and_old_api_on_0007(pg, tmp_path):
    engine, sessions = pg
    key, _, item = workspace_fixture(sessions)
    cfg = migration_config(engine)
    command.downgrade(cfg, "0007_supply_lifecycle")
    try:
        with engine.begin() as c:
            c.execute(text("""INSERT INTO item_supply_changes(item_id,version,action,known_on,effective_on,reason)
                VALUES (:item,1,'stop',:known,:effective,'Existing internal simulation')"""),
                dict(item=item, known=D, effective=D+timedelta(days=7)))
            before = {name:c.execute(text(f'SELECT to_jsonb(t)::text FROM "{name}" t ORDER BY 1')).scalars().all()
                      for name in Base.metadata.tables if not name.startswith("provider_product_notice")}
        with TestClient(create_app(settings(tmp_path))) as client:
            response = client.get(f"/api/v1/runs/{key}/inventory")
            assert response.status_code == 200, response.text
            assert response.json()["items"][0]["closing_qty"] == 7
            assert "source_sales_qty" not in response.json()["items"][0]
            assert "actual_blocked_qty" not in response.json()["items"][0]
            exported = client.get(f"/api/v1/runs/{key}/exports/inventory_daily")
            assert exported.status_code == 200 and "source_sales_qty" not in exported.text
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")
        with engine.connect() as c:
            for name, rows in before.items():
                added = {"inventory_daily": ["source_sales_qty", "actual_blocked_qty"],
                         "items": ["receiving_warehouse_id", "receiving_version"],
                         "replenishment_orders": ["receiving_warehouse_id"]}.get(name, [])
                expr = "to_jsonb(t)" + ("-ARRAY[" + ",".join(repr(column) for column in added) + "]" if added else "")
                assert c.execute(text(f'SELECT ({expr})::text FROM "{name}" t ORDER BY 1')).scalars().all() == rows
            assert compare_metadata(MigrationContext.configure(c, opts={"compare_type": True, "compare_server_default": True}), Base.metadata) == []
            assert c.scalar(text("SELECT count(*) FROM inventory_daily WHERE source_sales_qty IS NOT NULL OR actual_blocked_qty IS NOT NULL")) == 0
        with sessions.begin() as s:
            s.add(ItemSupplyChange(item_id=item, version=2, action="resume", target_change_id=1,
                                  known_on=D+timedelta(days=7), effective_on=D+timedelta(days=7), reason="Internal resume"))
        command.downgrade(cfg, "0007_supply_lifecycle")
    finally:
        command.upgrade(cfg, "head")


@pytest.mark.parametrize("kind", ["same_day", "notice", "ledger", "event", "profile"])
def test_downgrade_refuses_every_new_data_shape(pg, kind):
    engine, sessions = pg
    source, _, item = result_fixture(sessions)
    with sessions.begin() as s:
        if kind == "same_day":
            s.add(ItemSupplyChange(item_id=item, version=1, action="stop", known_on=D, effective_on=D, reason="Internal"))
        elif kind == "notice":
            supplier = s.scalar(text("SELECT id FROM suppliers ORDER BY id LIMIT 1"))
            s.add(ProviderProductNotice(supplier_id=supplier, scope_definition=scope((1,), ("DemoLand",))))
        elif kind == "profile":
            s.execute(text("UPDATE runs SET config_snapshot=config_snapshot || :value WHERE id=:run"),
                      dict(value='{"trade_lifecycle_profile":"internal_provider_trade_v2"}', run=source))
        elif kind == "ledger":
            s.add(InventoryDaily(run_id=source, window_origin=D, item_id=item, date=D, forecast_as_of_date=D,
                opening_qty=10, receipts_qty=0, sales_qty=0, source_sales_qty=4, actual_blocked_qty=4,
                fulfilled_qty=0, shortage_qty=0, closing_qty=10, pending_qty=0, inventory_position=10,
                config_status="ok"))
        else:
            s.add(InventoryEvent(run_id=source, window_origin=D, item_id=item, event_at=D, event_sequence=1,
                event_kind="sale_blocked", source_sequence=123, quantity=4, fulfilled_qty=0, shortage_qty=0,
                balance_after=10))
    with pytest.raises(RuntimeError, match="lose data"):
        command.downgrade(migration_config(engine), "0007_supply_lifecycle")
    with sessions() as s:
        assert s.scalar(text("SELECT version_num FROM alembic_version")) == "0009_receiving_warehouse"


def test_daily_source_split_check_preserves_existing_balance_rule(pg):
    _, sessions = pg
    source, _, item = result_fixture(sessions)
    values = dict(run_id=source, window_origin=D, item_id=item, date=D, forecast_as_of_date=D,
        opening_qty=10, receipts_qty=0, sales_qty=2, source_sales_qty=6, actual_blocked_qty=4,
        fulfilled_qty=2, shortage_qty=0, closing_qty=8, pending_qty=0, inventory_position=8, config_status="ok")
    for changes in [dict(source_sales_qty=None), dict(actual_blocked_qty=None), dict(source_sales_qty=5),
                    dict(actual_blocked_qty=-1), dict(closing_qty=7), dict(shortage_qty=1)]:
        with pytest.raises(IntegrityError), sessions.begin() as s:
            s.add(InventoryDaily(**{**values, **changes}))
    with sessions.begin() as s:
        s.add(InventoryDaily(**values))
