"""One local worker, protected by a PostgreSQL session advisory lock."""
import argparse
from datetime import datetime, timezone
import hashlib,json,os,time
from sqlalchemy import select,text,update
from sigma_m3.db import database
from sigma_m3.errors import DomainError
from sigma_m3.models import Run
from sigma_m3.services.ingestion import import_snapshot
from sigma_m3.services.runs import digest,code_digest
from sigma_m3.settings import Settings

LOCK_ID=734100719


def now(): return datetime.now(timezone.utc)


def process_one(settings,sessions):
    with sessions.begin() as session:
        row=session.scalar(select(Run).where(Run.status=='queued').order_by(Run.created_at,Run.id).with_for_update(skip_locked=True).limit(1))
        if row is None:return None
        row.status='running';row.started_at=now();row.heartbeat_at=now()
        key,kind,expected_code=row.id,row.kind,row.code_sha256
    try:
        if expected_code!=code_digest():raise DomainError('code_mismatch','Code changed after enqueue')
        if kind!='source_import':
            raise DomainError('stage_not_implemented','This run kind is not implemented in this foundation milestone')
        summary=import_snapshot(settings,sessions,key)
        with sessions.begin() as session:
            row=session.get(Run,key)
            row.config_sha256=digest(row.config_snapshot)
            manifest=dict(run_id=str(key),kind=kind,status='verified',source_sha256=row.source_sha256,
                code_sha256=row.code_sha256,config_sha256=row.config_sha256,target_version=row.target_version,
                config_version=row.config_version,assumption_version=row.assumption_version,summary=summary)
            folder=settings.output_root/str(key)
            folder.mkdir(parents=True,exist_ok=False)
            staging=folder/'manifest.staging.json'
            payload=json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False).encode()
            staging.write_bytes(payload)
            os.replace(staging,folder/'manifest.json')
            row.artifact_manifest={'manifest.json':hashlib.sha256(payload).hexdigest()}
            row.status='complete';row.finished_at=now();row.heartbeat_at=now()
    except Exception as exc:
        # Do not expose a raw source/path/driver traceback through run status.
        code=exc.code if isinstance(exc,DomainError) else 'source_import_failed' if kind=='source_import' else 'worker_failed'
        with sessions.begin() as session:
            row=session.get(Run,key);row.status='failed';row.error_code=code;row.finished_at=now();row.heartbeat_at=now()
    return key


def serve(settings,once=False):
    engine,sessions=database(settings.database_url)
    try:
        with engine.connect() as lock:
            if not lock.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':LOCK_ID}):
                raise DomainError('worker_already_running','A local M3 worker is already active',409)
            try:
                with sessions.begin() as session:
                    session.execute(update(Run).where(Run.status=='running').values(status='failed',error_code='interrupted',finished_at=now()))
                while True:
                    key=process_one(settings,sessions)
                    if once:return key
                    if key is None:time.sleep(1)
            finally:
                lock.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':LOCK_ID})
    finally:engine.dispose()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true')
    args=parser.parse_args();key=serve(Settings.from_env(),args.once)
    print('Processed one queued run' if key else 'No queued run')


if __name__=='__main__':main()
