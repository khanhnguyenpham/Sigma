"""Redis at-least-once transport; committed queued runs are the durable outbox."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from modules.runs.models import Run


def now():
    return datetime.now(timezone.utc)


class RedisTransport:
    def __init__(self, settings, client=None):
        import redis
        self.redis = client if client is not None else redis.Redis.from_url(settings.redis_url,
            decode_responses=True, protocol=2, socket_connect_timeout=2, socket_timeout=3, health_check_interval=30)
        self.stream = settings.queue_namespace + ':jobs'
        self.group = settings.queue_namespace + ':workers'
        self.consumer = str(uuid.uuid4())
        self.reclaim_cursor = '0-0'

    def ensure_group(self):
        from redis.exceptions import ResponseError
        try:
            self.redis.xgroup_create(self.stream,self.group,id='0-0',mkstream=True)
        except ResponseError as failure:
            if 'BUSYGROUP' not in str(failure):
                raise

    def dispatch(self,sessions,limit=20):
        """Publish then mark in PG; crash between them may duplicate, never lose intent."""
        timestamp=now().timestamp();count=0
        with sessions.begin() as session:
            rows=session.scalars(select(Run).where(Run.status=='queued').order_by(
                Run.result_summary['_transport']['published_at'].as_float().asc().nullsfirst(),Run.created_at,Run.id)
                .with_for_update(skip_locked=True).limit(limit)).all()
            for row in rows:
                summary=dict(row.result_summary or {})
                info=summary.get('_transport',{})
                if timestamp-float(info.get('published_at',0)) < 60:
                    continue
                self.redis.xadd(self.stream,{'version':'1','run_id':str(row.id)})
                summary['_transport']={'published_at':timestamp,'deliveries':int(info.get('deliveries',0))+1}
                row.result_summary=summary;count+=1
        return count

    def claim(self,sessions,key):
        with sessions.begin() as session:
            row=session.scalar(select(Run).where(Run.id==key,Run.status=='queued').with_for_update(skip_locked=True))
            if row is None:
                return None
            row.status='running';row.started_at=now();row.heartbeat_at=now()
            return row.id,row.kind,row.code_sha256

    def deliver(self,sessions,message_id,fields,process):
        try:
            if set(fields)!={'version','run_id'} or fields['version']!='1':
                raise ValueError()
            key=uuid.UUID(fields['run_id'])
        except (ValueError,TypeError,KeyError):
            self.redis.xack(self.stream,self.group,message_id)
            self.redis.xdel(self.stream,message_id)
            return None
        claimed=self.claim(sessions,key)
        if claimed:
            process(claimed)
        with sessions() as session:
            status=session.scalar(select(Run.status).where(Run.id==key))
        # Running jobs stay pending. Worker restart marks interruptions failed before consuming.
        if status is None or status in {'complete','failed','invalidated'}:
            self.redis.xack(self.stream,self.group,message_id)
            self.redis.xdel(self.stream,message_id)
        return key if claimed else None

    def step(self,sessions,process):
        self.ensure_group();self.dispatch(sessions)
        claimed=self.redis.xautoclaim(self.stream,self.group,self.consumer,min_idle_time=60000,start_id=self.reclaim_cursor,count=1)
        self.reclaim_cursor=claimed[0]
        messages=claimed[1]
        if not messages:
            fresh=self.redis.xreadgroup(self.group,self.consumer,{self.stream:'>'},count=1,block=1000)
            messages=fresh[0][1] if fresh else []
        if not messages:
            return None
        message_id,fields=messages[0]
        return self.deliver(sessions,message_id,fields,process)


def queue_status(settings):
    if settings.queue_driver!='redis':
        return {'driver':'postgres','available':True,'message':'Hàng đợi PostgreSQL'}
    from redis.exceptions import RedisError
    try:
        transport=RedisTransport(settings)
        try:
            transport.redis.ping()
            return {'driver':'redis','available':True,'message':'Hàng đợi Redis sẵn sàng'}
        finally:
            transport.redis.close()
    except RedisError:
        return {'driver':'redis','available':False,'message':'Redis chưa sẵn sàng. Công việc vẫn được giữ trong PostgreSQL.'}
