"""Replay the fixed days×1 baseline and audit posthoc warning opportunities only."""
import argparse
from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import html
import json
import math
from pathlib import Path
import sys
import uuid

import pandas as pd
from core.hashes import code_digest, digest
from core.serialization import clean_json
from modules.inventory.simulation import pure_window

PROTOCOL = Path(__file__).resolve().parents[1]/"configs/inventory-alert-opportunity-audit.json"
PROTOCOL_SHA256 = 'caa57e2d16c20cb9013b7603e3001a75b3a9a090ed4df0ae5861b6cc99226530'


def unique(pairs):
    result = {}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def invalid_constant(value):raise ValueError('Nonfinite JSON constant')


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data,
                      object_pairs_hook=unique,parse_constant=invalid_constant)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    data = json.dumps(clean_json(value), sort_keys=True, indent=2, allow_nan=False).encode('utf-8')
    Path(path).write_bytes(gzip.compress(data, mtime=0) if str(path).endswith('.gz') else data)


def load_parent(folder, split, protocol):
    folder = Path(folder).resolve(); pin = protocol[split]
    for name, field in [('manifest.json','manifest_sha256'), ('verification.json','verification_sha256'),
                        ('inputs.json.gz','input_sha256'), ('results/'+protocol['config_id']+'.json.gz','result_sha256')]:
        if sha(folder/name) != pin[field]: raise ValueError('Frozen parent hash differs')
    m, proof = read(folder/'manifest.json'), read(folder/'verification.json')
    if (m['split'] != split or m['protocol_sha256'] != protocol['parent_protocol_sha256']
        or proof['status'] != 'verified' or proof['independent_replay'] is not True
        or proof['evidence_class'] != 'local_frozen_db' or proof['anchor_scope'] != 'original_csv_and_readonly_db'
        or proof['manifest_sha256'] != pin['manifest_sha256']
        or proof['application_code_sha256'] != protocol['application_code_sha256']):
        raise ValueError('Parent proof differs')
    for name, checksum in m['artifacts'].items():
        path = (folder/name).resolve()
        if not path.is_relative_to(folder) or sha(path) != checksum: raise ValueError('Parent artifact differs')
    snapshot, result = read(folder/'inputs.json.gz'), read(folder/'results'/(protocol['config_id']+'.json.gz'))
    if snapshot['split'] != split or snapshot['period'] != {k:pin[k] for k in ('origin','end','score_start')}:
        raise ValueError('Parent period differs')
    if result['metrics']['config'] != dict(id='D-days-m1-cover7',group='D',mode='days',multiplier=1.0,cover=7,add_ss=False):
        raise ValueError('Parent policy differs')
    return snapshot, result


def same(actual, expected):
    if isinstance(expected, dict):
        if actual.keys() != expected.keys(): raise ValueError('Fields differ')
        for key in expected: same(actual[key], expected[key])
    elif isinstance(expected, list):
        if len(actual) != len(expected): raise ValueError('Row count differs')
        for a,b in zip(actual,expected,strict=True): same(a,b)
    elif isinstance(expected, float):
        if not isinstance(actual,(int,float)) or not math.isclose(actual,expected,rel_tol=0,abs_tol=1e-8):
            raise ValueError('Numeric value differs')
    elif actual != expected or isinstance(expected,(int,bool)) and type(actual) is not type(expected):
        raise ValueError('Value differs')


