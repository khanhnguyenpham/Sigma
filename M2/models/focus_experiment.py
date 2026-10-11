"""Preregistered LG U+ research; preserve nine sealed route forecasts exactly."""
import argparse
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, validate_run, new_manifest, seal_manifest
from src.data import audit_orders, daily_sales, route_top
from sigma.forecasting.weekly import prepare, checked_series, fit, predict_batch
from sigma.forecasting.calibration import relative_factor
from M2.models.common import prediction_rows, COLUMNS, effective_settings
from M2.models.registry import load_settings, implementation_hashes
from M2.models.families import metrics, select, monthly_metrics
from M2.models.verify import reconcile_metrics
from M2.models.calendar_experiment import protected_files, reconcile_labels

RECENT = ['recent_qty_growth7', 'recent_qty_growth14', 'recent_order_growth7',
          'recent_order_growth14', 'recent_basket_ratio7', 'recent_ema_ratio', 'recent_change7']
FOCUS = ('South Korea', 'LG U+')


def load_predictions(path):
    return pd.read_csv(path, parse_dates=['as_of_date', 'target_date', 'window_start'], float_precision='round_trip')


def combine_frozen(reference, focus):
    mask = reference.destination_country.eq(FOCUS[0]) & reference.carrier.eq(FOCUS[1])
    if focus.empty or not (focus.destination_country.eq(FOCUS[0]) & focus.carrier.eq(FOCUS[1])).all():
        raise ValueError('Only the focus route may be replaced')
    keys = ['as_of_date', 'block']
    a = reference.loc[mask, keys].sort_values(keys).reset_index(drop=True)
    b = focus[keys].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    return pd.concat([reference.loc[~mask], focus], ignore_index=True)


def candidates(experiment):
    result = {f'{parent}_{head}': {'parent': parent, **spec}
              for parent in experiment['parents'] for head, spec in experiment['heads'].items()}
    result.update({f'{parent}_{head}': {'parent': parent, **spec}
        for parent in experiment['residual_parents'] for head, spec in experiment['residual_heads'].items()})
    for parent in experiment['blend_parents']:
        for weight in experiment['blend_weights']:
            result[f'{parent}_blend{int(weight*100)}'] = {
                'kind': 'blend', 'parent': parent, 'weight': weight, 'control': 'focus_control_mul56p4'}
    return result


def prepare_parent(daily, settings, changes):
    prepared = prepare(daily, {**settings, 'blocks': [1, 2], 'models': {}})
    for (route, _), table in prepared.items():
        part = daily.loc[daily.destination_country.eq(route[0]) & daily.carrier.eq(route[1])].set_index('date').sort_index()
        y, orders = part.sales_qty, part.order_count
        origin = table['origins']
        scale_days = changes.get('scale_days', 90)
        if scale_days != 90:
            table['scale'] = (y.rolling(scale_days, min_periods=scale_days).mean()*7).clip(lower=1).reindex(origin).to_numpy()
        if changes.get('recent_features'):
            q = {n: y.rolling(n, min_periods=n).mean() for n in (7, 14, 28, 56)}
            o = {n: orders.rolling(n, min_periods=n).mean() for n in (7, 14, 28, 56)}
            extra = pd.DataFrame({
                RECENT[0]: q[7]/q[28].clip(lower=1/7),
                RECENT[1]: q[14]/q[56].clip(lower=1/7),
                RECENT[2]: o[7]/o[28].clip(lower=1/7),
                RECENT[3]: o[14]/o[56].clip(lower=1/7),
                RECENT[4]: (q[7]/o[7].clip(lower=1/7))/(q[28]/o[28].clip(lower=1/7)).clip(lower=1/7),
                RECENT[5]: y.ewm(span=7, adjust=False).mean()/y.ewm(span=28, adjust=False).mean().clip(lower=1/7),
                RECENT[6]: (q[7]-q[7].shift(7))/q[28].clip(lower=1/7)})
            table['x'][RECENT] = extra.reindex(origin).to_numpy()
    return prepared


