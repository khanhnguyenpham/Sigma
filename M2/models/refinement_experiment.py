"""Bounded validation refinement around the preceding validation winner."""
import argparse
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, new_manifest, seal_manifest, validate_run
from M2.models.registry import load_settings, implementation_hashes
from M2.models.focus_experiment import FOCUS, phase, candidates, verify_heads, combine_frozen, load_predictions
from M2.models.calendar_experiment import reconcile_labels
from M2.models.families import metrics, select, monthly_metrics
from M2.models.verify import reconcile_metrics


def run(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id): raise ValueError('Invalid run ID')
    path=ROOT/'data/configs/m2-refinement.json'; experiment=json.loads(path.read_text(encoding='utf-8'))
    cfg=read_config(experiment['base_config']); settings=load_settings(ROOT/experiment['model_config'])
    old=ROOT/'M2/artifacts'/experiment['reference_run']; validate_run(old)
    previous=ROOT/'M2/artifacts'/experiment['previous_experiment']; prior_manifest=validate_run(previous)
    hierarchy=ROOT/'M2/artifacts/m2_hierarchy_20261011'; hierarchy_manifest=validate_run(hierarchy)
    source=ROOT/cfg['source']; assert sha256(source)==prior_manifest['source_sha256']
    protected={**hierarchy_manifest['protected_before'],
        **{p.relative_to(ROOT).as_posix():sha256(p) for p in hierarchy.rglob('*') if p.is_file()}}
    out=ROOT/'M2/artifacts'/run_id; out.mkdir(parents=True,exist_ok=False)
    manifest=new_manifest(cfg,source,run_id)
    manifest.update(experiment=experiment,settings=settings,candidates=candidates(experiment),config_sha256=sha256(path),
        implementation_modules_sha256=implementation_hashes(),protected_before=protected,
        daily_lineage={'path':str(previous/'daily_sales.csv'),'sha256':sha256(previous/'daily_sales.csv')},production_modified=False)
    write_json(out/'protocol.json',manifest); write_json(out/'manifest.json',manifest)
    daily=pd.read_csv(previous/'daily_sales.csv',parse_dates=['date'])
    top=pd.read_csv(old/'top_routes.csv')
    focused=daily.merge(top[ROUTE],on=ROUTE,validate='many_to_one')
    checks={}; history=[]
    print('Registered 24 refinement candidates; historical folds then validation',flush=True)
    for start,end in experiment['historical_folds']:
        # All populations are frozen using the preceding historical run's already causal population.
        fold={**cfg,'validation_start':start,'validation_end':end}
        cutoff=pd.Timestamp(start)-pd.Timedelta(days=1)
        population=daily.loc[daily.date.le(cutoff)].groupby(ROUTE).sales_qty.sum().sort_values(ascending=False).head(10).reset_index()[ROUTE]
        subset=daily.loc[daily.date.le(end)].merge(population,on=ROUTE,validate='many_to_one')
        pred,log=phase(subset,fold,settings,experiment,'validation')
        table=metrics(pred,fold); table['fold_start']=start; history.append(table)
        write_csv(out/f'history_{start}_predictions.csv',pred); write_csv(out/f'history_{start}_fit_log.csv',log)
        checks[f'history_{start}_labels']=reconcile_labels(pred,subset,fold)
        checks[f'history_{start}_heads']=verify_heads(log,experiment,subset)
    write_csv(out/'historical_metrics.csv',pd.concat(history,ignore_index=True))
    validation,log=phase(focused,cfg,settings,experiment,'validation'); table=metrics(validation,cfg)
    for name,frame in [('validation_predictions',validation),('validation_metrics',table),('validation_fit_log',log),
        ('validation_monthly_metrics',monthly_metrics(validation,cfg))]: write_csv(out/f'{name}.csv',frame)
    checks['validation_labels']=reconcile_labels(validation,focused,cfg); checks['validation_metrics']=reconcile_metrics(validation,table,cfg)
    checks['validation_heads']=verify_heads(log,experiment,focused)
    prior=load_predictions(previous/'validation_predictions.csv'); prior=prior.loc[prior.model.eq('focus_scale56_mul56p4')]
    control=validation.loc[validation.model.eq('tune56_mul56p4')]
    pairs=control.merge(prior,on=ROUTE+['as_of_date','block'],suffixes=('','_old'),validate='one_to_one')
    assert len(pairs)==len(control)==len(prior)
    np.testing.assert_allclose(pairs.forecast_qty,pairs.forecast_qty_old,atol=1e-8,rtol=0)
    checks['control_max_difference']=float((pairs.forecast_qty-pairs.forecast_qty_old).abs().max())
    selected=select(table,validation,cfg).iloc[0]
    prior_score=prior_manifest['result']['validation_selected_mape_pct']
    improved=bool(selected.validation_mape_positive_pct<prior_score-1e-8)
    locked=pd.read_csv(old/'overall_selected_models.csv',float_precision='round_trip'); locked=locked.loc[locked.target.eq('direct_7d')].copy()
    if improved:
        locked.loc[locked.carrier.eq(FOCUS[1]),['family','model','validation_mape_positive_pct','validation_mae']]=[
            selected.family,selected.model,selected.validation_mape_positive_pct,selected.validation_mae]
    write_csv(out/'selected_models.csv',locked)
    lock={'selected_model':selected.model,'locked_at_utc':datetime.now(timezone.utc).isoformat(),
        'selected_sha256':sha256(out/'selected_models.csv'),'test_scored_if_improved':improved,'nine_routes_frozen':True}
    write_json(out/'selection_lock.json',lock)
    result={'validation_improved':improved,'selected_model':selected.model,'validation_previous_mape_pct':prior_score,
        'validation_selected_mape_pct':selected.validation_mape_positive_pct,'test_scored':False,'goal_achieved':False}
    if improved:
        print(f'Locked {selected.model}; one retrospective test',flush=True)
        test,test_log=phase(focused,cfg,settings,experiment,'test',[selected.model])
        original=load_predictions(old/'overall_test_predictions.csv'); original=original.loc[original.target.eq('direct_7d')]
        combined=combine_frozen(original,test); scored=metrics(combined,cfg)
        for name,frame in [('focus_test_predictions',test),('test_fit_log',test_log),('overall_test_predictions',combined),('overall_test_metrics',scored)]:
            write_csv(out/f'{name}.csv',frame)
        checks['test_labels']=reconcile_labels(combined,focused,cfg); checks['test_metrics']=reconcile_metrics(combined,scored,cfg)
        checks['test_heads']=verify_heads(test_log,experiment,focused)
        saved=load_predictions(out/'overall_test_predictions.csv')
        pd.testing.assert_frame_equal(saved.loc[~saved.carrier.eq(FOCUS[1])].reset_index(drop=True),
            original.loc[~original.carrier.eq(FOCUS[1])].reset_index(drop=True),check_exact=True)
        checks['other_nine_predictions_exact']=len(saved.loc[~saved.carrier.eq(FOCUS[1])])
        primary=scored.loc[scored.block.eq(1)&scored.cadence.eq('daily_origins')]
        baseline=metrics(original,cfg); baseline=baseline.loc[baseline.block.eq(1)&baseline.cadence.eq('daily_origins')]
        write_csv(out/'before_after_routes.csv',primary.merge(baseline,on=ROUTE,suffixes=('_new','_old'),validate='one_to_one'))
        row=primary.loc[primary.carrier.eq(FOCUS[1])].iloc[0]
        result.update(test_scored=True,focus_test_mape_pct=row.mape_positive_pct,reference_focus_test_mape_pct=float(baseline.loc[baseline.carrier.eq(FOCUS[1]),'mape_positive_pct'].iloc[0]),
            goal_achieved=bool(row.mape_positive_pct<20 and row.coverage==1),top10_passes_20_pct=int(primary.passes_20_pct.sum()))
        future,future_log=phase(focused,cfg,settings,experiment,'future',[selected.model])
        write_csv(out/'focus_future_predictions.csv',future); write_csv(out/'future_fit_log.csv',future_log)
        checks['future_labels']=reconcile_labels(future,focused,cfg)
    for name,digest in protected.items(): assert sha256(ROOT/name)==digest,name
    assert sha256(source)==manifest['source_sha256'] and sha256(out/'selected_models.csv')==lock['selected_sha256']
    checks.update(status='passed',protected_files_unchanged=len(protected),source_hash_unchanged=True,selection_lock_unchanged=True)
    write_json(out/'verification.json',checks); write_json(out/'result.json',result)
    primary=table.loc[table.block.eq(1)&table.cadence.eq('daily_origins')].sort_values(['mape_positive_pct','mae','model'])
    rows='\n'.join(f'| {r.model} | {r.mape_positive_pct:.6f} | {r.mae:.6f} |' for r in primary.itertuples())
    (out/'README.md').write_text(f'''# Tinh chỉnh cửa sổ chuẩn hóa — {run_id}

Lượt3 nghiên cứu tuần tự hồi cứu,24 cấu hình đăng ký trước fit. Cửa sổ được chọn quanh56 ngày vì thắng validation lượt1; không chọn theo test. Đủ coverage hai block, không thay nhãn/split/top10/R05 ngày hoặc chín tuyến cũ. Không đổi dashboard/báo cáo đã khóa.

Kết quả `{json.dumps(result,ensure_ascii=False)}`

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
