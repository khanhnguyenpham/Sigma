"""Score every previously registered LG U+ candidate, without a validation gate."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import re
import shutil

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config, sha256, write_csv, write_json, new_manifest, seal_manifest, validate_run
from src.data import route_top
from sigma.forecasting.weekly import checked_series
from M2.models import focus_experiment as focus, hierarchy_experiment as hierarchy
from M2.models import adaptive_experiment as adaptive, composition_experiment as composition
from M2.models.calendar_experiment import variants, protected_files, reconcile_labels, strata_metrics
from M2.models.calendar_reference import CalendarReference
from M2.models.LightGBM.model import phase as calendar_phase
from M2.models.registry import load_settings, implementation_hashes
from M2.models.families import metrics
from M2.models.verify import reconcile_metrics, reconcile_calibration

KEYS = ['as_of_date', 'block']


def only_focus(frame):
    return frame.loc[frame.destination_country.eq(focus.FOCUS[0]) & frame.carrier.eq(focus.FOCUS[1])].copy()


def validate_pairs(frame, daily, cfg, expected):
    """Coverage includes the full origin grid, even rows with incomplete labels."""
    assert set(frame.model) == set(expected), 'Candidate set differs from registered pool'
    assert len(only_focus(frame)) == len(frame) and frame.split.eq('test').all()
    origins = pd.date_range(pd.Timestamp(cfg['test_start'])-pd.Timedelta(days=1),
                            pd.Timestamp(cfg['test_end'])-pd.Timedelta(days=1))
    pairs = pd.MultiIndex.from_product([origins, [1, 2]], names=KEYS)
    for _, part in frame.groupby('model'):
        observed = pd.MultiIndex.from_frame(part[KEYS])
        assert observed.is_unique and observed.sort_values().equals(pairs), 'Missing or duplicate origin/block'
    return reconcile_labels(frame, daily, cfg)


def leaderboard(table, catalog):
    """Ranking is explicitly descriptive: never creates a model selection file."""
    primary = table.loc[table.block.eq(1) & table.cadence.eq('daily_origins')].copy()
    result = primary.merge(catalog, on=['pool', 'model'], validate='one_to_one', suffixes=('', '_validation'))
    assert len(result) == len(catalog)
    result['below_20_pct'] = result.coverage.eq(1) & result.mape_positive_pct.lt(20)
    result['ranking_basis'] = 'test_retrospective_exploration'
    result = result.sort_values(['mape_positive_pct', 'mae', 'pool', 'model']).reset_index(drop=True)
    result.insert(0, 'test_rank', np.arange(1, len(result)+1))
    return result


def run_pool(name, daily, cfg, settings, experiment, folder):
    """Reuse each sealed experiment's phase implementation and parameters."""
    folder.mkdir(exist_ok=False)
    extra = {}
    if name == 'calendar':
        settings = {**settings, 'models': {'LightGBM': variants(settings, experiment)}}
        groups = {key: part.sales_qty.astype(float) for key, part in checked_series(daily).items()}
        reference = CalendarReference.load(ROOT/experiment['calendar_path'])
        pred, log = calendar_phase(daily, groups, cfg, settings, 'direct_7d', 'test', calendar_reference=reference)
        checks = {'heads': reconcile_calibration(log, pred, groups, settings['models']['LightGBM'])}
        pred = only_focus(pred)
    elif name == 'composition':
        pred, log, counts, count_log, checks = composition.phase(daily, cfg, settings, experiment, 'test')
        write_csv(folder/'count_predictions.csv', counts)
        write_csv(folder/'count_fit_log.csv', count_log)
    elif name == 'adaptive':
        pred, log = adaptive.phase(daily, cfg, settings, experiment, 'test')
        checks = adaptive.verify(log, experiment, daily, cfg, settings, 'test')
    else:
        population = hierarchy.country_daily(daily) if name == 'hierarchy' else daily
        pred, log = focus.phase(population, cfg, settings, experiment, 'test')
        checks = {'heads': focus.verify_heads(log, experiment, population)}
        if name == 'hierarchy':
            extra['country_predictions'] = pred
    write_csv(folder/'phase_predictions.csv', pred)
    write_csv(folder/'fit_log.csv', log)
    write_json(folder/'causal_verification.json', checks)
    print(f'Completed phase: {name}', flush=True)
    return pred, checks, extra


