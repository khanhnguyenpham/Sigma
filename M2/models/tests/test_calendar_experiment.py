"""Calendar edge cases, announcement availability, parity and model leakage."""
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from M2.models.calendar_reference import (CalendarReference, build_reference, feature_names,
                                         holiday_view, analyze_train)
from M2.models.calendar_experiment import variants, compare_control, reconcile_labels
from M2.models.LightGBM.model import phase
from M2.models.tests.test_model_families import fixture


@pytest.fixture(scope='module')
def calendar():
    config = json.loads((ROOT/'data/configs/m2-calendar.json').read_text(encoding='utf-8'))
    frame, events = build_reference(config)
    return CalendarReference(frame, events), config


def test_full_grid_leap_lunar_overlap_and_cross_year(calendar):
    reference, config = calendar
    frame = reference.frame
    assert len(frame) == 4 * 745 == 2980
    assert frame.date.min() == pd.Timestamp('2024-01-01')
    assert frame.date.max() == pd.Timestamp('2026-01-14')
    assert len(frame.loc[frame.date.eq('2024-02-29')]) == 4
    assert not {'quantity', 'sales_qty', 'order_id', 'customer_id', 'is_peak'} & set(frame)
    korea = frame.loc[frame.destination_country.eq('South Korea')].set_index('date')
    assert 'Korean New Year' in korea.loc['2024-02-10', 'destination_holiday_name']
    assert 'Korean New Year' in korea.loc['2025-01-29', 'destination_holiday_name']
    assert korea.loc['2025-05-05', 'destination_holiday'] == 1
    assert 'Buddha' in korea.loc['2025-05-05', 'destination_holiday_name']
    assert 'Children' in korea.loc['2025-05-05', 'destination_holiday_name']
    assert korea.loc['2025-03-03', 'destination_is_observed'] == 1
    assert korea.loc['2026-01-04', 'vn_period_start'] == pd.Timestamp('2026-01-01')
    assert korea.loc['2026-01-05', 'vn_after7'] == 1
    assert 'New Year' in korea.loc['2026-01-05', 'vn_related_holiday_name']
    assert korea.loc['2025-02-01', 'vn_holiday'] == 1
    assert korea.loc['2025-02-01', 'vn_is_public_office_break'] == 1


def test_late_announcement_filters_all_calendar_derivatives(calendar):
    reference, _ = calendar
    before = reference.as_of('South Korea', '2025-01-14')
    after = reference.as_of('South Korea', '2025-01-15')
    assert before.loc['2025-01-27', 'destination_holiday'] == 0
    assert after.loc['2025-01-27', 'destination_holiday'] == 1
    assert before.loc['2025-01-20', 'destination_before7'] == 0
    assert after.loc['2025-01-20', 'destination_before7'] == 1
    a = reference.as_of('South Korea', '2025-04-07')
    b = reference.as_of('South Korea', '2025-04-08')
    assert a.loc['2025-06-03', 'destination_holiday'] == 0
    assert b.loc['2025-06-03', 'destination_holiday'] == 1
    assert reference.as_of('China', '2024-11-11').loc['2025-01-28', 'destination_holiday'] == 0
    assert reference.as_of('China', '2024-11-12').loc['2025-01-28', 'destination_holiday'] == 1
    assert reference.as_of('Japan', '2025-12-24').loc['2026-01-02', 'vn_holiday'] == 0
    assert reference.as_of('Japan', '2025-12-25').loc['2026-01-02', 'vn_holiday'] == 1


def test_unknown_special_dates_never_enter_model_features(calendar):
    reference, _ = calendar
    unknown = [e for e in reference.events if e['known_from'] is None]
    assert unknown
    trimmed = CalendarReference(reference.frame, [e for e in reference.events if e['known_from'] is not None])
    pd.testing.assert_frame_equal(reference.as_of('Thailand', '2025-08-01'),
                                  trimmed.as_of('Thailand', '2025-08-01'))
    with pytest.raises(ValueError, match='unavailable'):
        reference.as_of('Europe (EU)', '2025-01-01')
    with pytest.raises(ValueError, match='group'):
        feature_names('invented')


def test_week_features_sum_all_target_days_and_leave_flags_unscaled(calendar):
    reference, _ = calendar
    week = reference.weekly('South Korea', pd.DatetimeIndex(['2025-01-20']), pd.DatetimeIndex(['2025-01-21']))
    assert week.cal_destination_holiday.item() == 1  # Jan27; the other six days matter too
    assert week.cal_vn_holiday.item() == 3  # Jan25-27 official break
    summer = reference.weekly('Japan', pd.DatetimeIndex(['2025-06-29']), pd.DatetimeIndex(['2025-06-30']))
    assert summer.cal_summer_hypothesis.item() == 7
    assert summer.cal_spring_hypothesis.item() == 0
    assert len(feature_names('both_season')) == 13


