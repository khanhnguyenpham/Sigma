from dataclasses import replace
import os,uuid
from datetime import date
import pytest
from sqlalchemy import select,update
from redis.exceptions import ConnectionError as RedisConnectionError
from modules.runs.models import Run
from modules.runs.redis_queue import RedisTransport,queue_status
from test_postgres_api import settings


def queued(sessions):
    with sessions.begin() as session:
        row=Run(kind='source_import',status='queued',as_of_date=date(2025,10,31),observation_end=date(2025,10,31),
            target_version='synthetic',config_version='test',assumption_version='test',code_revision='test',code_sha256='0'*64,
            config_snapshot={},config_sha256='0'*64,request_key=str(uuid.uuid4()),request_sha256='0'*64)
        session.add(row);session.flush();return row.id


class FakeRedis:
    def __init__(self):self.messages=[];self.acks=[];self.down=False
    def xadd(self,stream,fields):
        if self.down:raise RedisConnectionError('offline')
        self.messages.append(fields);return str(len(self.messages))+'-0'
    def xack(self,stream,group,key):self.acks.append(key)
    def xdel(self,*args):return 1


def test_outage_rolls_back_publish_mark_and_duplicate_delivery_has_one_effect(pg,tmp_path):
    _,sessions=pg;key=queued(sessions);client=FakeRedis();transport=RedisTransport(settings(tmp_path),client)
    client.down=True
    with pytest.raises(RedisConnectionError):transport.dispatch(sessions)
    with sessions() as session:
        assert session.get(Run,key).status=='queued' and not session.get(Run,key).result_summary
    client.down=False;assert transport.dispatch(sessions)==1
    effects=[]
    def process(claimed):
        effects.append(claimed[0])
        with sessions.begin() as session:session.get(Run,claimed[0]).status='complete'
    fields={'version':'1','run_id':str(key)}
    transport.deliver(sessions,'1-0',fields,process);transport.deliver(sessions,'2-0',fields,process)
    assert effects==[key] and len(client.acks)==2


def test_unfinished_message_not_acknowledged_and_terminal_retry_does_not_compute(pg,tmp_path):
    _,sessions=pg;key=queued(sessions);client=FakeRedis();transport=RedisTransport(settings(tmp_path),client)
    def crash(claimed):raise RuntimeError('Synthetic worker failure')
    with pytest.raises(RuntimeError):transport.deliver(sessions,'1-0',{'version':'1','run_id':str(key)},crash)
    assert not client.acks
    with sessions.begin() as session:
        session.execute(update(Run).where(Run.id==key).values(status='failed',error_code='interrupted'))
    transport.deliver(sessions,'1-0',{'version':'1','run_id':str(key)},lambda _:pytest.fail('Do not refit an interrupted run'))
    assert client.acks==['1-0']


def test_interrupted_worker_cannot_resurrect_a_run(pg,tmp_path,monkeypatch):
    import worker
    _,sessions=pg;key=queued(sessions)
    with sessions.begin() as session:
        row=session.get(Run,key);row.status='running';row.code_sha256=worker.LOADED_CODE
    monkeypatch.setattr(worker,'code_digest',lambda:worker.LOADED_CODE)
    def interrupted(*args):
        with sessions.begin() as session:
            row=session.get(Run,key);row.status='failed';row.error_code='interrupted'
        return {'should_not_complete':True}
    monkeypatch.setattr(worker,'import_snapshot',interrupted)
    worker.process_one(settings(tmp_path),sessions,(key,'source_import',worker.LOADED_CODE))
    with sessions() as session:
        row=session.get(Run,key)
        assert row.status=='failed' and row.error_code=='interrupted'


@pytest.fixture
def real_transport(pg,tmp_path):
    url=os.environ.get('M3_TEST_REDIS_URL')
    if not url:
        if os.environ.get('CI')=='true':pytest.fail('CI must exercise a real Redis service')
        pytest.skip('Local Redis unavailable; mandatory service runs in CI')
    transport=RedisTransport(replace(settings(tmp_path),queue_driver='redis',redis_url=url,queue_namespace='sigma:test:'+uuid.uuid4().hex))
    transport.ensure_group()
    yield transport,pg[1]
    transport.redis.delete(transport.stream);transport.redis.close()


def test_real_stream_publish_consume_and_duplicate_no_double_compute(real_transport):
    transport,sessions=real_transport;key=queued(sessions)
    assert transport.dispatch(sessions)==1
    transport.redis.xadd(transport.stream,{'version':'1','run_id':str(key)})
    effects=[]
    def process(claimed):
        effects.append(claimed[0])
        with sessions.begin() as session:session.get(Run,claimed[0]).status='complete'
    transport.step(sessions,process);transport.step(sessions,process)
    assert effects==[key]
    assert transport.redis.xpending(transport.stream,transport.group)['pending']==0


def test_real_pending_reclaim_after_commit_ack_loss(real_transport):
    transport,sessions=real_transport;key=queued(sessions);transport.dispatch(sessions)
    messages=transport.redis.xreadgroup(transport.group,'dead-worker',{transport.stream:'>'},count=1)
    message_id=messages[0][1][0][0]
    with sessions.begin() as session:session.get(Run,key).status='complete'
    transport.redis.xclaim(transport.stream,transport.group,'dead-worker',0,[message_id],idle=61000)
    transport.step(sessions,lambda _:pytest.fail('Commit before ack must not run again'))
    assert transport.redis.xpending(transport.stream,transport.group)['pending']==0
