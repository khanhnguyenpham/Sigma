import json
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.common import sha256,seal_manifest,write_csv
from src.data import SOURCE_COLUMNS


@pytest.mark.parametrize('invalid_covariate',[False,True])
def test_independent_canonical_feature_check_preserves_quantity_privacy_and_existing_output(tmp_path,monkeypatch,capsys,cfg,order_rows,invalid_covariate):
    import src.common as common
    entrypoint=common.ROOT/'sigma/verification/data_check.py'
    if invalid_covariate:order_rows[0]['validity_days']='unknown'
    source=tmp_path/'synthetic.csv';pd.DataFrame(order_rows,columns=SOURCE_COLUMNS).to_csv(source,index=False)
    before=sha256(source);cfg['source']=source.name
    row=order_rows[0];folder=tmp_path/'outputs'/'fake_parent';folder.mkdir(parents=True)
    days=pd.date_range(cfg['observation_start'],cfg['observation_end'])
    daily=pd.DataFrame({'date':days,'destination_country':row['destination_country'],'carrier':row['carrier'],
                        'sales_qty':0.,'order_count':0.})
    daily.loc[daily.date.eq('2024-02-29'),['sales_qty','order_count']]=[3,1]
    top=pd.DataFrame({'destination_country':[row['destination_country']],'carrier':[row['carrier']],
                      'train_quantity':[3.],'rank':[1]})
    write_csv(folder/'daily_sales.csv',daily);write_csv(folder/'top_routes.csv',top)
    seal_manifest(folder,{'status':'complete','config':cfg,'source_sha256':before,'source_relative_path':source.name})
    monkeypatch.setattr(common,'ROOT',tmp_path)
    monkeypatch.setattr(sys,'argv',['check_data.py','--run-id','fake_parent','--output-id','quality'])
    runpy.run_path(str(entrypoint),run_name='__main__')
    feature=pd.read_csv(tmp_path/'outputs/quality/normalized_train_covariates.csv')
    assert feature.quantity.sum()==3 and len(feature)==1
    assert bool(feature.validity_days_valid.iloc[0]) is not invalid_covariate
    assert not {'customer_id','order_id'}&set(feature.columns)
    output=capsys.readouterr().out
    assert row['order_id'] not in output and row['customer_id'] not in output
    summary=tmp_path/'outputs/quality/summary.json';summary_hash=sha256(summary)
    with pytest.raises(FileExistsError):runpy.run_path(str(entrypoint),run_name='__main__')
    assert sha256(source)==before and sha256(summary)==summary_hash
