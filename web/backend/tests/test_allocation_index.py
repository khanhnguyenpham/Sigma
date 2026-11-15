import numpy as np
import pandas as pd
import pytest
from core.errors import DomainError
from modules.forecasting.allocation import allocate,index_prediction_totals


def fixture():
    return pd.DataFrame([dict(as_of_date=origin,destination_country=country,carrier='Carrier',block=block,forecast_qty=block*13.7)
        for origin in pd.date_range('2025-10-30',periods=2) for country in ['A','B'] for block in [2,1]])


def test_index_preserves_each_total_and_full_allocation_result():
    predictions=fixture();indexed=index_prediction_totals(predictions)
    history=pd.DataFrame({1:np.arange(1,92),2:np.arange(2,93)},index=pd.date_range('2025-08-02',periods=91))
    first_seen={1:'2025-01-01',2:'2025-01-01'}
    for key,totals in indexed.items():
        old=predictions.loc[predictions.as_of_date.eq(key[0])&predictions.destination_country.eq(key[1])&predictions.carrier.eq(key[2])].sort_values('block').forecast_qty.to_numpy()
        np.testing.assert_array_equal(totals,old)
        pd.testing.assert_frame_equal(allocate(history,first_seen,key[0],totals),allocate(history,first_seen,key[0],old))
        assert not totals.flags.writeable
    pd.testing.assert_frame_equal(predictions,fixture())


def test_duplicate_or_missing_forecast_block_fails_instead_of_overwriting():
    original=fixture()
    for malformed in [original.iloc[1:],pd.concat([original,original.iloc[[0]]])]:
        with pytest.raises(DomainError):index_prediction_totals(malformed)
