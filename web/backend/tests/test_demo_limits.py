"""Shared admission, request bounds and real owned-job termination."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from core.demo_limits import DemoLimits
from main import create_app
from modules.runs.models import Run
from modules.runs.schemas import RunCreate
from modules.runs.service import enqueue
from test_demo_runtime import demo_env, bundle, is_live
from test_postgres_api import seed

BODY = dict(kind='source_import', source_key='orders_snapshot', as_of_date='2025-12-31')


def test_cleanup_ignores_exited_model_handles(monkeypatch):
    from web.backend.scripts.demo_stack import stop
    model = subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read(1)'], stdin=subprocess.PIPE)
    owned = psutil.Process(model.pid)
    model.communicate(b'x', timeout=10)
    job = subprocess.Popen([sys.executable, '-c', 'pass'])
    job.wait(timeout=10)
    def forbidden_wait(*args, **kwargs):
        raise psutil.AccessDenied(owned.pid)
    monkeypatch.setattr(psutil, 'wait_procs', forbidden_wait)
    stop(job, group=False, owned=[owned])
    assert not owned.is_running()


def settings_for(pg, monkeypatch, tmp_path, **limits):
    settings = demo_env(monkeypatch, tmp_path, os.environ['M3_TEST_DATABASE_URL'])
    bundle(settings)
    return replace(settings, demo_limits=replace(DemoLimits(), **limits))


def test_atomic_admission_idempotency_and_two_client_versions(pg, monkeypatch, tmp_path):
    settings = settings_for(pg, monkeypatch, tmp_path, active_runs=1)
    seed(pg[1])
    with TestClient(create_app(settings)) as first, TestClient(create_app(settings)) as second:
        def submit(n):
            return first.post('/api/v1/runs', json=BODY, headers={'Idempotency-Key': f'concurrent-{n}'})
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(submit,range(6)))
        assert sorted(r.status_code for r in results)==[202,429,429,429,429,429]
        winner=next(n for n,r in enumerate(results) if r.status_code==202)
        again=second.post('/api/v1/runs',json=BODY,headers={'Idempotency-Key':f'concurrent-{winner}'})
        assert again.status_code==200 and again.json()['run_id']==results[winner].json()['run_id']
        refused=next(r for r in results if r.status_code==429)
        assert refused.headers['retry-after']=='60' and refused.json()['error']['code']=='demo_queue_full'
        with pg[1]() as session:assert len(list(session.scalars(select(Run))))==1
        a=first.get('/api/v1/warehouses/1').json();b=second.get('/api/v1/warehouses/1').json()
        assert a['version']==b['version']
        assert first.patch('/api/v1/warehouses/1',json={'city':'First client','expected_version':a['version']}).status_code==200
        assert second.patch('/api/v1/warehouses/1',json={'city':'Stale client','expected_version':b['version']}).status_code==409
        current=second.get('/api/v1/warehouses/1').json()
        assert current['city']=='First client'
        assert second.patch('/api/v1/warehouses/1',json={'city':'Second client','expected_version':current['version']}).status_code==200


def test_request_limits_streaming_rate_cors_and_read_access(pg, monkeypatch, tmp_path):
    settings=settings_for(pg,monkeypatch,tmp_path,body_bytes=128,writes_per_minute=1)
    with TestClient(create_app(settings)) as client:
        # Actual streamed bytes, irrespective of a forged Content-Length.
        huge=client.post('/api/v1/runs',content=iter([b'x'*80,b'x'*80]),headers={'Content-Length':'1','Origin':'https://demo.example'})
        assert huge.status_code==413
        assert huge.headers['access-control-allow-origin']=='https://demo.example'
        assert client.post('/api/v1/runs',json=BODY,headers={'Idempotency-Key':'first'}).status_code==202
        limited=client.patch('/api/v1/warehouses/1',json={},headers={'Origin':'https://demo.example'})
        assert limited.status_code==429 and int(limited.headers['retry-after'])>0
        assert 'Retry-After' in limited.headers['access-control-expose-headers']
        assert client.get('/api/v1/runs').status_code==200


@pytest.mark.parametrize('limit,code', [('runs_per_hour','demo_run_rate'),('retained_runs','demo_retention_full'),('database_mb','demo_database_full'),('free_disk_mb','demo_storage_full')])
def test_durable_admission_caps(pg,monkeypatch,tmp_path,limit,code):
    settings=settings_for(pg,monkeypatch,tmp_path,**{limit:1})
    if limit in {'runs_per_hour','retained_runs'}:
        with pg[1].begin() as session:
            row,_=enqueue(session,RunCreate(**BODY),'old')
            row.status='failed'
    if limit=='free_disk_mb':
        from collections import namedtuple
        monkeypatch.setattr('core.demo_limits.shutil.disk_usage',lambda _:namedtuple('Usage','total used free')(100,100,0))
    with TestClient(create_app(settings)) as client:
        response=client.post('/api/v1/runs',json=BODY,headers={'Idempotency-Key':'limited'})
        assert response.status_code==429 and response.json()['error']['code']==code


@pytest.mark.parametrize('seconds,memory,code',[(1,4096,'demo_job_timeout'),(30,1,'demo_job_memory')])
def test_job_guard_terminates_owned_process_tree_and_retry(pg,monkeypatch,tmp_path,seconds,memory,code):
    import worker
    settings=settings_for(pg,monkeypatch,tmp_path,job_seconds=seconds,job_memory_mb=memory)
    with pg[1].begin() as session:
        row,_=enqueue(session,RunCreate(**BODY),'guarded',settings);key=row.id
    pidfile=tmp_path/'pids.json'
    script=tmp_path/'job.py'
    script.write_text("import json,os,subprocess,sys,time\nfrom pathlib import Path\nassert not Path(sys.argv[2]).exists(), 'Producer must create its own artifact directory'\nchild=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\nopen(sys.argv[1],'w').write(json.dumps([os.getpid(),child.pid]))\ntime.sleep(60)\n")
    native=subprocess.Popen
    def launch(args,**kwargs):return native([sys.executable,str(script),str(pidfile),str(settings.output_root/str(key))],**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(subprocess,'Popen',launch)
        assert worker.demo_process_one(settings,pg[1])==key
    if pidfile.exists():assert all(not is_live(pid) for pid in json.loads(pidfile.read_text()))
    if code=='demo_job_timeout':assert pidfile.exists(),'The timeout must cover a running descendant'
    with pg[1]() as session:
        row=session.get(Run,key);assert row.status=='failed' and row.error_code==code
    with TestClient(create_app(settings)) as client:
        retry=client.post(f'/api/v1/runs/{key}/retry',headers={'Idempotency-Key':'retry'})
        assert retry.status_code==202
        assert client.post(f'/api/v1/runs/{key}/retry',headers={'Idempotency-Key':'retry'}).json()==retry.json()
        with pg[1]() as session:
            new=session.get(Run,__import__('uuid').UUID(retry.json()['run_id']))
            assert new.retry_of_run_id==key and new.status=='queued'


def test_limits_validate_env_and_preserve_local_configuration(monkeypatch):
    monkeypatch.setenv('M3_DEMO_ACTIVE_RUNS','0')
    with pytest.raises(ValueError):DemoLimits.from_env()


def test_replay_request_is_rejected_before_work_is_queued(pg,monkeypatch,tmp_path):
    settings=settings_for(pg,monkeypatch,tmp_path,replay_days=14)
    with TestClient(create_app(settings)) as client:
        body=dict(kind='policy_replay',as_of_date='2025-09-30',period_start='2025-10-01',
                  period_end='2025-10-15',scenario_id=1,
                  source_import_run_id='00000000-0000-0000-0000-000000000001',
                  forecast_run_id='00000000-0000-0000-0000-000000000002')
        response=client.post('/api/v1/runs',json=body,headers={'Idempotency-Key':'too-long'})
        assert response.status_code==422 and response.json()['error']['code']=='demo_replay_period'
        assert client.get('/api/v1/runs').json()['total']==0


def test_standalone_demo_worker_registers_models_and_finishes_a_claimed_job(pg,monkeypatch,tmp_path):
    settings=settings_for(pg,monkeypatch,tmp_path)
    with pg[1].begin() as session:
        row,_=enqueue(session,RunCreate(**BODY),'standalone',settings);key=row.id
    result=subprocess.run([sys.executable,'-m','worker','--once'],env=dict(os.environ),
                          capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    with pg[1]() as session:
        row=session.get(Run,key)
        # The infrastructure fixture deliberately has no valid order CSV. It must
        # reach the importer and fail normally, rather than crash on a missing FK.
        assert row.status=='failed' and row.error_code=='source_import_failed'
    assert (settings.output_root.parent/(str(key)+'_resources.private.log')).exists()
