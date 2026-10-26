"""Exact replay snapshots recorded from 203e506 before the step7 extraction."""
import json
from datetime import timedelta
from pathlib import Path

import pytest

from core.hashes import digest
from modules.inventory.simulation import pure_window
from test_simulation import inputs, ORIGIN


def replay_snapshot(kind, variant):
    args = list(inputs())
    if variant == "pending":
        args[5]["receipts_initial"] = [
            dict(item_id=1, lot_key="synthetic-pending", ordered_on=str(ORIGIN - timedelta(days=3)),
                 eta=str(ORIGIN + timedelta(days=4)), ordered_qty=1000)
        ]
    elif variant == "zero_stock":
        args[5]["cover_days"] = 0
    end = ORIGIN if kind == "stock_projection" else ORIGIN + timedelta(days=14)
    return pure_window(*args, kind, ORIGIN, end)


@pytest.mark.parametrize("kind", ["policy_replay", "alert_replay", "stock_projection"])
@pytest.mark.parametrize("variant", ["base", "pending", "zero_stock"])
def test_inventory_replay_matches_pre_step7_snapshot(kind, variant):
    baseline = json.loads((Path(__file__).parent / "fixtures/inventory_step7_baseline.json").read_text())
    expected = baseline["cases"][f"{kind}/{variant}"]
    result = replay_snapshot(kind, variant)
    # Step12 adds threshold signals and a nullable date, not legacy behavior.
    # Compare every original field against the immutable pre-step7 golden.
    result.pop("threshold_cases")
    result["alerts"] = [r for r in result["alerts"] if r["alert_type"] != "projected_below_rop"]
    for row in result["alerts"]:
        row.pop("predicted_threshold_date")
    assert digest(result) == expected["canonical_sha256"]
    assert result["summary"] == expected["summary"]
