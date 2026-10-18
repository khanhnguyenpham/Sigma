"""Mentor-facing M3 walkthrough, backed by the same verified local artifacts."""
from html import escape
import json

import pandas as pd
import streamlit as st

from src.common import ROOT, ROUTE, ITEM
from sigma.analysis.alert_diagnostics import explain_events
from sigma.ui import product30_charts as charts
from sigma.ui.product30_support import (number, filter_frame, ranked_recommendations,
    demand_chart_data, complete_actual, timeline_metrics, scenario_comparison,
    recommendation_action, item_parameters)

SCENARIOS={'base':'Cơ sở · nhận đủ, đúng hạn','one_day_drop':'Một ngày không bán được',
    'demand_drop':'Lượng bán còn 30% trong 7 ngày','demand_surge':'Lượng bán gấp đôi trong 3 ngày',
    'partial_receipt':'Đối tác chỉ giao 50%','late_receipt':'Đối tác giao trễ 3 ngày',
    'no_receipt':'Không nhận được hàng','sensitivity_cover_3':'Tồn đầu đủ 3 ngày',
    'sensitivity_cover_14':'Tồn đầu đủ 14 ngày','sensitivity_lead_1':'Lead time nhập 1 ngày',
    'sensitivity_lead_7':'Lead time nhập 7 ngày','sensitivity_safety_0.5':'Tồn an toàn ×0,5',
    'sensitivity_safety_1.5':'Tồn an toàn ×1,5'}
STATE={'already_empty':'Đã hết hàng','urgent':'Có thể cạn trong 1–6 ngày',
    'early':'Dự kiến cạn từ ngày 7','no_depletion_within_horizon':'Chưa thấy cạn trong 30 ngày'}
TYPES={'eSIM':'eSIM','physical_SIM':'SIM vật lý'}
LABELS={'destination_country':'Quốc gia','carrier':'Nhà mạng','sku':'SKU','product_type':'Loại',
    'on_hand':'Tồn hiện có','SS':'Tồn an toàn','ROP':'Điểm đặt lại','S':'Mức tồn mục tiêu',
    'IP':'Tồn + hàng đang về','Q':'Đề xuất đặt','eta':'Ngày lô mới về',
    'expected_depletion_date':'Ngày cạn dự kiến','mape_positive_pct':'MAPE (%)',
    'mae':'MAE (đơn vị)','wape_pct':'WAPE (%)','bias':'Bias (đơn vị)','coverage':'Độ phủ',
    'model':'Mô hình','passes_20_pct':'Đạt ≤20%','partner_id':'Đối tác giả định'}


def cards(items):
    html='<div class="sigma-kpis">'
    for label,value,foot,tone in items:
        html+=f'<div class="sigma-kpi {escape(tone)}"><div class="sigma-kpi-label">{escape(label)}</div><div class="sigma-kpi-value">{escape(str(value))}</div><div class="sigma-kpi-foot">{escape(foot)}</div></div>'
    st.markdown(html+'</div>',unsafe_allow_html=True)


def section(kicker,title,caption=None):
    st.markdown(f'<div class="sigma-section">{escape(kicker)}</div>',unsafe_allow_html=True)
    st.subheader(title)
    if caption:st.caption(caption)


def export(label,frame,filename):
    st.download_button(label,frame.to_csv(index=False).encode('utf-8-sig'),file_name=filename,mime='text/csv')


def pick(label,options,key,default=0,**kwargs):
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    return st.selectbox(label,options,index=default,key=key,**kwargs)


def reset_filters():
    for key in ['m3_country','m3_carrier','m3_scenario','m3_type','m3_sku','m3_focus']:
        st.session_state.pop(key,None)


def family(name):
    if 'lgbm' in name:return 'LightGBM'
    if 'prophet' in name:return 'Prophet'
    if 'sarima' in name:return 'SARIMA'
    return 'Baseline'


def day(value):
    return pd.Timestamp(value).strftime('%d/%m/%Y') if pd.notna(value) else '—'


