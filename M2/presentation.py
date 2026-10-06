"""Read the frozen M2 evidence and export a local report; never fit models."""
import argparse
import base64
import html
import json
import shutil

import pandas as pd

from src.common import ROOT, ROUTE, sha256, validate_run, write_csv, write_json

RUN_ID = 'm2_improved_models_20261006_fixed'
REVIEW_ID = RUN_ID + '_review'
MANIFEST_SHA = '6407c68e9f520da51924fb021a275a947ada9cca15fbde06f35287218f3561dc'
REPORT_ID = 'm2_report_20261007'


def load_checkpoint(root=ROOT):
    folder = root / 'M2/artifacts' / RUN_ID
    review = root / 'M2/reports' / REVIEW_ID
    manifest = validate_run(folder)
    if sha256(folder / 'manifest.json') != MANIFEST_SHA:
        raise ValueError('Frozen M2 run differs from the approved checkpoint')
    verified = json.loads((review / 'summary.json').read_text(encoding='utf-8'))
    if verified['status'] != 'verified' or verified['run_manifest_sha256'] != MANIFEST_SHA:
        raise ValueError('Independent verification differs from M2 checkpoint')
    for name, digest in verified['files'].items():
        if sha256(review / name) != digest:
            raise ValueError('Verified M2 report changed')
    choices = pd.read_csv(folder / 'overall_selected_models.csv')
    metrics = pd.read_csv(folder / 'overall_test_metrics.csv')
    metrics = metrics.loc[metrics.block.eq(1) & metrics.cadence.eq('daily_origins')]
    selected = choices.merge(metrics, on=ROUTE + ['family', 'target', 'model'], validate='one_to_one')
    weekly = selected.loc[selected.target.eq('direct_7d')].sort_values(ROUTE)
    day = selected.loc[selected.target.eq('daily')].sort_values(ROUTE)
    if (len(weekly) != 10 or len(day) != 10 or int(weekly.passes_20_pct.sum()) != 9
            or day.passes_20_pct.any() or not selected.coverage.eq(1).all()):
        raise ValueError('M2 coverage or acceptance differs from the approved 9/10 result')
    deferred = weekly.loc[~weekly.passes_20_pct]
    if list(deferred[ROUTE].itertuples(index=False, name=None)) != [('South Korea', 'LG U+')]:
        raise ValueError('Deferred M2 route differs from the approved checkpoint')
    monthly = pd.read_csv(review / 'validation_monthly_selected.csv')
    monthly = monthly.loc[monthly.block.eq(1) & monthly.cadence.eq('daily_origins')]
    mixed = monthly.merge(choices[ROUTE + ['family', 'target', 'model']], on=ROUTE + ['family', 'target', 'model'], validate='many_to_one')
    monthly_summary = mixed.groupby(['target', 'month']).agg(
        mean_mape_pct=('mape_positive_pct', 'mean'), routes_le20=('passes_20_pct', 'sum')).reset_index()
    return {'manifest': manifest, 'verified': verified, 'choices': choices, 'weekly': weekly,
            'daily': day, 'monthly': monthly_summary,
            'summary': pd.read_csv(folder / 'summary.csv'),
            'audit': json.loads((folder / 'data_audit.json').read_text(encoding='utf-8')),
            'folder': folder, 'review': review}


def route_table(frame):
    columns = ROUTE + ['family', 'model', 'validation_mape_positive_pct', 'mape_positive_pct',
                      'mae', 'wape_pct', 'bias', 'n_positive_pairs', 'coverage', 'passes_20_pct']
    return frame[columns].rename(columns={
        'destination_country': 'Điểm đến', 'carrier': 'Nhà mạng', 'family': 'Họ mô hình', 'model': 'Biến thể',
        'validation_mape_positive_pct': 'MAPE validation (%)', 'mape_positive_pct': 'MAPE test (%)',
        'mae': 'MAE quantity', 'wape_pct': 'WAPE (%)', 'bias': 'Bias quantity',
        'n_positive_pairs': 'Số cặp dương', 'coverage': 'Độ phủ', 'passes_20_pct': 'Đạt ≤20%'})


