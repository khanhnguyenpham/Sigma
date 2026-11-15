from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from modules.auth.models import User
from modules.auth.service import now, operator_reset_password
from test_auth import auth_app, login, PASSWORD

NEW='Synthetic-Changed-Password-2026'

@pytest.mark.parametrize('username',['admin','partner-a'])
def test_password_change_revokes_all_sessions_and_requires_current_password(auth_app,username):
    app,_=auth_app
    with TestClient(app) as first, TestClient(app) as second:
        headers=login(first,username); login(second,username)
        assert first.post('/api/v1/auth/password',json={'current_password':PASSWORD,'new_password':NEW}).status_code==403
        assert first.post('/api/v1/auth/password',headers=headers,json={'current_password':'wrong','new_password':NEW}).status_code==403
        assert first.post('/api/v1/auth/password',headers=headers,json={'current_password':PASSWORD,'new_password':NEW}).status_code==200
        assert second.get('/api/v1/auth/session').status_code==401
        assert first.post('/api/v1/auth/login',json={'username':username,'password':PASSWORD}).status_code==401
        assert first.post('/api/v1/auth/login',json={'username':username,'password':NEW}).status_code==200

def test_password_guess_lock_cannot_be_bypassed_by_existing_session(auth_app):
    app,sessions=auth_app
    with TestClient(app) as client:
        headers=login(client)
        for _ in range(5):
            assert client.post('/api/v1/auth/password',headers=headers,json={'current_password':'wrong','new_password':NEW}).status_code==403
        assert client.post('/api/v1/auth/password',headers=headers,json={'current_password':PASSWORD,'new_password':NEW}).status_code==403
    with sessions() as session:
        assert session.scalar(select(User).where(User.username=='admin')).locked_until > now()

def test_operator_recovery_revokes_sessions_without_reactivating_disabled_account(auth_app):
    app,sessions=auth_app
    with TestClient(app) as client:
        login(client,'partner-a')
        with sessions.begin() as session:
            session.execute(update(User).where(User.username=='partner-a').values(active=False,locked_until=now()+timedelta(minutes=15)))
            operator_reset_password(session,'partner-a',NEW)
        assert client.get('/api/v1/auth/session').status_code==401
        assert client.post('/api/v1/auth/login',json={'username':'partner-a','password':NEW}).status_code==401
