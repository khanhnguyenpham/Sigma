"""Export only a freshly reproducible synthetic M3 bundle for browser sharing."""
import argparse
import json
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, ITEM, sha256, write_json
from sigma.inventory.product30 import validate_product
from sigma.ui.product30_support import ledger_timeline, timeline_metrics
from sigma.sharing.demo import generated_source

FORBIDDEN={'order_id','customer_id','order_datetime','activation_datetime','email','phone','token','source'}


def table(frame,columns):
    if FORBIDDEN.intersection(columns):raise ValueError('Private columns are forbidden in the public bundle')
    result=frame[columns].copy()
    for col in result:
        if pd.api.types.is_datetime64_any_dtype(result[col]):result[col]=result[col].dt.strftime('%Y-%m-%d')
        elif col.endswith('_date') or col in ['date','eta']:
            result[col]=result[col].map(lambda x:str(x)[:10] if pd.notna(x) else None)
    return {'columns':columns,'rows':json.loads(result.to_json(orient='values',double_precision=15,date_format='iso'))}


def require_generated(config,generation,actual_hash,reproduced_hash):
    if not config.get('demo_source_generated') or generation.get('kind')!='entirely_generated_synthetic':
        raise ValueError('Public export accepts generated demonstration data only')
    if generation.get('uses_private_orders') is not False:
        raise ValueError('Private-source provenance cannot be published')
    if not (actual_hash==generation.get('source_sha256')==reproduced_hash):
        raise ValueError('Source is not exactly reproducible from the synthetic generator')


def execute(config,destination):
    path=(ROOT/config).resolve();settings=json.loads(path.read_text())
    folder=ROOT/'outputs'/settings['product_run'];summary=validate_product(folder)
    protocol=json.loads((folder/'protocol.json').read_text())
    cfg=protocol['config'];source=(ROOT/cfg['source']).resolve()
    if not source.is_relative_to(ROOT/'outputs') or source.name!='synthetic_orders.csv':
        raise ValueError('Export source must be inside a generated demo bundle')
    generation=json.loads((source.parent/'generation.json').read_text())
    # Independently regenerate before inspecting or exporting any source-derived table.
    with tempfile.TemporaryDirectory(prefix='share-proof-',dir=ROOT/'.cache') as scratch:
        reproduced=generated_source(Path(scratch)/'synthetic_orders.csv',cfg)
        require_generated(cfg,generation,sha256(source),sha256(reproduced))
    parent=ROOT/'outputs'/summary['aggregate_run']
    for name,location in [(summary['run_id'],folder),(summary['aggregate_run'],parent)]:
        receipt=json.loads((ROOT/'outputs'/(name+'_verification.json')).read_text())
        if receipt.get('status')!='verified' or receipt['summary_sha256']!=sha256(location/'summary.json'):
            raise ValueError('Synthetic bundle needs matching independent verification')
    read=lambda name:pd.read_csv(folder/name,float_precision='round_trip')
    daily=pd.read_csv(parent/'daily_sales.csv',parse_dates=['date'],float_precision='round_trip')
    forecast=pd.read_csv(parent/'daily_allocation.csv',parse_dates=['as_of_date','target_date'],float_precision='round_trip')
    origins=['2025-09-30','2025-10-31','2025-11-30',cfg['forecast_origin']]
    forecast=forecast.loc[forecast.as_of_date.isin(pd.to_datetime(origins))]
    timeline=ledger_timeline(folder/'inventory_ledger.csv')
    metrics=read('simulation_metrics.csv')
    derived=timeline_metrics(timeline)
    saved=metrics.loc[metrics.evaluation.eq('continuous_replenishment_policy')]
    checked=derived.merge(saved,on='scenario_id',suffixes=('_derived','_saved'),validate='one_to_one')
    for name in ['demand','shortage']:np.testing.assert_array_equal(checked[name+'_derived'],checked[name+'_saved'])
    for name in ['fill_rate','mean_closing_on_hand']:np.testing.assert_allclose(checked[name+'_derived'],checked[name+'_saved'],atol=1e-8,rtol=0)
    rec=read('recommendations_latest.csv')
    top=pd.read_csv(parent/'top10_results.csv')
    alerts=read('alerts_14d.csv')
    dates=['predicted_depletion_date','actual_depletion_date']
    payload={'meta':{'title':'SIGMA · Bản trình diễn M3','data_kind':'entirely_generated_synthetic',
        'uses_private_orders':False,'not_business_acceptance':True,'seed':cfg['seed'],
        'as_of_date':cfg['forecast_origin'],'origins':origins,'windows':[7,30],
        'route_count':len(daily[ROUTE].drop_duplicates()),'item_count':len(rec.loc[rec.scenario_id.eq('base')]),
        'customer_delivery_days':7,'model_selection':'validation then locked before retrospective test',
        'verification':'synthetic source regenerated exactly; forecast and policy independently checked',
        'forecast_summary_sha256':sha256(parent/'summary.json'),'policy_summary_sha256':sha256(folder/'summary.json')},
      'scenarios':[{'id':x['scenario']['name'],**{k:v for k,v in x['scenario'].items() if k!='name'}} for x in json.loads((folder/'scenario_configs.json').read_text())],
      'tables':{
        'daily':table(daily,ROUTE+['date','sales_qty','gross_revenue_vnd']),
        'forecasts':table(forecast,ROUTE+['window_days','as_of_date','target_date','forecast_qty']),
        'top':table(top,ROUTE+['window_days','model','mape_positive_pct','mae','wape_pct','bias','coverage','passes_20_pct','n_expected']),
        'stock':table(rec,ITEM+['scenario_id','on_hand','SS','ROP','S','IP','Q','eta','expected_depletion_date','depletion_state','needs_replenishment']),
        'timeline':table(timeline,ROUTE+['date','scenario_id','scenario_demand','fulfilled','shortage','closing']),
        'alerts':table(alerts,ITEM+['as_of_date']+dates+['predicted_days','actual_days','tp','fp','fn','already_empty','reported_early','late']),
        'items':table(read('item_forecast_latest.csv'),ITEM+['target_date','forecast_qty']),
        'delivery':table(read('delivery_projection.csv'),ROUTE+['delivery_date','known_commitment_qty','forecast_from_future_orders_qty'])}}
    target=Path(destination).resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Review payload must remain in workspace')
    target.parent.mkdir(parents=True,exist_ok=True)
    # Keep the portable browser payload small without changing any table values.
    target.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    audit={'status':'prepared_synthetic_only','destination':target.relative_to(ROOT).as_posix(),
        'sha256':sha256(target),'bytes':target.stat().st_size,'synthetic_regeneration_exact':True,
        'table_rows':{k:len(v['rows']) for k,v in payload['tables'].items()},'private_orders_included':False,
        'hosting_publication_performed':False}
    write_json(ROOT/'.tools/share_20261018/payload_audit.json',audit)
    print(json.dumps(audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--destination',required=True)
    args=parser.parse_args();execute(args.config,args.destination)