def compact_stock(frame):
    result=frame.copy()
    result['Tuyến']=result.destination_country+' · '+result.carrier
    result['Loại']=result.product_type.map(TYPES).fillna(result.product_type)
    result['Ưu tiên']=result.depletion_state.map(STATE)
    result['Ngày cạn']=result.expected_depletion_date.map(day)
    return result[['Tuyến','sku','Loại','on_hand','ROP','Q','Ngày cạn','Ưu tiên']].rename(columns=LABELS)


def queue(frame,limit=4):
    items=ranked_recommendations(frame)
    items=items.loc[items.needs_replenishment | items.depletion_state.isin(['already_empty','urgent'])]
    if items.empty:
        st.success('Không có mặt hàng cần ưu tiên trong phạm vi đang lọc.')
    for r in items.head(limit).itertuples():
        badge='Hết hàng' if r.on_hand<=0 else 'Sắp cạn' if r.depletion_state=='urgent' else 'Dưới điểm đặt lại'
        tone='danger' if r.on_hand<=0 else ''
        st.markdown(f'<div class="sigma-queue"><div class="sigma-queue-top"><span>{escape(r.carrier)} · {escape(r.sku)}</span><span class="sigma-badge {tone}">{badge}</span></div><div class="sigma-queue-sub">{escape(r.destination_country)} · {escape(TYPES.get(r.product_type,r.product_type))}<br>Tồn {number(r.on_hand)} / điểm đặt lại {number(r.ROP)} · đề xuất thêm {number(r.Q)}</div></div>',unsafe_allow_html=True)


def overview(bundle,context,stock):
    country,carrier,sku,ptype,scenario=context
    summary=bundle['summary'];origin=pd.Timestamp(summary['as_of_date'])
    selected=filter_frame(bundle['forecasts'],country,carrier)
    selected=selected.loc[selected.window_days.eq(30)&selected.as_of_date.eq(origin)]
    top=bundle['top'].loc[bundle['top'].window_days.eq(30)]
    urgent=stock.depletion_state.isin(['already_empty','urgent']).sum()
    future_period=f'{day(origin+pd.Timedelta(days=1))}–{day(origin+pd.Timedelta(days=30))}'
    section('01 / Bức tranh chung','Dự báo để quyết định bổ sung hàng',
        f"Tuyến: {country} / {carrier} · Kho: {SCENARIOS[scenario]}. Lượng bán theo tuyến; tồn và lượng đặt theo bộ lọc sản phẩm.")
    cards([('Dự kiến bán trong 30 ngày',number(selected.forecast_qty.sum(),1),future_period+' · đơn vị sản phẩm','teal'),
        ('Tuyến đạt MAPE ≤20%',f'{int(top.passes_20_pct.sum())}/{len(top)}',f'Top {len(top)} train · MAPE TB {number(top.mape_positive_pct.mean(),2)}%','amber' if not top.passes_20_pct.all() else 'teal'),
        ('Lượng đề xuất bổ sung',number(stock.Q.sum()),f'{int(stock.Q.gt(0).sum())} mặt hàng có đề xuất đặt','teal'),
        ('Mặt hàng cần ưu tiên',number(urgent),'Đã hết hoặc dự kiến cạn trong 1–6 ngày','amber')])
    left,right=st.columns([1.6,1],gap='large')
    with left:
        st.subheader('Nhu cầu đã quan sát và kỳ dự báo')
        daily=filter_frame(bundle['daily'],country,carrier)
        st.altair_chart(charts.demand(demand_chart_data(daily,selected,origin),origin),width='stretch')
        st.caption(f'Vạch dọc là ngày chốt {day(origin)}. Đường nét đứt là phân bổ từ tổng 30 ngày; chưa có actual cho kỳ tiếp theo.')
    with right:
        st.subheader('Danh sách cần xem xét')
        queue(stock,3)
        st.caption('Xem từng mặt hàng và xuất phiếu đề xuất tại tab Kho hàng.')
    st.markdown('<div class="sigma-flow"><div>1. Dự báo nhu cầu<span>Tổng 30 ngày theo quốc gia–nhà mạng, có sai số kiểm chứng.</span></div><div>2. Tính mức bổ sung<span>Phân bổ SKU, so tồn với điểm đặt lại và lượng đang về.</span></div><div>3. Theo dõi rủi ro<span>Ngày cạn dự kiến, biến động bán và kịch bản đối tác.</span></div></div>',unsafe_allow_html=True)
    note=('Dữ liệu demo do phần mềm tự sinh, tồn kho mô phỏng; kết quả không chứng minh chất lượng nguồn bài.' if bundle['demo'] else
        f"Bản trình diễn dùng dữ liệu lịch sử 2024–2025 và tồn kho mô phỏng. Tổng 30 đạt {int(top.passes_20_pct.sum())}/{len(top)} tuyến theo ngưỡng 20%.")
    st.markdown(f'<div class="sigma-note">{escape(note)} Tiêu chí dự báo ngày và cảnh báo sớm chưa được nghiệm thu toàn bộ. Chi tiết ở tab Kiểm chứng.</div>',unsafe_allow_html=True)


