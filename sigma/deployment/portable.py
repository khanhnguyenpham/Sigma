"""Prepare a local review package; this command never uploads or publishes."""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, ITEM, sha256, write_json
from sigma.inventory.product30 import validate_product
from sigma.ui.product30_support import ledger_timeline, timeline_metrics

# This is intentionally separate from the synthetic-only public exporter.
TABLES = {
    'recommendations': ('recommendations_latest.csv', ITEM + ['SS','ROP','S','IP','Q','needs_replenishment','on_hand','as_of_date','partner_id','scenario_id','depletion_state','depletion_days','expected_depletion_date','eta','status','is_simulated','assumption_version','decision_applied_to_real_orders']),
    'item_forecast': ('item_forecast_latest.csv', ITEM + ['as_of_date','target_date','horizon_day','forecast_qty','is_simulated_allocation']),
    'metrics': ('simulation_metrics.csv', ['evaluation','scenario_id','demand','shortage','fill_rate','mean_closing_on_hand','is_simulated','tp','fp','fn','precision','recall','early_event_rate','late_alerts','mean_day_error','n_item_windows','existing_empty_excluded']),
    'alerts': ('alerts_14d.csv', ITEM + ['as_of_date','scenario_id','is_simulated','predicted_depletion_date','actual_depletion_date','predicted_days','actual_days','state','tp','fp','fn','already_empty','reported_early','late','day_error']),
    'delivery': ('delivery_projection.csv', ROUTE + ['delivery_date','known_commitment_qty','order_date','forecast_from_future_orders_qty','delivery_horizon_day','planned_delivery_qty','basis','as_of_date','customer_delivery_days','customer_delay_days','is_assumed_delivery','actual_delivered_qty']),
    'signals': ('business_signals.csv', ROUTE + ['date','sales_qty','order_count','gross_revenue_vnd','money_valid','actual_available','target_definition_version','quantity_prior28_mean','quantity_change_fraction','quantity_drop_observed','quantity_surge_observed','revenue_prior28_mean','revenue_change_fraction','revenue_drop_observed','revenue_surge_observed','observed_after_day_close']),
    'daily': ('daily_sales.csv', ROUTE + ['date','sales_qty','order_count','gross_revenue_vnd','money_valid','actual_available','target_definition_version']),
    'forecasts': ('daily_allocation.csv', ROUTE + ['window_days','as_of_date','target_date','horizon_day','model','forecast_qty','aggregate_total_qty','is_daily_allocation']),
    'top': ('top10_results.csv', ROUTE + ['window_days','split','model','cadence','mape_positive_pct','mae','wape_pct','bias','n_expected','n_labeled_pairs','n_scored_pairs','n_positive_pairs','n_zero_pairs','coverage','positive_share','unique_target_days','passes_20_pct']),
    'selections': ('selected_models.csv', ROUTE + ['window_days','model','selection_split','selection_cutoff','validation_mape_positive_pct','validation_mae']),
}
FORBIDDEN = {'order_id','customer_id','event_id','order_datetime','activation_datetime','email','phone','token'}
SOURCE_CODE = ['src/__init__.py','src/common.py','sigma/__init__.py','sigma/ui/__init__.py',
    'sigma/ui/product30_pages.py','sigma/ui/product30_charts.py','sigma/ui/product30_support.py',
    'sigma/ui/product30.css','sigma/analysis/__init__.py','sigma/analysis/alert_diagnostics.py',
    'sigma/deployment/__init__.py','sigma/deployment/runtime.py','sigma/deployment/app.py']


def safe_columns(frame, columns):
    if FORBIDDEN.intersection(columns):
        raise ValueError('Private identifiers cannot enter a portable package')
    return frame.loc[:,columns].copy()


