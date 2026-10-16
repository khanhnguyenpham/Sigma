"""Local calendar ablation: train discovery, validation lock, conditional test."""
import argparse
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, validate_run, seal_manifest, new_manifest
from src.data import audit_orders, daily_sales, route_top
from sigma.forecasting.weekly import checked_series
from M2.models.registry import load_settings, implementation_hashes
from M2.models.LightGBM.model import phase
from M2.models.families import metrics, select, monthly_metrics
from M2.models.verify import reconcile_metrics, reconcile_calibration
from M2.models.calendar_reference import (CalendarReference, build_reference, analyze_train, feature_names, GROUPS)

DATE_COLUMNS = ['as_of_date', 'target_date', 'window_start']
PAIR = ROUTE + ['as_of_date', 'block']


def load_predictions(path):
    return pd.read_csv(path, parse_dates=DATE_COLUMNS)


def variants(settings, experiment):
    """Only feature groups change; each head retains the original calibration."""
    original = settings['models']['LightGBM']
    parent = 'lgbm_annual_ratio7'
    child = 'lgbm_cal_ratio7_56_p4'
    result = {}
    for group in experiment['groups']:
        if group not in GROUPS:
            raise ValueError('Unregistered calendar group')
        name = parent if group == 'none' else f'lgbm_calendar_{group}'
        head = child if group == 'none' else f'lgbm_calendar_{group}_cal56_p4'
        result[name] = {**original[parent], 'targets': ['direct_7d'],
                        'calendar_feature_columns': feature_names(group), 'calendar_group': group}
        result[head] = {**original[child], 'parent': name, 'calendar_group': group}
    return result


def compare_control(frame, reference, tolerance):
    controls = ['lgbm_annual_ratio7', 'lgbm_cal_ratio7_56_p4']
    left = frame.loc[frame.model.isin(controls)]
    right = reference.loc[reference.model.isin(controls) & reference.target.eq('direct_7d')]
    joined = left.merge(right, on=PAIR + ['model'], suffixes=('', '_reference'), validate='one_to_one')
    if len(joined) != len(left) or len(joined) != len(right):
        raise AssertionError('Control forecast pair coverage differs from reference')
    for column in ['forecast_qty', 'actual_qty']:
        np.testing.assert_allclose(joined[column], joined[f'{column}_reference'], atol=tolerance, rtol=0, equal_nan=True)
    return {'pairs': len(joined), 'maximum_forecast_difference': float((joined.forecast_qty-joined.forecast_qty_reference).abs().max())}


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


def strata_metrics(frame, reference, cfg):
    annotated = frame.copy()
    annotated['calendar_days'] = [int(reference.frame.loc[
        reference.frame.destination_country.eq(row.destination_country)
        & reference.frame.date.between(row.window_start, row.target_date), ['vn_holiday', 'destination_holiday']].any(axis=1).sum())
        for row in annotated.itertuples()]
    tables = []
    for label, mask in [('holiday_window', annotated.calendar_days.gt(0)), ('ordinary_window', annotated.calendar_days.eq(0))]:
        if mask.any():
            table = metrics(annotated.loc[mask], cfg)
            table['stratum'] = label
            table['stratum_note'] = 'Retrospective calendar grouping; not a selection criterion; coverage is within stratum'
            tables.append(table)
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def protected_files(reference):
    paths = list(reference.rglob('*')) + list((ROOT/'M2/reports/published_m2_20261007').rglob('*'))
    paths += [ROOT/'M2/report_app.py', ROOT/'M2/presentation.py', ROOT/'M2/notebooks/model_comparison.ipynb',
              ROOT/'scripts/start_m2.ps1', *list((ROOT/'docs').glob('*.docx'))]
    return {str(p.relative_to(ROOT)).replace('\\', '/'): sha256(p) for p in paths if p.is_file()}


