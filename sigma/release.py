"""Verify and freeze a local M2/M3 demo, keeping unmet acceptance visible."""
import argparse
import html
import json
import re
from datetime import datetime, timezone

import pandas as pd

from src.common import ROOT, sha256, validate_run, write_json
from sigma.delivery.customer import delivery_settings, validate_delivery
from sigma.inventory.policy import validate_policy
from sigma.inventory.snapshot import validate_inventory
from sigma.verification.weekly import validate_weekly


def checked_id(ident):
    if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
        raise ValueError('Invalid local run id')
    return ROOT / 'outputs' / ident


def comparison_summary(folder):
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    if summary.get('kind') != 'matched_day_week_comparison' or summary.get('status') != 'verified':
        raise ValueError('Comparison is not verified')
    for name, digest in summary['files'].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or sha256(path) != digest:
            raise ValueError('Comparison artifact changed')
    return summary


def load_checkpoint(bundle):
    folder = checked_id(bundle['release_checkpoint'])
    info = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    if (info.get('kind') != 'local_product_release_checkpoint' or info.get('status') != 'integrity_verified'
            or info['product_runs'] != bundle['product_runs'] or info['parent_hashes'] != bundle['product_summary_hashes']):
        raise ValueError('Release checkpoint differs from bundle')
    for name, digest in info['files'].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or sha256(path) != digest:
            raise ValueError('Release checkpoint changed')
    if json.loads((folder / 'delivery.json').read_text(encoding='utf-8')) != bundle:
        raise ValueError('Active bundle differs from frozen checkpoint')
    return folder, info


def verify_parents(bundle, summaries, hashes):
    source = summaries['daily']['source_sha256']
    for role, info in summaries.items():
        if info['source_sha256'] != source:
            raise ValueError('Release source differs: ' + role)
        if role not in ['daily', 'weekly'] and (
                info['weekly_run'] != bundle['weekly_run'] or info['daily_run'] != bundle['daily_run']):
            raise ValueError('Release forecast parent differs: ' + role)
    stock, comparison = summaries['stock'], summaries['comparison']
    if stock.get('stock_policy_run') != bundle['product_runs']['policy'] or stock.get('stock_policy_summary_sha256') != hashes['policy']:
        raise ValueError('Stock must use the exact weekly policy')
    if (comparison['policy_run'] != bundle['product_runs']['policy'] or
            comparison['weekly_parent_sha256'] != hashes['weekly'] or
            comparison['daily_parent_sha256'] != hashes['daily'] or
            comparison['policy_parent_sha256'] != hashes['policy'] or
            not comparison['policy_forecasts_equal_comparison_forecasts']):
        raise ValueError('Comparison parent hashes differ')
    delivery = summaries['delivery']
    if (delivery['customer_delivery_days'] != 7 or delivery['customer_delay_days'] != 0
            or delivery['supplier_lead_time_modified'] is not False):
        raise ValueError('Customer delivery is not D+7')


def acceptance(official_daily, weekly_passed, top_count, early_rate):
    daily_pass = official_daily == top_count == 10
    return [
        {'requirement': 'R05 · MAPE ngày dương ≤20% từng top10', 'status': 'Đạt' if daily_pass else 'Chưa đạt',
         'result': f'{official_daily}/{top_count} tuyến; giữ nguyên tiêu chí ngày'},
        {'requirement': 'Bổ sung · MAPE tổng7 ngày ≤20%', 'status': 'Đạt chỉ tiêu tuần' if weekly_passed == top_count else 'Chưa đạt đủ tuyến',
         'result': f'{weekly_passed}/{top_count} tuyến; không thay R05; test hồi cứu'},
        {'requirement': 'R06 · Tồn/ROP/SS, ledger giao dịch', 'status': 'Đã triển khai và kiểm hash',
         'result': 'Policy 13 kịch bản; tồn/nhập/lead time/mapping giả định, không là tồn doanh nghiệp'},
        {'requirement': 'R07 · Cảnh báo cạn trước ≥7 ngày', 'status': 'Còn ca chưa báo sớm',
         'result': f'Replay early-event-rate {early_rate:.2%}; giữ cả ca cạn trước ngày7'},
        {'requirement': 'R08 · Dashboard dự báo và sai số', 'status': 'Đã triển khai',
         'result': 'Sáu trang; chạy check-product riêng để kiểm bộ lọc và số liệu'},
        {'requirement': 'Giao khách · D+7 ngày lịch UTC', 'status': 'Đã triển khai theo giả định',
         'result': 'Không trễ khách; không có actual giao; tách lead time nhập kho'},
    ]


def verify_protocol_links(protocols, hashes):
    for role, protocol in protocols.items():
        if (protocol['weekly_summary_sha256'] != hashes['weekly'] or
                protocol['daily_manifest_sha256'] != hashes['daily']):
            raise ValueError('Release protocol parent differs: ' + role)


