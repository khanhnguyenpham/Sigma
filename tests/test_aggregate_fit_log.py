import pandas as pd
import pytest

from sigma.verification.aggregate import read_fit_log


def test_mixed_midnight_formats_compare_as_dates_not_strings(tmp_path):
    path=tmp_path/'synthetic_log.csv'
    pd.DataFrame({'fit_cutoff':['2025-06-30 00:00:00','2025-07-07'],
        'max_label_end':['2025-06-30','2025-07-08 00:00:00']}).to_csv(path,index=False)
    result=read_fit_log(path)
    assert pd.api.types.is_datetime64_any_dtype(result.fit_cutoff)
    assert result.max_label_end.le(result.fit_cutoff).tolist()==[True,False]


def test_unparseable_fit_date_cannot_be_verified(tmp_path):
    path=tmp_path/'synthetic_log.csv'
    pd.DataFrame({'fit_cutoff':['not-a-date'],'max_label_end':['2025-01-01']}).to_csv(path,index=False)
    with pytest.raises(ValueError):read_fit_log(path)