def report(out, experiment, result, validation, comparison):
    focus = experiment['focus_route']
    primary = validation.loc[validation.destination_country.eq(focus[0]) & validation.carrier.eq(focus[1])
        & validation.block.eq(1) & validation.cadence.eq('daily_origins')].sort_values(['mape_positive_pct', 'mae', 'model'])
    table = '\n'.join(f'| {r.model} | {r.mape_positive_pct:.6f} | {r.mae:.6f} | {r.coverage:.0%} |'
                      for r in primary.itertuples())
    test_text = 'Không chấm test mới vì validation không cải thiện đối chứng.'
    if result['test_scored']:
        test_text = f"LG U+ test tổng7 h1–7: **{result['focus_test_mape_pct']:.6f}%**, đối chứng {result['reference_focus_test_mape_pct']:.6f}%. Top10 đạt≤20%: {result['top10_passes_20_pct']}/10. Mục tiêu mới <20%: {result['goal_achieved']}."
    text = f'''# Thử nghiệm lịch lễ M2 — {out.name}

Nhánh `codex/m2-calendar-forecast`. Đây là nghiên cứu local; test đã xem trước, không phải holdout độc lập. Target A08 success theo ngày đặt UTC vẫn là giả định thực nghiệm; R05 ngày/R07/T14 không được đóng bởi kết quả tuần.

## Kết quả

Chọn LG U+ bằng validation: `{result['selected_model']}`. Cải thiện validation so với đầu hiệu chỉnh hiện tại: {result['validation_improved']}.

{test_text}

| Mô hình | MAPE validation % | MAE quantity/7 ngày | Coverage |
|---|---:|---:|---:|
{table}

## CSV và cách đọc

- [Lịch đủ ngày](../../../data/reference/calendar_features.csv): 2.980 dòng ngày×điểm đến, không chứa actual/quantity/ID. Trước/sau là 7 ngày quanh kỳ lễ liên tiếp. Khoảng cách clip ở15, nghĩa là ngoài14 ngày. Một ngày có thể cùng ở sau lễ này và trước lễ khác.
- [Các đỉnh trong train](sales_peaks.csv): đỉnh ngày và cửa sổ7 ngày có thể chồng nhau, không phải số sự kiện độc lập. `increase_pct` trống khi nền0. `sources` trống khi chưa tìm được lễ trùng ngày; không bịa nguyên nhân.
- [Tổng hợp lễ/mùa](train_calendar_summary.csv) ghi cả ngày lễ không tăng bán; [đối chiếu cùng thứ](train_matched_holidays.csv) dùng ngày thường±56 ngày bên trong train, chỉ là phân tích hồi cứu.
- [Đối chứng validation](validation_metrics.csv), [theo tháng](validation_monthly_metrics.csv), [nhóm lễ/ngày thường](validation_calendar_strata.csv), [khóa lựa chọn](selection_lock.json), [kiểm chứng](verification.json).
- `calendar_features.events.json` là catalog công khai có ngày công bố và lịch đệm; provider lọc sự kiện tại **origin của từng mẫu học/teacher**, rồi tính lại trước/sau/khoảng cách. Không được join trực tiếp toàn bộ cờ hồi cứu trong CSV vào các origin quá khứ.

## Phương pháp và giới hạn

Năm nhóm feature đã đăng ký trước fit, mỗi nhóm raw-parent ratio7 và đầu hiệu chỉnh56 ngày/prior4 tuần. Chỉ thay feature; giữ estimator/seed/refit/scaling. Pooled top10; chỉ lựa chọn LG U+ được phép thay đổi, chín tuyến khác giữ forecast đã khóa từ run đối chứng, được đối soát hash/actual/metric lại.

Ngày tăng dùng trung vị28 ngày quá khứ, z≥4 hoặc tăng≥50%; tổng7 so tám tuần trước không chồng. Không bỏ đỉnh hoặc ngày0 khi chấm. Các nhóm mô tả có thể chồng nhau và không chứng minh nhân quả. Mùa hè6–8 là giả thuyết thị trường Việt Nam; xuân3–5/thu9–11 chỉ áp Japan/South Korea. CSV không có xuất phát/ngày khởi hành của khách. Lịch công chức có cuối tuần, không là lịch nghỉ của mọi khách.

Các ngày nghỉ bổ sung thiếu nguồn ngày công bố được giữ nhãn chưa rõ trong catalog và loại khỏi model; không dùng chính ngày chưa biết làm feature. Luật lặp lại của thư viện được giả định có từ trước kỳ quan sát, không nhận đã có snapshot lịch lịch sử. Thông tin trạng thái cuối order vẫn là snapshot hồi cứu.

Mã chạy: `python -m M2.models.calendar_experiment --run-id <tên-mới>`. Lệnh mặc định phân tích, validation, khóa và chỉ chấm test nếu validation cải thiện. `--stage analyze` chỉ audit/phân tích/xuất CSV. Mỗi run cần tên mới, không ghi đè run đã seal.
'''
    (out/'README.md').write_text(text, encoding='utf-8')


