"""Compare sealed daily and weekly forecasts on identical complete windows."""
import argparse
import html
import json
import os
import re

from src.common import ROOT, ROUTE, sha256, validate_run, write_csv, write_json
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'outputs' / '_matplotlib_cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sigma.verification.weekly import validate_weekly
from sigma.inventory.policy import validate_policy


def score(actual, forecast):
    actual, forecast = np.asarray(actual, float), np.asarray(forecast, float)
    if actual.shape != forecast.shape or not len(actual) or not np.isfinite([actual, forecast]).all():
        raise ValueError('Comparison requires complete finite matched pairs')
    positive = actual > 0
    error = forecast - actual
    return {'pairs': len(actual), 'positive_pairs': int(positive.sum()), 'zero_pairs': int((actual == 0).sum()),
        'coverage': 1., 'mape_positive_pct': np.mean(np.abs(error[positive]) / actual[positive]) * 100 if positive.any() else np.nan,
        'mae_qty': np.abs(error).mean(), 'wape_pct': np.abs(error).sum() / actual.sum() * 100 if actual.sum() else np.nan,
        'bias_pct': error.sum() / actual.sum() * 100 if actual.sum() else np.nan}


def markdown(frame):
    # No optional tabulate dependency, and no raw records or identifiers.
    cells = [[str(v).replace('|', '/') for v in row] for row in frame.astype(str).to_numpy()]
    return '\n'.join(['| ' + ' | '.join(frame.columns) + ' |', '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |']
        + ['| ' + ' | '.join(row) + ' |' for row in cells])


