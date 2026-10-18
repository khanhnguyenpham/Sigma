from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from sigma.analysis.planning import Assumptions,simulate,thresholds
from src.inventory import replenishment


def params(**kwargs):
    return replace(Assumptions(on_hand=0,pending_quantity=0,pending_due_days=2,
        lead_time_days=2,review_days=1,safety_days=1),**kwargs)


def test_strict_threshold_and_initial_order_match_historical_policy():
    vector=np.array([2.,3.,1.,4.]*8)[:30]
    for lead in [1,3,7]:
        for safety in [0.,.5,2.]:
            a=params(lead_time_days=lead,safety_days=safety,moq=3)
            settings={'lead_time_days':lead,'review_days':1,'safety_days':safety,'moq':3}
            rop=replenishment(0,vector,0,settings)['ROP']
            for on_hand in [max(0,rop-1),rop,rop+1]:
                for pending in [0,100]:
                    actual=thresholds(on_hand,vector,pending,a)
                    expected=replenishment(on_hand,vector,pending,settings)
                    assert all(actual[k]==v for k,v in expected.items() if k!='on_hand')


def test_receipts_arrive_before_sales_and_partial_promises_do_not_become_stock():
    a=params(pending_quantity=12,pending_due_days=1,receipt_fraction=.5,lead_time_days=2,safety_days=0)
    result=simulate([4.]*8,'2025-12-31',a)
    ledger=result['ledger']
    assert ledger.iloc[0].Q==0 # Existing promise covers target; do not duplicate.
    assert ledger.iloc[1].receipts==6 and ledger.iloc[1].fulfilled==4
    np.testing.assert_allclose(ledger.closing,ledger.opening+ledger.receipts-ledger.fulfilled,atol=1e-10)
    np.testing.assert_allclose(ledger.demand,ledger.fulfilled+ledger.shortage,atol=1e-10)
    assert ledger.closing.ge(0).all() and ledger.actual_qty.isna().all()
    assert result['summary']['benchmark_metric'] is False


def test_no_receipt_and_delay_have_explicit_expected_shortage_and_missing_tail_decisions():
    result=simulate([1.]*7,'2025-12-31',params(receipt_fraction=0,receipt_delay_days=3))
    assert result['summary']['expected_shortage']==7 and result['summary']['expected_fill_rate']==0
    assert result['ledger'].receipts.sum()==0
    assert result['ledger'].tail(3).Q.isna().all() # No silent horizon extension.
    assert result['ledger'].tail(3).decision_status.eq('insufficient_forecast').all()
    assert result['orders'].modeled_eta.iloc[0]==pd.Timestamp('2026-01-05')


def test_zero_demand_keeps_fill_rate_unknown_and_moq_does_not_force_orders():
    result=simulate([0.]*8,'2025-12-31',params(moq=10))
    assert result['summary']['expected_fill_rate'] is None
    assert result['summary']['planned_order_quantity']==0 and result['orders'].empty


@pytest.mark.parametrize('kwargs',[{'lead_time_days':0},{'review_days':1.5},{'receipt_fraction':1.1},
    {'pending_quantity':-1},{'on_hand':True},{'safety_days':float('nan')},{'demand_multiplier':float('inf')}])
def test_invalid_assumptions_are_rejected(kwargs):
    with pytest.raises(ValueError):simulate([1.]*30,'2025-12-31',params(**kwargs))


def test_unknown_future_is_rejected_not_filled_with_zero():
    with pytest.raises(ValueError):simulate([1.,np.nan,2.],'2025-12-31',params())
    with pytest.raises(ValueError):simulate([1.]*3,'2025-12-31',params(lead_time_days=3))
