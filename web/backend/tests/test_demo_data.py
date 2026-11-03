"""Redaction/conservation, registered-source binding and real offline PG restore."""
from dataclasses import replace
import csv
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from core.errors import DomainError
from core.settings import Settings
from core.demo import source_ready
from main import create_app
from modules.forecasting.demo_source import require_registered_source, signatures
from src.data import audit_orders, SOURCE_COLUMNS
from src.common import DataQualityError
from test_demo_runtime import demo_env, bundle
from test_postgres_api import seed as seed_rows
from web.backend.scripts.demo_source import export_source
from web.backend.scripts.demo_data import backup, restore, snapshot_state, operator_url, check, maintenance
from web.backend.scripts import demo_data
from worker import LOCK_ID


def original(path):
    rows = []
    for identifier, timestamp, quantity, status in [
        ("PRIVATE-2", "2025-10-01T08:00:00Z", 2, "success"),
        ("PRIVATE-1", "2025-10-01T08:00:00Z", 3, "success"),
        ("PRIVATE-3", "2025-10-02T12:00:00Z", 1, "success"),
    ]:
        row = dict.fromkeys(SOURCE_COLUMNS, "private-free-text")
        row.update(order_id=identifier, order_datetime=timestamp, activation_datetime="",
            product_type="eSIM", destination_country="Thailand", carrier="dtac", sku="TEST-SKU",
            quantity=str(quantity), unit_price_vnd="777777", unit_cost_vnd="555555",
            gross_revenue_vnd=str(quantity*777777), customer_id="PRIVATE-CUSTOMER", order_status=status)
        rows.append(row)
    rows.append(rows[0].copy())
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer=csv.DictWriter(stream, fieldnames=SOURCE_COLUMNS);writer.writeheader();writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_redaction_preserves_source_and_model_transactions(monkeypatch, tmp_path):
    settings = demo_env(monkeypatch, tmp_path)
    path=tmp_path/'original.csv';checksum=original(path)
    manifest=export_source(settings,path,checksum)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==checksum and source_ready(settings)
    cfg=json.loads((Path.cwd()/'data/configs/config.json').read_text())
    before,old_audit=audit_orders(path,cfg)
    after,new_audit=audit_orders(settings.order_source('orders_snapshot'),cfg)
    assert signatures(before)==signatures(after)
    assert old_audit['duplicate_rows_removed']==new_audit['duplicate_rows_removed']==1
    data=pd.read_csv(settings.order_source('orders_snapshot'),dtype=str,keep_default_na=False)
    assert data.columns.tolist()==SOURCE_COLUMNS
    assert all(data[c].eq('0').all() for c in ['unit_price_vnd','unit_cost_vnd','gross_revenue_vnd'])
    assert data.activation_datetime.eq('').all() and data.customer_id.eq('DEMO_CUSTOMER').all()
    content=settings.order_source('orders_snapshot').read_text()
    assert all(value not in content for value in ['PRIVATE-','777777','555555','private-free-text'])
    assert require_registered_source(settings,after,manifest['source_sha256'],checksum)['parent_source_sha256']==checksum
    with pytest.raises(DomainError):require_registered_source(replace(settings,mode='local'),after,manifest['source_sha256'],checksum)
    changed=after.copy();changed.iloc[0,changed.columns.get_loc('quantity')]+=1
    with pytest.raises(DomainError):require_registered_source(settings,changed,manifest['source_sha256'],checksum)
    with pytest.raises(ValueError):export_source(settings,path,checksum)


def test_conflicting_duplicate_is_not_hidden_by_redaction(monkeypatch,tmp_path):
    settings=demo_env(monkeypatch,tmp_path);path=tmp_path/'original.csv';original(path)
    rows=list(csv.DictReader(path.open()))
    rows[-1]['unit_price_vnd']='1';rows[-1]['gross_revenue_vnd']='2'
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=SOURCE_COLUMNS);writer.writeheader();writer.writerows(rows)
    checksum=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(DataQualityError):export_source(settings,path,checksum)
    assert not settings.source_root.exists()


