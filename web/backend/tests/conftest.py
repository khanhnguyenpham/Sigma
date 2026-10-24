from pathlib import Path
import os
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sigma_m3.core.db import database


@pytest.fixture(scope="session")
def pg_database():
    url = os.environ.get("M3_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Real PostgreSQL integration requires M3_TEST_DATABASE_URL")
    assert make_url(url).database == "sigma_m3_test", (
        "Refuse destructive fixture setup outside the named test database"
    )
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")
    engine, sessions = database(url)
    yield engine, sessions
    engine.dispose()


@pytest.fixture
def pg(pg_database):
    engine, sessions = pg_database
    from sigma_m3.models import Base

    tables = ",".join('"' + name + '"' for name in sorted(Base.metadata.tables))
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    return engine, sessions
