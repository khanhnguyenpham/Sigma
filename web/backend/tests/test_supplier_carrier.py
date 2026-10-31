"""Carrier identity, database guards and non-destructive migration checks."""
from copy import deepcopy
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from core.errors import DomainError
from main import create_app
from models import Base
from modules.catalog.models import Supplier, Warehouse
from modules.configuration.models import Policy, Scenario
from modules.configuration.service import create_policy
from modules.runs.schemas import RunCreate
from modules.runs.service import enqueue
from test_postgres_api import D, request, seed, settings
from test_results_api import result_fixture


def test_import_and_seed_reuse_carrier_across_countries(pg, tmp_path, monkeypatch):
    import hashlib
    import pandas as pd
    from core.hashes import digest
    from modules.forecasting import ingestion
    from modules.inventory.seeding import seed_simulation
    _, sessions = pg
    cfg = settings(tmp_path)
    raw = tmp_path / 'data/sigma_sim_data_orders.csv'
    raw.parent.mkdir()
    raw.write_text('synthetic import fixture', encoding='utf-8')
    sales = pd.DataFrame([dict(destination_country=country, carrier='Vinaphone', sku='SYNTHETIC',
        product_type='eSIM', date=pd.Timestamp('2024-01-01'), quantity=1, order_id=f'synthetic-{n}')
        for n, country in enumerate(['Vietnam', 'Australia'])])
    audit = dict(source_sha256_before=hashlib.sha256(raw.read_bytes()).hexdigest(), sales_quantity=2, rows_raw=2)
    monkeypatch.setattr(ingestion, 'audit_orders', lambda *_: (sales, audit))
    monkeypatch.setattr(ingestion, 'daily_sales', lambda *_: sales)
    monkeypatch.setattr(ingestion, 'route_top', lambda *_: sales[['destination_country', 'carrier']])
    with sessions.begin() as session:
        source, _ = enqueue(session, RunCreate(kind='source_import', source_key='orders_snapshot', as_of_date='2025-12-31'), 'carrier-import')
        key = source.id
    summary = ingestion.import_snapshot(cfg, sessions, key)
    assert summary['routes'] == 2 and summary['items'] == 2
    with sessions.begin() as session:
        from modules.runs.models import Run
        source = session.get(Run, key)
        source.status = 'complete'
        source.config_sha256 = digest(source.config_snapshot)
    with sessions.begin() as session:
        assert len(session.scalars(select(Supplier)).all()) == 1
        assert session.scalar(select(Supplier.carrier)) == 'Vinaphone'
        result = seed_simulation(session, key, D)
        assert result['policies_created'] == 2
        assert len(set(session.scalars(select(Policy.supplier_id)))) == 1


def test_api_uses_carrier_and_rejects_wrong_supplier(pg, tmp_path):
    _, sessions = pg
    item, supplier, other = seed(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        rows = client.get('/api/v1/suppliers').json()['items']
        assert rows[0]['carrier'] == 'DemoCarrier'
        assert set(rows[0]) == {'id', 'carrier', 'created_at'}
        bad = client.post('/api/v1/supplier-item-policies', json=request(item, other).model_dump(mode='json'))
        assert bad.status_code == 422
        assert bad.json()['error']['code'] == 'supplier_carrier_mismatch'
        good = client.post('/api/v1/supplier-item-policies', json=request(item, supplier).model_dump(mode='json'))
        assert good.status_code == 201 and good.json()['version'] == 1
        assert client.get('/api/v1/supplier-item-policies').json()['items'][0]['carrier'] == 'DemoCarrier'
        scenario = dict(code='carrier', name='Carrier', settings=dict(cover_days=7, safety_multiplier=1,
            policy_overrides=[dict(item_id=item, supplier_id=other)], receipts_initial=[], receipts_declared=True))
        bad = client.post('/api/v1/scenarios', json=scenario)
        assert bad.status_code == 422 and bad.json()['error']['code'] == 'supplier_carrier_mismatch'


@pytest.mark.parametrize('change', ['policy_insert', 'policy_update', 'item_move', 'warehouse_change', 'supplier_rename'])
def test_database_blocks_cross_carrier_links(pg, change):
    engine, sessions = pg
    item, supplier, other = seed(sessions)
    with sessions.begin() as session:
        policy = create_policy(session, request(item, supplier))
        warehouse = Warehouse(code='DEMO-W2', destination_country='Elsewhere', carrier='OtherCarrier',
                              city='Synthetic', assumption_source='synthetic')
        session.add(warehouse)
        session.flush()
        ids = dict(item=item, supplier=other, policy=policy.id, warehouse=warehouse.id)
    sql = {
        'policy_insert': """INSERT INTO supplier_item_policies(item_id,supplier_id,version,effective_from,
            configured_rop_floor,fixed_order_qty,safety_days,is_assumed,assumption_source)
            VALUES (:item,:supplier,2,'2026-01-01',0,5,2,true,'synthetic')""",
        'policy_update': 'UPDATE supplier_item_policies SET supplier_id=:supplier WHERE id=:policy',
        'item_move': 'UPDATE items SET warehouse_id=:warehouse WHERE id=:item',
        'warehouse_change': "UPDATE warehouses SET carrier='OtherCarrier' WHERE code='DEMO-W1'",
        'supplier_rename': "UPDATE suppliers SET carrier='RenamedCarrier' WHERE carrier='DemoCarrier'",
    }[change]
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(sql), ids)


