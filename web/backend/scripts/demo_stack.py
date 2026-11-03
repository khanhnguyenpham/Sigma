"""Foreground supervisor for one demo API and worker, including their model children."""
import os
import signal
import subprocess
import sys
import threading
import uuid

import psutil
from core.demo import storage_ready
from core.settings import PROJECT_ROOT, Settings


def stop(process):
    if os.name == "posix":
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
    else:
        try:
            parent = psutil.Process(process.pid)
            targets = parent.children(recursive=True) + [parent]
            for target in reversed(targets):
                try:
                    target.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(targets, timeout=5)
            for target in alive:
                try:
                    target.kill()
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(alive, timeout=5)
        except psutil.NoSuchProcess:
            pass
        process.wait(timeout=5)


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
        for child in reversed(children):
            stop(child)
        for signum, handler in previous.items():
            signal.signal(signum, handler)


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
    env = {**os.environ, "M3_WORKER_INSTANCE": str(uuid.uuid4())}
    return supervise([[sys.executable, "-m", "worker"], [sys.executable, "-m", "uvicorn",
        "main:create_app", "--factory", "--host", "0.0.0.0", "--port", str(port)]], env)


if __name__ == "__main__":
    raise SystemExit(main())