def forecasts(bundle,context):
    country,carrier,*_=context
    section('02 / Nhu cầu','Dự báo tổng 30 ngày và đối chứng 7 ngày',
        'Chọn một mốc quá khứ để so với số bán đã có; chọn 31/12/2025 để xem kỳ chưa có actual.')
    a,b=st.columns([1,2])
    with a:window=st.radio('Cửa sổ dự báo',[30,7],format_func=lambda x:f'Tổng {x} ngày',horizontal=True,key='m3_window')
    frame=filter_frame(bundle['forecasts'],country,carrier)
    frame=frame.loc[frame.window_days.eq(window)]
    origins=sorted(frame.as_of_date.unique())
    with b:origin=pick('Ngày chốt dự báo',origins,'m3_origin',len(origins)-1,format_func=day)
    part=frame.loc[frame.as_of_date.eq(origin)]
    daily=filter_frame(bundle['daily'],country,carrier)
    start=pd.Timestamp(origin)+pd.Timedelta(days=1);end=start+pd.Timedelta(days=window-1)
    actual=complete_actual(daily,start,end)
    value=float(part.forecast_qty.sum())
    cols=st.columns(3)
    cols[0].metric('Tổng lượng dự báo',number(value,1))
    cols[1].metric('Tổng lượng đã quan sát',number(actual,0) if actual is not None else 'Chưa có')
    delta=(value-actual)/actual*100 if actual is not None and actual>0 else None
    cols[2].metric('Chênh lệch tổng',number(delta,2)+'%' if delta is not None else '—')
    # Target-period actual is never padded to zero when the horizon is unknown.
    allocated=part.groupby('target_date',as_index=False).forecast_qty.sum().rename(columns={'target_date':'date','forecast_qty':'quantity'})
    allocated['series']='Phân bổ từ dự báo tổng'
    observed=daily.loc[daily.date.between(start,end)].groupby('date',as_index=False).sales_qty.sum(min_count=1).rename(columns={'sales_qty':'quantity'})
    observed['series']='Số bán đã quan sát'
    st.altair_chart(charts.demand(pd.concat([allocated,observed],ignore_index=True),origin,height=260),width='stretch')
    st.caption(f'{day(start)}–{day(end)} · Chênh lệch tổng chỉ mô tả cửa sổ đang xem, không thay MAPE theo từng tuyến. Đường ngày là phân bổ; dữ liệu chưa có để trống.')
    top=filter_frame(bundle['top'],country,carrier).loc[lambda x:x.window_days.eq(window)]
    if len(top):
        st.subheader('Sai số trên các tuyến chủ lực')
        st.altair_chart(charts.route_error(top,height=max(110,len(top)*29)),width='stretch')
    st.caption(f'Test hồi cứu quý IV/2025 · {window} ngày liên tiếp · ngưỡng 20% cho từng tuyến. Hai cửa sổ có mẫu số khác nhau; không dùng chênh lệch MAPE để kết luận dự báo ngày tốt hơn.')
    with st.expander('So sánh tổng 7 / tổng 30 và xem chỉ số chi tiết'):
        comparison=bundle['top'].groupby('window_days').agg(tuyen_dat=('passes_20_pct','sum'),so_tuyen=('carrier','size'),MAPE=('mape_positive_pct','mean'),coverage=('coverage','min')).reset_index()
        st.dataframe(comparison.rename(columns={'window_days':'Số ngày','tuyen_dat':'Tuyến đạt','so_tuyen':'Tổng tuyến','MAPE':'MAPE TB (%)','coverage':'Độ phủ'}),hide_index=True,width='stretch')
        st.dataframe(top[ROUTE+['model','mape_positive_pct','mae','wape_pct','bias','coverage']].rename(columns=LABELS),hide_index=True,width='stretch')
        st.caption('Đối chứng 7 ngày thuộc pool mới. Bộ M2 final của Khang được giữ riêng; không trộn kết quả hai bộ.')
    export('Xuất dự báo đang xem',part.drop(columns='actual_qty',errors='ignore'),'sigma_du_bao.csv')


