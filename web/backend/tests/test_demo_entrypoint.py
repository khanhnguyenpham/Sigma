"""The tracked local entry point delegates to the existing demo runtime safely."""
from io import BytesIO
import json
from types import SimpleNamespace

import pytest

from src import start_demo
from web.backend.scripts import demo_stack


def test_demo_entrypoint_help_status_stop_and_changed_runtime(monkeypatch, tmp_path, capsys):
    base = tmp_path / "outputs/chg091_d4/local-hosted"
    monkeypatch.setattr(start_demo, "ROOT", tmp_path)
    monkeypatch.setattr(start_demo, "BASE", base)
    with pytest.raises(SystemExit) as help_exit:
        start_demo.main(["--help"])
    assert help_exit.value.code == 0
    assert "start" in capsys.readouterr().out
    assert start_demo.main(["status"]) == 0
    assert json.loads(capsys.readouterr().out) == {"active": False, "status": "stopped"}
    assert start_demo.main(["stop"]) == 0
    assert "stopped" in capsys.readouterr().out
    assert not base.exists()
    base.mkdir(parents=True)
    (base / "connection.json").write_text(json.dumps({"status": "ready", "ready": {"status": "ready"}}))
    assert start_demo.main(["status"]) == 0
    assert json.loads(capsys.readouterr().out) == {"active": False, "status": "stopped"}
    (base / "connection.json").unlink()
    (base / "prepared.json").write_text(json.dumps({"code_sha256": "old"}))
    monkeypatch.setattr(start_demo, "code_digest", lambda: "current")
    def no_process(*args, **kwargs):
        pytest.fail("Unreviewed runtime must not create a process")
    monkeypatch.setattr(start_demo.subprocess, "Popen", no_process)
    with pytest.raises(SystemExit, match="Runtime changed"):
        start_demo.main([])
    assert not (base / "connection.json").exists()
    monkeypatch.setattr(start_demo, "code_digest", lambda: "old")
    with pytest.raises(SystemExit, match="Build web/frontend"):
        start_demo.main(["start"])


@pytest.mark.parametrize("command,loopback,host", [
    ("start-local", "1", "127.0.0.1"),
    ("start", "0", "0.0.0.0"),
])
def test_demo_entrypoint_selects_exposure(monkeypatch, tmp_path, capsys, command, loopback, host):
    outputs = tmp_path / "outputs"
    base = outputs / "chg091_d4/local-hosted"
    base.mkdir(parents=True)
    operator = outputs / "chg089_d2"
    operator.mkdir()
    (operator / "operator-env.json").write_text(json.dumps({"M3_PG_BIN": str(tmp_path)}))
    (base / "prepared.json").write_text(json.dumps({"code_sha256": "approved"}))
    dist = tmp_path / "web/frontend/dist"
    dist.mkdir(parents=True)
    (dist / "index.html").touch()
    runtime_file = base / "runtime-env.private.json"
    runtime = {"PORT": "8041", "M3_DEMO_ROOT": str(base / "sigma-demo")}
    runtime_file.write_text(json.dumps(runtime))
    monkeypatch.setattr(start_demo, "ROOT", tmp_path)
    monkeypatch.setattr(start_demo, "BASE", base)
    monkeypatch.setattr(start_demo, "code_digest", lambda: "approved")
    monkeypatch.setattr(start_demo.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setattr(start_demo, "stop", lambda process: None)
    monkeypatch.setattr(demo_stack.Settings, "from_env", lambda: SimpleNamespace(mode="demo", output_root=base))
    monkeypatch.setattr(demo_stack, "storage_ready", lambda settings: True)
    public_url = "https://demo-example.trycloudflare.com"
    expected_url = start_demo.LOCAL_URL if command == "start-local" else public_url
    spawned = []

    def supervise(commands, env):
        api = commands[1]
        assert api[api.index("--host") + 1] == host
        assert env["M3_FRONTEND_ORIGIN"] == expected_url
        return 0

    def spawn(args, **options):
        spawned.append(args)
        if args[1] == "tunnel":
            options["stdout"].write(public_url)
        else:
            assert args[1:] == ["-m", "web.backend.scripts.demo_stack"]
            env = options["env"]
            assert env["M3_DEMO_LOOPBACK_ONLY"] == loopback
            monkeypatch.setenv("M3_DEMO_LOOPBACK_ONLY", env["M3_DEMO_LOOPBACK_ONLY"])
            monkeypatch.setenv("M3_FRONTEND_ORIGIN", env["M3_FRONTEND_ORIGIN"])
            assert demo_stack.main() == 0
        return SimpleNamespace(pid=len(spawned))

    def ready(url, timeout):
        assert url == f"{start_demo.LOCAL_URL}/api/v1/ready"
        (base / ".stop-requested").touch()
        response = BytesIO(b'{"status":"ready"}')
        response.status = 200
        return response

    monkeypatch.setattr(demo_stack, "supervise", supervise)
    monkeypatch.setattr(start_demo.subprocess, "Popen", spawn)
    monkeypatch.setattr(start_demo.urllib.request, "urlopen", ready)
    assert start_demo.main([command]) == 0
    assert capsys.readouterr().out.strip() == expected_url
    assert len(spawned) == (1 if command == "start-local" else 2)
    if command == "start-local":
        assert not (base / "tunnel.private.log").exists()
        assert json.loads(runtime_file.read_text()) == runtime
