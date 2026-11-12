"""Foreground supervisor for one demo API and worker, including their model children."""
import os
import signal
import subprocess
import sys
import threading
import time
import uuid

import psutil
from core.demo import storage_ready
from core.settings import PROJECT_ROOT, Settings


def group_alive(group):
    for process in psutil.process_iter(["pid", "status"]):
        try:
            if (process.info["status"] not in {psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD}
                    and os.getpgid(process.pid) == group):
                return True
        except (OSError, psutil.Error):
            continue
    return False


def stop(process, *, group=True, owned=()):
    if os.name == "posix" and group:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            pass
        # The root may have exited while a model child ignores SIGTERM.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        # SIGKILL delivery is asynchronous. Reaping only the direct child is
        # insufficient when its model children have already been reparented.
        deadline = time.monotonic() + 5
        while group_alive(process.pid):
            if time.monotonic() >= deadline:
                raise RuntimeError("Demo process group did not stop")
            time.sleep(.02)
    else:
        targets = list(owned)
        try:
            parent = psutil.Process(process.pid)
            targets += parent.children(recursive=True) + [parent]
        except psutil.NoSuchProcess:
            pass
        # Long jobs retain handles for exited model pools. Check process identity
        # before cleanup; waiting on a recycled Windows PID can raise AccessDenied.
        targets = [p for p in {p.pid: p for p in targets}.values() if p.is_running()]
        for target in reversed(targets):
            try:
                target.terminate()
            except psutil.NoSuchProcess:
                pass
        def remaining():
            live = []
            for target in targets:
                try:
                    if target.is_running() and target.status() not in {psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD}:
                        live.append(target)
                except psutil.NoSuchProcess:
                    pass
            return live
        deadline = time.monotonic() + 5
        while (alive := remaining()) and time.monotonic() < deadline:
            time.sleep(.02)
        for target in alive:
            try:
                target.kill()
            except psutil.NoSuchProcess:
                pass
        deadline = time.monotonic() + 5
        while remaining() and time.monotonic() < deadline:
            time.sleep(.02)
        process.wait(timeout=5)
        if remaining():
            raise RuntimeError("Demo process tree did not stop")


def supervise(commands, env, stopping=None):
    stopping = stopping or threading.Event()
    children = []
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, lambda *_: stopping.set())
    try:
        for command in commands:
            children.append(subprocess.Popen(command, cwd=PROJECT_ROOT, env=env,
                stdin=subprocess.DEVNULL, start_new_session=os.name == "posix",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        while not stopping.wait(.2):
            if any(child.poll() is not None for child in children):
                print("Demo process exited; stopping the complete stack.", file=sys.stderr)
                return 1
        return 0
    finally:
        failure = None
        for child in reversed(children):
            try:
                stop(child)
            except Exception as error:
                failure = error
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if failure:
            raise RuntimeError("Could not stop the complete demo stack") from failure


def main():
    settings = Settings.from_env()
    if settings.mode != "demo":
        raise SystemExit("demo_stack requires M3_MODE=demo")
    settings.output_root.mkdir(parents=True, exist_ok=True)
    if not storage_ready(settings):
        raise SystemExit("Demo source manifest or artifact disk is not ready; prepare D2 first")
    try:
        port = int(os.environ.get("PORT", "8000"))
        if not 1024 <= port <= 65535:
            raise ValueError()
    except ValueError:
        raise SystemExit("PORT must be in 1024..65535") from None
    host = "127.0.0.1" if os.environ.get("M3_DEMO_LOOPBACK_ONLY") == "1" else "0.0.0.0"
    env = {**os.environ, "M3_WORKER_INSTANCE": str(uuid.uuid4())}
    return supervise([[sys.executable, "-m", "worker"], [sys.executable, "-m", "uvicorn",
        "main:create_app", "--factory", "--host", host, "--port", str(port),
        '--limit-concurrency', '64', '--timeout-keep-alive', '5']], env)


if __name__ == "__main__":
    raise SystemExit(main())
