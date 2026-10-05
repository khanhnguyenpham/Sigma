"""Early opportunities never replace the full replay event denominator."""
import pandas as pd
import pytest

from sigma.analysis.alert_diagnostics import explain_events


def example():
    return pd.DataFrame({
        'destination_country': ['Fake'] * 6, 'carrier': ['A'] * 6,
        'sku': ['sample'] * 6, 'product_type': ['eSIM'] * 6,
        'as_of_date': pd.date_range('2025-01-01', periods=6),
        'actual_days': [3., 9., 8., None, None, 0.],
        'predicted_days': [2., 7., None, 10., None, 0.],
        'already_empty': [False] * 5 + [True],
        'tp': [True, True, False, False, False, True],
        'fp': [False, False, False, True, False, False],
        'fn': [False, False, True, False, False, False],
        'event_id': ['fake-internal'] * 6,
    })


def test_short_depletion_missed_and_already_empty_have_distinct_meanings():
    view, stats = explain_events(example())
    assert stats == {'windows': 6, 'actual_events': 3, 'already_empty_excluded': 1,
        'events_before_day7': 1, 'events_with_7day_opportunity': 2,
        'missed_with_7day_opportunity': 1, 'detected_with_7day_opportunity': 1,
        'official_early_event_rate': 1 / 3, 'opportunity_recall_diagnostic': .5}
    assert view.diagnostic_group.nunique() == 6
    assert 'event_id' not in view
    with pytest.raises(ValueError, match='Duplicate'):
        explain_events(pd.concat([example(), example().iloc[:1]]))


def test_no_event_denominators_are_unknown_not_perfect_accuracy():
    view, stats = explain_events(example().iloc[4:5])
    assert stats['official_early_event_rate'] is None and stats['opportunity_recall_diagnostic'] is None
    with pytest.raises(ValueError, match='Incomplete'):
        explain_events(example().drop(columns='actual_days'))
