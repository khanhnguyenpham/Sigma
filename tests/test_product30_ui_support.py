import pytest
import pandas as pd

from sigma.ui.product30_support import evidence_stamps, recommendation_action, route_forecast_status


def test_route_coverage_never_confuses_missing_forecast_with_zero_or_passed_metric():
    top=pd.DataFrame({'destination_country':['Synthetic']*3,'carrier':['A','B','C'],
        'window_days':[7]*3,'passes_20_pct':[True,False,True]})
    frame=pd.DataFrame([{'destination_country':'Synthetic','carrier':carrier,'window_days':7,
        'as_of_date':pd.Timestamp('2025-12-31'),'target_date':date,'forecast_qty':0.}
        for carrier,days in [('A',7),('B',6)] for date in pd.date_range('2026-01-01',periods=days)])
    result=route_forecast_status(frame,top,7,'2025-12-31').set_index('carrier')
    assert len(result)==3 and result.forecast_complete.to_dict()=={'A':True,'B':False,'C':False}
    assert result.loc['A','forecast_total']==0 and result.loc[['B','C'],'forecast_total'].isna().all()
    assert result.forecast_days.to_dict()=={'A':7,'B':6,'C':0}
    with pytest.raises(ValueError,match='Duplicate forecast day'):
        route_forecast_status(pd.concat([frame,frame.iloc[[0]]]),top,7,'2025-12-31')
    frame.loc[0,'forecast_qty']=float('inf')
    assert not route_forecast_status(frame,top,7,'2025-12-31').forecast_complete.any()


def test_cache_evidence_includes_parent_files_and_both_receipts(tmp_path):
    for name in ['synthetic_product','synthetic_forecast']:
        folder=tmp_path/'outputs'/name;folder.mkdir(parents=True)
        (folder/'summary.json').write_text('synthetic')
        (tmp_path/'outputs'/(name+'_verification.json')).write_text('synthetic receipt')
    before=evidence_stamps(tmp_path,'synthetic_product','synthetic_forecast')
    parent=tmp_path/'outputs/synthetic_forecast/top10_results.csv'
    parent.write_text('synthetic changed artifact')
    assert evidence_stamps(tmp_path,'synthetic_product','synthetic_forecast')!=before
    before=evidence_stamps(tmp_path,'synthetic_product','synthetic_forecast')
    receipt=tmp_path/'outputs/synthetic_forecast_verification.json'
    receipt.write_text('changed receipt size')
    assert evidence_stamps(tmp_path,'synthetic_product','synthetic_forecast')!=before
    receipt.unlink()
    with pytest.raises(FileNotFoundError):
        evidence_stamps(tmp_path,'synthetic_product','synthetic_forecast')


def test_cache_path_cannot_escape_outputs(tmp_path):
    with pytest.raises(ValueError):evidence_stamps(tmp_path,'../escape','synthetic_forecast')


@pytest.mark.parametrize('row,expected',[
    ({'on_hand':0,'Q':10,'needs_replenishment':True},'Hết hàng · ưu tiên xử lý'),
    ({'on_hand':5,'Q':10,'needs_replenishment':True},'Xem xét đặt bổ sung'),
    ({'on_hand':5,'Q':0,'needs_replenishment':True},'Đã có hàng đang về · theo dõi ETA'),
    ({'on_hand':50,'Q':0,'needs_replenishment':False},'Theo dõi định kỳ'),
])
def test_customer_action_keeps_low_stock_pending_and_empty_distinct(row,expected):
    assert recommendation_action(row)==expected
