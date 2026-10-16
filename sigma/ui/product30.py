"""Local M3 interface: verified forecasts, simulated decisions and observed errors."""
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.common import ROOT, ROUTE, ITEM, sha256
from sigma.jobs.product30 import settings
from sigma.inventory.product30 import validate_product

st.set_page_config(page_title='SIGMA · M3',layout='wide',initial_sidebar_state='expanded')
st.markdown('<style>.block-container{padding-top:1.5rem}h1,h2,h3{color:#14324a}div[data-testid="stMetric"]{background:#f0f5f8;padding:12px;border-radius:6px}div[data-testid="stMetricValue"]{font-size:1.8rem}[data-testid="stAppDeployButton"]{display:none}</style>',unsafe_allow_html=True)


@st.cache_data(show_spinner='Đang kiểm tra bộ kết quả…')
def load_bundle(run_id, summary_digest, stamps):
    folder=ROOT/'outputs'/run_id
    summary=validate_product(folder)
    parent=ROOT/'outputs'/summary['aggregate_run']
    for name in [run_id,summary['aggregate_run']]:
        receipt=ROOT/'outputs'/(name+'_verification.json')
        if not receipt.is_file():raise ValueError('Bộ kết quả chưa có đối soát độc lập.')
        info=json.loads(receipt.read_text(encoding='utf-8'))
        source=ROOT/'outputs'/name/'summary.json'
        if info.get('status')!='verified' or info['summary_sha256']!=sha256(source):
            raise ValueError('Biên bản đối soát không khớp bộ kết quả.')
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    return {'summary':summary,'protocol':protocol,
        'metrics':pd.read_csv(folder/'simulation_metrics.csv'),
        'recommendations':pd.read_csv(folder/'recommendations_latest.csv'),
        'item_forecast':pd.read_csv(folder/'item_forecast_latest.csv',parse_dates=['target_date']),
        'alerts':pd.read_csv(folder/'alerts_14d.csv',parse_dates=['as_of_date','actual_depletion_date','predicted_depletion_date']),
        'delivery':pd.read_csv(folder/'delivery_projection.csv',parse_dates=['delivery_date']),
        'signals':pd.read_csv(folder/'business_signals.csv',parse_dates=['date']),
        'forecasts':pd.read_csv(parent/'daily_allocation.csv',parse_dates=['as_of_date','target_date']),
        'top':pd.read_csv(parent/'top10_results.csv'),
        'daily':pd.read_csv(parent/'daily_sales.csv',parse_dates=['date']),
        'selections':pd.read_csv(parent/'selected_models.csv')}


def filtered(frame,country,carrier,sku=None,ptype=None):
    frame=frame.copy()
    for col,choice in [('destination_country',country),('carrier',carrier),('sku',sku),('product_type',ptype)]:
        if col in frame and choice and choice!='Tất cả': frame=frame.loc[frame[col].eq(choice)]
    return frame


def download(label,frame,filename):
    st.download_button(label,frame.to_csv(index=False).encode('utf-8-sig'),file_name=filename,mime='text/csv')


LABELS={'destination_country':'Quốc gia / điểm đến','carrier':'Nhà mạng','product_type':'Loại sản phẩm',
    'model':'Mô hình','mape_positive_pct':'MAPE (%)','mae':'MAE (quantity)','wape_pct':'WAPE (%)',
    'bias':'Bias (quantity)','coverage':'Độ phủ','passes_20_pct':'Đạt ngưỡng 20%',
    'on_hand':'Tồn hiện có','SS':'Tồn an toàn','ROP':'Điểm đặt lại','S':'Mức tồn mục tiêu',
    'IP':'Tồn + hàng đang về','Q':'Lượng đề xuất đặt','eta':'Ngày hàng về','partner_id':'Đối tác giả định',
    'status':'Trạng thái','expected_depletion_date':'Ngày cạn dự kiến','depletion_state':'Mức cảnh báo'}


