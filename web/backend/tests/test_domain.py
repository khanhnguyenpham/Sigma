from datetime import date, timedelta
import numpy as np
import pandas as pd
import pytest
from core.errors import DomainError
from services.inventory import PolicyValues, recommend, fulfill_day, eta
from services.alerts import project, replay_metrics
from modules.forecasting.allocation import allocate
from modules.runs.schemas import RunCreate
from modules.configuration.schemas import PolicyCreate

D = date(2025, 10, 31)
P = PolicyValues(100, 50, 2)


@pytest.mark.parametrize(
    "stock,pending,trigger,q",
    [
        (99, 0, True, 50),
        (100, 0, False, 0),
        (101, 0, False, 0),
        (80, 40, True, 0),
        (80, 0, True, 50),
    ],
)
def test_strict_floor_moq_pending(stock, pending, trigger, q):
    row = recommend([10] * 14, stock, pending, P)
    assert (row["ss"], row["rop_forecast"], row["rop"], row["target_stock"]) == (
        20,
        90,
        100,
        110,
    )
    assert row["needs_replenishment"] is trigger
    assert row["recommended_qty"] == q
    assert row["inventory_position"] == stock + pending


def test_supplier_specific_floor_and_no_floor():
    a = recommend([10] * 14, 80, 0, PolicyValues(150, 100, 2))
    b = recommend([10] * 14, 80, 0, PolicyValues(0, 50, 2))
    assert (a["rop"], a["target_stock"], a["recommended_qty"]) == (150, 160, 100)
    assert (b["rop"], b["target_stock"], b["recommended_qty"]) == (90, 100, 50)
    assert eta(D) == date(2025, 11, 7)


def test_event_balance_and_no_double_customer_deduction():
    row = fulfill_day(12, 5, [7, 15])
    assert (
        row["sales_qty"],
        row["fulfilled_qty"],
        row["shortage_qty"],
        row["closing_qty"],
    ) == (22, 17, 5, 0)
    assert [e["balance_after"] for e in row["events"]] == [10, 0]
    assert (
        row["closing_qty"]
        == row["opening_qty"] + row["receipts_qty"] - row["fulfilled_qty"]
    )
    assert fulfill_day(0, 0, [3])["shortage_qty"] == 3


@pytest.mark.parametrize(
    "forecast", [[10] * 13, [10] * 15, [np.nan] * 14, [np.inf] * 14, [-1] * 14]
)
def test_incomplete_or_invalid_vector_never_zero_padded(forecast):
    with pytest.raises(DomainError):
        recommend(forecast, 80, 0, P)


@pytest.mark.parametrize(
    "stock,state,lead",
    [
        (100, "early", 10),
        (30, "urgent", 3),
        (0, "already_depleted", 0),
        (200, "not_within_horizon", None),
        (70, "early", 7),
        (60, "urgent", 6),
    ],
)
def test_alert_boundaries(stock, state, lead):
    row = project(D, stock, [10] * 14, {})
    assert (row["state"], row["lead_days"]) == (state, lead)
    assert row["predicted_depletion_date"] == (
        D + timedelta(days=lead) if lead is not None else None
    )


def test_receipt_occurs_at_eta_before_day_sale():
    row = project(D, 100, [10] * 14, {D + timedelta(days=7): 100})
    assert row["state"] == "not_within_horizon"
    assert row["projection"][5]["closing_forecast"] == 40
    assert row["projection"][6]["closing_forecast"] == 130


def test_confusion_and_early_denominators():
    cases = [
        dict(
            as_of_date=D,
            predicted_depletion_date=D + timedelta(days=10),
            actual_depletion_date=D + timedelta(days=10),
        ),
        dict(as_of_date=D, predicted_depletion_date=D + timedelta(days=3)),
        dict(as_of_date=D, actual_depletion_date=D + timedelta(days=9)),
        dict(as_of_date=D, already_depleted=True),
    ]
    m = replay_metrics(cases)
    assert (m["TP"], m["FP"], m["FN"], m["TN"]) == (1, 1, 1, 0)
    assert m["precision"] == m["recall"] == m["early_rate"] == 0.5
    assert (m["early_numerator"], m["event_denominator"], m["excluded_count"]) == (
        1,
        2,
        1,
    )
    empty = replay_metrics([])
    assert empty["precision"] is None and empty["early_rate"] is None


def history():
    return pd.DataFrame(
        {1: 6.0, 2: 4.0, 3: 1000.0}, index=pd.date_range("2025-07-01", D)
    )


def test_allocation_conservation_and_future_item_exclusion():
    h = history()
    first = {1: "2024-01-01", 2: "2024-01-01", 3: "2025-11-01"}
    rows = allocate(h, first, D, [70, 140])
    assert set(rows.item_id) == {1, 2}
    np.testing.assert_allclose(
        rows.loc[rows.horizon_day.le(7)].groupby("item_id").forecast_qty.sum(),
        [42, 28],
        atol=1e-8,
    )
    np.testing.assert_allclose(
        rows.loc[rows.horizon_day.gt(7)].groupby("item_id").forecast_qty.sum(),
        [84, 56],
        atol=1e-8,
    )
    changed = pd.concat(
        [
            h,
            pd.DataFrame(
                {1: [9999.0], 2: [8888.0], 3: [7777.0]},
                index=[pd.Timestamp("2025-11-01")],
            ),
        ]
    )
    pd.testing.assert_frame_equal(rows, allocate(changed, first, D, [70, 140]))


def test_allocation_90_fallback_missing_source_and_missing_basis():
    h = history()[[1, 2]]
    first = {1: "2024-01-01", 2: "2024-01-01"}
    h.iloc[-30:] = 0
    assert allocate(h, first, D, [70, 140]).share_window_days.eq(90).all()
    with pytest.raises(DomainError, match="90 calendar"):
        allocate(h.drop(h.index[-10]), first, D, [70, 140])
    with pytest.raises(DomainError, match="No item sales"):
        allocate(h * 0, first, D, [70, 140])


def test_dto_rejects_source_path_and_mutable_lead_time():
    with pytest.raises(ValueError):
        RunCreate(kind="source_import", source_key="C:/secret.csv", as_of_date=D)
    with pytest.raises(ValueError):
        PolicyCreate(
            item_id=1,
            supplier_id=1,
            effective_from=D,
            configured_rop_floor=100,
            moq=50,
            safety_days=2,
            expected_version=0,
            lead_time_days=3,
        )
    with pytest.raises(ValueError):
        PolicyCreate(
            item_id=1,
            supplier_id=1,
            effective_from=D,
            configured_rop_floor=True,
            moq=50,
            safety_days=2,
            expected_version=0,
        )


def test_arithmetic_overflow_does_not_produce_a_false_zero_recommendation():
    with pytest.raises(DomainError):
        recommend([1e30] * 14, 80, 0, P)
    with pytest.raises(ValueError):
        PolicyCreate(
            item_id=1,
            supplier_id=1,
            effective_from=D,
            configured_rop_floor=2**64,
            moq=50,
            safety_days=2,
            expected_version=0,
        )
    from decimal import Decimal

    assert (
        recommend([10] * 14, 80, 0, PolicyValues(100, 50, Decimal("2.000")))[
            "recommended_qty"
        ]
        == 50
    )


def test_duplicate_allocation_history_is_blocked():
    h = history()
    with pytest.raises(DomainError, match="unique dates"):
        allocate(
            pd.concat([h, h.tail(1)]), {1: "2024-01-01", 2: "2024-01-01"}, D, [70, 140]
        )
