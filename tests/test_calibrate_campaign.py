"""Calibration isolation, independently known optima and coverage guards."""
import numpy as np
import pandas as pd
import pytest
from sigma.experiments.calibration import fit_head,predict_head,matrix


def test_future_labels_and_forecasts_cannot_change_a_calibration_head():
    dates=pd.date_range('2025-05-01',periods=16)
    x=np.column_stack([np.arange(16)+1.,np.full(16,5.)]);y=np.arange(16)+2.
    cutoff=dates[7]
    a=fit_head(x,y,dates,cutoff,False)
    changed_x=x.copy();changed_y=y.copy()
    changed_x[8:]=np.nan;changed_y[8:]=1e9
    b=fit_head(changed_x,changed_y,dates,cutoff,False)
    np.testing.assert_array_equal(a['weights'],b['weights'])
    assert a['intercept']==b['intercept'] and a['max_label_date']==cutoff


def test_convex_combination_can_recover_an_independent_exact_target():
    x=np.array([[1.,9.],[3.,7.],[9.,1.],[7.,3.]])
    # The only exact constant is a half-and-half mixture; neither base is exact.
    state=fit_head(x,np.full(4,5.),pd.date_range('2025-01-01',periods=4),'2025-01-04')
    np.testing.assert_allclose(state['weights'],[.5,.5],atol=1e-8)
    np.testing.assert_allclose(predict_head(state,x),5.,atol=1e-8)


def test_missing_base_pairs_are_not_silently_dropped():
    f=pd.DataFrame({'destination_country':['Fake']*3,'carrier':['A']*3,
       'as_of_date':pd.to_datetime(['2025-05-31','2025-05-31','2025-06-01']),
       'target_date':pd.to_datetime(['2025-06-01','2025-06-01','2025-06-02']),
       'horizon_day':[1]*3,'model':['a','b','a'],'forecast_qty':[3.,4.,3.],'actual_qty':[5.]*3})
    with pytest.raises(ValueError,match='coverage'):matrix(f)


def test_negative_observed_labels_are_errors_not_an_easy_day_filter():
    with pytest.raises(ValueError,match='Negative historical'):
        fit_head(np.ones((2,1)),np.array([3.,-2.]),pd.date_range('2025-01-01',periods=2),'2025-01-02')
