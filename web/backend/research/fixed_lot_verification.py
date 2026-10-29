"""Independent physical flow, decision, projection and episode scoring for CHG-077."""
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip, hashlib, json, math, statistics
from pathlib import Path
import numpy as np
from core.hashes import code_digest, digest

ROOT = Path(__file__).resolve().parents[3]

def read(path):
    raw=Path(path).read_bytes()
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    def nonfinite(value):raise ValueError('Nonfinite JSON constant')
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw,object_pairs_hook=unique,parse_constant=nonfinite)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition):
    if not condition:raise ValueError('Independent opportunity verification failed')

def equal(a,b):
    if isinstance(b,dict):
        require(isinstance(a,dict) and a.keys()==b.keys())
        for k in b:equal(a[k],b[k])
    elif isinstance(b,list):
        require(isinstance(a,list) and len(a)==len(b))
        for x,y in zip(a,b,strict=True):equal(x,y)
    elif isinstance(b,float):require(type(a) in (float,int) and math.isclose(a,b,abs_tol=1e-8,rel_tol=0))
    else:require(a==b and (type(a) is type(b) if isinstance(b,(bool,int)) else True))

def score_events(result,score_start,end):
    events=defaultdict(list);alarms=defaultdict(list);orders=defaultdict(list)
    for e in result['events']:events[e['item_id']].append(e)
    for a in result['alarms']:
        if a['predicted_depletion_date'] is not None:alarms[a['item_id']].append(a)
    for o in result['orders']:orders[o['item_id']].append(o)
    cases=[];errors=[];status=Counter()
    for item,rows in events.items():
        previous=None
        for e in rows:
            if e['date']>=str(score_start):
                candidates=[a for a in alarms[item] if a['date']<e['date'] and (previous is None or previous<=a['date'])
                    and (date.fromisoformat(e['date'])-date.fromisoformat(a['date'])).days<=14]
                first=min(candidates,key=lambda r:r['date']) if candidates else None
                lead=(date.fromisoformat(e['date'])-date.fromisoformat(first['date'])).days if first else None
                cases.append(dict(**e,alarm_date=first['date'] if first else None,
                    predicted_depletion_date=first['predicted_depletion_date'] if first else None,lead_days=lead,early=lead is not None and lead>=7))
                if first:errors.append(abs((date.fromisoformat(e['date'])-date.fromisoformat(first['predicted_depletion_date'])).days))
            previous=e['date']
    cases.sort(key=lambda r:(r['date'],r['item_id'],r['sequence']))
    for item,rows in alarms.items():
        for a in rows:
            if a['date']<str(score_start):continue
            day=date.fromisoformat(a['date']);limit=day+timedelta(days=14)
            hit=any(a['date']<e['date']<=str(limit) for e in events[item])
            intervention=any(not o['is_initial'] and o['ordered_on']>=a['date'] and o['eta']<=str(min(limit,end)) for o in orders[item])
            label='TP' if hit else 'intervened' if intervention else 'right_censored' if limit>end else 'FP'
            status[label]+=1
    n=len(cases);early=sum(c['early'] for c in cases);evaluated=status['TP']+status['FP']
    metrics=dict(early_numerator=early,event_denominator=n,early_rate=early/n if n else None,
        precision=status['TP']/evaluated if evaluated else None,recall=sum(c['alarm_date'] is not None for c in cases)/n if n else None,
        date_mae=sum(errors)/len(errors) if errors else None,alarm_TP=status['TP'],alarm_FP=status['FP'],
        intervened_count=status['intervened'],right_censored_count=status['right_censored'])
    return cases,metrics

