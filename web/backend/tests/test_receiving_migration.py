"""Rehearse receiving upgrade with nonempty legacy history on the named test DB."""
from copy import deepcopy
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

from main import create_app
from models import Base
from modules.catalog.receiving import update_receiving
from modules.catalog.schemas import ReceivingWarehouseUpdate
from modules.runs.models import Run
from test_postgres_api import settings
from test_receiving_warehouse import add_warehouse
from test_results_api import result_fixture
from run_split import LEGACY_ROW, NEW_TABLES, relation, without_dropped

# Tables renamed by 0015, read under their legacy names while the schema is older.
LEGACY = {'item_policies': 'supplier_item_policies'}


def test_legacy_upgrade_roundtrip_and_downgrade_guards(pg, tmp_path):
    engine, sessions = pg
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["database_url"] = engine.url.render_as_string(hide_password=False)
    source, forecast, item = result_fixture(sessions)
    target = add_warehouse(sessions)
    command.downgrade(cfg, "0008_trade_lifecycle")
    try:
        with engine.connect() as connection:
            before = {name: connection.execute(text(f"SELECT {LEGACY_ROW}::text FROM {relation(LEGACY.get(name, name), split=False)} t ORDER BY 1")).scalars().all()
                      for name in Base.metadata.tables if not name.startswith(('auth_', 'ops_', 'dealer')) and name != 'supplier_settings' and name not in NEW_TABLES}
        # Since 0015 renamed the policy table, current code needs the head schema; readiness keeps traffic away.
        with TestClient(create_app(settings(tmp_path))) as client:
            ready = client.get("/api/v1/ready")
            assert ready.status_code == 503 and ready.json()["checks"]["database"] is False
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")
        added = {"items": ["receiving_warehouse_id", "receiving_version"], "replenishment_orders": ["receiving_warehouse_id"], "item_forecasts": ["basis_as_of_date"]}
        with engine.connect() as connection:
            for name, rows in before.items():
                expr = "to_jsonb(t)" + ("-ARRAY[" + ",".join(repr(c) for c in added[name]) + "]" if name in added else "")
                assert connection.execute(text(f'SELECT {without_dropped(expr)}::text FROM {relation(name)} t ORDER BY 1')).scalars().all() == rows
            assert compare_metadata(MigrationContext.configure(connection, opts={
                "compare_type": True, "compare_server_default": True}), Base.metadata) == []
            assert connection.scalar(text("SELECT count(*) FROM items WHERE receiving_warehouse_id IS NOT NULL OR receiving_version<>0")) == 0
        command.downgrade(cfg, "0008_trade_lifecycle")
        command.upgrade(cfg, "head")
        with sessions.begin() as session:
            old = deepcopy(session.get(Run, source).config_snapshot)
            update_receiving(session, item, ReceivingWarehouseUpdate(receiving_warehouse_id=target, expected_version=0))
        with pytest.raises(RuntimeError, match="downgrade would lose data"):
            command.downgrade(cfg, "0008_trade_lifecycle")
        with engine.begin() as connection:
            connection.execute(text("UPDATE items SET receiving_warehouse_id=NULL,receiving_version=0"))
        with sessions.begin() as session:
            session.get(Run, source).config_snapshot = {**old, "receiving_warehouse_profile": "product_default_receiving_v1"}
        with pytest.raises(RuntimeError, match="downgrade would lose data"):
            command.downgrade(cfg, "0008_trade_lifecycle")
    finally:
        command.upgrade(cfg, "head")
