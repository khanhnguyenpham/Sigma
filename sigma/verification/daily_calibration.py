"""Independent raw-quantity, pair, metric and saved-weight checks for research."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from src.common import ROOT,ROUTE,sha256,write_csv,write_json


def verify(run_id,output_id):
    for value in [run_id,output_id]:
        if Path(value).name!=value or value in ('','.','..'):raise ValueError('Invalid id')
    run=ROOT/'outputs'/run_id;out=ROOT/'outputs'/output_id;out.mkdir(exist_ok=False)
    summary=json.loads((run/'summary.json').read_text());protocol=json.loads((run/'protocol.json').read_text())
    assert summary['status']=='complete' and not summary['test_used'] and not summary['production_modified']
    for name,digest in summary['files'].items():assert sha256(run/name)==digest
    assert sha256(ROOT/'calibrate_campaign.py')==protocol['script_sha256']
    raw=ROOT/'data/sigma_sim_data_orders.csv';assert sha256(raw)==protocol['raw_sha256']
    source=pd.read_csv(raw,usecols=ROUTE+['order_datetime','quantity','order_status'])
    source['date']=pd.to_datetime(source.order_datetime,utc=True).dt.tz_localize(None).dt.normalize()
    # Target is reconstructed directly from supplied orders, not pipeline helpers.
    sales=source.loc[source.order_status.eq('success')&source.date.le('2025-09-30')].copy()
    totals=sales.groupby(['date']+ROUTE).quantity.sum()
    train=sales.loc[sales.date.le('2025-06-30')].groupby(ROUTE).quantity.sum().reset_index()
    top=train.sort_values(['quantity']+ROUTE,ascending=[False,True,True]).head(10)
    keys=set(map(tuple,top[ROUTE].to_numpy()))
    pred=pd.read_csv(run/'validation_predictions.csv',parse_dates=['as_of_date','target_date'])
    assert set(map(tuple,pred[ROUTE].drop_duplicates().to_numpy()))==keys
    cols=ROUTE+['as_of_date','target_date','horizon_day']
    assert not pred.duplicated(cols).any() and pred.split.eq('validation').all()
    origins=pd.date_range('2025-06-30','2025-09-29')
    expected={(o,o+pd.Timedelta(days=h),h) for o in origins for h in range(1,15)
              if o+pd.Timedelta(days=h)<=pd.Timestamp('2025-09-30')}
    checks=[]
    metric=pd.read_csv(run/'validation_metrics.csv')
    for key,g in pred.groupby(ROUTE):
        actual_pairs=set(zip(g.as_of_date,g.target_date,g.horizon_day));assert actual_pairs==expected
        actual=np.array([totals.get((day,*key),0.) for day in g.target_date])
        np.testing.assert_array_equal(actual,g.actual_qty.to_numpy())
        for group,mask in [('h1_7',g.horizon_day.le(7)),('h8_14',g.horizon_day.gt(7))]:
            a=g.loc[mask,'actual_qty'].to_numpy();f=g.loc[mask,'forecast_qty'].to_numpy();positive=a>0
            mape=float(np.mean(np.abs(f[positive]-a[positive])/a[positive])*100)
            row=metric.loc[metric.destination_country.eq(key[0])&metric.carrier.eq(key[1])&metric.horizon_group.eq(group)].iloc[0]
            np.testing.assert_allclose([mape,np.mean(np.abs(f-a)),np.abs(f-a).sum()/a.sum()*100,np.mean(f-a)],
                [row.mape_positive_pct,row.mae,row.wape_pct,row.bias],rtol=0,atol=1e-8)
            assert row.n_expected==row.n_scored_pairs==len(a) and row.n_positive_pairs==positive.sum() and row.coverage==1
            checks.append({**dict(zip(ROUTE,key)),'horizon_group':group,'pairs':len(a),'mape':mape})
    base=ROOT/'outputs/sigma_ablation_campaign_v1'
    cached=pd.read_csv(base/'validation_predictions.csv',parse_dates=['as_of_date','target_date'])
    cached=cached.loc[cached.split.eq('validation')]
    logs=pd.read_csv(run/'head_fit_log.csv',parse_dates=['fit_cutoff','max_label_date'])
    assert logs.max_label_date.le(logs.fit_cutoff).all()
    assert len(logs)==10*14
    for key,g in pred.groupby(ROUTE):
        grid=cached.loc[cached.destination_country.eq(key[0])&cached.carrier.eq(key[1])].pivot(index=cols,columns='model',values='forecast_qty')
        route_logs=logs.loc[logs.destination_country.eq(key[0])&logs.carrier.eq(key[1])].sort_values('fit_cutoff')
        for origin,sub in g.groupby('as_of_date'):
            head=route_logs.loc[route_logs.fit_cutoff.le(origin)].iloc[-1]
            weights=np.array(json.loads(head.weights));assert (weights>=-1e-8).all() and weights.sum()<=2+1e-8 and head.intercept>=0
            x=grid.reindex(pd.MultiIndex.from_frame(sub[cols])).to_numpy()
            np.testing.assert_allclose(x@weights+head.intercept,sub.forecast_qty.to_numpy(),rtol=0,atol=1e-8)
    manifest=json.loads((ROOT/'outputs/sigma_scaled_v11/manifest.json').read_text())
    for name,digest in manifest['files'].items():assert sha256(ROOT/'outputs/sigma_scaled_v11'/name)==digest
    # This is an optimistic IN-SAMPLE diagnostic, never an admissible forecast
    # or proof of the minimum possible error of every future forecasting model.
    dates=pd.date_range('2024-01-01','2025-06-30');diagnostics=[]
    for key in sorted(keys):
        qty=np.array([totals.get((day,*key),0.) for day in dates],float)
        frame=pd.DataFrame({'date':dates,'quantity':qty,'month':dates.month,'weekday':dates.dayofweek})
        fitted=np.zeros(len(frame))
        for _,idx in frame.groupby(['month','weekday']).groups.items():
            y=frame.loc[idx,'quantity'].to_numpy();positive=y[y>0]
            if len(positive):
                z=np.sort(positive);w=1/z
                fitted[idx]=z[np.searchsorted(w.cumsum(),w.sum()/2)]
        positive=qty>0
        residual=qty-frame.groupby(['month','weekday']).quantity.transform('mean').to_numpy()
        diagnostics.append({**dict(zip(ROUTE,key)),'train_days':len(qty),'mean_qty':qty.mean(),'std_qty':qty.std(ddof=1),
            'positive_days':int(positive.sum()),'positive_qty_1_to_3_share':float(((qty>=1)&(qty<=3)).sum()/positive.sum()),
            'optimistic_in_sample_month_weekday_mape':float((np.abs(fitted[positive]-qty[positive])/qty[positive]).mean()*100),
            'calendar_demeaned_lag1_correlation':float(np.corrcoef(residual[1:],residual[:-1])[0,1]),
            'diagnostic_only_not_out_of_sample':True})
    write_csv(out/'independent_metrics.csv',pd.DataFrame(checks));write_csv(out/'train_diagnostics.csv',pd.DataFrame(diagnostics))
    prod=pd.read_csv(ROOT/'outputs/sigma_scaled_v11/selected_models.csv');prod=prod.loc[prod.is_top10]
    comp=pd.DataFrame(checks).query("horizon_group=='h1_7'").merge(prod[ROUTE+['validation_mape_positive_pct']],on=ROUTE)
    comp['delta_mape_points']=comp.mape-comp.validation_mape_positive_pct
    write_csv(out/'comparison.csv',comp)
    result={'status':'verified','raw_and_all_59_v11_hashes_unchanged':True,'validation_pairs':len(pred),'primary_pairs_per_route':623,
        'max_label_date_within_weekly_fit':True,'saved_weights_reproduce_every_forecast':True,
        'new_validation_mean_mape':float(comp.mape.mean()),'production_validation_mean_mape':float(comp.validation_mape_positive_pct.mean()),
        'passed':summary['passed'],'test_used':False,'production_modified':False,
        'in_sample_diagnostic_is_not_a_forecasting_error_lower_bound':True,
        'source_sha256':sha256(raw),'run_summary_sha256':sha256(run/'summary.json')}
    result['files']={p.name:sha256(p) for p in out.iterdir() if p.is_file()}
    write_json(out/'summary.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);p.add_argument('--output-id',required=True)
    args=p.parse_args();verify(args.run_id,args.output_id)
