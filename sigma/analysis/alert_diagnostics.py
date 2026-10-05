"""Explain sealed replay events without changing predictions or denominators."""
import pandas as pd

from src.common import ITEM


def explain_events(alerts):
    required = ITEM + ['as_of_date', 'actual_days', 'predicted_days', 'already_empty', 'tp', 'fp', 'fn']
    if not set(required).issubset(alerts.columns):
        raise ValueError('Incomplete alert replay')
    if alerts.duplicated(ITEM + ['as_of_date']).any():
        raise ValueError('Duplicate alert replay event')
    view = alerts.copy()
    actual = view.actual_days.notna() & ~view.already_empty
    opportunity = actual & view.actual_days.ge(7)
    missed = opportunity & view.fn
    detected = opportunity & view.tp
    view['diagnostic_group'] = 'Không cạn và không cảnh báo'
    view.loc[view.fp, 'diagnostic_group'] = 'Cảnh báo nhưng không cạn'
    view.loc[actual & view.actual_days.lt(7), 'diagnostic_group'] = 'Cạn trước ngày 7 của đợt'
    view.loc[missed, 'diagnostic_group'] = 'Có cơ hội ≥7 ngày nhưng bỏ sót'
    view.loc[detected, 'diagnostic_group'] = 'Có cơ hội ≥7 ngày và đã cảnh báo'
    view.loc[view.already_empty, 'diagnostic_group'] = 'Đã hết tồn tại origin (loại riêng)'
    total, opportunities = int(actual.sum()), int(opportunity.sum())
    stats = {'windows': len(view), 'actual_events': total,
        'already_empty_excluded': int(view.already_empty.sum()),
        'events_before_day7': int((actual & view.actual_days.lt(7)).sum()),
        'events_with_7day_opportunity': opportunities, 'missed_with_7day_opportunity': int(missed.sum()),
        'detected_with_7day_opportunity': int(detected.sum()),
        'official_early_event_rate': int(detected.sum()) / total if total else None,
        'opportunity_recall_diagnostic': int(detected.sum()) / opportunities if opportunities else None}
    # Order/customer identifiers and internal event IDs are not presentation data.
    columns = ITEM + ['as_of_date', 'predicted_days', 'actual_days', 'diagnostic_group']
    columns += [name for name in ['predicted_depletion_date', 'actual_depletion_date'] if name in view]
    return view[columns], stats
