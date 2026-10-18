"""Registered focused total-demand research; validation lock precedes test.

The focus route is explicitly chosen after prior test inspection. New test
results are retrospective, never described as an independent holdout.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from src.common import ROOT, ROUTE, sha256, write_csv, write_json
from sigma.forecasting.aggregate import (validate_aggregate, metric_table, select,
    allocate_days, model_job, origins_for, row)
from sigma.verification.aggregate import read_predictions
from sigma.experiments.aggregate_recent import check_run_id


def specifications(options):
    specs={}
    for other in options['ensemble_components']:
        for weight in options['ensemble_weights']:
            if not 0<weight<1:raise ValueError('Invalid convex weight')
            specs[f'mix_{other}_w{int(weight*100)}']={'kind':'mixture','other':other,'weight':weight}
    for harmonics in options['annual_harmonics']:
        for label in ['daily_sum','end_total']:
            for alpha in options['ridge_alphas']:
                for transform in ['raw','log_smear']:
                    if harmonics<1 or alpha<=0:raise ValueError('Invalid harmonic settings')
                    name=f'harmonic{harmonics}_{label}_a{alpha}_{transform}'
                    specs[name]={'kind':'harmonic','harmonics':harmonics,'label':label,
                        'alpha':alpha,'transform':transform,'training_days':options['training_days']}
    return specs


def calendar_features(dates, harmonics):
    dates=pd.DatetimeIndex(dates)
    # Fixed epoch/period, shared by fit and prediction, including leap years.
    phase=(dates-pd.Timestamp('2024-01-01')).days.to_numpy()/365.25*2*np.pi
    return np.column_stack([f(k*phase) for k in range(1,harmonics+1) for f in [np.sin,np.cos]]+
        [(dates.dayofweek==d).astype(float) for d in range(6)])


def fit_harmonic(y,cutoff,window,spec):
    y=y.loc[:pd.Timestamp(cutoff)].astype(float)
    labels=y if spec['label']=='daily_sum' else y.rolling(window,min_periods=window).sum()
    labels=labels.dropna().loc[pd.Timestamp(cutoff)-pd.Timedelta(days=spec['training_days']-1):]
    if len(labels)<90 or not np.isfinite(labels).all() or labels.lt(0).any():
        raise ValueError('Invalid causal harmonic history')
    x=calendar_features(labels.index,spec['harmonics'])
    target=np.log1p(labels.to_numpy()) if spec['transform']=='log_smear' else labels.to_numpy()
    model=Ridge(alpha=spec['alpha']).fit(x,target)
    smear=float(np.exp(target-model.predict(x)).mean()) if spec['transform']=='log_smear' else 1.
    return (model,smear),{'fit_cutoff':pd.Timestamp(cutoff),'max_label_end':labels.index.max(),'training_pairs':len(labels)}


def predict_harmonic(state,origin,window,spec):
    dates=pd.date_range(pd.Timestamp(origin)+pd.Timedelta(days=1),periods=window)
    if spec['label']=='end_total':dates=dates[-1:]
    model,smear=state
    values=model.predict(calendar_features(dates,spec['harmonics']))
    if spec['transform']=='log_smear':values=np.exp(values)*smear-1
    values=np.maximum(values,0)
    if not np.isfinite(values).all():raise ValueError('Invalid harmonic prediction')
    return float(values.sum())


def harmonic_frame(daily,route,cfg,settings,window,name,spec,split):
    group=daily.loc[(daily[ROUTE]==pd.Series(route,index=ROUTE)).all(axis=1)].set_index('date').sort_index()
    origins=origins_for(cfg,split)
    phase_end=pd.Timestamp(cfg['forecast_origin'] if split=='future' else cfg[f'{split}_end'])
    records=[];logs=[]
    for i,origin in enumerate(origins):
        if i%settings['refit_days']==0:
            state,info=fit_harmonic(group.sales_qty,origin,window,spec)
            cutoff=origin
            logs.append(dict(zip(ROUTE,route))|{'model':name,'window_days':window,'split':split,'status':'ok',**info})
        records.append(row(group,route,name,split,origin,window,predict_harmonic(state,origin,window,spec),phase_end,cutoff))
    return pd.DataFrame(records),pd.DataFrame(logs)


def blend(base,other,weight,name):
    keys=['window_days','split']+ROUTE+['as_of_date','window_start','target_date']
    if not 0<weight<1:raise ValueError('Invalid convex weight')
    merged=base.merge(other,on=keys,how='outer',suffixes=('_base','_other'),validate='one_to_one',indicator=True)
    if not merged._merge.eq('both').all():raise ValueError('Incomplete ensemble component')
    for col in ['actual_qty']:
        np.testing.assert_allclose(merged[col+'_base'],merged[col+'_other'],rtol=0,atol=0,equal_nan=True)
    values=merged[['forecast_qty_base','forecast_qty_other']].to_numpy()
    if not np.isfinite(values).all() or (values<0).any():raise ValueError('Invalid ensemble component')
    result=merged[keys].copy()
    result['model']=name
    result['forecast_qty']=(1-weight)*merged.forecast_qty_base+weight*merged.forecast_qty_other
    result['actual_qty']=merged.actual_qty_base
    result['fit_cutoff']=merged[['fit_cutoff_base','fit_cutoff_other']].max(axis=1)
    if result.fit_cutoff.gt(result.as_of_date).any():raise ValueError('Future component cutoff')
    return result


def focused(frame,options):
    route=options['route']
    return frame.window_days.eq(options['window_days']) & frame.destination_country.eq(route[0]) & frame.carrier.eq(route[1])


def check_sources(out):
    protocol=json.loads((out/'protocol.json').read_text())
    parent=ROOT/'outputs'/protocol['parent_run']
    validate_aggregate(parent)
    if sha256(parent/'summary.json')!=protocol['parent_summary_sha256']:raise ValueError('Changed parent')
    if sha256(ROOT/protocol['research_config_path'])!=protocol['config_sha256']:raise ValueError('Changed research config')
    if sha256(ROOT/protocol['config']['source'])!=protocol['source_sha256']:raise ValueError('Changed source')
    for name,digest in protocol['implementation_modules_sha256'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Changed implementation')
    return protocol,parent


def validation(run_id,config):
    check_run_id(run_id)
    options=json.loads((ROOT/config).read_text())
    specs=specifications(options)
    parent=ROOT/'outputs'/options['parent_run'];validate_aggregate(parent)
    original=json.loads((parent/'protocol.json').read_text())
    out=ROOT/'outputs'/run_id;out.mkdir(exist_ok=False)
    protocol={**original,'registered_at_utc':datetime.now(timezone.utc).isoformat(),
        'packages':{**original['packages'],'scikit-learn':importlib.metadata.version('scikit-learn')},
        'parent_run':options['parent_run'],'parent_summary_sha256':sha256(parent/'summary.json'),
        'research_config_path':config,'config_sha256':sha256(ROOT/config),'focus_options':options,
        'focus_specifications':specs,'implementation_modules_sha256':{**original['implementation_modules_sha256'],
            'sigma/experiments/aggregate_focus.py':sha256(__file__)}}
    write_json(out/'protocol.json',protocol) # Before reading validation labels or fitting.
    for name in ['daily_sales.csv','top_routes.csv']:(out/name).write_bytes((parent/name).read_bytes())
    cfg,settings=protocol['config'],protocol['settings']
    daily=pd.read_csv(parent/'daily_sales.csv',parse_dates=['date'],float_precision='round_trip')
    choices=pd.read_csv(parent/'selected_models.csv')
    all_val=read_predictions(parent/'validation_predictions.csv')
    controls=all_val.merge(choices[['window_days']+ROUTE+['model']],on=['window_days']+ROUTE+['model'],validate='many_to_one')
    base=controls.loc[focused(controls,options)]
    if base.empty or base.model.nunique()!=1:raise ValueError('Ambiguous focus champion')
    frames=[controls];logs=[]
    for name,spec in specs.items():
        if spec['kind']=='mixture':
            other=all_val.loc[focused(all_val,options)&all_val.model.eq(spec['other'])]
            frame=blend(base,other,spec['weight'],name)
        else:
            frame,log=harmonic_frame(daily,options['route'],cfg,settings,options['window_days'],name,spec,'validation')
            logs.append(log)
        frames.append(frame)
    predictions=pd.concat(frames,ignore_index=True)
    selected=select(predictions,cfg)
    # All other route/window choices must remain byte-equivalent in value.
    pd.testing.assert_frame_equal(selected.loc[~focused(selected,options)].reset_index(drop=True),
        choices.loc[~focused(choices,options)].reset_index(drop=True),check_exact=False,rtol=0,atol=1e-10)
    write_csv(out/'validation_predictions.csv',predictions)
    write_csv(out/'validation_metrics.csv',metric_table(predictions,cfg))
    write_csv(out/'selected_models.csv',selected)
    write_csv(out/'new_fit_log.csv',pd.concat(logs,ignore_index=True))
    write_json(out/'selection_lock.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'selection_sha256':sha256(out/'selected_models.csv'),'test_used_for_ranking':False,
        'basis':'focused validation positive MAPE, MAE, lexical model; all other champions fixed'})
    check_sources(out)
    result={'status':'validation_locked','registered_candidates':len(specs),'test_evaluated':False,
        'focus_selection':selected.loc[focused(selected,options)].to_dict('records')}
    write_json(out/'validation_summary.json',result);print(json.dumps(result),flush=True)
    return result


def test(run_id):
    check_run_id(run_id);out=ROOT/'outputs'/run_id
    if (out/'test_started.json').exists() or (out/'summary.json').exists():raise FileExistsError('Test cannot be repeated')
    protocol,parent=check_sources(out);cfg,settings=protocol['config'],protocol['settings'];options=protocol['focus_options']
    selected=pd.read_csv(out/'selected_models.csv');lock=json.loads((out/'selection_lock.json').read_text())
    if lock['test_used_for_ranking'] or sha256(out/'selected_models.csv')!=lock['selection_sha256']:raise ValueError('Changed selection')
    chosen=selected.loc[focused(selected,options)].iloc[0].model
    spec=protocol['focus_specifications'].get(chosen)
    write_json(out/'test_started.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),'selection_sha256':lock['selection_sha256']})
    daily=pd.read_csv(out/'daily_sales.csv',parse_dates=['date'],float_precision='round_trip')
    top=list(pd.read_csv(out/'top_routes.csv')[ROUTE].itertuples(index=False,name=None))
    logs=[pd.read_csv(parent/'fit_log.csv'),pd.read_csv(out/'new_fit_log.csv')];outputs=[]
    for split in ['test','future']:
        for window in settings['windows']:
            write_json(out/f'{split}_{window}d_execution.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),
                'selection_sha256':lock['selection_sha256']})
        frame=read_predictions(parent/f'{split}_predictions.csv')
        if spec is not None:
            base=frame.loc[focused(frame,options)]
            if spec['kind']=='mixture':
                other,log=model_job(daily,top,cfg,settings,options['window_days'],spec['other'],split,[options['route']])
                logs.append(log);replacement=blend(base,other,spec['weight'],chosen)
            else:
                replacement,log=harmonic_frame(daily,options['route'],cfg,settings,options['window_days'],chosen,spec,split)
                logs.append(log)
            frame=pd.concat([frame.loc[~focused(frame,options)],replacement],ignore_index=True)
        write_csv(out/f'{split}_predictions.csv',frame);outputs.append(frame)
    metrics=metric_table(outputs[0],cfg);write_csv(out/'test_metrics.csv',metrics)
    write_csv(out/'fit_log.csv',pd.concat(logs,ignore_index=True))
    write_csv(out/'daily_allocation.csv',allocate_days(pd.concat(outputs,ignore_index=True),daily))
    primary=metrics.merge(pd.read_csv(out/'top_routes.csv')[ROUTE],on=ROUTE,validate='many_to_one').loc[lambda x:x.cadence.eq('daily_origins')]
    write_csv(out/'top10_results.csv',primary);check_sources(out)
    result=[{'window_days':int(h),'routes_below_20_pct':int(p.passes_20_pct.sum()),
        'mean_mape_positive_pct':float(p.mape_positive_pct.mean()),'minimum_coverage':float(p.coverage.min()),
        'pairs_per_route':int(p.n_expected.iloc[0])} for h,p in primary.groupby('window_days')]
    summary={'kind':'consecutive_day_aggregate','status':'complete','run_id':run_id,'parent_run':protocol['parent_run'],
        'source_sha256':protocol['source_sha256'],'result':result,'top_routes':len(top),'all_routes':46,
        'test_independent':False,'daily_R05_acceptance_replaced':False,
        'files':{p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()}}
    write_json(out/'summary.json',summary);print(json.dumps(result),flush=True);return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--config',default='data/configs/aggregate-focus.json')
    parser.add_argument('--phase',choices=['validation','test'],required=True);args=parser.parse_args()
    validation(args.run_id,args.config) if args.phase=='validation' else test(args.run_id)
