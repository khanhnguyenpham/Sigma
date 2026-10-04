"""Local, validation-only context experiment; never modifies a source run."""
from pathlib import Path
import argparse
import json
import pandas as pd
from src.common import ROOT, ROUTE, read_config, sha256, code_hash, write_json, write_csv
from src.context_models import CONTEXT_FEATURES, CONTEXT_SPECS, context_validation
from src.evaluation import metric_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', default='sigma_release_v4')
    parser.add_argument('--experiment-id', default='context_validation_v1')
    args = parser.parse_args()
    root = ROOT / 'outputs'
    source = (root / args.source_run).resolve()
    dest = (root / args.experiment_id).resolve()
    if source.parent != root.resolve() or dest.parent != root.resolve() or source == dest:
        raise ValueError('Use separate direct children of outputs')
    if dest.exists():
        raise ValueError('Experiment folder already exists; preserve old evidence')
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['status'] != 'complete':
        raise ValueError('Source run is incomplete')
    inputs = ['daily_sales.csv', 'top_routes.csv', 'validation_metrics.csv', 'effective_config.json']
    hashes = {name: sha256(source / name) for name in inputs}
    if any(hashes[name] != manifest['files'][name] for name in inputs):
        raise ValueError('Source file hash mismatch')
    cfg = read_config(source / 'effective_config.json')
    daily = pd.read_csv(source / 'daily_sales.csv', parse_dates=['date'])
    top = pd.read_csv(source / 'top_routes.csv')
    dest.mkdir()
    protocol = {'status': 'running', 'scope': 'validation-only experiment, not production run',
        'source_run': args.source_run, 'source_manifest_sha256': sha256(source / 'manifest.json'),
        'inputs': hashes, 'config': cfg, 'features': CONTEXT_FEATURES, 'specs': CONTEXT_SPECS,
        'code_sha256': code_hash(), 'entrypoint_sha256': sha256(Path(__file__)),
        'test_used_for_this_experiment': False,
        'prior_test_exposure': 'Previously seen in earlier tuning; not an independent holdout'}
    write_json(dest / 'protocol.json', protocol)
    try:
        predictions, logs = context_validation(daily, top, cfg)
        metrics = metric_table(predictions.loc[predictions.split.eq('validation')])
        primary = metrics.loc[metrics.horizon_group.eq('h1_7')]
        best = primary.sort_values(['mape_positive_pct', 'mae', 'model']).groupby(ROUTE).head(1)
        old = pd.read_csv(source / 'validation_metrics.csv')
        old = old.loc[old.horizon_group.eq('h1_7') & old.coverage.eq(1)]
        old = old.sort_values(['mape_positive_pct', 'mae', 'model']).groupby(ROUTE).head(1)
        comparison = best.merge(old[ROUTE+['model', 'mape_positive_pct']], on=ROUTE,
            suffixes=('_context', '_previous'), validate='one_to_one')
        comparison['improved_validation'] = comparison.mape_positive_pct_context < comparison.mape_positive_pct_previous
        comparison['meets_20pct'] = comparison.mape_positive_pct_context.le(cfg['mape_limit_pct']) & comparison.coverage.eq(1)
        write_csv(dest / 'predictions.csv', predictions)
        write_csv(dest / 'metrics.csv', metrics)
        write_csv(dest / 'fit_log.csv', logs)
        write_csv(dest / 'comparison.csv', comparison)
        protocol.update(status='complete', improved_routes=int(comparison.improved_validation.sum()),
            passing_routes=int(comparison.meets_20pct.sum()),
            files={p.name: sha256(p) for p in dest.glob('*.csv')})
        write_json(dest / 'protocol.json', protocol)
        print(f'Validation complete: improved {protocol["improved_routes"]}/10, <=20% {protocol["passing_routes"]}/10')
    except Exception:
        protocol['status'] = 'failed'
        write_json(dest / 'protocol.json', protocol)
        raise


if __name__ == '__main__':
    main()