def residual_parameters(predicted, actual, scale, spec):
    p, y = np.asarray(predicted, float), np.asarray(actual, float)
    valid = (y > 0) & np.isfinite(y) & np.isfinite(p)
    p, y = p[valid]/scale, y[valid]/scale
    if not len(y):
        return np.zeros(2)
    x = np.column_stack([np.ones(len(p)), p]) if spec['kind'] == 'affine' else np.ones((len(p), 1))
    weight = 1/np.square(y)
    weight *= len(weight)/weight.sum()
    penalty = spec['prior_weeks'] * np.eye(x.shape[1])
    beta = np.linalg.solve(x.T @ (x*weight[:, None])+penalty, x.T @ (weight*(y-p)))
    return np.pad(beta, (0, 2-len(beta)))


def transform(value, scale, spec, parameters):
    if spec['kind'] == 'identity':
        return value
    if spec['kind'] == 'multiply':
        return max(0., value*parameters[0])
    correction = scale*parameters[0]+value*parameters[1]
    limit = spec['clip_fraction']*scale
    return max(0., value+float(np.clip(correction, -limit, limit)))


def phase(daily, cfg, settings, experiment, split, wanted=None):
    """Fit pooled teachers using only completed labels; emit only the focus route."""
    specifications = candidates(experiment)
    wanted = list(specifications) if wanted is None else list(wanted)
    required = set(wanted)
    for name in wanted:
        if specifications[name]['kind'] == 'blend':
            required.update([specifications[name]['control'], specifications[name]['parent']+'_raw'])
    parent_names = {specifications[name]['parent'] for name in required}
    groups = {key: part.sales_qty.astype(float) for key, part in checked_series(daily).items()}
    if FOCUS not in groups:
        raise ValueError('Focus absent from train-only population')
    end = pd.Timestamp(cfg[f'{split}_end']) if split != 'future' else daily.date.max()
    origins = pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1), end-pd.Timedelta(days=1)) if split != 'future' else [end]
    frames, logs = [], []
    base = settings['models']['LightGBM']['lgbm_annual_ratio7']
    for parent in experiment['parents']:
        if parent not in parent_names:
            continue
        changes = experiment['parents'][parent]
        prepared = prepare_parent(daily, settings, changes)
        pool = changes.get('pool', 'top10')
        training = {key: table for key, table in prepared.items()
                    if pool == 'top10' or pool == 'country' and key[0][0] == FOCUS[0]
                    or pool == 'route' and key[0] == FOCUS}
        spec = {'kind': 'lgbm', 'units': 'ratio', **base, **changes,
                'calendar_feature_columns': RECENT if changes.get('recent_features') else []}
        effective = effective_settings(settings, changes)
        fit_cache, prediction_cache = {}, {}
        def teacher(origin):
            if origin not in fit_cache:
                fit_cache[origin] = fit(training, origin, spec, cfg, effective)
                logs.append({'status': 'fit', 'parent': parent, 'fit_cutoff': origin, **fit_cache[origin][1]})
            return fit_cache[origin][0]
        def prediction(origin):
            if origin not in prediction_cache:
                prediction_cache[origin] = predict_batch(teacher(origin), prepared, origin, spec)
            return prediction_cache[origin]
        heads = {name: specifications[name] for name in required
                 if specifications[name]['parent'] == parent and specifications[name]['kind'] != 'blend'}
        parameters = {}
        for i, origin in enumerate(origins):
            if i % settings['refit_days'] == 0:
                model, cutoff = teacher(origin), origin
                for name, head in heads.items():
                    if head['kind'] == 'identity':
                        continue
                    for block in (1, 2):
                        p, y, label_ends = [], [], []
                        table = prepared[(FOCUS, block)]
                        for past in pd.date_range(origin-pd.Timedelta(days=head['history_days']), origin-pd.Timedelta(days=7), freq='7D'):
                            idx = np.flatnonzero(table['origins'] == past)
                            if len(idx) != 1:
                                raise ValueError('Missing teacher origin')
                            idx = idx[0]
                            finish = table['ends'][idx]
                            if finish > origin:
                                continue
                            forecast = prediction(past)[(FOCUS, block)]
                            actual = table['y'][idx]
                            p.append(forecast); y.append(actual); label_ends.append(finish)
                            logs.append({'status': 'head_pair', 'model': name, 'parent': parent, 'week_block': block,
                                'fit_cutoff': origin, 'teacher_origin': past, 'max_label_end': fit_cache[past][1]['max_label_end'],
                                'head_label_end': finish, 'forecast_qty': forecast, 'actual_qty': actual})
                        if not label_ends or max(label_ends) > origin:
                            raise ValueError('Incomplete causal head history')
                        idx = np.flatnonzero(table['origins'] == origin)[0]
                        scale = float(table['scale'][idx])
                        beta = np.array([relative_factor(p, y, head['prior_weeks']), 0.]) if head['kind'] == 'multiply' else residual_parameters(p, y, scale, head)
                        parameters[(name, block)] = (beta, scale)
                        logs.append({'status': 'head', 'model': name, 'parent': parent, 'week_block': block,
                            'fit_cutoff': origin, 'max_head_label_end': max(label_ends), 'n_weeks': len(y),
                            'beta0': beta[0], 'beta1': beta[1], 'head_scale': scale})
            predicted = predict_batch(model, prepared, origin, spec)
            for name, head in heads.items():
                values = []
                for block in (1, 2):
                    value = predicted[(FOCUS, block)]
                    if head['kind'] != 'identity':
                        beta, scale = parameters[(name, block)]
                        corrected = transform(value, scale, head, beta)
                        logs.append({'status': 'applied', 'model': name, 'week_block': block, 'as_of_date': origin,
                            'fit_cutoff': cutoff, 'forecast_qty': value, 'corrected_forecast_qty': corrected,
                            'beta0': beta[0], 'beta1': beta[1], 'head_scale': scale})
                        value = corrected
                    values.append(value)
                frames.extend(prediction_rows(groups[FOCUS], FOCUS, 'FocusResearch', 'direct_7d', name, split, origin, end, values))
        print(f'{split}: {parent} ({len(heads)} outputs)', flush=True)
    result = pd.DataFrame(frames, columns=COLUMNS)
    for name in wanted:
        spec = specifications[name]
        if spec['kind'] != 'blend':
            continue
        keys = ROUTE+['as_of_date', 'block']
        left = result.loc[result.model.eq(spec['control'])].copy()
        right = result.loc[result.model.eq(spec['parent']+'_raw'), keys+['forecast_qty']]
        joined = left.merge(right, on=keys, suffixes=('', '_component'), validate='one_to_one')
        assert len(joined) == len(left) == len(right)
        joined['forecast_qty'] = (1-spec['weight'])*joined.forecast_qty+spec['weight']*joined.forecast_qty_component
        joined['model'] = name
        result = pd.concat([result, joined[COLUMNS]], ignore_index=True)
    return result.loc[result.model.isin(wanted)].reset_index(drop=True), pd.DataFrame(logs)


