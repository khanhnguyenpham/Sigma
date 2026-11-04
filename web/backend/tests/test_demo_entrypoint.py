"""The tracked local entry point delegates to the existing demo runtime safely."""
import json
import pytest
from src import start_demo


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
