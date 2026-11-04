"""Replay C00 with forecast + SS and a configured ROP floor; never access a DB."""
import argparse
from datetime import date, datetime, timezone
from pathlib import Path

from core.hashes import code_digest
from web.backend.research import fixed_lot_baseline as base
from web.backend.research import fixed_lot_verification as independent

PROFILE = "forecast_floor_days_ss_v1"


def evaluate(source, policies, scenario):
    """Apply the frozen policy retrospectively, with no model selection or refit."""
    assert {p['item_id'] for p in policies} == {i['item_id'] for i in source['catalog']}
    assert len(policies) == len(source['catalog'])
    adapted = {**source, 'policies': [dict(p, safety_mode='days', rop_mode='forecast',
        effective_from=source['period']['origin'], effective_to=None) for p in policies]}
    result = base.replay(adapted, scenario)
    # Separate scalar arithmetic re-creates orders, stock, depletion and alarms.
    independent.reconstruct(adapted, policies, scenario, result)
    begin, end = (date.fromisoformat(source['period'][k]) for k in ('score_start', 'end'))
    cases, metrics = base.score(result, begin, end)
    other_cases, other_metrics = independent.score_events(result, begin, end)
    independent.equal(cases, other_cases)
    independent.equal(metrics, other_metrics)
    return result, cases, metrics


def run(folder, policy_snapshot):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    assert not (folder / 'lock.json').exists(), 'Do not overwrite an existing evaluation'
    policy_snapshot = Path(policy_snapshot)
    prior = policy_snapshot.parent
    proof = base.read(prior / 'verification.json')
    assert proof['status'] == 'verified'
    preserved = {p.name: base.sha(p) for p in prior.iterdir() if p.is_file()}
    for name, checksum in proof['manifest_artifacts'].items():
        assert base.sha(prior / name) == checksum, 'Historical evidence differs'
    old_lock = base.read(prior / 'lock.json')
    assert base.sha(policy_snapshot) == old_lock['policy_snapshot_sha256']
    assert base.sha(base.PROTOCOL) == old_lock['source_protocol_sha256']
    protocol = base.read(base.PROTOCOL)
    source, _ = base.parent(protocol, 'test')
    policies = base.read(policy_snapshot)['policies']
    assert len(policies) == 920
    assert all(p['moq'] is None and p['fixed_order_qty'] > 0 and p['safety_mode'] == 'days' for p in policies)
    scenario = old_lock['scenario']
    lock = dict(profile=PROFILE, formula='max(ceil(sum(f1..f7) + SS), configured_rop_floor)',
        policy_snapshot_sha256=base.sha(policy_snapshot), source_protocol_sha256=base.sha(base.PROTOCOL),
        runner_sha256=base.sha(__file__), application_code_sha256=code_digest(), scenario=scenario,
        period=source['period'], historical_files=preserved, retrospective=True, refit=False,
        selection=False, database_access=False)
    base.write(folder / 'lock.json', lock)
    print('Frozen test inputs verified; replaying C00 with forecast-floor ROP', flush=True)
    result, cases, metrics = evaluate(source, policies, scenario)
    print('Physical replay and both scorers independently verified', flush=True)
    base.write(folder / 'test-C00-physical.json.gz', result)
    base.write(folder / 'test-C00-cases.json.gz', cases)
    base.write(folder / 'metrics.json', metrics)
    assert preserved == {p.name: base.sha(p) for p in prior.iterdir() if p.is_file()}
    proof = dict(status='verified', profile=PROFILE, independently_reconstructed=True,
        independently_scored=True, database_access=False, refit=False,
        lock_sha256=base.sha(folder / 'lock.json'), metrics=metrics,
        artifacts={p.name: base.sha(p) for p in folder.iterdir() if p.is_file()})
    base.write(folder / 'verification.json', proof)
    report = dict(id='c00-forecast-floor-test-2025', candidate='C00', status='verified',
        inventory_policy_profile=PROFILE, rop_formula=lock['formula'],
        evaluated_at=datetime.now(timezone.utc).isoformat(), score_start=source['period']['score_start'],
        score_end=source['period']['end'], warmup_days=28, horizon_days=14, minimum_lead_days=7,
        policy_count=len(policies), cover_days=scenario['cover'], safety_multiplier=scenario['multiplier'],
        lead_time_days=7, early_numerator=metrics['early_numerator'], event_denominator=metrics['event_denominator'],
        early_rate=metrics['early_rate'], precision=metrics['precision'], recall=metrics['recall'],
        alarm_tp=metrics['alarm_TP'], alarm_fp=metrics['alarm_FP'], date_mae=metrics['date_mae'],
        matched_events=sum(c['alarm_date'] is not None for c in cases),
        policy_snapshot_sha256=lock['policy_snapshot_sha256'], reproduction_sha256=base.sha(folder / 'verification.json'),
        application_code_sha256=lock['application_code_sha256'])
    base.write(folder / 'public-report.json', report)
    print({k: report[k] for k in ('status','early_numerator','event_denominator','early_rate','precision','recall','date_mae')}, flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--policy-snapshot', required=True, type=Path)
    args = parser.parse_args()
    run(args.run_dir, args.policy_snapshot)