def run(run_id, config='data/configs/m2-calendar.json', stage='all'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run id')
    path = (ROOT/config).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Config must remain local')
    experiment = json.loads(path.read_text(encoding='utf-8'))
    if experiment['groups'] != list(GROUPS):
        raise ValueError('Expected the five preregistered calendar groups')
    cfg = read_config(experiment['base_config'])
    source = ROOT/cfg['source']
    reference_run = ROOT/'M2/artifacts'/experiment['reference_run']
    old_manifest = validate_run(reference_run)
    if old_manifest['source_sha256'] != sha256(source):
        raise ValueError('Reference source differs from current raw')
    protected = protected_files(reference_run)
    out = ROOT/'M2/artifacts'/run_id
    out.mkdir(parents=True, exist_ok=False)
    manifest = new_manifest(cfg, source, run_id)
    settings = load_settings(ROOT/experiment['model_config'])
    settings['models'] = {'LightGBM': variants(settings, experiment)}
    manifest.update(experiment=experiment, settings=settings, config_sha256=sha256(path),
        implementation_modules_sha256=implementation_hashes(), protected_before=protected,
        protocol='train discovery; validation lock; conditional previously-viewed test; nine other routes frozen',
        feature_contract={'daily': 'calendar reference has no target columns',
            'weekly': 'counts over all seven target dates; minimum clipped distances; teacher origin availability',
            'unverified_special_days': 'excluded, no future unresolved-date indicator'}, production_modified=False)
    write_json(out/'protocol.json', manifest)
    write_json(out/'manifest.json', manifest)
    print('Protocol registered; auditing raw and building calendar', flush=True)
    sales, audit = audit_orders(source, cfg)
    daily = daily_sales(sales, cfg)
    top = route_top(daily, cfg)
    calendar, events = build_reference(experiment)
    calendar_path = (ROOT/experiment['calendar_path']).resolve()
    if not calendar_path.is_relative_to(ROOT/'data/reference'):
        raise ValueError('Calendar must remain in local reference data')
    # A new run may reuse only byte-equivalent calendar content, never silently replace a different reference.
    if calendar_path.exists():
        existing = pd.read_csv(calendar_path, keep_default_na=False)
        proposed = pd.read_csv(__import__('io').StringIO(calendar.to_csv(index=False)), keep_default_na=False)
        pd.testing.assert_frame_equal(existing, proposed)
        if json.loads(calendar_path.with_suffix('.events.json').read_text(encoding='utf-8')) != events:
            raise ValueError('Existing calendar catalog differs')
    else:
        write_csv(calendar_path, calendar)
        write_json(calendar_path.with_suffix('.events.json'), events)
    write_csv(out/'calendar_features.csv', calendar)
    write_json(out/'calendar_features.events.json', events)
    reference = CalendarReference.load(calendar_path)
    focused = daily.merge(top[ROUTE], on=ROUTE, how='inner', validate='many_to_one')
    peaks, summary, matched = analyze_train(focused, cfg, reference)
    for name, frame in [('daily_sales', daily), ('top_routes', top), ('sales_peaks', peaks),
                         ('train_calendar_summary', summary), ('train_matched_holidays', matched)]:
        write_csv(out/f'{name}.csv', frame)
    write_json(out/'data_audit.json', audit)
    write_json(out/'calendar_provenance.json', {'settings': experiment, 'events': len(events),
        'calendar_sha256': sha256(calendar_path), 'catalog_sha256': sha256(calendar_path.with_suffix('.events.json')),
        'unverified_events': [e for e in events if e['known_from'] is None],
        'note': 'source checks are recorded in config; recurring-rule availability is an assumption'})
    manifest.update(calendar_sha256=sha256(calendar_path), catalog_sha256=sha256(calendar_path.with_suffix('.events.json')))
    groups = {key: part.sales_qty.astype(float) for key, part in checked_series(focused).items()}
    checks = {'raw_quantity_conserved': int(daily.sales_qty.sum()) == audit['sales_quantity'],
              'calendar_rows': len(calendar), 'train_peak_rows': len(peaks), 'train_peak_max_date': peaks.date.max(),
              'test_scored': False}
    assert checks['raw_quantity_conserved'] and peaks.date.max() <= pd.Timestamp(cfg['train_end'])
    if stage == 'analyze':
        write_json(out/'verification.json', checks)
        manifest.update(status='complete', stage='analyze', finished_at_utc=datetime.now(timezone.utc).isoformat())
        seal_manifest(out, manifest)
        print(f'Analysis complete: {out}', flush=True)
        return out
    print('Train analysis exported; fitting ten preregistered validation candidates', flush=True)
    validation, log = phase(focused, groups, cfg, settings, 'direct_7d', 'validation', calendar_reference=reference)
    table = metrics(validation, cfg)
    for name, frame in [('validation_predictions', validation), ('validation_fit_log', log),
        ('validation_metrics', table), ('validation_monthly_metrics', monthly_metrics(validation, cfg)),
        ('validation_calendar_strata', strata_metrics(validation, reference, cfg))]:
        write_csv(out/f'{name}.csv', frame)
    old_validation = load_predictions(reference_run/'LightGBM/direct_7d/validation_predictions.csv')
    checks['control_parity'] = compare_control(validation, old_validation, experiment['numeric_tolerance'])
    checks['validation_labels'] = reconcile_labels(validation, focused, cfg)
    checks['validation_metric_groups'] = reconcile_metrics(validation, table, cfg)
    checks['validation_calibration_heads'] = reconcile_calibration(log, validation, groups, settings['models']['LightGBM'])
    selection = select(table, validation, cfg)
    focus = tuple(experiment['focus_route'])
    chosen = selection.loc[selection.destination_country.eq(focus[0]) & selection.carrier.eq(focus[1])].iloc[0]
    control = table.loc[table.destination_country.eq(focus[0]) & table.carrier.eq(focus[1])
        & table.model.eq('lgbm_cal_ratio7_56_p4') & table.block.eq(1) & table.cadence.eq('daily_origins')].iloc[0]
    improved = bool(chosen.validation_mape_positive_pct < control.mape_positive_pct - experiment['numeric_tolerance'])
    selected_model = chosen.model if improved else control.model
    old_selected = pd.read_csv(reference_run/'overall_selected_models.csv')
    locked = old_selected.loc[old_selected.target.eq('direct_7d')].copy()
    mask = locked.destination_country.eq(focus[0]) & locked.carrier.eq(focus[1])
    locked.loc[mask, ['family', 'model', 'validation_mape_positive_pct', 'validation_mae']] = [
        'LightGBM', selected_model, chosen.validation_mape_positive_pct if improved else control.mape_positive_pct,
        chosen.validation_mae if improved else control.mae]
    write_csv(out/'selected_models.csv', locked)
    lock = {'locked_before_test': True, 'test_will_be_scored': improved,
            'selected_model': selected_model, 'files': {'selected_models.csv': sha256(out/'selected_models.csv')},
            'other_nine': 'reference selections and forecasts frozen; not reranked',
            'created_at_utc': datetime.now(timezone.utc).isoformat()}
    write_json(out/'selection_lock.json', lock)
    result = {'selected_model': selected_model, 'validation_improved': improved, 'test_scored': False,
              'goal_achieved': False, 'validation_baseline_mape_pct': control.mape_positive_pct,
              'validation_selected_mape_pct': chosen.validation_mape_positive_pct if improved else control.mape_positive_pct}
    comparison = pd.DataFrame()
    if improved:
        print(f'Validation choice locked: {selected_model}; scoring retrospective test once', flush=True)
        # The selected pooled estimator is evaluated for LG U+ only; other routes retain their sealed choices.
        choices = {key: selected_model for key in groups}
        test, test_log = phase(focused, groups, cfg, settings, 'direct_7d', 'test', choices, reference)
        test = test.loc[test.destination_country.eq(focus[0]) & test.carrier.eq(focus[1])].copy()
        old_test = load_predictions(reference_run/'overall_test_predictions.csv')
        old_test = old_test.loc[old_test.target.eq('direct_7d')]
        combined = pd.concat([old_test.loc[~(old_test.destination_country.eq(focus[0]) & old_test.carrier.eq(focus[1]))], test], ignore_index=True)
        test_table = metrics(combined, cfg)
        for name, frame in [('focus_test_predictions', test), ('test_fit_log', test_log),
            ('overall_test_predictions', combined), ('overall_test_metrics', test_table),
            ('test_calendar_strata', strata_metrics(combined, reference, cfg))]:
            write_csv(out/f'{name}.csv', frame)
        checks['test_labels'] = reconcile_labels(combined, focused, cfg)
        checks['test_metric_groups'] = reconcile_metrics(combined, test_table, cfg)
        focus_logs = test_log.loc[test_log.destination_country.eq(focus[0]) & test_log.carrier.eq(focus[1])
                                  | test_log.destination_country.isna()].copy() if 'destination_country' in test_log else test_log
        checks['test_calibration_heads'] = reconcile_calibration(focus_logs, test, groups, settings['models']['LightGBM'])
        primary = test_table.loc[test_table.block.eq(1) & test_table.cadence.eq('daily_origins')]
        new_focus = primary.loc[primary.carrier.eq(focus[1])].iloc[0]
        old_table = metrics(old_test, cfg)
        old_focus = old_table.loc[old_table.carrier.eq(focus[1]) & old_table.block.eq(1) & old_table.cadence.eq('daily_origins')].iloc[0]
        comparison = primary.merge(old_table.loc[old_table.block.eq(1) & old_table.cadence.eq('daily_origins')],
                                   on=ROUTE, suffixes=('_new', '_reference'), validate='one_to_one')
        comparison['mape_change_pp'] = comparison.mape_positive_pct_new - comparison.mape_positive_pct_reference
        write_csv(out/'before_after_routes.csv', comparison)
        result.update(test_scored=True, focus_test_mape_pct=new_focus.mape_positive_pct,
            reference_focus_test_mape_pct=old_focus.mape_positive_pct, top10_passes_20_pct=int(primary.passes_20_pct.sum()),
            goal_achieved=bool(new_focus.mape_positive_pct < 20 and new_focus.coverage == 1
                              and new_focus.mape_positive_pct < old_focus.mape_positive_pct))
        future, future_log = phase(focused, groups, cfg, settings, 'direct_7d', 'future', choices, reference)
        future = future.loc[future.carrier.eq(focus[1])]
        write_csv(out/'focus_future_predictions.csv', future)
        write_csv(out/'future_fit_log.csv', future_log)
        checks['future_labels'] = reconcile_labels(future, focused, cfg)
    if sha256(out/'selected_models.csv') != lock['files']['selected_models.csv']:
        raise AssertionError('Selection changed after lock')
    for name, expected in protected.items():
        if sha256(ROOT/name) != expected:
            raise AssertionError('Protected reference/report/dashboard changed')
    assert sha256(source) == manifest['source_sha256']
    checks.update(test_scored=result['test_scored'], protected_files_unchanged=len(protected), selection_lock_unchanged=True,
                  source_hash_unchanged=True, status='passed')
    write_json(out/'verification.json', checks)
    write_json(out/'result.json', result)
    report(out, experiment, result, table, comparison)
    manifest.update(status='complete', result=result, finished_at_utc=datetime.now(timezone.utc).isoformat())
    seal_manifest(out, manifest)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--config', default='data/configs/m2-calendar.json')
    parser.add_argument('--stage', choices=['analyze', 'all'], default='all')
    args = parser.parse_args()
    run(args.run_id, args.config, args.stage)
