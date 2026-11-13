"""Demo configuration, private probes and owned process cleanup on synthetic data."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

import psutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from core.settings import Settings, PROJECT_ROOT
from core.demo import source_ready, worker_heartbeat, worker_ready
from main import create_app
from web.backend.scripts.demo_stack import supervise, stop


def demo_env(monkeypatch, tmp_path, url="postgresql://demo:fake@localhost/sigma_m3_test"):
    base = tmp_path / "sigma-demo"
    for key, value in dict(M3_MODE="demo", M3_DATABASE_URL=url,
        M3_DEMO_ROOT=str(base), M3_SOURCE_ROOT=str(base / "source"),
        M3_OUTPUT_ROOT=str(base / "outputs/m3"), M3_FRONTEND_ORIGIN="https://demo.example",
        M3_WORKER_INSTANCE="test-instance").items():
        monkeypatch.setenv(key, value)
    return Settings.from_env()


def bundle(settings):
    settings.output_root.mkdir(parents=True, exist_ok=True)
    source = settings.order_source("orders_snapshot")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("synthetic source for infrastructure probes, never imported\n", encoding="utf-8")
    manifest = dict(version=1, anonymized=True, money_policy="zero",
        source_file="data/sigma_sim_data_orders.csv", source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    (settings.source_root / "demo-manifest.json").write_text(json.dumps(manifest))


def is_live(pid):
    try:
        return psutil.Process(pid).is_running() and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def test_demo_normalizes_url_without_changing_credentials(monkeypatch, tmp_path):
    settings = demo_env(monkeypatch, tmp_path, "postgres://demo:fake%40secret@localhost/sigma_demo?sslmode=require")
    assert settings.database_url == "postgresql+psycopg://demo:fake%40secret@localhost/sigma_demo?sslmode=require"
    assert settings.mode == "demo"


def test_demo_accepts_launcher_origin_only_in_loopback_mode(monkeypatch, tmp_path):
    demo_env(monkeypatch, tmp_path)
    monkeypatch.setenv("M3_FRONTEND_ORIGIN", "http://127.0.0.1:8041")
    monkeypatch.setenv("M3_DEMO_LOOPBACK_ONLY", "0")
    with pytest.raises(ValueError, match="local frontend"):
        Settings.from_env()
    monkeypatch.setenv("M3_DEMO_LOOPBACK_ONLY", "1")
    assert Settings.from_env().frontend_origin == "http://127.0.0.1:8041"


@pytest.mark.parametrize("key,value", [
    ("M3_DATABASE_URL", "postgresql://demo:secret@localhost/sigma_m3"),
    ("M3_DATABASE_URL", "sqlite:///demo.db"),
    ("M3_FRONTEND_ORIGIN", "https://demo.example/path"),
    ("M3_FRONTEND_ORIGIN", "https://demo.example/"),
    ("M3_FRONTEND_ORIGIN", "https://user:secret@demo.example"),
    ("M3_FRONTEND_ORIGIN", "https://*.example"),
    ("M3_FRONTEND_ORIGIN", "http://remote.example"),
    ("M3_FRONTEND_ORIGIN", "https://demo.example?x=1"),
    ("M3_MODE", "production"),
    ("M3_SOURCE_ROOT", ""),
    ("M3_OUTPUT_ROOT", str(PROJECT_ROOT / "outputs/m3")),
])
def test_rejects_unsafe_demo_configuration(monkeypatch, tmp_path, key, value):
    demo_env(monkeypatch, tmp_path)
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError) as failure:
        Settings.from_env()
    assert "secret" not in str(failure.value)


def test_manifest_and_heartbeat_reject_tampering(monkeypatch, tmp_path):
    settings = demo_env(monkeypatch, tmp_path)
    bundle(settings)
    assert source_ready(settings)
    settings.order_source("orders_snapshot").write_text("changed")
    assert not source_ready(settings)
    (settings.source_root / "demo-manifest.json").write_text("[]")
    assert not source_ready(settings)
    with worker_heartbeat(settings, "code"):
        assert worker_ready(settings, "code")
        with monkeypatch.context() as patch:
            patch.setattr(psutil.Process, "status", lambda self: psutil.STATUS_ZOMBIE)
            assert not worker_ready(settings, "code")
        assert not worker_ready(replace(settings, worker_instance="another-launch"), "code")
        assert not worker_ready(settings, "old-code")
        path = settings.output_root / ".worker-heartbeat.json"
        row = json.loads(path.read_text()); row["updated"] = 0
        path.write_text(json.dumps(row))
        assert not worker_ready(settings, "code")
    assert not worker_ready(settings, "code")


def test_readiness_schema_storage_and_worker_with_real_pg(pg, monkeypatch, tmp_path):
    settings = demo_env(monkeypatch, tmp_path, os.environ["M3_TEST_DATABASE_URL"])
    bundle(settings)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/live").json() == {"status": "ok"}
        assert client.get("/api/v1/ready").status_code == 503
        with worker_heartbeat(settings, client.app.state.code_sha256):
            assert client.get("/api/v1/ready").status_code == 200
            # Writes retain ordinary validation and enqueue; no read-only middleware.
            assert client.post("/api/v1/runs", json={}).status_code == 422
            preflight = client.options("/api/v1/runs", headers={"Origin": settings.frontend_origin,
                "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Idempotency-Key,Content-Type"})
            assert preflight.status_code == 200 and preflight.headers["access-control-allow-origin"] == settings.frontend_origin
            body = dict(kind="source_import", source_key="orders_snapshot", as_of_date="2025-12-31")
            created = client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "demo-write"})
            assert created.status_code == 202
            again = client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "demo-write"})
            assert again.status_code == 200 and again.json()["run_id"] == created.json()["run_id"]
            # This synthetic queued request is removed by the isolated DB fixture;
            # infrastructure source bytes above are intentionally not imported.
            with pg[0].begin() as connection:
                connection.execute(text("DELETE FROM runs"))
            with pg[0].begin() as connection:
                connection.execute(text("UPDATE alembic_version SET version_num='wrong'"))
            try:
                response = client.get("/api/v1/ready")
                assert response.status_code == 503 and response.json()["checks"]["database"] is False
                assert "postgresql" not in response.text and str(tmp_path) not in response.text
            finally:
                with pg[0].begin() as connection:
                    connection.execute(text("UPDATE alembic_version SET version_num='0009_receiving_warehouse'"))
        assert client.get("/api/v1/ready").status_code == 503


def test_supervisor_cleans_model_descendants_after_child_failure(tmp_path):
    marker = tmp_path / "model.pid"
    child = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"
    worker = ("import subprocess,sys,time;from pathlib import Path;"
        f"p=subprocess.Popen([sys.executable,'-c',{child!r}]);Path({str(marker)!r}).write_text(str(p.pid));time.sleep(60)")
    peer = ("import time;from pathlib import Path;"
        f"p=Path({str(marker)!r});\nfor i in range(100):\n if p.exists():break\n time.sleep(.05)\nraise SystemExit(3)")
    assert supervise([[sys.executable, "-c", worker], [sys.executable, "-c", peer]], os.environ.copy()) == 1
    pid = int(marker.read_text())
    assert not is_live(pid)


def test_supervisor_stops_cleanly_on_request():
    stopping = threading.Event()
    timer = threading.Timer(.5, stopping.set); timer.start()
    try:
        assert supervise([[sys.executable, "-c", "import time; time.sleep(60)"]], os.environ.copy(), stopping) == 0
    finally:
        timer.cancel()


def test_real_demo_stack_boot_worker_failure_and_restart(pg, monkeypatch, tmp_path):
    settings = demo_env(monkeypatch, tmp_path, os.environ["M3_TEST_DATABASE_URL"])
    bundle(settings)
    prior_instance = None
    for attempt in range(2):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
        env = {**os.environ, "PORT": str(port), "PYTHONDONTWRITEBYTECODE": "1"}
        process = subprocess.Popen([sys.executable, "web/backend/scripts/demo_stack.py"], cwd=PROJECT_ROOT,
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=os.name == "posix", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                assert process.poll() is None, "Launcher exited before ready"
                try:
                    with urlopen(f"http://127.0.0.1:{port}/api/v1/ready", timeout=1) as response:
                        if response.status == 200: break
                except OSError:
                    time.sleep(.1)
            else:
                pytest.fail("Demo never became ready")
            row = json.loads((settings.output_root / ".worker-heartbeat.json").read_text())
            assert row["instance"] != prior_instance
            prior_instance = row["instance"]
            if attempt == 0:
                psutil.Process(row["pid"]).kill()
                assert process.wait(timeout=15) == 1
            elif os.name == "posix":
                process.send_signal(signal.SIGTERM)
                assert process.wait(timeout=15) == 0
            # A restart must release the old port and worker advisory lock.
        finally:
            stop(process)
        assert not is_live(row["pid"])
