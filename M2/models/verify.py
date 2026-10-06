"""Independent raw-label/metric reconciliation and a local model-family report."""
import argparse
import json
import os
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, validate_run, write_json, write_csv
from M2.models.common import active_variants


def recorded_source(name, digest):
    """Resolve current source, or the exact pre-move bytes for historical runs."""
    current = (ROOT/name).resolve()
    if not current.is_relative_to(ROOT):
        raise ValueError('Recorded source must be local')
    if current.is_file() and sha256(current) == digest:
        return current
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Invalid recorded source digest')
    snapshot = ROOT/'M2/artifacts/source_snapshots'/digest/current.name
    if not snapshot.is_file() or sha256(snapshot) != digest:
        raise ValueError('Recorded implementation changed without an exact historical snapshot')
    return snapshot


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


def reconcile_calibration(log, frame, groups, specs):
    """Recompute weighted-median factors and applied forecasts from causal pairs."""
    heads = log.loc[log.status.eq('calibration')]
    if heads.empty:
        return 0
    teachers = log.loc[log.status.eq('teacher')]
    assert (pd.to_datetime(teachers.max_label_end)<=pd.to_datetime(teachers.teacher_origin)).all()
    pairs = log.loc[log.status.eq('calibration_pair')].copy()
    for name in ('fit_cutoff','teacher_origin','max_label_end','head_label_end'):
        pairs[name] = pd.to_datetime(pairs[name])
    assert (pairs.max_label_end<=pairs.teacher_origin).all()
    assert (pairs.head_label_end<=pairs.fit_cutoff).all()
    assert (pairs.head_label_end==pairs.teacher_origin+pd.to_timedelta(7*pairs.week_block,unit='D')).all()
    for key, part in pairs.groupby(ROUTE):
        expected = groups[key].rolling(7,min_periods=7).sum().reindex(part.head_label_end).to_numpy()
        np.testing.assert_allclose(part.actual_qty,expected,rtol=0,atol=0)
    for row in heads.itertuples():
        cutoff = pd.Timestamp(row.fit_cutoff)
        spec = specs[row.model]
        subset = pairs.loc[pairs.model.eq(row.model)&pairs.destination_country.eq(row.destination_country)
            &pairs.carrier.eq(row.carrier)&pairs.week_block.eq(row.week_block)&pairs.fit_cutoff.eq(cutoff)]
        origins = pd.date_range(cutoff-pd.Timedelta(days=spec['history_days']),cutoff-pd.Timedelta(days=7),freq='7D')
        expected_origins = origins[origins+pd.Timedelta(days=7*int(row.week_block))<=cutoff]
        assert len(subset)==len(expected_origins)==row.nonoverlapping_head_weeks
        assert pd.DatetimeIndex(subset.teacher_origin).sort_values().equals(expected_origins)
        assert pd.Timestamp(row.max_head_label_end)==subset.head_label_end.max()<=cutoff
        predicted, actual = subset.forecast_qty.to_numpy(),subset.actual_qty.to_numpy()
        assert np.isfinite(predicted).all() and (predicted>=0).all()
        keep = (predicted>0)&(actual>0)
        factor = 1.
        if keep.any():
            ratios, weights = actual[keep]/predicted[keep],predicted[keep]/actual[keep]
            if spec['prior_weeks']:
                ratios=np.append(ratios,1.); weights=np.append(weights,spec['prior_weeks']*weights.mean())
            order=np.argsort(ratios,kind='stable')
            factor=float(np.clip(ratios[order][np.searchsorted(np.cumsum(weights[order]),weights.sum()/2)],.5,1.5))
        np.testing.assert_allclose(row.factor,factor,rtol=0,atol=1e-8)
    applied = log.loc[log.status.eq('calibration_applied')].copy()
    applied['as_of_date']=pd.to_datetime(applied.as_of_date)
    applied['fit_cutoff']=pd.to_datetime(applied.fit_cutoff)
    merged = applied.merge(heads[ROUTE+['model','week_block','fit_cutoff','factor']].assign(fit_cutoff=lambda f:pd.to_datetime(f.fit_cutoff)),
        on=ROUTE+['model','week_block','fit_cutoff'],validate='many_to_one',suffixes=('','_head'))
    assert len(merged)==len(applied)
    assert (merged.as_of_date>=merged.fit_cutoff).all() and ((merged.as_of_date-merged.fit_cutoff).dt.days<7).all()
    np.testing.assert_allclose(merged.factor,merged.factor_head,rtol=0,atol=1e-8)
    np.testing.assert_allclose(merged.corrected_forecast_qty,merged.parent_forecast_qty*merged.factor,rtol=0,atol=1e-8)
    matched = frame.loc[frame.model.isin(heads.model.unique())].merge(applied,
        left_on=ROUTE+['model','as_of_date','block'],right_on=ROUTE+['model','as_of_date','week_block'],validate='one_to_one',suffixes=('','_log'))
    assert len(matched)==len(frame.loc[frame.model.isin(heads.model.unique())])
    np.testing.assert_allclose(matched.forecast_qty,matched.corrected_forecast_qty,rtol=0,atol=1e-8)
    return len(heads)


