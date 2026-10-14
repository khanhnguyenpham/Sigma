"""Fresh replay of ten fixed weekly choices and an aggregate M2 final report."""
import argparse
import base64
import importlib.metadata
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import json
import os
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, new_manifest, seal_manifest, validate_run
from src.data import audit_orders, daily_sales, route_top
from M2.models.weekly import checked_series
from M2.models.registry import load_settings, implementation_hashes
from M2.models.LightGBM.model import phase as lgbm_phase
from M2.models.families import ts_job, metrics, monthly_metrics
from M2.models.focus import FOCUS, phase as focus_phase, verify_heads, load_predictions
from M2.models.verify import reconcile_labels, reconcile_metrics

CONFIG = 'data/configs/m2-final.json'
REPORT = ROOT/'M2/reports/final_m2_20261011'
PAIR = ROUTE+['as_of_date', 'block']


def focus_experiment(exp):
    route = next(r for r in exp['routes'] if (r['destination_country'], r['carrier']) == FOCUS)
    parent, head = route['model'].rsplit('_', 1)
    return {'parents': {parent: {'scale_days': route['scale_days'], 'training_window_days': route['training_window_days']}},
        'heads': {head: {'kind': 'multiply', 'history_days': route['head_history_days'], 'prior_weeks': route['head_prior_weeks']}}}


def configurations(exp, settings):
    """One authoritative effective configuration per route, including Prophet differences."""
    rows = []
    for route in exp['routes']:
        family, name = route['family'], route['model']
        is_focus = (route['destination_country'], route['carrier']) == FOCUS
        spec = settings['models'][family]['lgbm_annual_ratio7' if is_focus else name]
        ratio = spec.get('units') == 'ratio'
        prophet = family == 'Prophet'
        rows.append({**route, 'target': 'direct_7d',
            'training_window_days': route.get('training_window_days', spec.get('training_window_days', settings['training_window_days'])),
            'normalization_days': route.get('scale_days', 90) if ratio else None,
            'normalization': 'max(1, past_daily_mean_times7)' if ratio else 'quantity_units',
            'training_population': 'own_route' if prophet else 'train_top10_pooled',
            'objective': 'Prophet MAP' if prophet else spec['objective'],
            'inverse_target_weighting': not prophet and spec['objective'] == 'regression_l1',
            'annual_features': bool(spec.get('yearly_seasonality')) if prophet else spec.get('annual_features', False),
            'weekly_seasonality': spec.get('weekly_seasonality') if prophet else None,
            'yearly_fourier_order': spec.get('yearly_seasonality') if prophet else None,
            'seasonality_mode': spec.get('seasonality_mode') if prophet else None,
            'changepoint_prior_scale': spec.get('changepoint_prior_scale') if prophet else None,
            'n_changepoints': 10 if prophet else None,
            'trees': None if prophet else settings['n_estimators'], 'leaves': None if prophet else spec['leaves'],
            'min_child_samples': None if prophet else spec.get('min_child_samples', settings['min_child_samples']),
            'learning_rate': None if prophet else settings['learning_rate'],
            'reg_lambda': None if prophet else settings['reg_lambda'],
            'refit_days': settings['refit_days'], 'seed': 42, 'horizon_days': 14, 'block_days': 7,
            'head_history_days': route.get('head_history_days', 0), 'head_prior_weeks': route.get('head_prior_weeks', 0),
            'holiday_features': False, 'recent_or_distribution_features': False,
            'minimum_history_days': settings['minimum_history_days'],
            'features': 'trend + yearly Fourier3 + weekly seasonality on rolling7 totals' if prophet else
                'route/block/weekday/month/year_sin/year_cos/elapsed_days + quantity rolling7/14/28/90 + previous7/std28/positive_share28 + orders28/basket28'
                + (' + prior-year7/28/90' if spec.get('annual_features') else '')})
    return pd.DataFrame(rows)


