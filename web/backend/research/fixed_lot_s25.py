"""Locked C00/S25 alarm comparison on the verified CHG-077 fixed-lot path."""
import argparse
from collections import defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import uuid

from core.hashes import code_digest, digest
from modules.alerts.service import project
from web.backend.research import fixed_lot_baseline as base
from web.backend.research import fixed_lot_verification as independent

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = Path(__file__).resolve().parents[1] / 'configs/fixed-lot-s25-v1.json'
PHYSICAL = ('initialization', 'ledger', 'transactions', 'orders', 'events')


def alarms(source, frozen, alpha, effective):
    """Only prefix forecast, closing stock and pre-decision receipts are inputs."""
    forecasts = {(r['as_of_date'], r['item_id']): r['forecast'] for r in source['forecasts']}
    orders = defaultdict(list)
    for order in frozen['orders']:
        orders[order['item_id']].append(order)
    result = []
    for row in frozen['ledger']:
        day = date.fromisoformat(row['date'])
        factor = alpha if row['date'] >= effective else 1
        vector = [float(q) * factor for q in forecasts[(row['date'], row['item_id'])]]
        receipts = defaultdict(int)
        for order in orders[row['item_id']]:
            arrival = date.fromisoformat(order['eta'])
            if day < arrival <= day + timedelta(days=14) and (order['is_initial'] or order['ordered_on'] < row['date']):
                receipts[arrival] += order['ordered_qty']
        path = project(day, row['closing_qty'], vector, receipts)
        prediction = path['predicted_depletion_date'] if path['state'] != 'already_depleted' else None
        result.append(dict(date=row['date'], item_id=row['item_id'], origin_on_hand=row['closing_qty'],
                           predicted_depletion_date=str(prediction) if prediction else None))
    return sorted(result, key=lambda r: (r['date'], r['item_id']))


def reference_alarms(source, frozen, candidate, effective):
    """Scalar projection, without production projection/receipt/transform helpers."""
    vectors = {(r['as_of_date'], r['item_id']): r['forecast'] for r in source['forecasts']}
    by_item = defaultdict(list)
    for order in frozen['orders']:
        by_item[order['item_id']].append(order)
    result = []
    for row in frozen['ledger']:
        origin = date.fromisoformat(row['date']); balance = float(row['closing_qty']); predicted = None
        vector = vectors[(row['date'], row['item_id'])]
        independent.require(len(vector) == 14)
        for h in range(1, 15):
            target = str(origin + timedelta(days=h))
            incoming = sum(o['ordered_qty'] for o in by_item[row['item_id']]
                           if o['eta'] == target and (o['is_initial'] or o['ordered_on'] < row['date']))
            demand = float(vector[h-1])
            if candidate == 'S25' and row['date'] >= effective:
                demand = demand * 5 / 4
            balance = max(0., balance + incoming - demand)
            if balance == 0 and predicted is None:
                predicted = target
        if row['closing_qty'] == 0:
            predicted = None
        result.append(dict(date=row['date'], item_id=row['item_id'], origin_on_hand=row['closing_qty'],
                           predicted_depletion_date=predicted))
    return sorted(result, key=lambda r: (r['date'], r['item_id']))


def paired(cases, baseline_cases):
    baseline = {r['event_id']: r for r in baseline_cases}
    independent.require(len(baseline) == len(cases) and set(baseline) == {r['event_id'] for r in cases})
    independent.require(all((r['item_id'], r['date'], r['sequence']) ==
                            (baseline[r['event_id']]['item_id'], baseline[r['event_id']]['date'], baseline[r['event_id']]['sequence']) for r in cases))
    return dict(gained_early=sum(r['early'] and not baseline[r['event_id']]['early'] for r in cases),
                lost_early=sum(not r['early'] and baseline[r['event_id']]['early'] for r in cases))


