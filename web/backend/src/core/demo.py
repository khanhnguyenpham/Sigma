"""Demo runtime probes and an idle/busy worker heartbeat; no business data writes."""
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import os
import tempfile
import threading
import time

import psutil
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from core.settings import PROJECT_ROOT


@lru_cache(maxsize=1)
def schema_head():
    return ScriptDirectory.from_config(Config(str(PROJECT_ROOT / "web/backend/alembic.ini"))).get_current_head()


@lru_cache(maxsize=2)
def _verified_source(manifest_path, manifest_stat, source_path, source_stat):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not (isinstance(manifest, dict) and type(manifest.get("version")) is int
            and manifest.get("version") == 1 and manifest.get("anonymized") is True
            and manifest.get("money_policy") == "zero"
            and manifest.get("source_file") == "data/sigma_sim_data_orders.csv"):
        return False
    with Path(source_path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == manifest.get("source_sha256")


def source_ready(settings):
    manifest = settings.source_root / "demo-manifest.json"
    source = settings.order_source("orders_snapshot")
    try:
        stats = lambda p: (p.stat().st_mtime_ns, p.stat().st_size)
        return _verified_source(str(manifest), stats(manifest), str(source), stats(source))
    except (OSError, ValueError, TypeError):
        return False


def storage_ready(settings):
    try:
        # Probe only the configured artifact root; never write into the source.
        with tempfile.TemporaryFile(dir=settings.output_root) as stream:
            stream.write(b"probe")
            stream.flush()
        return source_ready(settings)
    except OSError:
        return False


@contextmanager
def worker_heartbeat(settings, code_sha):
    if settings.mode != "demo":
        yield
        return
    if not settings.worker_instance:
        raise ValueError("Demo worker must be started by demo_stack")
    path = settings.output_root / ".worker-heartbeat.json"
    staging = path.with_suffix(f".{os.getpid()}.tmp")
    stopped = threading.Event()
    def write():
        staging.write_text(json.dumps(dict(pid=os.getpid(), started=psutil.Process().create_time(),
            updated=time.time(), instance=settings.worker_instance, code_sha256=code_sha)), encoding="utf-8")
        os.replace(staging, path)
    def pulse():
        while not stopped.wait(2):
            try:
                write()
            except OSError:
                # A stale heartbeat makes readiness fail; it must not pretend healthy.
                pass
    write()
    thread = threading.Thread(target=pulse, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stopped.set()
        thread.join(3)
        path.unlink(missing_ok=True)
        staging.unlink(missing_ok=True)


def worker_ready(settings, code_sha):
    try:
        row = json.loads((settings.output_root / ".worker-heartbeat.json").read_text())
        process = psutil.Process(row["pid"])
        return bool(settings.worker_instance and row["instance"] == settings.worker_instance
            and row["code_sha256"] == code_sha and 0 <= time.time() - row["updated"] < 10
            and abs(process.create_time() - row["started"]) < .1 and process.is_running())
    except (OSError, ValueError, KeyError, TypeError, psutil.Error):
        return False


def readiness(settings, engine, code_sha):
    checks = dict(database=False)
    try:
        with engine.connect() as connection:
            checks["database"] = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all() == [schema_head()]
    except Exception:
        pass  # Readiness never exposes SQL, paths or credentials.
    if settings.mode == "demo":
        checks.update(storage=storage_ready(settings), worker=worker_ready(settings, code_sha))
    return checks
