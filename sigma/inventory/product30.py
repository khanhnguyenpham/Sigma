"""M3 product from a sealed aggregate forecast and explicit stock assumptions."""
from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, ITEM, sha256, write_csv, write_json
from src.data import audit_orders
from src.inventory import (initialize_partners, item_matrix, run_policy, replay_alerts,
    simulation_metrics, AllocationPlan, allocation, alert_opportunity_summary)
from src.transactions import prepare_transactions, EVENT_COLUMNS
from sigma.forecasting.aggregate import validate_aggregate
from sigma.inventory.policy import scenarios
from sigma.delivery.customer import commitments, projection


def business_signals(sales, daily):
    """Retrospective observations; today's shock is never a forecast feature."""
    # Reuse the audited daily money-validity contract: invalid money stays
    # missing and must not turn into an apparent zero-revenue shock.
    frame=daily.copy()
    frame=frame.sort_values(ROUTE+['date'])
    for col,label in [('sales_qty','quantity'),('gross_revenue_vnd','revenue')]:
        prior=frame.groupby(ROUTE)[col].transform(lambda y:y.shift(1).rolling(28,min_periods=14).mean())
        frame[label+'_prior28_mean']=prior
        change=frame[col].div(prior.where(prior.gt(0)))-1
        frame[label+'_change_fraction']=change
        frame[label+'_drop_observed']=change.le(-.5)
        frame[label+'_surge_observed']=change.ge(1.)
    frame['observed_after_day_close']=True
    return frame


