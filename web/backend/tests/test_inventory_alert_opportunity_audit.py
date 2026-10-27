"""Synthetic arithmetic and posthoc-bound tests; no real private records."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import ast

import pytest
from web.backend.research import inventory_alert_opportunity_audit as r
from web.backend.research import inventory_alert_opportunity_verification as v
from test_simulation import inputs,ORIGIN


def world(event_days,close=None,length=24):
    events=[dict(window_origin=str(ORIGIN),date=str(ORIGIN+timedelta(days=d)),item_id=1,sequence=n,
                 event_id=str(n)) for n,d in enumerate(event_days,1)]
    ledger=[dict(date=str(ORIGIN+timedelta(days=d)),item_id=1,closing_qty=(close or {}).get(d,1)) for d in range(length+1)]
    return dict(events=events,ledger=ledger,alarms=[],orders=[])


def ceiling(w):
    cases=[dict(**e,early=False) for e in w['events']]
    a=r.opportunities(w,cases);assert a==v.event_opportunities(w,cases)
    return a


@pytest.mark.parametrize('day,expected',[ (6,False),(7,True),(14,True) ])
def test_six_seven_fourteen_day_boundaries(day,expected):
    rows,metric=ceiling(world([day]))
    assert rows[0]['eligible'] is expected
    assert metric['ceiling_numerator']==int(expected)
    if day==14:assert rows[0]['candidate_dates']==[str(ORIGIN+timedelta(days=d)) for d in range(8)]


def test_prior_episode_blocks_warning_even_when_stock_positive_and_same_day_second_episode():
    rows,m=ceiling(world([8,13,13]))
    assert [x['eligible'] for x in rows]==[True,False,False]
    assert rows[1]['reason']==rows[2]['reason']=='prior_depletion_blocks_all'
    assert m['event_denominator']==3 and m['target_numerator']==2


def test_zero_stretch_does_not_create_opportunity_then_recovery_allows_it():
    w=world([8,17],close={d:0 for d in range(8,11)})
    rows,m=ceiling(w)
    assert rows[1]['reason']=='no_positive_stock'
    w['ledger'][10]['closing_qty']=2
    rows,m=ceiling(w)
    assert rows[1]['candidate_dates']==[str(ORIGIN+timedelta(days=10))]
    assert m['ceiling_numerator']==2


def test_no_events_has_null_rate_and_cannot_pass_target():
    rows,m=ceiling(world([]))
    assert rows==[] and m['ceiling_rate'] is m['target_structurally_possible'] is None


def test_warmup_repeated_alarms_and_first_event_matching():
    w=world([8,16],close={8:0,16:0})
    w['alarms']=[dict(date=str(ORIGIN+timedelta(days=d)),item_id=1,
        predicted_depletion_date=str(ORIGIN+timedelta(days=p))) for d,p in [(0,8),(1,8),(9,16),(10,16)]]
    a=r.score(w,ORIGIN+timedelta(days=10),ORIGIN+timedelta(days=24))
    assert a==v.score_events(w,ORIGIN+timedelta(days=10),ORIGIN+timedelta(days=24))
    cases,m=a
    assert len(cases)==1 and m['early_numerator']==1 and m['event_denominator']==1
    assert cases[0]['alarm_date']==str(ORIGIN+timedelta(days=9))
    assert m['alarm_TP']==1


def test_same_day_order_intervention_and_late_unlabelled_alarm_are_separate():
    w=world([])
    w['alarms']=[dict(date=str(ORIGIN+timedelta(days=d)),item_id=1,predicted_depletion_date=str(ORIGIN+timedelta(days=d+1))) for d in (10,23)]
    w['orders']=[dict(item_id=1,is_initial=False,ordered_on=str(ORIGIN+timedelta(days=10)),eta=str(ORIGIN+timedelta(days=17)))]
    a=r.score(w,ORIGIN,ORIGIN+timedelta(days=24))
    assert a==v.score_events(w,ORIGIN,ORIGIN+timedelta(days=24))
    assert a[1]['intervened_count']==1 and a[1]['right_censored_count']==1
    assert a[1]['alarm_FP']==0 and a[1]['early_rate'] is None


def fixture():
    matrix,sales,catalog,forecasts,policies,scenario=inputs()
    snapshot=dict(period=dict(origin=str(ORIGIN),end=str(ORIGIN+timedelta(days=14)),score_start=str(ORIGIN+timedelta(days=1))),
        catalog=catalog,policies=policies,receipts=[],
        daily=[dict(date=str(d.date()),item_id=1,quantity=int(q),actual_available=True) for d,q in matrix[1].items()],
        forecasts=[dict(as_of_date=str(d),item_id=i,forecast=f) for (d,i),f in forecasts.items()],
        sales=[dict(date=str(d),item_id=i,sequence=s['source_sequence'],quantity=s['quantity']) for (d,i),records in sales.items() for s in records])
    baseline=r.replay(snapshot)
    frozen=deepcopy(baseline)
    frozen['initialization']=[dict(**x,base_qty=x['initial_qty'],added_ss=0) for x in baseline['initialization']]
    return snapshot,baseline,frozen


def test_real_app_replay_reconciles_physics_and_projection_independently():
    snapshot,result,frozen=fixture()
    r.compare_replay(result,frozen)
    assert result==v.reconstruct(snapshot,frozen)
    assert result['initialization']==[dict(item_id=1,initial_qty=70)]
    first=result['ledger'][0]
    assert first['ss']==20 and first['rop']==100 and first['recommended_qty']==50
    assert result['orders'][0]['eta']=='2025-10-07'


def test_validation_seed_without_database_ids_has_identical_inventory_and_alarms():
    snapshot,expected,_=fixture()
    for p in snapshot['policies']:
        p.pop('id');p.pop('supplier_id');p.pop('version')
    assert r.replay(snapshot)==expected


def test_long_zero_stock_then_receipt_and_same_day_depletion_form_only_two_episodes():
    snapshot,_,_=fixture()
    for p in snapshot['policies']:p['configured_rop_floor']=0
    for f in snapshot['forecasts']:f['forecast']=[0]*14
    snapshot['receipts']=[dict(item_id=1,ordered_on=str(ORIGIN),eta=str(ORIGIN+timedelta(days=7)),ordered_qty=10,lot_key='known')]
    snapshot['sales'][0]['quantity']=80
    for row in snapshot['daily']:
        if row['date']==str(ORIGIN+timedelta(days=1)):row['quantity']=80
    result=r.replay(snapshot);frozen=deepcopy(result)
    frozen['initialization']=[dict(**x,base_qty=x['initial_qty'],added_ss=0) for x in result['initialization']]
    assert result==v.reconstruct(snapshot,frozen)
    assert [e['date'] for e in result['events']]==['2025-10-01','2025-10-07']
    receipt_day=result['ledger'][7]
    assert receipt_day['opening_qty']==0 and receipt_day['receipts_qty']==10 and receipt_day['closing_qty']==0
    cases,metrics=r.score(result,ORIGIN+timedelta(days=1),ORIGIN+timedelta(days=14))
    assert metrics['event_denominator']==2
    rows,metric=r.opportunities(result,cases)
    assert (rows,metric)==v.event_opportunities(result,cases)
    assert metric['ceiling_numerator']==0


def test_initially_zero_and_unfulfilled_sales_never_create_new_depletion_episode():
    snapshot,_,_=fixture()
    for p in snapshot['policies']:p['configured_rop_floor']=0
    for f in snapshot['forecasts']:f['forecast']=[0]*14
    for row in snapshot['daily']:
        if row['date']<=str(ORIGIN):row['quantity']=0
    result=r.replay(snapshot)
    assert result['events']==[] and all(t['balance_after']==0 for t in result['transactions'])
    cases,m=r.score(result,ORIGIN+timedelta(days=1),ORIGIN+timedelta(days=14))
    assert cases==[] and m['early_rate'] is None


@pytest.mark.parametrize('field',['closing_qty','receipts_qty'])
def test_independent_rebuild_rejects_forged_physical_ledger(field):
    snapshot,_,frozen=fixture();frozen['ledger'][2][field]+=1
    with pytest.raises(ValueError):v.reconstruct(snapshot,frozen)


def test_future_actual_does_not_change_replayed_decisions_before_cutoff():
    snapshot,first,_=fixture();other=deepcopy(snapshot)
    for s in other['sales']:
        if s['date']>='2025-10-08':s['quantity']+=100
    for row in other['daily']:
        if row['date']>='2025-10-08':row['quantity']+=100
    second=r.replay(other)
    for table in ('ledger','alarms'):
        assert [x for x in first[table] if x['date']<'2025-10-08']==[x for x in second[table] if x['date']<'2025-10-08']
    assert [x for x in first['orders'] if x['ordered_on']<'2025-10-08']==[x for x in second['orders'] if x['ordered_on']<'2025-10-08']


def test_readers_reject_duplicate_keys_and_nonfinite_json(tmp_path):
    path=tmp_path/'bad.json'
    for text in ('{"a":1,"a":2}','{"a":NaN}'):
        path.write_text(text)
        for reader in (r.read,v.read):
            with pytest.raises(ValueError):reader(path)


def test_verifier_has_no_production_arithmetic_or_runner_import():
    tree=ast.parse(Path(v.__file__).read_text(encoding='utf-8'))
    imports=[node.module or '' for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    assert not any(name.startswith('modules.') or 'inventory_alert_opportunity_audit' in name for name in imports)