def replay(daily, cfg, settings, exp, split):
    groups = {key: part.sales_qty.astype(float) for key, part in checked_series(daily).items()}
    choices = {(r['destination_country'], r['carrier']): r['model'] for r in exp['routes']
               if r['family'] == 'LightGBM' and (r['destination_country'], r['carrier']) != FOCUS}
    selected_groups = {key: groups[key] for key in choices}
    prophet = next(r for r in exp['routes'] if r['family'] == 'Prophet')
    key = (prophet['destination_country'], prophet['carrier'])
    with ProcessPoolExecutor(max_workers=settings['workers']) as pool:
        jobs = [pool.submit(lgbm_phase, daily, selected_groups, cfg, settings, 'direct_7d', split, choices),
            pool.submit(focus_phase, daily, cfg, settings, focus_experiment(exp), split),
            pool.submit(ts_job, groups[key], key, 'Prophet', 'direct_7d', prophet['model'],
                        settings['models']['Prophet'][prophet['model']], cfg, settings, split)]
        output = [job.result() for job in jobs]
    frames = []
    for index, (frame, log) in enumerate(output):
        if index == 1: frame = frame.assign(family='LightGBM')
        frames.append(frame)
    return pd.concat(frames, ignore_index=True), {'lightgbm': output[0][1], 'focus': output[1][1], 'prophet': output[2][1]}


def check_pairs(frame, daily, cfg, exp, split):
    expected_routes = {(r['destination_country'], r['carrier']): r['model'] for r in exp['routes']}
    assert set(frame[ROUTE].itertuples(index=False, name=None)) == set(expected_routes)
    origins = ([daily.date.max()] if split == 'future' else pd.date_range(
        pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1), pd.Timestamp(cfg[f'{split}_end'])-pd.Timedelta(days=1)))
    expected = pd.MultiIndex.from_product([origins, [1, 2]], names=['as_of_date', 'block'])
    for key, part in frame.groupby(ROUTE):
        assert part.model.nunique() == 1 and part.model.iloc[0] == expected_routes[key]
        observed = pd.MultiIndex.from_frame(part[['as_of_date', 'block']])
        assert observed.is_unique and observed.sort_values().equals(expected), 'Missing or duplicate forecast pair'
    return reconcile_labels(frame, daily, cfg)


def parity(frame, previous, tolerance):
    joined = frame.merge(previous, on=PAIR+['model'], suffixes=('', '_old'), validate='one_to_one')
    assert len(joined) == len(frame) == len(previous)
    for column in ['forecast_qty', 'actual_qty']:
        np.testing.assert_allclose(joined[column], joined[column+'_old'], atol=tolerance if column == 'forecast_qty' else 0,
                                   rtol=0, equal_nan=True)
    return {'pairs': len(joined), 'max_forecast_difference': float((joined.forecast_qty-joined.forecast_qty_old).abs().max())}


