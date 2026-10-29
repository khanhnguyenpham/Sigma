"""CHG-077: original point-forecast alarms on newly replayed fixed-lot scenarios."""
import argparse
from collections import defaultdict, Counter
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
import copy, csv, gzip, hashlib, html, json, math, statistics, sys, uuid
from pathlib import Path
import pandas as pd
from contextlib import ExitStack
from unittest.mock import patch
from core.errors import DomainError
from core.hashes import code_digest, digest
from core.serialization import clean_json
from modules.inventory.service import history_quantities
from modules.inventory.simulation import pure_window

PROTOCOL = Path(__file__).resolve().parents[1]/"configs/fixed-lot-baseline-v1.json"
ROOT = Path(__file__).resolve().parents[3]

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

def replay(snapshot, config, indexed=True):
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
    scenario = dict(cover_days=config["cover"],safety_multiplier=config["multiplier"],receipts_initial=snapshot['receipts'],receipts_declared=True)
    # This CLI runs alone: replace only accessors within the context, then restore
    # them. Arithmetic stays in pure_window; no app source or DB is changed.
    observed = {(date.fromisoformat(r['date']),r['item_id']):r['quantity'] if r['actual_available'] else None
                for r in snapshot['daily']}
    by_item = defaultdict(list)
    for p in policies: by_item[p['item_id']].append(p)
    def indexed_history(_matrix, item, decision, days):
        values=[observed.get((decision-timedelta(days=h),item)) for h in range(days-1,-1,-1)]
        return history_quantities(values,days)
    def indexed_policy(_policies, item, decision):
        active=[p for p in by_item[item] if p['effective_from']<=str(decision)
                and (p['effective_to'] is None or str(decision)<p['effective_to'])]
        if len(active)!=1: raise DomainError('missing_partner_config','Expected one frozen policy',item_id=item)
        return active[0]
    with ExitStack() as stack:
        if indexed:
            stack.enter_context(patch('modules.inventory.simulation.history_at',indexed_history))
            stack.enter_context(patch('modules.inventory.simulation.policy_at',indexed_policy))
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


