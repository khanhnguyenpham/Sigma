"""Synthetic checks for public payload integrity and session-only M3 planning."""

import csv
from datetime import date
import gzip
import io
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "streamlit"))
from sigma_public import runtime
from sigma_public.planner import plan


def fixture_release(folder):
    folder.mkdir()
    tables, files = {}, {}
    for name in runtime.TABLES:
        filename = name + ".csv.gz"
        frame = pd.DataFrame(dict(quantity=[1]))
        data = gzip.compress(frame.to_csv(index=False).encode(), mtime=0)
        (folder / filename).write_bytes(data)
        tables[name] = dict(file=filename, rows=1, columns=["quantity"])
        files[filename] = runtime.sha(data)
    binary = io.BytesIO()
    np.savez_compressed(
        binary, forecast=np.zeros((1, 920, 14)), origins=np.array(["2025-12-31"])
    )
    (folder / "item_forecasts.npz").write_bytes(binary.getvalue())
    files["item_forecasts.npz"] = runtime.sha(binary.getvalue())
    meta = dict(
        kind="sigma-m3-public-v1",
        raw_orders_included=False,
        tables=tables,
        files=files,
        profile=dict(L=7, R=1, H=14),
        acceptance=dict(version="r05-sales-30d-v1"),
    )
    data = json.dumps(meta).encode()
    (folder / "manifest.json").write_bytes(data)
    (folder / "manifest.sha256").write_text(runtime.sha(data))
    return meta


def test_public_payload_integrity_and_immutable_cube(tmp_path):
    folder = tmp_path / "release"
    fixture_release(folder)
    meta, _ = runtime.manifest(folder)
    assert runtime.table(folder, meta, "catalog").quantity.tolist() == [1]
    cube, origins = runtime.item_cube(folder, meta)
    assert cube.shape == (1, 920, 14) and origins[0] == "2025-12-31"
    with pytest.raises(ValueError):
        cube[0, 0, 0] = 1
    (folder / "catalog.csv.gz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        runtime.table(folder, meta, "catalog")
    (folder / "manifest.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        runtime.manifest(folder)


def test_public_schema_forbids_private_identifiers():
    data = gzip.compress(b"order_id\nSYNTHETIC-ONLY\n")
    with pytest.raises(ValueError, match="schema"):
        runtime.decode_table(data, dict(columns=["order_id"], rows=1))


def test_public_csv_preserves_null_context_and_escapes_formulas():
    frame = pd.DataFrame(
        dict(model=["=formula"], actual_qty=[np.nan], forecast_qty=[10.5])
    )
    meta = dict(
        version="demo",
        source_sha256="a" * 64,
        acceptance=dict(version="r05-sales-30d-v1"),
    )
    data = runtime.csv_export(frame, meta, "future/30d")
    row = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))[0]
    assert row["model"] == "'=formula" and row["actual_qty"] == ""
    assert row["forecast_qty"] == "10.5" and row["export_scope"] == "future/30d"


def test_public_plan_uses_m3_pending_strict_trigger_and_eta():
    result = plan(date(2025, 10, 28), np.ones(14), 7, 20, 7, 20, 10, 2)
    assert result["decision"]["inventory_position"] == 27
    assert result["decision"]["rop"] == 20
    assert result["decision"]["target_stock"] == 21
    assert result["decision"]["recommended_qty"] == 0
    assert result["decision"]["state"] == "pending_covers"
    assert result["proposed_eta"] == "2025-11-04"
    assert result["timeline"].iloc[6].receipts_existing_qty == 20
    equal = plan(date(2025, 10, 28), np.ones(14), 20, 0, 7, 20, 10, 2)
    assert (
        not equal["decision"]["needs_replenishment"]
        and equal["decision"]["recommended_qty"] == 0
    )
    low = plan(date(2025, 10, 28), np.ones(14), 19, 0, 7, 20, 10, 2)
    assert low["decision"]["recommended_qty"] == 10


def test_public_plan_sensitivity_does_not_mutate_forecast():
    f = np.ones(14)
    result = plan(
        date(2025, 10, 28),
        f,
        2,
        20,
        7,
        20,
        10,
        2,
        demand_factor=2.0,
        receipt_fraction=0.5,
    )
    assert np.array_equal(f, np.ones(14))
    assert result["timeline"].iloc[0].forecast_qty == 2
    assert result["timeline"].iloc[6].receipts_existing_qty == 10
    assert result["timeline"].iloc[7].forecast_qty == 1
    assert result["is_simulated"] is True


@pytest.mark.parametrize(
    "changed",
    [
        dict(arrival_days=8),
        dict(demand_factor=float("nan")),
        dict(receipt_fraction=1.1),
        dict(shock_days=0),
    ],
)
def test_public_plan_rejects_invalid_inputs(changed):
    kwargs = dict(
        origin=date(2025, 10, 28),
        forecast=np.ones(14),
        on_hand=5,
        pending=0,
        arrival_days=7,
        floor=10,
        moq=1,
        safety_days=2,
    )
    kwargs.update(changed)
    with pytest.raises(ValueError):
        plan(**kwargs)
