import json

import pandas as pd
import pytest

from src.common import seal_manifest, validate_run, write_csv


def test_incomplete_and_tampered_runs_rejected(tmp_path):
    write_csv(tmp_path / "a.csv", pd.DataFrame({"quantity": [3]}))
    manifest = {"status": "partial"}
    seal_manifest(tmp_path, manifest)
    with pytest.raises(ValueError, match="incomplete"):
        validate_run(tmp_path)
    manifest["status"] = "complete"
    seal_manifest(tmp_path, manifest)
    assert validate_run(tmp_path)["status"] == "complete"
    (tmp_path / "a.csv").write_text("quantity\n4\n")
    with pytest.raises(ValueError, match="changed"):
        validate_run(tmp_path)


def test_manifest_rejects_path_escape(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"status": "complete", "files": {"../private.csv": "fake"}}))
    with pytest.raises(ValueError, match="Invalid manifest path"):
        validate_run(tmp_path)


def test_notebook_has_no_outputs():
    import nbformat
    nb = nbformat.read("notebooks/run_local.ipynb", as_version=4)
    assert all(not cell.get("outputs") and cell.get("execution_count") is None for cell in nb.cells)


def test_dashboard_rejects_complete_label_with_missing_schema_artifacts(tmp_path, monkeypatch):
    import src.common as common
    from streamlit.testing.v1 import AppTest
    app_path = common.ROOT / "app.py"
    folder = tmp_path / "outputs" / "synthetic_incomplete_package"
    folder.mkdir(parents=True)
    seal_manifest(folder, {"status": "complete", "schema_version": "1", "config": {}})
    monkeypatch.setattr(common, "ROOT", tmp_path)
    at = AppTest.from_file(str(app_path), default_timeout=30).run()
    assert not at.exception
    assert any("missing required dashboard artifacts" in message.value for message in at.error)


def test_cli_blocking_quality_message_has_category_without_identifiers(tmp_path, monkeypatch, capsys, cfg, order_rows):
    import run
    import sys
    from src.data import SOURCE_COLUMNS
    from src.common import sha256
    order_rows[0]["quantity"] = "-1"
    source = tmp_path / "synthetic_orders.csv"
    pd.DataFrame(order_rows, columns=SOURCE_COLUMNS).to_csv(source, index=False)
    original_hash = sha256(source)
    cfg["source"] = source.name
    config = tmp_path / "config.json"
    config.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(run, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["run.py", "--config", str(config), "--stage", "audit", "--run-id", "invalid_fixture"])
    assert run.main() == 1
    output = capsys.readouterr().err
    assert "invalid_quantity=1" in output
    assert order_rows[0]["order_id"] not in output
    assert order_rows[0]["customer_id"] not in output
    assert sha256(source) == original_hash