def verify_heads(log, experiment, daily):
    specs = candidates(experiment)
    count = 0
    if log.empty:
        return count
    fits = log.loc[log.status.eq('fit')]
    assert (fits.max_label_end <= fits.fit_cutoff).all()
    actual = daily.loc[daily.destination_country.eq(FOCUS[0]) & daily.carrier.eq(FOCUS[1])].set_index('date').sales_qty.rolling(7).sum()
    for head in log.loc[log.status.eq('head')].itertuples():
        pairs = log.loc[log.status.eq('head_pair') & log.model.eq(head.model)
                        & log.fit_cutoff.eq(head.fit_cutoff) & log.week_block.eq(head.week_block)]
        assert (pairs.max_label_end <= pairs.teacher_origin).all()
        assert (pairs.head_label_end <= pairs.fit_cutoff).all() and len(pairs) == head.n_weeks
        spec = specs[head.model]
        origins = pd.date_range(head.fit_cutoff-pd.Timedelta(days=spec['history_days']), head.fit_cutoff-pd.Timedelta(days=7), freq='7D')
        origins = origins[origins+pd.Timedelta(days=7*int(head.week_block)) <= head.fit_cutoff]
        assert pd.DatetimeIndex(pairs.teacher_origin).equals(origins)
        assert (pairs.head_label_end == pairs.teacher_origin+pd.to_timedelta(7*pairs.week_block,unit='D')).all()
        np.testing.assert_array_equal(pairs.actual_qty,actual.reindex(pairs.head_label_end))
        beta = np.array([relative_factor(pairs.forecast_qty, pairs.actual_qty, spec['prior_weeks']), 0.]) if spec['kind'] == 'multiply' else residual_parameters(pairs.forecast_qty, pairs.actual_qty, head.head_scale, spec)
        np.testing.assert_allclose(beta, [head.beta0, head.beta1], atol=1e-8, rtol=0)
        applied = log.loc[log.status.eq('applied') & log.model.eq(head.model)
                          & log.fit_cutoff.eq(head.fit_cutoff) & log.week_block.eq(head.week_block)]
        expected = [transform(v, head.head_scale, spec, beta) for v in applied.forecast_qty]
        np.testing.assert_allclose(expected, applied.corrected_forecast_qty, atol=1e-8, rtol=0)
        count += 1
    return count


