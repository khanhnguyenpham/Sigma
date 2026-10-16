"""Country-total forecasts allocated by past route shares; sequential research."""
import argparse
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, new_manifest, seal_manifest, validate_run
from M2.models.registry import load_settings, implementation_hashes
from M2.models.focus_experiment import FOCUS, phase, candidates, verify_heads, combine_frozen, load_predictions
from M2.models.calendar_experiment import protected_files, reconcile_labels
from M2.models.families import metrics, select, monthly_metrics
from M2.models.verify import reconcile_metrics


def country_daily(daily):
    result=daily.loc[daily.destination_country.eq(FOCUS[0])].groupby('date')[['sales_qty','order_count']].sum().reset_index()
    result['destination_country'],result['carrier']=FOCUS
    return result


def allocate(country_predictions,daily,windows):
    country=country_daily(daily).set_index('date').sales_qty
    route=daily.loc[daily.destination_country.eq(FOCUS[0])&daily.carrier.eq(FOCUS[1])].set_index('date').sales_qty
    actual=route.rolling(7).sum()
    frames=[]
    for window in windows:
        share=route.rolling(window,min_periods=window).sum()/country.rolling(window,min_periods=window).sum().replace(0,np.nan)
        frame=country_predictions.copy()
        weights=share.reindex(frame.as_of_date).to_numpy()
        if not np.isfinite(weights).all() or (weights<0).any() or (weights>1).any():
            raise ValueError('Missing or invalid past route share')
        frame['forecast_qty']*=weights
        frame['actual_qty']=np.where(frame.actual_qty.notna(),actual.reindex(frame.target_date),np.nan)
        frame['model']=frame.model+f'_share{window}'
        frame['family']='FocusHierarchy'
        frames.append(frame)
    return pd.concat(frames,ignore_index=True)


def assemble(predictions,benchmark,experiment):
    """Fixed blends with the winner locked in the preceding validation experiment."""
    frames=[predictions,benchmark]
    keys=ROUTE+['as_of_date','block']
    for parent in experiment['blend_country_parents']:
        for head in experiment['heads']:
            model=f'{parent}_{head}_share{experiment["blend_share_days"]}'
            left=predictions.loc[predictions.model.eq(model)]
            merged=left.merge(benchmark[keys+['forecast_qty']],on=keys,suffixes=('','_base'),validate='one_to_one')
            assert len(merged)==len(left)==len(benchmark)
            w=experiment['blend_weight']
            merged['forecast_qty']=w*merged.forecast_qty+(1-w)*merged.forecast_qty_base
            merged['model']=model+'_blend50'
            frames.append(merged[left.columns])
    return pd.concat(frames,ignore_index=True)


def blend_selected(frame,benchmark,model):
    keys=ROUTE+['as_of_date','block']
    joined=frame.merge(benchmark[keys+['forecast_qty']],on=keys,suffixes=('','_base'),validate='one_to_one')
    assert len(joined)==len(frame)==len(benchmark)
    joined['forecast_qty']=.5*joined.forecast_qty+.5*joined.forecast_qty_base
    joined['model']=model
    return joined[frame.columns]