def event_opportunities(result,cases):
    """Event-first enumeration of every permitted 7..14 day look-back date."""
    ledger={(r['date'],r['item_id']):r['closing_qty'] for r in result['ledger']}
    prior={};previous={}
    for e in result['events']:
        prior[e['event_id']]=previous.get(e['item_id']);previous[e['item_id']]=e['date']
    rows=[]
    for c in cases:
        candidates=[];available=unblocked=0
        for lead in range(14,6,-1):
            d=str(date.fromisoformat(c['date'])-timedelta(days=lead));key=(d,c['item_id'])
            if key not in ledger:continue
            available+=1
            if prior[c['event_id']] is not None and prior[c['event_id']]>d:continue
            unblocked+=1
            if ledger[key]>0:candidates.append(d)
        reason='eligible' if candidates else 'no_decision_day' if available==0 else 'prior_depletion_blocks_all' if unblocked==0 else 'no_positive_stock'
        require(not c['early'] or bool(candidates))
        rows.append(dict(event_id=c['event_id'],item_id=c['item_id'],date=c['date'],candidate_dates=candidates,
            eligible=bool(candidates),reason=reason,baseline_early=c['early']))
    n=len(rows);ceiling=sum(r['eligible'] for r in rows);early=sum(r['baseline_early'] for r in rows)
    required=math.ceil(45*n/100)
    return rows,dict(event_denominator=n,baseline_early_numerator=early,ceiling_numerator=ceiling,ceiling_rate=ceiling/n if n else None,
        target_numerator=required,needed_additional_early=required-early if n else None,additional_opportunities=ceiling-early,
        target_structurally_possible=ceiling>=required if n else None,
        reason_counts={k:sum(r['reason']==k for r in rows) for k in ('eligible','no_decision_day','prior_depletion_blocks_all','no_positive_stock')},
        scope='posthoc_structural_upper_bound_not_a_forecast')


def quantity_basis(snapshot, specification):
    start, finish = (date.fromisoformat(specification[k]) for k in ('start','end'))
    totals = {}
    for item in snapshot['catalog']:
        rows = [r for r in snapshot['daily'] if r['item_id']==item['item_id'] and str(start)<=r['date']<=str(finish)]
        require(len(rows)==(finish-start).days+1 and len({r['date'] for r in rows})==len(rows))
        require(all(r['actual_available'] is True and type(r['quantity']) is int and r['quantity']>=0 for r in rows))
        totals[item['item_id']] = sum(r['quantity'] for r in rows)
    thresholds={kind:statistics.median(totals[i['item_id']] for i in snapshot['catalog'] if i['product_type']==kind)
                for kind in specification['lots']}
    return [dict(item_id=i['item_id'],product_type=i['product_type'],quantity_28d=totals[i['item_id']],
                 threshold=thresholds[i['product_type']],level='high' if totals[i['item_id']]>thresholds[i['product_type']] else 'low',
                 fixed_order_qty=specification['lots'][i['product_type']]['high' if totals[i['item_id']]>thresholds[i['product_type']] else 'low'])
            for i in sorted(snapshot['catalog'],key=lambda r:r['item_id'])]


