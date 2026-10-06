"""Configuration, provenance and complete-run validation."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ["destination_country", "carrier"]
ITEM = ROUTE + ["sku", "product_type"]
BASELINES = ["naive", "ma7", "seasonal_naive7"]


class DataQualityError(ValueError):
    """A blocking problem; messages must never contain private row values."""


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def config_path(path="data/configs/config.json", root=None):
    """Resolve current inputs and the recorded paths in historical bundles."""
    root = ROOT if root is None else Path(root)
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        relative = path.relative_to(root) if path.is_relative_to(root) else None
        if relative is not None and len(relative.parts) == 1 and relative.name.startswith('config') and relative.suffix == '.json':
            path = root / 'data/configs' / relative.name
        elif relative is not None and relative.parts[0] == 'configs':
            path = root / 'data' / relative
    return path.resolve()


def read_config(path="data/configs/config.json"):
    path = config_path(path)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for key in ["horizon", "refit_days", "top_n"]:
        if not isinstance(cfg[key], int) or cfg[key] < 1:
            raise ValueError(f"Invalid configuration: {key}")
    dates = [cfg[k] for k in ["observation_start", "train_end", "validation_start", "validation_end", "test_start", "test_end"]]
    if dates != sorted(dates):
        raise ValueError("Invalid chronological split")
    if pd.Timestamp(cfg["validation_start"]) != pd.Timestamp(cfg["train_end"]) + pd.Timedelta(days=1):
        raise ValueError("Validation must follow train")
    if pd.Timestamp(cfg["test_start"]) != pd.Timestamp(cfg["validation_end"]) + pd.Timedelta(days=1):
        raise ValueError("Test must follow validation")
    if not set(cfg["sales_statuses"]).issubset(cfg["known_statuses"]):
        raise ValueError("Unknown configured sales status")
    if not cfg["sales_statuses"]:
        raise ValueError("Empty sales definition")
    return cfg


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        return clean_json(value.item())
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(clean_json(value), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def write_csv(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def code_hash():
    paths = sorted({ROOT / "sigma/ui/daily.py", *(ROOT / "src").glob("*.py")})
    digest = hashlib.sha256()
    for path in paths:
        if path.is_file():
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def new_manifest(cfg, source, run_id):
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    packages = {}
    for name in ["numpy", "pandas", "statsmodels", "lightgbm", "matplotlib", "streamlit", "holidays"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "schema_version": "1", "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running", "stages": {}, "files": {},
        "source_sha256": sha256(source), "source_bytes": Path(source).stat().st_size,
        "source_kind": "synthetic" if "synthetic" in Path(source).name else "private_order_snapshot",
        "code_sha256": code_hash(), "git_revision": revision,
        "config": cfg, "python": platform.python_version(), "packages": packages,
        "assumption_status": "user-approved-experiment-not-mentor-confirmed",
        "missing_requirement_sources": ["docs/PROJECT_REQUIREMENTS.png", "docs/Báo cáo chi tiết Sigma.pdf"],
        "snapshot_limit": "Final order statuses are retrospective; operational origin state cannot be reconstructed.",
    }


def seal_manifest(folder, manifest):
    folder = Path(folder)
    manifest["files"] = {p.relative_to(folder).as_posix(): sha256(p) for p in sorted(folder.rglob("*")) if p.is_file() and p.name != "manifest.json" and not p.name.endswith(".tmp")}
    write_json(folder / "manifest.json", manifest)


def validate_run(folder, require_complete=True):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if require_complete and manifest["status"] != "complete":
        raise ValueError("Run is incomplete or failed")
    for name, expected in manifest["files"].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError("Invalid manifest path")
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Missing or changed run artifact: {name}")
    return manifest
