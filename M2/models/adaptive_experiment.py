"""Bounded LG U+ residual, age-weighting and refit experiment; frozen other routes."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, new_manifest, seal_manifest, validate_run
from src.data import route_top
from sigma.forecasting.weekly import fit, inputs, predict_batch, checked_series, CATEGORIES
from sigma.forecasting.boosting import estimator_count
from sigma.forecasting.calibration import relative_factor
from M2.models.common import effective_settings, prediction_rows, COLUMNS
from M2.models.registry import load_settings, implementation_hashes
from M2.models.focus_experiment import (FOCUS, candidates, prepare_parent, residual_parameters,
    transform, verify_heads, combine_frozen, load_predictions)
from M2.models.calendar_experiment import reconcile_labels
from M2.models.families import metrics, select, monthly_metrics
from M2.models.verify import reconcile_metrics


def weighted_batch(prepared, cutoff, spec, settings):
    """Retain the baseline sample population and total weight; change only relative age weights."""
    xs, ys, ends = [], [], []
    for table in prepared.values():
        mask = ((table['ends'] <= cutoff)
                & (table['ends'] >= cutoff-pd.Timedelta(days=settings['training_window_days']-1)))
        idx = np.flatnonzero(mask)
        if len(idx):
            xs.append(inputs(table, spec, idx))
            ys.append(table['y'][idx]/table['scale'][idx])
            ends.extend(table['ends'][idx])
    if not xs:
        raise ValueError('No completed labels')
    y = np.concatenate(ys)
    if not np.isfinite(y).all() or (y < 0).any():
        raise ValueError('Invalid training labels')
    age = (cutoff-pd.DatetimeIndex(ends)).days.to_numpy(float)
    half = spec['half_life_days']
    if half <= 0 or not np.isfinite(half) or (age < 0).any():
        raise ValueError('Invalid half life or future label')
    base = np.divide(1., y, out=np.zeros_like(y), where=y > 0)
    weight = base*np.exp2(-age/half)
    if weight.sum() > 0:
        weight *= base.sum()/weight.sum()
    log = {'max_label_end': max(ends), 'min_label_end': min(ends), 'training_pairs': len(y),
           'half_life_days': half, 'min_label_age_days': age.min(), 'max_label_age_days': age.max(),
           'base_weight_sum': base.sum(), 'weight_sum': weight.sum(),
           'effective_sample_size': weight.sum()**2/np.square(weight).sum() if weight.sum() else 0.,
           'weight_sha256': hashlib.sha256(weight.astype('<f8').tobytes()).hexdigest()}
    return pd.concat(xs, ignore_index=True), y, weight, log


def fit_age(prepared, cutoff, spec, cfg, settings):
    if not spec.get('half_life_days'):
        return fit(prepared, cutoff, spec, cfg, settings)
    x, y, weight, log = weighted_batch(prepared, cutoff, spec, settings)
    if not np.any(y > 0):
        return fit(prepared, cutoff, spec, cfg, settings)
    model = LGBMRegressor(objective=spec['objective'], num_leaves=spec['leaves'],
        n_estimators=estimator_count(spec, settings), learning_rate=settings['learning_rate'],
        min_child_samples=settings['min_child_samples'], reg_lambda=settings['reg_lambda'],
        n_jobs=cfg['lightgbm_threads'], random_state=cfg['seed'], deterministic=True,
        force_col_wise=True, verbosity=-1)
    model.fit(x, y, sample_weight=weight, categorical_feature=CATEGORIES)
    return model, log


def phase(daily, cfg, settings, experiment, split, wanted=None):
    specs = candidates(experiment)
    wanted = list(specs) if wanted is None else list(wanted)
    groups = {key: part.sales_qty.astype(float) for key, part in checked_series(daily).items()}
    end = pd.Timestamp(cfg[f'{split}_end']) if split != 'future' else daily.date.max()
    origins = (pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1), end-pd.Timedelta(days=1))
               if split != 'future' else [end])
    rows, logs = [], []
    base = settings['models']['LightGBM']['lgbm_annual_ratio7']
    for parent, changes in experiment['parents'].items():
        heads = {name: specs[name] for name in wanted if specs[name]['parent'] == parent}
        if not heads:
            continue
        prepared = prepare_parent(daily, settings, changes)
        spec = {'kind': 'lgbm', 'units': 'ratio', **base, **changes}
        effective = effective_settings(settings, changes)
        interval = changes.get('refit_days', settings['refit_days'])
        if type(interval) is not int or interval < 1:
            raise ValueError('Invalid refit cadence')
        fits, predictions = {}, {}
        def teacher(origin):
            if origin not in fits:
                fits[origin] = fit_age(prepared, origin, spec, cfg, effective)
                logs.append({'status': 'fit', 'parent': parent, 'fit_cutoff': origin, **fits[origin][1]})
            return fits[origin][0]
        def prediction(origin):
            if origin not in predictions:
                predictions[origin] = predict_batch(teacher(origin), prepared, origin, spec)
            return predictions[origin]
        parameters = {}
        for i, origin in enumerate(origins):
            if i % interval == 0:
                model, cutoff = teacher(origin), origin
                for name, head in heads.items():
                    if head['kind'] == 'identity':
                        continue
                    for block in (1, 2):
                        p, y, ends = [], [], []
                        table = prepared[(FOCUS, block)]
                        for past in pd.date_range(origin-pd.Timedelta(days=head['history_days']), origin-pd.Timedelta(days=7), freq='7D'):
                            idx = np.flatnonzero(table['origins'] == past)
                            if len(idx) != 1:
                                raise ValueError('Missing teacher origin')
                            idx = idx[0]; finish = table['ends'][idx]
                            if finish > origin:
                                continue
                            value, actual = prediction(past)[(FOCUS, block)], table['y'][idx]
                            p.append(value); y.append(actual); ends.append(finish)
                            logs.append({'status': 'head_pair', 'model': name, 'parent': parent, 'week_block': block,
                                'fit_cutoff': origin, 'teacher_origin': past, 'max_label_end': fits[past][1]['max_label_end'],
                                'head_label_end': finish, 'forecast_qty': value, 'actual_qty': actual})
                        if not ends or max(ends) > origin:
                            raise ValueError('Incomplete head history')
                        scale = float(table['scale'][np.flatnonzero(table['origins'] == origin)[0]])
                        beta = (np.array([relative_factor(p, y, head['prior_weeks']), 0.]) if head['kind'] == 'multiply'
                                else residual_parameters(p, y, scale, head))
                        parameters[(name, block)] = beta, scale
                        logs.append({'status': 'head', 'model': name, 'parent': parent, 'week_block': block,
                            'fit_cutoff': origin, 'max_head_label_end': max(ends), 'n_weeks': len(y),
                            'beta0': beta[0], 'beta1': beta[1], 'head_scale': scale})
            predicted = predict_batch(model, prepared, origin, spec)
            for name, head in heads.items():
                values = []
                for block in (1, 2):
                    value = predicted[(FOCUS, block)]
                    beta, scale = parameters[(name, block)] if head['kind'] != 'identity' else (np.zeros(2), 1.)
                    corrected = transform(value, scale, head, beta)
                    logs.append({'status': 'applied', 'model': name, 'parent': parent, 'week_block': block,
                        'as_of_date': origin, 'fit_cutoff': cutoff, 'forecast_qty': value, 'corrected_forecast_qty': corrected,
                        'beta0': beta[0], 'beta1': beta[1], 'head_scale': scale})
                    values.append(corrected)
                rows.extend(prediction_rows(groups[FOCUS], FOCUS, 'AdaptiveResearch', 'direct_7d', name, split, origin, end, values))
        print(f'{split}: {parent} ({len(heads)} outputs, refit {interval})', flush=True)
    return pd.DataFrame(rows, columns=COLUMNS), pd.DataFrame(logs)


def verify(log, experiment, daily, cfg, settings, split):
    heads = verify_heads(log, experiment, daily)
    weighted = log.loc[log.status.eq('fit') & log.half_life_days.notna()] if 'half_life_days' in log else log.iloc[:0]
    prepared = prepare_parent(daily, settings, {'scale_days': 56})
    for row in weighted.itertuples():
        changes = experiment['parents'][row.parent]
        spec = {'kind': 'lgbm', 'units': 'ratio', **settings['models']['LightGBM']['lgbm_annual_ratio7'], **changes}
        _, _, _, expected = weighted_batch(prepared, row.fit_cutoff, spec, effective_settings(settings, changes))
        for field in ['training_pairs', 'weight_sha256', 'max_label_end', 'min_label_end']:
            assert getattr(row, field) == expected[field], field
        np.testing.assert_allclose([row.weight_sum, row.base_weight_sum], [expected['weight_sum'], expected['base_weight_sum']], atol=1e-8, rtol=0)
    applied = log.loc[log.status.eq('applied')]
    start = pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1) if split != 'future' else daily.date.max()
    for parent, group in applied.groupby('parent'):
        interval = experiment['parents'][parent].get('refit_days', settings['refit_days'])
        expected = start+pd.to_timedelta(((group.as_of_date-start).dt.days//interval)*interval, unit='D')
        np.testing.assert_array_equal(group.fit_cutoff.to_numpy(), expected.to_numpy())
    return {'heads': heads, 'weighted_fits': len(weighted), 'applications': len(applied)}


def run(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run ID')
    path = ROOT/'data/configs/m2-adaptive.json'; experiment = json.loads(path.read_text(encoding='utf-8'))
    assert tuple(experiment['focus_route']) == FOCUS and len(candidates(experiment)) == 21
    cfg = read_config(experiment['base_config']); settings = load_settings(ROOT/experiment['model_config'])
    old = ROOT/'M2/artifacts'/experiment['reference_run']; validate_run(old)
    previous = ROOT/'M2/artifacts'/experiment['previous_experiment']; prior_manifest = validate_run(previous)
    protected = {}
    for name in experiment['protected_experiments']:
        folder = ROOT/'M2/artifacts'/name; existing = validate_run(folder)
        protected.update(existing['protected_before'])
        protected.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in folder.rglob('*') if p.is_file()})
    # Preserve preceding research code/config and independent receipts as well as published outputs.
    for p in (ROOT/'M2/models').glob('*experiment.py'):
        if p.name != 'adaptive_experiment.py': protected[p.relative_to(ROOT).as_posix()] = sha256(p)
    for p in (ROOT/'data/configs').glob('m2-*.json'):
        if p != path: protected[p.relative_to(ROOT).as_posix()] = sha256(p)
    for p in (ROOT/'M2/artifacts').glob('m2_*_20261011_review.json'):
        protected[p.relative_to(ROOT).as_posix()] = sha256(p)
    source = ROOT/cfg['source']; assert sha256(source) == prior_manifest['source_sha256']
    out = ROOT/'M2/artifacts'/run_id; out.mkdir(parents=True, exist_ok=False)
    manifest = new_manifest(cfg, source, run_id)
    manifest.update(experiment=experiment, settings=settings, candidates=candidates(experiment), config_sha256=sha256(path),
        implementation_modules_sha256=implementation_hashes(), protected_before=protected,
        daily_lineage={'path': str(previous/'daily_sales.csv'), 'sha256': sha256(previous/'daily_sales.csv')}, production_modified=False)
    write_json(out/'protocol.json', manifest); write_json(out/'manifest.json', manifest)
    daily = pd.read_csv(previous/'daily_sales.csv', parse_dates=['date'])
    top = route_top(daily, cfg)
    pd.testing.assert_frame_equal(top, pd.read_csv(old/'top_routes.csv'), check_exact=True)
    audit = json.loads((previous/'data_audit.json').read_text())
    assert daily.sales_qty.sum() == audit['sales_quantity']
    focused = daily.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    checks = {'raw_hash_and_quantity_conserved': True, 'train_top10_exact': True}; history = []
    print('Registered 21 candidates: residual / age weights / refit cadence', flush=True)
    for start, end in experiment['historical_folds']:
        cutoff = pd.Timestamp(start)-pd.Timedelta(days=1)
        fold = {**cfg, 'train_end': cutoff, 'validation_start': start, 'validation_end': end}
        population = route_top(daily, fold)
        subset = daily.loc[daily.date.le(end)].merge(population[ROUTE], on=ROUTE, validate='many_to_one')
        pred, log = phase(subset, fold, settings, experiment, 'validation')
        table = metrics(pred, fold); table['fold_start'] = start; history.append(table)
        write_csv(out/f'history_{start}_predictions.csv', pred); write_csv(out/f'history_{start}_fit_log.csv', log)
        checks[f'history_{start}_labels'] = reconcile_labels(pred, subset, fold)
        checks[f'history_{start}_causal'] = verify(log, experiment, subset, fold, settings, 'validation')
    write_csv(out/'historical_metrics.csv', pd.concat(history, ignore_index=True))
    validation, log = phase(focused, cfg, settings, experiment, 'validation'); table = metrics(validation, cfg)
    for name, frame in [('validation_predictions', validation), ('validation_metrics', table), ('validation_fit_log', log),
                        ('validation_monthly_metrics', monthly_metrics(validation, cfg))]: write_csv(out/f'{name}.csv', frame)
    checks['validation_labels'] = reconcile_labels(validation, focused, cfg)
    checks['validation_metrics'] = reconcile_metrics(validation, table, cfg)
    checks['validation_causal'] = verify(log, experiment, focused, cfg, settings, 'validation')
    prior = load_predictions(previous/'validation_predictions.csv'); prior = prior.loc[prior.model.eq('focus_scale56_mul56p4')]
    control = validation.loc[validation.model.eq('adapt56_mul56p4')]
    joined = control.merge(prior, on=ROUTE+['as_of_date', 'block'], suffixes=('', '_old'), validate='one_to_one')
    assert len(joined) == len(control) == len(prior)
    np.testing.assert_allclose(joined.forecast_qty, joined.forecast_qty_old, atol=1e-8, rtol=0)
    checks['control_max_difference'] = float((joined.forecast_qty-joined.forecast_qty_old).abs().max())
    selected = select(table, validation, cfg).iloc[0]; prior_score = prior_manifest['result']['validation_selected_mape_pct']
    improved = bool(selected.validation_mape_positive_pct < prior_score-experiment['numeric_tolerance'])
    locked = pd.read_csv(old/'overall_selected_models.csv', float_precision='round_trip')
    locked = locked.loc[locked.target.eq('direct_7d')].copy()
    focus_mask = locked.destination_country.eq(FOCUS[0]) & locked.carrier.eq(FOCUS[1])
    # The prior validation winner remains the research selection if this wave does not improve.
    prior_selected = pd.read_csv(previous/'selected_models.csv', float_precision='round_trip')
    locked.loc[focus_mask, ['family', 'model', 'validation_mape_positive_pct', 'validation_mae']] = (
        [selected.family, selected.model, selected.validation_mape_positive_pct, selected.validation_mae] if improved
        else prior_selected.loc[prior_selected.carrier.eq(FOCUS[1]), ['family', 'model', 'validation_mape_positive_pct', 'validation_mae']].iloc[0].tolist())
    write_csv(out/'selected_models.csv', locked)
    lock = {'selected_model': selected.model if improved else 'focus_scale56_mul56p4',
        'best_validation_candidate': selected.model, 'locked_at_utc': datetime.now(timezone.utc).isoformat(),
        'selected_sha256': sha256(out/'selected_models.csv'), 'test_scored_if_improved': improved, 'nine_routes_frozen': True}
    write_json(out/'selection_lock.json', lock)
    result = {'validation_improved': improved, 'selected_model': lock['selected_model'],
        'best_validation_candidate': selected.model, 'validation_previous_mape_pct': prior_score,
        'validation_selected_mape_pct': selected.validation_mape_positive_pct, 'test_scored': False, 'goal_achieved': False}
    if improved:
        print(f'Locked {selected.model}; one retrospective test', flush=True)
        test, test_log = phase(focused, cfg, settings, experiment, 'test', [selected.model])
        original = load_predictions(old/'overall_test_predictions.csv'); original = original.loc[original.target.eq('direct_7d')]
        combined = combine_frozen(original, test); scored = metrics(combined, cfg)
        for name, frame in [('focus_test_predictions', test), ('test_fit_log', test_log), ('overall_test_predictions', combined), ('overall_test_metrics', scored)]:
            write_csv(out/f'{name}.csv', frame)
        checks['test_labels'] = reconcile_labels(combined, focused, cfg)
        checks['test_metrics'] = reconcile_metrics(combined, scored, cfg)
        checks['test_causal'] = verify(test_log, experiment, focused, cfg, settings, 'test')
        saved = load_predictions(out/'overall_test_predictions.csv')
        other = ~saved.carrier.eq(FOCUS[1]); old_other = ~original.carrier.eq(FOCUS[1])
        pd.testing.assert_frame_equal(saved.loc[other].reset_index(drop=True), original.loc[old_other].reset_index(drop=True), check_exact=True)
        checks['other_nine_predictions_exact'] = int(other.sum())
        primary = scored.loc[scored.block.eq(1) & scored.cadence.eq('daily_origins')]
        baseline = metrics(original, cfg); baseline = baseline.loc[baseline.block.eq(1) & baseline.cadence.eq('daily_origins')]
        comparison = primary.merge(baseline, on=ROUTE, suffixes=('_new', '_old'), validate='one_to_one')
        write_csv(out/'before_after_routes.csv', comparison)
        row = primary.loc[primary.carrier.eq(FOCUS[1])].iloc[0]
        result.update(test_scored=True, focus_test_mape_pct=row.mape_positive_pct,
            reference_focus_test_mape_pct=float(baseline.loc[baseline.carrier.eq(FOCUS[1]), 'mape_positive_pct'].iloc[0]),
            goal_achieved=bool(row.mape_positive_pct < 20 and row.coverage == 1), top10_passes_20_pct=int(primary.passes_20_pct.sum()))
        future, future_log = phase(focused, cfg, settings, experiment, 'future', [selected.model])
        write_csv(out/'focus_future_predictions.csv', future); write_csv(out/'future_fit_log.csv', future_log)
        checks['future_labels'] = reconcile_labels(future, focused, cfg)
        checks['future_causal'] = verify(future_log, experiment, focused, cfg, settings, 'future')
    for name, digest in protected.items(): assert sha256(ROOT/name) == digest, name
    assert sha256(source) == manifest['source_sha256'] and sha256(out/'selected_models.csv') == lock['selected_sha256']
    checks.update(status='passed', protected_files_unchanged=len(protected), source_hash_unchanged=True, selection_lock_unchanged=True)
    write_json(out/'verification.json', checks); write_json(out/'result.json', result)
    primary = table.loc[table.block.eq(1) & table.cadence.eq('daily_origins')].sort_values(['mape_positive_pct', 'mae', 'model'])
    rows = '\n'.join(f'| {r.model} | {r.mape_positive_pct:.6f} | {r.mae:.6f} | {r.coverage:.0%} |' for r in primary.itertuples())
    (out/'README.md').write_text(f'''# LG U+ hiệu chỉnh và cập nhật — {run_id}

21 cấu hình đăng ký trước fit:7 bản của chuẩn hóa56 ngày;6 bản age-weight28/56/112 ngày;4 bản refit1/3 ngày;4 bản kết hợp age56/refit1/3. Chỉ chọn bằng validation chính, hai fold lịch sử là chẩn đoán. Một lựa chọn thắng mới được khóa/chấm test hồi cứu; dừng sau lượt hữu hạn này. Chín tuyến và dashboard/báo cáo khóa giữ nguyên; R05 ngày/R07/T14 không đổi.

Kết quả `{json.dumps(result, ensure_ascii=False)}`

[Protocol](protocol.json), [khóa](selection_lock.json), [kiểm chứng](verification.json), [metric](validation_metrics.csv), [lịch sử](historical_metrics.csv).

| Ứng viên | MAPE validation % | MAE | Coverage |
|---|---:|---:|---:|
{rows}
''', encoding='utf-8')
    manifest.update(status='complete', result=result, finished_at_utc=datetime.now(timezone.utc).isoformat()); seal_manifest(out, manifest)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--run-id', required=True)
    run(parser.parse_args().run_id)