def inventory(bundle,context,stock):
    section('03 / Quyết định','Mặt hàng nào cần bổ sung?',
        'Tồn giả định sau chốt ngày 31/12/2025. Hàng đang về chưa được cộng vào tồn hiện có.')
    cards([('Tồn hiện có',number(stock.on_hand.sum()),'Đơn vị sản phẩm · mô phỏng','teal'),
        ('Dưới điểm đặt lại',number(stock.needs_replenishment.sum()),f'Trong {len(stock)} mặt hàng đang lọc','amber'),
        ('Đề xuất đặt thêm',number(stock.Q.sum()),'Đã tính lượng đặt chưa nhận','teal'),
        ('Mặt hàng đã hết',number(stock.on_hand.eq(0).sum()),'Ưu tiên kiểm tra nguồn bổ sung','amber')])
    ranked=ranked_recommendations(stock)
    st.dataframe(compact_stock(ranked.head(15)),hide_index=True,width='stretch')
    st.caption('Hiển thị 15 mặt hàng ưu tiên đầu. Thứ tự chỉ phục vụ đọc; lượng đặt giữ nguyên từ policy đã đối soát.')
    choices=list(ranked[ITEM].itertuples(index=False,name=None))
    if choices:
        key=pick('Mặt hàng minh họa',choices,'m3_focus',format_func=lambda x:f'{x[1]} · {x[2]} · {TYPES.get(x[3],x[3])} · {x[0]}')
        row=ranked.loc[(ranked[ITEM]==pd.Series(key,index=ITEM)).all(axis=1)].iloc[0]
        params=item_parameters(bundle['scenario_configs'],row)
        left,right=st.columns([1,1.25],gap='large')
        with left:
            st.subheader(recommendation_action(row))
            st.write(f"**{row.carrier} / {row.sku}** · {TYPES.get(row.product_type,row.product_type)}")
            st.write(f"Tồn hiện có **{number(row.on_hand)}**; điểm đặt lại **{number(row.ROP)}**; đã đặt chưa nhận **{number(row.IP-row.on_hand)}**.")
            st.write(f"Đề xuất bổ sung **{number(row.Q)} đơn vị**; ngày lô mới về **{day(row.eta)}**.")
            st.caption(f"Tham số giả định của {row.partner_id}: lead time {params['lead_time_days']} ngày, kỳ review {params['review_days']} ngày, safety {params['safety_days']} ngày, MOQ {params['moq']}. Giao khách D+7 là bước khác.")
        with right:
            detail=bundle['item_forecast'].loc[(bundle['item_forecast'][ITEM]==pd.Series(key,index=ITEM)).all(axis=1)]
            st.subheader('Nhu cầu phân bổ cho mặt hàng')
            chart=detail[['target_date','forecast_qty']].rename(columns={'target_date':'Ngày','forecast_qty':'Lượng dự báo'})
            st.bar_chart(chart.set_index('Ngày'),color=charts.TEAL,height=210)
        with st.expander('Giải thích công thức và các ngưỡng của mặt hàng'):
            st.write(f"Tồn an toàn SS = **{number(row.SS)}** · ROP = **{number(row.ROP)}** · mức mục tiêu S = **{number(row.S)}** · IP = **{number(row.IP)}**.")
            st.code('Cần bổ sung khi tồn hiện có < ROP\nQ = ceil(max(0, S − IP)); áp MOQ khi Q > 0','text')
            st.caption('Tồn thấp nhưng Q=0 có thể do hàng đã đặt đủ. ETA chỉ làm tăng tồn khi lô thực sự đến trong mô phỏng. Đây là phiếu đề xuất, chưa gửi đơn nhập thực.')
    with st.expander('Toàn bộ mặt hàng và phiếu đề xuất nhập'):
        st.dataframe(compact_stock(ranked),hide_index=True,width='stretch')
        export('Xuất phiếu đề xuất nhập CSV',stock.loc[stock.Q.gt(0),ITEM+['partner_id','as_of_date','on_hand','SS','ROP','S','IP','Q','eta','scenario_id','is_simulated']], 'sigma_phieu_de_xuat_nhap.csv')


