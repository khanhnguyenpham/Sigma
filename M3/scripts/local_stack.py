"""Start/stop only owned local API+worker processes. PostgreSQL is managed separately."""

import argparse, json, os, subprocess, sys, time
from pathlib import Path
import psutil
from sqlalchemy import text
from sigma_m3.db import database
from sigma_m3.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "outputs/m3-stack.json"


def owned(record):
    try:
        process = psutil.Process(record["pid"])
        return (
            process
            if abs(process.create_time() - record["created"]) < 0.1
            and process.exe().lower() == str(Path(sys.executable).resolve()).lower()
            else None
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def stop(records):
    for record in reversed(records):
        process = owned(record)
        if process:
            # A model pool belongs to the worker. Capture identity before stopping
            # anything and never terminate unrelated Python/Node processes.
            children = [
                dict(pid=p.pid, created=p.create_time())
                for p in process.children(recursive=True)
            ]
            for child_record in reversed(children):
                child = owned(child_record)
                if child:
                    child.terminate()
                    try:
                        child.wait(5)
                    except psutil.TimeoutExpired:
                        child.kill()
                        child.wait(5)
            process.terminate()
            try:
                process.wait(10)
            except psutil.TimeoutExpired:
                process.kill()
                process.wait(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["start", "stop"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    previous = json.loads(STATE.read_text()) if STATE.exists() else []
    if args.command == "stop":
        stop(previous)
        STATE.unlink(missing_ok=True)
        print(
            "Stopped the processes recorded by this launcher. PostgreSQL remains available."
        )
        return
    if any(owned(record) for record in previous):
        raise SystemExit(
            "This checkout already has a managed local stack. Stop it before starting another."
        )
    if not 1024 <= args.port <= 65535:
        raise SystemExit("Port must be in 1024..65535")
    if not (ROOT / "M3/frontend/dist/index.html").is_file():
        raise SystemExit("Build M3/frontend with npm ci and npm run build first.")
    settings = Settings.from_env()
    engine, _ = database(settings.database_url)
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    # Check local binding before launching either child; never stop an existing service.
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
    STATE.parent.mkdir(parents=True, exist_ok=True)
    records = []
    try:
        for label, arguments in [
            ("worker", ["-m", "sigma_m3.worker"]),
            (
                "api",
                [
                    "-m",
                    "uvicorn",
                    "sigma_m3.main:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.port),
                ],
            ),
        ]:
            with (STATE.parent / f"m3-{label}.log").open("ab") as log:
                process = subprocess.Popen(
                    [sys.executable, *arguments],
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            records.append(
                dict(
                    pid=process.pid,
                    created=psutil.Process(process.pid).create_time(),
                    kind=label,
                )
            )
        STATE.write_text(json.dumps(records, indent=2))
        time.sleep(2)
        if not all(owned(r) for r in records):
            raise RuntimeError(
                "A child exited; inspect outputs/m3-api.log and outputs/m3-worker.log"
            )
    except Exception:
        stop(records)
        STATE.unlink(missing_ok=True)
        raise
    print(
        f"SIGMA M3 ready at http://127.0.0.1:{args.port}/ ; API and worker are running in the background."
    )


if __name__ == "__main__":
    main()
