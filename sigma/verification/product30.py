"""Verify M3 balances, raw SKU shares, thresholds, pending clocks and D+7."""
import argparse
from datetime import datetime, timezone
import json
import math
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ITEM, ROUTE, sha256, write_json
from src.data import audit_orders
from src.transactions import verify_events
from sigma.inventory.product30 import validate_product


def execute(run_id, output=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id) or (output and not re.fullmatch(r'[A-Za-z0-9_.-]+',output)):
        raise ValueError('Invalid local evidence name')
    folder=ROOT/'outputs'/run_id;summary=validate_product(folder)
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'));cfg=protocol['config']
    for path,digest in protocol['implementation_modules_sha256'].items(): assert sha256(ROOT/path)==digest
    assert sha256(ROOT/cfg['source'])==summary['source_sha256']
    sales,audit=audit_orders(ROOT/cfg['source'],cfg)
    matrix=sales.groupby(['date']+ITEM).quantity.sum().unstack(ITEM,fill_value=0).reindex(
        pd.date_range(cfg['observation_start'],cfg['observation_end']),fill_value=0)
    parent=ROOT/'outputs'/summary['aggregate_run']
    forecasts=pd.read_csv(parent/'daily_allocation.csv',parse_dates=['as_of_date','target_date'],float_precision='round_trip')
    forecasts=forecasts.loc[forecasts.window_days.eq(summary['forecast_window_days'])]
    assert not forecasts.duplicated(ROUTE+['as_of_date','horizon_day']).any()
    thresholds=[];vectors={}
    for (country,carrier,origin),part in forecasts.groupby(ROUTE+['as_of_date']):
        keys=[key for key in matrix if key[:2]==(country,carrier) and matrix.loc[:origin,key].sum()>0]
        for window in [cfg['inventory']['allocation_window_days'],cfg['inventory']['allocation_fallback_days']]:
            totals=matrix.loc[origin-pd.Timedelta(days=window-1):origin,keys].sum()
            if totals.sum()>0: break
        if totals.sum()<=0: raise ValueError('No independent SKU allocation basis')
        shares=totals/totals.sum();route=part.sort_values('horizon_day').forecast_qty.to_numpy()
        assert len(route)==summary['forecast_window_days']
        for key in keys:
            vector=route*shares[key];vectors[(origin,key)]=vector
            thresholds.append({**dict(zip(ITEM,key)),'as_of_date':origin,'mean':vector.mean(),
                **{f'sum{h}':vector[:h].sum() for h in [1,2,3,4,7,8]}})
    thresholds=pd.DataFrame(thresholds)
    scenarios=json.loads((folder/'scenario_configs.json').read_text(encoding='utf-8'))
    scenarios={v['scenario']['name']:v for v in scenarios}
    rec=pd.read_csv(folder/'inventory_recommendations.csv',parse_dates=['as_of_date','eta','expected_depletion_date'],float_precision='round_trip',low_memory=False,
                    dtype={k:'category' for k in ITEM+['scenario_id','partner_id','status','depletion_state']})
    assert not rec.duplicated(ITEM+['scenario_id','as_of_date']).any()
    for name,part in rec.groupby('scenario_id',observed=True):
        merged=part.merge(thresholds,on=ITEM+['as_of_date'],validate='many_to_one');assert len(merged)==len(part)
        for partner,g in merged.groupby('partner_id',observed=True):
            p=scenarios[name]['inventory']['partners'][partner]
            ss=np.ceil(p['safety_days']*g['mean']);rop=np.ceil(g[f"sum{p['lead_time_days']}"]+ss)
            target=np.ceil(g[f"sum{p['lead_time_days']+p['review_days']}"]+ss)
            np.testing.assert_array_equal(g.SS,ss);np.testing.assert_array_equal(g.ROP,rop);np.testing.assert_array_equal(g.S,target)
            np.testing.assert_array_equal(g.needs_replenishment,g.on_hand<rop)
            q=np.where(g.on_hand<rop,np.ceil(np.maximum(0,target-g.IP)),0)
            q=np.where(q>0,np.maximum(q,p['moq']),0);np.testing.assert_array_equal(g.Q,q)
            positive=g.Q.gt(0);assert g.loc[~positive,'eta'].isna().all()
            assert g.loc[positive,'eta'].eq(g.loc[positive,'as_of_date']+pd.Timedelta(days=p['lead_time_days'])).all()
    # Independently reconstruct outstanding orders, removing full promised
    # quantities only when the simulated actual receipt has arrived.
    codes,unique=pd.factorize(pd.MultiIndex.from_frame(rec[['scenario_id']+ITEM]),sort=True)
    n_days=(pd.Timestamp(cfg['test_end'])-pd.Timestamp(cfg['test_start'])).days+1
    day=(rec.as_of_date-pd.Timestamp(cfg['test_start'])).dt.days.to_numpy()
    lead=np.array([scenarios[n]['inventory']['partners'][p]['lead_time_days'] for n,p in zip(rec.scenario_id,rec.partner_id)])
    delay=rec.scenario_id.map({n:v['scenario']['receipt_delay_days'] for n,v in scenarios.items()}).to_numpy(int)
    width=n_days+int(max(lead+delay))+1
    placed=np.zeros((len(unique),width),dtype=np.int64);removed=np.zeros_like(placed)
    np.add.at(placed,(codes,day),rec.Q.to_numpy(np.int64))
    np.add.at(removed,(codes,day+lead+delay),rec.Q.to_numpy(np.int64))
    pending=placed.cumsum(axis=1)-placed-removed.cumsum(axis=1)
    for r in cfg['inventory']['initial_receipts']:
        key=tuple(r[k] for k in ITEM)
        valid=pd.date_range(cfg['test_start'],periods=n_days)<pd.Timestamp(r['eta'])
        for i,k in enumerate(unique):
            if tuple(k[1:])==key: pending[i,:n_days]+=valid*r['quantity']
    np.testing.assert_array_equal(rec.IP.to_numpy()-rec.on_hand.to_numpy(),pending[codes,day])
    ledger_rows=0;totals={};closing={}
    expected_sales=int(sales.loc[sales.date.between(cfg['test_start'],cfg['test_end'])].quantity.sum())
    for chunk in pd.read_csv(folder/'inventory_ledger.csv',chunksize=50000):
        values=chunk[['opening','receipts','historical_sales','scenario_demand','fulfilled','shortage','closing']].to_numpy()
        assert np.isfinite(values).all() and (values>=0).all() and np.equal(values,np.floor(values)).all()
        np.testing.assert_array_equal(chunk.closing,chunk.opening+chunk.receipts-chunk.fulfilled)
        np.testing.assert_array_equal(chunk.scenario_demand,chunk.fulfilled+chunk.shortage)
        for name,g in chunk.groupby('scenario_id'):
            totals[name]=totals.get(name,np.zeros(4))+g[['historical_sales','scenario_demand','fulfilled','shortage']].sum().to_numpy()
            closing[name]=closing.get(name,0)+g.closing.sum()
        ledger_rows+=len(chunk)
    assert all(t[0]==expected_sales for t in totals.values()) and set(totals)==set(scenarios)
    events=verify_events(folder/'inventory_events.csv',folder/'inventory_ledger.csv',sales,cfg)
    metrics=pd.read_csv(folder/'simulation_metrics.csv',float_precision='round_trip')
    for name,(_,demand,filled,shortage) in totals.items():
        r=metrics.loc[metrics.scenario_id.eq(name)].iloc[0]
        np.testing.assert_allclose([r.demand,r.shortage,r.fill_rate,r.mean_closing_on_hand],
            [demand,shortage,filled/demand if demand else np.nan,closing[name]/n_days],atol=1e-8,rtol=0)
    replay_count=0
    for horizon in [14,summary['forecast_window_days']]:
        alerts=pd.read_csv(folder/f'alerts_{horizon}d.csv',parse_dates=['as_of_date','actual_depletion_date','predicted_depletion_date'])
        assert not alerts.event_id.duplicated().any()
        for r in alerts.itertuples():
            key=tuple(getattr(r,k) for k in ITEM);origin=r.as_of_date
            hist=matrix.loc[origin-pd.Timedelta(days=cfg['inventory']['initial_window_days']-1):origin,key]
            stock=math.ceil(cfg['inventory']['initial_cover_days']*hist.mean())
            assert r.already_empty==(stock<=0)
            actual=matrix.loc[origin+pd.Timedelta(days=1):origin+pd.Timedelta(days=horizon),key].to_numpy()
            def first_zero(demand):
                s=stock
                if s<=0:return None
                for h,q in enumerate(demand,1):
                    date=origin+pd.Timedelta(days=h)
                    s+=sum(x['quantity'] for x in cfg['inventory']['initial_receipts'] if tuple(x[k] for k in ITEM)==key and pd.Timestamp(x['eta'])==date)
                    s=max(0,s-q)
                    if s<=1e-9:return h
                return None
            ad=first_zero(actual);pd_=first_zero(vectors[(origin,key)][:horizon])
            assert (pd.isna(r.actual_days) if ad is None else r.actual_days==ad)
            assert (pd.isna(r.predicted_days) if pd_ is None else r.predicted_days==pd_)
            assert r.tp==bool(ad is not None and pd_ is not None)
            assert r.fp==bool(ad is None and pd_ is not None)
            assert r.fn==bool(ad is not None and pd_ is None)
            assert r.reported_early==bool(ad is not None and pd_ is not None and ad>=7)
        replay_count+=len(alerts)
        if horizon==14:
            denom=int(alerts.tp.sum()+alerts.fn.sum())
            expected=alerts.reported_early.sum()/denom if denom else np.nan
            np.testing.assert_allclose(summary['early_event_rate'],expected,atol=1e-8,rtol=0,equal_nan=True)
            old=ROOT/'outputs/sigma_scaled_v11/alerts.csv'
            old_manifest=old.parent/'manifest.json'
            same_source=old_manifest.is_file() and json.loads(old_manifest.read_text()).get('source_sha256')==summary['source_sha256']
            if old.is_file() and same_source:
                previous=pd.read_csv(old,parse_dates=['actual_depletion_date'])
                joined=alerts.merge(previous,on='event_id',suffixes=('','_old'),validate='one_to_one')
                assert len(joined)==len(alerts)==len(previous)
                assert joined.actual_depletion_date.equals(joined.actual_depletion_date_old)
    delivery=pd.read_csv(folder/'delivery_projection.csv',parse_dates=['delivery_date','order_date','as_of_date'],float_precision='round_trip')
    assert delivery.actual_delivered_qty.isna().all() and delivery.customer_delay_days.eq(0).all()
    assert delivery.delivery_date.eq(delivery.order_date+pd.Timedelta(days=7)).all()
    latest=forecasts.loc[forecasts.as_of_date.eq(cfg['forecast_origin'])]
    np.testing.assert_allclose(delivery.forecast_from_future_orders_qty.sum(),latest.forecast_qty.sum(),atol=1e-8,rtol=0)
    dates=pd.to_datetime(sales.order_datetime,utc=True).dt.tz_localize(None).dt.normalize()
    known=int(sales.loc[dates.le(cfg['forecast_origin'])&(dates+pd.Timedelta(days=7)).gt(cfg['forecast_origin'])].quantity.sum())
    assert delivery.known_commitment_qty.sum()==known
    result={'status':'verified','run_id':run_id,'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'summary_sha256':sha256(folder/'summary.json'),'raw_rows':audit['rows_raw'],'raw_quantity':audit['sales_quantity'],
        'ledger_rows':ledger_rows,'recommendations':len(rec),'independent_sku_thresholds':len(thresholds),
        'pending_order_clocks_checked':len(rec),'alert_windows_checked':replay_count,'known_delivery_qty':known,
        'stock_is_simulated':True,'strict_on_hand_trigger':True,'daily_R05_acceptance_replaced':False,
        'project_fully_accepted':False,**events}
    path=ROOT/'outputs'/(output or (run_id+'_verification.json'))
    if path.exists(): raise FileExistsError('Never overwrite verification evidence')
    write_json(path,result);print(json.dumps(result),flush=True);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True);parser.add_argument('--output')
    a=parser.parse_args();execute(a.run_id,a.output)
