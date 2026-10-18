import numpy as np
import pandas as pd
import pytest

from sigma.experiments.aggregate_focus import fit_harmonic,predict_harmonic,blend,specifications


@pytest.mark.parametrize('label',['daily_sum','end_total'])
@pytest.mark.parametrize('transform',['raw','log_smear'])
def test_harmonic_fit_ignores_all_future_labels_and_predicts_consecutive_total(label,transform):
    dates=pd.date_range('2024-01-01',periods=731)
    y=pd.Series(10+3*np.sin(np.arange(731)*2*np.pi/365.25),index=dates)
    spec={'label':label,'transform':transform,'harmonics':2,'alpha':1,'training_days':540}
    cutoff=pd.Timestamp('2025-06-30')
    state,info=fit_harmonic(y,cutoff,30,spec)
    changed=y.copy();changed.loc[changed.index>cutoff]=1000000
    other,other_info=fit_harmonic(changed,cutoff,30,spec)
    a=predict_harmonic(state,cutoff,30,spec);b=predict_harmonic(other,cutoff,30,spec)
    assert a==b and a>0 and info==other_info and info['max_label_end']<=cutoff
    assert abs(a-y.loc['2025-07-01':'2025-07-30'].sum())<10


def forecast():
    return pd.DataFrame({'destination_country':['Synthetic'],'carrier':['One'],'window_days':[30],
        'split':['validation'],'as_of_date':[pd.Timestamp('2025-06-30')],
        'window_start':[pd.Timestamp('2025-07-01')],'target_date':[pd.Timestamp('2025-07-30')],
        'model':['A'],'forecast_qty':[100.],'actual_qty':[0.],'fit_cutoff':[pd.Timestamp('2025-06-29')]})


def test_mixture_conserves_origin_alignment_keeps_zero_and_rejects_missing_component():
    base=forecast();other=base.copy();other['forecast_qty']=200.
    result=blend(base,other,.25,'mix')
    assert result.forecast_qty.iloc[0]==125 and result.actual_qty.iloc[0]==0
    other.loc[0,'actual_qty']=np.nan
    with pytest.raises(AssertionError):blend(base,other,.25,'mix')
    with pytest.raises(ValueError,match='Incomplete'):blend(base,base.iloc[:0],.25,'mix')
    with pytest.raises(ValueError):blend(base,base,1.25,'mix')
