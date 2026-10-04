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