def replay(snapshot):
    """Use the existing app replay, preserving source sequence within each UTC day."""
    origin, end = (date.fromisoformat(snapshot['period'][k]) for k in ('origin','end'))
    daily = pd.DataFrame(snapshot['daily']); daily['date'] = pd.to_datetime(daily['date'])
    daily['quantity'] = daily.quantity.where(daily.actual_available)
    matrix = daily.pivot(index='date', columns='item_id', values='quantity')
    forecasts = {(date.fromisoformat(r['as_of_date']),r['item_id']):r['forecast'] for r in snapshot['forecasts']}
    demands = defaultdict(list)
    for r in sorted(snapshot['sales'],key=lambda r:r['sequence']):
        day = date.fromisoformat(r['date'])
        # The frozen audit stores date and source sequence, not original timestamps.
        # End-of-day scoring needs only that day and the original within-item order.
        demands[(day,r['item_id'])].append(dict(event_at=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc),
            source_sequence=r['sequence'],quantity=r['quantity']))
    # Validation's local causal seed has no database policy ID. The app uses
    # this ID for metadata only; negative adapter IDs are never persisted.
    policies = [{**p,'id':p.get('id',-index-1),'safety_mode':'days','rop_mode':'forecast','warning_horizon_days':7}
                for index,p in enumerate(snapshot['policies'])]
    scenario = dict(cover_days=7,safety_multiplier=1,receipts_initial=snapshot['receipts'],receipts_declared=True)
    native = pure_window(matrix,demands,snapshot['catalog'],forecasts,policies,scenario,'policy_replay',origin,end)
    ledger = [{**clean_json(row),**{k:str(row[k]) for k in ('window_origin','date','forecast_as_of_date')}} for row in native['ledger']]
    initial = [dict(item_id=e['item_id'],initial_qty=e['quantity']) for e in native['events'] if e['event_kind']=='initial_stock']
    transactions = [dict(window_origin=str(origin),date=e['event_at'].date().isoformat(),item_id=e['item_id'],
        sequence=e['source_sequence'],**{k:e[k] for k in ('quantity','fulfilled_qty','shortage_qty','balance_after')})
        for e in native['events'] if e['event_kind']=='sale']
    by_day = {(r['date'],r['item_id']):r for r in ledger}; balances = {}
    events = []
    for t in transactions:
        key = (t['date'],t['item_id'])
        before = balances.get(key,by_day[key]['opening_qty']+by_day[key]['receipts_qty'])
        if before > 0 and t['balance_after'] == 0:
            events.append(dict(window_origin=str(origin),date=t['date'],item_id=t['item_id'],sequence=t['sequence'],
                event_id=f"{origin}:{t['item_id']}:{t['sequence']}"))
        balances[key] = t['balance_after']
    alarms = [dict(date=str(a['as_of_date']),item_id=a['item_id'],origin_on_hand=a['explanation']['origin_on_hand'],
        predicted_depletion_date=str(a['predicted_depletion_date']) if a['state']!='already_depleted' and a['predicted_depletion_date'] else None)
        for a in native['alerts'] if a['alert_type']=='depletion']
    orders = [dict(window_origin=str(origin),item_id=o['item_id'],ordered_on=str(o['ordered_on']),eta=str(o['eta']),
        ordered_qty=o['ordered_qty'],is_initial=o['is_initial'],received=o['status']=='received') for o in native['orders']]
    fields = ['window_origin','item_id','date','opening_qty','receipts_qty','sales_qty','fulfilled_qty','shortage_qty',
        'closing_qty','forecast_as_of_date','ss','rop','rop_forecast','target_stock','pending_qty','inventory_position',
        'needs_replenishment','recommended_qty']
    result = dict(initialization=initial,ledger=[{k:r[k] for k in fields} for r in ledger],transactions=transactions,
                  events=events,alarms=alarms,orders=orders)
    for rows in result.values():rows.sort(key=lambda r:(r.get('date',r.get('ordered_on','')),r['item_id'],r.get('sequence',0),r.get('eta','')))
    return result


def compare_replay(result, frozen):
    for name in result:
        expected = frozen[name]
        if name=='initialization': expected = [dict(item_id=r['item_id'],initial_qty=r['initial_qty']) for r in expected]
        expected = [{k:r[k] for k in result[name][0]} for r in expected] if result[name] else expected
        def key(r):return (r.get('date',r.get('ordered_on','')),r['item_id'],r.get('sequence',0),r.get('eta',''))
        same(sorted(result[name],key=key),sorted(expected,key=key))


