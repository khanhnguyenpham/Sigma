"""Start, stop or inspect the isolated local demo and its temporary HTTPS tunnel."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "web/backend/src"), str(ROOT)]
from core.hashes import code_digest
from web.backend.scripts.demo_stack import stop

BASE = ROOT / "outputs/chg091_d4/local-hosted"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Chay/dung demo SIGMA local va link HTTPS tam.")
    parser.add_argument("command", choices=["start", "stop", "status"], nargs="?", default="start",
                        help="start (mac dinh), stop hoac status")
    args = parser.parse_args(argv)
    state_file, stop_file = BASE / "connection.json", BASE / ".stop-requested"
    if not BASE.resolve().is_relative_to(ROOT / "outputs/chg091_d4"):
        raise SystemExit("Refuse a demo directory outside the isolated D4 root")
    previous = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    owner = None
    try:
        candidate = psutil.Process(previous["supervisor_pid"])
        if abs(candidate.create_time() - previous["supervisor_created"]) < .01 and candidate.is_running():
            owner = candidate
    except (KeyError, psutil.Error):
        pass
    if args.command == "status":
        current = {**previous, "active": owner is not None,
                   "status": previous.get("status", "starting") if owner else "stopped"}
        if not owner:
            current.pop("ready", None)
        print(json.dumps(current, indent=2))
        return 0
    if args.command == "stop":
        if owner:
            stop_file.write_text("Operator requested stop\n", encoding="utf-8")
            deadline = time.monotonic() + 25
            while owner.is_running() and time.monotonic() < deadline:
                time.sleep(.2)
            if owner.is_running():
                raise SystemExit("Shutdown has not finished; inspect supervisor.private.log")
        print("Demo supervisor stopped")
        return 0
    if owner:
        raise SystemExit("Demo is already running; use status")
    prepared_file = BASE / "prepared.json"
    if not prepared_file.exists():
        raise SystemExit("Demo is not prepared; see web/backend/configs/DEMO_RUNTIME.md")
    prepared = json.loads(prepared_file.read_text(encoding="utf-8"))
    if code_digest() != prepared["code_sha256"]:
        raise SystemExit("Runtime changed; review code/schema/build before opening the demo. No migration was run.")
    if not (ROOT / "web/frontend/dist/index.html").is_file():
        raise SystemExit("Build web/frontend with npm run build before starting the demo")
    runtime = json.loads((BASE / "runtime-env.private.json").read_text(encoding="utf-8"))
    if runtime.get("PORT") != "8041" or Path(runtime["M3_DEMO_ROOT"]) != BASE / "sigma-demo":
        raise SystemExit("Refuse a runtime outside the isolated demo on port8041")
    pg_bin = Path(json.loads((ROOT / "outputs/chg089_d2/operator-env.json").read_text(encoding="utf-8-sig"))["M3_PG_BIN"])
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    children, started_postgres = [], False
    state = {"status": "starting", "supervisor_pid": os.getpid(),
             "supervisor_created": psutil.Process().create_time(), "api_port": 8041, "postgres_port": 55433}

    def save():
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def stopping(*_):
        stop_file.write_text("Signal requested stop\n", encoding="utf-8")

    stop_file.unlink(missing_ok=True)
    handlers = {signum: signal.signal(signum, stopping) for signum in (signal.SIGTERM, signal.SIGINT)}
    save()
    try:
        with (BASE / "postgres-control.private.log").open("a") as log:
            status = subprocess.run([str(pg_bin / "pg_ctl.exe"), "-D", str(BASE / "pgdata"), "status"],
                                    stdout=log, stderr=log, creationflags=flags)
            if status.returncode:
                subprocess.run([str(pg_bin / "pg_ctl.exe"), "-D", str(BASE / "pgdata"),
                                "-l", str(BASE / "postgres.private.log"), "-w", "start"],
                               check=True, stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=flags)
                started_postgres = True
        tunnel_log = BASE / "tunnel.private.log"
        with tunnel_log.open("w", encoding="utf-8") as log:
            tunnel = subprocess.Popen([str(ROOT / "outputs/chg091_d4/tools/cloudflared.exe"), "tunnel",
                "--no-autoupdate", "--protocol", "http2", "--metrics", "127.0.0.1:20441",
                "--url", "http://127.0.0.1:8041"], cwd=BASE, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, creationflags=flags)
        children.append(tunnel)
        state["tunnel_pid"] = tunnel.pid
        save()
        deadline = time.monotonic() + 90
        while True:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", tunnel_log.read_text(encoding="utf-8", errors="replace"))
            if match:
                public = match.group()
                break
            if tunnel.poll() is not None or time.monotonic() > deadline or stop_file.exists():
                raise RuntimeError("Tunnel did not provide an HTTPS URL; inspect tunnel.private.log")
            time.sleep(.3)
        runtime["M3_FRONTEND_ORIGIN"] = public
        (BASE / "runtime-env.private.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("M3_", "PGPASSWORD", "PGPASSFILE"))}
        env.update(runtime)
        with (BASE / "stack.private.log").open("a", encoding="utf-8") as log:
            backend = subprocess.Popen([sys.executable, "-m", "web.backend.scripts.demo_stack"], cwd=ROOT, env=env,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=flags)
        children.append(backend)
        state.update(backend_pid=backend.pid, url=public)
        save()
        deadline = time.monotonic() + 60
        while True:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8041/api/v1/ready", timeout=3) as response:
                    ready = json.load(response)
                    assert response.status == 200
                break
            except Exception:
                if any(p.poll() is not None for p in children) or time.monotonic() > deadline or stop_file.exists():
                    raise RuntimeError("Demo readiness failed; inspect stack.private.log") from None
                time.sleep(.5)
        state.update(status="ready", ready=ready, code_sha256=code_digest())
        save()
        print(public, flush=True)
        while not stop_file.exists():
            if any(p.poll() is not None for p in children):
                raise RuntimeError("A demo process stopped; shutting down the owned stack")
            time.sleep(.4)
    finally:
        try:
            for process in reversed(children):
                stop(process)
        finally:
            if started_postgres:
                with (BASE / "postgres-control.private.log").open("a") as log:
                    subprocess.run([str(pg_bin / "pg_ctl.exe"), "-D", str(BASE / "pgdata"), "-m", "fast", "-w", "stop"],
                                   stdout=log, stderr=log, creationflags=flags)
            state["status"] = "stopped"
            save()
            for signum, handler in handlers.items():
                signal.signal(signum, handler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