def test_one_carrier_supplies_multiple_routes_and_disallows_duplicates(pg):
    _, sessions = pg
    _, supplier, _ = seed(sessions)
    with sessions.begin() as session:
        session.add(Warehouse(code='DEMO-W2', destination_country='AnotherCountry', carrier='DemoCarrier',
                              city='Synthetic', assumption_source='synthetic'))
    with sessions() as session:
        assert session.scalar(select(Supplier.id).where(Supplier.carrier == 'DemoCarrier')) == supplier
        assert len(session.scalars(select(Warehouse).where(Warehouse.carrier == 'DemoCarrier')).all()) == 2
    for carrier in ('DemoCarrier', '', '   ', ' DemoCarrier'):
        with pytest.raises(IntegrityError), sessions.begin() as session:
            session.add(Supplier(carrier=carrier))


def test_legacy_scenario_cannot_bypass_carrier_at_freeze(pg):
    _, sessions = pg
    source, forecast, item = result_fixture(sessions)
    with sessions.begin() as session:
        create_policy(session, request(item, 1))
        scenario = Scenario(code='legacy', version=1, name='Legacy', assumption_version='synthetic',
            settings=dict(cover_days=7, safety_multiplier=1, policy_overrides=[dict(item_id=item, supplier_id=2)],
                          receipts_initial=[], receipts_declared=True))
        session.add(scenario)
        session.flush()
        scenario_id = scenario.id
    with pytest.raises(DomainError) as error, sessions.begin() as session:
        enqueue(session, RunCreate(kind='stock_projection', source_import_run_id=source,
            forecast_run_id=forecast, scenario_id=scenario_id, as_of_date=D), 'bad-carrier')
    assert error.value.code == 'supplier_carrier_mismatch'


def test_migration_preserves_all_other_tables_and_supplier_ids(pg):
    engine, sessions = pg
    source, _, item = result_fixture(sessions)
    with sessions.begin() as session:
        create_policy(session, request(item, 1))
    cfg = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    cfg.attributes['database_url'] = engine.url.render_as_string(hide_password=False)
    command.downgrade(cfg, '0004_fixed_qty')
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE suppliers SET code='SUP-001',display_name='Simulated supplier 001',assumption_source='route_supplier_seed_v1' WHERE id=1"))
            connection.execute(text("UPDATE warehouses SET code='WH-001' WHERE id=1"))
            before = {name: deepcopy(connection.execute(text(f'SELECT to_jsonb(t) FROM "{name}" t ORDER BY to_jsonb(t)::text')).scalars().all())
                      for name in Base.metadata.tables if name != 'suppliers'}
            identity = connection.execute(text('SELECT id,created_at FROM suppliers ORDER BY id')).all()
        command.upgrade(cfg, 'head')
        command.upgrade(cfg, 'head')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT id,created_at FROM suppliers ORDER BY id')).all() == identity
            assert connection.scalar(text('SELECT carrier FROM suppliers WHERE id=1')) == 'DemoCarrier'
            for name, rows in before.items():
                assert connection.execute(text(f'SELECT to_jsonb(t) FROM "{name}" t ORDER BY to_jsonb(t)::text')).scalars().all() == rows
            assert compare_metadata(MigrationContext.configure(connection, opts={'compare_type': True, 'compare_server_default': True}), Base.metadata) == []
    finally:
        command.upgrade(cfg, 'head')