def situations(bundle,context):
    country,carrier,_,_,scenario=context
    section('04 / Sức chịu đựng','Nếu tình huống bất thường xảy ra thì sao?',
        'Chọn kịch bản ở đầu trang. Kết quả dưới đây tính từ sổ mô phỏng 01/10–31/12/2025, theo tuyến đang lọc; không lọc theo SKU.')
    timeline=filter_frame(bundle['timeline'],country,carrier)
    metrics=scenario_comparison(timeline_metrics(timeline))
    row=metrics.loc[metrics.scenario_id.eq(scenario)].iloc[0]
    base=metrics.loc[metrics.scenario_id.eq('base')].iloc[0]
    cols=st.columns(3)
    cols[0].metric('Tỷ lệ đáp ứng',number(row.fill_rate*100,2)+'%',delta=number(row.fill_change_pp,2)+' điểm % so cơ sở',delta_color='normal')
    cols[1].metric('Lượng chưa đáp ứng',number(row.shortage),delta=number(row.shortage_change)+' đơn vị so cơ sở',delta_color='inverse')
    cols[2].metric('Tồn cuối ngày bình quân',number(row.mean_closing_on_hand,1))
    spec=next(x['scenario'] for x in bundle['scenario_configs'] if x['scenario']['name']==scenario)
    st.write(f'**{SCENARIOS[scenario]}**')
    if scenario.startswith('demand_') or scenario=='one_day_drop':
        st.caption(f"Cú sốc giả định bắt đầu {day(spec['demand_start'])}, kéo dài {spec['demand_days']} ngày, lượng yêu cầu ×{spec['demand_multiplier']}. Không coi cú sốc này là thông tin mô hình biết trước.")
    elif scenario in ['partial_receipt','late_receipt','no_receipt']:
        st.caption(f"Lượng nhận = {number(spec['receipt_fraction']*100)}% kế hoạch; trễ thêm {spec['receipt_delay_days']} ngày. Các giả định khác giữ cơ sở.")
    elif scenario!='base':st.caption('Kịch bản độ nhạy thay một tham số tồn/nhập; bộ dự báo không đổi.')
    a,b=st.columns(2,gap='large')
    with a:
        st.subheader('Yêu cầu bán và phần đáp ứng')
        st.altair_chart(charts.policy_service(timeline,scenario),width='stretch')
    with b:
        st.subheader('Diễn biến tồn so với cơ sở')
        st.altair_chart(charts.policy_stock(timeline,scenario),width='stretch')
    st.subheader('So sánh toàn bộ kịch bản')
    st.altair_chart(charts.scenarios(metrics,SCENARIOS,scenario),width='stretch')
    st.caption('Tồn cao có thể cải thiện đáp ứng nhưng cũng tăng lượng lưu kho. Chưa có chi phí lưu kho/thiếu hàng được xác nhận nên chưa kết luận tối ưu chi phí.')
    with st.expander('Giám sát biến động bán và doanh thu đã quan sát'):
        signals=filter_frame(bundle['signals'],country,carrier)
        history=signals.groupby('date')[['sales_qty','gross_revenue_vnd']].sum(min_count=1)
        a,b=st.columns(2)
        with a:st.line_chart(history.sales_qty.rename('Lượng bán'),height=210)
        with b:st.line_chart(history.gross_revenue_vnd.rename('Doanh thu · VND'),height=210)
        st.caption('Chỉ báo phát hiện sau chốt ngày so với 28 ngày trước. Doanh thu giảm và quantity giảm được kiểm riêng; số tiền thiếu/lỗi không chuyển thành 0. Không tuyên bố dự báo trước cú sốc.')


