"""Independent frozen-flow, event-first scoring and warning-opportunity verification."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import sys

from core.hashes import code_digest, digest

PROTOCOL = Path(__file__).resolve().parents[1]/'configs/inventory-alert-opportunity-audit.json'
RUNNER = Path(__file__).with_name('inventory_alert_opportunity_audit.py')
PROTOCOL_SHA256 = 'caa57e2d16c20cb9013b7603e3001a75b3a9a090ed4df0ae5861b6cc99226530'
LEDGER = ['window_origin','item_id','date','opening_qty','receipts_qty','sales_qty','fulfilled_qty','shortage_qty',
    'closing_qty','forecast_as_of_date','ss','rop','rop_forecast','target_stock','pending_qty','inventory_position',
    'needs_replenishment','recommended_qty']


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


def parent(folder,split,p):
    folder=Path(folder).resolve();pin=p[split]
    for name,field in [('manifest.json','manifest_sha256'),('verification.json','verification_sha256'),
        ('inputs.json.gz','input_sha256'),('results/'+p['config_id']+'.json.gz','result_sha256')]:
        require(sha(folder/name)==pin[field])
    m,proof=read(folder/'manifest.json'),read(folder/'verification.json')
    require(m['split']==split and m['protocol_sha256']==p['parent_protocol_sha256'])
    require(proof['status']=='verified' and proof['independent_replay'] is True
            and proof['evidence_class']=='local_frozen_db' and proof['anchor_scope']=='original_csv_and_readonly_db'
            and proof['manifest_sha256']==pin['manifest_sha256'] and proof['application_code_sha256']==p['application_code_sha256'])
    for name,h in m['artifacts'].items():
        path=(folder/name).resolve();require(path.is_relative_to(folder) and sha(path)==h)
    snapshot=read(folder/'inputs.json.gz');frozen=read(folder/'results'/(p['config_id']+'.json.gz'))
    equal(snapshot['period'],{k:pin[k] for k in ('origin','end','score_start')})
    require(snapshot['split']==split)
    equal(frozen['metrics']['config'],dict(id='D-days-m1-cover7',group='D',mode='days',multiplier=1.0,cover=7,add_ss=False))
    return snapshot,frozen


def reconstruct(snapshot,frozen):
    """Rebuild physical transactions and projection without production arithmetic."""
    start=date.fromisoformat(snapshot['period']['origin']);finish=date.fromisoformat(snapshot['period']['end'])
    ids=sorted(r['item_id'] for r in snapshot['catalog'] if r['first_seen_date']<=str(start))
    daily={(r['date'],r['item_id']):r for r in snapshot['daily']}
    stock={}
    for i in ids:
        history=[daily[(str(start-timedelta(days=h)),i)] for h in range(28)]
        require(all(r['actual_available'] for r in history))
        stock[i]=math.ceil(sum(r['quantity'] for r in history)/28*7)
    initial=[dict(item_id=i,initial_qty=stock[i]) for i in ids]
    equal(sorted(initial,key=lambda r:r['item_id']),sorted([
        dict(item_id=r['item_id'],initial_qty=r['initial_qty']) for r in frozen['initialization']],key=lambda r:r['item_id']))
    require(all(r['added_ss']==0 and r['base_qty']==r['initial_qty'] for r in frozen['initialization']))
    sales=defaultdict(list);receipts=Counter();events=[];transactions=[]
    for r in sorted(snapshot['sales'],key=lambda r:r['sequence']):sales[(r['date'],r['item_id'])].append(r)
    for o in frozen['orders']:receipts[(o['eta'],o['item_id'])]+=o['ordered_qty']
    ledger={(r['date'],r['item_id']):r for r in frozen['ledger']}
    d=start
    while d<=finish:
        for i in ids:
            row=ledger[(str(d),i)];opening=stock[i];arrival=receipts[(str(d),i)];balance=opening+arrival
            sold=filled=missing=0
            for s in sales[(str(d),i)] if d>start else []:
                before=balance;qty=s['quantity'];fulfilled=min(balance,qty);balance-=fulfilled
                sold+=qty;filled+=fulfilled;missing+=qty-fulfilled
                transactions.append(dict(window_origin=str(start),date=str(d),item_id=i,sequence=s['sequence'],
                    quantity=qty,fulfilled_qty=fulfilled,shortage_qty=qty-fulfilled,balance_after=balance))
                if before>0 and balance==0:
                    events.append(dict(window_origin=str(start),date=str(d),item_id=i,sequence=s['sequence'],
                        event_id=f"{start}:{i}:{s['sequence']}"))
            equal([row[k] for k in ('opening_qty','receipts_qty','sales_qty','fulfilled_qty','shortage_qty','closing_qty')],
                  [opening,arrival,sold,filled,missing,balance])
            stock[i]=balance
        d+=timedelta(days=1)
    equal(transactions,frozen['transactions']);equal(events,frozen['events'])
    forecasts={(r['as_of_date'],r['item_id']):r['forecast'] for r in snapshot['forecasts']};alarms=[]
    orders_by_item=defaultdict(list)
    for order in frozen['orders']:orders_by_item[order['item_id']].append(order)
    for row in frozen['ledger']:
        day=date.fromisoformat(row['date']);balance=float(row['closing_qty']);predicted=None
        vector=forecasts[(row['date'],row['item_id'])];require(len(vector)==14)
        require(all(isinstance(q,(int,float)) and math.isfinite(q) and q>=0 for q in vector))
        if balance>0:
            for h,q in enumerate(vector,1):
                arrival=str(day+timedelta(days=h))
                known=sum(o['ordered_qty'] for o in orders_by_item[row['item_id']] if o['eta']==arrival
                    and (o['ordered_on']<row['date'] or o['is_initial']))
                balance=max(0.0,balance+known-float(q))
                if predicted is None and balance==0:predicted=arrival
        alarms.append(dict(date=row['date'],item_id=row['item_id'],origin_on_hand=row['closing_qty'],predicted_depletion_date=predicted))
    expected=dict(initialization=initial,ledger=[{k:r[k] for k in LEDGER} for r in frozen['ledger']],
        transactions=transactions,events=events,alarms=alarms,
        orders=[{k:o[k] for k in ('window_origin','item_id','ordered_on','eta','ordered_qty','is_initial','received')} for o in frozen['orders']])
    for rows in expected.values():rows.sort(key=lambda r:(r.get('date',r.get('ordered_on','')),r['item_id'],r.get('sequence',0),r.get('eta','')))
    return expected


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


class Table(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=None
    def handle_starttag(self,tag,attrs):
        require(tag!='script')
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.cell=''
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self,tag):
        if tag in ('td','th'):self.row.append(self.cell);self.cell=None
        if tag=='tr':self.rows.append(self.row)


def verify(folder):
    folder=Path(folder).resolve();m=read(folder/'manifest.json');p=read(PROTOCOL)
    require(digest(p)==PROTOCOL_SHA256)
    require(m['status']=='calculated_unverified' and m['protocol']==p and m['protocol_sha256']==digest(p))
    require(m['application_code_sha256']==p['application_code_sha256']==code_digest() and m['research_code_sha256']==sha(RUNNER))
    require(m['verifier_code_sha256']==sha(__file__))
    names={split+'-'+name+'.json.gz' for split in ('validation','test') for name in ('replay','cases','opportunities')}|{'metrics.json','report.html'}
    require(set(m['artifacts'])==names)
    for name,h in m['artifacts'].items():require(sha(folder/name)==h)
    summaries=[]
    for split in ('validation','test'):
        source,frozen=parent(m['parents'][split],split,p)
        expected=reconstruct(source,frozen);actual=read(folder/(split+'-replay.json.gz'));equal(actual,expected)
        cases,metrics=score_events(expected,date.fromisoformat(p[split]['score_start']),date.fromisoformat(p[split]['end']))
        equal(cases,frozen['cases']);equal(cases,read(folder/(split+'-cases.json.gz')))
        equal(metrics,{k:frozen['metrics'][k] for k in metrics})
        require((metrics['early_numerator'],metrics['event_denominator'])==(p[split]['early_numerator'],p[split]['event_denominator']))
        rows,opportunity=event_opportunities(expected,cases);equal(rows,read(folder/(split+'-opportunities.json.gz')))
        summaries.append(dict(split=split,baseline=metrics,opportunity=opportunity))
        print('Independently verified '+split,file=sys.stderr,flush=True)
    equal(read(folder/'metrics.json'),summaries)
    table=Table();table.feed((folder/'report.html').read_text(encoding='utf-8'))
    equal(table.rows,[['Split','Baseline early','Episodes','Eligible ceiling','Ceiling rate','45% structurally possible']]+[
        [str(v) for v in (s['split'],s['baseline']['early_numerator'],s['baseline']['event_denominator'],s['opportunity']['ceiling_numerator'],
                         s['opportunity']['ceiling_rate'],s['opportunity']['target_structurally_possible'])] for s in summaries])
    proof=dict(status='verified',independent_physical_flow=True,independent_event_first_scoring=True,independent_opportunity_check=True,
        evidence_class='previously_verified_frozen_inputs_and_results',raw_csv_or_db_reaudit=False,
        manifest_sha256=sha(folder/'manifest.json'),research_code_sha256=sha(RUNNER),verifier_code_sha256=sha(__file__),
        protocol_sha256=digest(p),splits_checked=2)
    path=folder/'verification.json'
    if path.exists():
        previous=read(path);stamp=previous.pop('created_at');equal(previous,proof)
        require(datetime.fromisoformat(stamp).tzinfo is not None);proof['created_at']=stamp
    else:
        proof['created_at']=datetime.now(timezone.utc).isoformat()
        with path.open('x',encoding='utf-8') as stream:json.dump(proof,stream,sort_keys=True,indent=2,allow_nan=False)
    return proof
