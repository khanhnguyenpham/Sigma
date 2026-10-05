"""Weekly forecast stock recommendations and unchanged-denominator replay."""
import pandas as pd
import streamlit as st

from src.common import ROOT
from sigma.inventory.snapshot import validate_inventory
from sigma.inventory.policy import validate_policy
from sigma.ui.bundle import folders_for, settings_for_ui
from sigma.analysis.alert_diagnostics import explain_events

st.set_page_config(page_title='SIGMA · Tồn từ dự báo tuần', page_icon='📋', layout='wide')
st.title('Tồn kho và khuyến nghị từ dự báo tổng tuần')
bundle = settings_for_ui()
runs = []
for p in folders_for(bundle, 'stock'):
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
sku = st.sidebar.selectbox('Mặt hàng SKU', ['Tất cả', *sorted(view.sku.unique())])
product_type = st.sidebar.selectbox('Loại sản phẩm', ['Tất cả', *sorted(view.product_type.unique())])
def item_filter(frame):
    if sku != 'Tất cả':
        frame = frame.loc[frame.sku.eq(sku)]
    if product_type != 'Tất cả':
        frame = frame.loc[frame.product_type.eq(product_type)]
    return frame
view = item_filter(view)
st.caption(f"Chốt {pd.Timestamp(info['as_of_date']).date()} · Tồn mô phỏng từ {info.get('stock_source_run', info['daily_run'])} · Dự báo từ {info['weekly_run']}")
st.info('Tồn khả dụng đã trừ khi nhận đặt hàng trong sổ mô phỏng. Giao khách D+7 không trừ tồn lần nữa. Thời gian nhập hàng về kho giữ riêng theo đối tác.')
a, b, c = st.columns(3)
a.metric('Tồn khả dụng mô phỏng', int(view.on_hand.sum()))
b.metric('Hàng đang về mô phỏng', int(view.pending_quantity.sum()))
c.metric('Lượng đặt thêm đề xuất', int(view.Q.sum()))
st.dataframe(view, hide_index=True, column_config={
    'sku': 'Mặt hàng', 'product_type': 'Loại sản phẩm', 'partner_id': 'Đối tác giả định',
    'on_hand': 'Tồn khả dụng', 'pending_quantity': 'Hàng đang về', 'SS': 'Tồn an toàn (SS)',
    'ROP': 'Điểm đặt lại (ROP)', 'S': 'Mức tồn mục tiêu', 'IP': 'Tồn + hàng đang về',
    'Q': 'Lượng đặt đề xuất', 'needs_replenishment': 'Dưới điểm đặt lại',
    'expected_depletion_date': 'Ngày cạn dự kiến', 'eta_if_ordered': 'Ngày nhập nếu đặt',
    'decision_applied': 'Đã áp dụng đặt hàng'})
empty = int(view.on_hand.eq(0).sum())
low = int((view.on_hand.gt(0) & view.on_hand.lt(view.ROP)).sum())
covered = int((view.needs_replenishment & view.Q.eq(0) & view.pending_quantity.gt(0)).sum())
st.caption(f'{empty} mặt hàng hết tồn; {low} mặt hàng còn tồn dưới điểm đặt lại; {covered} mặt hàng dưới ngưỡng nhưng đã có đủ lượng đang về nên không đặt thêm. Bộ lọc SKU/loại áp dụng cho khuyến nghị và sổ bên dưới.')
st.download_button('Tải khuyến nghị theo tuyến', view.to_csv(index=False).encode('utf-8-sig'),
    file_name='sigma_weekly_inventory_recommendations.csv', mime='text/csv')
st.warning('Khuyến nghị dùng tồn và hàng đang về của run mô phỏng ghi ở trên; không gửi đơn đặt hàng thật. Sổ chính sách tuần và các kịch bản được trình bày riêng bên dưới.')
st.write(f"Replay giữ nguyên {info['replay_windows']:,} cửa sổ và các sự kiện cạn thực của mô phỏng: cảnh báo sớm ≥7 ngày {info['early_event_rate']:.2%}, precision {info['precision']:.2%}, recall {info['recall']:.2%}.")
st.dataframe(pd.read_csv(folder / 'weekly_inventory_metrics.csv'), hide_index=True)
st.caption('MAPE tuần và lịch giao D+7 chưa đủ để nhận cảnh báo đạt trong mọi trường hợp. Mẫu số replay không bỏ các ca cạn trước ngày 7.')