def build():
    evidence = load_checkpoint()
    output = ROOT / 'M2/reports' / REPORT_ID
    training = ROOT / 'data/training' / REPORT_ID
    if output.exists() or training.exists():
        raise FileExistsError('Use the frozen report already built; never overwrite its evidence')
    output.mkdir(parents=True)
    training.mkdir(parents=True)
    cfg, folder = evidence['manifest']['config'], evidence['folder']
    daily = pd.read_csv(folder / 'daily_sales.csv', parse_dates=['date'])
    top = pd.read_csv(folder / 'top_routes.csv')
    top_daily = daily.merge(top[ROUTE], on=ROUTE, validate='many_to_one')
    splits = {}
    for name, start, end in [('train', cfg['observation_start'], cfg['train_end']),
                             ('validation', cfg['validation_start'], cfg['validation_end']),
                             ('test', cfg['test_start'], cfg['test_end'])]:
        subset = top_daily.loc[top_daily.date.between(start, end)]
        write_csv(training / f'{name}_daily_top10.csv', subset)
        splits[name] = {'start': start, 'end': end, 'rows': len(subset), 'quantity': float(subset.sales_qty.sum())}
    for name in ('daily_sales.csv', 'top_routes.csv', 'data_audit.json'):
        shutil.copyfile(folder / name, training / name)
    for name in ('overall_selected_models.csv', 'overall_test_metrics.csv', 'selection_lock.json', 'summary.csv'):
        shutil.copyfile(folder / name, output / name)
    write_csv(output / 'selected_weekly_routes.csv', evidence['weekly'])
    write_csv(output / 'selected_daily_routes.csv', evidence['daily'])
    write_csv(output / 'validation_monthly_mix.csv', evidence['monthly'])
    week, audit = evidence['weekly'], evidence['audit']
    image = base64.b64encode((evidence['review'] / 'comparison.png').read_bytes()).decode()
    table = lambda frame: '<div class="table">' + frame.to_html(index=False, float_format=lambda v: f'{v:.2f}', escape=True, border=0) + '</div>'
    sections = [
        '<h1>SIGMA · Báo cáo M2 · 07/10/2026</h1>',
        f'<p class="lead">Tổng 7 ngày: <strong>9/10 tuyến đạt ≤20%</strong> · MAPE trung bình <strong>{week.mape_positive_pct.mean():.2f}%</strong> · độ phủ 100%.</p>',
        '<p class="note">LG U+ chưa đạt: 20,69%, để tối ưu sau. Dự báo ngày 0/10, chưa đạt R05. Test đã được xem trước: đây là đánh giá hồi cứu.</p>',
        '<h2>1. Dữ liệu và cách đánh giá</h2>',
        f'<p>Snapshot order do người dùng mô tả là dữ liệu giả định; chưa xác minh cơ chế sinh. Nguồn {html.escape(cfg["source"])} có {audit["rows_raw"]:,} dòng, {audit["sales_rows"]:,} sale hợp lệ, tổng {audit["sales_quantity"]:,.0f} quantity và {audit["routes"]} tuyến. Target: quantity của success theo ngày đặt UTC, không lọc activation. Top 10 xác định bằng train.</p>',
        table(pd.DataFrame(splits).T.reset_index(names='split')),
        '<p>Horizon 14; báo D+1…D+7 chính, D+8…D+14 riêng; refit mỗi 7 ngày. Mỗi tuyến chọn theo MAPE validation, rồi MAE/tên biến thể; khóa trước test. MAPE chỉ ngày/tổng có actual dương; báo thêm MAE, WAPE, bias và độ phủ. Nhãn thiếu không biến thành 0.</p>',
        '<h2>2. Mô hình và phương pháp</h2>',
        '<p>12 biến thể đối chứng +14 mới: LightGBM 10, SARIMA 8, Prophet 8; 50 cấu hình biến thể × mục tiêu, 500 ứng viên tuyến × cấu hình validation. Hai hiệu chỉnh LightGBM chỉ cho tổng 7; tối đa 3 worker local.</p>',
        '<p><strong>Ngày:</strong> dự báo quantity từng ngày h1–14, rồi cộng h1–7 để so tổng. <strong>Trực tiếp tổng 7:</strong> LightGBM học nhãn tổng D+1…D+7; SARIMA/Prophet học S(t)=sum(y[t−6:t]) rồi lấy S(D+7), S(D+14). Không lấy bước D+1 của chuỗi tổng hoặc cộng đầu ra ngày để gọi trực tiếp.</p>',
        '<p>LightGBM học pooled top 10 với lag/rolling/lịch, có biến thể chuẩn hóa mức bán 90 ngày và feature năm; hoàn nguyên quantity trước chấm. SARIMA riêng tuyến có state update, log1p và sin/cos năm. Prophet riêng tuyến thử bật/tắt năm, tuần, cửa sổ 365/540 ngày. Lỗi hội tụ làm ứng viên bị loại. Hiệu chỉnh tổng dùng dự báo ngoài mẫu quá khứ 56 ngày, prior 4 tuần và hệ số 0,5–1,5; chỉ dùng actual đã hoàn tất.</p>',
        table(evidence['summary']),
        f'<img alt="So sánh ba họ mô hình" src="data:image/png;base64,{image}">',
        '<p>Dự báo ngày hữu ích cho lịch giao/vận hành, nhưng lỗi ngày có thể tích lũy khi cộng. Trực tiếp tổng 7 khớp quyết định theo tuần và có MAPE tổng tốt hơn trong lượt này; chưa cung cấp lịch từng ngày, cần kiểm riêng nếu phân bổ xuống ngày. MAPE ngày và MAPE tổng có mẫu số khác nhau; không dùng tổng để nhận đạt ngày.</p>',
        '<h2>3. Mô hình tổng 7 được chọn từng tuyến</h2>', table(route_table(week)),
        '<p>LightGBM cho 9 tuyến; Prophet cho au (KDDI), chọn bằng validation. SARIMA giữ làm đối chứng. Không đổi mô hình sau khi xem test.</p>',
        '<h2>4. Dự báo ngày và độ ổn định</h2>', table(route_table(evidence['daily'])), table(evidence['monthly']),
        '<p>Tháng 9 validation tổng 7: 18,70%, 7/10, yếu hơn tháng 7–8. Báo tháng chỉ chẩn đoán; không chọn lại theo tháng/test.</p>',
        '<h2>5. Kết luận và bước sau</h2>',
        '<p>Dùng kết quả 9/10 cho báo cáo M2 ngày mai. LG U+ 20,69% là tuyến chưa đạt được giữ trong bảng; hoãn tối ưu theo quyết định người dùng. R05 ngày vẫn chưa đạt; chưa nghiệm thu toàn bài. Chưa thay sản phẩm V13/tồn/cảnh báo.</p>',
        f'<p>Đối soát độc lập {evidence["verified"]["raw_quantity_pairs_checked"]:,} dòng/{evidence["verified"]["metric_groups_checked"]:,} nhóm metric; 2 ứng viên SARIMA lỗi được loại. Run đã seal, khóa lựa chọn và actual tương lai được kiểm. Mã và test local; dữ liệu/kết quả riêng tư không upload.</p>',
        f'<p class="hash">Run: {RUN_ID}<br>Manifest SHA256: {MANIFEST_SHA}<br>Selection SHA256: {evidence["manifest"]["selection_hashes"]["overall_selected_models.csv"]}<br>Raw SHA256: {evidence["manifest"]["source_sha256"]}</p>',
    ]
    document = '<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGMA M2 · 07/10/2026</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#183048;max-width:1250px;margin:auto;padding:36px;background:#f6f8fb}h1,h2{color:#124e78}h2{margin-top:36px}.lead{font-size:22px}.note{padding:16px;background:#fff0d8;border-left:5px solid #d38d20}.table{overflow-x:auto;background:white;border-radius:8px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;text-align:left;border-bottom:1px solid #e1e8ef}th{background:#e6f0f7}img{max-width:100%;background:white;margin-top:20px}.hash{font:12px/1.8 monospace;overflow-wrap:anywhere}@media print{body{padding:0;background:white}.table{overflow:visible}table{font-size:9px}h2{break-after:avoid}}</style><main>' + '\n'.join(sections) + '</main></html>'
    (output / 'index.html').write_text(document, encoding='utf-8')
    (training / 'README.md').write_text('# Dữ liệu M2 đã dẫn xuất\n\nNguồn raw ở data/sigma_sim_data_orders.csv giữ nguyên. Các bảng daily/top10/audit sao chép đúng byte từ run đã seal; ba bảng split top10 cắt theo ngày, quantity được bảo toàn. Train kết thúc30/06/2025; validation/test không được dùng để chọn top10 hoặc tạo nhãn fit trước cutoff. Không có order/customer ID trong bảng train.\n', encoding='utf-8')
    write_json(training / 'manifest.json', {'run_id': RUN_ID, 'run_manifest_sha256': MANIFEST_SHA, 'raw_sha256': evidence['manifest']['source_sha256'], 'splits': splits, 'files': {p.name: sha256(p) for p in training.iterdir() if p.is_file()}})
    write_json(output / 'checkpoint.json', {'status': 'frozen', 'report_date': '2026-10-07', 'run_id': RUN_ID, 'run_manifest_sha256': MANIFEST_SHA, 'selection_sha256': evidence['manifest']['selection_hashes']['overall_selected_models.csv'], 'deferred_route': ['South Korea', 'LG U+'], 'retrained': False, 'test_limit': 'retrospective', 'files': {p.name: sha256(p) for p in output.iterdir() if p.is_file()}})
    print(output / 'index.html')
    return output


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