def parent(protocol, split):
    pin = protocol['parents'][split]
    folder = ROOT / pin['folder']
    for name, checksum in pin['files'].items():
        if sha(folder / name.replace('\\', '/')) != checksum:
            raise ValueError('Frozen parent differs')
    proof = read(folder/'verification.json')
    if proof['status'] != 'verified' or not proof['independent_replay']:
        raise ValueError('Parent is not independently verified')
    manifest = read(folder/'manifest.json')
    for name, checksum in manifest['artifacts'].items():
        path = (folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or sha(path) != checksum:
            raise ValueError('Parent artifact differs')
    return read(folder/'inputs.json.gz'), read(folder/'results/D-days-m1-cover7.json.gz')


def quantities(snapshot, specification):
    start, end = specification['start'], specification['end']
    items = snapshot['catalog']
    observed = {(r['date'], r['item_id']): r for r in snapshot['daily'] if start <= r['date'] <= end}
    days = pd.date_range(start, end)
    totals = {}
    for item in items:
        rows = [observed[(str(day.date()), item['item_id'])] for day in days]
        if not all(r['actual_available'] is True and type(r['quantity']) is int and r['quantity'] >= 0 for r in rows):
            raise ValueError('Quantity basis must be fully observed')
        totals[item['item_id']] = sum(r['quantity'] for r in rows)
    thresholds = {kind: statistics.median(totals[i['item_id']] for i in items if i['product_type'] == kind)
                  for kind in specification['lots']}
    result = []
    for item in sorted(items, key=lambda i: i['item_id']):
        kind = item['product_type']; total = totals[item['item_id']]
        level = 'high' if total > thresholds[kind] else 'low'
        result.append(dict(item_id=item['item_id'], product_type=kind, quantity_28d=total,
                           threshold=thresholds[kind], level=level, fixed_order_qty=specification['lots'][kind][level]))
    return result


def fixed_snapshot(snapshot, lots):
    lookup = {r['item_id']: r['fixed_order_qty'] for r in lots}
    if set(lookup) != {i['item_id'] for i in snapshot['catalog']}:
        raise ValueError('Fixed quantity cohort differs')
    return {**snapshot, 'policies': [{**p, 'moq': None, 'fixed_order_qty': lookup[p['item_id']]}
                                    for p in snapshot['policies']]}


def summarize(result, snapshot):
    start, end = (date.fromisoformat(snapshot['period'][k]) for k in ('score_start', 'end'))
    cases, metrics = score(result, start, end)
    opportunity_rows, opportunity = opportunities(result, cases)
    for name, begin in [('full_period', snapshot['period']['origin']), ('scored_period', str(start - timedelta(days=1)))]:
        rows = [r for r in result['ledger'] if r['date'] > begin]
        sales = sum(r['sales_qty'] for r in rows); filled = sum(r['fulfilled_qty'] for r in rows)
        orders = [r for r in result['orders'] if not r['is_initial'] and
                  (r['ordered_on'] >= begin if name == 'full_period' else r['ordered_on'] > begin)]
        metrics[name] = dict(sales_qty=sales, fulfilled_qty=filled, shortage_qty=sales-filled,
                             fill_rate=filled/sales if sales else None,
                             mean_closing=sum(r['closing_qty'] for r in rows)/len(rows) if rows else None,
                             mean_pending=sum(r['pending_qty'] for r in rows)/len(rows) if rows else None,
                             stockout_item_days=sum(r['closing_qty'] == 0 for r in rows),
                             order_count=len(orders), ordered_qty=sum(r['ordered_qty'] for r in orders))
    metrics['alarm_item_days'] = sum(r['date'] >= str(start) and r['predicted_depletion_date'] is not None for r in result['alarms'])
    metrics['alarms_per_day'] = metrics['alarm_item_days'] / ((end-start).days+1)
    metrics['opportunity'] = opportunity
    return cases, metrics, opportunity_rows


def run(output_root):
    protocol = read(PROTOCOL)
    if protocol['alarm_alpha'] != 1 or not protocol['no_selection']:
        raise ValueError('This phase only runs the original alarm approach')
    validation, _ = parent(protocol, 'validation')
    lots = quantities(validation, protocol['quantity_basis'])
    del validation
    folder = Path(output_root)/(protocol['id']+'-'+str(uuid.uuid4()))
    folder.mkdir(parents=True, exist_ok=False)
    write(folder/'quantities.json', lots)
    lock = dict(protocol=protocol, protocol_sha256=digest(protocol), application_code_sha256=code_digest(),
                runner_sha256=sha(__file__), verifier_sha256=sha(Path(__file__).with_name('fixed_lot_verification.py')),
                quantities_sha256=sha(folder/'quantities.json'), created_at=datetime.now(timezone.utc).isoformat(),
                evidence='derived_from_verified_frozen_inputs_not_a_new_raw_or_DB_audit', S25_run=False)
    write(folder/'lock.json', lock)  # Freeze before any new replay result.
    summaries=[]
    for split in ('validation', 'test'):
        snapshot, old = parent(protocol, split)
        legacy = replay(snapshot, protocol['scenarios'][0])
        for name in legacy:
            expected = old[name]
            if name == 'initialization':
                expected = [dict(item_id=r['item_id'], initial_qty=r['initial_qty']) for r in expected]
            expected = [{k:r[k] for k in legacy[name][0]} for r in expected] if legacy[name] else expected
            key = lambda r: (r.get('date',r.get('ordered_on','')),r['item_id'],r.get('sequence',0),r.get('eta',''))
            same(legacy[name], sorted(expected,key=key))
        cases, metrics, _ = summarize(legacy, snapshot)
        same([metrics['early_numerator'],metrics['event_denominator']], protocol['legacy_expected'][split])
        summaries.append(dict(split=split, scenario='legacy_reference', **metrics))
        write(folder/(split+'-legacy-reference.json'), metrics)
        del legacy, old, cases
        fixed = fixed_snapshot(snapshot, lots)
        for config in protocol['scenarios']:
            print(split+' '+config['id']+' starting', file=sys.stderr, flush=True)
            result = replay(fixed, config)
            cases, metrics, opportunity_rows = summarize(result, fixed)
            prefix = split+'-'+config['id']
            write(folder/(prefix+'-replay.json.gz'), result)
            write(folder/(prefix+'-cases.json.gz'), cases)
            write(folder/(prefix+'-opportunities.json.gz'), opportunity_rows)
            summaries.append(dict(split=split, scenario=config['id'], **metrics))
            write(folder/'summary.json', summaries)
            print(prefix+' '+str(metrics['early_numerator'])+'/'+str(metrics['event_denominator']), file=sys.stderr, flush=True)
            del result, cases, opportunity_rows
        del snapshot, fixed
    columns=['split','scenario','early_numerator','event_denominator','early_rate','precision','recall','alarm_FP','alarm_TP','alarms_per_day']
    with (folder/'summary.csv').open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        writer.writerows({k:r[k] for k in columns} for r in summaries)
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in columns)+'</tr>' for r in summaries)
    (folder/'report.html').write_text("<!doctype html><meta charset='utf-8'><h1>CHG-077: original alarms, fixed lots</h1>"
        '<p>Simulated quantities; retrospective. Scenario paths and episode denominators differ. No S25, refit, app DB write or R07/T14 acceptance. Verification receipt required.</p>'
        '<table border="1"><tr>'+''.join('<th>'+k+'</th>' for k in columns)+'</tr>'+rows+'</table>',encoding='utf-8')
    write(folder/'manifest.json', dict(lock_sha256=sha(folder/'lock.json'), status='calculated_unverified',
                                     artifacts={p.name:sha(p) for p in folder.iterdir() if p.is_file()}))
    return folder


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run','verify'])
    parser.add_argument('--output-root', type=Path, default=ROOT/'outputs/research/fixed-lot-baseline')
    parser.add_argument('--run-dir', type=Path)
    args=parser.parse_args()
    if args.command=='run': print(json.dumps(dict(output=str(run(args.output_root).resolve()))))
    else:
        from web.backend.research.fixed_lot_verification import verify
        print(json.dumps(verify(args.run_dir)))


if __name__=='__main__': main()