policies = []
for p in folders_for(bundle, 'policy'):
    if not (p / 'summary.json').is_file():
        continue
    try:
        info = validate_policy(p)
        if info['weekly_run'] == bundle['weekly_run'] and info['daily_run'] == bundle['daily_run']:
            policies.append((p, info))
    except (OSError, ValueError, KeyError):
        continue
if policies:
    policy_folder, policy = max(policies, key=lambda v: v[0].stat().st_mtime_ns)
    with st.expander('Giải thích từng ca cảnh báo trong replay'):
        events = pd.read_csv(policy_folder / 'alerts.csv')
        event_view, overall = explain_events(events)
        st.write(f"Toàn bộ replay: {overall['actual_events']:,} sự kiện cạn; "
            f"{overall['events_before_day7']:,} ca cạn trước ngày 7; "
            f"{overall['events_with_7day_opportunity']:,} ca còn cơ hội ≥7 ngày, "
            f"trong đó bỏ sót {overall['missed_with_7day_opportunity']:,} ca.")
        st.caption('Mốc 7 ngày tính từ origin của từng đợt replay. Bắt đầu theo dõi khi đã gần cạn không tạo đủ 7 ngày báo trước. Đây là chẩn đoán hồi cứu, không dùng actual tương lai làm tín hiệu cảnh báo; tất cả sự kiện vẫn nằm trong mẫu số chính.')
        visible = item_filter(event_view.loc[event_view.destination_country.eq(country) & event_view.carrier.eq(carrier)])
        group = st.selectbox('Nhóm ca cảnh báo', ['Tất cả', *sorted(visible.diagnostic_group.unique())])
        if group != 'Tất cả':
            visible = visible.loc[visible.diagnostic_group.eq(group)]
        st.dataframe(visible, hide_index=True, column_config={
            'as_of_date': 'Ngày bắt đầu đợt', 'predicted_days': 'Ngày đến cạn dự kiến',
            'actual_days': 'Ngày đến cạn thực trong mô phỏng', 'diagnostic_group': 'Giải thích',
            'predicted_depletion_date': 'Ngày cạn dự kiến', 'actual_depletion_date': 'Ngày cạn trong mô phỏng'})
    st.subheader('Chính sách nhập hàng liên tục từ dự báo tuần')
    st.caption('Mô phỏng toàn kỳ 01/10–31/12/2025; giao khách D+7 giữ riêng, nhập kho có kịch bản nhận thiếu/trễ/không về.')
    policy_metrics = pd.read_csv(policy_folder / 'simulation_metrics.csv')
    st.dataframe(policy_metrics, hide_index=True)
    scenario = st.selectbox('Kịch bản tồn tuần', policy_metrics.loc[policy_metrics.evaluation.eq('continuous_replenishment_policy'), 'scenario_id'].tolist())
    @st.cache_data(show_spinner=False)
    def policy_route_table(path, expected_hash, country, carrier, scenario):
        parts = []
        for chunk in pd.read_csv(path, chunksize=50000, low_memory=False):
            parts.append(chunk.loc[chunk.destination_country.eq(country) & chunk.carrier.eq(carrier) & chunk.scenario_id.eq(scenario)])
        return pd.concat(parts, ignore_index=True)
    ledger = item_filter(policy_route_table(str(policy_folder / 'inventory_ledger.csv'), policy['files']['inventory_ledger.csv'], country, carrier, scenario))
    st.line_chart(ledger.groupby('date')[['receipts', 'scenario_demand', 'fulfilled', 'shortage', 'closing']].sum())
    st.dataframe(ledger, hide_index=True)
    st.caption(f"Run {policy_folder.name}: {policy['scenarios']} kịch bản, {policy['ledger_rows']:,} dòng sổ; đây là mô phỏng, không gửi đơn nhập thật.")
