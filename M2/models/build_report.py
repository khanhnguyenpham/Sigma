"""Summarize immutable M2 runs; never select models using test results."""
import sys
from pathlib import Path
import json
import os
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'outputs/_matplotlib_cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(ROOT))
from src.common import validate_run, sha256
from sigma.verification.weekly import validate_weekly

DAILY = ROOT / 'outputs/sigma_full_m2_20261005'
WEEKLY = ROOT / 'outputs/sigma_weekly_v13_m2_analysis_20261006'
VERIFIED = ROOT / 'outputs/sigma_weekly_v13_m2_analysis_verified_20261006'
OUT = ROOT / 'M2/reports/m2_analysis_20261006'
KEY = ['destination_country', 'carrier']

def markdown(frame):
    columns = list(frame.columns)
    lines = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for row in frame.itertuples(index=False, name=None):
        values = [f'{value:.2f}' if isinstance(value, (float, np.floating)) else str(value) for value in row]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)

def daily_family(model):
    for prefix, family in [('lgbm_mape_', 'LightGBM weighted L1'), ('lgbm_', 'LightGBM Poisson'),
        ('sarima_', 'SARIMA'), ('robust_', 'Weighted median'), ('calendar_', 'Calendar regression'),
        ('context_', 'LightGBM context'), ('distribution_', 'Seasonal distribution'),
        ('count_', 'Compound Poisson count'), ('cohort_', 'LightGBM cohort'),
        ('countmonth_', 'Monthly compound Poisson'), ('hiercount_', 'Hierarchical Poisson'),
        ('monthlad_', 'Monthly weighted LAD'), ('scaledmonthlad_', 'Monthly weighted LAD')]:
        if model.startswith(prefix):
            return family
    return 'Baseline'

def family_summary(metrics, family_column, metric_column, mae_column):
    selected = metrics.sort_values([metric_column, mae_column, 'model']).drop_duplicates([family_column] + KEY)
    rows = []
    for family, group in selected.groupby(family_column, sort=False):
        rows.append({'family': family, 'candidates': metrics.loc[metrics[family_column].eq(family), 'model'].nunique(),
            'routes_covered': len(group), 'validation_mean_mape_pct': group[metric_column].mean(),
            'validation_routes_le20': int(group[metric_column].le(20).sum())})
    return pd.DataFrame(rows), selected

