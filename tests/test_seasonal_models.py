import numpy as np
import pandas as pd
import pytest
from src.seasonal_models import positive_mape_action, distribution_forecast
from src.models import rolling_route


def test_kernel_mape_action_is_weighted_loss_minimizer():
    values=np.array([0.,1.,3.,10.]);weights=np.array([100.,1.,2.,3.])
    action=positive_mape_action(values,weights)
    loss=lambda f: np.sum(weights[1:]*np.abs(values[1:]-f)/values[1:])
    assert loss(action)==min(loss(f) for f in values[1:])


@pytest.mark.parametrize('model',['distribution_14_0','distribution_56_28'])
def test_distribution_origin_ignores_future_and_scores_tail_as_missing(model):
    dates=pd.date_range('2024-01-01',periods=600)
    series=pd.Series(5+np.sin(np.arange(600)/30),index=dates)
    altered=series.copy();altered.loc['2025-07-01':]=1e6
    cfg={'horizon':14,'refit_days':7}
    a,_=rolling_route(series,('Synthetic','Carrier'),model,'2025-07-01','2025-07-02',cfg)
    b,_=rolling_route(altered,('Synthetic','Carrier'),model,'2025-07-01','2025-07-02',cfg)
    np.testing.assert_array_equal(a.loc[a.as_of_date.eq('2025-06-30'),'forecast_qty'],
                                  b.loc[b.as_of_date.eq('2025-06-30'),'forecast_qty'])
    assert a.loc[a.target_date.gt('2025-07-02'),'actual_qty'].isna().all()


def test_zero_distribution_and_invalid_history():
    dates=pd.date_range('2024-01-01',periods=80)
    np.testing.assert_array_equal(distribution_forecast(pd.Series(0.,index=dates),'distribution_28_28',dates[-3:]),[0,0,0])
    with pytest.raises(ValueError):
        distribution_forecast(pd.Series(np.nan,index=dates),'distribution_28_28',dates[-3:])
