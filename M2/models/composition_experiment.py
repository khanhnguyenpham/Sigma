"""Quantity distribution features and count times past-basket forecasts for LG U+."""
import argparse
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, new_manifest, seal_manifest, validate_run
from src.data import audit_orders, daily_sales, route_top
from sigma.forecasting.weekly import fit, predict_batch, checked_series
from sigma.forecasting.calibration import relative_factor
from M2.models.registry import load_settings, implementation_hashes
from M2.models.common import prediction_rows, COLUMNS
from M2.models.focus_experiment import FOCUS, prepare_parent, combine_frozen, load_predictions, candidates as head_candidates
from M2.models.adaptive_experiment import phase as count_phase, verify as verify_phase
from M2.models.calendar_experiment import reconcile_labels
from M2.models.families import metrics, select, monthly_metrics
from M2.models.verify import reconcile_metrics

MOMENTS = ['large_order_count', 'large_quantity', 'squared_quantity']
LARGE = ['large_order_share28', 'large_order_share56', 'large_quantity_share28', 'large_quantity_share56', 'large_order_growth7']
DISPERSION = ['basket_cv28', 'basket_cv56']


def subexperiment(experiment, which):
    return {'parents': experiment[which+'_parents'], 'heads': experiment['heads'],
            'residual_heads': {}, 'residual_parents': [], 'blend_parents': [], 'blend_weights': []}


def candidates(experiment):
    result = head_candidates(subexperiment(experiment, 'quantity'))
    for name, head in head_candidates(subexperiment(experiment, 'count')).items():
        for window in experiment['basket_windows']:
            result[f'{name}_basket{window}'] = {**head, 'count_model': name, 'basket_days': window}
    return result


def distribution_daily(sales, daily, minimum):
    if not sales.order_id.is_unique:
        raise ValueError('Order distribution requires one row per order in this snapshot')
    large = sales.quantity.ge(minimum)
    observed = sales.assign(large_order_count=large.astype(int), large_quantity=sales.quantity.where(large, 0),
        squared_quantity=sales.quantity**2).groupby(['date']+ROUTE)[MOMENTS].sum().reset_index()
    result = daily.merge(observed, on=['date']+ROUTE, how='left', validate='one_to_one')
    result[MOMENTS] = result[MOMENTS].fillna(0).astype('int64')
    assert (result.large_order_count <= result.order_count).all() and (result.large_quantity <= result.sales_qty).all()
    assert result.squared_quantity.sum() == (sales.quantity**2).sum()
    return result


def prepare_quantity(daily, settings, changes):
    prepared = prepare_parent(daily, settings, changes)
    for (route, _), table in prepared.items():
        part = daily.loc[daily.destination_country.eq(route[0]) & daily.carrier.eq(route[1])].set_index('date').sort_index()
        extra = pd.DataFrame(index=part.index)
        for days in (28, 56):
            n = part.order_count.rolling(days, min_periods=days).sum().clip(lower=1)
            q = part.sales_qty.rolling(days, min_periods=days).sum()
            mean = q/n
            variance = (part.squared_quantity.rolling(days, min_periods=days).sum()/n-mean**2).clip(lower=0)
            extra[f'large_order_share{days}'] = part.large_order_count.rolling(days, min_periods=days).sum()/n
            extra[f'large_quantity_share{days}'] = part.large_quantity.rolling(days, min_periods=days).sum()/q.clip(lower=1)
            extra[f'basket_cv{days}'] = np.sqrt(variance)/mean.clip(lower=1)
        extra['large_order_growth7'] = (part.large_order_count.rolling(7, min_periods=7).mean()
            /part.large_order_count.rolling(28, min_periods=28).mean().clip(lower=1/28))
        table['x'][LARGE+DISPERSION] = extra.reindex(table['origins'])[LARGE+DISPERSION].to_numpy()
    return prepared


