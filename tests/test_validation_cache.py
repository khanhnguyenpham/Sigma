import copy
import pandas as pd
import pytest
from src.common import seal_manifest, write_csv
from src.validation_cache import import_validation


def cache_fixture(tmp_path):
    source=tmp_path/'historical';source.mkdir()
    destination=tmp_path/'new';destination.mkdir()
    cfg={'config_version':'old','seed':42,'tuning':{'enabled':True}}
    daily=pd.DataFrame({'date':pd.to_datetime(['2024-01-01']),
        'destination_country':['Synthetic'],'carrier':['Carrier'],'sales_qty':[2]})
    top=daily[['destination_country','carrier']]
    write_csv(source/'daily_sales.csv',daily);write_csv(source/'top_routes.csv',top)
    write_csv(source/'validation_metrics.csv',pd.DataFrame({'split':['validation'],'model':['ma7']}))
    write_csv(source/'sarima_log.csv',pd.DataFrame(columns=['destination_country','carrier','model','status']))
    manifest={'status':'complete','config':cfg,'source_sha256':'synthetic-hash','code_sha256':'historical-code'}
    seal_manifest(source,manifest)
    return source,destination,cfg,daily,top,manifest


def test_historical_import_provenance_and_new_candidate_flags(tmp_path):
    source,dest,cfg,daily,top,_=cache_fixture(tmp_path)
    current=copy.deepcopy(cfg);current['config_version']='new';current['tuning']['context_enabled']=True
    metrics,failed,evidence=import_validation(source,dest,current,'synthetic-hash',daily,top)
    assert metrics.split.eq('validation').all() and not failed
    assert evidence['historical_code_sha256']=='historical-code'
    assert evidence['test_metrics_imported'] is False


def test_historical_import_rejects_changed_data_and_configuration(tmp_path):
    source,dest,cfg,daily,top,_=cache_fixture(tmp_path)
    with pytest.raises(ValueError,match='different source'):
        import_validation(source,dest,cfg,'different-hash',daily,top)
    changed=copy.deepcopy(cfg);changed['seed']=99
    with pytest.raises(ValueError,match='configuration differs'):
        import_validation(source,dest,changed,'synthetic-hash',daily,top)
    daily.sales_qty=999
    with pytest.raises(AssertionError):
        import_validation(source,dest,cfg,'synthetic-hash',daily,top)


def test_historical_import_rejects_test_metrics_even_if_sealed(tmp_path):
    source,dest,cfg,daily,top,manifest=cache_fixture(tmp_path)
    write_csv(source/'validation_metrics.csv',pd.DataFrame({'split':['test'],'model':['ma7']}))
    seal_manifest(source,manifest)
    with pytest.raises(ValueError,match='Only validation'):
        import_validation(source,dest,cfg,'synthetic-hash',daily,top)