def report(folder, out, manifest, primary):
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache'/'matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary = pd.read_csv(folder/'summary.csv')
    family_names = list(manifest['settings']['models'])
    fig,axes = plt.subplots(1,len(family_names),figsize=(14 if len(family_names)==3 else 4.7*len(family_names),5),sharey=True,squeeze=False)
    axes = axes.ravel()
    labels = {'daily':'Daily quantity','sum_daily':'Sum of daily forecasts','direct_7d':'Direct next7 total'}
    for axis,family in zip(axes,family_names):
        selected = summary.loc[summary.family.eq(family)].set_index('target').reindex(labels)
        values = selected.mean_mape_pct.to_numpy()
        bars = axis.bar(range(3),values,color=['#5684d6','#79b5bc','#eb9c4e'])
        axis.set_xticks(range(3),[labels[t] for t in labels],rotation=20,ha='right',fontsize=9)
        axis.axhline(20,color='#c44848',linestyle='--',linewidth=1)
        axis.set_title(family); axis.grid(axis='y',alpha=.2); axis.set_axisbelow(True)
        for bar,value in zip(bars,values):
            if np.isfinite(value):
                axis.text(bar.get_x()+bar.get_width()/2,value+1,f'{value:.2f}%',ha='center',fontsize=9)
    axes[0].set_ylabel('Mean of per-route positive MAPE (%)')
    fig.suptitle(f'M2: {len(family_names)} families, top10, retrospective test\nDaily and total errors have different targets; sum/direct totals share the same windows',fontsize=12)
    fig.tight_layout(); fig.savefig(out/'comparison.png',dpi=170); plt.close(fig)
    lines = ['# M2 — '+', '.join(family_names),'',
        'Run mới, top 10 theo quantity train; train đến 30/06/2025, validation 01/07–30/09/2025, test 01/10–31/12/2025.',
        'Chọn biến thể từng tuyến bằng validation rồi khóa trước test. Biến thể mỗi họ theo protocol; hai mục tiêu, refit 7 ngày; cửa sổ và tham số riêng ghi trong manifest.',
        '**Test đã được xem ở các thử nghiệm trước: đây là đánh giá hồi cứu. MAPE tổng 7 không thay tiêu chí R05 theo ngày.**','',
        '| Họ | Mục tiêu | MAPE trung bình test | Tuyến ≤20% | Độ phủ thấp nhất |',
        '|---|---|---:|---:|---:|']
    for row in summary.itertuples():
        lines.append(f'| {row.family} | {row.target} | {row.mean_mape_pct:.2f}% | {row.routes_le20}/{row.routes} | {row.minimum_coverage:.0%} |')
    lines += ['', f'![So sánh]({(out/"comparison.png").as_posix()})','',
        'MAPE ngày dùng các cặp h1–7 đủ nhãn; hai phương án tổng dùng cùng cửa sổ D+1…D+7. Bảng có MAE, WAPE, bias, độ phủ và số mẫu; block2 và cadence 7 ngày được báo riêng.',
        'Mô hình ngày được chọn theo lỗi ngày. Tổng cộng từ mô hình ngày giữ nguyên lựa chọn đó, không chọn lại theo lỗi tổng. Vì vậy so sánh này đánh giá hai quy trình sử dụng, không cô lập riêng tác động của kiến trúc.',
        'SARIMA/Prophet trực tiếp dùng S(t)=tổng[t−6,t], dự báo S(D+7) và S(D+14); không cộng đầu ra mô hình ngày.',
        'SARIMA log1p dùng expm1 cho dự báo điểm, chưa thêm hiệu chỉnh bias. Prophet có biến thể bật/tắt mùa vụ năm và cửa sổ riêng; thành phần trend/năm có thể chưa ổn định.',
        'Baseline đối chứng nằm trong run gốc, không tham gia lựa chọn giữa ba họ. Đây là run nghiên cứu top10; chưa cập nhật sản phẩm 46 tuyến hoặc chính sách tồn.', '',
        '## Kết quả từng tuyến (MAPE test %)','',
        '| Tuyến | '+' | '.join(f'{family} {label}' for label in ('ngày','tổng7') for family in family_names)+' |',
        '|---|'+ '---:|'*(2*len(family_names))]
    for key, group in primary.loc[primary.target.isin(['daily','direct_7d'])].groupby(ROUTE,sort=True):
        values = {(r.family,r.target):r.mape_positive_pct for r in group.itertuples()}
        numbers = [values[(family,target)] for target in ('daily','direct_7d') for family in family_names]
        lines.append(f"| {' / '.join(key)} | "+' | '.join(f'{v:.2f}' for v in numbers)+' |')
    lines += ['', '## Mô hình tốt nhất giữa các họ (chọn bằng validation)','',
        '| Tuyến | Mục tiêu | Họ | Biến thể | MAPE validation | MAPE test |','|---|---|---|---|---:|---:|']
    selected = pd.read_csv(folder/'overall_selected_models.csv')
    for row in selected.sort_values(ROUTE+['target']).itertuples():
        matched = primary.loc[primary.destination_country.eq(row.destination_country)&primary.carrier.eq(row.carrier)
                              &primary.target.eq(row.target)&primary.family.eq(row.family)]
        lines.append(f'| {row.destination_country} / {row.carrier} | {row.target} | {row.family} | {row.model} | {row.validation_mape_positive_pct:.2f}% | {matched.iloc[0].mape_positive_pct:.2f}% |')
    if manifest['settings'].get('reference_run'):
        reference=ROOT/'M2/artifacts'/manifest['settings']['reference_run']
        before=pd.read_csv(reference/'summary.csv')
        compared=summary.merge(before,on=['family','target'],suffixes=('_new','_old'),validate='one_to_one')
        lines += ['', '## Trước và sau cải tiến','',
            '| Họ | Mục tiêu | MAPE cũ → mới | Tuyến đạt cũ → mới |','|---|---|---:|---:|']
        for row in compared.itertuples():
            lines.append(f'| {row.family} | {row.target} | {row.mean_mape_pct_old:.2f}% → {row.mean_mape_pct_new:.2f}% | {row.routes_le20_old} → {row.routes_le20_new} |')
        lines += ['', 'Chọn theo validation: kết quả test có thể tăng hoặc giảm. Không đổi lựa chọn sau khi xem test.',
            '', '[Chi tiết từng tuyến trước/sau](before_after_routes.csv). [Độ ổn định tháng 7/8/9 của lựa chọn đã khóa](validation_monthly_selected.csv).']
    lines += ['', '## Thư mục kết quả từng họ','']
    for family in family_names:
        path = (folder/family).as_posix()
        lines.append(f'- [{family}]({path}): `daily/`, `direct_7d/`; validation/test/future predictions, metrics, fit logs, selected_models.')
    lines += ['', 'Run gốc: '+folder.as_posix(), '', 'Đối soát độc lập: `summary.json` trong thư mục báo cáo này.']
    (out/'M2_three_models.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def verify(run_id, output_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+',name) for name in (run_id,output_id)) or run_id==output_id:
        raise ValueError('Invalid or identical run identifiers')
    folder = ROOT/'M2/artifacts'/run_id
    manifest = validate_run(folder)
    cfg,settings = manifest['config'],manifest['settings']
    source = (ROOT/cfg['source']).resolve()
    assert source.is_relative_to(ROOT) and sha256(source)==manifest['source_sha256']
    for name,digest in manifest['implementation_modules_sha256'].items():
        recorded_source(name, digest)
    raw = pd.read_csv(source,usecols=ROUTE+['order_id','order_datetime','order_status','quantity'],dtype=str,keep_default_na=False)
    raw = raw.apply(lambda s:s.str.strip())
    raw = raw.drop_duplicates('order_id').loc[lambda f:f.order_status.isin(cfg['sales_statuses'])]
    raw['quantity'] = pd.to_numeric(raw.quantity)
    raw['date'] = pd.to_datetime(raw.order_datetime,format='mixed',utc=True).dt.tz_convert(None).dt.normalize()
    ranked = raw.loc[raw.date.le(pd.Timestamp(cfg['train_end']))].groupby(ROUTE).quantity.sum().reset_index(name='train_quantity')
    ranked = ranked.sort_values(['train_quantity']+ROUTE,ascending=[False,True,True],kind='stable').head(cfg['top_n']).reset_index(drop=True)
    top = pd.read_csv(folder/'top_routes.csv')
    pd.testing.assert_frame_equal(top[ROUTE+['train_quantity']],ranked,check_dtype=False)
    dates = pd.date_range(cfg['observation_start'],cfg['observation_end'])
    grouped = raw.groupby(ROUTE+['date']).quantity.sum()
    groups = {key:grouped.loc[key].reindex(dates,fill_value=0).astype(float) for key in map(tuple,top[ROUTE].to_numpy())}
    saved = pd.read_csv(folder/'daily_sales.csv',parse_dates=['date'])
    assert len(saved)==len(dates)*cfg['top_n'] and not saved.duplicated(ROUTE+['date']).any()
    for key,frame in saved.groupby(ROUTE):
        np.testing.assert_array_equal(frame.sort_values('date').sales_qty,groups[key])
    pairs,metric_groups,failed_validation,frames,selection_frames = 0,0,0,[],[]
    for family in settings['models']:
        for target in ('daily','direct_7d'):
            subdir = folder/family/target
            selected = pd.read_csv(subdir/'selected_models.csv')
            assert selected.selection_split.eq('validation').all() and selected.selection_cutoff.eq(cfg['validation_end']).all()
            selection_frames.append(selected)
            for split in ('validation','test','future'):
                frame = pd.read_csv(subdir/f'{split}_predictions.csv',parse_dates=['as_of_date','target_date','window_start'])
                assert frame.family.eq(family).all() and frame.target.eq(target).all() and frame.split.eq(split).all()
                assert set(map(tuple,frame[ROUTE].to_numpy()))==set(groups)
                assert not frame.duplicated(ROUTE+['model','as_of_date','horizon_day']).any()
                assert (frame.target_date==frame.as_of_date+pd.to_timedelta(frame.horizon_day,unit='D')).all()
                assert (frame.window_start==frame.target_date-pd.to_timedelta(0 if target=='daily' else 6,unit='D')).all()
                assert (frame.block==np.where(frame.horizon_day<=7,1,2)).all()
                log = pd.read_csv(subdir/f'{split}_fit_log.csv')
                ok = log.loc[log.status.eq('ok')]
                assert (pd.to_datetime(ok.max_label_end)<=pd.to_datetime(ok.fit_cutoff)).all()
                if family=='LightGBM' and target=='direct_7d':
                    reconcile_calibration(log,frame,groups,settings['models'][family])
                for (country,carrier,model),part in frame.groupby(ROUTE+['model']):
                    key = (country,carrier)
                    horizons = list(range(1,15)) if target=='daily' else [7,14]
                    origin_days = pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1),pd.Timestamp(cfg[f'{split}_end'])-pd.Timedelta(days=1)) if split!='future' else pd.DatetimeIndex([pd.Timestamp(cfg['observation_end'])])
                    assert len(part)==len(origin_days)*len(horizons)
                    assert part.as_of_date.nunique()==len(origin_days) and sorted(part.horizon_day.unique())==horizons
                    assert pd.DatetimeIndex(part.as_of_date.unique()).sort_values().equals(origin_days)
                    if split=='validation':
                        assert model in active_variants(settings,family,target)
                    else:
                        assert model==selected.loc[selected.destination_country.eq(country)&selected.carrier.eq(carrier)].iloc[0].model
                    series = groups[key]
                    labels = series if target=='daily' else series.rolling(7,min_periods=7).sum()
                    expected = labels.reindex(part.target_date).to_numpy(copy=True)
                    if split=='future':
                        expected[:]=np.nan
                    else:
                        expected[part.target_date.gt(pd.Timestamp(cfg[f'{split}_end'])).to_numpy()]=np.nan
                    np.testing.assert_allclose(part.actual_qty,expected,rtol=0,atol=0,equal_nan=True)
                    forecasts = part.forecast_qty.to_numpy()
                    assert (forecasts[np.isfinite(forecasts)]>=0).all()
                    if not np.isfinite(forecasts).all():
                        assert split=='validation'
                        failure = log.loc[log.status.eq('failed')&log.destination_country.eq(country)&log.carrier.eq(carrier)&log.model.eq(model)]
                        assert len(failure)>0
                        failed_validation+=1
                if split!='future':
                    table = pd.read_csv(subdir/f'{split}_metrics.csv')
                    assert len(table)==(len(active_variants(settings,family,target)) if split=='validation' else 1)*len(groups)*4
                    assert not table.duplicated(['model']+ROUTE+['block','cadence']).any()
                    metric_groups+=reconcile_metrics(frame,table,cfg)
                    if split=='validation':
                        monthly_path=subdir/'validation_monthly_metrics.csv'
                        if monthly_path.exists():
                            monthly=pd.read_csv(monthly_path)
                            assert len(monthly)==len(table)*len(pd.period_range(cfg['validation_start'],cfg['validation_end'],freq='M'))
                            for month,part in monthly.groupby('month'):
                                period=pd.Period(month,freq='M')
                                scoped=frame.loc[frame.as_of_date.ge(period.start_time-pd.Timedelta(days=1))&frame.as_of_date.lt(period.end_time.normalize())]
                                metric_groups+=reconcile_metrics(scoped,part,{**cfg,'validation_end':min(period.end_time.normalize(),pd.Timestamp(cfg['validation_end']))})
                        for row in selected.itertuples():
                            subset=frame.loc[frame.destination_country.eq(row.destination_country)&frame.carrier.eq(row.carrier)]
                            complete=set(name for name,g in subset.groupby('model') if np.isfinite(g.forecast_qty).all())
                            choices=table.loc[table.destination_country.eq(row.destination_country)&table.carrier.eq(row.carrier)
                                &table.block.eq(1)&table.cadence.eq('daily_origins')&table.model.isin(complete)
                                &table.coverage.eq(1)&table.mape_positive_pct.notna()].sort_values(['mape_positive_pct','mae','model'])
                            assert row.model==choices.iloc[0].model
                            np.testing.assert_allclose(row.validation_mape_positive_pct,choices.iloc[0].mape_positive_pct,rtol=0,atol=1e-8)
                if split=='test':
                    frames.append(frame)
                pairs+=len(frame)
    all_selection=pd.concat(selection_frames,ignore_index=True)
    overall=pd.read_csv(folder/'overall_selected_models.csv')
    expected_selection=all_selection.sort_values(['validation_mape_positive_pct','validation_mae','family','model']).drop_duplicates(ROUTE+['target'])
    pd.testing.assert_frame_equal(overall.sort_values(ROUTE+['target']).reset_index(drop=True),expected_selection.sort_values(ROUTE+['target']).reset_index(drop=True),check_dtype=False)
    lock=json.loads((folder/'selection_lock.json').read_text())
    assert lock['locked_before_test'] is True
    for name,digest in lock['files'].items():
        assert sha256(folder/name)==digest==manifest['selection_hashes'][name]
    tests=pd.concat(frames,ignore_index=True)
    overall_predictions=pd.read_csv(folder/'overall_test_predictions.csv',parse_dates=['as_of_date','target_date','window_start'])
    expected_overall=tests.merge(overall[ROUTE+['family','target','model']],on=ROUTE+['family','target','model'],validate='many_to_one')
    keys=ROUTE+['family','target','model','as_of_date','horizon_day']
    pd.testing.assert_frame_equal(overall_predictions.sort_values(keys).reset_index(drop=True),expected_overall.sort_values(keys).reset_index(drop=True),check_dtype=False,rtol=0,atol=1e-8)
    metric_groups+=reconcile_metrics(overall_predictions,pd.read_csv(folder/'overall_test_metrics.csv'),cfg)
    sums=pd.read_csv(folder/'summed_daily_predictions.csv',parse_dates=['as_of_date','target_date','window_start'])
    daily=tests.loc[tests.target.eq('daily')]
    for row in sums.itertuples():
        part=daily.loc[daily.family.eq(row.family)&daily.destination_country.eq(row.destination_country)
            &daily.carrier.eq(row.carrier)&daily.as_of_date.eq(row.as_of_date)&daily.block.eq(row.block)]
        assert len(part)==7 and part.horizon_day.nunique()==7
        np.testing.assert_allclose(row.forecast_qty,part.forecast_qty.sum(),rtol=0,atol=1e-8)
        np.testing.assert_allclose(row.actual_qty,part.actual_qty.sum(min_count=7),rtol=0,atol=1e-8,equal_nan=True)
        assert row.window_start==part.target_date.min() and row.target_date==part.target_date.max()
    comparison=pd.read_csv(folder/'comparison_metrics.csv')
    metric_groups+=reconcile_metrics(pd.concat([tests,sums],ignore_index=True),comparison,cfg)
    baseline=pd.read_csv(folder/'baseline_predictions.csv',parse_dates=['as_of_date','target_date','window_start'])
    for key,part in baseline.groupby([*ROUTE,'as_of_date','target','model']):
        country,carrier,origin,target,model=key
        y=groups[(country,carrier)].loc[:origin]
        if target=='daily':
            if model=='naive':
                values=np.repeat(y.iloc[-1],len(part))
            elif model=='ma7':
                values=np.repeat(y.iloc[-7:].mean(),len(part))
            else:
                values=y.iloc[-7:].to_numpy()[(part.horizon_day.to_numpy()-1)%7]
        else:
            values=np.repeat(y.iloc[-int(model.removeprefix('mean')):].mean()*7,len(part))
        np.testing.assert_allclose(part.forecast_qty,values,rtol=0,atol=1e-8)
    for key,part in baseline.groupby(ROUTE+['target','split']):
        country,carrier,target,split=key
        series=groups[(country,carrier)]
        labels=series if target=='daily' else series.rolling(7,min_periods=7).sum()
        expected=labels.reindex(part.target_date).to_numpy(copy=True)
        expected[part.target_date.gt(pd.Timestamp(cfg[f'{split}_end'])).to_numpy()]=np.nan
        np.testing.assert_allclose(part.actual_qty,expected,rtol=0,atol=0,equal_nan=True)
    metric_groups+=reconcile_metrics(baseline,pd.read_csv(folder/'baseline_metrics.csv'),cfg)
    primary=comparison.loc[comparison.block.eq(1)&comparison.cadence.eq('daily_origins')]
    expected_summary=primary.groupby(['family','target'],sort=True).agg(mean_mape_pct=('mape_positive_pct','mean'),
        routes_le20=('passes_20_pct','sum'),routes=('carrier','size'),minimum_coverage=('coverage','min')).reset_index()
    pd.testing.assert_frame_equal(pd.read_csv(folder/'summary.csv'),expected_summary,check_dtype=False,rtol=0,atol=1e-8)
    out=ROOT/'M2/reports'/output_id
    out.mkdir(exist_ok=False)
    write_csv(out/'route_comparison.csv',primary)
    monthly_parts=[]
    for family in settings['models']:
        for target in ('daily','direct_7d'):
            subdir=folder/family/target
            if (subdir/'validation_monthly_metrics.csv').exists():
                part=pd.read_csv(subdir/'validation_monthly_metrics.csv')
                choices=pd.read_csv(subdir/'selected_models.csv')
                monthly_parts.append(part.merge(choices[ROUTE+['model']],on=ROUTE+['model'],validate='many_to_one'))
    if monthly_parts:
        write_csv(out/'validation_monthly_selected.csv',pd.concat(monthly_parts,ignore_index=True))
    reference_run=settings.get('reference_run')
    if reference_run:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',reference_run):
            raise ValueError('Invalid reference run')
        reference=ROOT/'M2/artifacts'/reference_run
        original=validate_run(reference)
        assert original['source_sha256']==manifest['source_sha256'] and original['config']==cfg
        for family,variants in original['settings']['models'].items():
            assert all(settings['models'][family].get(name)==spec for name,spec in variants.items())
        before=pd.read_csv(reference/'comparison_metrics.csv')
        before=before.loc[before.block.eq(1)&before.cadence.eq('daily_origins')]
        compared=primary.merge(before,on=ROUTE+['family','target','split','block','cadence'],suffixes=('_new','_old'),validate='one_to_one')
        compared['mape_delta_pct_points']=compared.mape_positive_pct_new-compared.mape_positive_pct_old
        write_csv(out/'before_after_routes.csv',compared)
    report(folder,out,manifest,primary)
    validate_run(folder)
    assert sha256(source)==manifest['source_sha256']
    result={'status':'verified','run_id':run_id,'run_manifest_sha256':sha256(folder/'manifest.json'),
        'raw_quantity_pairs_checked':pairs,'metric_groups_checked':metric_groups,
        'failed_validation_candidates':failed_validation,'raw_unchanged':True,'selection_locked':True,
        'future_actuals_missing':True,'test_limit':manifest['test_limit'],
        'files':{path.name:sha256(path) for path in out.iterdir() if path.is_file()}}
    write_json(out/'summary.json',result)
    print(json.dumps(result),flush=True)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--output-id',required=True)
    args=parser.parse_args()
    verify(args.run_id,args.output_id)
