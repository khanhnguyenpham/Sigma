"""Customer D+7 commitments; no claim of observed deliveries or sales accuracy."""
import os

import pandas as pd
import streamlit as st

from sigma.delivery.customer import validate_delivery
from src.common import ROOT, ROUTE
from sigma.ui.bundle import folders_for, settings_for_ui

st.set_page_config(page_title='SIGMA · Giao hàng D+7', page_icon='📦', layout='wide')
st.title('SIGMA · Giao đến khách sau đúng 7 ngày')
st.caption('Ngày đặt D → ngày giao D+7 · Ngày lịch UTC, gồm cuối tuần · Không trễ giao trong giả định')
folders = []
bundle = settings_for_ui()
for p in folders_for(bundle, 'delivery'):
    if p.is_dir() and (p / 'summary.json').is_file():
        try:
            info = validate_delivery(p)
            if info['weekly_run'] == bundle['weekly_run'] and info['daily_run'] == bundle['daily_run']:
                folders.append((info['created_at_utc'], p))
        except (OSError, ValueError, KeyError):
            continue
folders.sort(reverse=True)
if not folders:
    st.info('Chưa có lịch giao đã kiểm tra. Chạy delivery.py theo README trước.')
    st.stop()
names = [p.name for _, p in folders]
preferred = os.environ.get('SIGMA_DELIVERY_RUN_ID')
name = st.sidebar.selectbox('Run lịch giao', names, index=names.index(preferred) if preferred in names else 0)
folder = ROOT / 'outputs' / name
try:
    summary = validate_delivery(folder)
except (OSError, ValueError, KeyError):
    st.error('Run lịch giao đã thay đổi hoặc thiếu tệp; không hiển thị kết quả.')
    st.stop()
view = pd.read_csv(folder / 'delivery_projection.csv', parse_dates=['delivery_date', 'as_of_date'])
routes = view[ROUTE].drop_duplicates().sort_values(ROUTE)
country = st.sidebar.selectbox('Điểm đến', sorted(routes.destination_country.unique()))
carrier = st.sidebar.selectbox('Nhà mạng', sorted(routes.loc[routes.destination_country.eq(country), 'carrier'].unique()))
chosen = view.loc[view.destination_country.eq(country) & view.carrier.eq(carrier)]
st.info('Bảy ngày đầu là lịch của đơn đã đặt. Từ ngày 8 trở đi là lượng giao dự kiến từ dự báo đơn mới; chưa phải đơn đã nhận.')
left, right = st.columns(2)
left.metric('Đơn vị đã đặt, dự kiến giao 7 ngày tới', int(chosen.known_commitment_qty.sum()))
right.metric('Đơn vị dự báo bán mới trong 14 ngày tới', f'{chosen.forecast_from_future_orders_qty.sum():.2f}')
source_label = 'Nguồn demo do phần mềm sinh' if summary['source_kind'] == 'generated_synthetic_demo' else 'Snapshot do người dùng mô tả là giả định'
st.caption(f"Chốt dữ liệu: {pd.Timestamp(summary['as_of_date']).date()} · {source_label}; không phải dữ liệu cập nhật hôm nay.")
st.bar_chart(chosen.set_index('delivery_date')[['known_commitment_qty', 'forecast_from_future_orders_qty']])
st.dataframe(chosen, hide_index=True)
st.warning('Lịch D+7 không xác nhận kho đủ hàng. Xem riêng tồn/thiếu hụt; thời gian nhập hàng từ đối tác về kho được cấu hình độc lập.')
with st.expander('Lịch giao theo SKU / loại sản phẩm từ đơn đã có'):
    historical = pd.read_csv(folder / 'delivery_commitments.csv', parse_dates=['order_date', 'delivery_date'])
    historical = historical.loc[historical.destination_country.eq(country) & historical.carrier.eq(carrier)]
    backlog = historical.loc[historical.delivery_date.gt(pd.Timestamp(summary['as_of_date']))]
    st.dataframe(backlog, hide_index=True)
    st.download_button('Tải lịch giao đã đặt của tuyến', backlog.to_csv(index=False).encode('utf-8-sig'),
        file_name='sigma_known_delivery_commitments.csv', mime='text/csv')
st.caption('Không có sự kiện giao thực tế trong nguồn. Actual giao hàng để trống; lịch này được tính theo quy tắc giả định, không dùng làm MAPE dự báo bán.')
