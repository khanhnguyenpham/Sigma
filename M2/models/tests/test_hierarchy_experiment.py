import numpy as np
import pandas as pd
import pytest

from M2.models.hierarchy_experiment import country_daily,allocate,blend_selected
from M2.models.focus_experiment import phase
from M2.models.calendar_experiment import reconcile_labels
from M2.models.tests.test_focus_experiment import data,experiment


def test_country_allocation_uses_past_share_and_route_actuals():
    daily,cfg,settings=data(); exp=experiment()
    exp['parents']={'focus_control':{}}
    pred,_=phase(country_daily(daily),cfg,settings,exp,'validation',['focus_control_raw'])
    result=allocate(pred,daily,[28,56,90])
    assert reconcile_labels(result,daily,cfg)==6
    # Fixture country quantity is LG U+ + KT, with a fixed past LG U+ share of 1/2.2.
    for window in [28,56,90]:
        np.testing.assert_allclose(result.loc[result.model.str.endswith(f'share{window}'),'forecast_qty'],pred.forecast_qty/2.2,atol=1e-8,rtol=0)
    changed=daily.copy(); changed.loc[changed.date>'2024-06-30','sales_qty']*=1000
    mutated,_=phase(country_daily(changed),cfg,settings,exp,'validation',['focus_control_raw'])
    other=allocate(mutated,changed,[28,56,90])
    np.testing.assert_array_equal(result.forecast_qty,other.forecast_qty)
    future,_=phase(country_daily(daily),cfg,settings,exp,'future',['focus_control_raw'])
    assert allocate(future,daily,[28]).actual_qty.isna().all()


def test_selected_blend_aligns_pairs_and_rejects_missing_pairs():
    daily,cfg,settings=data(); exp=experiment()
    pred,_=phase(country_daily(daily),cfg,settings,exp,'validation',['focus_control_raw'])
    allocated=allocate(pred,daily,[28]); base=allocated.iloc[::-1].copy(); base['forecast_qty']*=2
    result=blend_selected(allocated,base,'selected')
    np.testing.assert_allclose(result.forecast_qty,allocated.forecast_qty*1.5,rtol=0,atol=1e-8)
    with pytest.raises(AssertionError): blend_selected(allocated,base.iloc[:1],'selected')
