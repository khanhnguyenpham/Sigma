import numpy as np
import pandas as pd
import pytest

from sigma.analysis.benchmark import baseline_forecasts,score,compare


def test_baselines_do_not_read_future_or_skip_zero_days():
    dates=pd.date_range('2025-01-01',periods=60)
    series=pd.Series(np.arange(60,dtype=float),index=dates)
    origin=dates[40];before=baseline_forecasts(series,pd.DatetimeIndex([origin]),7)
    series.loc[series.index>origin]=100000
    after=baseline_forecasts(series,pd.DatetimeIndex([origin]),7)
    assert all(np.array_equal(before[name],after[name]) for name in before)
    assert before['MA7'][0]==sum(range(34,41)) and before['Naive'][0]==280
    with pytest.raises(ValueError,match='Missing calendar'):baseline_forecasts(series.drop(index=dates[1]),pd.DatetimeIndex([origin]),7)


def test_zero_missing_forecasts_and_bias_keep_metric_contract():
    result=score([0,10,20],[5,8,25])
    assert result['mape_positive_pct']==22.5 and result['mae']==4 and result['bias']==8/3
    assert result['n_zero_pairs']==1 and result['coverage']==1
    assert not score([0,0],[0,0])['passes_20_pct']
    missing=score([10,10],[10,np.nan])
    assert missing['coverage']==.5 and not missing['passes_20_pct']


def fixture():
    dates=pd.date_range('2025-01-01',periods=45)
    daily=pd.DataFrame({'date':dates,'destination_country':'Synthetic','carrier':'One','sales_qty':10.})
    allocations=[]
    for origin in dates[30:33]:
        for h in range(1,8):
            allocations.append({'destination_country':'Synthetic','carrier':'One','window_days':7,
                'as_of_date':origin,'horizon_day':h,'forecast_qty':12.,'aggregate_total_qty':84.})
    top=pd.DataFrame([{'destination_country':'Synthetic','carrier':'One','window_days':7,
        **score([70]*3,[84]*3)}])
    return daily,pd.DataFrame(allocations),top


def test_comparison_reproduces_locked_score_and_enforces_same_origins():
    daily,forecasts,top=fixture()
    result=compare(daily,forecasts,top)
    assert len(result)==4 and result.n_expected.eq(3).all()
    assert result.loc[result.method.eq('MA7'),'mape_positive_pct'].iloc[0]==0
    assert result.loc[result.method.str.startswith('Đã chọn'),'mape_positive_pct'].iloc[0]==pytest.approx(20)
    with pytest.raises(ValueError):compare(daily,forecasts.iloc[:-1],top)
    with pytest.raises(ValueError):compare(pd.concat([daily,daily.iloc[[0]]]),forecasts,top)
    changed=top.copy();changed['mae']=100
    with pytest.raises(AssertionError):compare(daily,forecasts,changed)
