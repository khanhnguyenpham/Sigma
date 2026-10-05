"""Show the authenticated comparison for the selected product bundle."""
import json

import pandas as pd
import streamlit as st

from src.common import ROOT, sha256
from sigma.delivery.customer import delivery_settings

st.set_page_config(page_title='SIGMA · So sánh ngày và tuần', page_icon='⚖️', layout='wide')
st.title('So sánh dự báo ngày và tổng 7 ngày')
bundle = delivery_settings()
runs = []
for folder in (ROOT / 'outputs').glob('*'):
    if not (folder / 'summary.json').is_file():
        continue
    try:
        summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
        if (summary.get('kind') != 'matched_day_week_comparison' or summary.get('status') != 'verified'
                or summary['weekly_run'] != bundle['weekly_run'] or summary['daily_run'] != bundle['daily_run']):
            continue
        for name, expected in summary['files'].items():
            path = (folder / name).resolve()
            if not path.is_relative_to(folder.resolve()) or sha256(path) != expected:
                raise ValueError('Comparison changed')
        runs.append(folder)
    except (OSError, ValueError, KeyError):
        continue
if not runs:
    st.info('Chưa có bảng so sánh đã kiểm cho bộ dự báo đang xem. Dùng lệnh python -m sigma compare theo README.')
    st.stop()
folder = max(runs, key=lambda p: p.stat().st_mtime_ns)
summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
st.caption(f"{summary['weekly_run']} · {summary['daily_run']} · Cùng nguồn, top train và cửa sổ test; đánh giá hồi cứu")
st.info('MAPE ngày và MAPE tuần có target khác nhau. So sánh công bằng theo tuần: cộng dự báo ngày thành tổng 7 ngày rồi chấm cùng cửa sổ với mô hình tuần trực tiếp.')
a, b = st.columns(2)
top = pd.read_csv(folder / 'top10_comparison.csv')
a.metric('Tiêu chí ngày R05', f"{summary['official_daily_top10_passed']}/{len(top)} tuyến")
b.metric('MAPE tổng 7 ngày ≤20%', f"{summary['weekly_top10_passed']}/{len(top)} tuyến")
st.dataframe(top, hide_index=True)
st.image(str(folder / 'weekly_comparison.png'))
st.caption('h1–7: 86 cửa sổ đầy đủ/tuyến; h8–14: 79. Cadence không chồng lấp 13/12 được báo riêng. MAPE chỉ trên actual dương; MAE/WAPE/bias và actual bằng 0 vẫn có trong bảng chi tiết.')
country = st.sidebar.selectbox('Điểm đến', sorted(top.destination_country.unique()))
carrier = st.sidebar.selectbox('Nhà mạng', sorted(top.loc[top.destination_country.eq(country), 'carrier'].unique()))
metrics = pd.read_csv(folder / 'matched_week_metrics.csv')
view = metrics.loc[metrics.destination_country.eq(country) & metrics.carrier.eq(carrier)]
st.subheader('Cùng cửa sổ: tuần trực tiếp, tổng mô hình ngày và baseline')
st.dataframe(view, hide_index=True)
st.download_button('Tải bảng so sánh theo tuyến', view.to_csv(index=False).encode('utf-8-sig'), 'sigma_comparison.csv', 'text/csv')
st.subheader('Phân bổ tuần xuống từng ngày: kiểm tra bổ sung')
days = pd.read_csv(folder / 'matched_daily_diagnostics.csv')
st.dataframe(days.loc[days.destination_country.eq(country) & days.carrier.eq(carrier)], hide_index=True)
st.caption('Cùng 602 cặp h1–7/tuyến, khác grid R05 623 cặp. Tổng tuần chính xác hơn không bảo đảm từng ngày đạt MAPE20%.')
st.subheader('13 kịch bản tồn kho với cùng nhu cầu và giả định')
st.dataframe(pd.read_csv(folder / 'stock_scenario_comparison.csv'), hide_index=True)
st.warning('Tồn/nhập là mô phỏng. Cảnh báo trước ≥7 ngày còn có ca không đạt; ngày giao khách D+7 không chứng minh độ chính xác dự báo hoặc bảo đảm nhập kho.')