def alerts(bundle,context,stock):
    country,carrier,sku,ptype,_=context
    section('05 / Rủi ro','Cần xử lý trước khi mặt hàng cạn',
        'Danh sách tại mốc 31/12/2025 nhìn trước 30 ngày; kết quả đánh giá cảnh báo lịch sử được trình bày riêng bên dưới.')
    queue(stock,4)
    with st.expander('Toàn bộ cảnh báo tại mốc mới nhất'):
        active=stock.loc[stock.depletion_state.ne('no_depletion_within_horizon')]
        st.dataframe(compact_stock(ranked_recommendations(active)),hide_index=True,width='stretch')
    replay=filter_frame(bundle['alerts'],country,carrier,sku,ptype)
    explanation,stats=explain_events(replay)
    st.subheader('Kiểm chứng khả năng báo trước 7 ngày')
    total=stats['actual_events'];early=stats['detected_with_7day_opportunity']
    cards([('Sự kiện cạn trong replay',number(total),'Sổ không đặt thêm hàng · H14','teal'),
        ('Được báo trước ≥7 ngày',f'{number(early)}/{number(total)}',number(early/total*100,2)+'%' if total else 'Không có sự kiện','amber'),
        ('Cạn trước ngày thứ 7',number(stats['events_before_day7']),'Không đủ 7 ngày từ origin của đợt','amber'),
        ('Có cơ hội nhưng bỏ sót',number(stats['missed_with_7day_opportunity']),'Phần cần tiếp tục cải thiện','amber')])
    st.warning('Chưa bảo đảm mọi sự kiện đều được báo trước ít nhất 7 ngày. Tỷ lệ chính giữ cả ca cạn sớm trong mẫu số; không dùng tỷ lệ điều kiện để thay tiêu chí.')
    with st.expander('Cách chấm, ca bỏ sót và bảng đối chiếu'):
        st.write(f"Có {number(stats['events_with_7day_opportunity'])} ca cạn từ ngày 7 trở đi; phát hiện {number(early)}, bỏ sót {number(stats['missed_with_7day_opportunity'])}. Các ca cạn trước ngày 7 vẫn thuộc mẫu số chính.")
        st.caption('Replay theo đợt H14 không chồng lấn, mỗi mặt hàng/đợt chấm sự kiện cạn đầu tiên. Sổ có đặt hàng đánh giá riêng; hàng đặt giúp ngăn cạn không bị gọi là cảnh báo sai.')
        st.dataframe(explanation,hide_index=True,width='stretch')
        export('Xuất đối chiếu cảnh báo',explanation,'sigma_doi_chieu_canh_bao.csv')


def customer_delivery(bundle,context):
    country,carrier,*_=context
    section('06 / Khách hàng','Đặt ngày D, lịch giao ngày D+7',
        'Bảy ngày lịch, gồm cuối tuần, theo thông tin mentor do người dùng thuật lại. Giữ riêng với lead time nhập kho.')
    frame=filter_frame(bundle['delivery'],country,carrier)
    known=frame.known_commitment_qty.sum();future=frame.forecast_from_future_orders_qty.sum()
    cols=st.columns(3)
    cols[0].metric('Đơn đã đặt · lịch 7 ngày đầu',number(known))
    cols[1].metric('Đơn tương lai · lịch ngày 8–37',number(future,1))
    cols[2].metric('Actual giao', 'Chưa cung cấp')
    st.altair_chart(charts.delivery(frame),width='stretch')
    st.caption('Đơn vị là số sản phẩm, không phải số đơn. Phần tương lai đến từ phân bổ dự báo tổng 30. Tồn đã trừ lúc đáp ứng đơn, không trừ lần hai khi giao khách.')
    with st.expander('Xem và xuất lịch giao tổng hợp theo tuyến'):
        st.dataframe(frame,hide_index=True,width='stretch')
        export('Xuất lịch giao khách',frame,'sigma_lich_giao_khach.csv')