def execute(config, output_id, delivery_run, policy_run, stock_run, comparison_run):
    bundle = delivery_settings(config)
    ids = {'daily': bundle['daily_run'], 'weekly': bundle['weekly_run'], 'delivery': delivery_run,
           'policy': policy_run, 'stock': stock_run, 'comparison': comparison_run}
    folders = {role: checked_id(ident) for role, ident in ids.items()}
    out = checked_id(output_id)
    if out.exists():
        raise ValueError('Release output already exists; choose a new id')
    validators = {'daily': validate_run, 'weekly': validate_weekly, 'delivery': validate_delivery,
                  'policy': validate_policy, 'stock': validate_inventory, 'comparison': comparison_summary}
    summaries = {role: validators[role](folder) for role, folder in folders.items()}
    hashes = {role: sha256(folder / ('manifest.json' if role == 'daily' else 'summary.json')) for role, folder in folders.items()}
    bundle['product_runs'], bundle['product_summary_hashes'] = ids, hashes
    verify_parents(bundle, summaries, hashes)
    protocols = {role: json.loads((folders[role] / 'protocol.json').read_text(encoding='utf-8'))
                 for role in ['delivery', 'policy', 'stock']}
    verify_protocol_links(protocols, hashes)
    cfg = summaries['daily']['config']
    source = (ROOT / cfg['source']).resolve()
    if not source.is_relative_to(ROOT) or sha256(source) != summaries['daily']['source_sha256']:
        raise ValueError('Raw source changed')
    top = pd.read_csv(folders['weekly'] / 'top_routes.csv')
    daily = pd.read_csv(folders['daily'] / 'accuracy_acceptance.csv')
    if set(map(tuple, top[['destination_country', 'carrier']].to_numpy())) != set(map(tuple, daily[['destination_country', 'carrier']].to_numpy())):
        raise ValueError('Daily and weekly top routes differ')
    daily_count = int(daily.accuracy_passed.eq(True).sum())
    comparison = summaries['comparison']
    if daily_count != comparison['official_daily_top10_passed'] or summaries['weekly']['top10_test_weekly_passed'] != comparison['weekly_top10_passed']:
        raise ValueError('Release accuracy disagrees with comparison')
    rows = acceptance(daily_count, comparison['weekly_top10_passed'], len(top), summaries['policy']['early_event_rate'])
    # Check the exact same immutable parents again before writing the checkpoint.
    for role, folder in folders.items():
        if sha256(folder / ('manifest.json' if role == 'daily' else 'summary.json')) != hashes[role]:
            raise ValueError('Release parent changed during check')
    out.mkdir()
    bundle['release_checkpoint'] = output_id
    write_json(out / 'delivery.json', bundle)
    pd.DataFrame(rows).to_csv(out / 'readiness.csv', index=False, encoding='utf-8-sig')
    report = ('<!doctype html><html lang="vi"><meta charset="utf-8"><title>SIGMA · Kiểm tra M2–M3</title>'
              '<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px}table{border-collapse:collapse;width:100%}'
              'td,th{border:1px solid #ddd;padding:12px;text-align:left}h1{color:#075985}</style>'
              '<h1>SIGMA · Bộ sản phẩm dùng báo cáo M2–M3</h1><p>Đã kiểm tính toàn vẹn và đúng bộ run. Chưa nghiệm thu toàn bài.'
              ' Đánh giá hồi cứu; dữ liệu và đầu ra giữ local.</p>' + pd.DataFrame(rows).to_html(index=False, escape=True)
              + '<h2>Bộ run đã khóa</h2><ul>' + ''.join('<li>' + html.escape(role + ': ' + ident) + '</li>' for role, ident in ids.items())
              + '</ul><p>Đối soát chi tiết độc lập và AppTest phải được chạy riêng; kiểm hash này không thay chúng.</p></html>')
    (out / 'readiness.html').write_text(report, encoding='utf-8')
    summary = {'kind': 'local_product_release_checkpoint', 'status': 'integrity_verified',
               'created_at_utc': datetime.now(timezone.utc).isoformat(), 'product_runs': ids, 'parent_hashes': hashes,
               'source_sha256': summaries['daily']['source_sha256'], 'project_fully_accepted': False,
               'daily_top10_passed': daily_count, 'weekly_top10_passed': comparison['weekly_top10_passed'],
               'tests_or_independent_verifiers_run_by_this_command': False,
               'files': {p.name: sha256(p) for p in out.iterdir() if p.is_file()}}
    write_json(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ['files', 'parent_hashes']}, ensure_ascii=False), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery-config', default='data/configs/config.delivery.json')
    parser.add_argument('--output-id', required=True)
    for role in ['delivery', 'policy', 'stock', 'comparison']:
        parser.add_argument('--' + role + '-run', required=True)
    args = parser.parse_args()
    execute(args.delivery_config, args.output_id, args.delivery_run, args.policy_run, args.stock_run, args.comparison_run)