def execute(destination, config='data/configs/product30-focus.json'):
    target=Path(destination).resolve()
    if not target.is_relative_to(ROOT/'outputs') or target.exists():
        raise ValueError('Choose a fresh local package directory inside outputs')
    settings=json.loads((ROOT/config).read_text(encoding='utf-8'))
    folder=ROOT/'outputs'/settings['product_run']
    summary=validate_product(folder)
    parent=ROOT/'outputs'/summary['aggregate_run']
    if settings['aggregate_run']!=summary['aggregate_run']:
        raise ValueError('Configured forecast parent differs')
    protocol=json.loads((folder/'protocol.json').read_text())
    if protocol['config'].get('demo_source_generated'):
        raise ValueError('This release requires the provided order snapshot, not a generated demo')
    source=(ROOT/protocol['config']['source']).resolve()
    if not source.is_relative_to(ROOT) or sha256(source)!=summary['source_sha256']:
        raise ValueError('Observed source differs from the verified results')
    receipts={}
    for run,base in [(summary['run_id'],folder),(summary['aggregate_run'],parent)]:
        receipt=json.loads((ROOT/'outputs'/(run+'_verification.json')).read_text())
        if receipt.get('status')!='verified' or receipt['summary_sha256']!=sha256(base/'summary.json'):
            raise ValueError('A matching independent verification receipt is required')
        receipts[run]={k:receipt[k] for k in ['status','summary_sha256','raw_rows','sales_quantity'] if k in receipt}
    timeline=ledger_timeline(folder/'inventory_ledger.csv')
    calculated=timeline_metrics(timeline)
    saved=pd.read_csv(folder/'simulation_metrics.csv',float_precision='round_trip')
    saved=saved.loc[saved.evaluation.eq('continuous_replenishment_policy')]
    joined=calculated.merge(saved,on='scenario_id',suffixes=('_new','_saved'),validate='one_to_one')
    if len(joined)!=summary['scenarios']:raise ValueError('Missing scenario reconciliation')
    for column in ['demand','shortage','fill_rate','mean_closing_on_hand']:
        np.testing.assert_allclose(joined[column+'_new'],joined[column+'_saved'],atol=1e-8,rtol=0)
    target.mkdir(parents=True); data=target/'release'; data.mkdir()
    tables={}
    for key,(name,columns) in TABLES.items():
        base=parent if key in ['daily','forecasts','top','selections'] else folder
        frame=pd.read_csv(base/name,float_precision='round_trip')
        frame=safe_columns(frame,columns)
        frame.to_csv(data/(key+'.csv'),index=False)
        tables[key]={'file':key+'.csv','columns':columns,'rows':len(frame)}
    timeline.to_csv(data/'timeline.csv',index=False)
    tables['timeline']={'file':'timeline.csv','columns':list(timeline.columns),'rows':len(timeline)}
    slim_summary={k:v for k,v in summary.items() if k!='files'}
    metadata={'kind':'sigma_verified_portable_v1','publication_performed':False,
        'data_kind':'provided_order_snapshot','contains_private_aggregates':True,
        'raw_orders_included':False,'order_customer_ids_included':False,
        'summary':slim_summary,'verification':receipts,
        'protocol':{'config':{'demo_source_generated':False}},
        'scenario_configs':json.loads((folder/'scenario_configs.json').read_text()),
        'tables':tables,'source_summary_sha256':sha256(folder/'summary.json'),
        'files':{p.name:sha256(p) for p in data.iterdir()}}
    write_json(data/'manifest.json',metadata)
    for name in SOURCE_CODE:
        output=target/name;output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,output)
    (target/'streamlit_app.py').write_text('from sigma.deployment.app import main\nmain()\n')
    (target/'requirements.txt').write_text('streamlit==1.65.0\npandas==3.0.6\nnumpy==2.5.3\naltair==6.3.0\n')
    (target/'.streamlit').mkdir()
    (target/'.streamlit/config.toml').write_text('[browser]\ngatherUsageStats = false\n[theme]\nprimaryColor = "#087f8c"\nbase = "light"\n')
    (target/'.gitignore').write_text('.venv/\n__pycache__/\n.streamlit/secrets.toml\n.env\n*.log\n')
    # CSV hashes must survive Git checkout on a different operating system.
    (target/'.gitattributes').write_text('release/** -text\n')
    write_json(target/'package-review.json',{'kind':metadata['kind'],'publication_performed':False,
        'contains_private_aggregates':True,'raw_orders_included':False,'manifest_sha256':sha256(data/'manifest.json'),
        'files':{p.relative_to(target).as_posix():sha256(p) for p in target.rglob('*') if p.is_file()}})
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',required=True)
    parser.add_argument('--config',default='data/configs/product30-focus.json')
    args=parser.parse_args();print(execute(args.destination,args.config))
