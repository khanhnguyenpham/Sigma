from streamlit.testing.v1 import AppTest


SCRIPT='''
import pandas as pd
from sigma.ui.product30_planner import render_planner
items=[];forecasts=[]
for sku in ['SYN-A','SYN-B']:
    key={'destination_country':'Synthetic','carrier':'One','sku':sku,'product_type':'eSIM'}
    items.append({**key,'scenario_id':'base','partner_id':'SYN','as_of_date':'2025-12-31',
        'on_hand':0,'IP':1,'Q':5,'needs_replenishment':True,'depletion_state':'already_empty'})
    forecasts.extend([{**key,'horizon_day':h,'forecast_qty':1.} for h in range(1,31)])
bundle={'summary':{'run_id':'synthetic_planner'},'recommendations':pd.DataFrame(items),
    'item_forecast':pd.DataFrame(forecasts),'scenario_configs':[{'scenario':{'name':'base'},
    'inventory':{'partners':{'SYN':{'lead_time_days':3,'review_days':1,'safety_days':2,'moq':1}}}}]}
render_planner(bundle,('Tất cả','Tất cả','Tất cả','Tất cả','base'))
'''


def test_reset_and_item_change_remount_browser_fields_not_only_server_values():
    at=AppTest.from_string(SCRIPT).run(timeout=30)
    assert not at.exception
    def field(label):return next(n for n in at.number_input if n.label==label)
    first_id=field('Tỷ lệ nhận hàng · %').proto.id
    field('Tỷ lệ nhận hàng · %').set_value(50)
    field('Nhu cầu so với dự báo · lần').set_value(2.)
    next(b for b in at.button if b.label=='Tính và so sánh phương án').click().run(timeout=30)
    assert field('Tỷ lệ nhận hàng · %').value==50
    next(b for b in at.button if b.label=='Khôi phục giả định cơ sở').click().run(timeout=30)
    assert not at.exception
    reset_id=field('Tỷ lệ nhận hàng · %').proto.id
    assert reset_id!=first_id # Browser must discard the previous form buffer.
    assert field('Tỷ lệ nhận hàng · %').value==100
    assert field('Nhu cầu so với dự báo · lần').value==1.
    at.selectbox(key='plan_item').set_value(('Synthetic','One','SYN-B','eSIM')).run(timeout=30)
    assert not at.exception and field('Tỷ lệ nhận hàng · %').proto.id!=reset_id