def run(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id): raise ValueError('Invalid run ID')
    path = ROOT/CONFIG; exp = json.loads(path.read_text(encoding='utf-8'))
    cfg = read_config(exp['base_config']); settings = load_settings(ROOT/exp['model_config'])
    assert cfg['seed'] == 42 and len(exp['routes']) == 10
    source = ROOT/cfg['source']; assert sha256(source) == exp['source_sha256']
    assert len({(r['destination_country'], r['carrier']) for r in exp['routes']}) == 10
    for name, digest in [('reference_run', exp['reference_manifest_sha256']), ('sweep_run', exp['sweep_manifest_sha256'])]:
        previous = ROOT/'M2/artifacts'/exp[name]
        validate_run(previous); assert sha256(previous/'manifest.json') == digest
    assert (ROOT/'M2/artifacts'/exp['refinement_run']/'validation_predictions.csv').is_file()
    protected = {source.relative_to(ROOT).as_posix(): sha256(source)}
    for base in [ROOT/'M2/artifacts', ROOT/'M2/reports/published_m2_20261007']:
        protected.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in base.rglob('*') if p.is_file()})
    out = ROOT/'M2/artifacts'/run_id; out.mkdir(exist_ok=False)
    manifest = new_manifest(cfg, source, run_id)
    manifest['packages']['prophet'] = importlib.metadata.version('prophet')
    manifest.update(experiment=exp, settings=settings, config_sha256=sha256(path),
        implementation_modules_sha256=implementation_hashes(), runner_sha256=sha256(__file__),
        protected_before=protected, production_inventory_modified=False,
        selection_limit=exp['evaluation_limit'], test_independent=False)
    write_json(out/'protocol.json', manifest)
    write_json(out/'manifest.json', manifest)
    selected = pd.DataFrame(exp['routes']).assign(target='direct_7d')
    write_csv(out/'selected_models.csv', selected)
    write_json(out/'selection_lock.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'selection_sha256': sha256(out/'selected_models.csv'), 'config_sha256': sha256(path),
        'selection_basis': 'nine original validation choices and one prior test-sweep winner, fixed by user before this rerun',
        'independent_test': False})
    print('Ten choices locked; fresh raw audit and replay, no candidate search', flush=True)
    sales, audit = audit_orders(source, cfg); daily = daily_sales(sales, cfg); top = route_top(daily, cfg)
    assert daily.sales_qty.sum() == audit['sales_quantity']
    assert set(top[ROUTE].itertuples(index=False, name=None)) == set(selected[ROUTE].itertuples(index=False, name=None))
    focused = daily.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    write_csv(out/'daily_sales.csv', daily); write_csv(out/'top_routes.csv', top); write_json(out/'data_audit.json', audit)
    write_csv(out/'model_configurations.csv', configurations(exp, settings))
    checks = {}
    for split in ['validation', 'test', 'future']:
        write_json(out/f'{split}_execution.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
            'selection_lock_sha256': sha256(out/'selection_lock.json'), 'fresh_fit': True})
        pred, logs = replay(focused, cfg, settings, exp, split)
        write_csv(out/f'{split}_predictions.csv', pred)
        for name, log in logs.items(): write_csv(out/f'{split}_{name}_fit_log.csv', log)
        checks[split+'_pairs'] = check_pairs(pred, focused, cfg, exp, split)
        checks[split+'_heads'] = verify_heads(logs['focus'], focus_experiment(exp), focused)
        if split != 'future':
            table = metrics(pred, cfg); write_csv(out/f'{split}_metrics.csv', table)
            checks[split+'_metrics'] = reconcile_metrics(pred, table, cfg)
            assert len(table) == 40 and table.coverage.eq(1).all()
            if split == 'validation': write_csv(out/'validation_monthly_metrics.csv', monthly_metrics(pred, cfg))
        print(f'Fresh {split} replay and causal checks complete', flush=True)
    for name, digest in protected.items(): assert sha256(ROOT/name) == digest, f'Previous artifact changed: {name}'
    checks['protected_files_unchanged'] = len(protected); checks['raw_quantity_conserved'] = True
    write_json(out/'verification.json', checks)
    primary = metrics(load_predictions(out/'test_predictions.csv'), cfg)
    primary = primary.loc[primary.block.eq(1) & primary.cadence.eq('daily_origins')]
    result = {'routes': len(primary), 'routes_below_20_pct': int((primary.coverage.eq(1) & primary.mape_positive_pct.lt(20)).sum()),
        'mean_mape_positive_pct': primary.mape_positive_pct.mean(), 'minimum_coverage': primary.coverage.min(),
        'goal_achieved': bool(primary.coverage.eq(1).all() and primary.mape_positive_pct.lt(20).all()),
        'independent_test': False, 'daily_R05_acceptance_replaced': False}
    manifest.update(status='complete', result=result, finished_at_utc=datetime.now(timezone.utc).isoformat())
    seal_manifest(out, manifest)
    print(json.dumps(result), flush=True)
    return out