try:
    config,cfg=settings(os.environ.get('SIGMA_M3_CONFIG','data/configs/product30.json'))
    namespace=hashlib.sha256(config.relative_to(ROOT).as_posix().encode()).hexdigest()[:12]
    state_dir=ROOT/'outputs/jobs'/('m3_'+namespace)
    state=json.loads((state_dir/'state.json').read_text()) if (state_dir/'state.json').is_file() else {}
    run_id=state.get('last_good_run',cfg['product_run'])
    folder=ROOT/'outputs'/run_id
    stamps=tuple((p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in folder.iterdir() if p.is_file())
    bundle=load_bundle(run_id,sha256(folder/'summary.json'),stamps)
    if bundle['summary']['aggregate_run']!=cfg['aggregate_run']:raise ValueError('Bộ tồn kho không khớp cấu hình dự báo.')
    source=ROOT/bundle['protocol']['config']['source']
    if sha256(source)!=bundle['summary']['source_sha256']:raise ValueError('Dữ liệu đã thay đổi; cần bộ dự báo và đối soát mới.')
except (OSError,ValueError,KeyError) as error:
    st.title('SIGMA · M3')
    st.error('Chưa thể mở bộ kết quả đã kiểm tra. '+str(error))
    st.info('Cần hoàn tất dự báo, mô phỏng tồn và đối soát trước khi dùng màn hình.')
    st.stop()

summary=bundle['summary'];rec=bundle['recommendations']
demo=bool(bundle['protocol']['config'].get('demo_source_generated',False))
st.sidebar.title('SIGMA · M3')
country=st.sidebar.selectbox('Quốc gia / điểm đến',['Tất cả']+sorted(rec.destination_country.unique().tolist()))
carriers=filtered(rec,country,'Tất cả').carrier.unique().tolist()
carrier=st.sidebar.selectbox('Nhà mạng',['Tất cả']+sorted(carriers))
view=filtered(rec,country,carrier)
ptype=st.sidebar.selectbox('Loại sản phẩm',['Tất cả']+sorted(view.product_type.unique().tolist()))
skus=filtered(view,'Tất cả','Tất cả',ptype=ptype).sku.unique().tolist()
sku=st.sidebar.selectbox('SKU',['Tất cả']+sorted(skus))
scenario_names={'base':'Cơ sở','one_day_drop':'Một ngày không bán','demand_drop':'Lượng bán còn 30% trong 7 ngày',
    'demand_surge':'Lượng bán gấp đôi trong 3 ngày','partial_receipt':'Đối tác chỉ giao 50%',
    'late_receipt':'Đối tác nhập trễ 3 ngày','no_receipt':'Không nhận được hàng',
    'sensitivity_cover_3':'Tồn đầu đủ 3 ngày','sensitivity_cover_14':'Tồn đầu đủ 14 ngày',
    'sensitivity_lead_1':'Lead time nhập 1 ngày','sensitivity_lead_7':'Lead time nhập 7 ngày',
    'sensitivity_safety_0.5':'Tồn an toàn ×0,5','sensitivity_safety_1.5':'Tồn an toàn ×1,5'}
scenario=st.sidebar.selectbox('Kịch bản tồn kho',rec.scenario_id.drop_duplicates().tolist(),format_func=lambda x:scenario_names.get(x,x))
st.sidebar.caption('Tồn, nhập hàng, đối tác và lead time đều là giả định mô phỏng.')
st.sidebar.button('Nạp lại kết quả đã kiểm',on_click=st.cache_data.clear)

st.title('Dự báo nhu cầu và theo dõi tồn SIM / gói data')
st.caption(f"Mốc dữ liệu: {summary['as_of_date']} · Dự báo {summary['forecast_window_days']} ngày · Chạy tại máy · Đơn vị: quantity")
st.info('Demo ba tuyến do phần mềm tự sinh; không chứng minh độ chính xác top10 của nguồn bài.' if demo else
        'Màn hình dùng snapshot lịch sử 2024–2025. Tồn kho là mô phỏng; khuyến nghị chưa được gửi thành đơn nhập thực.')
tabs=st.tabs(['Tổng quan','Dự báo 7 / 30 ngày','Tồn và đặt hàng','Cảnh báo','Lịch giao khách','Biến động bán','Cập nhật & nguồn'])

with tabs[0]:
    top=bundle['top'].loc[bundle['top'].window_days.eq(30)]
    cols=st.columns(2)+st.columns(2)
    cols[0].metric('Tuyến tổng 30 đạt ≤20%',f"{int(top.passes_20_pct.sum())}/{len(top)}")
    cols[1].metric('MAPE tổng 30 trung bình',f'{top.mape_positive_pct.mean():.2f}%')
    cols[2].metric('Đáp ứng bán · cơ sở',f"{summary['base_fill_rate']:.2%}")
    cols[3].metric('Sự kiện báo trước ≥7 ngày',f"{summary['early_event_rate']:.2%}")
    st.caption('MAPE là trung bình theo top10 train, trên cửa sổ đủ nhãn. Tỷ lệ cảnh báo lấy replay H14 riêng, giữ cả ca không được báo sớm trong mẫu số.')
    st.subheader('Luồng sản phẩm')
    st.write('Đơn hàng → dự báo tổng 30 → phân bổ ngày và SKU → sổ tồn theo giao dịch → lượng đặt / ngày cạn → cảnh báo và theo dõi sai số.')
    st.dataframe(top[ROUTE+['model','mape_positive_pct','mae','wape_pct','bias','coverage','passes_20_pct']].rename(columns=LABELS),hide_index=True,width='stretch')
    st.warning('Kết quả test là hồi cứu. Tổng 30 và tổng 7 được chấm riêng; chưa thay tiêu chí dự báo ngày R05 hoặc xác nhận mọi sự kiện đều báo trước 7 ngày.')

with tabs[1]:
    window=st.radio('Tổng lượng bán dự báo',[30,7],format_func=lambda x:f'{x} ngày',horizontal=True)
    if window==7:
        st.caption('Đây là đối chứng 7 ngày trong thử nghiệm mới chạy cùng tổng30. Bộ final M2 của Khang ngày11/10 được giữ riêng, không bị thay thế bằng bảng này.')
    forecast=filtered(bundle['forecasts'],country,carrier)
    forecast=forecast.loc[forecast.window_days.eq(window)]
    origins=sorted(forecast.as_of_date.unique())
    origin=st.selectbox('Ngày chốt dự báo',origins,index=len(origins)-1,format_func=lambda x:pd.Timestamp(x).strftime('%d/%m/%Y'))
    part=forecast.loc[forecast.as_of_date.eq(origin)]
    totals=part.groupby(ROUTE,as_index=False).forecast_qty.sum()
    st.dataframe(totals.rename(columns={'forecast_qty':f'forecast_quantity_{window}d'}),hide_index=True,width='stretch')
    chart=part.groupby('target_date').forecast_qty.sum().rename('Phân bổ từ tổng')
    actual=filtered(bundle['daily'],country,carrier).groupby('date').sales_qty.sum(min_count=1)
    plot=pd.concat([chart,actual.reindex(chart.index).rename('Số bán đã quan sát')],axis=1)
    st.line_chart(plot)
    st.caption('Đường theo ngày là phân bổ từ mô hình tổng, không phải các dự báo ngày độc lập. Ngày chưa có actual để trống.')
    st.dataframe(filtered(bundle['top'],country,carrier).loc[lambda x:x.window_days.eq(window)],hide_index=True,width='stretch')
    download('Tải dự báo đang xem',part.drop(columns='actual_qty',errors='ignore'),'sigma_forecast.csv')

with tabs[2]:
    part=filtered(rec,country,carrier,sku,ptype)
    part=part.loc[part.scenario_id.eq(scenario)]
    cols=st.columns(2)+st.columns(1)
    cols[0].metric('Tồn hiện có · mô phỏng',f'{part.on_hand.sum():,.0f}')
    cols[1].metric('Mặt hàng dưới điểm đặt lại',int(part.needs_replenishment.sum()))
    cols[2].metric('Lượng đề xuất đặt',f'{part.Q.sum():,.0f}')
    st.caption('Cảnh báo khi tồn hiện có < ROP. Hàng đang về chỉ dùng tính lượng đặt Q; không cộng vào tồn trước ETA. Q trong bảng là quyết định của mô phỏng, chưa gửi đơn nhập thực.')
    columns=ITEM+['partner_id','on_hand','SS','ROP','S','IP','Q','eta','status','expected_depletion_date','depletion_state']
    st.dataframe(part[columns].rename(columns=LABELS),hide_index=True,width='stretch')
    st.subheader('Phân bổ nhu cầu theo mặt hàng')
    detail=filtered(bundle['item_forecast'],country,carrier,sku,ptype)
    st.line_chart(detail.groupby('target_date').forecast_qty.sum().rename('Quantity phân bổ'))
    st.dataframe(bundle['metrics'].loc[lambda x:x.scenario_id.eq(scenario)],hide_index=True,width='stretch')
    download('Tải khuyến nghị đang xem',part,'sigma_stock_recommendations.csv')

with tabs[3]:
    alerts=filtered(bundle['alerts'],country,carrier,sku,ptype)
    tp,fp,fn=int(alerts.tp.sum()),int(alerts.fp.sum()),int(alerts.fn.sum())
    cols=st.columns(2)+st.columns(2)
    cols[0].metric('Sự kiện cạn thực trong replay',tp+fn)
    cols[1].metric('Báo trước ≥7 ngày',int(alerts.reported_early.sum()))
    cols[2].metric('Báo muộn',int(alerts.late.sum()))
    cols[3].metric('Bỏ sót sự kiện',fn)
    st.caption('Replay không đặt hàng mới, chấm sự kiện cạn đầu tiên trong các đợt H14 không chồng lấn. Chính sách có nhập hàng được đánh giá riêng ở tab Tồn.')
    active=filtered(rec,country,carrier,sku,ptype).loc[lambda x:x.scenario_id.eq(scenario)]
    active=active.loc[active.depletion_state.ne('no_depletion_within_horizon')]
    st.subheader('Cảnh báo tại mốc mới nhất · nhìn trước 30 ngày')
    st.dataframe(active[ITEM+['on_hand','expected_depletion_date','depletion_days','depletion_state','Q','eta']],hide_index=True,width='stretch')
    st.caption('urgent: cạn trong 1–6 ngày; early: từ 7 ngày; already_empty: đã hết tại mốc hiện tại. Không thấy cạn trong 30 ngày không chứng minh sẽ không bao giờ cạn.')
    st.subheader('Đối chiếu cảnh báo và diễn biến bán đã biết')
    st.dataframe(alerts.drop(columns='event_id'),hide_index=True,width='stretch')
    download('Tải bảng cảnh báo',alerts.drop(columns='event_id'),'sigma_alerts.csv')

with tabs[4]:
    part=filtered(bundle['delivery'],country,carrier)
    st.write('Khách đặt D → lịch giao D+7 ngày lịch, gồm cuối tuần. Thời gian này được giữ riêng với lead time nhập kho.')
    st.line_chart(part.groupby('delivery_date')[['known_commitment_qty','forecast_from_future_orders_qty']].sum())
    st.caption('Bảy ngày đầu từ đơn đã đặt; ngày 8–37 từ dự báo đơn tương lai. Actual giao chưa được cung cấp. Tồn đã trừ khi đáp ứng đơn, không trừ lần hai lúc giao khách.')
    st.dataframe(part,hide_index=True,width='stretch')

with tabs[5]:
    part=filtered(bundle['signals'],country,carrier)
    totals=part.groupby('date')[['sales_qty','gross_revenue_vnd']].sum(min_count=1)
    st.subheader('Số bán quan sát');st.line_chart(totals.sales_qty)
    st.subheader('Doanh thu quan sát · VND');st.line_chart(totals.gross_revenue_vnd)
    signal=part.loc[part.quantity_drop_observed|part.quantity_surge_observed|part.revenue_drop_observed]
    st.dataframe(signal[['date']+ROUTE+['sales_qty','gross_revenue_vnd','quantity_change_fraction','revenue_change_fraction']],hide_index=True,width='stretch')
    st.caption('Phát hiện sau chốt ngày, đối chiếu 28 ngày trước. Doanh thu giảm có thể do giá; không tự coi là giảm quantity hoặc sửa nhãn huấn luyện. Các chỉ báo này chưa được dùng để đoán trước cú sốc.')

with tabs[6]:
    last=json.loads((state_dir/'last_attempt.json').read_text()) if (state_dir/'last_attempt.json').is_file() else {'status':'not_run'}
    status_names={'complete':'Đã cập nhật và đối soát','adopted_existing':'Đã nhận bộ kết quả có sẵn đã đối soát',
        'skipped_unchanged':'Đầu vào không đổi','skipped_running':'Đang có lượt cập nhật khác',
        'failed':'Cập nhật lỗi; giữ bộ kết quả tốt gần nhất','not_run':'Chưa chạy job'}
    st.write('Trạng thái cập nhật gần nhất:',status_names.get(last.get('status'),last.get('status')))
    if last.get('error_category')=='SourceChangedError':
        st.warning('Dữ liệu nguồn đã đổi. Cần dự báo và đối soát snapshot mới trước khi tính tồn.')
    st.write('Bộ kết quả đang dùng:',run_id)
    st.write('Mốc dữ liệu:',summary['as_of_date'])
    st.write('Cập nhật giữ kết quả tốt gần nhất khi lỗi; đầu vào không đổi thì bỏ qua. Dữ liệu nguồn đổi cần bộ dự báo mới đã đối soát trước khi tính tồn.')
    st.json({'stock':'simulated','customer_delivery_days':7,'forecast_window_days':30,
        'aggregate_run':summary['aggregate_run'],'source_sha256':summary['source_sha256'],
        'test_independent':False,'daily_R05_acceptance_replaced':False})
