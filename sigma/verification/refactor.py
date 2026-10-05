"""Prove a structural refactor preserves locked selection and fresh forecasts."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, sha256, validate_run, write_json
from sigma.provenance import implementation_hashes
from sigma.verification.weekly import validate_weekly


def verify(before_run, after_run, output_id, daily_run='sigma_scaled_v11'):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in [before_run, after_run, output_id, daily_run]):
        raise ValueError('Invalid parity identifier')
    old, new = [ROOT / 'outputs' / name for name in [before_run, after_run]]
    a, b = validate_weekly(old), validate_weekly(new)
    protocol = json.loads((new / 'protocol.json').read_text(encoding='utf-8'))
    prior = json.loads((old / 'protocol.json').read_text(encoding='utf-8'))
    assert protocol['base_config'] == prior['base_config']
    assert protocol['weekly_config']['models'] == prior['weekly_config']['models']
    assert protocol['validation_cache']['run_id'] == before_run and not protocol['validation_cache']['test_predictions_reused']
    assert protocol['implementation_modules_sha256'] == implementation_hashes('forecasting')
    counts = {}
    for name in ['top_routes.csv', 'selected_weekly_models.csv', 'validation_weekly_predictions.csv',
        'test_weekly_predictions.csv', 'selected_test_weekly_metrics.csv', 'weekly_forecast.csv', 'daily_allocation.csv']:
        left, right = [pd.read_csv(folder / name) for folder in [old, new]]
        assert left.columns.tolist() == right.columns.tolist() and left.shape == right.shape
        for column in left.columns:
            if pd.api.types.is_numeric_dtype(left[column]):
                np.testing.assert_allclose(left[column], right[column], atol=1e-8, rtol=0, equal_nan=True)
            else:
                pd.testing.assert_series_equal(left[column], right[column], check_names=False)
        counts[name] = len(left)
    daily = validate_run(ROOT / 'outputs' / daily_run)
    source = ROOT / protocol['base_config']['source']
    assert sha256(source) == a['source_sha256'] == b['source_sha256'] == daily['source_sha256']
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    result = {'status': 'verified', 'kind': 'refactor_numerical_parity', 'before_run': before_run, 'after_run': after_run,
        'fresh_test_and_future_forecasts_equal': True, 'selection_semantically_identical': True,
        'selection_byte_identical': a['selection_sha256'] == b['selection_sha256'], 'absolute_tolerance': 1e-8,
        'cached_validation_not_claimed_as_retrained': True, 'rows_checked': counts,
        'canonical_implementation_hashes_match': True, 'source_unchanged': True,
        'daily_sealed_files_unchanged': len(daily['files']), 'before_summary_sha256': sha256(old / 'summary.json'),
        'after_summary_sha256': sha256(new / 'summary.json'), 'test_is_independent': False, 'project_fully_accepted': False}
    write_json(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-run', required=True)
    parser.add_argument('--after-run', required=True)
    parser.add_argument('--output-id', required=True)
    parser.add_argument('--daily-run', default='sigma_scaled_v11')
    args = parser.parse_args()
    verify(args.before_run, args.after_run, args.output_id, args.daily_run)
