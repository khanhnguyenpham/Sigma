"""M2 presentation reads frozen evidence; opening it never trains a model."""
import streamlit as st
from M2.presentation import load_checkpoint, route_table

st.set_page_config(page_title='SIGMA · M2', page_icon='📊', layout='wide')
st.title('SIGMA · Báo cáo M2 · 07/10/2026')
try:
    evidence = load_checkpoint()
except (OSError, ValueError, KeyError) as error:
    st.error('Thiếu hoặc sai bộ kết quả M2 đã khóa. Xem M2/README.md để chuẩn bị dữ liệu local.')
    st.stop()
weekly, daily = evidence['weekly'], evidence['daily']
columns = st.columns(3)
columns[0].metric('Tuyến tổng 7 đạt ≤20%', f'{int(weekly.passes_20_pct.sum())}/10')
columns[1].metric('MAPE tổng 7 trung bình', f'{weekly.mape_positive_pct.mean():.2f}%')
columns[2].metric('Độ phủ', '100%')
st.caption('Lựa chọn khóa bằng validation · Test hồi cứu · Không huấn luyện khi mở báo cáo')
st.warning('LG U+ 20,69% chưa đạt, để tối ưu sau. Dự báo ngày 0/10; R05 và nghiệm thu toàn bài còn mở.')
data_tab, method_tab, result_tab = st.tabs(['Dữ liệu', 'Mô hình & phương pháp', 'Kết quả từng tuyến'])
with data_tab:
    cfg, audit = evidence['manifest']['config'], evidence['audit']
    st.write(f'Snapshot do người dùng mô tả là dữ liệu giả định: {audit["rows_raw"]:,} dòng, {audit["sales_quantity"]:,.0f} quantity sale hợp lệ, {audit["routes"]} tuyến. Chưa xác minh cơ chế sinh.')
    st.write('Target: quantity success theo ngày đặt UTC; không lọc activation. Top 10 chỉ theo train. Raw giữ nguyên; bảng train/split local ở data/training/m2_report_20261007.')
    st.table({'Tập': ['Train', 'Validation', 'Test'], 'Từ': [cfg['observation_start'], cfg['validation_start'], cfg['test_start']], 'Đến': [cfg['train_end'], cfg['validation_end'], cfg['test_end']]})
with method_tab:
    st.write('26 biến thể trong ba họ; 50 cấu hình ngày–tổng 7, giữ 12 đối chứng. H14, refit 7 ngày, tối đa 3 worker; lựa chọn MAPE validation rồi MAE/tên biến thể, khóa trước test.')
    st.write('Ngày: dự báo h1–14, cộng h1–7 khi so tổng. Trực tiếp tổng 7: LightGBM học nhãn D+1…D+7; SARIMA/Prophet học tổng trượt S(t), lấy S(D+7) và S(D+14).')
    st.write('LightGBM: pooled top 10, lag/rolling/lịch, chuẩn hóa 90 ngày và feature năm. SARIMA: riêng tuyến, state update/log1p/SARIMAX. Prophet: riêng tuyến, thử mùa vụ năm–tuần và cửa sổ 365/540 ngày. Hiệu chỉnh dùng lịch sử ngoài mẫu đủ nhãn tại cutoff.')
    st.image(str(evidence['review'] / 'comparison.png'))
    st.dataframe(evidence['summary'], hide_index=True)
    st.write('Ngày cung cấp lịch vận hành chi tiết nhưng cộng lỗi có thể tích lũy; tổng trực tiếp phù hợp quyết định theo tuần, chưa cung cấp lịch từng ngày. MAPE tổng không thay R05 ngày.')
with result_tab:
    target = st.radio('Phương pháp', ['Trực tiếp tổng 7', 'Dự báo ngày'], horizontal=True)
    frame = weekly if target == 'Trực tiếp tổng 7' else daily
    st.dataframe(route_table(frame).style.format(precision=2), hide_index=True, width='stretch')
    st.download_button('Tải bảng đang xem', route_table(frame).to_csv(index=False).encode('utf-8-sig'), 'm2_selected_routes.csv', 'text/csv')
    st.subheader('Độ ổn định validation tháng 7–8–9')
    st.dataframe(evidence['monthly'], hide_index=True)
    st.write('Tháng 9 tổng 7 kém ổn định hơn tháng 7–8. Giữ lựa chọn đã khóa; không chọn lại từ test. LightGBM cho 9 tuyến, Prophet cho au (KDDI).')