def score(result, score_start, end):
    matches, evaluations = {}, []
    events, orders = defaultdict(list), defaultdict(list)
    for e in result['events']: events[e['item_id']].append(e)
    for o in result['orders']: orders[o['item_id']].append(o)
    for a in sorted(result['alarms'],key=lambda r:(r['date'],r['item_id'])):
        if a['predicted_depletion_date'] is None: continue
        d = date.fromisoformat(a['date']); limit = min(end,d+timedelta(days=14))
        event = next((e for e in events[a['item_id']] if a['date']<e['date']<=str(limit)),None)
        if event: matches.setdefault(event['event_id'],a)
        intervention = any(not o['is_initial'] and a['date']<=o['ordered_on'] and o['eta']<=str(limit) for o in orders[a['item_id']])
        status = 'TP' if event else 'intervened' if intervention else 'right_censored' if d+timedelta(days=14)>end else 'FP'
        if a['date']>=str(score_start):evaluations.append(status)
    cases = []
    for e in result['events']:
        if e['date']<str(score_start):continue
        a = matches.get(e['event_id']); lead = (date.fromisoformat(e['date'])-date.fromisoformat(a['date'])).days if a else None
        cases.append(dict(**e,alarm_date=a['date'] if a else None,predicted_depletion_date=a['predicted_depletion_date'] if a else None,
                          lead_days=lead,early=lead is not None and lead>=7))
    errors = [abs((date.fromisoformat(e['date'])-date.fromisoformat(e['predicted_depletion_date'])).days) for e in cases if e['alarm_date']]
    n = len(cases); early = sum(e['early'] for e in cases); tp,fp = evaluations.count('TP'),evaluations.count('FP')
    return cases,dict(early_numerator=early,event_denominator=n,early_rate=early/n if n else None,
        precision=tp/(tp+fp) if tp+fp else None,recall=sum(e['alarm_date'] is not None for e in cases)/n if n else None,
        date_mae=sum(errors)/len(errors) if errors else None,alarm_TP=tp,alarm_FP=fp,
        intervened_count=evaluations.count('intervened'),right_censored_count=evaluations.count('right_censored'))


def opportunities(result, cases):
    """Day-first search; actual events are used exclusively for this posthoc bound."""
    events = defaultdict(list)
    for e in result['events']:events[e['item_id']].append(e)
    dates = {i:[e['date'] for e in rows] for i,rows in events.items()}
    available, unblocked, candidates = defaultdict(list),defaultdict(list),defaultdict(list)
    scored = {e['event_id'] for e in cases}
    for row in result['ledger']:
        d = date.fromisoformat(row['date']); item = row['item_id']
        for e in events[item]:
            if e['event_id'] in scored and 7<=(date.fromisoformat(e['date'])-d).days<=14:
                available[e['event_id']].append(row['date'])
        pos = bisect_right(dates.get(item,[]),row['date'])
        if pos==len(events[item]):continue
        e = events[item][pos];lead=(date.fromisoformat(e['date'])-d).days
        if e['event_id'] not in scored or not 7<=lead<=14:continue
        unblocked[e['event_id']].append(row['date'])
        if row['closing_qty']>0:candidates[e['event_id']].append(row['date'])
    rows=[]
    for c in cases:
        k=c['event_id'];days=sorted(candidates[k])
        reason = 'eligible' if days else 'no_decision_day' if not available[k] else 'prior_depletion_blocks_all' if not unblocked[k] else 'no_positive_stock'
        if c['early'] and not days:raise ValueError('Observed early case exceeds structural ceiling')
        rows.append(dict(event_id=k,item_id=c['item_id'],date=c['date'],candidate_dates=days,eligible=bool(days),
                         reason=reason,baseline_early=c['early']))
    n=len(rows);count=sum(r['eligible'] for r in rows);target=(45*n+99)//100
    return rows,dict(event_denominator=n,baseline_early_numerator=sum(r['baseline_early'] for r in rows),
        ceiling_numerator=count,ceiling_rate=count/n if n else None,target_numerator=target,
        needed_additional_early=target-sum(r['baseline_early'] for r in rows) if n else None,
        additional_opportunities=count-sum(r['baseline_early'] for r in rows),target_structurally_possible=count>=target if n else None,
        reason_counts={k:sum(r['reason']==k for r in rows) for k in ('eligible','no_decision_day','prior_depletion_blocks_all','no_positive_stock')},
        scope='posthoc_structural_upper_bound_not_a_forecast')


