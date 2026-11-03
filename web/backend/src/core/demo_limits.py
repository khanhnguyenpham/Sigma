"""Limits for the single shared demo; local runs retain their existing behavior."""
from collections import deque
import asyncio
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
import os
import shutil
import time

from sqlalchemy import func, select, text
from starlette.responses import JSONResponse
from core.errors import DomainError

ADMISSION_LOCK = 734100720


@dataclass(frozen=True)
class DemoLimits:
    active_runs: int = 2
    runs_per_hour: int = 8
    retained_runs: int = 16
    writes_per_minute: int = 60
    body_bytes: int = 65536
    job_seconds: int = 7200
    job_memory_mb: int = 4096
    free_disk_mb: int = 512
    database_mb: int = 4096
    replay_days: int = 92

    @classmethod
    def from_env(cls):
        values = {}
        for field in fields(cls):
            try:
                value = int(os.environ.get('M3_DEMO_' + field.name.upper(), field.default))
                if not 1 <= value <= 10000000:
                    raise ValueError()
                values[field.name] = value
            except ValueError:
                raise ValueError('Invalid positive demo limit: ' + field.name) from None
        return cls(**values)


def reject(code, message, seconds=60):
    raise DomainError(code, message, 429, retry_after_seconds=seconds)


def admit(session, settings, request):
    from modules.runs.models import Run
    limits = settings.demo_limits
    if request.period_start and (request.period_end - request.period_start).days + 1 > limits.replay_days:
        raise DomainError('demo_replay_period', f'Khoảng chạy demo tối đa {limits.replay_days} ngày.', 422)
    if session.scalar(select(func.count()).select_from(Run).where(Run.status.in_(['queued', 'running']))) >= limits.active_runs:
        reject('demo_queue_full', 'Hàng đợi đang đầy. Vui lòng thử lại sau.')
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = session.scalars(select(Run.created_at).where(Run.created_at > since).order_by(Run.created_at)).all()
    if len(recent) >= limits.runs_per_hour:
        seconds = max(1, int((recent[-limits.runs_per_hour] + timedelta(hours=1) - datetime.now(timezone.utc)).total_seconds()) + 1)
        reject('demo_run_rate', 'Đã đạt giới hạn tạo kế hoạch. Vui lòng thử lại sau.', seconds)
    if session.scalar(select(func.count()).select_from(Run)) >= limits.retained_runs:
        reject('demo_retention_full', 'Demo đã đầy lịch sử. Người vận hành cần sao lưu và reset trước khi tạo thêm.')
    if shutil.disk_usage(settings.output_root).free < limits.free_disk_mb * 1024**2:
        reject('demo_storage_full', 'Demo không còn đủ dung lượng để nhận kế hoạch mới.')
    if session.scalar(text('SELECT pg_database_size(current_database())')) >= limits.database_mb * 1024**2:
        reject('demo_database_full', 'Demo đã đạt giới hạn dữ liệu. Người vận hành cần sao lưu và reset.')


class DemoRequestLimits:
    """One API process, one shared write budget; job admission persists in PostgreSQL."""
    def __init__(self, app, limits):
        self.app, self.limits, self.writes = app, limits, deque()

    async def __call__(self, scope, receive, send):
        if (scope['type'] != 'http' or not scope['path'].startswith('/api/v1/')
                or scope['method'] not in {'POST', 'PATCH', 'PUT', 'DELETE'}):
            return await self.app(scope, receive, send)
        body = bytearray()
        deadline = time.monotonic() + 10
        while True:
            try:
                event = await asyncio.wait_for(receive(), max(.001, deadline-time.monotonic()))
            except asyncio.TimeoutError:
                return await JSONResponse(status_code=408, content={'error': {
                    'code': 'demo_request_timeout', 'message': 'Yêu cầu gửi quá lâu. Vui lòng thử lại.'}})(scope, receive, send)
            if event['type'] == 'http.disconnect':
                return
            part = event.get('body', b'')
            if len(body) + len(part) > self.limits.body_bytes:
                response = JSONResponse(status_code=413, content={'error': {
                    'code': 'demo_request_too_large', 'message': 'Nội dung gửi vượt giới hạn demo.'}})
                return await response(scope, receive, send)
            body.extend(part)
            if not event.get('more_body'):
                break
        now = time.monotonic()
        while self.writes and self.writes[0] <= now - 60:
            self.writes.popleft()
        if len(self.writes) >= self.limits.writes_per_minute:
            seconds = max(1, int(60 - (now - self.writes[0])) + 1)
            response = JSONResponse(status_code=429, headers={'Retry-After': str(seconds)}, content={'error': {
                'code': 'demo_write_rate', 'message': 'Có quá nhiều thay đổi. Vui lòng thử lại sau.',
                'details': {'retry_after_seconds': seconds}}})
            return await response(scope, receive, send)
        self.writes.append(now)
        sent = False
        async def replay():
            nonlocal sent
            if sent:
                return await receive()
            sent = True
            return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
        return await self.app(scope, replay, send)