def main():
    dm, wm = validate_run(DAILY), validate_weekly(WEEKLY)
    evidence = json.loads((VERIFIED / 'summary.json').read_text(encoding='utf-8'))
    assert evidence['status'] == 'verified' and evidence['weekly_summary_sha256'] == sha256(WEEKLY / 'summary.json')
    assert dm['source_sha256'] == wm['source_sha256']
    protocol = json.loads((WEEKLY / 'protocol.json').read_text(encoding='utf-8'))
    specs = protocol['weekly_config']['models']
    top = pd.read_csv(WEEKLY / 'top_routes.csv')[KEY]
    ds = pd.read_csv(DAILY / 'selected_models.csv').merge(top, on=KEY)
    dt = pd.read_csv(DAILY / 'metrics.csv').query("split == 'test' and horizon_group == 'h1_7'")
    daily = ds.merge(dt, on=KEY, suffixes=('', '_metric'))
    ws = pd.read_csv(WEEKLY / 'selected_weekly_models.csv').merge(top, on=KEY)
    wt = pd.read_csv(WEEKLY / 'selected_test_weekly_metrics.csv').query("week_block == 1 and cadence == 'daily_origins'")
    weekly = ws.merge(wt, on=KEY, suffixes=('', '_test'))
    route = top.merge(daily[KEY + ['model', 'validation_mape_positive_pct', 'mape_positive_pct']], on=KEY)
    route = route.rename(columns={'model': 'daily_model', 'validation_mape_positive_pct': 'daily_validation_mape_pct', 'mape_positive_pct': 'daily_test_mape_pct'})
    route = route.merge(weekly[KEY + ['model', 'mape_positive_week_pct', 'mape_positive_week_pct_test']], on=KEY)
    route = route.rename(columns={'model': 'weekly_model', 'mape_positive_week_pct': 'weekly_validation_mape_pct', 'mape_positive_week_pct_test': 'weekly_test_mape_pct'})
    comparison = pd.read_csv(VERIFIED / 'weekly_comparison.csv')
    print('Comparison columns:', comparison.columns.tolist())
    primary_comparison = comparison.merge(top, on=KEY).query("week_block == 1 and cadence == 'daily_origins'")
    comparison_pivot = top.merge(primary_comparison.pivot(index=KEY, columns='method', values='mape_positive_week_pct').reset_index(), on=KEY)
    comparison_summary = primary_comparison.groupby('method').agg(mean_route_mape_pct=('mape_positive_week_pct','mean'),
        routes_le20=('mape_positive_week_pct',lambda values: int(values.le(20).sum()))).reset_index()
    allocation_day = pd.read_csv(ROOT / 'outputs/m2_day_allocation_diagnostic_20261006.csv')
    native_allocation = pd.read_csv(VERIFIED / 'daily_allocation_diagnostic.csv').merge(top,on=KEY).query('week_block == 1')
    allocation_check = allocation_day.merge(native_allocation, on=KEY, validate='one_to_one')
    np.testing.assert_allclose(allocation_check.weekly_allocation_day_mape_602pairs, allocation_check.mape_positive_day_pct, rtol=0,atol=1e-8)
    assert allocation_check.daily_pairs.eq(602).all() and allocation_check.pairs.eq(602).all()
    reference_daily = [43.29,44.66,43.27,46.22,41.89,43.14,56.39,45.21,53.70,58.13]
    reference_weekly = [14.17,18.13,15.27,17.16,13.30,17.02,13.09,12.67,21.19,19.73]
    assert np.allclose(route.daily_test_mape_pct, reference_daily, atol=.006, rtol=0)
    assert np.allclose(route.weekly_test_mape_pct, reference_weekly, atol=.006, rtol=0), 'Fresh V13 differs from published comparison'
    assert len(route) == 10 and route.weekly_test_mape_pct.le(20).sum() == 9
    assert abs(route.weekly_test_mape_pct.mean() - 16.173459) < 1e-5
    dv = pd.read_csv(DAILY / 'validation_metrics.csv').merge(top, on=KEY)
    dv = dv.query("horizon_group == 'h1_7' and coverage == 1").dropna(subset=['mape_positive_pct']).copy()
    dv['family'] = dv.model.map(daily_family)
    df, df_best = family_summary(dv, 'family', 'mape_positive_pct', 'mae')
    wv = pd.read_csv(WEEKLY / 'validation_weekly_metrics.csv').merge(top, on=KEY)
    wv = wv.query("week_block == 1 and cadence == 'daily_origins' and coverage == 1").dropna(subset=['mape_positive_week_pct']).copy()
    wv['family'] = wv.model.map(lambda model: specs[model]['kind'])
    wf, wf_best = family_summary(wv, 'family', 'mape_positive_week_pct', 'mae_week_qty')
    daily_model_summary = dv.groupby(['family','model']).agg(routes_covered=('carrier','size'),
        validation_mean_mape_pct=('mape_positive_pct','mean'), validation_min_mape_pct=('mape_positive_pct','min'),
        validation_max_mape_pct=('mape_positive_pct','max'), validation_routes_le20=('mape_positive_pct',lambda values:int(values.le(20).sum()))).reset_index()
    weekly_model_summary = wv.groupby(['family','model']).agg(routes_covered=('carrier','size'),
        validation_mean_mape_pct=('mape_positive_week_pct','mean'), validation_min_mape_pct=('mape_positive_week_pct','min'),
        validation_max_mape_pct=('mape_positive_week_pct','max'), validation_routes_le20=('mape_positive_week_pct',lambda values:int(values.le(20).sum()))).reset_index()
    weekly_history = pd.DataFrame([
        ('V1',9,'Baseline + LightGBM trực tiếp',17.192945),
        ('V2',12,'Thêm đặc trưng cùng kỳ năm trước',16.090186),
        ('V3',15,'Thêm phối hợp trọng số cố định',16.180811),
        ('V4',18,'Thêm đặc trưng tổng hợp (macro)',15.997608),
        ('V5',30,'Thêm hiệu chỉnh causal',15.966928),
        ('V6',34,'Thêm hồi quy median tuần',16.109422),
        ('V7',38,'Thêm phối hợp thích ứng annual/linear',16.209849),
        ('V8',42,'Thêm mô hình riêng tuyến',16.209849),
        ('V9 / V12',48,'Phối hợp sau hiệu chỉnh / tổ chức mã',16.193421),
        ('V10',52,'Thêm phối hợp thích ứng annual/macro; top10 như V9',16.193421),
        ('V13',58,'Thêm booster 300 cây và hiệu chỉnh',16.173459)],
        columns=['Phiên bản','Số cấu hình','Phần mở rộng','MAPE test tổng 7 ngày (%)'])
    day_values = pd.read_csv(DAILY / 'daily_sales.csv', parse_dates=['date']).merge(top, on=KEY)
    day_values = day_values.loc[day_values.date.between('2025-07-01','2025-09-30')]
    cv_day = day_values.groupby(KEY).sales_qty.agg(lambda values: values.std(ddof=0)/values.mean())
    week_values = pd.read_csv(WEEKLY / 'validation_weekly_predictions.csv', usecols=KEY+['model','week_block','actual_qty_7d']).merge(top,on=KEY)
    week_values = week_values.query("model == 'week_last7' and week_block == 1")
    cv_week = week_values.groupby(KEY).actual_qty_7d.agg(lambda values: values.std(ddof=0)/values.mean())
    dispersion = pd.DataFrame({'daily_validation_cv':cv_day, 'seven_day_validation_cv':cv_week}).reset_index()
    OUT.mkdir(exist_ok=False)
    for name, frame in [('route_models.csv', route), ('daily_candidate_validation.csv', dv),
        ('weekly_candidate_validation.csv', wv), ('daily_family_validation.csv', df),
        ('weekly_family_validation.csv', wf), ('weekly_selected_test_all_metrics.csv', weekly),
        ('daily_selected_test_all_metrics.csv', daily), ('matched_weekly_comparison.csv', comparison),
        ('comparison_top10.csv', comparison_pivot), ('comparison_summary.csv', comparison_summary),
        ('daily_model_validation_summary.csv',daily_model_summary), ('weekly_model_validation_summary.csv',weekly_model_summary),
        ('weekly_history_documented.csv',weekly_history), ('validation_dispersion.csv',dispersion)]:
        frame.to_csv(OUT / name, index=False, encoding='utf-8-sig')
    allocation_day.to_csv(OUT / 'daily_allocation_matched_diagnostic.csv',index=False,encoding='utf-8-sig')
    labels = [f'{country} / {carrier}' for country, carrier in top.itertuples(index=False, name=None)]
    route_display = route.assign(Tuyến=labels)
    daily_display = route_display[['Tuyến','daily_model','daily_validation_mape_pct','daily_test_mape_pct']].rename(columns={
        'daily_model':'Mô hình ngày', 'daily_validation_mape_pct':'MAPE validation (%)', 'daily_test_mape_pct':'MAPE test (%)'})
    weekly_display = route_display[['Tuyến','weekly_model','weekly_validation_mape_pct','weekly_test_mape_pct']].rename(columns={
        'weekly_model':'Mô hình tổng 7 ngày', 'weekly_validation_mape_pct':'MAPE validation (%)', 'weekly_test_mape_pct':'MAPE test (%)'})
    sum_daily = comparison_pivot.sum_daily_v11.to_numpy()
    assert np.allclose(sum_daily, [16.88,28.65,25.93,32.59,30.18,27.79,33.97,36.18,27.54,39.28], atol=.006, rtol=0)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, axes = plt.subplots(1,2, figsize=(14,6.5), gridspec_kw={'width_ratios':[1,1.35]}, layout='constrained')
    y = np.arange(10)
    axes[0].barh(y, route.daily_test_mape_pct, color='#64748b')
    axes[0].set_yticks(y, labels)
    axes[0].set_title('MAPE từng ngày (R05)\nMục tiêu: quantity của từng ngày')
    axes[1].barh(y-.17, sum_daily, height=.32, label='Cộng 7 dự báo ngày', color='#94a3b8')
    axes[1].barh(y+.17, route.weekly_test_mape_pct, height=.32, label='Dự báo trực tiếp tổng 7 ngày V13', color='#0f766e')
    axes[1].set_yticks(y, labels)
    axes[1].set_title('MAPE tổng 7 ngày trên cùng 86 cửa sổ/tuyến\nMục tiêu: tổng quantity của 7 ngày')
    for axis in axes:
        axis.invert_yaxis()
        axis.axvline(20, color='#dc2626', linestyle='--', linewidth=1.2)
        axis.set_xlabel('MAPE (%) — thấp hơn là tốt hơn')
        axis.grid(axis='x', alpha=.2)
        axis.set_axisbelow(True)
    axes[1].legend(loc='upper center', bbox_to_anchor=(.5,-.14), fontsize=9)
    fig.suptitle('SIGMA M2 — test hồi cứu 01/10–31/12/2025\nHai biểu đồ có mục tiêu khác nhau; không suy kết quả tuần thành đạt R05 ngày', fontsize=13)
    fig.savefig(OUT / 'day_vs_week.png', dpi=180)
    plt.close(fig)
    report = '\n\n'.join([
        '# Đối chiếu kết quả M2 — 06/10/2026',
        'Run ngày local: `sigma_full_m2_20261005`, complete và hash hợp lệ. Run tuần tái lập mới: `sigma_weekly_v13_m2_analysis_20261006`, toàn bộ 58 cấu hình fit validation lại, khóa lựa chọn trước test. Verifier độc lập kiểm toàn bộ nhãn/metric/coverage/lựa chọn/không dùng nhãn tương lai và bảo toàn phân bổ tuần. Các con số top 10 khớp bảng V13 đã công bố đến độ làm tròn 0,01%. Không thay cấu hình sản phẩm hoặc run cũ.',
        f'Ngày: validation MAPE trung bình {route.daily_validation_mape_pct.mean():.6f}%, test {route.daily_test_mape_pct.mean():.6f}%, 0/10 đạt ≤20%. Tuần: validation {route.weekly_validation_mape_pct.mean():.6f}%, test {route.weekly_test_mape_pct.mean():.6f}%, 9/10 đạt; LG U+ chưa đạt. Trung bình là trung bình MAPE của 10 tuyến, không phải WAPE gộp.',
        'Train: 01/01/2024–30/06/2025; validation: 01/07–30/09/2025; test: 01/10–31/12/2025. Quantity bán success theo UTC; top 10 chỉ xếp bằng train. H1–7 là chỉ tiêu chính; h8–14 và cadence 7 ngày lưu riêng. Test đã được xem trong các đợt trước; kết quả hồi cứu, chưa là kiểm định độc lập trên dữ liệu mới.',
        '## Mô hình được khóa cho từng tuyến\n\nDự báo ngày:\n\n' + markdown(daily_display) + '\n\nDự báo trực tiếp tổng 7 ngày:\n\n' + markdown(weekly_display),
        '## Các nhóm mô hình ngày\n\nMỗi dòng chọn cấu hình tốt nhất trong nhóm cho từng tuyến **bằng validation**, rồi lấy trung bình 10 tuyến. Đây không phải test, không phải trung bình toàn bộ cấu hình và không thể so trực tiếp với MAPE target tuần. Một SARIMA không đủ coverage được loại khỏi lựa chọn.\n\n' + markdown(df),
        'Nghiên cứu ngày ngoài pool đã ghi trong E30/E32/E34: tám prototype monthly weighted-LAD (raw/scaled × window × alpha), chỉ hai có lợi được tích hợp; 12 ablation calendar/history/annual × raw/ratio × leaves7/31 chọn trong train cho validation mean44,968965%, 0/10 đạt; hiệu chỉnh/kết hợp causal chọn trong train cho validation mean45,106266%, 0/10 đạt. Hai campaign không cải thiện toàn bộ so V11 validation41,978903%, nên không tích hợp. Đây là số nhật ký, không nhận đã tái chạy campaign trong lượt này. Tham chiếu LP fit/score cùng validation là chẩn đoán lạc quan hồi cứu, không forecast ngoài mẫu hoặc mô hình nghiệm thu. Không có run Prophet được ghi nhận trong danh mục đã đối chiếu.',
        '## Các nhóm mô hình tổng 7 ngày\n\nCách tổng hợp tương tự, dùng MAPE validation tổng 7 ngày. `calibrated` là hiệu chỉnh nhân causal; `blend` phối hợp cố định; `adaptive_mix` học trọng số từ tuần quá khứ đã hoàn tất; `calibrated_blend` phối hợp sau hiệu chỉnh. Các tên nhóm là loại triển khai, các thành phần cơ sở có thể được dùng lại.\n\n' + markdown(wf),
        '## Lịch sử nghiên cứu tổng 7 ngày\n\nSố dưới đây từ nhật ký E36/E38/E40/E42/E43/E44/E53, không nhận đã tái chạy các phiên bản cũ trong lượt này. Mỗi phiên bản giữ lựa chọn validation riêng; không chọn phiên bản theo test. V14: 6 cấu hình mùa vụ ngoài pool V13, chỉ validation, 4/10 đạt và 0/10 cải thiện so V13; chưa chấm test hoặc tích hợp.\n\n' + markdown(weekly_history),
        '## So sánh cùng target\n\nCùng 86 cửa sổ đủ nhãn/tuyến, tổng quantity 7 ngày.\n\n' + markdown(comparison_summary) + '\n\n' + markdown(comparison_pivot),
        f'## Phân bổ tổng tuần xuống ngày\n\nTrên cùng602cặp h1–7/tuyến (chỉ các origin đủ7ngày), mô hình ngày có mean MAPE{allocation_day.daily_model_mape_602pairs.mean():.6f}%, còn phân bổ tổng tuần theo weekday90 ngày có{allocation_day.weekly_allocation_day_mape_602pairs.mean():.6f}%. Phân bổ kém hơn ở{int((allocation_day.weekly_allocation_day_mape_602pairs>allocation_day.daily_model_mape_602pairs).sum())}/10tuyến. Kết quả phân bổ khớp verifier độc lập1e-8. Đây là diagnostic chung602cặp, khác R05 chính thức623cặp. Không nhận weekly allocation là daily model đạt20%.\n\n' + markdown(allocation_day),
        '## Đề xuất\n\nDùng dự báo trực tiếp tổng 7 ngày, chọn mô hình riêng từng tuyến bằng validation, làm đầu vào chính cho kế hoạch nhu cầu và tồn. Giữ baseline đơn giản để theo dõi; không thay lựa chọn bằng model có test tốt hơn. Phân bổ xuống ngày bằng tỷ trọng weekday từ lịch sử chỉ là kế hoạch phân bổ, chưa chứng minh dự báo ngày đạt R05. Theo dõi đơn đã đặt và sổ tồn hằng ngày để xử lý spike và nguy cơ cạn giữa tuần. Khách giao D+7 và lead time nhập kho là hai thông số riêng.',
        'V13 không có MAPE test thấp nhất trong mọi phiên bản đã thử: V5 từng có 15,966928%, còn V13 là 16,173459%. V13 được chọn trước đọc test mới dựa trên validation (14,978399%, 10/10 đạt) và được kiểm/tích hợp; không quay về V5 chỉ vì test. Lịch sử tại E38/E52/E53 trong review-log.',
        'V13 so V12 chỉ giảm mean MAPE test tổng tuần khoảng0,019962 điểm phần trăm (16,193421%→16,173459%); số tuyến đạt giữ9/10 và LG U+ vẫn21,192259%. Cập nhật V14 không thay sản phẩm vì không cải thiện top10 validation. Không diễn giải số phiên bản mới thành cải thiện mạnh hoặc đã giải quyết tuyến chưa đạt.',
        'So sánh tổng dự báo ngày 29,898718% với tuần trực tiếp 16,173459% giữ cùng nhãn và cửa sổ, nhưng các daily model được chọn theo MAPE ngày, còn weekly model chọn theo MAPE tổng tuần. Nó không cô lập hoàn toàn kiến trúc khỏi mục tiêu lựa chọn. Campaign local cũ `sigma_weekly_m2_20261005` chọn theo tổng tuần trong pool 66 ứng viên (61 tổng daily + 3 baseline + 2 direct): chọn 8 sumdaily và 2 direct, test 16,721038%, 9/10 đạt. Nhóm 2 direct riêng có test 16,64%, 8/10 đạt. Đây là run khác, không phải V13; không chứng minh mọi phương án sumdaily đều kém.',
        'Ưu điểm ngày: nhìn được nhịp từng ngày, spike và thời điểm nguy cơ thiếu; nhược điểm: dao động lớn, MAPE nhạy với quantity thấp, kết quả chưa đạt. Ưu điểm tổng 7 ngày: giảm một phần biến động, khớp quyết định nhu cầu trong cửa sổ 7 ngày, test cùng target tốt hơn tổng daily ở cả 10 tuyến. Nhược điểm: mất thông tin ngày, tổng đúng vẫn có thể sai từng ngày, cửa sổ rolling chồng lấn, không giải quyết tự động chất lượng tồn/cảnh báo.',
        f'Tái tính từ CSV validation: CV ngày {cv_day.min():.6f}–{cv_day.max():.6f}; CV tổng 7 ngày {cv_week.min():.6f}–{cv_week.max():.6f}, khớp chẩn đoán đã công bố. CV dùng độ lệch chuẩn ddof=0 chia trung bình, không phải MAPE.',
        '## Bằng chứng chưa tái lập trong lượt này\n\nTheo `docs/day-week-comparison.md`, policy tuần V4 có fill 85,02% so với ngày 83,52%, thiếu 2.392 so 2.631 quantity; báo sớm ≥7 ngày 33,73% so 33,10%. Đây là số đã ghi trong tài liệu của run mô phỏng trên máy trước; lượt này không chạy lại policy. Nghiên cứu mùa vụ V14 chỉ validation: 4/10 đạt, 0/10 cải thiện top10 so V13, chưa tích hợp/chấm test (`docs/model-diagnostics.md`).',
        '## Giới hạn và nguồn\n\nR05 ngày vẫn mở; metric tổng tuần chưa được mentor xác nhận thay thế. Ngưỡng MAPE là trung bình trên các cặp có actual dương, không phải mọi ngày/tuần đều sai ≤20%. Ngày/tuần 0 vẫn giữ trong MAE/WAPE/bias; windows chồng lấn không là mẫu độc lập. Không suy MAPE 16,17% thành độ chính xác 83,83%. Nguồn availability chỉ là snapshot hồi cứu.',
        'Tài liệu repo: `docs/day-week-comparison.md`, `docs/model-diagnostics.md`, `docs/weekly-forecast.md`, E31/E38/E40/E53/E57 trong `docs/review-log.md`. Phương pháp metric: [Forecasting: Principles and Practice — Accuracy](https://otexts.com/fpp3/accuracy.html); [rolling origin](https://otexts.com/fpp3/tscv.html).',
        '![So sánh](' + str(OUT / 'day_vs_week.png').replace('\\','/') + ')'
    ])
    (OUT / 'M2_analysis.md').write_text(report, encoding='utf-8')
    metadata = {'daily_source_sha256': dm['source_sha256'], 'daily_manifest_sha256': sha256(DAILY/'manifest.json'),
        'fresh_weekly_summary_sha256': sha256(WEEKLY/'summary.json'), 'verifier_summary_sha256': sha256(VERIFIED/'summary.json'),
        'comparison_sum_daily_values': 'Recomputed by independent verifier on identical complete windows; matches published rounded comparison',
        'production_modified': False, 'test_is_independent': False,
        'files': {p.name:sha256(p) for p in OUT.iterdir() if p.is_file()}}
    (OUT / 'analysis_sources.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(route.round(4).to_string(index=False))
    print(wf.round(4).to_string(index=False))
    print('Report:', OUT / 'M2_analysis.md')

if __name__ == '__main__':
    main()
