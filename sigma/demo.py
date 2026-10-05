"""Build a separate, fully verified synthetic bundle for the five-page product."""
import argparse
import copy
import json
import re

from src.common import ROOT, read_config, sha256, validate_run, write_json
from run import execute as execute_daily
from sigma.forecasting.weekly import run_weekly
from sigma.delivery.customer import execute as execute_delivery
from sigma.inventory.snapshot import execute as execute_stock
from sigma.inventory.policy import execute as execute_policy
from sigma.verification.weekly import verify as verify_weekly
from sigma.verification.delivery import verify as verify_delivery
from sigma.verification.weekly_inventory import verify as verify_stock
from sigma.verification.weekly_policy import verify as verify_policy
from sigma.analysis.comparison import compare


def create_demo(prefix):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', prefix):
        raise ValueError('Synthetic bundle prefix must be a new local run identifier')
    names = {part: prefix + '_' + part for part in ['daily', 'weekly', 'delivery', 'stock', 'policy']}
    setup = ROOT / 'outputs' / (prefix + '_bundle')
    setup.mkdir(exist_ok=False)
    base_path = setup / 'base.json'
    cfg = copy.deepcopy(read_config('config.original.json'))
    cfg['source'] = 'outputs/' + names['daily'] + '/synthetic_orders.csv'
    write_json(base_path, cfg)
    execute_daily(config=str(base_path), run_id=names['daily'], demo=True, baseline_only=True)
    daily = validate_run(ROOT / 'outputs' / names['daily'])
    if daily['source_kind'] != 'generated_synthetic':
        raise ValueError('Demo requires a generated synthetic parent')
    write_json(base_path, daily['config'])
    settings = json.loads((ROOT / 'config.weekly.json').read_text(encoding='utf-8'))
    settings.update(weekly_version='generated-synthetic-five-method-demo-v1',
        base_config=base_path.relative_to(ROOT).as_posix(), n_estimators=20, min_child_samples=20)
    settings['models'] = {
        'week_ma28': {'kind': 'mean', 'window': 28},
        'linear': {'kind': 'linear_week', 'objective': 'regression_l1', 'units': 'ratio', 'harmonics': 2, 'alpha': .01},
        'annual': {'kind': 'lgbm', 'objective': 'regression_l1', 'units': 'ratio', 'annual_features': True, 'leaves': 7},
        'calibrated': {'kind': 'calibrated', 'parent': 'annual', 'history_days': 28, 'prior_weeks': 0},
        'combined': {'kind': 'calibrated_blend', 'parent': 'annual', 'components': ['annual', 'linear'],
            'history_days': 28, 'prior_weeks': 0, 'weights': [.5, .5], 'calibrated_reference': 'calibrated'}}
    settings['demo_note'] = 'Three generated routes; demonstrates integration, never certifies the provided snapshot or its top10 accuracy'
    weekly_path = setup / 'weekly.json'
    write_json(weekly_path, settings)
    run_weekly(names['weekly'], weekly_path.relative_to(ROOT).as_posix())
    bundle = json.loads((ROOT / 'config.delivery.json').read_text(encoding='utf-8'))
    bundle.update(base_config=base_path.relative_to(ROOT).as_posix(), weekly_run=names['weekly'],
        daily_run=names['daily'], source_description='generated_synthetic_demo')
    bundle_path = setup / 'delivery.json'
    write_json(bundle_path, bundle)
    execute_delivery(names['delivery'], str(bundle_path))
    execute_policy(names['policy'], names['weekly'], names['daily'])
    execute_stock(names['stock'], names['weekly'], names['daily'], names['policy'])
    verify_weekly(names['weekly'], prefix + '_verify_weekly', names['daily'])
    verify_delivery(names['delivery'], prefix + '_verify_delivery')
    verify_stock(names['stock'], prefix + '_verify_stock')
    verify_policy(names['policy'], prefix + '_verify_policy')
    compare(names['weekly'], names['daily'], names['policy'], prefix + '_comparison')
    source = ROOT / daily['source_relative_path']
    if sha256(source) != daily['source_sha256']:
        raise ValueError('Synthetic source changed during integration')
    result = {'status': 'verified', 'kind': 'generated_synthetic_product_bundle', 'runs': names,
        'delivery_config': bundle_path.relative_to(ROOT).as_posix(),
        'generated_source_sha256': sha256(source), 'source_generated_by_this_program': True,
        'supplied_snapshot_read_or_modified': False, 'certifies_supplied_snapshot_accuracy': False,
        'project_fully_accepted': False}
    write_json(setup / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, help='Fresh prefix; existing outputs are never overwritten')
    args = parser.parse_args()
    create_demo(args.prefix)