def test_operator_guards_and_maintenance_blocks_all_business_requests(pg,monkeypatch,tmp_path):
    settings=demo_env(monkeypatch,tmp_path,os.environ['M3_TEST_DATABASE_URL']);bundle(settings)
    with pytest.raises(ValueError):check(replace(settings,database_url=settings.database_url.replace('sigma_m3_test','sigma_m3')))
    with pytest.raises(ValueError):operator_url(settings,settings.database_url.replace('sigma_m3_test','sigma_m3'))
    with pytest.raises(ValueError):restore(settings,settings.database_url,'baseline','sigma_m3')
    with pg[0].connect() as lock:
        lock.execute(text('SELECT pg_advisory_lock(:key)'),dict(key=LOCK_ID))
        try:
            with pytest.raises(ValueError,match='Stop the demo'):
                with maintenance(settings,settings.database_url):pass
            assert not (settings.demo_root/'.maintenance').exists()
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(:key)'),dict(key=LOCK_ID))
    with TestClient(create_app(settings)) as client:
        with maintenance(settings,settings.database_url):
            assert client.get('/api/v1/items').status_code==503
            assert client.post('/api/v1/runs',json={}).status_code==503
            assert client.get('/api/v1/live').status_code==200
            assert client.get('/api/v1/ready').status_code==503
        assert client.get('/api/v1/items').status_code==200


def test_real_snapshot_restores_db_artifacts_and_rejects_tampering(pg,monkeypatch,tmp_path):
    pg_bin=os.environ.get('M3_PG_BIN')
    if not pg_bin:pytest.skip('M3_PG_BIN points to matching native PostgreSQL tools')
    settings=demo_env(monkeypatch,tmp_path,os.environ['M3_TEST_DATABASE_URL']);bundle(settings)
    seed_rows(pg[1]);artifact=settings.output_root/'synthetic.json';artifact.write_text('{"value":1}')
    before=snapshot_state(pg[0])
    manifest=backup(settings,settings.database_url,'baseline',pg_bin)
    with pg[0].begin() as connection:connection.execute(text("UPDATE warehouses SET city='Changed demo'"))
    artifact.write_text('{"value":2}');(settings.output_root/'extra.json').write_text('extra')
    assert restore(settings,settings.database_url,'baseline','sigma_m3_test',pg_bin)['status']=='restored'
    assert snapshot_state(pg[0])==before and artifact.read_text()=='{"value":1}'
    assert not (settings.output_root/'extra.json').exists() and not (settings.demo_root/'.maintenance').exists()
    # A real reset frees the retained-run budget without deleting parent rows in place.
    limited = replace(settings, demo_limits=replace(settings.demo_limits, retained_runs=1))
    body = dict(kind='source_import', source_key='orders_snapshot', as_of_date='2025-12-31')
    with TestClient(create_app(limited)) as client:
        assert client.post('/api/v1/runs', json=body, headers={'Idempotency-Key':'before-reset'}).status_code == 202
        refused = client.post('/api/v1/runs', json=body, headers={'Idempotency-Key':'full'})
        assert refused.status_code == 429 and refused.json()['error']['code'] == 'demo_retention_full'
    # Synthetic fixture has no worker; make it idle before the operator reset.
    with pg[0].begin() as connection:connection.execute(text("UPDATE runs SET status='failed',error_code='interrupted'"))
    restore(settings,settings.database_url,'baseline','sigma_m3_test',pg_bin)
    with TestClient(create_app(limited)) as client:
        assert client.post('/api/v1/runs', json=body, headers={'Idempotency-Key':'after-reset'}).status_code == 202
    with pg[0].begin() as connection:connection.execute(text("UPDATE runs SET status='failed',error_code='interrupted'"))
    restore(settings,settings.database_url,'baseline','sigma_m3_test',pg_bin)
    assert snapshot_state(pg[0]) == before
    native=demo_data.pg_tool
    def interrupted(*args,**kwargs):
        raise RuntimeError('Simulated operator interruption')
    monkeypatch.setattr(demo_data,'pg_tool',interrupted)
    with pytest.raises(RuntimeError,match='interruption'):
        restore(settings,settings.database_url,'baseline','sigma_m3_test',pg_bin)
    assert (settings.demo_root/'.maintenance').exists()
    with pytest.raises(ValueError,match='Maintenance marker'):
        restore(settings,settings.database_url,'baseline','sigma_m3_test',pg_bin)
    monkeypatch.setattr(demo_data,'pg_tool',native)
    assert restore(settings,settings.database_url,'baseline','sigma_m3_test',pg_bin,recover=True)['status']=='restored'
    assert snapshot_state(pg[0])==before and not (settings.demo_root/'.maintenance').exists()
    assert not list(settings.demo_root.glob('.restore-*')) and not list(settings.demo_root.glob('.previous-*'))
    dump=settings.demo_root/'backups/baseline/database.dump';dump.write_bytes(dump.read_bytes()+b'changed')
    with pytest.raises(ValueError):restore(settings,settings.database_url,'baseline','sigma_m3_test',pg_bin)
    assert snapshot_state(pg[0])==before
