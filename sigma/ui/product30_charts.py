"""Charts with explicit units and observed/allocated series."""
import altair as alt
import pandas as pd

TEAL = '#087f8c'
NAVY = '#263d57'
AMBER = '#cf702b'


def style(chart):
    return chart.configure_view(strokeOpacity=0).configure_axis(
        labelColor='#66778a', titleColor='#66778a', gridColor='#eaf0f5',
        domain=False, labelFontSize=11, titleFontSize=11).configure_legend(
        title=None, labelColor='#526275', orient='top', labelFontSize=11)


def demand(frame, origin, height=245):
    line = alt.Chart(frame).mark_line(strokeWidth=2.5).encode(
        x=alt.X('date:T', title=None, axis=alt.Axis(format='%d/%m', tickCount=6)),
        y=alt.Y('quantity:Q', title='Lượng bán · đơn vị', scale=alt.Scale(zero=True)),
        color=alt.Color('series:N', scale=alt.Scale(domain=[
            'Số bán đã quan sát', 'Phân bổ từ dự báo tổng'], range=[NAVY, TEAL])),
        strokeDash=alt.StrokeDash('series:N', scale=alt.Scale(domain=[
            'Số bán đã quan sát', 'Phân bổ từ dự báo tổng'], range=[[1,0],[5,3]]), legend=None),
        tooltip=[alt.Tooltip('date:T', title='Ngày', format='%d/%m/%Y'),
            alt.Tooltip('series:N', title='Nguồn'), alt.Tooltip('quantity:Q', title='Lượng', format=',.2f')])
    boundary = alt.Chart(pd.DataFrame({'date':[pd.Timestamp(origin)]})).mark_rule(
        color='#9ba9b7', strokeDash=[3,3]).encode(x='date:T')
    return style((line+boundary).properties(height=height))


def route_error(frame, height=285):
    data=frame.copy()
    data['route']=data.destination_country+' · '+data.carrier
    data['result']=data.passes_20_pct.map({True:'Đạt ≤20%',False:'Còn trên 20%'})
    bar=alt.Chart(data).mark_bar(cornerRadiusEnd=4,size=16).encode(
        y=alt.Y('route:N',sort=alt.SortField('mape_positive_pct','ascending'),title=None,
            axis=alt.Axis(labelLimit=200)),
        x=alt.X('mape_positive_pct:Q',title='MAPE tổng (%)',scale=alt.Scale(domainMin=0)),
        color=alt.Color('result:N',scale=alt.Scale(domain=['Đạt ≤20%','Còn trên 20%'],range=[TEAL,AMBER])),
        tooltip=[alt.Tooltip('route:N',title='Tuyến'),alt.Tooltip('mape_positive_pct:Q',title='MAPE (%)',format='.2f'),
            alt.Tooltip('coverage:Q',title='Độ phủ',format='.0%')])
    limit=alt.Chart(pd.DataFrame({'limit':[20.]})).mark_rule(color=AMBER,strokeDash=[4,3]).encode(x='limit:Q')
    return style((bar+limit).properties(height=height))


def scenarios(frame, names, selected):
    data=frame.copy()
    data['label']=data.scenario_id.map(names)
    data['rate']=data.fill_rate*100
    data['selected']=data.scenario_id.eq(selected)
    chart=alt.Chart(data).mark_bar(cornerRadiusEnd=4,size=17).encode(
        y=alt.Y('label:N',title=None,sort=alt.SortField('rate','descending'),axis=alt.Axis(labelLimit=250)),
        x=alt.X('rate:Q',title='Lượng yêu cầu được đáp ứng (%)',scale=alt.Scale(domain=[0,100])),
        color=alt.condition(alt.datum.selected,alt.value(TEAL),alt.value('#bacbd8')),
        tooltip=[alt.Tooltip('label:N',title='Kịch bản'),alt.Tooltip('rate:Q',title='Đáp ứng (%)',format='.2f'),
            alt.Tooltip('shortage:Q',title='Lượng thiếu',format=',.0f')])
    return style(chart.properties(height=360))


def delivery(frame):
    data=frame.groupby('delivery_date',as_index=False)[['known_commitment_qty','forecast_from_future_orders_qty']].sum()
    data=data.melt('delivery_date',var_name='series',value_name='quantity')
    data['series']=data.series.map({'known_commitment_qty':'Đơn đã đặt · lịch D+7',
        'forecast_from_future_orders_qty':'Đơn tương lai · phân bổ dự báo'})
    chart=alt.Chart(data).mark_bar().encode(
        x=alt.X('delivery_date:T',title=None,axis=alt.Axis(format='%d/%m',tickCount=7)),
        y=alt.Y('quantity:Q',title='Lượng giao dự kiến · đơn vị'),
        color=alt.Color('series:N',scale=alt.Scale(range=[TEAL,'#b7c8d8'])),
        tooltip=[alt.Tooltip('delivery_date:T',title='Ngày giao',format='%d/%m/%Y'),
            alt.Tooltip('series:N',title='Nguồn'),alt.Tooltip('quantity:Q',title='Lượng',format=',.2f')])
    return style(chart.properties(height=280))


def policy_stock(timeline, selected):
    view=timeline.loc[timeline.scenario_id.isin(['base',selected])].groupby(['date','scenario_id'],as_index=False).closing.sum()
    view['label']=view.scenario_id.map(lambda x:'Cơ sở' if x=='base' else 'Kịch bản đang chọn')
    chart=alt.Chart(view).mark_line(strokeWidth=2.3).encode(
        x=alt.X('date:T',title=None,axis=alt.Axis(format='%d/%m',tickCount=6)),
        y=alt.Y('closing:Q',title='Tồn cuối ngày · đơn vị',scale=alt.Scale(zero=True)),
        color=alt.Color('label:N',scale=alt.Scale(domain=['Cơ sở','Kịch bản đang chọn'],range=['#acbdcc',TEAL])),
        tooltip=[alt.Tooltip('date:T',title='Ngày',format='%d/%m/%Y'),alt.Tooltip('label:N',title='Kịch bản'),alt.Tooltip('closing:Q',title='Tồn',format=',.0f')])
    return style(chart.properties(height=240))


def policy_service(timeline, selected):
    view=timeline.loc[timeline.scenario_id.eq(selected)].groupby('date',as_index=False)[['fulfilled','shortage']].sum()
    view=view.melt('date',var_name='series',value_name='quantity')
    view['series']=view.series.map({'fulfilled':'Đã đáp ứng','shortage':'Chưa đáp ứng'})
    chart=alt.Chart(view).mark_bar().encode(
        x=alt.X('date:T',title=None,axis=alt.Axis(format='%d/%m',tickCount=6)),
        y=alt.Y('quantity:Q',title='Yêu cầu bán · đơn vị'),
        color=alt.Color('series:N',scale=alt.Scale(domain=['Đã đáp ứng','Chưa đáp ứng'],range=[TEAL,'#e0a36f'])),
        tooltip=[alt.Tooltip('date:T',title='Ngày',format='%d/%m/%Y'),alt.Tooltip('series:N',title='Kết quả'),alt.Tooltip('quantity:Q',title='Lượng',format=',.0f')])
    return style(chart.properties(height=240))