def test_holiday_period_boundary_buffer_and_empty_calendar():
    events = [{'date': '2023-12-31', 'name': 'New Year', 'is_observed': False, 'kind': 'library_public_holiday',
               'source': 'fixture', 'known_from': '2023-01-01', 'verification_status': 'fixture'}]
    frame = holiday_view(pd.date_range('2024-01-01', periods=10), events)
    assert frame.iloc[0].after7 == 1 and frame.iloc[6].after7 == 1 and frame.iloc[7].after7 == 0
    empty = holiday_view(pd.date_range('2024-01-01', periods=2), [])
    assert empty.holiday.sum() == 0 and empty.days_to.eq(15).all()


def test_reference_rejects_duplicate_missing_days_and_changed_season(calendar):
    reference, _ = calendar
    with pytest.raises(ValueError, match='Duplicate'):
        CalendarReference(pd.concat([reference.frame, reference.frame.iloc[:1]]), reference.events)
    with pytest.raises(ValueError, match='Incomplete'):
        CalendarReference(reference.frame.iloc[1:], reference.events)
    changed = reference.frame.copy()
    changed.loc[0, 'summer_hypothesis'] = 1
    with pytest.raises(ValueError, match='hypotheses'):
        CalendarReference(changed, reference.events)


def test_train_peak_detection_excludes_validation_and_counts_holidays_without_surges(calendar):
    reference, _ = calendar
    dates = pd.date_range('2024-01-01', '2025-07-10')
    daily = pd.DataFrame({'date': dates, 'destination_country': 'South Korea', 'carrier': 'LG U+',
                          'sales_qty': 10., 'order_count': 10.})
    daily.loc[daily.date.eq('2025-06-01'), 'sales_qty'] = 100.
    cfg = {'train_end': '2025-06-30', 'anomalies': {'history_days': 28, 'minimum_history_days': 14,
           'robust_z_threshold': 4., 'relative_change_threshold': .5}}
    daily['gross_revenue_vnd'] = daily.sales_qty * 100
    peaks, summary, matched = analyze_train(daily, cfg, reference)
    assert peaks.date.max() <= pd.Timestamp(cfg['train_end'])
    assert ((peaks.date == '2025-06-01') & (peaks.window_days == 1)).any()
    assert summary.non_surge_days.sum() > 0 and len(matched) > 0
    changed = daily.copy(); changed.loc[changed.date.gt(cfg['train_end']), 'sales_qty'] = 999999.
    for a, b in zip((peaks, summary, matched), analyze_train(changed, cfg, reference), strict=True):
        pd.testing.assert_frame_equal(a, b)


def test_small_real_estimator_control_parity_ratio_and_future_mutation(calendar):
    reference, experiment = calendar
    series, cfg, settings = fixture()
    cfg['validation_end'] = cfg['validation_start']
    settings.update(minimum_history_days=90, min_child_samples=5)
    models = variants(settings, experiment)
    assert len(models) == 10
    small = {**settings, 'models': {'LightGBM': {k: models[k] for k in ['lgbm_annual_ratio7', 'lgbm_calendar_both_season']}}}
    def make(values):
        return pd.DataFrame({'date': values.index, 'sales_qty': values.to_numpy(), 'order_count': values.to_numpy(),
                             'destination_country': 'South Korea', 'carrier': 'LG U+'})
    groups = {('South Korea', 'LG U+'): series}
    original, logs = phase(make(series), groups, cfg, small, 'direct_7d', 'validation', calendar_reference=reference)
    control, _ = phase(make(series), groups, cfg,
        {**settings, 'models': {'LightGBM': {'lgbm_annual_ratio7': settings['models']['LightGBM']['lgbm_annual_ratio7']}}},
        'direct_7d', 'validation')
    assert compare_control(original.loc[original.model.eq('lgbm_annual_ratio7')], control, 1e-8)['maximum_forecast_difference'] == 0
    changed = series.copy(); changed.loc[changed.index > '2024-06-30'] = 999999.
    other, _ = phase(make(changed), {('South Korea', 'LG U+'): changed}, cfg, small,
                     'direct_7d', 'validation', calendar_reference=reference)
    np.testing.assert_array_equal(original.forecast_qty, other.forecast_qty)
    assert (logs.max_label_end <= logs.fit_cutoff).all()
    assert reconcile_labels(original, make(series), cfg) == len(original)