def reconstruct(snapshot, lots, config, result):
    """Re-decide orders from prefix data; do not trust the runner's order schedule."""
    start,end=(date.fromisoformat(snapshot['period'][k]) for k in ('origin','end'))
    ids=sorted(i['item_id'] for i in snapshot['catalog'])
    daily={(r['date'],r['item_id']):r for r in snapshot['daily']}
    forecasts={(r['as_of_date'],r['item_id']):r['forecast'] for r in snapshot['forecasts']}
    quantities={r['item_id']:r['fixed_order_qty'] for r in lots}
    stock={}
    for item in ids:
        history=[daily[(str(start-timedelta(days=h)),item)] for h in range(28)]
        require(all(r['actual_available'] for r in history))
        stock[item]=math.ceil(sum(r['quantity'] for r in history)/28*config['cover'])
    expected=dict(initialization=[dict(item_id=i,initial_qty=stock[i]) for i in ids],ledger=[],transactions=[],events=[],alarms=[],orders=[])
    by_item=defaultdict(list)
    for lot in snapshot['receipts']:
        require(lot['ordered_on']<=str(start))
        if lot['eta']>str(start):
            row=dict(window_origin=str(start),item_id=lot['item_id'],ordered_on=lot['ordered_on'],eta=lot['eta'],
                     ordered_qty=lot['ordered_qty'],is_initial=True,received=False)
            expected['orders'].append(row);by_item[lot['item_id']].append(row)
    sales=defaultdict(list)
    for row in sorted(snapshot['sales'],key=lambda r:r['sequence']):sales[(row['date'],row['item_id'])].append(row)
    policies=defaultdict(list)
    for p in snapshot['policies']:policies[p['item_id']].append(p)
    d=start
    while d<=end:
        for item in ids:
            day=str(d);opening=stock[item]
            arriving=[o for o in by_item[item] if o['eta']==day]
            received=sum(o['ordered_qty'] for o in arriving)
            for o in arriving:o['received']=True
            balance=opening+received;sold=filled=shortage=0
            if d>start:require(daily[(day,item)]['actual_available'])
            for sale in sales[(day,item)] if d>start else []:
                before=balance;q=sale['quantity'];take=min(balance,q);balance-=take
                sold+=q;filled+=take;shortage+=q-take
                expected['transactions'].append(dict(window_origin=str(start),date=day,item_id=item,sequence=sale['sequence'],
                    quantity=q,fulfilled_qty=take,shortage_qty=q-take,balance_after=balance))
                if before>0 and balance==0:
                    expected['events'].append(dict(window_origin=str(start),date=day,item_id=item,sequence=sale['sequence'],event_id=f"{start}:{item}:{sale['sequence']}"))
            stock[item]=balance
            active=[p for p in policies[item] if p['effective_from']<=day and (p['effective_to'] is None or day<p['effective_to'])]
            require(len(active)==1);p=active[0]
            vector=np.array(forecasts[(day,item)],dtype=float)
            require(vector.shape==(14,) and np.isfinite(vector).all() and (vector>=0).all())
            ss=math.ceil(float(p['safety_days'])*config['multiplier']*float(vector.mean()))
            forecast_rop=math.ceil(float(vector[:7].sum())+ss);rop=max(forecast_rop,p['configured_rop_floor'])
            target=rop+math.ceil(float(vector[7]));pending=sum(o['ordered_qty'] for o in by_item[item] if o['eta']>day)
            ip=balance+pending;trigger=balance<rop;q=quantities[item] if trigger and ip<target else 0
            expected['ledger'].append(dict(window_origin=str(start),item_id=item,date=day,opening_qty=opening,receipts_qty=received,
                sales_qty=sold,fulfilled_qty=filled,shortage_qty=shortage,closing_qty=balance,forecast_as_of_date=day,
                ss=ss,rop_forecast=forecast_rop,rop=rop,target_stock=target,pending_qty=pending,inventory_position=ip,
                needs_replenishment=trigger,recommended_qty=q))
            projected=float(balance);prediction=None
            if projected>0:
                for h,demand in enumerate(vector,1):
                    future=str(d+timedelta(days=h))
                    receipt=sum(o['ordered_qty'] for o in by_item[item] if o['eta']==future)
                    projected=max(0.,projected+receipt-float(demand))
                    if projected==0 and prediction is None:prediction=future
            expected['alarms'].append(dict(date=day,item_id=item,origin_on_hand=balance,predicted_depletion_date=prediction))
            if q:
                order=dict(window_origin=str(start),item_id=item,ordered_on=day,eta=str(d+timedelta(days=7)),
                           ordered_qty=q,is_initial=False,received=False)
                expected['orders'].append(order);by_item[item].append(order)
        d+=timedelta(days=1)
    for rows in expected.values():rows.sort(key=lambda r:(r.get('date',r.get('ordered_on','')),r['item_id'],r.get('sequence',0),r.get('eta','')))
    equal(result,expected)


