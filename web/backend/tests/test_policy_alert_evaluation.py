from datetime import date, timedelta
from types import SimpleNamespace

from modules.alerts.policy_evaluation import policy_warning_metrics


def test_scores_purchasing_run_episodes_and_separates_followup():
    origin = date(2025, 10, 31)
    def day(offset):
        return origin + timedelta(days=offset)

    def row(item, offset, closing=5, predicted=None, opening=5, received=0):
        return SimpleNamespace(item_id=item, date=day(offset), opening_qty=opening,
                               closing_qty=closing, receipts_qty=received, sales_allowed=True,
                               predicted_depletion_date=None if predicted is None else day(predicted))

    rows = [
        row(1, 0, predicted=7), row(1, 1, predicted=7), row(1, 7, closing=0),
        row(1, 8, closing=0, opening=0), row(1, 10, closing=0, opening=0, received=5),
        row(2, 0), row(2, 9, closing=0),
        row(3, 0, predicted=8), row(4, 10, predicted=14),
        row(5, 0, closing=0, opening=0),
    ]
    receipts = [SimpleNamespace(item_id=3, ordered_on=day(0), eta=day(7))]
    result = policy_warning_metrics(rows, receipts, day(14))
    assert result["event_denominator"] == 3
    assert result["eligible_early_events"] == 2
    assert result["observed_early_numerator"] == 1
    assert result["eligible_detection_rate"] == 0.5
    assert result["recall"] == 1 / 3
    assert result["warnings_with_receipt"] == 1
    assert result["warnings_with_incomplete_followup"] == 1
    assert result["blocked_sales_item_days"] == result["warnings_with_sales_block"] == 0


def test_provider_block_separates_warnings_and_depletions_before_and_after_resume():
    origin = date(2025, 10, 31)

    def row(item, offset, *, stock=5, warning=False, allowed=True):
        day = origin + timedelta(days=offset)
        return SimpleNamespace(item_id=item, date=day, opening_qty=5, receipts_qty=0,
                               closing_qty=stock, sales_allowed=allowed,
                               predicted_depletion_date=day + timedelta(days=8) if warning else None)

    rows = [
        row(1, 0, warning=True), row(1, 4, allowed=False), row(1, 7), row(1, 12, stock=0),
        row(2, 0, warning=True), row(2, 8, stock=0), row(2, 10, allowed=False),
        row(3, 0, warning=True), row(3, 4, allowed=False), row(3, 5, warning=True), row(3, 13, stock=0),
    ]
    receipts = [SimpleNamespace(item_id=1, ordered_on=origin, eta=origin + timedelta(days=3))]
    result = policy_warning_metrics(rows, receipts, origin + timedelta(days=14))
    assert result["event_denominator"] == 3
    assert result["eligible_early_events"] == result["observed_early_numerator"] == 2
    assert result["detected_events"] == 2 and result["recall"] == 2 / 3
    assert result["blocked_sales_item_days"] == 3
    assert result["warnings_with_sales_block"] == 2
    assert result["warnings_with_receipt"] == result["warnings_with_incomplete_followup"] == 0