def audit(validation, test, output_root):
    p=read(PROTOCOL)
    if digest(p)!=PROTOCOL_SHA256:raise ValueError('Audit protocol changed')
    if code_digest()!=p['application_code_sha256']:raise ValueError('Application arithmetic changed')
    folder=Path(output_root)/(p['id']+'-'+str(uuid.uuid4()));folder.mkdir(parents=True,exist_ok=False)
    summaries=[];parents={}
    for split,path in [('validation',validation),('test',test)]:
        source,frozen=load_parent(path,split,p);result=replay(source);compare_replay(result,frozen)
        cases,metrics=score(result,date.fromisoformat(p[split]['score_start']),date.fromisoformat(p[split]['end']))
        same(cases,frozen['cases'])
        same(metrics,{k:frozen['metrics'][k] for k in metrics})
        if (metrics['early_numerator'],metrics['event_denominator'])!=(p[split]['early_numerator'],p[split]['event_denominator']):
            raise ValueError('Baseline counts differ')
        rows,ceiling=opportunities(result,cases)
        write(folder/(split+'-replay.json.gz'),result);write(folder/(split+'-cases.json.gz'),cases)
        write(folder/(split+'-opportunities.json.gz'),rows)
        summaries.append(dict(split=split,baseline=metrics,opportunity=ceiling))
        parents[split]=str(Path(path).resolve())
        print('Replayed and audited '+split,file=sys.stderr,flush=True)
    write(folder/'metrics.json',summaries)
    body=''.join('<tr>'+''.join('<td>'+html.escape(str(value))+'</td>' for value in [s['split'],s['baseline']['early_numerator'],
        s['baseline']['event_denominator'],s['opportunity']['ceiling_numerator'],s['opportunity']['ceiling_rate'],s['opportunity']['target_structurally_possible']])+'</tr>' for s in summaries)
    (folder/'report.html').write_text("<!doctype html><meta charset='utf-8'><h1>Opportunity audit — independent verification pending</h1>"
        "<p>Posthoc structural bound only; not a forecast, not an achieved early rate. Same days×1 inventory path. Retrospective; no alpha experiments or R07/T14 acceptance.</p>"
        "<table border='1'><tr><th>Split</th><th>Baseline early</th><th>Episodes</th><th>Eligible ceiling</th><th>Ceiling rate</th><th>45% structurally possible</th></tr>"+body+'</table>',encoding='utf-8')
    write(folder/'manifest.json',dict(status='calculated_unverified',protocol=p,protocol_sha256=digest(p),parents=parents,
        application_code_sha256=code_digest(),research_code_sha256=sha(__file__),
        verifier_code_sha256=sha(Path(__file__).with_name('inventory_alert_opportunity_verification.py')),
        artifacts={f.name:sha(f) for f in folder.iterdir() if f.is_file()}))
    return folder


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    run=commands.add_parser('audit');run.add_argument('--validation-run',type=Path,required=True);run.add_argument('--test-run',type=Path,required=True)
    run.add_argument('--output-root',type=Path,default=Path('outputs/research'))
    check=commands.add_parser('verify');check.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='audit':print(json.dumps(dict(output=str(audit(args.validation_run,args.test_run,args.output_root).resolve()),status='calculated_unverified')))
        else:
            from web.backend.research.inventory_alert_opportunity_verification import verify
            print(json.dumps(verify(args.run_dir)))
        return 0
    except Exception as exc:
        import traceback
        diagnostic = (args.output_root if args.command=='audit' else args.run_dir.parent)
        diagnostic.mkdir(parents=True,exist_ok=True)
        (diagnostic/('opportunity-failure-'+str(uuid.uuid4())+'.private.log')).write_text(traceback.format_exc(),encoding='utf-8')
        print(json.dumps(dict(status='failed',error_type=type(exc).__name__)));return 1

if __name__=='__main__':raise SystemExit(main())