def run(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id): raise ValueError('Invalid run ID')
    path=ROOT/'data/configs/m2-hierarchy.json'; experiment=json.loads(path.read_text(encoding='utf-8'))
    cfg=read_config(experiment['base_config']); settings=load_settings(ROOT/experiment['model_config'])
    old=ROOT/'M2/artifacts'/experiment['reference_run']; validate_run(old)
    previous=ROOT/'M2/artifacts'/experiment['previous_experiment']; previous_manifest=validate_run(previous)
    assert not previous_manifest['result']['goal_achieved']
    source=ROOT/cfg['source']; assert sha256(source)==previous_manifest['source_sha256']
    protected={**protected_files(old),**previous_manifest['protected_before'],
        **{p.relative_to(ROOT).as_posix():sha256(p) for p in previous.rglob('*') if p.is_file()}}
    out=ROOT/'M2/artifacts'/run_id; out.mkdir(parents=True,exist_ok=False)
    manifest=new_manifest(cfg,source,run_id)
    manifest.update(experiment=experiment,settings=settings,config_sha256=sha256(path),
        implementation_modules_sha256=implementation_hashes(),protected_before=protected,
        daily_lineage={'path':str(previous/'daily_sales.csv'),'sha256':sha256(previous/'daily_sales.csv'),
            'note':'reuse sealed fresh audit from preceding experiment; current raw hash rechecked'},production_modified=False)
    write_json(out/'protocol.json',manifest); write_json(out/'manifest.json',manifest)
    daily=pd.read_csv(previous/'daily_sales.csv',parse_dates=['date'])
    assert daily.sales_qty.sum()==118296
    previous_choice=previous_manifest['result']['selected_model']
    print('Registered 44 candidates: country totals, past shares and fixed blends',flush=True)
    checks={}; histories=[]
    for start,end in experiment['historical_folds']:
        fold={**cfg,'validation_start':start,'validation_end':end}
        subset=daily.loc[daily.date.le(end)]
        country=country_daily(subset)
        pred,log=phase(country,fold,settings,experiment,'validation')
        allocated=allocate(pred,subset,experiment['share_days'])
        base=load_predictions(previous/f'history_{start}_predictions.csv')
        baseline=base.loc[base.model.eq(previous_choice)]
        result=assemble(allocated,baseline,experiment)
        original=base.loc[base.model.eq('focus_control_mul56p4')]
        result=pd.concat([result,original],ignore_index=True)
        table=metrics(result,fold); table['fold_start']=start; histories.append(table)
        write_csv(out/f'history_{start}_predictions.csv',result)
        write_csv(out/f'history_{start}_country_fit_log.csv',log)
        checks[f'history_{start}_labels']=reconcile_labels(result,subset,fold)
        checks[f'history_{start}_heads']=verify_heads(log,experiment,country)
    write_csv(out/'historical_metrics.csv',pd.concat(histories,ignore_index=True))
    country=country_daily(daily)
    raw,log=phase(country,cfg,settings,experiment,'validation')
    allocated=allocate(raw,daily,experiment['share_days'])
    prior=load_predictions(previous/'validation_predictions.csv')
    benchmark=prior.loc[prior.model.eq(previous_choice)]
    validation=assemble(allocated,benchmark,experiment)
    validation=pd.concat([validation,prior.loc[prior.model.eq('focus_control_mul56p4')]],ignore_index=True)
    assert validation.model.nunique()==44
    table=metrics(validation,cfg)
    for name,frame in [('validation_predictions',validation),('validation_metrics',table),('country_validation_predictions',raw),
        ('validation_country_fit_log',log),('validation_monthly_metrics',monthly_metrics(validation,cfg))]: write_csv(out/f'{name}.csv',frame)
    checks['validation_labels']=reconcile_labels(validation,daily,cfg)
    checks['validation_metrics']=reconcile_metrics(validation,table,cfg)
    checks['validation_heads']=verify_heads(log,experiment,country)
    selected=select(table,validation,cfg).iloc[0]
    previous_score=previous_manifest['result']['validation_selected_mape_pct']
    improved=bool(selected.validation_mape_positive_pct<previous_score-1e-8)
    locked=pd.read_csv(old/'overall_selected_models.csv',float_precision='round_trip')
    locked=locked.loc[locked.target.eq('direct_7d')].copy()
    if improved:
        locked.loc[locked.carrier.eq(FOCUS[1]),['family','model','validation_mape_positive_pct','validation_mae']]=[
            selected.family,selected.model,selected.validation_mape_positive_pct,selected.validation_mae]
    write_csv(out/'selected_models.csv',locked)
    lock={'selected_model':selected.model,'locked_at_utc':datetime.now(timezone.utc).isoformat(),
        'selected_sha256':sha256(out/'selected_models.csv'),'test_scored_if_improved':improved,'nine_routes_frozen':True}
    write_json(out/'selection_lock.json',lock)
    result={'validation_improved':improved,'selected_model':selected.model,'validation_previous_mape_pct':previous_score,
        'validation_selected_mape_pct':selected.validation_mape_positive_pct,'test_scored':False,'goal_achieved':False}
    if improved:
        model=selected.model; print(f'Locked {model}; one retrospective test',flush=True)
        # Only the already locked country estimator is fit on test; no competing test candidates.
        base_model=model.split('_share')[0]
        share_days=int(model.split('_share')[1].split('_')[0])
        raw,test_log=phase(country,cfg,settings,experiment,'test',[base_model])
        test=allocate(raw,daily,[share_days])
        if model.endswith('_blend50'):
            base=load_predictions(previous/'focus_test_predictions.csv')
            test=blend_selected(test,base,model)
        reference=load_predictions(old/'overall_test_predictions.csv'); reference=reference.loc[reference.target.eq('direct_7d')]
        combined=combine_frozen(reference,test); scored=metrics(combined,cfg)
        for name,frame in [('focus_test_predictions',test),('overall_test_predictions',combined),('overall_test_metrics',scored),
            ('test_country_fit_log',test_log),('country_test_predictions',raw)]: write_csv(out/f'{name}.csv',frame)
        checks['test_labels']=reconcile_labels(combined,daily,cfg); checks['test_metrics']=reconcile_metrics(combined,scored,cfg)
        checks['test_heads']=verify_heads(test_log,experiment,country)
        saved=load_predictions(out/'overall_test_predictions.csv')
        pd.testing.assert_frame_equal(saved.loc[~saved.carrier.eq(FOCUS[1])].reset_index(drop=True),
            reference.loc[~reference.carrier.eq(FOCUS[1])].reset_index(drop=True),check_exact=True)
        checks['other_nine_predictions_exact']=len(saved.loc[~saved.carrier.eq(FOCUS[1])])
        primary=scored.loc[scored.block.eq(1)&scored.cadence.eq('daily_origins')]
        original=metrics(reference,cfg); original=original.loc[original.block.eq(1)&original.cadence.eq('daily_origins')]
        write_csv(out/'before_after_routes.csv',primary.merge(original,on=ROUTE,suffixes=('_new','_old'),validate='one_to_one'))
        row=primary.loc[primary.carrier.eq(FOCUS[1])].iloc[0]
        result.update(test_scored=True,focus_test_mape_pct=row.mape_positive_pct,reference_focus_test_mape_pct=float(original.loc[original.carrier.eq(FOCUS[1]),'mape_positive_pct'].iloc[0]),
            goal_achieved=bool(row.mape_positive_pct<20 and row.coverage==1),top10_passes_20_pct=int(primary.passes_20_pct.sum()))
        raw,future_log=phase(country,cfg,settings,experiment,'future',[base_model]); future=allocate(raw,daily,[share_days])
        if model.endswith('_blend50'):
            base=load_predictions(previous/'focus_future_predictions.csv')
            future=blend_selected(future,base,model)
        write_csv(out/'focus_future_predictions.csv',future); write_csv(out/'future_country_fit_log.csv',future_log)
        checks['future_labels']=reconcile_labels(future,daily,cfg)
    assert sha256(out/'selected_models.csv')==lock['selected_sha256'] and sha256(source)==manifest['source_sha256']
    for name,digest in protected.items(): assert sha256(ROOT/name)==digest,name
    checks.update(status='passed',protected_files_unchanged=len(protected),source_hash_unchanged=True,selection_lock_unchanged=True)
    write_json(out/'verification.json',checks); write_json(out/'result.json',result)
    primary=table.loc[table.block.eq(1)&table.cadence.eq('daily_origins')].sort_values(['mape_positive_pct','mae','model'])
    rows='\n'.join(f'| {r.model} | {r.mape_positive_pct:.6f} | {r.mae:.6f} |' for r in primary.itertuples())
    (out/'README.md').write_text(f'''# Phân rã tổng Hàn Quốc — {run_id}

Nghiên cứu tuần tự hồi cứu sau lượt focus. Test đã xem nhiều lần; không là holdout độc lập. Không chọn/tinh chỉnh theo test, không đổi R05 ngày/R07/T14 hoặc dashboard/bộ báo cáo đã khóa.

Kết quả `{json.dumps(result,ensure_ascii=False)}`

44 ứng viên đăng ký trước fit. Tổng bán Hàn Quốc được học bằng cùng target7 ngày, sau đó nhân tỷ trọng LG U+28/56/90 ngày đã biết tại origin. Country target/teacher logs là tổng quốc gia; actual/metric đầu ra là quantity của LG U+. Blend50% với lựa chọn đã khóa ở lượt trước. Phải thắng validation của lượt trước mới chấm một ứng viên test.

[Protocol](protocol.json), [khóa](selection_lock.json), [kiểm chứng](verification.json), [metric](validation_metrics.csv), [lịch sử](historical_metrics.csv).

| Ứng viên | MAPE validation % | MAE |
|---|---:|---:|
{rows}
''',encoding='utf-8')
    manifest.update(status='complete',result=result,finished_at_utc=datetime.now(timezone.utc).isoformat()); seal_manifest(out,manifest)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--run-id',required=True)
    run(parser.parse_args().run_id)
