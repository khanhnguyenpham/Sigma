import pytest

from sigma.ui.product30_support import evidence_stamps, recommendation_action


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