def evidence(bundle,run_id,state_dir):
    section('07 / Kiểm chứng','Phần đã làm, phần còn thiếu và nguồn số liệu',
        'Các kết quả dưới đây là hồi cứu. Tồn kho/nhập hàng/đối tác là giả định; chưa nhận nghiệm thu toàn bộ bài.')
    top=bundle['top'].loc[bundle['top'].window_days.eq(30)]
    failed=top.loc[~top.passes_20_pct]
    limits='Nguồn demo tự sinh, không chứng minh chất lượng nguồn bài' if bundle['demo'] else '; '.join(
        f'{r.carrier}: {number(r.mape_positive_pct,2)}%' for r in failed.itertuples()) or 'Đạt ngưỡng trên test hồi cứu; chưa chứng minh holdout độc lập'
    st.dataframe(pd.DataFrame([
        ['Tổng lượng bán 30 ngày',f'{int(top.passes_20_pct.sum())}/{len(top)} tuyến ≤20%',limits],
        ['Quy tắc sổ tồn và đặt hàng','Đã triển khai và đối soát','Tồn giả định; không chứng minh tồn doanh nghiệp'],
        ['Cảnh báo trước ít nhất 7 ngày',f"{number(bundle['summary']['early_event_rate']*100,2)}% sự kiện",'Chưa bảo đảm mọi trường hợp'],
        ['Dự báo từng ngày theo R05','Còn mở','Tổng 30 không tự thay tiêu chí gốc'],
    ],columns=['Hạng mục','Kết quả hiện tại','Giới hạn']),hide_index=True,width='stretch')
    with st.expander('Dữ liệu đầu vào và phương pháp'):
        receipt=bundle['verification'][bundle['summary']['aggregate_run']]
        st.write(f"Nguồn bài đã audit: **{number(receipt['raw_rows'])} dòng**, **{number(receipt['sales_quantity'])} quantity hợp lệ theo định nghĩa cơ sở**. Top tuyến xếp theo quantity train.")
        st.write('Train 01/01/2024–30/06/2025 → validation quý III/2025 chọn mô hình → test quý IV/2025 sau khóa lựa chọn. Label tổng là D+1…D+30 liên tiếp, không phải tháng lịch.')
        selected=bundle['selections'].loc[lambda x:x.window_days.eq(30)].copy()
        selected['Mô hình']=selected.model.map(family)
        st.dataframe(selected[ROUTE+['Mô hình','validation_mape_positive_pct']].rename(columns={**LABELS,'validation_mape_positive_pct':'MAPE validation (%)'}),hide_index=True,width='stretch')
        st.caption('Bộ lọc success/ngày đặt UTC là A08 đề xuất, chưa phải quy tắc kế toán mentor xác nhận. Không dùng activation loại sale hợp lệ. Test đã xem nên không gọi là holdout độc lập.')
    with st.expander('Cập nhật định kỳ và truy vết kỹ thuật'):
        path=state_dir/'last_attempt.json'
        last=json.loads(path.read_text()) if path.is_file() else {'status':'not_run'}
        names={'complete':'Đã cập nhật','adopted_existing':'Đã nhận bộ đã đối soát','skipped_unchanged':'Đầu vào không đổi',
            'skipped_running':'Đã có lượt khác chạy','failed':'Lỗi cập nhật · giữ last-good','not_run':'Chưa chạy job'}
        st.write('Cập nhật gần nhất:',names.get(last.get('status'),last.get('status')))
        if bundle.get('hosted_release'):
            st.write('Bản triển khai đọc bộ kết quả đã kiểm tra; không có job huấn luyện hoặc đồng bộ nguồn tự động trên host này. Cập nhật bằng một release mới đã đối soát. Job local 07:00 không chạy trên host.')
        else:
            st.write('Job local 07:00 giờ Việt Nam. Nguồn đổi cần bộ dự báo mới đã đối soát; không tự kéo dài split hoặc train khi mở dashboard.')
        st.code(f"Forecast: {bundle['summary']['aggregate_run']}\nM3: {run_id}\nSource SHA256: {bundle['summary']['source_sha256']}",'text')
        st.caption('Hai thử nghiệm hiệu chỉnh/học ngắn giữ riêng vì không cải thiện ổn định. Bộ final M2 của Khang cũng được giữ riêng, không trộn với pool 7/30 mới.')
    st.info('Khi báo cáo: trình bày đây là sản phẩm M3 dùng snapshot lịch sử và tồn mô phỏng; giải thích các phần còn thiếu thay vì nhận đã đạt 100%.')


