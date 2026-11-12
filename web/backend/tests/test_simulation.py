from datetime import date, datetime, timedelta, timezone
import pandas as pd
import pytest
from modules.inventory.simulation import pure_window
from core.errors import DomainError

ORIGIN = date(2025, 9, 30)


def inputs():
    matrix = pd.DataFrame({1: 10}, index=pd.date_range("2025-08-01", "2025-10-31"))
    catalog = [
        dict(
            item_id=1,
            destination_country="Demo",
            carrier="DemoNet",
            sku="DEMO",
            product_type="eSIM",
            first_seen_date="2024-01-01",
        )
    ]
    policies = [
        dict(
            id=1,
            item_id=1,
            supplier_id=1,
            version=1,
            effective_from="2025-09-30",
            effective_to=None,
            configured_rop_floor=100,
            moq=50,
            safety_days=2,
        )
    ]
    vectors = {(ORIGIN + timedelta(days=h), 1): [10] * 14 for h in range(32)}
    events = {
        (ORIGIN + timedelta(days=h), 1): [
            dict(
                event_at=datetime(2025, 10, h, 10, tzinfo=timezone.utc),
                source_sequence=h,
                quantity=10,
            )
        ]
        for h in range(1, 15)
    }
    scenario = dict(
        cover_days=7, safety_multiplier=1, receipts_initial=[], receipts_declared=True
    )
    return matrix, events, catalog, vectors, policies, scenario


def test_policy_replay_places_and_receives_at_exact_eta_without_double_counting():
    result = pure_window(
        *inputs(), "policy_replay", ORIGIN, ORIGIN + timedelta(days=14)
    )
    assert result["orders"][0]["ordered_on"] == ORIGIN
    assert result["orders"][0]["eta"] == date(2025, 10, 7)
    receipts = [e for e in result["events"] if e["event_kind"] == "receipt"]
    assert receipts[0]["event_at"].date() == date(2025, 10, 7)
    assert sum(r["sales_qty"] for r in result["ledger"]) == 140
    assert len(
        {
            (r["window_origin"], r["item_id"], r["event_sequence"])
            for r in result["events"]
        }
    ) == len(result["events"])
    for row in result["ledger"]:
        assert (
            row["closing_qty"]
            == row["opening_qty"] + row["receipts_qty"] - row["fulfilled_qty"]
        )
        assert row["sales_qty"] == row["fulfilled_qty"] + row["shortage_qty"]
        assert row["inventory_position"] == row["closing_qty"] + row["pending_qty"]


def test_alert_replay_does_not_place_orders_and_has_single_first_event():
    result = pure_window(*inputs(), "alert_replay", ORIGIN, ORIGIN + timedelta(days=14))
    assert not result["orders"]
    depletion = [a for a in result["alerts"] if a["alert_type"] == "depletion"]
    assert len(depletion) == 1
    assert (
        depletion[0]["predicted_depletion_date"]
        == depletion[0]["actual_depletion_date"]
        == date(2025, 10, 7)
    )
    assert depletion[0]["evaluation_class"] == "TP"
    assert result["cases"][0]["as_of_date"] == ORIGIN


def test_stock_projection_is_snapshot_without_future_actual_ledger():
    result = pure_window(*inputs(), "stock_projection", ORIGIN, ORIGIN)
    assert len(result["ledger"]) == 1 and result["ledger"][0]["sales_qty"] == 0
    assert not result["orders"] and result["summary"]["fill_rate"] is None
    assert result["alerts"][0]["is_evaluable"] is False


@pytest.mark.parametrize(
    "recent,older,missing_day,fallback_days,expected",
    [
        (0, 3, None, 90, 15),
        (1, 3, None, 90, 7),
        (0, 0, None, 90, 0),
        (0, 3, 40, 90, 0),
        (0, 3, None, None, 0),
        (0, 3, 1, 90, None),
    ],
)
def test_initial_stock_uses_only_complete_history_at_cutoff(
    recent, older, missing_day, fallback_days, expected
):
    args = list(inputs())
    dates = pd.date_range(ORIGIN - timedelta(days=89), ORIGIN + timedelta(days=1))
    matrix = pd.DataFrame({1: [older] * 62 + [recent] * 28 + [900]}, index=dates)
    if missing_day is not None:
        matrix = matrix.drop(pd.Timestamp(ORIGIN - timedelta(days=missing_day)))
    args[0] = matrix
    if expected is None:
        with pytest.raises(DomainError) as error:
            pure_window(*args, "stock_projection", ORIGIN, ORIGIN, initial_stock_fallback_days=fallback_days)
        assert error.value.code == "insufficient_history"
    else:
        result = pure_window(*args, "stock_projection", ORIGIN, ORIGIN, initial_stock_fallback_days=fallback_days)
        assert result["ledger"][0]["opening_qty"] == result["events"][0]["quantity"] == expected


def test_missing_vector_fails_instead_of_using_actual_sales():
    args = list(inputs())
    args[3] = {}
    with pytest.raises(DomainError, match="H14"):
        pure_window(*args, "policy_replay", ORIGIN, ORIGIN + timedelta(days=1))