def check_summary(result, snapshot, actual):
    start,end=(date.fromisoformat(snapshot['period'][k]) for k in ('score_start','end'))
    cases,metrics=score_events(result,start,end)
    rows,ceiling=event_opportunities(result,cases)
    for name,begin in [('full_period',snapshot['period']['origin']),('scored_period',str(start-timedelta(days=1)))]:
        ledger=[r for r in result['ledger'] if r['date']>begin]
        demand=sum(r['sales_qty'] for r in ledger);fulfilled=sum(r['fulfilled_qty'] for r in ledger)
        orders=[o for o in result['orders'] if not o['is_initial'] and
                (o['ordered_on']>=begin if name=='full_period' else o['ordered_on']>begin)]
        metrics[name]=dict(sales_qty=demand,fulfilled_qty=fulfilled,shortage_qty=demand-fulfilled,
            fill_rate=fulfilled/demand if demand else None,mean_closing=sum(r['closing_qty'] for r in ledger)/len(ledger) if ledger else None,
            mean_pending=sum(r['pending_qty'] for r in ledger)/len(ledger) if ledger else None,
            stockout_item_days=sum(r['closing_qty']==0 for r in ledger),order_count=len(orders),ordered_qty=sum(o['ordered_qty'] for o in orders))
    metrics['alarm_item_days']=sum(a['predicted_depletion_date'] is not None and a['date']>=str(start) for a in result['alarms'])
    metrics['alarms_per_day']=metrics['alarm_item_days']/((end-start).days+1);metrics['opportunity']=ceiling
    equal({k:actual[k] for k in metrics},metrics)
    return cases,rows


def verify(folder):
    folder=Path(folder).resolve();manifest=read(folder/'manifest.json');lock=read(folder/'lock.json')
    require(manifest['lock_sha256']==sha(folder/'lock.json'))
    require(lock['application_code_sha256']==code_digest() and lock['runner_sha256']==sha(Path(__file__).with_name('fixed_lot_baseline.py'))
            and lock['verifier_sha256']==sha(__file__) and not lock['S25_run'])
    p=lock['protocol'];equal(p,read(Path(__file__).resolve().parents[1]/'configs/fixed-lot-baseline-v1.json'))
    require(digest(p)==lock['protocol_sha256'] and p['alarm_alpha']==1 and p['no_selection'])
    for name,checksum in manifest['artifacts'].items():
        path=(folder/name).resolve();require(path.is_relative_to(folder) and sha(path)==checksum)
    lots=read(folder/'quantities.json');require(sha(folder/'quantities.json')==lock['quantities_sha256'])
    summaries=read(folder/'summary.json');require(len(summaries)==12)
    count=0
    for split in ('validation','test'):
        pin=p['parents'][split];parent=ROOT/pin['folder']
        for name,checksum in pin['files'].items():require(sha(parent/name.replace('\\','/'))==checksum)
        snapshot=read(parent/'inputs.json.gz')
        if split=='validation':equal(lots,quantity_basis(snapshot,p['quantity_basis']))
        require({r['item_id'] for r in lots}=={i['item_id'] for i in snapshot['catalog']})
        reference=next(s for s in summaries if s['split']==split and s['scenario']=='legacy_reference')
        equal([reference['early_numerator'],reference['event_denominator']],p['legacy_expected'][split])
        for config in p['scenarios']:
            prefix=split+'-'+config['id'];result=read(folder/(prefix+'-replay.json.gz'))
            reconstruct(snapshot,lots,config,result)
            summary=next(s for s in summaries if s['split']==split and s['scenario']==config['id'])
            cases,opportunities=check_summary(result,snapshot,summary)
            equal(read(folder/(prefix+'-cases.json.gz')),cases)
            equal(read(folder/(prefix+'-opportunities.json.gz')),opportunities)
            count+=len(result['ledger'])
            print('Independently verified '+prefix,flush=True)
    proof=dict(status='verified',independent_replay=True,independent_decisions=True,independent_scoring=True,
               manifest_sha256=sha(folder/'manifest.json'),ledger_rows_checked=count,scenarios_checked=10,
               S25_run=False,evidence=lock['evidence'])
    target=folder/'verification.json'
    if target.exists():equal(read(target),proof)
    else:target.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return proof