def run(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run id')
    path = ROOT/'data/configs/m2-focus.json'
    experiment = json.loads(path.read_text(encoding='utf-8'))
    assert tuple(experiment['focus_route']) == FOCUS
    cfg = read_config(experiment['base_config'])
    settings = load_settings(ROOT/experiment['model_config'])
    old = ROOT/'M2/artifacts'/experiment['reference_run']
    reference_manifest = validate_run(old)
    calendar_run = ROOT/'M2/artifacts/m2_calendar_20261011'
    validate_run(calendar_run)
    protected = {**protected_files(old), **{p.relative_to(ROOT).as_posix(): sha256(p) for p in calendar_run.rglob('*') if p.is_file()}}
    out = ROOT/'M2/artifacts'/run_id
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT/cfg['source']
    manifest = new_manifest(cfg, source, run_id)
    manifest.update(experiment=experiment, settings=settings, candidates=candidates(experiment),
        config_sha256=sha256(path), implementation_modules_sha256=implementation_hashes(), protected_before=protected,
        selection_test_policy=experiment['test_policy'], production_modified=False)
    write_json(out/'protocol.json', manifest); write_json(out/'manifest.json', manifest)
    print(f'Preregistered {len(candidates(experiment))} candidates; auditing raw', flush=True)
    sales, audit = audit_orders(source, cfg)
    daily = daily_sales(sales, cfg); top = route_top(daily, cfg)
    assert manifest['source_sha256'] == reference_manifest['source_sha256'] and daily.sales_qty.sum() == audit['sales_quantity']
    focused = daily.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    for name, frame in [('daily_sales', daily), ('top_routes', top)]:
        write_csv(out/f'{name}.csv', frame)
    write_json(out/'data_audit.json', audit)
    checks = {'source_quantity_conserved': True}
    folds = []
    for start, end in experiment['historical_folds']:
        cutoff = pd.Timestamp(start)-pd.Timedelta(days=1)
        fold_cfg = {**cfg, 'train_end': cutoff, 'validation_start': start, 'validation_end': end}
        population = route_top(daily, fold_cfg)
        subset = daily.loc[daily.date.le(end)].merge(population[ROUTE], on=ROUTE, validate='many_to_one')
        predictions, log = phase(subset, fold_cfg, settings, experiment, 'validation')
        table = metrics(predictions, fold_cfg); table['fold_start'] = start
        folds.append(table)
        write_csv(out/f'history_{start}_predictions.csv', predictions)
        write_csv(out/f'history_{start}_fit_log.csv', log)
        checks[f'history_{start}_labels'] = reconcile_labels(predictions, subset, fold_cfg)
        checks[f'history_{start}_heads'] = verify_heads(log, experiment, subset)
    write_csv(out/'historical_metrics.csv', pd.concat(folds, ignore_index=True))
    validation, log = phase(focused, cfg, settings, experiment, 'validation')
    table = metrics(validation, cfg)
    for name, frame in [('validation_predictions', validation), ('validation_metrics', table),
                        ('validation_fit_log', log), ('validation_monthly_metrics', monthly_metrics(validation, cfg))]:
        write_csv(out/f'{name}.csv', frame)
    checks['validation_labels'] = reconcile_labels(validation, focused, cfg)
    checks['validation_metrics'] = reconcile_metrics(validation, table, cfg)
    checks['validation_heads'] = verify_heads(log, experiment, focused)
    prior = load_predictions(old/'LightGBM/direct_7d/validation_predictions.csv')
    errors = []
    for new, previous in [('focus_control_raw', 'lgbm_annual_ratio7'), ('focus_control_mul56p4', 'lgbm_cal_ratio7_56_p4')]:
        left = validation.loc[validation.model.eq(new)]
        right = prior.loc[prior.model.eq(previous) & prior.carrier.eq(FOCUS[1])]
        joined = left.merge(right, on=ROUTE+['as_of_date','block'], suffixes=('', '_old'), validate='one_to_one')
        assert len(joined) == len(left) == len(right)
        np.testing.assert_allclose(joined.forecast_qty, joined.forecast_qty_old, atol=1e-8, rtol=0)
        errors.append(float((joined.forecast_qty-joined.forecast_qty_old).abs().max()))
    checks['control_max_difference'] = max(errors)
    chosen = select(table, validation, cfg).iloc[0]
    control = table.loc[table.model.eq('focus_control_mul56p4') & table.block.eq(1) & table.cadence.eq('daily_origins')].iloc[0]
    improved = bool(chosen.validation_mape_positive_pct < control.mape_positive_pct-experiment['numeric_tolerance'])
    locked = pd.read_csv(old/'overall_selected_models.csv')
    locked = locked.loc[locked.target.eq('direct_7d')].copy()
    mask = locked.carrier.eq(FOCUS[1]) & locked.destination_country.eq(FOCUS[0])
    if improved:
        locked.loc[mask, ['family','model','validation_mape_positive_pct','validation_mae']] = [chosen.family,chosen.model,chosen.validation_mape_positive_pct,chosen.validation_mae]
    write_csv(out/'selected_models.csv', locked)
    lock = {'selected_model': chosen.model if improved else 'focus_control_mul56p4',
        'locked_at_utc': datetime.now(timezone.utc).isoformat(), 'selected_sha256': sha256(out/'selected_models.csv'),
        'test_scored_if_improved': improved, 'nine_routes_frozen': True}
    write_json(out/'selection_lock.json', lock)
    result = {'validation_improved': improved, 'selected_model': lock['selected_model'],
        'validation_control_mape_pct': control.mape_positive_pct, 'validation_selected_mape_pct': chosen.validation_mape_positive_pct,
        'test_scored': False, 'goal_achieved': False}
    if improved:
        print(f'Locked {chosen.model}; scoring one retrospective test', flush=True)
        test, test_log = phase(focused, cfg, settings, experiment, 'test', [chosen.model])
        old_test = load_predictions(old/'overall_test_predictions.csv')
        old_test = old_test.loc[old_test.target.eq('direct_7d')]
        others = old_test.loc[~(old_test.destination_country.eq(FOCUS[0]) & old_test.carrier.eq(FOCUS[1]))]
        combined = combine_frozen(old_test, test)
        scored = metrics(combined, cfg)
        for name, frame in [('focus_test_predictions',test),('test_fit_log',test_log),('overall_test_predictions',combined),('overall_test_metrics',scored)]:
            write_csv(out/f'{name}.csv',frame)
        checks['test_labels'] = reconcile_labels(combined, focused, cfg)
        checks['test_metrics'] = reconcile_metrics(combined,scored,cfg)
        checks['test_heads'] = verify_heads(test_log,experiment,focused)
        saved = load_predictions(out/'overall_test_predictions.csv')
        preserved = saved.loc[~saved.carrier.eq(FOCUS[1])].reset_index(drop=True)
        pd.testing.assert_frame_equal(preserved, others.reset_index(drop=True),check_exact=True)
        checks['other_nine_predictions_exact'] = len(others)
        primary = scored.loc[scored.block.eq(1) & scored.cadence.eq('daily_origins')]
        focus_score = primary.loc[primary.carrier.eq(FOCUS[1])].iloc[0]
        old_scored = metrics(old_test,cfg)
        old_focus = old_scored.loc[old_scored.carrier.eq(FOCUS[1]) & old_scored.block.eq(1) & old_scored.cadence.eq('daily_origins')].iloc[0]
        comparison = primary.merge(old_scored.loc[old_scored.block.eq(1) & old_scored.cadence.eq('daily_origins')],on=ROUTE,suffixes=('_new','_old'),validate='one_to_one')
        write_csv(out/'before_after_routes.csv',comparison)
        result.update(test_scored=True,focus_test_mape_pct=focus_score.mape_positive_pct,reference_focus_test_mape_pct=old_focus.mape_positive_pct,
            goal_achieved=bool(focus_score.mape_positive_pct<20 and focus_score.coverage==1 and focus_score.mape_positive_pct<old_focus.mape_positive_pct),
            top10_passes_20_pct=int(primary.passes_20_pct.sum()))
        future, future_log = phase(focused,cfg,settings,experiment,'future',[chosen.model])
        write_csv(out/'focus_future_predictions.csv',future); write_csv(out/'future_fit_log.csv',future_log)
        checks['future_labels'] = reconcile_labels(future,focused,cfg)
    assert sha256(out/'selected_models.csv') == lock['selected_sha256'] and sha256(source)==manifest['source_sha256']
    for name,digest in protected.items():
        assert sha256(ROOT/name)==digest,name
    checks.update(status='passed',protected_files_unchanged=len(protected),selection_lock_unchanged=True,source_hash_unchanged=True)
    write_json(out/'verification.json',checks); write_json(out/'result.json',result)
    primary = table.loc[table.block.eq(1) & table.cadence.eq('daily_origins')].sort_values(['mape_positive_pct','mae','model'])
    rows='\n'.join(f'| {r.model} | {r.mape_positive_pct:.6f} | {r.mae:.6f} | {r.coverage:.0%} |' for r in primary.itertuples())
    (out/'README.md').write_text(f'''# LG U+ — {run_id}

Nghiên cứu local, test đã xem trước là hồi cứu; R05 ngày/R07/T14 giữ mở. Chín tuyến khác giữ nguyên dự báo/lựa chọn cũ; dashboard và báo cáo khóa không đổi.

Kết quả: `{json.dumps(result,ensure_ascii=False)}`

| Ứng viên | MAPE validation % | MAE | Coverage |
|---|---:|---:|---:|
{rows}

[Protocol](protocol.json), [lựa chọn khóa trước test](selection_lock.json), [kiểm chứng](verification.json), [metric h1–7/h8–14 và cadence](validation_metrics.csv), [hai cửa sổ lịch sử](historical_metrics.csv).

35 ứng viên được đăng ký trước fit; hai cửa sổ lịch sử là chẩn đoán, không thay tiêu chí validation. Top10 ở mỗi cửa sổ lịch sử tính từ dữ liệu trước origin đầu kỳ; top10 validation/test tính từ train chính. Model học country/local vẫn chỉ xuất LG U+; feature và nhãn không nhìn tương lai. Chuẩn hóa28/56/90 ngày; cờ gần đây là tỷ lệ đã biết tại origin. Residual head ridge theo sai số tương đối có prior về0, clip±25% scale ở cutoff. Teacher các tuần không chồng chỉ dùng khi nhãn hoàn tất. Blend trọng số cố định, không chọn theo test.
''',encoding='utf-8')
    manifest.update(status='complete',result=result,finished_at_utc=datetime.now(timezone.utc).isoformat())
    seal_manifest(out,manifest)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    run(parser.parse_args().run_id)
