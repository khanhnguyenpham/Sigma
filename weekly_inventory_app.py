"""Weekly forecast stock recommendations and unchanged-denominator replay."""
import json

import pandas as pd
import streamlit as st

from delivery import delivery_settings
from src.common import ROOT
from weekly_inventory import validate_inventory

st.set_page_config(page_title='SIGMA · Tồn từ dự báo tuần', page_icon='📋', layout='wide')
st.title('Tồn kho và khuyến nghị từ dự báo tổng tuần')
bundle = delivery_settings()
runs = []
for p in (ROOT / 'outputs').glob('*'):
    if not (p / 'summary.json').is_file():
        continue
    try:
        info = validate_inventory(p)
        if info['weekly_run'] == bundle['weekly_run'] and info['daily_run'] == bundle['daily_run']:
            runs.append(p)
    except (OSError, ValueError, KeyError):
        continue
if not runs:
    st.info('Chưa có khuyến nghị tồn đã kiểm cho cặp run hiện hành. Chạy weekly_inventory.py theo README.')
    st.stop()
folder = max(runs, key=lambda p: p.stat().st_mtime_ns)
info = validate_inventory(folder)
rec = pd.read_csv(folder / 'weekly_item_recommendations.csv')
country = st.sidebar.selectbox('Điểm đến', sorted(rec.destination_country.unique()))
carrier = st.sidebar.selectbox('Nhà mạng', sorted(rec.loc[rec.destination_country.eq(country), 'carrier'].unique()))
view = rec.loc[rec.destination_country.eq(country) & rec.carrier.eq(carrier)]
st.caption(f"Chốt {pd.Timestamp(info['as_of_date']).date()} · Tồn mô phỏng từ {info['daily_run']} · Dự báo từ {info['weekly_run']}")
st.info('Tồn khả dụng đã trừ khi nhận đặt hàng trong sổ mô phỏng. Giao khách D+7 không trừ tồn lần nữa. Thời gian nhập hàng về kho giữ riêng theo đối tác.')
a, b, c = st.columns(3)
a.metric('Tồn khả dụng mô phỏng', int(view.on_hand.sum()))
b.metric('Hàng đang về mô phỏng', int(view.pending_quantity.sum()))
c.metric('Lượng đặt thêm đề xuất', int(view.Q.sum()))
st.dataframe(view, hide_index=True)
st.download_button('Tải khuyến nghị theo tuyến', view.to_csv(index=False).encode('utf-8-sig'),
    file_name='sigma_weekly_inventory_recommendations.csv', mime='text/csv')
st.warning('Đây là khuyến nghị tại snapshot; chưa gửi đơn đặt hàng và chưa chạy lại toàn bộ chính sách liên tục bằng mô hình tuần.')
st.write(f"Replay giữ nguyên 5.520 cửa sổ và các sự kiện cạn thực của mô phỏng: cảnh báo sớm ≥7 ngày {info['early_event_rate']:.2%}, precision {info['precision']:.2%}, recall {info['recall']:.2%}.")
st.dataframe(pd.read_csv(folder / 'weekly_inventory_metrics.csv'), hide_index=True)
st.caption('MAPE tuần và lịch giao D+7 chưa đủ để nhận cảnh báo đạt trong mọi trường hợp. Mẫu số replay không bỏ các ca cạn trước ngày 7.')