def validate_product(folder, check_parent=True):
    folder=Path(folder).resolve()
    info=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    if info.get('kind')!='m3_30day_product' or info.get('status')!='complete':
        raise ValueError('Not a complete M3 product')
    required={'protocol.json','effective_config.json','recommendations_latest.csv','inventory_ledger.csv',
        'inventory_events.csv','alerts_14d.csv','simulation_metrics.csv','delivery_projection.csv','business_signals.csv'}
    if not required.issubset(info['files']): raise ValueError('Missing M3 evidence')
    for name,digest in info['files'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha256(path)!=digest:
            raise ValueError('Missing or changed M3 artifact')
    if check_parent:
        parent=(ROOT/'outputs'/info['aggregate_run']).resolve()
        validate_aggregate(parent)
        if sha256(parent/'summary.json')!=info['aggregate_summary_sha256']: raise ValueError('Different forecast parent')
    return info


def execute(run_id, aggregate_run, window=30):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [run_id,aggregate_run]):
        raise ValueError('Invalid run ID')
    parent=ROOT/'outputs'/aggregate_run; aggregate=validate_aggregate(parent)
    protocol=json.loads((parent/'protocol.json').read_text(encoding='utf-8'))
    cfg=copy.deepcopy(protocol['config']); source=ROOT/cfg['source']
    if window not in protocol['settings']['windows'] or window<14: raise ValueError('M3 requires a registered forecast of at least 14 days')
    if sha256(source)!=aggregate['source_sha256']: raise ValueError('M3 source differs from forecast')
    sales,audit=audit_orders(source,cfg);cfg=initialize_partners(sales,cfg)
    cfg['horizon']=window
    cfg['assumption_version']='A08-A17-aggregate30-m3-v1'
    daily=pd.read_csv(parent/'daily_sales.csv',parse_dates=['date'])
    forecast=pd.read_csv(parent/'daily_allocation.csv',parse_dates=['as_of_date','target_date'],float_precision='round_trip')
    forecast=forecast.loc[forecast.window_days.eq(window)].copy()
    if not np.isfinite(forecast.forecast_qty).all() or forecast.forecast_qty.lt(0).any(): raise ValueError('Invalid policy forecast')
    if forecast.duplicated(ROUTE+['as_of_date','horizon_day']).any(): raise ValueError('Duplicate policy forecast')
    out=ROOT/'outputs'/run_id;out.mkdir(exist_ok=False)
    core=['sigma/inventory/product30.py','src/inventory.py','src/transactions.py','sigma/delivery/customer.py']
    meta={'registered_at_utc':datetime.now(timezone.utc).isoformat(),'aggregate_run':aggregate_run,
        'aggregate_summary_sha256':sha256(parent/'summary.json'),'source_sha256':sha256(source),
        'config':cfg,'implementation_modules_sha256':{f:sha256(ROOT/f) for f in core},
        'forecast_window_days':window,'alert_primary_replay_days':14,
        'stock_kind':'simulated','supplier_lead_time_kind':'assumed_per_partner',
        'customer_delivery_days':7,'stock_debit':'order reservation once, no second debit at customer delivery',
        'decision_applied_to_real_orders':False,'test_independent':False,'project_fully_accepted':False}
    write_json(out/'protocol.json',meta);write_json(out/'effective_config.json',cfg)
    try:
        matrix=item_matrix(sales,cfg); plan=AllocationPlan(matrix,forecast,cfg)
        transactions=prepare_transactions(sales,cfg)
        # Keep original R07 14-day replay windows and denominator; longer view is separate.
        alert_cfg={**cfg,'horizon':14}
        alert_forecast=forecast.loc[forecast.horizon_day.le(14)]
        alerts=replay_alerts(matrix,alert_forecast,alert_cfg)
        alerts30=replay_alerts(matrix,forecast,cfg)
        write_csv(out/'alerts_14d.csv',alerts);write_csv(out/'alerts_30d.csv',alerts30)
        write_json(out/'alert_opportunity.json',alert_opportunity_summary(alerts))
        print('Independent H14 and H30 alert replays ready; starting continuous policy',flush=True)
        variants=scenarios(cfg);metrics=[];latest=[];issues=[];configs=[];ledger_rows=0;rec_rows=0
        with (out/'inventory_events.csv.tmp').open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=EVENT_COLUMNS);writer.writeheader()
            for index,(scenario_cfg,stress) in enumerate(variants):
                ledger,recs,issue=run_policy(matrix,forecast,scenario_cfg,stress,
                    lambda msg:print(msg,flush=True),transactions=transactions,event_writer=writer,allocation_plan=plan)
                mode='w' if index==0 else 'a'
                ledger.to_csv(out/'inventory_ledger.csv.tmp',mode=mode,header=index==0,index=False)
                recs.to_csv(out/'inventory_recommendations.csv.tmp',mode=mode,header=index==0,index=False)
                current=simulation_metrics(ledger,alerts)
                metrics.append(current.loc[current.evaluation.eq('continuous_replenishment_policy')])
                latest.append(recs.loc[recs.as_of_date.eq(pd.Timestamp(cfg['forecast_origin']))])
                issues.append(issue);configs.append({'scenario':stress,'inventory':scenario_cfg['inventory']})
                ledger_rows+=len(ledger);rec_rows+=len(recs)
        for name in ['inventory_events','inventory_ledger','inventory_recommendations']:
            (out/f'{name}.csv.tmp').replace(out/f'{name}.csv')
        replay=simulation_metrics(ledger,alerts).loc[lambda x:x.evaluation.ne('continuous_replenishment_policy')]
        all_metrics=pd.concat(metrics+[replay],ignore_index=True)
        write_csv(out/'simulation_metrics.csv',all_metrics)
        recs_latest=pd.concat(latest,ignore_index=True)
        recs_latest['decision_applied_to_real_orders']=False
        write_csv(out/'recommendations_latest.csv',recs_latest)
        nonempty=[p for p in issues if len(p)]
        write_csv(out/'allocation_issues.csv',pd.concat(nonempty,ignore_index=True) if nonempty else
                  pd.DataFrame(columns=ROUTE+['as_of_date','scenario_id','status']))
        write_json(out/'scenario_configs.json',configs)
        latest_forecast=forecast.loc[forecast.as_of_date.eq(pd.Timestamp(cfg['forecast_origin']))]
        details,errors=allocation(matrix,latest_forecast,cfg['forecast_origin'],cfg)
        if errors: raise ValueError('Latest item allocation has no basis')
        item_rows=[]
        for key,vector in details.items():
            item_rows.extend([{**dict(zip(ITEM,key)),'as_of_date':cfg['forecast_origin'],
                'target_date':pd.Timestamp(cfg['forecast_origin'])+pd.Timedelta(days=h),
                'horizon_day':h,'forecast_qty':float(q),'is_simulated_allocation':True}
                for h,q in enumerate(vector,1)])
        write_csv(out/'item_forecast_latest.csv',pd.DataFrame(item_rows))
        delivery=projection(sales,latest_forecast,cfg['forecast_origin'],horizon=window)
        write_csv(out/'delivery_projection.csv',delivery)
        write_csv(out/'business_signals.csv',business_signals(sales,daily))
        validate_aggregate(parent)
        if sha256(source)!=meta['source_sha256'] or any(sha256(ROOT/f)!=v for f,v in meta['implementation_modules_sha256'].items()):
            raise ValueError('Source or M3 implementation changed during run')
        summary={'kind':'m3_30day_product','status':'complete','run_id':run_id,'aggregate_run':aggregate_run,
            'aggregate_summary_sha256':meta['aggregate_summary_sha256'],'source_sha256':meta['source_sha256'],
            'as_of_date':cfg['forecast_origin'],'forecast_window_days':window,'scenarios':len(variants),
            'ledger_rows':ledger_rows,'recommendation_rows':rec_rows,'items_per_scenario':int(recs_latest.groupby('scenario_id').size().min()),
            'alert_replay_windows':len(alerts),'early_event_rate':float(replay.early_event_rate.iloc[0]),
            'base_fill_rate':float(all_metrics.loc[all_metrics.scenario_id.eq('base'),'fill_rate'].iloc[0]),
            'project_fully_accepted':False,'actual_inventory_provided':False,
            'finished_at_utc':datetime.now(timezone.utc).isoformat(),
            'files':{p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()}}
        write_json(out/'summary.json',summary)
        print(json.dumps({k:v for k,v in summary.items() if k!='files'}),flush=True)
        return summary
    except BaseException as error:
        write_json(out/'failed.json',{'status':'failed','error_type':type(error).__name__});raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--aggregate-run',required=True);parser.add_argument('--window',type=int,default=30)
    args=parser.parse_args();execute(args.run_id,args.aggregate_run,args.window)
