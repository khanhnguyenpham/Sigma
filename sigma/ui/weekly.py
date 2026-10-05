"""Local seven-day quantity dashboard; no training or upload on page load."""
import os

import pandas as pd
import streamlit as st

from src.common import ROOT, ROUTE
from sigma.verification.weekly import validate_weekly

st.set_page_config(page_title='SIGMA · Tổng bán 7 ngày', page_icon='📊', layout='wide')
st.title('SIGMA · Dự báo tổng quantity bán trong 7 ngày')
st.caption('Hai khối riêng: ngày 1–7 và 8–14 · UTC · Chạy và lưu dữ liệu tại máy này')
st.info('MAPE tuần và MAPE ngày là hai phép đánh giá khác nhau. Kết quả tuần chưa xác nhận đạt R05 theo ngày của kickoff.')
folders = []
for p in (ROOT / 'outputs').glob('*'):
    if p.is_dir() and (p / 'summary.json').is_file():
        try:
            if validate_weekly(p)['kind'] == 'weekly_quantity_run':
                folders.append(p)
        except (OSError, ValueError, KeyError):
            continue
folders.sort(key=lambda p: p.name, reverse=True)
if not folders:
    st.warning('Chưa có run tuần hoàn tất và đúng hash. Chạy weekly_forecast.py theo README.')
    st.stop()
names = [p.name for p in folders]
preferred = os.environ.get('SIGMA_WEEKLY_RUN_ID')
chosen = st.sidebar.selectbox('Run tuần', names, index=names.index(preferred) if preferred in names else 0)
folder = ROOT / 'outputs' / chosen
try:
    summary = validate_weekly(folder)
except (OSError, ValueError, KeyError):
    st.error('Run đã thay đổi hoặc thiếu tệp. Không hiển thị kết quả chưa kiểm chứng.')
    st.stop()
forecast = pd.read_csv(folder / 'weekly_forecast.csv')
selected = pd.read_csv(folder / 'selected_weekly_models.csv')
routes = forecast[ROUTE].drop_duplicates().sort_values(ROUTE)
country = st.sidebar.selectbox('Điểm đến', sorted(routes.destination_country.unique()))
carrier = st.sidebar.selectbox('Nhà mạng', sorted(routes.loc[routes.destination_country.eq(country), 'carrier'].unique()))
cadence = st.sidebar.selectbox('Lịch đánh giá', ['daily_origins', 'seven_day_origins'],
    format_func=lambda value: 'Dự báo mới mỗi ngày' if value == 'daily_origins' else 'Dự báo mới mỗi 7 ngày')
block = st.sidebar.selectbox('Khối dự báo', [1, 2], format_func=lambda value: 'Ngày 1–7' if value == 1 else 'Ngày 8–14')
def route(frame):
    return frame.loc[frame.destination_country.eq(country) & frame.carrier.eq(carrier)]

tabs = st.tabs(['Dự báo tuần', 'Sai số và baseline', 'Phân bổ về ngày', 'Kiểm chứng'])
with tabs[0]:
    st.subheader(f'{country} · {carrier}')
    st.dataframe(route(forecast), hide_index=True)
    st.caption('Forecast nối tiếp snapshot 2024–2025, không phải dữ liệu cập nhật hôm nay. Actual tương lai chưa có được để trống. Quantity là số sản phẩm, không phải số đơn hoặc doanh thu.')
    st.dataframe(route(selected), hide_index=True)
    daily = pd.read_csv(folder / 'daily_sales.csv', parse_dates=['date'])
    bins = route(daily).set_index('date').sales_qty.resample('168h', origin='start')
    history = bins.sum().loc[bins.count().eq(7)]
    st.line_chart(history.rename('Quantity lịch sử / 7 ngày'))
    st.caption('Chỉ hiển thị nhóm đủ 7 ngày, gộp từ đầu chuỗi; không vẽ tuần cuối thiếu ngày như một tuần tụt bán. Cửa sổ chấm sai số ở tab tiếp theo gắn với ngày dự báo.')
with tabs[1]:
    st.warning('Test đã được xem trong các thử nghiệm ngày trước đây; chưa phải kiểm định độc lập mới.')
    scores = pd.read_csv(folder / 'selected_test_weekly_metrics.csv')
    view = scores.loc[scores.cadence.eq(cadence) & scores.week_block.eq(block)]
    top = view.loc[view.is_top10]
    passed = int((top.mape_positive_week_pct.le(20) & top.coverage.eq(1)).sum())
    st.metric('Tuyến chủ lực có MAPE tổng tuần ≤20% trên test hồi cứu', f'{passed}/{len(top)}')
    if len(top) < 10:
        st.caption(f'Run này có {len(top)} tuyến chủ lực; chưa phải phép chấm đủ 10 tuyến của snapshot được cung cấp.')
    st.dataframe(top, hide_index=True)
    st.dataframe(route(view), hide_index=True)
    validation = pd.read_csv(folder / 'validation_weekly_metrics.csv')
    st.caption('So sánh tất cả mô hình/baseline trên validation; lựa chọn khóa trước chấm test.')
    st.dataframe(route(validation.loc[validation.cadence.eq(cadence) & validation.week_block.eq(block)]), hide_index=True)
    pred = pd.read_csv(folder / 'test_weekly_predictions.csv', parse_dates=['as_of_date'])
    chart = route(pred.loc[pred.week_block.eq(block)])
    if cadence == 'seven_day_origins':
        chart = chart.loc[chart.weekly_cadence.eq(True)]
    st.line_chart(chart.set_index('as_of_date')[['actual_qty_7d', 'forecast_qty_7d']])
with tabs[2]:
    allocation = pd.read_csv(folder / 'daily_allocation.csv', parse_dates=['target_date'])
    st.caption('Phân bổ theo tỷ trọng weekday trong 90 ngày quá khứ, bảo toàn tổng từng tuần. Đây chưa phải dự báo ngày độc lập hoặc chính sách tồn đã nghiệm thu.')
    st.dataframe(route(allocation), hide_index=True)
    st.bar_chart(route(allocation).set_index('target_date').forecast_qty)
with tabs[3]:
    st.json({k: v for k, v in summary.items() if k != 'files' and v is not None})
    st.download_button('Tải dự báo tuần của tuyến đang xem', route(forecast).to_csv(index=False).encode('utf-8-sig'),
        file_name='sigma_weekly_route.csv', mime='text/csv')
