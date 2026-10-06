"""Reuse sealed validation forecasts only after proving estimator code equivalence."""
import ast
import re
import pandas as pd
from src.common import ROOT, ROUTE, sha256, validate_run
from M2.models.common import active_variants


def checked_cache(run_id, cfg, settings, daily):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id):
        raise ValueError('Invalid validation cache run')
    folder=ROOT/'M2/artifacts'/run_id
    manifest=validate_run(folder)
    if manifest['config']!=cfg or manifest['settings']!=settings or sha256(ROOT/cfg['source'])!=manifest['source_sha256']:
        raise ValueError('Validation cache source or configuration changed')
    saved=pd.read_csv(folder/'daily_sales.csv',parse_dates=['date'])
    pd.testing.assert_frame_equal(saved,daily.reset_index(drop=True),check_dtype=False,rtol=0,atol=0)
    for name,digest in manifest['implementation_modules_sha256'].items():
        path=ROOT/name
        if sha256(path)==digest:
            continue
        snapshot=ROOT/'M2/artifacts/source_snapshots'/digest/path.name
        if not snapshot.is_file() or sha256(snapshot)!=digest:
            raise ValueError('Cache needs the exact original estimator source')
        before=snapshot.read_text(encoding='utf-8');after=path.read_text(encoding='utf-8')
        if name=='M2/models/LightGBM/model.py':
            repaired=before.replace("end = table['ends'][idx]","label_end = table['ends'][idx]").replace('if end <= origin:','if label_end <= origin:').replace("'head_label_end': end,","'head_label_end': label_end,")
            if repaired!=after:
                raise ValueError('Cached estimator changed beyond the actual-label repair')
        elif name=='M2/models/families.py':
            def functions(source):
                return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(source).body
                        if isinstance(n,ast.FunctionDef) and n.name not in ('run','main')}
            if functions(before)!=functions(after):
                raise ValueError('Cached forecasting/metric/selection functions changed')
        else:
            raise ValueError(f'Cached implementation changed: {name}')
    return folder,{'run_id':run_id,'manifest_sha256':sha256(folder/'manifest.json'),
        'estimator_equivalence_checked':True,'actuals_rebuilt_from_fresh_audit':True,
        'files':{name:digest for name,digest in manifest['files'].items()
                 if name.endswith(('validation_predictions.csv','validation_fit_log.csv'))}}


def validation_frames(folder, groups, cfg, settings, family, target):
    subdir=folder/family/target
    frame=pd.read_csv(subdir/'validation_predictions.csv',parse_dates=['as_of_date','target_date','window_start'])
    log=pd.read_csv(subdir/'validation_fit_log.csv')
    assert frame.split.eq('validation').all() and frame.family.eq(family).all() and frame.target.eq(target).all()
    assert set(frame.model)==set(active_variants(settings,family,target))
    for key,index in frame.groupby(ROUTE).groups.items():
        part=frame.loc[index]
        labels=groups[key] if target=='daily' else groups[key].rolling(7,min_periods=7).sum()
        actual=labels.reindex(part.target_date).to_numpy(copy=True)
        actual[part.target_date.gt(pd.Timestamp(cfg['validation_end'])).to_numpy()]=float('nan')
        frame.loc[index,'actual_qty']=actual
    return frame,log
