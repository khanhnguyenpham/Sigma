"""Integrated candidates using route/country/global history known at origin.

Calendar dates are known ahead. Other routes' future sales are never features.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.common import ROUTE

CONTEXT_FEATURES = [
    'route_index', 'horizon_day', 'lag0', 'lag1', 'lag7', 'lag14',
    'mean7', 'mean28', 'mean56', 'mean90', 'std28',
    'weekday_last', 'weekday_previous',
    'country_mean7', 'country_mean28', 'country_mean56',
    'global_mean7', 'global_mean28', 'global_mean56', 'route_country_share28',
    'target_weekday', 'target_month', 'target_elapsed_days', 'year_sin', 'year_cos',
]
CONTEXT_SPECS = [('context_180_mape',180,'mape'),('context_365_mape',365,'mape'),
                 ('context_180_poisson',180,'poisson'),('context_365_poisson',365,'poisson')]

def prepare_context(daily, keys, cutoff):
    observed=daily.loc[daily.date.le(pd.Timestamp(cutoff))].copy()
    wide=observed.pivot(index='date',columns=ROUTE,values='sales_qty').sort_index()
    if len(wide)<56 or not wide.index.equals(pd.date_range(wide.index.min(),wide.index.max(),name='date')):
        raise ValueError('Context model needs at least 56 consecutive days')
    if not np.isfinite(wide.to_numpy()).all() or (wide.to_numpy()<0).any():
        raise ValueError('Context model requires complete nonnegative sales history')
    countries={country:wide.loc[:,wide.columns.get_level_values(0)==country].sum(axis=1)
               for country in wide.columns.get_level_values(0).unique()}
    total=wide.sum(axis=1)
    result={}
    def rolling(series):return {w:series.rolling(w,min_periods=min(w,28)).mean().to_numpy() for w in [7,28,56,90]}
    total_roll=rolling(total)
    for ri,key in enumerate(sorted(keys)):
        y=wide[key];cy=countries[key[0]]
        result[key]={'dates':wide.index,'values':y.to_numpy(),'route_index':ri,
                     'rolling':rolling(y),'std':y.rolling(28).std(ddof=0).to_numpy(),
                     'country':rolling(cy),'global':total_roll}
    return result

def context_features(context, indices, horizon):
    indices=np.asarray(indices,dtype=int)
    dates=context['dates'];values=context['values'];roll=context['rolling']
    if (indices<55).any() or (indices>=len(values)).any():raise ValueError('Incomplete context history')
    target=dates[indices]+pd.Timedelta(days=horizon)
    weekday_idx=indices-(dates[indices].dayofweek-target.dayofweek)%7
    country=context['country'];glob=context['global']
    shares=np.divide(roll[28][indices],country[28][indices],
                     out=np.zeros(len(indices)),where=country[28][indices]>0)
    phase=2*np.pi*(target.dayofyear.to_numpy()-1)/365.25
    x=np.column_stack([
        np.full(len(indices),context['route_index']),np.full(len(indices),horizon),
        values[indices],values[indices-1],values[indices-7],values[indices-14],
        *[roll[w][indices] for w in [7,28,56,90]],context['std'][indices],
        values[weekday_idx],values[weekday_idx-7],
        *[country[w][indices] for w in [7,28,56]],*[glob[w][indices] for w in [7,28,56]],shares,
        target.dayofweek,target.month,(target-dates[0]).days,np.sin(phase),np.cos(phase)])
    assert np.isfinite(x).all()
    return pd.DataFrame(x,columns=CONTEXT_FEATURES)

def context_training(daily, keys, cutoff, window, horizon):
    contexts=prepare_context(daily,keys,cutoff)
    xs=[];ys=[];last_label_dates=[]
    start=pd.Timestamp(cutoff)-pd.Timedelta(days=window-1)
    for context in contexts.values():
        for h in range(1,horizon+1):
            inds=np.arange(55,len(context['values'])-h)
            inds=inds[context['dates'][inds+h]>=start]
            if not len(inds):continue
            xs.append(context_features(context,inds,h));ys.append(context['values'][inds+h])
            last_label_dates.append(context['dates'][inds[-1]+h])
    if not xs:raise ValueError('No context labels at cutoff')
    assert max(last_label_dates)<=pd.Timestamp(cutoff)
    return pd.concat(xs,ignore_index=True),np.concatenate(ys)

def fit_context(daily,keys,cutoff,window,loss,cfg):
    from lightgbm import LGBMRegressor
    from sklearn.dummy import DummyRegressor
    x,y=context_training(daily,keys,cutoff,window,cfg['horizon'])
    if not (y>0).any():
        # An inactive training window has no positive MAPE labels and Poisson
        # cannot fit an all-zero target. Preserve the known zero forecast.
        return DummyRegressor(strategy='constant',constant=0).fit(x,y)
    model=LGBMRegressor(objective='regression_l1' if loss=='mape' else 'poisson',
        num_leaves=31,min_child_samples=50,n_estimators=300,learning_rate=.05,
        random_state=cfg['seed'],n_jobs=cfg['lightgbm_threads'],deterministic=True,
        force_col_wise=True,verbosity=-1)
    weights=np.divide(1.,y,out=np.zeros_like(y),where=y>0) if loss=='mape' else None
    model.fit(x,y,sample_weight=weights,categorical_feature=['route_index','target_weekday','target_month'])
    return model

def context_rolling(daily,top,cfg,model_ids,split,progress=print):
    if split not in {'validation','test'}:
        raise ValueError('Unsupported context evaluation split')
    specs={name:(window,loss) for name,window,loss in CONTEXT_SPECS}
    if not set(model_ids).issubset(specs):
        raise ValueError('Unknown context model')
    # Labels after the evaluated split are absent even at its trailing origins.
    observed=daily.loc[daily.date.le(pd.Timestamp(cfg[f'{split}_end']))].copy()
    actual_lookup=observed.set_index(['date']+ROUTE).sales_qty.to_dict()
    keys=sorted(map(tuple,top[ROUTE].to_numpy()));rows=[];logs=[]
    origins=pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1),
                          pd.Timestamp(cfg[f'{split}_end'])-pd.Timedelta(days=1))
    for model_id in model_ids:
        window,loss=specs[model_id]
        model=None
        for i,origin in enumerate(origins):
            if i%cfg['refit_days']==0:
                model=fit_context(observed,keys,origin,window,loss,cfg)
                logs.append({'model':model_id,'fit_cutoff':origin,'max_label_date':origin,'status':'ok'})
                progress(f'{model_id}: {split} fit {origin.date()}')
            contexts=prepare_context(observed,keys,origin)
            all_x=[];metadata=[]
            for key in keys:
                ctx=contexts[key]
                for h in range(1,cfg['horizon']+1):
                    all_x.append(context_features(ctx,[len(ctx['values'])-1],h));metadata.append((key,h))
            predictions=np.maximum(model.predict(pd.concat(all_x,ignore_index=True)),0)
            for (key,h),pred in zip(metadata,predictions):
                target=origin+pd.Timedelta(days=h)
                actual=actual_lookup.get((target,*key),np.nan)
                rows.append({**dict(zip(ROUTE,key)),'as_of_date':origin,'target_date':target,
                             'forecast_date':target,'effective_model':model_id,
                             'horizon_day':h,'model':model_id,'forecast_qty':float(pred),
                             'actual_qty':float(actual),
                             'split':split if target<=pd.Timestamp(cfg[f'{split}_end']) else 'outside_'+split})
    return pd.DataFrame(rows),pd.DataFrame(logs)


def context_validation(daily,top,cfg,progress=print):
    return context_rolling(daily,top,cfg,[name for name,_,_ in CONTEXT_SPECS],'validation',progress)