def load_parent(p):
    folder = ROOT / p['baseline_folder']
    for name, checksum in p['baseline_files'].items():
        independent.require(base.sha(folder/name) == checksum)
    manifest = base.read(folder/'manifest.json'); proof = base.read(folder/'verification.json')
    independent.require(proof['status'] == 'verified' and proof['independent_decisions'] and
                        proof['manifest_sha256'] == base.sha(folder/'manifest.json'))
    for name, checksum in manifest['artifacts'].items():
        path = (folder/name).resolve()
        independent.require(path.is_relative_to(folder.resolve()) and base.sha(path) == checksum)
    return folder, base.read(folder/'lock.json')['protocol']


def run(output_root):
    p = base.read(PROTOCOL)
    independent.require(p['candidates'] == {'C00': 1, 'S25': 1.25} and not p['selection'] and not p['application_change'])
    parent, original_protocol = load_parent(p)
    folder = Path(output_root)/(p['id']+'-'+str(uuid.uuid4())); folder.mkdir(parents=True, exist_ok=False)
    base.write(folder/'lock.json', dict(protocol=p, protocol_sha256=digest(p), code_sha256=base.sha(__file__),
        application_code_sha256=code_digest(), base_code_sha256=base.sha(base.__file__),
        verifier_code_sha256=base.sha(independent.__file__), created_at=datetime.now(timezone.utc).isoformat(),
        no_reselection=True, inventory_replayed=False, evidence='verified_frozen_inputs_not_new_raw_DB_audit'))
    summaries = []; legacy = []; state = {}
    for split in ('validation', 'test'):
        source, old = base.parent(original_protocol, split)
        frozen = base.read(parent/(split+'-base-replay.json.gz'))
        baseline_cases = base.read(parent/(split+'-base-cases.json.gz'))
        state[split] = {k: digest(frozen[k]) for k in PHYSICAL}
        for candidate, alpha in p['candidates'].items():
            old_alarms = alarms(source, old, alpha, p['effective_from'])
            old_cases, old_metrics = base.score({**old, 'alarms': old_alarms},
                date.fromisoformat(source['period']['score_start']), date.fromisoformat(source['period']['end']))
            independent.equal([old_metrics['early_numerator'], old_metrics['event_denominator']], p['legacy_expected'][split][candidate])
            legacy.append(dict(split=split, candidate=candidate, **old_metrics))
            projected = alarms(source, frozen, alpha, p['effective_from'])
            if candidate == 'C00':
                independent.equal(projected, frozen['alarms'])
            result = {**frozen, 'alarms': projected}
            cases, metrics, _ = base.summarize(result, source)
            if candidate == 'C00':
                independent.equal([metrics['early_numerator'], metrics['event_denominator']], p['fixed_expected'][split])
            independent.equal(state[split], {k: digest(frozen[k]) for k in PHYSICAL})
            summary = dict(split=split, candidate=candidate, **metrics, **paired(cases, baseline_cases))
            summary['target_numerator'] = (45*metrics['event_denominator']+99)//100
            summary['working_target_met'] = metrics['event_denominator'] > 0 and metrics['early_numerator'] >= summary['target_numerator']
            base.write(folder/(split+'-'+candidate+'-alarms.json.gz'), projected)
            base.write(folder/(split+'-'+candidate+'-cases.json.gz'), cases)
            summaries.append(summary)
            print(split+' '+candidate+' '+str(metrics['early_numerator'])+'/'+str(metrics['event_denominator']), flush=True)
        independent.equal(state[split], {k: digest(frozen[k]) for k in PHYSICAL})
    base.write(folder/'summary.json', summaries); base.write(folder/'legacy-reproduction.json', legacy)
    base.write(folder/'physical-hashes.json', state)
    columns = ['split', 'candidate', 'early_numerator', 'event_denominator', 'early_rate', 'precision', 'recall',
               'alarm_TP', 'alarm_FP', 'alarms_per_day', 'gained_early', 'lost_early', 'target_numerator', 'working_target_met']
    with (folder/'summary.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        writer.writerows({k: r[k] for k in columns} for r in summaries)
    base.write(folder/'manifest.json', dict(status='calculated_unverified', lock_sha256=base.sha(folder/'lock.json'),
        artifacts={f.name: base.sha(f) for f in folder.iterdir() if f.is_file()}))
    return folder


def verify(folder):
    folder = Path(folder); m = base.read(folder/'manifest.json'); lock = base.read(folder/'lock.json'); p = base.read(PROTOCOL)
    independent.require(m['lock_sha256'] == base.sha(folder/'lock.json') and lock['protocol'] == p and lock['protocol_sha256'] == digest(p))
    independent.require(lock['code_sha256'] == base.sha(__file__) and lock['application_code_sha256'] == code_digest() and
                        lock['base_code_sha256'] == base.sha(base.__file__) and lock['verifier_code_sha256'] == base.sha(independent.__file__))
    for name, checksum in m['artifacts'].items():
        path = (folder/name).resolve(); independent.require(path.is_relative_to(folder.resolve()) and base.sha(path) == checksum)
    parent, original_protocol = load_parent(p); summaries = base.read(folder/'summary.json')
    independent.require(len(summaries) == 4)
    state = base.read(folder/'physical-hashes.json'); checked = 0
    for split in ('validation', 'test'):
        source, old = base.parent(original_protocol, split)
        frozen = base.read(parent/(split+'-base-replay.json.gz'))
        baseline_cases = base.read(parent/(split+'-base-cases.json.gz'))
        independent.equal(state[split], {k: digest(frozen[k]) for k in PHYSICAL})
        for candidate in ('C00', 'S25'):
            legacy = reference_alarms(source, old, candidate, p['effective_from'])
            _, historical = independent.score_events({**old, 'alarms': legacy},
                date.fromisoformat(source['period']['score_start']), date.fromisoformat(source['period']['end']))
            independent.equal(historical, {k: r[k] for r in base.read(folder/'legacy-reproduction.json')
                                           if r['split'] == split and r['candidate'] == candidate for k in historical})
            independent.equal([historical['early_numerator'], historical['event_denominator']], p['legacy_expected'][split][candidate])
            expected = reference_alarms(source, frozen, candidate, p['effective_from'])
            independent.equal(base.read(folder/(split+'-'+candidate+'-alarms.json.gz')), expected)
            summary = next(r for r in summaries if r['split'] == split and r['candidate'] == candidate)
            cases, _ = independent.check_summary({**frozen, 'alarms': expected}, source, summary)
            independent.equal(base.read(folder/(split+'-'+candidate+'-cases.json.gz')), cases)
            independent.equal({k: summary[k] for k in ('gained_early', 'lost_early')}, paired(cases, baseline_cases))
            target = (45*len(cases)+99)//100
            independent.require(summary['target_numerator'] == target and summary['working_target_met'] == (bool(cases) and sum(c['early'] for c in cases) >= target))
            checked += len(expected)
        print('Independently verified '+split, flush=True)
    proof = dict(status='verified', independent_scalar_projection=True, independent_event_scoring=True,
        same_physical_path=True, paired_cohort=True, legacy_S25_reproduced=True, alarm_rows_checked=checked,
        manifest_sha256=base.sha(folder/'manifest.json'), no_reselection=True, application_change=False)
    target = folder/'verification.json'
    if target.exists(): independent.equal(base.read(target), proof)
    else: base.write(target, proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'verify'])
    parser.add_argument('--output-root', type=Path, default=ROOT/'outputs/research/fixed-lot-s25')
    parser.add_argument('--run-dir', type=Path)
    args = parser.parse_args()
    if args.command == 'run': print(json.dumps(dict(output=str(run(args.output_root).resolve()))))
    else: print(json.dumps(verify(args.run_dir)))


if __name__ == '__main__': main()
