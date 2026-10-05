"""Independently reconcile calibrated component quantities and fixed weights."""
import argparse
import json
import re

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, sha256, write_json
from sigma.verification.weekly import validate_weekly
from sigma.forecasting.reuse import validation_cache


def verify(run_id, output_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in [run_id, output_id]):
        raise ValueError('Invalid local id')
    folder = ROOT / 'outputs' / run_id
    summary = validate_weekly(folder)
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    cfg, settings = protocol['base_config'], protocol['weekly_config']
    source = ROOT / cfg['source']
    assert sha256(source) == summary['source_sha256']
    parent = ROOT / cfg['output_root'] / protocol['validation_cache']['run_id']
    inherited, _, provenance = validation_cache(parent, cfg, settings, sha256(source))
    assert provenance == protocol['validation_cache']
    rows_checked = 0
    for phase in ['validation', 'test', 'future']:
        frame = pd.read_csv(folder / ('weekly_forecast.csv' if phase == 'future' else f'{phase}_weekly_predictions.csv'), parse_dates=['as_of_date'])
        logs = pd.read_csv(folder / f'{phase}_head_log.csv', parse_dates=['head_fit_cutoff', 'max_head_label_end'])
        assert logs.max_head_label_end.le(logs.head_fit_cutoff).all()
        for ident, spec in settings['models'].items():
            if spec['kind'] != 'calibrated_blend':
                continue
            g = frame.loc[frame.model.eq(ident)].copy()
            if g.empty:
                continue
            w = np.array(spec['weights'], float)
            assert len(w) == 2 and (w >= 0).all() and abs(w.sum() - 1) < 1e-12
            assert g.component_calibration_factor.between(.5, 1.5).all()
            expected = w[0] * g.mixture_first_qty * g.component_calibration_factor + w[1] * g.mixture_second_qty
            np.testing.assert_allclose(g.forecast_qty_7d, expected, rtol=0, atol=1e-8)
            if phase == 'future':
                g['head_fit_cutoff'] = g.as_of_date
            else:
                first = pd.Timestamp(cfg[f'{phase}_start']) - pd.Timedelta(days=1)
                g['head_fit_cutoff'] = first + pd.to_timedelta(((g.as_of_date - first).dt.days // settings['refit_days']) * settings['refit_days'], unit='D')
            aligned = g.merge(logs, on=ROUTE + ['model', 'week_block', 'head_fit_cutoff'], validate='many_to_one')
            assert len(aligned) == len(g)
            np.testing.assert_allclose(aligned.component_calibration_factor, aligned.factor, rtol=0, atol=1e-8)
            if phase == 'validation':
                for column, candidate in [('mixture_first_qty', spec['components'][0]),
                    ('mixture_second_qty', spec['components'][1])]:
                    base = frame.loc[frame.model.eq(candidate), ROUTE + ['as_of_date', 'week_block', 'forecast_qty_7d']]
                    linked = g.merge(base, on=ROUTE + ['as_of_date', 'week_block'], suffixes=('', '_parent'), validate='one_to_one')
                    assert len(linked) == len(g)
                    np.testing.assert_allclose(linked[column], linked.forecast_qty_7d_parent, rtol=0, atol=1e-8)
                calibrated = frame.loc[frame.model.eq(spec['calibrated_reference']), ROUTE + ['as_of_date', 'week_block', 'forecast_qty_7d']]
                linked = g.merge(calibrated, on=ROUTE + ['as_of_date', 'week_block'], suffixes=('', '_calibrated'), validate='one_to_one')
                assert len(linked) == len(g)
                np.testing.assert_allclose(linked.mixture_first_qty * linked.component_calibration_factor,
                    linked.forecast_qty_7d_calibrated, rtol=0, atol=1e-8)
            rows_checked += len(g)
    current = pd.read_csv(folder / 'validation_weekly_predictions.csv', parse_dates=['as_of_date', 'window_start', 'window_end'])
    linked = inherited.merge(current, on=ROUTE + ['model', 'as_of_date', 'week_block'], suffixes=('_old', '_new'), validate='one_to_one')
    assert len(linked) == len(inherited)
    np.testing.assert_allclose(linked.forecast_qty_7d_old, linked.forecast_qty_7d_new, rtol=0, atol=1e-8)
    validate_weekly(folder); validate_weekly(parent)
    assert sha256(source) == summary['source_sha256']
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    result = {'status': 'verified', 'calibrated_combination_pairs_checked': rows_checked,
        'first_calibrated_component_matches_reference': True, 'both_raw_components_match_validation_parents': True,
        'component_factor_matches_causal_head_log': True, 'inherited_validation_pairs_unchanged': len(linked),
        'source_unchanged': True, 'weekly_summary_sha256': sha256(folder / 'summary.json'),
        'project_fully_accepted': False, 'test_is_independent': False}
    write_json(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-id', required=True)
    args = parser.parse_args()
    verify(args.run_id, args.output_id)
