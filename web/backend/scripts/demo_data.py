"""Offline operator tools for the isolated demo, never exposed as HTTP routes."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from psycopg import sql

from core.db import database
from core.demo import schema_head, source_ready
from core.hashes import code_digest
from core.settings import PROJECT_ROOT, Settings
from models import Base
from modules.runs.models import Run
from modules.runs.schemas import RunCreate
from modules.runs.service import enqueue
from modules.inventory.seeding import seed_simulation
from web.backend.scripts.demo_source import export_source
from worker import serve, LOCK_ID


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(settings):
    url = make_url(settings.database_url)
    root = settings.demo_root
    if (settings.mode != "demo" or url.database not in {"sigma_demo", "sigma_m3_test"}
            or root is None or root.name != "sigma-demo" or root == PROJECT_ROOT
            or root in PROJECT_ROOT.parents or settings.source_root != root / "source"
            or settings.output_root != root / "outputs/m3"):
        raise ValueError("Operator tools require the isolated demo database and canonical demo paths")
    return url


def operator_url(settings, value):
    target = check(settings)
    try:
        operator = make_url(value)
        if (operator.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}
                or (operator.host, operator.port, operator.database) != (target.host, target.port, target.database)
                or (operator.database != "sigma_m3_test" and operator.username == target.username)):
            raise ValueError()
        return operator.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
    except Exception:
        raise ValueError("A separate operator URL for the same demo database/server is required") from None


def tree_files(root):
    if root.is_symlink():
        raise ValueError("Demo snapshots cannot use a symlink root")
    result = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("Demo snapshots cannot contain symlinks")
        if p.is_file() and not p.name.startswith(".worker-heartbeat") and not p.name.endswith(".private.log"):
            result[p.relative_to(root).as_posix()] = sha(p)
    return result


def remove_owned(settings, path):
    path = path.resolve()
    if not path.is_relative_to(settings.demo_root) or not path.name.startswith((".snapshot-", ".restore-", ".previous-")):
        raise ValueError("Refuse deletion outside an owned temporary demo directory")
    if path.exists():
        shutil.rmtree(path)


def snapshot_state(engine):
    tables = sorted([*Base.metadata.tables, "alembic_version"])
    state = {}
    with engine.begin() as connection:
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
        raw = connection.connection.driver_connection
        for name in tables:
            columns = [c.name for c in Base.metadata.tables[name].primary_key] if name in Base.metadata.tables else ["version_num"]
            statement = sql.SQL("COPY (SELECT * FROM {} ORDER BY {}) TO STDOUT").format(
                sql.Identifier(name), sql.SQL(",").join(map(sql.Identifier, columns)))
            digest = hashlib.sha256()
            with raw.cursor() as cursor:
                with cursor.copy(statement) as copy:
                    for block in copy:
                        digest.update(block)
                rows = cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(name))).fetchone()[0]
            state[name] = dict(rows=rows, sha256=digest.hexdigest())
    return state


def grant_app(settings, engine):
    role = make_url(settings.database_url).username
    with engine.begin() as connection:
        cursor = connection.connection.driver_connection.cursor()
        cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
        for table in Base.metadata.tables:
            cursor.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON {} TO {}").format(sql.Identifier(table), sql.Identifier(role)))
        cursor.execute(sql.SQL("GRANT SELECT ON alembic_version TO {}").format(sql.Identifier(role)))
        cursor.execute(sql.SQL("GRANT USAGE,SELECT,UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(role)))
        cursor.close()


def pg_tool(settings, operator, tool, pg_bin, dump, *, restore=False):
    check(settings)
    url = make_url(operator_url(settings, operator))
    executable = Path(pg_bin) / (tool + (".exe" if os.name == "nt" else "")) if pg_bin else shutil.which(tool)
    if not executable or not Path(executable).is_file():
        raise ValueError("Install matching PostgreSQL client tools or set M3_PG_BIN")
    env = {**os.environ, "PGHOST": url.host or "", "PGPORT": str(url.port or 5432),
        "PGDATABASE": url.database, "PGUSER": url.username, "PGPASSWORD": url.password or ""}
    for key in ("sslmode", "sslrootcert", "sslcert", "sslkey"):
        if key in url.query:
            env["PG" + key.upper()] = url.query[key]
    args = [str(executable), "--no-owner", "--no-acl"]
    args += ["--clean", "--if-exists", "--single-transaction", "--exit-on-error", "--dbname", url.database] if restore else ["--format=custom"]
    log = settings.demo_root / ".operator.private.log"
    with log.open("ab") as errors, Path(dump).open("rb" if restore else "wb") as stream:
        completed = subprocess.run(args, env=env, stdin=stream if restore else subprocess.DEVNULL,
            stdout=subprocess.DEVNULL if restore else stream, stderr=errors)
    if completed.returncode:
        raise RuntimeError("PostgreSQL operation failed; inspect the private operator log")


@contextmanager
def maintenance(settings, operator, recover=False, destructive=False):
    check(settings)
    url = operator_url(settings, operator)
    marker = settings.demo_root / ".maintenance"
    if marker.exists() and not recover:
        raise ValueError("Maintenance marker exists; inspect the prior failure before --recover")
    if not marker.exists():
        with marker.open("x", encoding="utf-8") as stream:
            json.dump(dict(operation=str(uuid.uuid4()), started=datetime.now(timezone.utc).isoformat()), stream)
    engine, _ = database(url)
    acquired = False
    entered = False
    try:
        with engine.connect() as lock:
            acquired = bool(lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), dict(key=LOCK_ID)))
            if not acquired:
                raise ValueError("Stop the demo launcher/worker before operator maintenance")
            try:
                entered = True
                yield engine
                marker.unlink()
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), dict(key=LOCK_ID))
    finally:
        # A restore may have committed DB state before a filesystem error.
        # Fail closed on any entered operation error; recovery is explicit.
        if (not entered and not recover) or not destructive:
            marker.unlink(missing_ok=True)
        engine.dispose()


def init_schema(settings, operator):
    check(settings)
    with maintenance(settings, operator) as engine:
        from sqlalchemy import inspect
        if set(inspect(engine).get_table_names()) - {"alembic_version"}:
            raise ValueError("Init requires an empty demo database; never overwrites existing data")
        config = Config(str(PROJECT_ROOT / "web/backend/alembic.ini"))
        config.attributes["database_url"] = operator_url(settings, operator)
        command.upgrade(config, "head")
        grant_app(settings, engine)
    settings.output_root.mkdir(parents=True, exist_ok=True)


def run_job(settings, body, request_key=None):
    check(settings)
    engine, sessions = database(settings.database_url)
    try:
        with sessions.begin() as session:
            row, _ = enqueue(session, RunCreate(**body), request_key or str(uuid.uuid4()), settings)
            key = row.id
        while True:
            with sessions() as session:
                row = session.get(Run, key)
                if row.status in {"complete", "failed", "invalidated"}:
                    if row.status != "complete":
                        raise RuntimeError("Demo run failed: " + str(row.error_code))
                    return dict(id=str(row.id), kind=row.kind, summary=row.result_summary)
            serve(replace(settings, worker_instance="operator-" + str(uuid.uuid4())), once=True)
    finally:
        engine.dispose()


def seed(settings, source_id, origin):
    check(settings)
    engine, sessions = database(settings.database_url)
    try:
        with sessions.begin() as session:
            return seed_simulation(session, uuid.UUID(source_id), date.fromisoformat(origin))
    finally:
        engine.dispose()


def backup_path(settings, name):
    check(settings)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
        raise ValueError("Snapshot name must contain only letters, digits, underscore or hyphen")
    path = settings.demo_root / "backups" / name
    if path.parent.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(settings.demo_root):
        raise ValueError("Snapshot path escaped the demo root")
    return path


def backup(settings, operator, name, pg_bin=None):
    destination = backup_path(settings, name)
    if destination.exists() or not source_ready(settings):
        raise ValueError("Backup needs a new name and a verified demo source")
    staging = settings.demo_root / (".snapshot-" + str(uuid.uuid4()))
    staging.mkdir()
    try:
        with maintenance(settings, operator) as engine:
            before = snapshot_state(engine)
            files = tree_files(settings.output_root.parent)
            pg_tool(settings, operator, "pg_dump", pg_bin, staging / "database.dump")
            shutil.copytree(settings.output_root.parent, staging / "outputs",
                ignore=shutil.ignore_patterns(".worker-heartbeat*", "*.private.log"))
            if (snapshot_state(engine) != before or tree_files(settings.output_root.parent) != files
                    or tree_files(staging / "outputs") != files):
                raise ValueError("Demo data changed while taking the offline snapshot")
            manifest = dict(version=1, database=check(settings).database, schema=schema_head(),
                source_sha256=sha(settings.order_source("orders_snapshot")), code_sha256=code_digest(),
                dump_sha256=sha(staging / "database.dump"), tables=before, files=files)
            (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            destination.parent.mkdir(exist_ok=True)
            staging.rename(destination)
        return manifest
    finally:
        if staging.exists():
            remove_owned(settings, staging)


def restore(settings, operator, name, confirm, pg_bin=None, recover=False):
    if confirm != check(settings).database:
        raise ValueError("Reset confirmation must match the isolated demo database name")
    snapshot = backup_path(settings, name)
    manifest = json.loads((snapshot / "manifest.json").read_text())
    if (manifest.get("version") != 1 or manifest.get("database") != confirm
            or manifest.get("schema") != schema_head()
            or manifest.get("source_sha256") != sha(settings.order_source("orders_snapshot"))
            or manifest.get("dump_sha256") != sha(snapshot / "database.dump")
            or manifest.get("files") != tree_files(snapshot / "outputs")):
        raise ValueError("Snapshot hashes, schema or demo source context differ")
    staging = settings.demo_root / (".restore-" + str(uuid.uuid4()))
    previous = settings.demo_root / (".previous-" + str(uuid.uuid4()))
    with maintenance(settings, operator, recover, destructive=True) as engine:
        marker = settings.demo_root / ".maintenance"
        prior = json.loads(marker.read_text())
        old_temporary = prior.get("temporary_dirs", [])
        if old_temporary and prior.get("snapshot") != name:
            raise ValueError("Recover the same snapshot that began the interrupted restore")
        temporary = [*old_temporary, staging.name, previous.name]
        for entry in temporary:
            if (Path(entry).name != entry or not re.fullmatch(r"\.(?:restore|previous)-[0-9a-f-]{36}", entry)):
                raise ValueError("Invalid recovery temporary path")
        prior.update(snapshot=name, temporary_dirs=temporary)
        pending = settings.demo_root / ".maintenance.tmp"
        pending.write_text(json.dumps(prior), encoding="utf-8")
        pending.replace(marker)
        shutil.copytree(snapshot / "outputs", staging)
        pg_tool(settings, operator, "pg_restore", pg_bin, snapshot / "database.dump", restore=True)
        grant_app(settings, engine)
        if snapshot_state(engine) != manifest["tables"]:
            raise ValueError("Restored database rows do not match the snapshot")
        active = settings.output_root.parent
        if active.exists():
            active.rename(previous)
        staging.rename(active)
        if tree_files(active) != manifest["files"]:
            raise ValueError("Restored artifacts do not match the snapshot")
        for entry in temporary:
            if (settings.demo_root / entry).exists():
                remove_owned(settings, settings.demo_root / entry)
    return dict(status="restored", database=confirm, snapshot=name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export"); export.add_argument("--orders", type=Path, required=True)
    sub.add_parser("init")
    run = sub.add_parser("run"); run.add_argument("--request", type=Path, required=True)
    plant = sub.add_parser("seed"); plant.add_argument("--source-run", required=True); plant.add_argument("--origin", required=True)
    save = sub.add_parser("backup"); save.add_argument("--name", required=True)
    reset = sub.add_parser("reset"); reset.add_argument("--name", required=True); reset.add_argument("--confirm", required=True); reset.add_argument("--recover", action="store_true")
    args = parser.parse_args();settings = Settings.from_env();check(settings)
    if args.command == "export": result = export_source(settings, args.orders)
    elif args.command == "run": result = run_job(settings, json.loads(args.request.read_text()))
    elif args.command == "seed": result = seed(settings, args.source_run, args.origin)
    else:
        operator = os.environ.get("M3_OPERATOR_DATABASE_URL", "")
        if args.command == "init": result = init_schema(settings, operator) or dict(status="initialized")
        elif args.command == "backup": result = backup(settings, operator, args.name, os.environ.get("M3_PG_BIN"))
        else: result = restore(settings, operator, args.name, args.confirm, os.environ.get("M3_PG_BIN"), args.recover)
    print(json.dumps(result, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
