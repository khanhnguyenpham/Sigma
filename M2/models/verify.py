"""Independent final metric and seven-day label reconciliation."""
import numpy as np
import pandas as pd
from M2.models.weekly import checked_series

def reconcile_metrics(frame, table, cfg):
    checked = 0
    for row in table.itertuples():
        subset = frame.loc[frame.destination_country.eq(row.destination_country)&frame.carrier.eq(row.carrier)
            &frame.family.eq(row.family)&frame.target.eq(row.target)&frame.model.eq(row.model)
            &frame.split.eq(row.split)&frame.block.eq(row.block)
            &frame.target_date.le(pd.Timestamp(cfg[f'{row.split}_end']))]
        if row.cadence == 'nonoverlapping_7d':
            anchor = pd.Timestamp(cfg[f'{row.split}_start'])-pd.Timedelta(days=1)
            subset = subset.loc[(subset.as_of_date-anchor).dt.days.mod(7).eq(0)]
        y,p = subset.actual_qty.to_numpy(),subset.forecast_qty.to_numpy()
        valid = np.isfinite(y)&np.isfinite(p)
        a,f = y[valid],p[valid]
        e,positive = f-a,a>0
        expected = {'mape_positive_pct':np.mean(np.abs(e[positive])/a[positive])*100 if positive.any() else np.nan,
            'mae':np.mean(np.abs(e)) if len(a) else np.nan,
            'wape_pct':np.abs(e).sum()/a.sum()*100 if a.sum()>0 else np.nan,
            'bias':np.mean(e) if len(a) else np.nan,'coverage':len(a)/len(subset),
            'positive_share':positive.mean() if len(a) else np.nan}
        for field,value in expected.items():
            np.testing.assert_allclose(getattr(row,field),value,rtol=0,atol=1e-8,equal_nan=True)
        assert row.n_expected==len(subset) and row.n_labeled_pairs==np.isfinite(y).sum()
        assert row.n_scored_pairs==len(a) and row.n_positive_pairs==positive.sum() and row.n_zero_pairs==(a==0).sum()
        assert row.unique_target_days==subset.loc[valid,'target_date'].nunique()
        assert bool(row.passes_20_pct)==bool(len(a)==len(subset) and expected['mape_positive_pct']<=cfg['mape_limit_pct'])
        checked += 1
    return checked

def reconcile_labels(frame, daily, cfg):
    groups = {key: group.sales_qty for key, group in checked_series(daily).items()}
    seen = set()
    for row in frame.itertuples():
        key = (row.destination_country, row.carrier, row.model, row.split, row.as_of_date, row.block)
        if key in seen:
            raise AssertionError('Duplicate forecast pair')
        seen.add(key)
        assert row.window_start == row.as_of_date + pd.Timedelta(days=1 + 7 * (row.block - 1))
        assert row.target_date == row.as_of_date + pd.Timedelta(days=7 * row.block)
        assert np.isfinite(row.forecast_qty) and row.forecast_qty >= 0
        if row.split == 'future' or row.target_date > pd.Timestamp(cfg[f'{row.split}_end']):
            assert pd.isna(row.actual_qty)
        else:
            y = groups[(row.destination_country, row.carrier)].loc[row.window_start:row.target_date]
            assert len(y) == 7 and float(y.sum()) == row.actual_qty
    return len(frame)
