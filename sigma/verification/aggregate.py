"""Independent raw-label, calendar, selection, metric and allocation checks."""
import argparse
from datetime import datetime, timezone
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, write_json
from src.data import audit_orders, daily_sales, route_top
from sigma.forecasting.aggregate import validate_aggregate


def read_predictions(path):
    return pd.read_csv(path, parse_dates=['as_of_date','window_start','target_date','fit_cutoff'], float_precision='round_trip')


def independently_score(part, expected):
    valid = part.actual_qty.notna() & np.isfinite(part.forecast_qty)
    a = part.loc[valid,'actual_qty'].to_numpy(float)
    f = part.loc[valid,'forecast_qty'].to_numpy(float)
    e = f-a; pos = a>0
    return {'mape_positive_pct': np.mean(np.abs(e[pos])/a[pos])*100 if pos.any() else np.nan,
        'mae': np.mean(np.abs(e)) if len(a) else np.nan,
        'wape_pct': np.abs(e).sum()/a.sum()*100 if a.sum()>0 else np.nan,
        'bias': e.mean() if len(a) else np.nan,
        'n_expected': expected,'n_labeled_pairs':int(part.actual_qty.notna().sum()),
        'n_scored_pairs':len(a),'n_positive_pairs':int(pos.sum()),'n_zero_pairs':int((a==0).sum()),
        'coverage':len(a)/expected if expected else np.nan,
        'positive_share':pos.mean() if len(a) else np.nan,
        'unique_target_days':part.loc[valid,'target_date'].nunique()}


def check_metrics(pred, saved, cfg, tolerance):
    count = 0
    keys=['window_days','split','model']+ROUTE
    for r in saved.itertuples():
        mask=np.ones(len(pred),dtype=bool)
        for key in keys: mask &= pred[key].eq(getattr(r,key)).to_numpy()
        part=pred.loc[mask & pred.target_date.le(pd.Timestamp(cfg[f'{r.split}_end']))]
        anchor=pd.Timestamp(cfg[f'{r.split}_start'])-pd.Timedelta(days=1)
        n=max(0,(pd.Timestamp(cfg[f'{r.split}_end'])-anchor).days-int(r.window_days)+1)
        if r.cadence!='daily_origins':
            part=part.loc[(part.as_of_date-anchor).dt.days.mod(int(r.window_days)).eq(0)]
            n=len(range(0,n,int(r.window_days)))
        metrics=independently_score(part,n)
        for name,value in metrics.items():
            np.testing.assert_allclose(getattr(r,name),value,atol=tolerance,rtol=0,equal_nan=True)
        assert bool(r.passes_20_pct)==bool(metrics['coverage']==1 and metrics['mape_positive_pct']<=cfg['mape_limit_pct'])
        count+=1
    assert not saved.duplicated(keys+['cadence']).any()
    return count


