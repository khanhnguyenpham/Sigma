"""Refactor guards captured before module extraction, not regenerated from new code."""
import json
import hashlib
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from sigma_m3.core.db import Base
from sigma_m3.core.settings import Settings
from sigma_m3.main import create_app
from sigma_m3 import models
from sigma_m3.modules.catalog.models import Item, Supplier, Warehouse
from sigma_m3.modules.configuration.models import Policy, Scenario


FIXTURES = Path(__file__).parent / "fixtures"


def settings(folder):
    return Settings(
        "postgresql+psycopg://synthetic:synthetic@127.0.0.1/sigma_m3_test",
        folder, folder,
    )


def test_full_openapi_matches_pre_refactor_contract(tmp_path):
    app = create_app(settings(tmp_path))
    try:
        expected = json.loads((FIXTURES / "openapi_baseline.json").read_text(encoding="utf-8"))
        canonical = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(canonical).hexdigest() == expected["canonical_sha256"]
    finally:
        app.state.engine.dispose()


def test_all_postgresql_tables_and_indexes_match_pre_refactor_ddl():
    statements = []
    for _, table in sorted(Base.metadata.tables.items()):
        statements.append(str(CreateTable(table).compile(dialect=dialect())).strip())
        for index in sorted(table.indexes, key=lambda index: index.name):
            statements.append(str(CreateIndex(index).compile(dialect=dialect())).strip())
    # SQLAlchemy emits spaces after commas; normalize only end-of-line whitespace.
    actual = "\n".join(line.rstrip() for line in (";\n\n".join(statements) + ";\n").splitlines()) + "\n"
    assert actual == (
        FIXTURES / "postgresql_schema_baseline.sql"
    ).read_text(encoding="utf-8")


def test_features_share_the_single_registered_metadata():
    assert models.Base is Base
    assert len(Base.metadata.tables) == 13
    for model in (Warehouse, Item, Supplier, Policy, Scenario, models.Run):
        assert model.__table__.metadata is Base.metadata


def test_settings_keep_checkout_defaults_and_explicit_paths(monkeypatch, tmp_path):
    project = next(p for p in Path(__file__).parents if (p / "M2/final_report.py").is_file())
    monkeypatch.setenv("M3_DATABASE_URL", settings(tmp_path).database_url)
    for name in ("M3_SOURCE_ROOT", "M3_OUTPUT_ROOT", "M3_FRONTEND_ORIGIN"):
        monkeypatch.delenv(name, raising=False)
    defaults = Settings.from_env()
    assert defaults.source_root == project
    assert defaults.output_root == project / "outputs/m3"
    assert defaults.order_source("orders_snapshot") == project / "data/sigma_sim_data_orders.csv"
    monkeypatch.setenv("M3_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("M3_OUTPUT_ROOT", str(tmp_path / "runs"))
    explicit = Settings.from_env()
    assert explicit.source_root == (tmp_path / "source").resolve()
    assert explicit.output_root == (tmp_path / "runs").resolve()


def test_relocated_backend_serves_the_existing_react_build(monkeypatch, tmp_path):
    from sigma_m3 import main

    frontend = tmp_path / "M3/frontend/dist"
    frontend.mkdir(parents=True)
    (frontend / "index.html").write_text("synthetic-react-build", encoding="utf-8")
    monkeypatch.setattr(main, "PROJECT_ROOT", tmp_path)
    with TestClient(main.create_app(settings(tmp_path))) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "synthetic-react-build"


def test_code_digest_detects_changes_in_the_relocated_backend(monkeypatch, tmp_path):
    from sigma_m3.core import hashes

    source = tmp_path / "web/backend/src/sigma_m3/main.py"
    source.parent.mkdir(parents=True)
    source.write_text("before", encoding="utf-8")
    final_report = tmp_path / "M2/final_report.py"
    final_report.parent.mkdir()
    final_report.write_text("unchanged", encoding="utf-8")
    monkeypatch.setattr(hashes, "PROJECT_ROOT", tmp_path)
    before = hashes.code_digest()
    source.write_text("after", encoding="utf-8")
    assert hashes.code_digest() != before


def test_shared_router_uses_each_application_session(tmp_path):
    def sessions(label):
        @contextmanager
        def scope():
            session = MagicMock()
            session.scalar.return_value = 1
            session.scalars.return_value.all.return_value = [
                Supplier(id=1, code=label, display_name=label,
                         assumption_source="synthetic", is_assumed=True)
            ]
            yield session
        return scope

    first, second = create_app(settings(tmp_path)), create_app(settings(tmp_path))
    first.state.sessions, second.state.sessions = sessions("SYN-A"), sessions("SYN-B")
    with TestClient(first) as a, TestClient(second) as b:
        for client, label in ((a, "SYN-A"), (b, "SYN-B"), (a, "SYN-A")):
            response = client.get("/api/v1/suppliers")
            assert response.status_code == 200
            assert response.json()["items"][0]["code"] == label
