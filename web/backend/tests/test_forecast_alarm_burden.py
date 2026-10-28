"""Boundary and accounting checks for retrospective alarm burden, no new forecast."""

from datetime import date

import pytest

from web.backend.research import forecast_alarm_burden as burden


def alarm(day="2025-01-10", prediction="2025-01-17", stock=2):
    return dict(date=day, item_id=1, predicted_depletion_date=prediction, origin_on_hand=stock)


def order(ordered="2025-01-10", eta="2025-01-17", initial=False):
    return dict(item_id=1, ordered_on=ordered, eta=eta, is_initial=initial, ordered_qty=5)


@pytest.mark.parametrize("event_day,orders,end,label", [
    ("2025-01-24", [order()], "2025-01-31", "TP"),
    ("2025-01-10", [], "2025-01-31", "FP"),
    ("2025-01-25", [], "2025-01-31", "FP"),
    (None, [order()], "2025-01-31", "intervened"),
    (None, [order(ordered="2025-01-09")], "2025-01-31", "FP"),
    (None, [order(initial=True)], "2025-01-31", "FP"),
    (None, [], "2025-01-24", "FP"),
    (None, [], "2025-01-23", "right_censored"),
    ("2025-01-20", [], "2025-01-23", "TP"),
    (None, [order()], "2025-01-23", "intervened"),
])
def test_status_matches_H14_priority(event_day, orders, end, label):
    events = [dict(item_id=1, date=event_day)] if event_day else []
    rows = burden.classify([alarm()], events, orders, date.fromisoformat(end))
    assert rows[0]["label"] == label


def test_known_receipts_use_strictly_prior_information_not_received_status():
    orders = [order(), order(ordered="2025-01-09"), order(initial=True),
              order(ordered="2025-01-01", eta="2025-01-10"), order(ordered="2025-01-01", eta="2025-01-25")]
    assert burden.classify([alarm()], [], orders, date(2025, 1, 31))[0]["known_receipts_H14"] == 10


@pytest.mark.parametrize("rows", [[alarm(), alarm()], [alarm(stock=0)], [alarm(prediction="2025-01-25")]])
def test_reject_duplicate_or_invalid_valid_signal(rows):
    with pytest.raises(ValueError):
        burden.classify(rows, [], [], date(2025, 1, 31))


def test_no_prediction_is_not_counted_as_signal():
    assert burden.classify([alarm(prediction=None, stock=0)], [], [], date(2025, 1, 31)) == []


def test_streaks_preserve_item_days_and_break_at_gaps_or_non_FP():
    rows = [dict(item_id=1, date="2025-01-01", label="FP"), dict(item_id=1, date="2025-01-02", label="TP"),
            dict(item_id=1, date="2025-01-03", label="FP"), dict(item_id=1, date="2025-01-05", label="FP"),
            dict(item_id=2, date="2025-01-01", label="FP")]
    all_runs, fp_runs = burden.streaks(rows), burden.streaks(rows, "FP")
    assert sorted(r["length"] for r in all_runs) == [1, 1, 3]
    assert sorted(r["length"] for r in fp_runs) == [1, 1, 1, 1]
    assert sum(r["length"] for r in all_runs) == len(rows)


def test_daily_distribution_includes_zero_days_and_linear_percentiles():
    result = burden.distribution([0, 0, 2, 6])
    assert result["mean"] == 2 and result["median"] == 1
    assert result["p90"] == pytest.approx(4.8)
    assert burden.distribution([])["mean"] is None


def test_html_escapes_catalog_text():
    assert "&lt;script&gt;" in burden.html_table([dict(sku="<script>")], ["sku"])