def quantity_phase(daily, cfg, settings, experiment, split, wanted):
    exp = subexperiment(experiment, 'quantity'); specs = head_candidates(exp)
    groups = {key: part.sales_qty.astype(float) for key, part in checked_series(daily).items()}
    end = pd.Timestamp(cfg[f'{split}_end']) if split != 'future' else daily.date.max()
    origins = (pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1), end-pd.Timedelta(days=1))
               if split != 'future' else [end])
    rows, logs = [], []
    for parent, changes in exp['parents'].items():
        heads = {name: specs[name] for name in wanted if name in specs and specs[name]['parent'] == parent}
        if not heads: continue
        prepared = prepare_quantity(daily, settings, changes)
        group = changes['feature_group']
        columns = LARGE+DISPERSION if group == 'both' else LARGE if group == 'large' else DISPERSION if group == 'dispersion' else []
        spec = {'kind': 'lgbm', 'units': 'ratio', **settings['models']['LightGBM']['lgbm_annual_ratio7'], 'calendar_feature_columns': columns}
        fits, predictions, parameters = {}, {}, {}
        def teacher(origin):
            if origin not in fits:
                fits[origin] = fit(prepared, origin, spec, cfg, settings)
                logs.append({'status': 'fit', 'parent': parent, 'fit_cutoff': origin, **fits[origin][1]})
            return fits[origin][0]
        def prediction(origin):
            if origin not in predictions: predictions[origin] = predict_batch(teacher(origin), prepared, origin, spec)
            return predictions[origin]
        for i, origin in enumerate(origins):
            if i % settings['refit_days'] == 0:
                model, cutoff = teacher(origin), origin
                for name, head in heads.items():
                    if head['kind'] == 'identity': continue
                    for block in (1, 2):
                        p, y, ends = [], [], []; table = prepared[(FOCUS, block)]
                        for past in pd.date_range(origin-pd.Timedelta(days=head['history_days']), origin-pd.Timedelta(days=7), freq='7D'):
                            idx = np.flatnonzero(table['origins'] == past)
                            if len(idx) != 1: raise ValueError('Missing teacher origin')
                            idx = idx[0]; finish = table['ends'][idx]
                            if finish > origin: continue
                            value, actual = prediction(past)[(FOCUS, block)], table['y'][idx]
                            p.append(value); y.append(actual); ends.append(finish)
                            logs.append({'status': 'head_pair', 'model': name, 'parent': parent, 'week_block': block,
                                'fit_cutoff': origin, 'teacher_origin': past, 'max_label_end': fits[past][1]['max_label_end'],
                                'head_label_end': finish, 'forecast_qty': value, 'actual_qty': actual})
                        factor = relative_factor(p, y, head['prior_weeks']); parameters[(name, block)] = factor
                        logs.append({'status': 'head', 'model': name, 'parent': parent, 'week_block': block,
                            'fit_cutoff': origin, 'max_head_label_end': max(ends), 'n_weeks': len(y),
                            'beta0': factor, 'beta1': 0., 'head_scale': 1.})
            predicted = predict_batch(model, prepared, origin, spec)
            for name, head in heads.items():
                values = []
                for block in (1, 2):
                    value = predicted[(FOCUS, block)]; factor = parameters.get((name, block), 1.)
                    corrected = max(0., value*factor); values.append(corrected)
                    logs.append({'status': 'applied', 'model': name, 'parent': parent, 'week_block': block,
                        'as_of_date': origin, 'fit_cutoff': cutoff, 'forecast_qty': value, 'corrected_forecast_qty': corrected,
                        'beta0': factor, 'beta1': 0., 'head_scale': 1.})
                rows.extend(prediction_rows(groups[FOCUS], FOCUS, 'CompositionResearch', 'direct_7d', name, split, origin, end, values))
        print(f'{split}: {parent} ({len(heads)} outputs)', flush=True)
    return pd.DataFrame(rows, columns=COLUMNS), pd.DataFrame(logs)


def allocate_basket(counts, daily, name, window):
    part = daily.loc[daily.destination_country.eq(FOCUS[0]) & daily.carrier.eq(FOCUS[1])].set_index('date').sort_index()
    n = part.order_count.rolling(window, min_periods=window).sum()
    basket = (part.sales_qty.rolling(window, min_periods=window).sum()/n.replace(0, np.nan)).fillna(1.)
    result = counts.copy(); result['model'] = name; result['family'] = 'CompositionResearch'
    result['forecast_qty'] *= basket.reindex(result.as_of_date).to_numpy()
    actual = part.sales_qty.rolling(7).sum().reindex(result.target_date).to_numpy()
    result['actual_qty'] = np.where(counts.actual_qty.notna().to_numpy(), actual, np.nan)
    if not np.isfinite(result.forecast_qty).all(): raise ValueError('Missing basket forecast')
    return result


