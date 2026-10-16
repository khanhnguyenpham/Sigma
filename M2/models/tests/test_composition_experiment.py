"""Order moments, causal distribution features and true-quantity count allocation."""
import json

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT
from M2.models.composition_experiment import (FOCUS, MOMENTS, LARGE, DISPERSION, candidates,
    distribution_daily, prepare_quantity, allocate_basket, phase, subexperiment)
from M2.models.adaptive_experiment import phase as control_phase
from M2.models.calendar_experiment import reconcile_labels
from M2.models.tests.test_focus_experiment import data


def experiment():
    return json.loads((ROOT/'data/configs/m2-composition.json').read_text(encoding='utf-8'))


def fixture():
    daily, cfg, settings = data()
    daily['order_count'] = (daily.sales_qty/1.5).round().clip(lower=1)
    daily['large_order_count'] = np.floor(daily.order_count/5)
    daily['large_quantity'] = daily.large_order_count*3
    daily['squared_quantity'] = daily.sales_qty**2/daily.order_count+daily.order_count*.2
    return daily, cfg, settings


def test_aggregate_order_moments_and_block_duplicate_order_rows():
    sales = pd.DataFrame({'order_id': ['example1', 'example2', 'example3'], 'quantity': [1, 3, 2],
        'date': pd.to_datetime(['2024-01-01', '2024-01-01', '2024-01-02']),
        'destination_country': FOCUS[0], 'carrier': FOCUS[1]})
    daily = pd.DataFrame({'date': pd.date_range('2024-01-01', periods=3), 'sales_qty': [4, 2, 0],
        'order_count': [2, 1, 0], 'destination_country': FOCUS[0], 'carrier': FOCUS[1]})
    result = distribution_daily(sales, daily, 3)
    np.testing.assert_array_equal(result[MOMENTS], [[1, 3, 10], [0, 0, 4], [0, 0, 0]])
    with pytest.raises(ValueError): distribution_daily(pd.concat([sales, sales.iloc[:1]]), daily, 3)


def test_distribution_features_and_real_estimator_are_causal_and_control_matches():
    daily, cfg, settings = fixture(); exp = experiment(); assert len(candidates(exp)) == 26
    exp['count_parents'] = {}; exp['quantity_parents'] = {k: v for k, v in exp['quantity_parents'].items() if 'control' in k or 'both' in k}
    cutoff = pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    changed = daily.copy(); changed.loc[changed.date > cutoff, ['sales_qty', 'order_count']+MOMENTS] = 999999
    first, second = prepare_quantity(daily, settings, {'scale_days': 56}), prepare_quantity(changed, settings, {'scale_days': 56})
    for key, table in first.items():
        mask = table['origins'] <= cutoff
        pd.testing.assert_frame_equal(table['x'].loc[mask, LARGE+DISPERSION], second[key]['x'].loc[mask, LARGE+DISPERSION])
    a, _, _, _, checks = phase(daily, cfg, settings, exp, 'validation')
    b, _, _, _, _ = phase(changed, cfg, settings, exp, 'validation')
    np.testing.assert_array_equal(a.forecast_qty, b.forecast_qty)
    assert checks['quantity']['heads'] == 4
    old_exp = subexperiment(exp, 'quantity'); old_exp['parents'] = {'composition_control56': {'scale_days': 56}}
    old, _ = control_phase(daily, cfg, settings, old_exp, 'validation')
    keys = ['model', 'as_of_date', 'block']; control = a.loc[a.model.str.contains('control')]
    np.testing.assert_array_equal(control.sort_values(keys).forecast_qty, old.sort_values(keys).forecast_qty)


def test_count_times_basket_uses_past_ratio_and_restores_quantity_labels():
    daily, cfg, settings = fixture(); exp = experiment()
    exp['quantity_parents'] = {}; exp['count_parents'] = {'count56': exp['count_parents']['count56']}
    result, _, counts, _, checks = phase(daily, cfg, settings, exp, 'validation')
    assert checks['counts']['heads'] == 2
    part = daily.loc[daily.carrier.eq('LG U+')].set_index('date')
    target = part.sales_qty.rolling(7).sum()
    for name, sample in result.groupby('model'):
        component, window = name.split('_basket'); window = int(window)
        ratio = part.sales_qty.rolling(window).sum()/part.order_count.rolling(window).sum()
        baseline = counts.loc[counts.model.eq(component)]
        np.testing.assert_allclose(sample.forecast_qty, baseline.forecast_qty.to_numpy()*ratio.reindex(sample.as_of_date), atol=1e-10, rtol=0)
        expected = target.reindex(sample.target_date).to_numpy(copy=True)
        expected[sample.target_date.gt(cfg['validation_end']).to_numpy()] = np.nan
        np.testing.assert_array_equal(sample.actual_qty, expected)
    changed = daily.copy(); cutoff = pd.Timestamp(cfg['validation_start'])-pd.Timedelta(days=1)
    changed.loc[changed.date > cutoff, ['sales_qty', 'order_count']+MOMENTS] = 999999
    name = 'count56_mul56p4_basket56'
    selected, _, _, _, _ = phase(changed, cfg, settings, exp, 'validation', [name])
    np.testing.assert_array_equal(selected.forecast_qty, result.loc[result.model.eq(name), 'forecast_qty'])
    future, _, _, _, _ = phase(daily, cfg, settings, exp, 'future', [name])
    assert future.actual_qty.isna().all() and len(future) == 2


def test_partial_week_labels_stay_blank_despite_future_snapshot_orders():
    daily, cfg, settings = fixture(); exp = experiment()
    cfg['validation_end'] = str(pd.Timestamp(cfg['validation_start'])+pd.Timedelta(days=9))[:10]
    result, _, _, _, _ = phase(daily, cfg, settings, exp, 'validation', ['count56_raw_basket56'])
    assert result.actual_qty.notna().any() and result.actual_qty.isna().any()
    assert result.loc[result.target_date.gt(cfg['validation_end']), 'actual_qty'].isna().all()
    assert reconcile_labels(result, daily, cfg) == len(result)
