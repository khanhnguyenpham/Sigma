import pytest
import pandas as pd
from sigma.sharing.export import require_generated,table


def test_claiming_synthetic_is_not_enough_without_reproducible_hash():
    cfg={'demo_source_generated':True};generation={'kind':'entirely_generated_synthetic',
        'uses_private_orders':False,'source_sha256':'provided-source'}
    with pytest.raises(ValueError,match='not exactly reproducible'):
        require_generated(cfg,generation,'provided-source','freshly-generated-source')


def test_real_snapshot_cannot_be_exported():
    with pytest.raises(ValueError,match='generated demonstration'):
        require_generated({'demo_source_generated':False},{},'same','same')


def test_sensitive_fields_blocked_even_for_generated_data():
    with pytest.raises(ValueError,match='Private columns'):
        table(pd.DataFrame({'customer_id':['synthetic']}),['customer_id'])


def test_unknown_date_is_null_and_never_fake_zero():
    result=table(pd.DataFrame({'date':pd.to_datetime(['2026-01-01',None]),'quantity':[1.,None]}),['date','quantity'])
    assert result['rows']==[['2026-01-01',1.],[None,None]]
