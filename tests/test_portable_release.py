import hashlib
import json

import pytest

from sigma.deployment.runtime import load
from sigma.deployment.portable import safe_columns


def fixture(tmp_path,columns='date,sales_qty',row='2026-01-01,3'):
    table=tmp_path/'daily.csv';table.write_text(columns+'\n'+row+'\n')
    meta={'kind':'sigma_verified_portable_v1','data_kind':'provided_order_snapshot',
        'raw_orders_included':False,'summary':{'project_fully_accepted':False},
        'verification':{},'protocol':{},'scenario_configs':[],
        'tables':{'daily':{'file':'daily.csv','columns':columns.split(','),'rows':1}},
        'files':{'daily.csv':hashlib.sha256(table.read_bytes()).hexdigest()}}
    (tmp_path/'manifest.json').write_text(json.dumps(meta));return meta


def test_source_result_loads_without_original_orders_and_future_remains_missing(tmp_path):
    fixture(tmp_path,row='2026-01-01,')
    frame=load(tmp_path)['daily']
    assert frame.date.dt.year.iloc[0]==2026 and frame.sales_qty.isna().all()


def test_changed_table_cannot_use_unchanged_manifest(tmp_path):
    fixture(tmp_path);(tmp_path/'daily.csv').write_text('date,sales_qty\n2026-01-01,99\n')
    with pytest.raises(ValueError,match='changed'):load(tmp_path)


def test_changed_manifest_is_rejected_by_approved_digest(tmp_path):
    fixture(tmp_path)
    with pytest.raises(ValueError,match='approved'):load(tmp_path,'0'*64)


def test_unsealed_path_cannot_escape_release(tmp_path):
    meta=fixture(tmp_path);meta['tables']['daily']['file']='../daily.csv'
    (tmp_path/'manifest.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError,match='sealed files'):load(tmp_path)


def test_identifiers_stay_forbidden_even_if_file_hash_matches(tmp_path):
    fixture(tmp_path,columns='customer_id,sales_qty',row='synthetic,3')
    with pytest.raises(ValueError,match='identifiers'):load(tmp_path)


def test_synthetic_source_cannot_be_relabelled_as_provided_snapshot(tmp_path):
    meta=fixture(tmp_path);meta['data_kind']='entirely_generated_synthetic'
    (tmp_path/'manifest.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError,match='provenance'):load(tmp_path)


def test_export_drops_private_columns_but_rejects_explicit_selection():
    import pandas as pd
    frame=pd.DataFrame({'order_id':['synthetic'],'sales_qty':[3]})
    assert list(safe_columns(frame,['sales_qty']))==['sales_qty']
    with pytest.raises(ValueError,match='identifiers'):safe_columns(frame,['order_id'])