def read_log(path):
    frame = pd.read_csv(path, float_precision='round_trip')
    for name in ['fit_cutoff', 'as_of_date', 'teacher_origin', 'max_label_end', 'head_label_end', 'max_head_label_end']:
        if name in frame: frame[name] = pd.to_datetime(frame[name])
    return frame


def verify_run(run_id, *, artifacts_only=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run ID')
    out = ROOT/'M2/artifacts'/run_id; manifest = validate_run(out)
    cfg, exp = manifest['config'], manifest['experiment']
    recorded_code = manifest['implementation_modules_sha256']
    current_code_matches = (sha256(ROOT/CONFIG) == manifest['config_sha256']
        and sha256(__file__) == manifest['runner_sha256']
        and all((ROOT/name).is_file() and sha256(ROOT/name) == digest for name, digest in recorded_code.items()))
    if not artifacts_only and not current_code_matches:
        raise ValueError('Recorded code differs; use verify-artifacts for historical evidence or restore the backup branch')
    assert sha256(ROOT/cfg['source']) == manifest['source_sha256'], 'Raw source changed'
    sales, audit = audit_orders(ROOT/cfg['source'], cfg)
    daily = daily_sales(sales, cfg); top = route_top(daily, cfg)
    pd.testing.assert_frame_equal(daily, pd.read_csv(out/'daily_sales.csv', parse_dates=['date'], float_precision='round_trip'))
    pd.testing.assert_frame_equal(top, pd.read_csv(out/'top_routes.csv'))
    focused = daily.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    selection = pd.read_csv(out/'selected_models.csv', float_precision='round_trip')
    expected = pd.DataFrame(exp['routes']).assign(target='direct_7d')
    pd.testing.assert_frame_equal(selection, expected)
    lock = json.loads((out/'selection_lock.json').read_text(encoding='utf-8'))
    assert lock['selection_sha256'] == sha256(out/'selected_models.csv')
    checks = {'fresh_raw_rows': audit['rows_raw'], 'sales_quantity': audit['sales_quantity'], 'train_top10_exact': True,
        'current_code_matches_recorded_run': current_code_matches}
    for split in ['validation', 'test', 'future']:
        pred = load_predictions(out/f'{split}_predictions.csv')
        checks[split+'_pairs'] = check_pairs(pred, daily, cfg, exp, split)
        log = read_log(out/f'{split}_focus_fit_log.csv')
        checks[split+'_heads'] = verify_heads(log, focus_experiment(exp), focused)
        execution = json.loads((out/f'{split}_execution.json').read_text(encoding='utf-8'))
        assert lock['created_at_utc'] <= execution['started_at_utc']
        assert execution['selection_lock_sha256'] == sha256(out/'selection_lock.json') and execution['fresh_fit']
        for component in ['lightgbm', 'focus', 'prophet']:
            fits = read_log(out/f'{split}_{component}_fit_log.csv')
            if 'max_label_end' in fits:
                rows = fits.loc[fits.max_label_end.notna()]
                assert (rows.max_label_end <= rows.fit_cutoff).all()
            assert not fits.status.eq('failed').any()
        if split == 'future': continue
        table = pd.read_csv(out/f'{split}_metrics.csv', float_precision='round_trip')
        checks[split+'_metrics'] = reconcile_metrics(pred, table, cfg)
        old = ROOT/'M2/artifacts'/exp['reference_run']
        if old.exists():
            validate_run(old); assert sha256(old/'manifest.json') == exp['reference_manifest_sha256']
            if split == 'test':
                previous = load_predictions(old/'overall_test_predictions.csv')
                previous = previous.loc[previous.target.eq('direct_7d')]
            else:
                frames = [load_predictions(old/r['family']/'direct_7d/validation_predictions.csv').loc[
                    lambda f: f.destination_country.eq(r['destination_country']) & f.carrier.eq(r['carrier']) & f.model.eq(r['model'])]
                    for r in exp['routes'] if (r['destination_country'], r['carrier']) != FOCUS]
                previous = pd.concat(frames, ignore_index=True)
            other = ~(pred.destination_country.eq(FOCUS[0]) & pred.carrier.eq(FOCUS[1]))
            old_other = ~(previous.destination_country.eq(FOCUS[0]) & previous.carrier.eq(FOCUS[1]))
            checks[split+'_other_nine_parity'] = parity(pred.loc[other], previous.loc[old_other], exp['numeric_tolerance'])
        parent = ROOT/'M2/artifacts'/(exp['sweep_run'] if split == 'test' else exp['refinement_run'])
        if parent.exists():
            validate_run(parent)
            previous = load_predictions(parent/('refinement/test_predictions.csv' if split == 'test' else 'validation_predictions.csv'))
            previous = previous.loc[previous.model.eq('tune56_w540_mul56p4')]
            checks[split+'_focus_parity'] = parity(pred.loc[pred.carrier.eq(FOCUS[1])], previous, exp['numeric_tolerance'])
    for name, digest in manifest['protected_before'].items(): assert sha256(ROOT/name) == digest
    checks['protected_files_unchanged'] = len(manifest['protected_before'])
    receipt = {'status': 'artifacts_verified' if artifacts_only else 'verified',
        'verification_scope': 'raw, labels, metrics, causal logs and artifact hashes; no model refit' if artifacts_only else 'current code and run artifacts',
        'run_id': run_id, 'run_manifest_sha256': sha256(out/'manifest.json'),
        'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks, 'result': manifest['result']}
    if not artifacts_only:
        path = out.with_name(run_id+'_review.json')
        if path.exists(): raise FileExistsError('Never overwrite an existing verification receipt')
        write_json(path, receipt)
    print(json.dumps(receipt), flush=True)
    return receipt


def markdown_table(frame):
    return '| '+' | '.join(frame.columns)+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+''.join(
        '| '+' | '.join(str(value) for value in row)+' |\n' for row in frame.itertuples(index=False, name=None))


def export_report(run_id, report_id=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id): raise ValueError('Invalid run ID')
    folder = ROOT/'M2/artifacts'/run_id; manifest = validate_run(folder)
    receipt_path = folder.with_name(run_id+'_review.json'); receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    assert receipt['status'] == 'verified' and receipt['run_manifest_sha256'] == sha256(folder/'manifest.json')
    report_id = report_id or manifest['experiment']['report_id']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', report_id): raise ValueError('Invalid report ID')
    out = ROOT/'M2/reports'/report_id; out.mkdir(parents=True, exist_ok=False)
    configs = configurations(manifest['experiment'], manifest['settings'])
    write_json(out/'model_configurations.json', configs.to_dict(orient='records'))
    for name in ['selected_models.csv', 'test_metrics.csv', 'validation_metrics.csv', 'validation_monthly_metrics.csv']:
        frame = pd.read_csv(folder/name, float_precision='round_trip'); write_csv(out/name, frame)
    primary = pd.read_csv(out/'test_metrics.csv', float_precision='round_trip')
    primary = primary.loc[primary.block.eq(1) & primary.cadence.eq('daily_origins')]
    selected = pd.read_csv(out/'selected_models.csv', float_precision='round_trip')
    routes = selected.merge(primary, on=ROUTE+['family', 'target', 'model'], validate='one_to_one').sort_values(ROUTE)
    old = ROOT/'M2/artifacts'/manifest['experiment']['reference_run']
    if old.exists():
        before = pd.read_csv(old/'overall_test_metrics.csv', float_precision='round_trip')
        before = before.loc[before.target.eq('direct_7d') & before.block.eq(1) & before.cadence.eq('daily_origins')]
        comparison = routes.merge(before[ROUTE+['model', 'mape_positive_pct']], on=ROUTE, suffixes=('', '_before'), validate='one_to_one')
        write_csv(out/'before_after_routes.csv', comparison[ROUTE+['model_before', 'model', 'mape_positive_pct_before', 'mape_positive_pct']])
    config_table = configs[ROUTE+['family', 'model', 'training_window_days', 'normalization_days', 'training_population', 'refit_days']].copy()
    config_table['normalization_days'] = config_table.normalization_days.map(lambda v: str(int(v)) if pd.notna(v) else 'Không chuẩn hóa tỷ lệ')
    config_table.columns = ['Điểm đến', 'Nhà mạng', 'Họ', 'Model', 'Lịch sử học (ngày)', 'Mốc bán (ngày)', 'Dữ liệu học', 'Refit (ngày)']
    config_text = '# Cấu hình 10 mô hình cho 10 tuyến M2\n\n'+markdown_table(config_table)
    config_text += '\nMỗi dòng là một cấu hình theo tuyến; các tuyến có thể dùng chung biến thể. Mốc bán = max(1, trung bình quantity/ngày trong N ngày quá khứ ×7), cập nhật theo origin. Model tỷ lệ chia nhãn và feature lượng bán cho mốc này, rồi nhân dự báo trở lại quantity. Không có mốc bán nghĩa mô hình học quantity gốc. Lịch sử học là cửa sổ tối đa của nhãn hoàn tất trước cutoff; tối thiểu90 ngày đầu vào. Refit trượt7 ngày, được học thêm nhãn validation/test đã hoàn tất trước origin, không khóa mãi tại30/06/2025.\n\n'
    config_text += 'LightGBM học pooled trên top10 train, 150 cây, learning-rate0,03, lambda10, seed42. Bộ feature gồm route/block/thứ/tháng, sin/cos năm, ngày từ đầu chuỗi, tổng7/14/28/90, tuần trước, std28, tỷ lệ ngày bán dương28, số đơn và quantity/đơn28; bản annual thêm tổng7 và trung bình28/90 cùng kỳ năm trước. Không dùng lễ hoặc feature cơ cấu đơn trong bộ final.\n\n'
    details = configs[ROUTE+['objective', 'leaves', 'min_child_samples', 'annual_features', 'head_history_days', 'head_prior_weeks']].fillna('—')
    details.columns = ['Điểm đến', 'Nhà mạng', 'Loss', 'Số lá', 'Min child', 'Feature năm', 'Lịch sử hiệu chỉnh', 'Prior tuần']
    config_text += markdown_table(details)
    config_text += '\nLoss regression_l1 dùng inverse-target weights; poisson dùng weights=1. LG U+ chuẩn hóa56/học540 ngày, đầu nhân56 ngày/prior4 tuần. Prophet au(KDDI) học riêng tuyến từ tổng trượt7, cửa sổ540, additive, Fourier năm3, mùa vụ tuần bật, changepoint prior0,01, 10 changepoints; không chuẩn hóa tỷ lệ.\n\n'
    config_text += 'H14, h1–7 chính/h8–14 riêng, refit7, seed42. Chín tuyến giữ lựa chọn validation cũ; LG U+ chọn qua test-sweep theo yêu cầu người dùng. [Tham số máy đọc đầy đủ](model_configurations.json).\n'
    (out/'model_configurations.md').write_text(config_text, encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh([f'{r.destination_country} / {r.carrier}' for r in routes.itertuples()], routes.mape_positive_pct, color='#217d91')
    ax.axvline(20, color='#c44c3c', linestyle='--', label='20%'); ax.invert_yaxis()
    ax.set_xlabel('MAPE total quantity D+1…D+7 (%)'); ax.set_title('M2 final — retrospective test, fixed 10-route bundle')
    for i, value in enumerate(routes.mape_positive_pct): ax.text(value+.15, i, f'{value:.2f}%', va='center')
    ax.set_xlim(0, max(23, routes.mape_positive_pct.max()+3)); ax.legend(); fig.tight_layout()
    fig.savefig(out/'route_comparison.png', dpi=160); plt.close(fig)
    display = routes[ROUTE+['family', 'model', 'mape_positive_pct', 'mae', 'wape_pct', 'bias', 'coverage', 'selection_basis']].copy()
    for column in ['mape_positive_pct', 'mae', 'wape_pct', 'bias']: display[column] = display[column].map(lambda v: f'{v:.6f}')
    result = manifest['result']; cfg = manifest['config']
    report = '# SIGMA — Báo cáo final M2 · 11/10/2026\n\n'
    report += f'**Tổng quantity7 ngày: {result["routes_below_20_pct"]}/10 tuyến MAPE test<20%, trung bình {result["mean_mape_positive_pct"]:.6f}%, coverage {result["minimum_coverage"]:.0%}.** Chạy lại mới validation/test/future từ CSV gốc với10 lựa chọn cố định.\n\n'
    report += '**Test hồi cứu:** chín tuyến chọn từ validation trước đây; LG U+ được chọn bằng test-sweep160 cấu hình rồi người dùng yêu cầu đưa vào bộ final. Lượt rerun này kiểm tái lập, không tạo holdout độc lập.\n\n'
    report += markdown_table(display)+'\n![MAPE từng tuyến](route_comparison.png)\n\n'
    report += 'Target: tổng quantity success theo ngày đặt UTC, A08 thực nghiệm; top10 theo train. Train01/01/2024–30/06/2025, validation01/07–30/09/2025, test01/10–31/12/2025. H14, h1–7 chính; mỗi tuyến86 cặp đủ nhãn h1–7/79 cặp h8–14. Không bỏ đỉnh/ngày khó, không thay actual hoặc mẫu số.\n\n'
    focus_h1 = routes.loc[routes.carrier.eq(FOCUS[1]), 'mape_positive_pct'].item()
    full_metrics = pd.read_csv(out/'test_metrics.csv', float_precision='round_trip')
    focus_h2 = full_metrics.loc[full_metrics.carrier.eq(FOCUS[1]) & full_metrics.block.eq(2) & full_metrics.cadence.eq('daily_origins'), 'mape_positive_pct'].item()
    report += f'LG U+ đạt{focus_h1:.6f}%; h8–14 còn{focus_h2:.6f}%. Xem bảng trước/sau, metric đủ40 nhóm và cadence không chồng lấn. MAPE tổng không thay R05 theo ngày; R05 ngày/R07/T14 còn mở, chưa nghiệm thu toàn bài. Tồn/lead time/mapping không thuộc lượt final này. Snapshot trạng thái cuối không tái dựng dữ liệu tại origin vận hành.\n\n'
    report += '[Cấu hình 10 tuyến](model_configurations.md) · [Metric test](test_metrics.csv) · [Metric validation](validation_metrics.csv) · [Ổn định validation tháng](validation_monthly_metrics.csv) · [Bản HTML offline](index.html) · [Đối soát](verification_summary.json)\n\n'
    report += f'Run local: `{run_id}`. Raw SHA `{manifest["source_sha256"]}`. Run manifest SHA `{sha256(folder/"manifest.json")}`. Raw/daily/per-origin forecast giữ local; GitHub chỉ có mã, cấu hình và bảng tổng hợp.\n'
    (out/'README.md').write_text(report, encoding='utf-8')
    table_html = routes[ROUTE+['family', 'model', 'mape_positive_pct', 'mae', 'wape_pct', 'bias', 'coverage', 'selection_basis']].to_html(index=False, float_format=lambda v: f'{v:.4f}', border=0)
    image = base64.b64encode((out/'route_comparison.png').read_bytes()).decode()
    document = '<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGMA — M2 final</title><style>body{font:16px/1.6 system-ui;color:#16334a;max-width:1280px;margin:auto;padding:30px;background:#f4f7fa}table{border-collapse:collapse;background:white;font-size:13px;width:100%}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}.table{overflow:auto}img{max-width:100%}.note{padding:14px;background:#fff0d4}h1,h2{color:#176376}@media print{body{padding:0;background:white}table{font-size:10px}}</style><main>'
    document += f'<h1>SIGMA · M2 final · 11/10/2026</h1><p><strong>{result["routes_below_20_pct"]}/10 tuyến MAPE tổng7 test&lt;20% · trung bình {result["mean_mape_positive_pct"]:.4f}% · coverage100%.</strong></p>'
    document += f'<p class="note">Test hồi cứu: LG U+ chọn qua test-sweep; chín tuyến giữ lựa chọn validation. Rerun xác minh tái lập. R05 theo ngày/R07/T14 còn mở. H8–14 LG U+ {focus_h2:.4f}%.</p><h2>Kết quả 10 tuyến</h2><div class="table">'+table_html+'</div>'
    document += f'<img alt="MAPE từng tuyến" src="data:image/png;base64,{image}"><h2>Cấu hình</h2><div class="table">'+config_table.to_html(index=False, border=0)+'</div>'
    document += '<p>Target quantity success/ngày đặt UTC; top10 train; train2024–06/2025, validation07–09/2025, test10–12/2025. H14, refit7; chỉ nhãn đủ cửa sổ. Dữ liệu gốc và dự báo từng origin giữ local.</p><p><a href="model_configurations.md">Cấu hình đầy đủ</a> · <a href="test_metrics.csv">40 nhóm metric</a> · <a href="verification_summary.json">Đối soát</a></p></main></html>'
    (out/'index.html').write_text(document, encoding='utf-8')
    write_json(out/'verification_summary.json', receipt)
    write_json(out/'report_manifest.json', {'status': 'complete', 'run_id': run_id, 'run_manifest_sha256': sha256(folder/'manifest.json'),
        'result': result, 'config': cfg, 'selection_limit': manifest['selection_limit'],
        'files': {p.name: sha256(p) for p in out.iterdir() if p.is_file()}})
    print(out, flush=True); return out


def load_report(folder=REPORT):
    manifest = json.loads((folder/'report_manifest.json').read_text(encoding='utf-8'))
    if manifest['status'] != 'complete': raise ValueError('Final report is incomplete')
    if not {'selected_models.csv', 'test_metrics.csv', 'model_configurations.json'} <= manifest['files'].keys():
        raise ValueError('Final report manifest is incomplete')
    for name, digest in manifest['files'].items():
        path = (folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or sha256(path) != digest: raise ValueError('Final report changed')
    choices = pd.read_csv(folder/'selected_models.csv', float_precision='round_trip')
    table = pd.read_csv(folder/'test_metrics.csv', float_precision='round_trip')
    primary = table.loc[table.block.eq(1) & table.cadence.eq('daily_origins')]
    routes = choices.merge(primary, on=ROUTE+['family', 'target', 'model'], validate='one_to_one')
    if len(routes) != 10 or routes[ROUTE].duplicated().any() or not routes.coverage.eq(1).all():
        raise ValueError('Final report needs ten complete unique routes')
    configs = pd.DataFrame(json.loads((folder/'model_configurations.json').read_text(encoding='utf-8')))
    if len(configs) != 10 or configs[ROUTE].duplicated().any(): raise ValueError('Incomplete configurations')
    if set(configs[ROUTE].itertuples(index=False, name=None)) != set(routes[ROUTE].itertuples(index=False, name=None)):
        raise ValueError('Configurations do not match report routes')
    return {'manifest': manifest, 'routes': routes, 'metrics': table, 'configurations': configs}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--stage', choices=['run', 'verify', 'verify-artifacts', 'export', 'all'], default='all')
    parser.add_argument('--report-id', help='New report directory; existing reports are never overwritten')
    args = parser.parse_args()
    if args.stage in ['run', 'all']: run(args.run_id)
    if args.stage in ['verify', 'all']: verify_run(args.run_id)
    if args.stage == 'verify-artifacts': verify_run(args.run_id, artifacts_only=True)
    if args.stage in ['export', 'all']: export_report(args.run_id, args.report_id)