def compare_previous(pred, previous, old_model, new_model, tolerance):
    left = pred.loc[pred.model.eq(new_model)]
    right = only_focus(previous).loc[lambda x: x.model.eq(old_model)]
    joined = left.merge(right, on=ROUTE+KEYS, validate='one_to_one', suffixes=('', '_old'))
    assert len(joined) == len(left) == len(right) > 0
    np.testing.assert_allclose(joined.forecast_qty, joined.forecast_qty_old, atol=tolerance, rtol=0)
    np.testing.assert_allclose(joined.actual_qty, joined.actual_qty_old, atol=0, rtol=0, equal_nan=True)
    return {'pairs': len(joined), 'max_forecast_difference': float((joined.forecast_qty-joined.forecast_qty_old).abs().max())}


def run(run_id, reuse_phases=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run ID')
    path = ROOT/'data/configs/m2-test-sweep.json'
    exp = json.loads(path.read_text(encoding='utf-8'))
    cfg = read_config(exp['base_config']); settings = load_settings(ROOT/exp['model_config'])
    assert 1 <= exp['workers'] <= settings['workers'] <= 3
    root = ROOT/'M2/artifacts'; source = ROOT/cfg['source']
    old = root/exp['reference_run']; locked = root/exp['locked_run']
    old_manifest = validate_run(old); locked_manifest = validate_run(locked)
    assert sha256(source) == old_manifest['source_sha256'] == locked_manifest['source_sha256']
    protected = {**protected_files(old), **locked_manifest['protected_before']}
    baseline_paths = {'original': old/'LightGBM/direct_7d/test_predictions.csv',
        'focus': root/exp['daily_run']/'focus_test_predictions.csv',
        'composition': locked/'focus_test_predictions.csv'}
    for baseline_path in baseline_paths.values():
        if not baseline_path.is_file(): raise ValueError('Missing baseline prediction file')
    reused = None
    if reuse_phases:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', reuse_phases): raise ValueError('Invalid reuse ID')
        reused = root/reuse_phases; previous = validate_run(reused, require_complete=False)
        assert previous['status'] == 'failed' and previous['phase_forecasts_complete'] is True
        assert previous['experiment'] == exp and previous['settings'] == settings
        assert previous['source_sha256'] == sha256(source) and previous['config'] == cfg
        protected.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in reused.rglob('*') if p.is_file()})
    experiments, catalogs, lineage = {}, [], {}
    for name, spec in exp['pools'].items():
        previous = root/spec['run']; manifest = validate_run(previous)
        assert manifest['source_sha256'] == sha256(source)
        experiments[name] = json.loads((ROOT/spec['config']).read_text(encoding='utf-8'))
        assert manifest['config_sha256'] == sha256(ROOT/spec['config'])
        table = only_focus(pd.read_csv(previous/'validation_metrics.csv', float_precision='round_trip'))
        table = table.loc[table.block.eq(1) & table.cadence.eq('daily_origins')]
        assert len(table) == spec['count'] and table.model.is_unique
        if name not in ('calendar', 'hierarchy'):
            names = composition.candidates(experiments[name]) if name == 'composition' else focus.candidates(experiments[name])
            assert set(table.model) == set(names)
        catalog = table[['model', 'mape_positive_pct', 'mae', 'coverage']].rename(columns={
            'mape_positive_pct': 'validation_mape_positive_pct', 'mae': 'validation_mae', 'coverage': 'validation_coverage'})
        catalog.insert(0, 'pool', name); catalogs.append(catalog)
        lineage[name] = {'run': spec['run'], 'manifest_sha256': sha256(previous/'manifest.json'),
                         'config_sha256': sha256(ROOT/spec['config'])}
        protected.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in previous.rglob('*') if p.is_file()})
        receipt = previous.with_name(previous.name+'_review.json')
        if receipt.exists(): protected[receipt.relative_to(ROOT).as_posix()] = sha256(receipt)
    for item in [source, ROOT/'data/reference/calendar_features.csv', ROOT/'data/reference/calendar_features.events.json',
                 path, ROOT/exp['base_config'], ROOT/exp['model_config']]:
        protected[item.relative_to(ROOT).as_posix()] = sha256(item)
    protected.update(implementation_hashes())
    daily_path = root/exp['daily_run']/'daily_sales.csv'
    daily = pd.read_csv(daily_path, parse_dates=['date'])
    distribution_path = locked/'daily_distribution.csv'
    distribution = pd.read_csv(distribution_path, parse_dates=['date'])
    quantity_columns = ['date']+ROUTE+['sales_qty', 'order_count']
    pd.testing.assert_frame_equal(daily[quantity_columns].sort_values(['date']+ROUTE).reset_index(drop=True),
        distribution[quantity_columns].sort_values(['date']+ROUTE).reset_index(drop=True))
    top = route_top(daily, cfg)
    pd.testing.assert_frame_equal(top, pd.read_csv(root/exp['daily_run']/'top_routes.csv'))
    assert daily.sales_qty.sum() == 118296 and len(top) == 10
    focused = daily.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    rich = distribution.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    catalog = pd.concat(catalogs, ignore_index=True)
    assert len(catalog) == 160 and not catalog.duplicated(['pool', 'model']).any()
    if reused is not None:
        pd.testing.assert_frame_equal(catalog, pd.read_csv(reused/'candidate_catalog.csv', float_precision='round_trip'), check_exact=True)
    out = root/run_id; out.mkdir(exist_ok=False)
    write_csv(out/'candidate_catalog.csv', catalog)
    manifest = new_manifest(cfg, source, run_id)
    manifest.update(experiment=exp, settings=settings, config_sha256=sha256(path),
        implementation_modules_sha256=implementation_hashes(), protected_before=protected, lineage=lineage,
        daily_lineage={'path': daily_path.relative_to(ROOT).as_posix(), 'sha256': sha256(daily_path),
            'distribution_path': distribution_path.relative_to(ROOT).as_posix(), 'distribution_sha256': sha256(distribution_path),
            'note': 'Reuse sealed raw audits; current raw SHA rechecked. No new raw audit claimed.'},
        candidate_catalog_sha256=sha256(out/'candidate_catalog.csv'), official_selection_modified=False,
        production_modified=False, reused_phases_from=reuse_phases,
        reuse_note='If present, reuse hashed completed forecasts after baseline-path finalization failure; no new fitting, candidates or parameters.',
        policy='All registered candidates scored; test ranking is exploratory only')
    write_json(out/'protocol.json', manifest); write_json(out/'manifest.json', manifest)
    write_json(out/'test_execution.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'protocol_sha256': sha256(out/'protocol.json'), 'candidate_catalog_sha256': sha256(out/'candidate_catalog.csv'),
        'authorization': exp['authorization'], 'validation_gate': False})
    print('Registered all 160 entries; reuse completed phases' if reused else
          'Registered all 160 entries; scoring test with three local workers', flush=True)
    results, checks = {}, {}
    if reused is not None:
        for name in exp['pools']:
            (out/name).mkdir()
            for item in (reused/name).iterdir():
                if item.is_file(): shutil.copyfile(item, out/name/item.name)
            results[name] = focus.load_predictions(out/name/'phase_predictions.csv')
            checks[name] = json.loads((out/name/'causal_verification.json').read_text(encoding='utf-8'))
    else:
        with ProcessPoolExecutor(max_workers=exp['workers']) as pool:
            jobs = {pool.submit(run_pool, name, rich if name == 'composition' else focused, cfg, settings,
                                experiments[name], out/name): name for name in exp['pools']}
            for job in as_completed(jobs):
                name = jobs[job]; results[name], checks[name], _ = job.result()
    country = results['hierarchy']
    prior56 = results['focus'].loc[results['focus'].model.eq('focus_scale56_mul56p4')]
    allocated = hierarchy.allocate(country, daily, experiments['hierarchy']['share_days'])
    results['hierarchy'] = pd.concat([hierarchy.assemble(allocated, prior56, experiments['hierarchy']),
        results['focus'].loc[results['focus'].model.eq('focus_control_mul56p4')]], ignore_index=True)
    predictions, tables, strata = [], [], []
    calendar = CalendarReference.load(ROOT/experiments['calendar']['calendar_path'])
    for name, frame in results.items():
        expected = catalog.loc[catalog.pool.eq(name), 'model']
        checks[name]['labels_and_pairs'] = validate_pairs(frame, daily, cfg, expected)
        if reused is not None:
            prior_frame = focus.load_predictions(reused/name/'test_predictions.csv')
            pd.testing.assert_frame_equal(frame, prior_frame, check_exact=True)
        table = metrics(frame, cfg)
        checks[name]['metric_groups'] = reconcile_metrics(frame, table, cfg)
        assert table.coverage.eq(1).all() and len(table) == 4*len(expected)
        write_csv(out/name/'test_predictions.csv', frame); write_csv(out/name/'test_metrics.csv', table)
        predictions.append(frame.assign(pool=name)); tables.append(table.assign(pool=name))
        strata.append(strata_metrics(frame, calendar, cfg).assign(pool=name))
    tolerance = exp['numeric_tolerance']
    checks['original_control'] = compare_previous(results['calendar'], focus.load_predictions(baseline_paths['original']),
        'lgbm_cal_ratio7_56_p4', 'lgbm_cal_ratio7_56_p4', tolerance)
    checks['previous_focus'] = compare_previous(results['focus'], focus.load_predictions(baseline_paths['focus']),
        'focus_scale56_mul56p4', 'focus_scale56_mul56p4', tolerance)
    checks['locked_composition'] = compare_previous(results['composition'], focus.load_predictions(baseline_paths['composition']),
        'composition_both56_mul56p4', 'composition_both56_mul56p4', tolerance)
    all_predictions = pd.concat(predictions, ignore_index=True); all_metrics = pd.concat(tables, ignore_index=True)
    ranking = leaderboard(all_metrics, catalog)
    write_csv(out/'test_predictions.csv', all_predictions); write_csv(out/'test_metrics.csv', all_metrics)
    write_csv(out/'test_calendar_strata.csv', pd.concat(strata, ignore_index=True))
    write_csv(out/'test_leaderboard.csv', ranking)
    summaries = []
    for name, part in ranking.groupby('pool', sort=False):
        winner = part.iloc[0]
        summaries.append({'pool': name, 'entries': len(part), 'below_20_pct': int(part.below_20_pct.sum()),
            'best_model': winner.model, 'best_test_mape_positive_pct': winner.mape_positive_pct,
            'best_validation_mape_positive_pct': winner.validation_mape_positive_pct})
    write_csv(out/'pool_summary.csv', pd.DataFrame(summaries))
    checks['raw_sha_unchanged'] = sha256(source) == manifest['source_sha256']
    for name, expected in protected.items(): assert sha256(ROOT/name) == expected, f'Protected file changed: {name}'
    checks['protected_files_unchanged'] = len(protected)
    checks['all_160_scored'] = len(ranking) == 160
    checks['official_selection_and_other_nine_unchanged'] = True
    write_json(out/'verification.json', checks)
    best = ranking.iloc[0]
    result = {'entries': len(ranking), 'below_20_pct_entries': int(ranking.below_20_pct.sum()),
        'test_best_pool': best.pool, 'test_best_model': best.model, 'test_best_mape_positive_pct': best.mape_positive_pct,
        'test_best_validation_mape_positive_pct': best.validation_mape_positive_pct,
        'ranking_basis': 'test_retrospective_exploration', 'official_selection_modified': False,
        'independent_holdout': False, 'production_modified': False}
    write_json(out/'result.json', result)
    lines = ['# Toàn bộ cấu hình trên test — CHG-041/E69', '',
        'So sánh hồi cứu theo yêu cầu người dùng; xếp hạng bằng test, không phải đánh giá độc lập hoặc lựa chọn chính thức.',
        '160 lượt cấu hình của sáu nhóm, có đối chứng lặp. Giữ nguyên quantity success UTC, train top10, split, H14 và refit từng cấu hình.',
        'Chín tuyến khác, lựa chọn đã khóa, báo cáo và dashboard giữ nguyên. R05 theo ngày chưa được thay đổi.', '',
        f'Có {result["below_20_pct_entries"]}/160 lượt đạt MAPE test h1–7 <20%, coverage=100%.', '',
        '| Hạng | Nhóm | Mô hình | Validation MAPE | Test MAPE | MAE | WAPE | Bias |',
        '|---:|---|---|---:|---:|---:|---:|---:|']
    for row in ranking.head(20).itertuples():
        lines.append(f'| {row.test_rank} | {row.pool} | {row.model} | {row.validation_mape_positive_pct:.6f}% | {row.mape_positive_pct:.6f}% | {row.mae:.6f} | {row.wape_pct:.6f}% | {row.bias:.6f} |')
    lines += ['', 'Toàn bộ 160 dòng: [test_leaderboard.csv](test_leaderboard.csv). H1–7/h8–14 và cadence: [test_metrics.csv](test_metrics.csv).',
        'Dịp lễ/ngày thường: [test_calendar_strata.csv](test_calendar_strata.csv). Nguồn/config/hash: [manifest.json](manifest.json).',
        'Không suy diễn hiệu quả vận hành từ snapshot trạng thái cuối; kết quả đã dùng để so sánh trên test, không bảo đảm tương lai.', '']
    (out/'report.md').write_text('\n'.join(lines), encoding='utf-8')
    manifest.update(status='complete', result=result, finished_at_utc=datetime.now(timezone.utc).isoformat())
    seal_manifest(out, manifest)
    print(json.dumps(result), flush=True)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--reuse-phases', help='Reuse sealed completed phases after a finalization-only failure')
    args = parser.parse_args()
    run(args.run_id, args.reuse_phases)
