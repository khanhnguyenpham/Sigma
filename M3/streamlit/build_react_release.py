"""Build an allowlisted React/Streamlit release, retaining all sealed source data.

Only sanitized simulated projection values are added to the existing public alerts;
no raw explanation, order/customer IDs, transactions, DB or environment is copied.
"""

import argparse
from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid
import numpy as np
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from sigma_public import runtime
from sigma_m3.db import database
from sigma_m3.models import Alert, Item, Warehouse
from sigma_m3.settings import Settings
from sigma_m3.services.runs import required_run


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(base, destination, frontend, settings):
    base, destination, frontend = Path(base), Path(destination), Path(frontend)
    if destination.exists():
        raise ValueError("Destination must be new")
    meta, pin = runtime.manifest(base / "release_m3")
    for name in meta["files"]:
        runtime.payload(base / "release_m3", meta, name)
    catalog = runtime.table(base / "release_m3", meta, "catalog")
    keys = {
        (r.destination_country, r.carrier, r.sku, r.product_type): int(r.item_key)
        for r in catalog.itertuples()
    }
    alerts = runtime.table(base / "release_m3", meta, "alerts")
    labels = {
        uuid.UUID(meta["runs"][name]["run_id"]): name
        for name in ["alert_base", "snapshot_2025-10-31_pending", "snapshot_2025-12-31"]
    }
    projections = {}
    engine, sessions = database(settings.database_url)
    try:
        with sessions() as session:
            for key, label in labels.items():
                run = required_run(session, key, complete=True)
                if (
                    run.source_sha256 != meta["source_sha256"]
                    or run.target_version != meta["target_version"]
                ):
                    raise ValueError("Public source differs")
            query = (
                select(
                    Alert.run_id,
                    Alert.as_of_date,
                    Alert.alert_type,
                    Alert.item_id,
                    Alert.explanation,
                    Item.sku,
                    Item.product_type,
                    Warehouse.destination_country,
                    Warehouse.carrier,
                )
                .join(Item, Item.id == Alert.item_id)
                .join(Warehouse, Warehouse.id == Item.warehouse_id)
                .where(Alert.run_id.in_(labels))
            )
            for (
                run_id,
                origin,
                kind,
                item_id,
                explanation,
                sku,
                product,
                country,
                carrier,
            ) in session.execute(query):
                key = (
                    labels[run_id],
                    str(origin),
                    kind,
                    keys[(country, carrier, sku, product)],
                )
                if kind != "depletion":
                    continue
                raw = explanation.get("projection")
                if not isinstance(raw, list) or len(raw) != 14:
                    raise ValueError("Projection incomplete")
                safe = []
                for h, row in enumerate(raw, 1):
                    day = (origin + timedelta(days=h)).isoformat()
                    qty, receipt = (
                        float(row["closing_forecast"]),
                        float(row["receipts_qty"]),
                    )
                    if (
                        row["date"] != day
                        or not np.isfinite([qty, receipt]).all()
                        or min(qty, receipt) < 0
                    ):
                        raise ValueError("Invalid projection")
                    safe.append(
                        dict(date=day, closing_forecast=qty, receipts_qty=receipt)
                    )
                if key in projections:
                    raise ValueError("Duplicate public alert")
                projections[key] = json.dumps(
                    safe, separators=(",", ":"), allow_nan=False
                )
    finally:
        engine.dispose()
    alerts["projection_json"] = [
        projections.get((r.run_label, str(r.as_of_date), r.alert_type, int(r.item_key)))
        for r in alerts.itertuples()
    ]
    if alerts[alerts.alert_type == "depletion"].projection_json.isna().any():
        raise ValueError("Missing public projection")
    destination.mkdir(parents=True)
    shutil.copytree(base / "release_m3", destination / "release_m3")
    release = destination / "release_m3"
    data = gzip.compress(alerts.to_csv(index=False).encode("utf-8"), mtime=0)
    (release / "alerts.csv.gz").write_bytes(data)
    meta["version"] = "m3-react-public-20261020-v2"
    meta["prepared_at_utc"] = datetime.now(timezone.utc).isoformat()
    meta["base_public_manifest_sha256"] = pin
    meta["projection_scope"] = (
        "date, closing_forecast, receipts_qty only; no raw explanation"
    )
    meta["ui_profile"] = "react-management-session"
    meta["files"]["alerts.csv.gz"] = sha(data)
    meta["tables"]["alerts"]["columns"] = list(alerts)
    manifest = json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False).encode(
        "utf-8"
    )
    (release / "manifest.json").write_bytes(manifest)
    (release / "manifest.sha256").write_text(sha(manifest), encoding="ascii")
    shutil.copytree(
        Path(__file__).parent / "sigma_public",
        destination / "sigma_public",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in [
        "__init__.py",
        "errors.py",
        "services/inventory.py",
        "services/alerts.py",
    ]:
        target = destination / "sigma_m3" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "M3/backend/src/sigma_m3" / name, target)
    if not (frontend / "index.html").is_file():
        raise ValueError("Build the Streamlit React bundle first")
    shutil.copytree(frontend, destination / "react_ui")
    (destination / "streamlit_app.py").write_text(
        "from sigma_public.react_host import main\nmain()\n", encoding="utf-8"
    )
    shutil.copyfile(base / "requirements.txt", destination / "requirements.txt")
    (destination / ".streamlit").mkdir()
    (destination / ".streamlit/config.toml").write_text(
        '[browser]\ngatherUsageStats = false\n[client]\ntoolbarMode = "minimal"\n[theme]\nprimaryColor = "#5366df"\nbase = "light"\n',
        encoding="utf-8",
    )
    return dict(
        status="prepared_not_published",
        version=meta["version"],
        manifest_sha256=sha(manifest),
        projection_rows=int(alerts.projection_json.notna().sum()),
        release_bytes=sum(p.stat().st_size for p in release.iterdir()),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--frontend", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.base, args.destination, args.frontend, Settings.from_env())
        )
    )
