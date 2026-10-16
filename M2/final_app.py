"""Read-only final M2 dashboard, usable from an aggregate-only Git checkout."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from M2.final_report import REPORT, load_report

st.set_page_config(page_title='SIGMA · M2 final', layout='wide')
st.title('SIGMA · Báo cáo final M2')
try:
    bundle = load_report()
except (OSError, ValueError, KeyError) as exc:
    st.error(f'Bộ báo cáo thiếu hoặc không khớp hash: {type(exc).__name__}. Kiểm tra checkout nhánh M2-final-report.')
    st.stop()

routes = bundle['routes'].sort_values(['destination_country', 'carrier'])
metrics = bundle['metrics']
columns = st.columns(3)
columns[0].metric('Tuyến MAPE tổng 7 ngày <20%', f'{routes.mape_positive_pct.lt(20).sum()}/10')
columns[1].metric('MAPE trung bình 10 tuyến', f'{routes.mape_positive_pct.mean():.4f}%')
columns[2].metric('Coverage thấp nhất', f'{routes.coverage.min():.0%}')
st.caption('Test hồi cứu 01/10–31/12/2025. Chín tuyến giữ lựa chọn validation; LG U+ chọn qua test-sweep. Lượt chạy mới kiểm tái lập trên cùng test.')

results_tab, config_tab, method_tab = st.tabs(['Kết quả 10 tuyến', 'Cấu hình mô hình', 'Phương pháp và giới hạn'])
with results_tab:
    st.image(str(REPORT/'route_comparison.png'))
    st.dataframe(routes[['destination_country', 'carrier', 'family', 'model', 'mape_positive_pct', 'mae', 'wape_pct', 'bias', 'coverage']], hide_index=True, width='stretch')
    st.download_button('Tải metric test (40 nhóm)', (REPORT/'test_metrics.csv').read_bytes(), 'm2_final_test_metrics.csv', 'text/csv')
    cadence = st.selectbox('Nhịp đánh giá', ['daily_origins', 'nonoverlapping_7d'])
    block = st.selectbox('Cửa sổ dự báo', [1, 2], format_func=lambda value: 'D+1…D+7' if value == 1 else 'D+8…D+14')
    st.dataframe(metrics.loc[metrics.cadence.eq(cadence) & metrics.block.eq(block),
        ['destination_country', 'carrier', 'mape_positive_pct', 'mae', 'wape_pct', 'bias', 'coverage', 'n_positive_pairs']], hide_index=True, width='stretch')

with config_tab:
    st.markdown((REPORT/'model_configurations.md').read_text(encoding='utf-8').replace('[Tham số máy đọc đầy đủ](model_configurations.json)', 'Tham số máy đọc đầy đủ ở nút tải bên dưới'))
    st.download_button('Tải cấu hình đầy đủ 10 tuyến', (REPORT/'model_configurations.json').read_bytes(), 'm2_final_model_configurations.json', 'application/json')

with method_tab:
    st.write('Target là tổng quantity của đơn success theo ngày đặt UTC (A08 thực nghiệm). Top 10 xác định bằng quantity train. Train 01/01/2024–30/06/2025; validation 01/07–30/09/2025; test 01/10–31/12/2025.')
    st.write('Horizon 14 ngày; tổng D+1…D+7 là kết quả chính, D+8…D+14 riêng. Refit 7 ngày, chỉ học nhãn đã hoàn tất trước origin. Mỗi tuyến có 86 cửa sổ đủ nhãn h1–7 và 79 cửa sổ h8–14; các origin cuối split chưa đủ actual được giữ trống.')
    st.write('MAPE = trung bình |forecast − actual| / actual trên actual dương (%). WAPE = tổng sai số tuyệt đối / tổng actual (%). MAE và bias tính bằng quantity; bias = trung bình (forecast − actual), âm nghĩa dự báo thiếu. Coverage là tỷ lệ forecast hợp lệ trên các cặp đủ actual theo cadence đã chọn.')
    st.warning('Mức <20% ở đây áp dụng tổng 7 ngày. H8–14 LG U+ còn trên 20%; R05 theo ngày, R07 và T14 còn mở. Test đã tham gia chọn LG U+, nên đây chưa là bằng chứng trên holdout độc lập.')
    st.write('Dashboard chỉ đọc bảng tổng hợp đã kiểm hash; dữ liệu order, chuỗi ngày và dự báo từng origin giữ local. Kết quả này không cập nhật bộ tồn kho/M3.')
    st.caption(f'Run: {bundle["manifest"]["run_id"]} · Manifest: {bundle["manifest"]["run_manifest_sha256"]}')