def compare(weekly_run, daily_run, policy_run, output_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [weekly_run, daily_run, policy_run, output_id]):
        raise ValueError('Invalid comparison run identifier')
    wdir, ddir, pdir = [ROOT / 'outputs' / name for name in [weekly_run, daily_run, policy_run]]
    w, d, p = validate_weekly(wdir), validate_run(ddir), validate_policy(pdir)
    wp = json.loads((wdir / 'protocol.json').read_text(encoding='utf-8'))
    pp = json.loads((pdir / 'protocol.json').read_text(encoding='utf-8'))
    cfg = d['config']
    keys = ['sales_statuses', 'target_definition_version', 'train_end', 'validation_start', 'validation_end', 'test_start', 'test_end', 'horizon']
    if any(wp['base_config'][key] != cfg[key] for key in keys) or pp['config'] != cfg or p['daily_run'] != daily_run:
        raise ValueError('Comparison parent protocols differ')
    # Policy may come from an earlier equivalent locked forecast. Prove every
    # test total and future total is identical, rather than relying on its name.
    policy_week = ROOT / 'outputs' / p['weekly_run']
    pw = validate_weekly(policy_week)
    for filename in ['test_weekly_predictions.csv', 'weekly_forecast.csv']:
        left, right = [pd.read_csv(folder / filename).sort_values(ROUTE + ['as_of_date', 'week_block']) for folder in [wdir, policy_week]]
        pd.testing.assert_frame_equal(left[ROUTE + ['as_of_date', 'week_block']].reset_index(drop=True), right[ROUTE + ['as_of_date', 'week_block']].reset_index(drop=True))
        np.testing.assert_allclose(left.forecast_qty_7d, right.forecast_qty_7d, rtol=0, atol=1e-8)
    source = ROOT / cfg['source']
    if not sha256(source) == w['source_sha256'] == d['source_sha256'] == p['source_sha256'] == pw['source_sha256']:
        raise ValueError('Comparison source differs')
    top = pd.read_csv(wdir / 'top_routes.csv')
    pd.testing.assert_frame_equal(top[ROUTE].reset_index(drop=True), pd.read_csv(ddir / 'top_routes.csv')[ROUTE].reset_index(drop=True))
    top_keys = set(top[ROUTE].itertuples(index=False, name=None))
    weekly = pd.read_csv(wdir / 'test_weekly_predictions.csv', parse_dates=['as_of_date', 'window_start', 'window_end'])
    daily = pd.read_csv(ddir / 'predictions.csv', parse_dates=['as_of_date', 'target_date'])
    daily = daily.loc[daily.split.eq('test') & daily.model.eq('selected')].copy()
    daily['week_block'] = (daily.horizon_day - 1) // 7 + 1
    daily_totals = daily.groupby(ROUTE + ['as_of_date', 'week_block']).agg(
        total=('forecast_qty', 'sum'), actual=('actual_qty', 'sum'), count=('forecast_qty', 'size')).reset_index()
    weekly = weekly.merge(daily_totals.loc[daily_totals['count'].eq(7)], on=ROUTE + ['as_of_date', 'week_block'], validate='one_to_one')
    assert len(weekly) == len(pd.read_csv(wdir / 'test_weekly_predictions.csv'))
    np.testing.assert_array_equal(weekly.actual_qty_7d, weekly.actual)
    series = {key: g.set_index('date').sales_qty for key, g in pd.read_csv(wdir / 'daily_sales.csv', parse_dates=['date']).groupby(ROUTE)}
    results, allocated_results = [], []
    for key, group in weekly.groupby(ROUTE):
        history = series[key]
        methods = {'direct_weekly': group.forecast_qty_7d.to_numpy(), 'sum_daily_model': group.total.to_numpy()}
        for window, name in [(1, 'naive'), (7, 'ma7'), (28, 'ma28')]:
            methods[name] = history.rolling(window, min_periods=1).mean().reindex(group.as_of_date).to_numpy() * 7
        for block in [1, 2]:
            for cadence in ['daily_origins', 'seven_day_origins']:
                mask = (group.week_block.eq(block) & (group.weekly_cadence.eq(True) if cadence == 'seven_day_origins' else True)).to_numpy()
                for name, values in methods.items():
                    results.append({**dict(zip(ROUTE, key)), 'is_top10': key in top_keys, 'week_block': block,
                        'cadence': cadence, 'method': name, **score(group.actual_qty_7d.to_numpy()[mask], values[mask])})
        # Daily forecasts and weekly allocations on exactly the same complete
        # windows. Each route has 602 h1-7 pairs, not the official 623-pair grid.
        if key not in top_keys:
            continue
        for block, windows in group.groupby('week_block'):
            arrays = {'daily_model': [], 'allocated_weekly': []}
            actuals = []
            own_daily = daily.loc[daily.destination_country.eq(key[0]) & daily.carrier.eq(key[1])].set_index(['as_of_date', 'horizon_day'])
            for row in windows.itertuples():
                dates = pd.date_range(row.window_start, row.window_end)
                old = history.loc[:row.as_of_date].iloc[-wp['weekly_config']['allocation_history_days']:]
                weights = old.groupby(old.index.dayofweek).mean().reindex(dates.dayofweek, fill_value=0).to_numpy()
                weights = weights / weights.sum() if weights.sum() else np.repeat(1 / 7, 7)
                actual = history.reindex(dates).to_numpy()
                model_days = own_daily.loc[[(row.as_of_date, h) for h in range(1 + 7 * (block - 1), 1 + 7 * block)]]
                np.testing.assert_array_equal(model_days.actual_qty, actual)
                arrays['daily_model'].extend(model_days.forecast_qty)
                arrays['allocated_weekly'].extend(weights * row.forecast_qty_7d)
                actuals.extend(actual)
            for name, values in arrays.items():
                allocated_results.append({**dict(zip(ROUTE, key)), 'week_block': block, 'method': name, **score(actuals, values), 'official_daily_R05': False})
    comparison = pd.DataFrame(results)
    official = pd.read_csv(ddir / 'accuracy_acceptance.csv')
    primary = comparison.loc[comparison.is_top10 & comparison.week_block.eq(1) & comparison.cadence.eq('daily_origins')]
    table = top[ROUTE].merge(official[ROUTE + ['mape_positive_pct']], on=ROUTE, validate='one_to_one').rename(columns={'mape_positive_pct': 'daily_R05_mape'})
    pivot = primary.pivot(index=ROUTE, columns='method', values='mape_positive_pct').reset_index()
    table = table.merge(pivot, on=ROUTE, validate='one_to_one')
    table['weekly_passed'] = table.direct_weekly.le(20)
    # All 13 scenarios use the unchanged base configuration and same actual demand.
    dm, wm = [pd.read_csv(folder / 'simulation_metrics.csv') for folder in [ddir, pdir]]
    stocks = dm.merge(wm, on=['evaluation', 'scenario_id'], suffixes=('_daily', '_weekly'), validate='one_to_one')
    assert len(stocks) == len(dm) == len(wm) == 14
    np.testing.assert_allclose(stocks.demand_daily, stocks.demand_weekly, atol=0, rtol=0, equal_nan=True)
    replay = stocks.loc[stocks.evaluation.eq('independent_no_new_order_alert_replay')].iloc[0]
    assert replay.tp_daily + replay.fn_daily == replay.tp_weekly + replay.fn_weekly
    assert replay.n_item_windows_daily == replay.n_item_windows_weekly and replay.existing_empty_excluded_daily == replay.existing_empty_excluded_weekly
    stocks['fill_delta_percentage_points'] = (stocks.fill_rate_weekly - stocks.fill_rate_daily) * 100
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    write_csv(out / 'matched_week_metrics.csv', comparison)
    write_csv(out / 'top10_comparison.csv', table)
    write_csv(out / 'matched_daily_diagnostics.csv', pd.DataFrame(allocated_results))
    write_csv(out / 'stock_scenario_comparison.csv', stocks)
    labels = table.destination_country + ' / ' + table.carrier
    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(table))
    ax.barh(x - .2, table.sum_daily_model, .4, label='Daily model summed over 7 days')
    ax.barh(x + .2, table.direct_weekly, .4, label='Direct 7-day model')
    ax.axvline(20, color='firebrick', linestyle='--', label='20% weekly threshold')
    ax.set(yticks=x, yticklabels=labels, xlabel='Positive-week MAPE (%)', title='Same 86 complete h1-7 windows per route')
    ax.invert_yaxis(); ax.legend(); fig.tight_layout()
    fig.savefig(out / 'weekly_comparison.png', dpi=160); plt.close(fig)
    view = table.round(2)
    text = ('# So sánh dự báo ngày và tổng 7 ngày\n\n'
        'Nguồn: cùng quantity success theo ngày UTC; top 10 chỉ xếp trong train. '
        'Test 01/10–31/12/2025 đã từng được xem: kết quả hồi cứu, chưa phải nghiệm thu độc lập.\n\n'
        '**Không so trực tiếp hai MAPE có target khác nhau.** Cột daily_R05_mape là tiêu chí ngày chính thức (623 cặp/tuyến). '
        'Các cột còn lại chấm tổng 7 ngày trên cùng 86 cửa sổ h1–7 đầy đủ/tuyến. '
        'H8–14 và 13/12 cửa sổ không chồng lấp được lưu riêng trong CSV.\n\n'
        + markdown(view) + '\n\n'
        f'Dự báo tuần trực tiếp đạt {int(table.weekly_passed.sum())}/{len(top)} tuyến ≤20%; '
        f'MAPE trung bình tuyến {table.direct_weekly.mean():.2f}%. Tiêu chí ngày đạt {int(official.accuracy_passed.sum())}/{len(top)}. '
        'Các tuyến chưa đạt được giữ nguyên trong bảng. MAPE không tính ngày/tuần actual bằng 0; MAE, WAPE, bias và số zero được báo kèm.\n\n'
        'Phân bổ tổng tuần xuống ngày cũng được chấm trên cùng 602 cặp h1–7/tuyến; đây là kiểm tra bổ sung, không thay grid R05.\n\n'
        '![So sánh cùng cửa sổ](weekly_comparison.png)\n\n'
        '## Tồn kho mô phỏng\n\n'
        + markdown(stocks.loc[stocks.evaluation.eq('continuous_replenishment_policy'), ['scenario_id', 'demand_daily', 'shortage_daily', 'shortage_weekly', 'fill_rate_daily', 'fill_rate_weekly', 'fill_delta_percentage_points']].round(4))
        + '\n\nNhập đầu ngày; xử lý đơn theo timestamp/ID; chỉ trừ tồn một lần khi đặt. '
        '13 kịch bản giữ cùng nguồn/giả định; không chọn tham số tồn bằng kết quả test. '
        f'Cảnh báo sớm ≥7 ngày: {replay.early_event_rate_daily:.2%} → {replay.early_event_rate_weekly:.2%}, '
        f'cùng {int(replay.tp_daily + replay.fn_daily)} sự kiện; vẫn có ca cạn trước ngày 7. '
        'Khách giao D+7 không trễ là giả định tách biệt với thời gian nhà cung cấp nhập kho.\n')
    (out / 'comparison.md').write_text(text, encoding='utf-8')
    # Standalone local preview with real tables and a linked figure.
    body = '<h1>SIGMA · So sánh ngày / tổng 7 ngày</h1><p>' + html.escape(text.split('**')[0].split('\n\n', 1)[1]) + '</p>'
    body += '<p>MAPE ngày chính thức và MAPE tuần có target khác nhau. Các phương án tuần được so trên cùng cửa sổ.</p>' + view.to_html(index=False)
    body += '<img src="weekly_comparison.png" alt="Same-window weekly MAPE" style="max-width:100%"><h2>13 kịch bản tồn mô phỏng</h2>' + stocks.round(4).to_html(index=False)
    (out / 'comparison.html').write_text('<!doctype html><meta charset="utf-8"><style>body{font:16px system-ui;margin:32px;line-height:1.5}table{border-collapse:collapse;font-size:13px}th,td{padding:8px;border:1px solid #ccc}th{background:#e8f2f8}</style>' + body, encoding='utf-8')
    validate_weekly(wdir); validate_run(ddir); validate_policy(pdir)
    assert sha256(source) == w['source_sha256']
    result = {'status': 'verified', 'kind': 'matched_day_week_comparison', 'weekly_run': weekly_run,
        'daily_run': daily_run, 'policy_run': policy_run, 'policy_forecasts_equal_comparison_forecasts': True,
        'weekly_parent_sha256': sha256(wdir / 'summary.json'), 'daily_parent_sha256': sha256(ddir / 'manifest.json'),
        'policy_parent_sha256': sha256(pdir / 'summary.json'), 'source_sha256': sha256(source), 'entrypoint_sha256': sha256(__file__),
        'matched_week_windows': len(weekly), 'weekly_top10_passed': int(table.weekly_passed.sum()),
        'official_daily_top10_passed': int(official.accuracy_passed.sum()), 'test_is_independent': False,
        'daily_acceptance_replaced': False, 'stock_scenarios_compared': 13, 'actual_replay_events': int(replay.tp_daily + replay.fn_daily),
        'files': {file.name: sha256(file) for file in out.iterdir() if file.is_file()}}
    write_json(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weekly-run', required=True)
    parser.add_argument('--daily-run', default='sigma_scaled_v11')
    parser.add_argument('--policy-run', required=True)
    parser.add_argument('--output-id', required=True)
    args = parser.parse_args()
    compare(args.weekly_run, args.daily_run, args.policy_run, args.output_id)