def phase(daily, cfg, settings, experiment, split, wanted=None):
    specs = candidates(experiment); wanted = list(specs) if wanted is None else list(wanted)
    quantity, qlog = quantity_phase(daily, cfg, settings, experiment, split, wanted)
    frames = [quantity] if len(quantity) else []
    count_names = sorted({specs[name]['count_model'] for name in wanted if 'count_model' in specs[name]})
    counts = pd.DataFrame(columns=COLUMNS); clog = pd.DataFrame()
    count_daily = daily.copy(); count_daily['sales_qty'] = count_daily.order_count
    if count_names:
        counts, clog = count_phase(count_daily, cfg, settings, subexperiment(experiment, 'count'), split, count_names)
        for name in wanted:
            spec = specs[name]
            if 'count_model' in spec:
                frames.append(allocate_basket(counts.loc[counts.model.eq(spec['count_model'])], daily, name, spec['basket_days']))
    quantity = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    checks = {'quantity': verify_phase(qlog, subexperiment(experiment, 'quantity'), daily, cfg, settings, split) if len(qlog) else {},
              'counts': verify_phase(clog, subexperiment(experiment, 'count'), count_daily, cfg, settings, split) if len(clog) else {}}
    return quantity, qlog, counts, clog, checks


def run(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id): raise ValueError('Invalid run ID')
    path = ROOT/'data/configs/m2-composition.json'; exp = json.loads(path.read_text(encoding='utf-8'))
    assert len(candidates(exp)) == 26 and tuple(exp['focus_route']) == FOCUS
    cfg = read_config(exp['base_config']); settings = load_settings(ROOT/exp['model_config'])
    old = ROOT/'M2/artifacts'/exp['reference_run']; validate_run(old)
    previous = ROOT/'M2/artifacts'/exp['previous_experiment']; previous_manifest = validate_run(previous)
    preceding = ROOT/'M2/artifacts'/exp['protected_experiment']; preceding_manifest = validate_run(preceding)
    protected = {**preceding_manifest['protected_before'],
        **{p.relative_to(ROOT).as_posix(): sha256(p) for p in preceding.rglob('*') if p.is_file()}}
    failed = ROOT/'M2/artifacts'/exp['rerun_of'] if exp.get('rerun_of') else None
    if failed:
        invalidated = validate_run(failed, require_complete=False)
        assert invalidated['status'] == 'failed' and invalidated.get('invalidated')
        for key in ['quantity_parents', 'count_parents', 'heads', 'basket_windows', 'large_order_quantity_min', 'historical_folds', 'selection', 'test_policy']:
            assert exp[key] == invalidated['experiment'][key], key
        assert not (failed/'selection_lock.json').exists() and not (failed/'focus_test_predictions.csv').exists()
        protected.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in failed.rglob('*') if p.is_file()})
    for p in [ROOT/'M2/models/adaptive_experiment.py', ROOT/'data/configs/m2-adaptive.json', ROOT/'M2/artifacts/m2_adaptive_20261011_review.json']:
        protected[p.relative_to(ROOT).as_posix()] = sha256(p)
    source = ROOT/cfg['source']; assert sha256(source) == previous_manifest['source_sha256']
    out = ROOT/'M2/artifacts'/run_id; out.mkdir(parents=True, exist_ok=False)
    manifest = new_manifest(cfg, source, run_id)
    manifest.update(experiment=exp, settings=settings, candidates=candidates(exp), config_sha256=sha256(path),
        implementation_modules_sha256=implementation_hashes(), protected_before=protected, production_modified=False)
    write_json(out/'protocol.json', manifest); write_json(out/'manifest.json', manifest)
    print('Registered 26 composition candidates; fresh raw audit', flush=True)
    sales, audit = audit_orders(source, cfg); daily = daily_sales(sales, cfg)
    daily = distribution_daily(sales, daily, exp['large_order_quantity_min'])[['date']+ROUTE+['sales_qty', 'order_count']+MOMENTS]
    del sales
    write_json(out/'data_audit.json', audit); write_csv(out/'daily_distribution.csv', daily)
    top = route_top(daily, cfg); pd.testing.assert_frame_equal(top, pd.read_csv(old/'top_routes.csv'), check_exact=True)
    write_csv(out/'top_routes.csv', top)
    focused = daily.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    checks = {'raw_hash_and_quantity_conserved': True, 'train_top10_exact': True}; history = []
    phases = [(start, end, True) for start, end in exp['historical_folds']]+[(cfg['validation_start'], cfg['validation_end'], False)]
    for start, end, historical in phases:
        fold = {**cfg, 'validation_start': start, 'validation_end': end}
        subset = focused
        if historical:
            fold['train_end'] = pd.Timestamp(start)-pd.Timedelta(days=1)
            pop = route_top(daily, fold)
            subset = daily.loc[daily.date.le(end)].merge(pop[ROUTE], on=ROUTE, validate='many_to_one')
        predictions, log, counts, clog, causal = phase(subset, fold, settings, exp, 'validation')
        table = metrics(predictions, fold); prefix = f'history_{start}' if historical else 'validation'
        if failed:
            prior_predictions = load_predictions(failed/f'{prefix}_predictions.csv')
            keys = ROUTE+['model', 'as_of_date', 'block']
            parity = predictions.merge(prior_predictions, on=keys, suffixes=('', '_failed'), validate='one_to_one')
            assert len(parity) == len(predictions) == len(prior_predictions)
            np.testing.assert_allclose(parity.forecast_qty, parity.forecast_qty_failed, atol=1e-8, rtol=0)
            checks[prefix+'_repair_forecast_max_difference'] = float((parity.forecast_qty-parity.forecast_qty_failed).abs().max())
        for suffix, frame in [('predictions', predictions), ('fit_log', log), ('count_predictions', counts), ('count_fit_log', clog), ('metrics', table)]:
            write_csv(out/f'{prefix}_{suffix}.csv', frame)
        checks[prefix+'_labels'] = reconcile_labels(predictions, subset, fold)
        checks[prefix+'_metrics'] = reconcile_metrics(predictions, table, fold); checks[prefix+'_causal'] = causal
        if historical:
            table['fold_start'] = start; history.append(table)
        else:
            validation, validation_table = predictions, table
            write_csv(out/'validation_monthly_metrics.csv', monthly_metrics(predictions, fold))
    write_csv(out/'historical_metrics.csv', pd.concat(history, ignore_index=True))
    prior = load_predictions(previous/'validation_predictions.csv'); prior = prior.loc[prior.model.eq('focus_scale56_mul56p4')]
    control = validation.loc[validation.model.eq('composition_control56_mul56p4')]
    joined = control.merge(prior, on=ROUTE+['as_of_date', 'block'], suffixes=('', '_old'), validate='one_to_one')
    assert len(joined) == len(control) == len(prior)
    np.testing.assert_allclose(joined.forecast_qty, joined.forecast_qty_old, atol=1e-8, rtol=0)
    checks['control_max_difference'] = float((joined.forecast_qty-joined.forecast_qty_old).abs().max())
    chosen = select(validation_table, validation, cfg).iloc[0]; prior_score = previous_manifest['result']['validation_selected_mape_pct']
    improved = bool(chosen.validation_mape_positive_pct < prior_score-exp['numeric_tolerance'])
    locked = pd.read_csv(old/'overall_selected_models.csv', float_precision='round_trip'); locked = locked.loc[locked.target.eq('direct_7d')].copy()
    mask = locked.carrier.eq(FOCUS[1]) & locked.destination_country.eq(FOCUS[0])
    prior_selected = pd.read_csv(previous/'selected_models.csv', float_precision='round_trip')
    locked.loc[mask, ['family', 'model', 'validation_mape_positive_pct', 'validation_mae']] = (
        [chosen.family, chosen.model, chosen.validation_mape_positive_pct, chosen.validation_mae] if improved else
        prior_selected.loc[prior_selected.carrier.eq(FOCUS[1]), ['family', 'model', 'validation_mape_positive_pct', 'validation_mae']].iloc[0].tolist())
    write_csv(out/'selected_models.csv', locked)
    lock = {'selected_model': chosen.model if improved else 'focus_scale56_mul56p4', 'best_validation_candidate': chosen.model,
        'locked_at_utc': datetime.now(timezone.utc).isoformat(), 'selected_sha256': sha256(out/'selected_models.csv'),
        'test_scored_if_improved': improved, 'nine_routes_frozen': True}
    write_json(out/'selection_lock.json', lock)
    result = {'validation_improved': improved, 'selected_model': lock['selected_model'], 'best_validation_candidate': chosen.model,
        'validation_previous_mape_pct': prior_score, 'validation_selected_mape_pct': chosen.validation_mape_positive_pct,
        'test_scored': False, 'goal_achieved': False, 'rerun_of': exp.get('rerun_of')}
    if improved:
        write_json(out/'test_execution.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'selection_lock_sha256': sha256(out/'selection_lock.json')})
        print(f'Locked {chosen.model}; one retrospective test', flush=True)
        test, log, counts, clog, causal = phase(focused, cfg, settings, exp, 'test', [chosen.model])
        original = load_predictions(old/'overall_test_predictions.csv'); original = original.loc[original.target.eq('direct_7d')]
        combined = combine_frozen(original, test); scored = metrics(combined, cfg)
        for name, frame in [('focus_test_predictions', test), ('test_fit_log', log), ('test_count_predictions', counts),
            ('test_count_fit_log', clog), ('overall_test_predictions', combined), ('overall_test_metrics', scored)]: write_csv(out/f'{name}.csv', frame)
        checks['test_labels'] = reconcile_labels(combined, focused, cfg); checks['test_metrics'] = reconcile_metrics(combined, scored, cfg); checks['test_causal'] = causal
        saved = load_predictions(out/'overall_test_predictions.csv'); other = ~saved.carrier.eq(FOCUS[1])
        pd.testing.assert_frame_equal(saved.loc[other].reset_index(drop=True), original.loc[~original.carrier.eq(FOCUS[1])].reset_index(drop=True), check_exact=True)
        checks['other_nine_predictions_exact'] = int(other.sum())
        primary = scored.loc[scored.block.eq(1) & scored.cadence.eq('daily_origins')]
        baseline = metrics(original, cfg); baseline = baseline.loc[baseline.block.eq(1) & baseline.cadence.eq('daily_origins')]
        write_csv(out/'before_after_routes.csv', primary.merge(baseline, on=ROUTE, suffixes=('_new', '_old'), validate='one_to_one'))
        row = primary.loc[primary.carrier.eq(FOCUS[1])].iloc[0]
        result.update(test_scored=True, focus_test_mape_pct=row.mape_positive_pct,
            reference_focus_test_mape_pct=float(baseline.loc[baseline.carrier.eq(FOCUS[1]), 'mape_positive_pct'].iloc[0]),
            goal_achieved=bool(row.mape_positive_pct < 20 and row.coverage == 1), top10_passes_20_pct=int(primary.passes_20_pct.sum()))
        future, log, counts, clog, causal = phase(focused, cfg, settings, exp, 'future', [chosen.model])
        for name, frame in [('focus_future_predictions', future), ('future_fit_log', log), ('future_count_predictions', counts), ('future_count_fit_log', clog)]: write_csv(out/f'{name}.csv', frame)
        checks['future_labels'] = reconcile_labels(future, focused, cfg); checks['future_causal'] = causal
    for name, digest in protected.items(): assert sha256(ROOT/name) == digest, name
    assert sha256(source) == manifest['source_sha256'] and sha256(out/'selected_models.csv') == lock['selected_sha256']
    checks.update(status='passed', protected_files_unchanged=len(protected), source_hash_unchanged=True, selection_lock_unchanged=True)
    write_json(out/'verification.json', checks); write_json(out/'result.json', result)
    primary = validation_table.loc[validation_table.block.eq(1) & validation_table.cadence.eq('daily_origins')].sort_values(['mape_positive_pct', 'mae', 'model'])
    rows = '\n'.join(f'| {r.model} | {r.mape_positive_pct:.6f} | {r.mae:.6f} | {r.coverage:.0%} |' for r in primary.itertuples())
    (out/'README.md').write_text(f'''# LG U+ cơ cấu đơn — {run_id}

26 cấu hình đăng ký trước fit:8 bản feature quantity và18 bản count×basket. Count teacher/head có nhãn order_count; nhãn/metric đầu ra luôn quantity thật. Basket dự báo bằng trung bình quantity/order trailing28/56/90 ngày đã biết tại origin. Một lựa chọn thắng validation mới khóa/chấm một test hồi cứu. Dừng sau lượt hữu hạn; chín tuyến/dashboard/báo cáo khóa giữ nguyên, R05 ngày/R07/T14 không đổi.

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
