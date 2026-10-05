"""Independent source-to-daily check; private derived features, never edits raw."""
from pathlib import Path
import numpy as np
import pandas as pd
from src.common import ROOT,sha256,write_csv,write_json,validate_run,ROUTE
import argparse

parser=argparse.ArgumentParser(description='Independent local normalization/quantity/feature audit; no model tuning or upload')
parser.add_argument('--run-id',required=True)
parser.add_argument('--output-id',required=True)
args=parser.parse_args()
parent=(ROOT/'outputs'/args.run_id).resolve()
out=(ROOT/'outputs'/args.output_id).resolve()
if parent.parent!=(ROOT/'outputs').resolve() or out.parent!=(ROOT/'outputs').resolve():raise ValueError('Invalid local output path')
manifest=validate_run(parent);cfg=manifest['config']
source=(ROOT/(manifest.get('source_relative_path') or cfg['source'])).resolve()
if not source.is_relative_to(ROOT):raise ValueError('Source path escapes project')
before=sha256(source)
if before!=manifest['source_sha256']:raise ValueError('Source hash differs from audited run')
out.mkdir(exist_ok=False)
raw=pd.read_csv(source,dtype=str,keep_default_na=False)
frame=raw.apply(lambda col:col.str.strip())
signatures=pd.util.hash_pandas_object(raw,index=False)
if signatures.groupby(frame.order_id).nunique().gt(1).any():raise ValueError('Conflicting duplicate orders prevent independent normalization')
removed=int(frame.order_id.duplicated().sum())
frame=frame.loc[~frame.order_id.duplicated()].copy()
timestamps=pd.to_datetime(frame.order_datetime,format='mixed',utc=True,errors='coerce')
assert timestamps.notna().all()
frame['date']=timestamps.dt.tz_convert(None).dt.normalize()
frame['quantity']=pd.to_numeric(frame.quantity,errors='coerce')
assert frame.quantity.notna().all() and frame.quantity.ge(1).all() and frame.quantity.eq(np.floor(frame.quantity)).all()
frame['quantity']=frame.quantity.astype('int64')
covariates={}
for col in ['validity_days','data_gb','unit_price_vnd','unit_cost_vnd','gross_revenue_vnd']:
 values=pd.to_numeric(frame[col],errors='coerce')
 valid=np.isfinite(values)&values.ge(0)
 if col=='validity_days':valid&=values.ge(1)&values.eq(np.floor(values))
 frame[col]=values.where(valid)
 frame[col+'_valid']=valid
 covariates[col]={'invalid_rows':int((~valid).sum()),'dtype':str(frame[col].dtype)}
money_mismatch=frame.gross_revenue_vnd.ne(frame.quantity*frame.unit_price_vnd)
frame['revenue_consistent']=~money_mismatch & frame.gross_revenue_vnd_valid & frame.unit_price_vnd_valid
sales=frame.loc[frame.order_status.isin(cfg['sales_statuses'])].copy()
groups=sales.groupby(['date']+ROUTE)
source_daily=groups.quantity.sum().rename('sales_qty')
counts=groups.order_id.nunique().rename('order_count')
existing=pd.read_csv(parent/'daily_sales.csv',parse_dates=['date']).set_index(['date']+ROUTE)
expected=source_daily.reindex(existing.index,fill_value=0)
np.testing.assert_array_equal(existing.sales_qty,expected)
np.testing.assert_array_equal(existing.order_count,counts.reindex(existing.index,fill_value=0))
train=sales.loc[sales.date.le(cfg['train_end'])]
rank=train.groupby(ROUTE).quantity.sum().rename('train_quantity').reset_index()
rank=rank.sort_values(['train_quantity']+ROUTE,ascending=[False,True,True],kind='stable').head(cfg['top_n']).reset_index(drop=True)
rank['rank']=np.arange(1,len(rank)+1)
pd.testing.assert_frame_equal(rank,pd.read_csv(parent/'top_routes.csv'),check_dtype=False)
cols=['date']+ROUTE+['sku','product_type','plan_type','quantity','data_gb','validity_days',
                   'unit_price_vnd','unit_cost_vnd','gross_revenue_vnd','sales_channel','customer_type']+[col+'_valid' for col in ['validity_days','data_gb','unit_price_vnd','unit_cost_vnd','gross_revenue_vnd']]+['revenue_consistent']
write_csv(out/'normalized_train_covariates.csv',train[cols])
write_csv(out/'independent_daily_sales.csv',existing.reset_index()[['date']+ROUTE+['sales_qty','order_count']])
train_daily=existing.reset_index();train_daily=train_daily.loc[train_daily.date.le(cfg['train_end'])]
variability=train_daily.groupby(ROUTE).agg(mean_sales_qty=('sales_qty','mean'),std_sales_qty=('sales_qty','std'),
    mean_order_count=('order_count','mean'),variance_order_count=('order_count','var'))
variability['quantity_cv']=variability.std_sales_qty/variability.mean_sales_qty
variability['count_dispersion_ratio']=variability.variance_order_count/variability.mean_order_count
write_csv(out/'train_variability.csv',variability.reset_index())
assert before==sha256(source)
summary={'source_sha256':before,'parent_manifest_sha256':sha256(parent/'manifest.json'),'raw_unchanged':True,
 'independent_source_daily_quantity_and_count_match':True,'train_top10_match':True,'rows_raw':len(raw),
 'duplicate_rows_removed':removed,'tool_sha256':sha256(Path(__file__)),'sales_rows':len(sales),'sales_quantity':int(sales.quantity.sum()),'train_rows':len(train),'covariate_audit':covariates,
 'canonical_rules':'UTC dates, int64 quantity, numeric covariates with explicit invalid flags; route/item labels preserved',
 'no_target_smoothing_or_outlier_removal':True,'identifiers_in_derived_feature_csv':False,
 'feature_export_scope':'train only; private local; no external upload',
 'interpretation':'Variability is descriptive train evidence, not proof of universal forecast impossibility',
 'files':{path.name:sha256(path) for path in out.glob('*.csv')}}
write_json(out/'summary.json',summary);print({key:summary[key] for key in ['raw_unchanged','sales_rows','sales_quantity','train_rows','independent_source_daily_quantity_and_count_match','train_top10_match']})
