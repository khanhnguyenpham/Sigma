"""Rebuild fair aggregate baseline comparisons from approved daily tables.

All compared methods use the exact completed origins of the locked forecast.
This is presentation/evaluation only; no model selection or refitting occurs.
"""
import numpy as np
import pandas as pd

from src.common import ROUTE


def baseline_forecasts(series,origins,window):
    if series.index.has_duplicates or not series.index.is_monotonic_increasing:
        raise ValueError('Daily baseline series must be ordered and unique')
    if not series.index.equals(pd.date_range(series.index.min(),series.index.max(),freq='D')):
        raise ValueError('Missing calendar day')
    return {'Naive':series.reindex(origins).to_numpy(float)*window,
        'MA7':series.rolling(7,min_periods=7).mean().reindex(origins).to_numpy(float)*window,
        'MA28':series.rolling(28,min_periods=28).mean().reindex(origins).to_numpy(float)*window}


def score(actual,predicted):
    actual=np.asarray(actual,float);predicted=np.asarray(predicted,float)
    if len(actual)!=len(predicted) or not len(actual) or not np.isfinite(actual).all() or (actual<0).any():
        raise ValueError('Invalid complete evaluation labels')
    valid=np.isfinite(predicted)&(predicted>=0)
    a=actual[valid];p=predicted[valid];error=p-a;positive=a>0
    mape=float(np.mean(np.abs(error[positive])/a[positive])*100) if positive.any() else np.nan
    return {'mape_positive_pct':mape,'mae':float(np.abs(error).mean()) if len(a) else np.nan,
        'wape_pct':float(np.abs(error).sum()/a.sum()*100) if a.sum()>0 else np.nan,
        'bias':float(error.mean()) if len(a) else np.nan,'n_expected':len(actual),
        'n_scored_pairs':int(valid.sum()),'n_positive_pairs':int(positive.sum()),
        'n_zero_pairs':int((a==0).sum()),'coverage':float(valid.mean()),
        'passes_20_pct':bool(valid.all() and np.isfinite(mape) and mape<=20)}


def compare(daily,forecasts,top):
    if daily.duplicated(ROUTE+['date']).any():raise ValueError('Duplicate daily labels')
    if top.duplicated(ROUTE+['window_days']).any():raise ValueError('Duplicate top route metric')
    groups={key:part.sort_values('date').set_index('date').sales_qty.astype(float)
        for key,part in daily.groupby(ROUTE)}
    output=[]
    for record in top.itertuples():
        route=(record.destination_country,record.carrier);window=int(record.window_days)
        if route not in groups:raise ValueError('Missing baseline route')
        y=groups[route]
        part=forecasts.loc[forecasts.window_days.eq(window)&forecasts.destination_country.eq(route[0])&forecasts.carrier.eq(route[1])]
        if part.duplicated(['as_of_date','horizon_day']).any():raise ValueError('Duplicate allocation day')
        totals=part.groupby('as_of_date').agg(total=('aggregate_total_qty','first'),
            versions=('aggregate_total_qty','nunique'),allocated=('forecast_qty','sum'),days=('horizon_day','size'))
        if not totals.versions.eq(1).all() or not totals.days.eq(window).all():raise ValueError('Incomplete aggregate allocation')
        np.testing.assert_allclose(totals.total,totals.allocated,atol=1e-8,rtol=0)
        # The portable forecast contains locked test and future allocations.
        # A future window without every label is excluded from this comparison.
        eligible=totals.index+pd.Timedelta(days=window)<=y.index.max()
        totals=totals.loc[eligible].sort_index();origins=totals.index
        if len(totals)!=int(record.n_expected):raise ValueError('Comparison does not match locked test origins')
        actual=y.rolling(window,min_periods=window).sum().reindex(origins+pd.Timedelta(days=window)).to_numpy()
        methods={'Đã chọn (khóa validation)':totals.total.to_numpy(),**baseline_forecasts(y,origins,window)}
        for method,values in methods.items():
            metric=score(actual,values)
            if method=='Đã chọn (khóa validation)':
                for name in ['mape_positive_pct','mae','wape_pct','bias','coverage']:
                    np.testing.assert_allclose(metric[name],getattr(record,name),atol=1e-8,rtol=0,equal_nan=True)
            output.append({'destination_country':route[0],'carrier':route[1],'window_days':window,
                'method':method,**metric})
    return pd.DataFrame(output)
