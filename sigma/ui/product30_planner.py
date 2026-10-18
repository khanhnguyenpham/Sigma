"""Interactive expected-inventory planning over the approved aggregate release."""
from dataclasses import asdict
import json

import altair as alt
import pandas as pd
import streamlit as st

from src.common import ITEM
from sigma.analysis.planning import Assumptions,simulate
from sigma.ui.product30_support import filter_frame,item_parameters,number,ranked_recommendations
from sigma.ui.product30_charts import style,TEAL,NAVY


def reset_assumptions():
    for name in ['stock','lead','review','safety','multiplier','fraction','delay','pending_due']:
        st.session_state.pop('plan_'+name,None)
    # Forms keep a client-side input buffer. Recreate the form as well as
    # clearing server keys, otherwise inputs can display stale assumptions.
    st.session_state['_plan_form_generation']=st.session_state.get('_plan_form_generation',0)+1


def render_planner(bundle,context):
    country,carrier,sku,ptype,_=context
    source=filter_frame(bundle['recommendations'],country,carrier,sku,ptype)
    source=ranked_recommendations(source.loc[source.scenario_id.eq('base')])
    st.caption('Thử phương án cho một mặt hàng trong 30 ngày sau mốc chốt. '
        'Khởi tạo từ snapshot cơ sở; bộ lọc kịch bản lịch sử ở đầu trang không áp vào bảng này. '
        'Đây là mô phỏng tất định theo lượng dự báo, chưa mô hình hóa bất định và có thể có số lẻ; '
        'không phải actual hoặc điểm kiểm chứng mô hình.')
    if source.empty:
        st.info('Không có mặt hàng cơ sở trong bộ lọc.');return
    choices=list(source[ITEM].itertuples(index=False,name=None))
    if st.session_state.get('plan_item') not in choices:st.session_state.pop('plan_item',None)
    key=st.selectbox('Mặt hàng thử phương án',choices,key='plan_item',
        format_func=lambda x:f'{x[1]} · {x[2]} · {x[3]} · {x[0]}')
    row=source.loc[(source[ITEM]==pd.Series(key,index=ITEM)).all(axis=1)].iloc[0]
    params=item_parameters(bundle['scenario_configs'],row)
    detail=bundle['item_forecast'].loc[(bundle['item_forecast'][ITEM]==pd.Series(key,index=ITEM)).all(axis=1)].sort_values('horizon_day')
    if detail.horizon_day.tolist()!=list(range(1,31)):
        st.error('Thiếu dự báo đủ 30 ngày cho mặt hàng này.');return
    token=(bundle['summary']['run_id'],str(row.as_of_date),key)
    if st.session_state.get('_plan_item_context')!=token:
        reset_assumptions()
        st.session_state['_plan_item_context']=token
    pending=int(row.IP-row.on_hand)
    base=Assumptions(on_hand=int(row.on_hand),pending_quantity=pending,
        pending_due_days=int(params['lead_time_days']),lead_time_days=int(params['lead_time_days']),
        review_days=int(params['review_days']),safety_days=float(params['safety_days']),moq=int(params['moq']))
    generation=st.session_state.get('_plan_form_generation',0)
    def widget_key(name):return f'plan_{name}_{generation}'
    with st.form(f'plan_controls_{generation}'):
        a,b,c=st.columns(3)
        stock=a.number_input('Tồn đầu giả định',min_value=0,max_value=100000,value=base.on_hand,step=1,key=widget_key('stock'))
        lead=b.number_input('Lead time nhập · ngày',min_value=1,max_value=14,value=base.lead_time_days,step=1,key=widget_key('lead'))
        review=c.number_input('Kỳ rà soát · ngày',min_value=1,max_value=14,value=base.review_days,step=1,key=widget_key('review'))
        safety=a.number_input('Số ngày tồn an toàn',min_value=0.,max_value=14.,value=base.safety_days,step=.5,key=widget_key('safety'))
        multiplier=b.number_input('Nhu cầu so với dự báo · lần',min_value=0.,max_value=3.,value=1.,step=.1,key=widget_key('multiplier'))
        fraction=c.number_input('Tỷ lệ nhận hàng · %',min_value=0,max_value=100,value=100,step=5,key=widget_key('fraction'))
        delay=a.number_input('Trễ nhập bổ sung · ngày',min_value=0,max_value=14,value=0,step=1,key=widget_key('delay'))
        pending_due=b.number_input('Hàng đã đặt về sau · ngày giả định',min_value=1,max_value=30,
            value=base.pending_due_days,step=1,key=widget_key('pending_due'),disabled=pending==0)
        c.caption(f'Đã đặt chưa nhận: {number(pending)} đơn vị. MOQ giả định: {base.moq}. '
            'Thời gian nhập này khác thời gian giao khách D+7.')
        a,b=st.columns(2)
        a.form_submit_button('Tính và so sánh phương án',type='primary')
        b.form_submit_button('Khôi phục giả định cơ sở',on_click=reset_assumptions)
    if pending:
        st.warning(f'Gói tổng hợp có {number(pending)} đơn vị đã đặt, chưa có ETA từng lô. '
            'Ngày hàng đã đặt về ở đây là giả định bạn chọn; mô hình cơ sở tạm dùng lead time đối tác. '
            'Không dùng kết quả này xác nhận lịch giao hàng thật.')
    proposed=Assumptions(on_hand=int(stock),pending_quantity=pending,pending_due_days=int(pending_due),
        lead_time_days=int(lead),review_days=int(review),safety_days=float(safety),moq=base.moq,
        demand_multiplier=float(multiplier),receipt_fraction=float(fraction)/100,receipt_delay_days=int(delay))
    vector=detail.forecast_qty.to_numpy(float)
    try:
        baseline=simulate(vector,row.as_of_date,base)
        candidate=simulate(vector,row.as_of_date,proposed)
    except ValueError:
        st.error('Chưa đủ horizon hoặc tham số không hợp lệ. Lead time + kỳ rà soát phải nằm trong 30 ngày.');return
    comparison=[]
    for label,result in [('Cơ sở nhìn tới',baseline),('Phương án đang thử',candidate)]:
        s=result['summary']
        comparison.append({'Phương án':label,'Nhu cầu kỳ vọng':s['expected_demand'],
            'Tỷ lệ đáp ứng kỳ vọng (%)':s['expected_fill_rate']*100 if s['expected_fill_rate'] is not None else None,
            'Lượng thiếu kỳ vọng':s['expected_shortage'],'Tồn cuối ngày bình quân':s['mean_closing_on_hand'],
            'Lượng dự kiến đặt':s['planned_order_quantity'],'Số lượt đặt':s['planned_order_lines']})
    st.dataframe(pd.DataFrame(comparison),hide_index=True,width='stretch',column_config={
        name:st.column_config.NumberColumn(format='%.2f') for name in
        ['Nhu cầu kỳ vọng','Tỷ lệ đáp ứng kỳ vọng (%)','Lượng thiếu kỳ vọng','Tồn cuối ngày bình quân']})
    s=candidate['summary'];a,b,c=st.columns(3)
    a.metric('Lượng thiếu kỳ vọng',number(s['expected_shortage'],2))
    b.metric('Lượng dự kiến đặt',number(s['planned_order_quantity']))
    c.metric('Ngày thiếu đầu tiên',pd.Timestamp(s['first_shortage_date']).strftime('%d/%m/%Y')
        if pd.notna(s['first_shortage_date']) else 'Chưa thấy trong 30 ngày')
    lines=[]
    for label,result in [('Cơ sở nhìn tới',baseline),('Phương án đang thử',candidate)]:
        frame=result['ledger'][['date','closing']].copy();frame['Phương án']=label;lines.append(frame)
    chart=alt.Chart(pd.concat(lines,ignore_index=True)).mark_line(strokeWidth=2.5).encode(
        x=alt.X('date:T',title=None,axis=alt.Axis(format='%d/%m')),
        y=alt.Y('closing:Q',title='Tồn kỳ vọng · đơn vị',scale=alt.Scale(zero=True)),
        color=alt.Color('Phương án:N',scale=alt.Scale(domain=['Cơ sở nhìn tới','Phương án đang thử'],range=[NAVY,TEAL])),
        tooltip=[alt.Tooltip('date:T',title='Ngày',format='%d/%m/%Y'),'Phương án:N',
            alt.Tooltip('closing:Q',title='Tồn kỳ vọng',format='.2f')])
    st.altair_chart(style(chart.properties(height=235)),width='stretch')
    st.caption('Nhận hàng đầu ngày, đáp ứng nhu cầu kỳ vọng rồi chốt ngày và xét đặt. '
        'Trigger tồn < ROP; IP tính lượng đã đặt, chưa cộng vào tồn. Lượng nhận mô phỏng làm tròn xuống theo tỷ lệ. '
        'Dòng ngày 0 chỉ là snapshot ban đầu. Cuối horizon không đủ L+R thì để trống quyết định nhập; không bổ sung dự báo bằng 0. '
        'Không dùng tỷ lệ đáp ứng này thay kết quả replay lịch sử hoặc metric 10/10.')
    display=candidate['ledger'][['date','opening','receipts','demand','fulfilled','shortage',
        'closing','ROP','IP','Q','decision_status']].copy()
    display['decision_status']=display.decision_status.map({'forecast_available':'Đủ dữ liệu để xét nhập',
        'insufficient_forecast':'Thiếu dự báo L+R · chưa xét nhập'})
    st.dataframe(display.rename(columns={
        'date':'Ngày','opening':'Tồn đầu','receipts':'Nhận mô phỏng','demand':'Nhu cầu kỳ vọng',
        'fulfilled':'Đáp ứng kỳ vọng','shortage':'Thiếu kỳ vọng','closing':'Tồn cuối','Q':'Đề xuất đặt',
        'decision_status':'Phạm vi quyết định'}),
        hide_index=True,width='stretch')
    a,b=st.columns(2)
    a.download_button('Xuất sổ phương án CSV',candidate['ledger'].to_csv(index=False).encode('utf-8-sig'),
        file_name='sigma_phuong_an_mo_phong.csv',mime='text/csv')
    payload={'item':dict(zip(ITEM,key)),'as_of_date':str(row.as_of_date),
        'assumptions':asdict(proposed),'basis':'fixed forecast; expected quantities; assumed receipts; not actual',
        'benchmark_modified':False,'real_orders_placed':False}
    b.download_button('Xuất giả định JSON',json.dumps(payload,ensure_ascii=False,indent=2),
        file_name='sigma_gia_dinh_phuong_an.json',mime='application/json')
    if len(candidate['orders']):
        st.caption('Lịch lô nhập giả định của phương án; lô có thể về sau cuối horizon.')
        st.dataframe(candidate['orders'],hide_index=True,width='stretch')
