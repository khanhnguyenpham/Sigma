"""Allowlisted release reader. Hash the same bytes that are subsequently parsed."""

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import numpy as np
import pandas as pd

TABLES = {
    "catalog",
    "route_daily",
    "monthly_forecasts",
    "monthly_metrics",
    "baselines",
    "weekly",
    "weekly_metrics",
    "inventory",
    "alerts",
    "receipts",
    "scenarios",
}
FORBIDDEN = {
    "order_id",
    "customer_id",
    "order_datetime",
    "activation_datetime",
    "event_id",
    "email",
    "phone",
    "password",
    "token",
    "source_sequence",
    "order_key",
    "explanation",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest(folder):
    folder = Path(folder)
    data = (folder / "manifest.json").read_bytes()
    pin = (folder / "manifest.sha256").read_text().strip()
    if sha(data) != pin:
        raise ValueError("Release manifest checksum differs")
    meta = json.loads(data)
    if (
        meta.get("kind") != "sigma-m3-public-v1"
        or meta.get("raw_orders_included") is not False
        or set(meta["tables"]) != TABLES
        or meta["profile"] != {"L": 7, "R": 1, "H": 14}
        or meta["acceptance"]["version"] != "r05-sales-30d-v1"
    ):
        raise ValueError("Unexpected public release scope")
    expected = {v["file"] for v in meta["tables"].values()} | {"item_forecasts.npz"}
    if set(meta["files"]) != expected:
        raise ValueError("Unexpected release files")
    for name in expected:
        if Path(name).name != name:
            raise ValueError("Invalid release path")
    return meta, pin


def payload(folder, meta, name):
    data = (Path(folder) / name).read_bytes()
    if sha(data) != meta["files"][name]:
        raise ValueError("Release payload checksum differs")
    return data


def table(folder, meta, name):
    if name not in TABLES:
        raise ValueError("Unknown public table")
    spec = meta["tables"][name]
    return decode_table(payload(folder, meta, spec["file"]), spec)


def decode_table(data, spec):
    frame = pd.read_csv(io.BytesIO(gzip.decompress(data)), float_precision="round_trip")
    if (
        list(frame.columns) != spec["columns"]
        or len(frame) != spec["rows"]
        or FORBIDDEN & set(frame)
    ):
        raise ValueError("Unexpected public table schema")
    return frame


def item_cube(folder, meta):
    return decode_cube(payload(folder, meta, "item_forecasts.npz"))


def decode_cube(data):
    with np.load(io.BytesIO(data), allow_pickle=False) as raw:
        forecast, origins = raw["forecast"], raw["origins"]
    if (
        forecast.shape != (len(origins), 920, 14)
        or not np.isfinite(forecast).all()
        or (forecast < 0).any()
    ):
        raise ValueError("Incomplete H14 public allocation cube")
    if list(origins) != sorted(set(origins.tolist())):
        raise ValueError("Duplicate or unordered origins")
    forecast.setflags(write=False)
    origins.setflags(write=False)
    return forecast, origins


def csv_export(frame, meta, scope):
    """Context travels with each row; spreadsheet formulas remain inert strings."""
    frame = frame.copy()
    for name, value in {
        "release_version": meta["version"],
        "source_sha256": meta["source_sha256"],
        "acceptance_version": meta["acceptance"]["version"],
        "export_scope": scope,
    }.items():
        frame[name] = value
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(frame.columns)
    for row in frame.itertuples(index=False, name=None):
        writer.writerow(
            [
                ""
                if pd.isna(value)
                else "'" + value
                if isinstance(value, str)
                and value.startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
                for value in row
            ]
        )
    return output.getvalue().encode("utf-8-sig")