def render(bundle,cfg,state_dir,run_id):
    summary=bundle['summary'];rec=bundle['recommendations']
    bundle['demo']=bool(bundle['protocol']['config'].get('demo_source_generated',False))
    st.markdown(f'<div class="sigma-head"><div><div class="sigma-brand">SIGMA / DEMAND & INVENTORY</div><div class="sigma-title">Điều phối nhu cầu & tồn kho</div><div class="sigma-subtitle">Dự báo SIM / gói data · đề xuất bổ sung theo từng mặt hàng</div></div><div class="sigma-stamp"><span class="sigma-tag">M3 · TỒN MÔ PHỎNG</span><br>Dữ liệu đến {day(summary["as_of_date"])}<br>Kỳ dự báo: 30 ngày tiếp theo</div></div>',unsafe_allow_html=True)
    if bundle['demo']:st.info('Dữ liệu demo do phần mềm tự sinh; không dùng điểm demo chứng minh chất lượng nguồn bài.')
    cols=st.columns([1,1,1.4,.7],gap='small')
    with cols[0]:country=pick('Quốc gia / điểm đến',['Tất cả']+sorted(rec.destination_country.unique()),'m3_country')
    with cols[1]:carrier=pick('Nhà mạng',['Tất cả']+sorted(filter_frame(rec,country).carrier.unique()),'m3_carrier')
    with cols[2]:scenario=pick('Tình huống mô phỏng',list(SCENARIOS),'m3_scenario',format_func=lambda x:SCENARIOS[x])
    view=filter_frame(rec,country,carrier)
    with cols[3]:
        st.caption('Sản phẩm')
        with st.popover('Lọc SKU'):
            ptype=pick('Loại sản phẩm',['Tất cả']+sorted(view.product_type.unique()),'m3_type',format_func=lambda x:TYPES.get(x,x))
            sku=pick('SKU',['Tất cả']+sorted(filter_frame(view,ptype=ptype).sku.unique()),'m3_sku')
            st.caption('Bộ lọc sản phẩm dùng cho kho và cảnh báo; biểu đồ nhu cầu/lịch giao theo tuyến.')
            st.button('Đặt lại bộ lọc',on_click=reset_filters)
    context=(country,carrier,sku,ptype,scenario)
    stock=filter_frame(rec,country,carrier,sku,ptype).loc[lambda x:x.scenario_id.eq(scenario)]
    tabs=st.tabs(['Tổng quan','Dự báo','Kho hàng','Kịch bản','Cảnh báo','Giao khách','Kiểm chứng'])
    with tabs[0]:overview(bundle,context,stock)
    with tabs[1]:forecasts(bundle,context)
    with tabs[2]:inventory(bundle,context,stock)
    with tabs[3]:situations(bundle,context)
    with tabs[4]:alerts(bundle,context,stock)
    with tabs[5]:customer_delivery(bundle,context)
    with tabs[6]:evidence(bundle,run_id,state_dir)
