"""Past-only calibration of saved causal forecasts; isolated from production."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy import sparse
from src.common import ROOT, ROUTE, sha256, write_csv, write_json
from src.evaluation import metric_table

KEY = ROUTE + ['as_of_date', 'target_date', 'horizon_day']
SPECS = {'convex': (True, 0.), 'affine_lad': (False, 0.),
         'affine_regularized': (False, .02)}


def fit_head(x, y, dates, cutoff, convex=True, penalty=0.):
    """Positive-day relative LAD, with nonnegative forecasts and causal labels."""
    cutoff = pd.Timestamp(cutoff)
    dates = pd.DatetimeIndex(dates)
    x, y = np.asarray(x, float), np.asarray(y, float)
    if (y[(dates <= cutoff) & np.isfinite(y)] < 0).any():
        raise ValueError('Negative historical calibration label')
    keep = (dates <= cutoff) & np.isfinite(y) & (y > 0)
    if x.ndim != 2 or len(x) != len(y) or not keep.any():
        raise ValueError('No labeled causal calibration examples')
    x, y = x[keep], y[keep]
    if not np.isfinite(x).all() or (x < 0).any():
        raise ValueError('Invalid base forecasts')
    # A bounded constant is an intercept, not a target or future feature.
    z = x if convex else np.column_stack([x, np.ones(len(x))])
    n, k = z.shape
    a = sparse.csr_matrix(z)
    eye = sparse.eye(n, format='csr')
    bounds = [(0., 1. if convex else 2.)] * x.shape[1]
    if not convex:
        bounds += [(0., float(y.max()))]
    bounds += [(0., None)] * n
    c = np.r_[np.full(k, penalty), 1. / y / n]
    inequalities = sparse.vstack([sparse.hstack([a, -eye]), sparse.hstack([-a, -eye])],format='csr')
    if convex:
        eq = sparse.csr_matrix(np.r_[np.ones(k), np.zeros(n)][None, :])
        result = linprog(c, A_ub=inequalities, b_ub=np.r_[y,-y], A_eq=eq,
                         b_eq=[1.], bounds=bounds, method='highs')
    else:
        cap = sparse.csr_matrix(np.r_[np.ones(x.shape[1]),0.,np.zeros(n)][None,:])
        result = linprog(c, A_ub=sparse.vstack([inequalities,cap]), b_ub=np.r_[y,-y,2.],
                         bounds=bounds, method='highs')
    if not result.success:
        raise ValueError('Calibration optimization failed: '+result.message)
    return {'weights':result.x[:x.shape[1]], 'intercept':0. if convex else float(result.x[k-1]),
            'max_label_date': dates[keep].max(), 'training_pairs':int(keep.sum()),
            'fit_cutoff':cutoff}


def predict_head(state, x):
    x=np.asarray(x,float)
    if not np.isfinite(x).all() or (x<0).any():
        raise ValueError('Invalid base forecasts')
    return np.maximum(x@state['weights']+state['intercept'],0.)


def matrix(frame):
    if frame.duplicated(KEY+['model']).any():
        raise ValueError('Duplicate forecast pair')
    groups=frame.groupby(KEY,dropna=False).actual_qty
    actuals=groups.agg(['first','nunique'])
    if groups.nunique(dropna=False).gt(1).any():
        raise ValueError('Base model labels disagree')
    wide=frame.pivot(index=KEY,columns='model',values='forecast_qty').sort_index()
    if wide.isna().any().any():
        raise ValueError('Incomplete base forecast coverage')
    meta=wide.index.to_frame(index=False)
    meta['actual_qty']=actuals['first'].reindex(wide.index).to_numpy()
    return meta,wide.to_numpy(float),list(wide.columns)


def run(output_id):
    if Path(output_id).name!=output_id or output_id in ('','.','..'):
        raise ValueError('Output id must be a directory name')
    out=ROOT/'outputs'/output_id;out.mkdir(exist_ok=False)
    base=ROOT/'outputs/sigma_ablation_campaign_v1'
    summary=json.loads((base/'summary.json').read_text())
    source=ROOT/'data/sigma_sim_data_orders.csv'
    source_hash=sha256(source)
    files=['inner_train_predictions.csv','validation_predictions.csv']
    for name in files:
        if sha256(base/name)!=summary['files'][name]:
            raise ValueError('Saved causal forecast hash changed')
    write_json(out/'protocol.json',{
        'specs':SPECS,'script_sha256':sha256(Path(__file__)), 'raw_sha256':source_hash,
        'input_sha256':{n:sha256(base/n) for n in files},
        'selection':'Fit heads on May labels, choose on June inside train; lock by route before validation.',
        'outer':'July-September only, weekly refit head with past OOF labels; test never read/scored.',
        'base_models':'12 preregistered causal forecast models from campaign v1, weekly refit.',
        'target':'Unchanged UTC sales quantity, top10 train, H14, positive-day MAPE h1-7.',
        'no_new_acceptance_claim':'Repeated validation and viewed test limitations remain.'})
    inner=pd.read_csv(base/files[0],parse_dates=['as_of_date','target_date'])
    outer=pd.read_csv(base/files[1],parse_dates=['as_of_date','target_date'])
    inner=inner.loc[inner.split.eq('inner_train')]
    outer=outer.loc[outer.split.eq('validation')]
    for frame,start,end in [(inner,'2025-05-01','2025-06-30'),(outer,'2025-07-01','2025-09-30')]:
        if (not frame.target_date.between(start,end).all()
                or not frame.as_of_date.ge(pd.Timestamp(start)-pd.Timedelta(days=1)).all()
                or not frame.horizon_day.between(1,14).all()
                or not ((frame.target_date-frame.as_of_date).dt.days==frame.horizon_day).all()):
            raise ValueError('Saved forecast phase/horizon violates unchanged protocol')
    locks=[]; june_rows=[]; outer_rows=[]; logs=[]
    for key, g in inner.groupby(ROUTE,sort=True):
        meta,x,names=matrix(g)
        primary=meta.horizon_day.le(7).to_numpy()
        june=(meta.target_date.ge('2025-06-01') & meta.as_of_date.ge('2025-05-31')).to_numpy()
        candidates=[]
        for name,(convex,penalty) in SPECS.items():
            state=fit_head(x[primary],meta.actual_qty.to_numpy()[primary],
                           meta.target_date[primary],'2025-05-31',convex,penalty)
            frame=meta.loc[june].copy();frame['forecast_qty']=predict_head(state,x[june])
            frame['model']=name;frame['split']='inner_june'
            june_rows.append(frame)
            primary_metric=metric_table(frame).query("horizon_group=='h1_7'").iloc[0]
            candidates.append((primary_metric.mape_positive_pct,primary_metric.mae,name))
        chosen=min(candidates)[2]
        locks.append({**dict(zip(ROUTE,key)),'model':chosen,'selection_end':'2025-06-30'})
        write_csv(out/'inner_locked_models.csv',pd.DataFrame(locks))
    lock_hash=sha256(out/'inner_locked_models.csv')
    # Selection is fully written before any outer labels are scored/fitted.
    for lock in locks:
        key=tuple(lock[k] for k in ROUTE);chosen=lock['model'];convex,penalty=SPECS[chosen]
        same=lambda df:df.destination_country.eq(key[0])&df.carrier.eq(key[1])
        im,ix,names=matrix(inner.loc[same(inner)])
        om,ox,outer_names=matrix(outer.loc[same(outer)])
        if names!=outer_names:raise ValueError('Base model order changed')
        all_meta=pd.concat([im,om],ignore_index=True);all_x=np.vstack([ix,ox])
        origins=sorted(om.as_of_date.unique())
        state=None
        for i,origin in enumerate(origins):
            if i%7==0:
                available=(all_meta.horizon_day.le(7)&all_meta.target_date.le(origin)).to_numpy()
                state=fit_head(all_x[available],all_meta.actual_qty.to_numpy()[available],
                               all_meta.target_date[available],origin,convex,penalty)
                logs.append({**dict(zip(ROUTE,key)),'model':chosen,
                             'fit_cutoff':origin,'max_label_date':state['max_label_date'],
                             'training_pairs':state['training_pairs'],
                             'weights':json.dumps(state['weights'].tolist()),'intercept':state['intercept']})
            mask=om.as_of_date.eq(origin).to_numpy();f=om.loc[mask].copy()
            f['forecast_qty']=predict_head(state,ox[mask]);f['model']='calibrated_locked';f['split']='validation'
            outer_rows.append(f)
        print('Calibrated one train-top10 route',flush=True)
    if sha256(out/'inner_locked_models.csv')!=lock_hash:raise ValueError('Selection changed')
    predictions=pd.concat(outer_rows,ignore_index=True)
    metrics=metric_table(predictions)
    write_csv(out/'inner_june_predictions.csv',pd.concat(june_rows,ignore_index=True))
    write_csv(out/'validation_predictions.csv',predictions)
    write_csv(out/'validation_metrics.csv',metrics)
    write_csv(out/'head_fit_log.csv',pd.DataFrame(logs))
    primary=metrics.loc[metrics.horizon_group.eq('h1_7')]
    assert primary.coverage.eq(1).all()
    result={'status':'complete','routes':len(primary),'passed':int(primary.mape_positive_pct.le(20).sum()),
            'mean_mape':float(primary.mape_positive_pct.mean()),'min_mape':float(primary.mape_positive_pct.min()),
            'max_mape':float(primary.mape_positive_pct.max()),'selection_sha256':lock_hash,
            'raw_unchanged':sha256(source)==source_hash,'test_used':False,'production_modified':False}
    result['files']={p.name:sha256(p) for p in out.iterdir() if p.is_file()}
    write_json(out/'summary.json',result);print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-id',required=True)
    run(parser.parse_args().output_id)
