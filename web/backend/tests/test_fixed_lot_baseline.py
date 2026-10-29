"""Synthetic protocol checks; never access private research artifacts or app DB."""
from datetime import date, timedelta
import copy
import pytest
from web.backend.research import fixed_lot_baseline as runner
from web.backend.research import fixed_lot_verification as verifier


def fixture():
    origin=date(2025,6,30);end=date(2025,7,20)
    catalog=[dict(item_id=i,product_type='eSIM' if i<3 else 'physical_SIM',
                  first_seen_date='2024-01-01') for i in range(1,5)]
    daily=[];forecasts=[];sales=[];sequence=0
    for offset in range(-27,21):
        day=str(origin+timedelta(days=offset))
        for item in range(1,5):
            q=1 if item%2 else 3
            daily.append(dict(item_id=item,date=day,quantity=q,actual_available=True))
            if offset>=0:forecasts.append(dict(item_id=item,as_of_date=day,forecast=[1.3]*14))
            if offset>0:
                sequence+=1;sales.append(dict(item_id=item,date=day,quantity=q,sequence=sequence))
    return dict(catalog=catalog,daily=daily,forecasts=forecasts,sales=sales,receipts=[],
                policies=[dict(item_id=i,moq=5,safety_days=2,configured_rop_floor=2,
                               effective_from=str(origin),effective_to=None) for i in range(1,5)],
                period=dict(origin=str(origin),end=str(end),score_start='2025-07-05'))


def test_quantity_groups_use_only_locked_history():
    s=fixture();p=runner.read(runner.PROTOCOL)
    lots=runner.quantities(s,p['quantity_basis'])
    assert [r['fixed_order_qty'] for r in lots]==[5,10,10,15]
    assert [r['threshold'] for r in lots]==[56,56,56,56]
    changed=copy.deepcopy(s)
    for row in changed['daily']:
        if row['date']>'2025-06-30':row['quantity']=9999
    assert runner.quantities(changed,p['quantity_basis'])==lots
    assert verifier.quantity_basis(s,p['quantity_basis'])==lots


def test_missing_actual_is_not_zero_or_a_group():
    s=fixture();s['daily'][0]['actual_available']=False
    with pytest.raises(ValueError,match='fully observed'):
        runner.quantities(s,runner.read(runner.PROTOCOL)['quantity_basis'])


@pytest.mark.parametrize('config',runner.read(runner.PROTOCOL)['scenarios'],ids=lambda r:r['id'])
def test_native_replay_matches_independent_fixed_decisions(config):
    s=fixture();lots=runner.quantities(s,runner.read(runner.PROTOCOL)['quantity_basis'])
    result=runner.replay(runner.fixed_snapshot(s,lots),config)
    assert result==runner.replay(runner.fixed_snapshot(s,lots),config,indexed=False)
    verifier.reconstruct(s,lots,config,result)
    cases,metrics,opportunities=runner.summarize(result,s)
    assert verifier.check_summary(result,s,metrics)==(cases,opportunities)
    lookup={r['item_id']:r['fixed_order_qty'] for r in lots}
    assert result['orders']
    assert all(o['ordered_qty']==lookup[o['item_id']] for o in result['orders'])
    tampered=copy.deepcopy(result);tampered['orders'][0]['ordered_qty']+=1
    with pytest.raises(ValueError):verifier.reconstruct(s,lots,config,tampered)


def test_future_actual_does_not_change_prior_orders_or_alarms():
    s=fixture();p=runner.read(runner.PROTOCOL);lots=runner.quantities(s,p['quantity_basis']);config=p['scenarios'][0]
    expected=runner.replay(runner.fixed_snapshot(s,lots),config)
    changed=copy.deepcopy(s)
    for row in changed['sales']:
        if row['date']>'2025-07-10':row['quantity']*=10
    for row in changed['daily']:
        if row['date']>'2025-07-10':row['quantity']*=10
    actual=runner.replay(runner.fixed_snapshot(changed,lots),config)
    for key,field in [('alarms','date'),('ledger','date'),('orders','ordered_on')]:
        assert [r for r in expected[key] if r[field]<='2025-07-10']==[r for r in actual[key] if r[field]<='2025-07-10']


def test_lock_runs_original_forecast_without_selection_or_s25():
    p=runner.read(runner.PROTOCOL)
    assert p['alarm_alpha']==1 and p['no_selection']
    assert [s['id'] for s in p['scenarios']]==['base','cover_3','cover_14','safety_05','safety_15']
    assert p['quantity_basis']['end']<'2025-07-01'