def execute(run_id, output=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id) or (output and not re.fullmatch(r'[A-Za-z0-9_.-]+',output)):
        raise ValueError('Invalid local evidence name')
    out=ROOT/'outputs'/run_id
    info=validate_aggregate(out)
    protocol=json.loads((out/'protocol.json').read_text(encoding='utf-8'))
    cfg,settings=protocol['config'],protocol['settings']; tolerance=settings['numeric_tolerance']
    assert sha256(ROOT/cfg['source'])==info['source_sha256']==protocol['source_sha256']
    for path,digest in protocol['implementation_modules_sha256'].items(): assert sha256(ROOT/path)==digest
    sales,audit=audit_orders(ROOT/cfg['source'],cfg); daily=daily_sales(sales,cfg);top=route_top(daily,cfg)
    pd.testing.assert_frame_equal(daily,pd.read_csv(out/'daily_sales.csv',parse_dates=['date'],float_precision='round_trip'))
    pd.testing.assert_frame_equal(top,pd.read_csv(out/'top_routes.csv',float_precision='round_trip'))
    groups={key:part.set_index('date').sales_qty for key,part in daily.groupby(ROUTE)}
    selection=pd.read_csv(out/'selected_models.csv',float_precision='round_trip')
    expected_keys={(h,*key) for h in settings['windows'] for key in groups}
    assert set(selection[['window_days']+ROUTE].itertuples(index=False,name=None))==expected_keys
    assert not selection.duplicated(['window_days']+ROUTE).any()
    lock=json.loads((out/'selection_lock.json').read_text(encoding='utf-8'))
    assert lock['selection_sha256']==sha256(out/'selected_models.csv') and lock['test_used_for_ranking'] is False
    counts={};frames={}
    for split in ['validation','test','future']:
        pred=read_predictions(out/f'{split}_predictions.csv');frames[split]=pred
        assert set(pred[['window_days']+ROUTE].itertuples(index=False,name=None))==expected_keys
        assert not pred.duplicated(['window_days']+ROUTE+['model','as_of_date']).any()
        expected_origins=(pd.DatetimeIndex([pd.Timestamp(cfg['forecast_origin'])]) if split=='future' else
            pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1),pd.Timestamp(cfg[f'{split}_end'])-pd.Timedelta(days=1)))
        for (window,country,carrier,model),part in pred.groupby(['window_days']+ROUTE+['model']):
            assert pd.DatetimeIndex(part.as_of_date).sort_values().equals(expected_origins)
            assert part.window_start.eq(part.as_of_date+pd.Timedelta(days=1)).all()
            assert part.target_date.eq(part.as_of_date+pd.Timedelta(days=int(window))).all()
            y=groups[(country,carrier)]
            expected=y.rolling(int(window),min_periods=int(window)).sum().reindex(part.target_date).to_numpy(copy=True)
            if split=='future': expected[:]=np.nan
            else: expected[part.target_date.gt(pd.Timestamp(cfg[f'{split}_end'])).to_numpy()]=np.nan
            np.testing.assert_allclose(part.actual_qty,expected,atol=0,rtol=0,equal_nan=True)
            assert part.fit_cutoff.le(part.as_of_date).all()
            if split!='validation':
                chosen=selection.loc[selection.window_days.eq(window)&selection.destination_country.eq(country)&selection.carrier.eq(carrier)]
                assert len(chosen)==1 and chosen.model.iloc[0]==model
                assert np.isfinite(part.forecast_qty).all() and part.forecast_qty.ge(0).all()
        if split!='future':
            saved=pd.read_csv(out/f'{split}_metrics.csv',float_precision='round_trip')
            counts[split+'_metric_groups']=check_metrics(pred,saved,cfg,tolerance)
        counts[split+'_prediction_rows']=len(pred)
    # Independent choice reconstruction, including full-phase forecasts.
    val=frames['validation']
    valmetrics=pd.read_csv(out/'validation_metrics.csv',float_precision='round_trip')
    for r in selection.itertuples():
        candidates=valmetrics.loc[valmetrics.window_days.eq(r.window_days)&valmetrics.destination_country.eq(r.destination_country)
            &valmetrics.carrier.eq(r.carrier)&valmetrics.cadence.eq('daily_origins')&valmetrics.coverage.eq(1)&valmetrics.mape_positive_pct.notna()]
        complete=val.loc[val.window_days.eq(r.window_days)&val.destination_country.eq(r.destination_country)&val.carrier.eq(r.carrier)].groupby('model').forecast_qty.agg(lambda x:np.isfinite(x).all())
        candidates=candidates.loc[candidates.model.map(complete)]
        assert candidates.sort_values(['mape_positive_pct','mae','model']).iloc[0].model==r.model
    for window in settings['windows']:
        for split in ['test','future']:
            execution=json.loads((out/f'{split}_{window}d_execution.json').read_text())
            assert lock['created_at_utc']<=execution['started_at_utc']
            assert execution['selection_sha256']==lock['selection_sha256']
    logs=pd.read_csv(out/'fit_log.csv',parse_dates=['fit_cutoff','max_label_end'])
    fits=logs.loc[logs.status.eq('ok')]
    assert fits.max_label_end.le(fits.fit_cutoff).all()
    allocation=pd.read_csv(out/'daily_allocation.csv',parse_dates=['as_of_date','target_date'],float_precision='round_trip')
    assert allocation.actual_qty.isna().all() and allocation.is_daily_allocation.all()
    assert not allocation.duplicated(['window_days']+ROUTE+['as_of_date','horizon_day']).any()
    assert allocation.target_date.eq(allocation.as_of_date+pd.to_timedelta(allocation.horizon_day,unit='D')).all()
    sums=allocation.groupby(['window_days']+ROUTE+['as_of_date']).forecast_qty.sum()
    count=0
    for r in pd.concat([frames['test'],frames['future']]).itertuples():
        key=(r.window_days,r.destination_country,r.carrier,r.as_of_date)
        np.testing.assert_allclose(sums.loc[key],r.forecast_qty,atol=tolerance,rtol=0)
        count+=1
    receipt={'status':'verified','run_id':run_id,'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'summary_sha256':sha256(out/'summary.json'),'raw_rows':audit['rows_raw'],'sales_quantity':audit['sales_quantity'],
        'top10_train_exact':True,'selection_count':len(selection),'selection_locked_before_test':True,
        'allocation_groups':count,'fit_cutoffs_checked':len(fits),'candidate_failures_logged':int(logs.status.eq('failed').sum()),
        **counts,'test_independent':False,'daily_R05_acceptance_replaced':False}
    path=ROOT/'outputs'/(output or (run_id+'_verification.json'))
    if path.exists(): raise FileExistsError('Never overwrite verification evidence')
    write_json(path,receipt);print(json.dumps(receipt),flush=True);return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True);parser.add_argument('--output')
    args=parser.parse_args();execute(args.run_id,args.output)
