"""Authenticate inherited validation and reproduce local fit/scaler checkpoints."""
import argparse
import json
import re

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor

from src.common import ROOT, ROUTE, sha256, validate_run, write_json
from sigma.verification.weekly import validate_weekly
from sigma.forecasting.weekly import prepare, fit, predict_batch, inputs
from sigma.forecasting.reuse import validation_cache


def verify(run_id, output_id, daily_run='sigma_scaled_v11'):
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in [run_id, output_id, daily_run]):
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
    validation = pd.read_csv(folder / 'validation_weekly_predictions.csv', parse_dates=['as_of_date', 'window_start', 'window_end'])
    new_ids = set(settings['models']) - set(inherited.model)
    joined = inherited.merge(validation, on=ROUTE + ['model', 'as_of_date', 'week_block'],
        suffixes=('_parent', '_new'), validate='one_to_one')
    assert len(joined) == len(inherited)
    for column in ['forecast_qty_7d', 'actual_qty_7d', 'base_forecast_qty_7d', 'calibration_factor']:
        np.testing.assert_allclose(joined[column + '_parent'], joined[column + '_new'], rtol=0, atol=1e-8)
    raw = pd.read_csv(source, usecols=ROUTE + ['order_datetime', 'quantity', 'order_status', 'order_id'])
    raw['date'] = pd.to_datetime(raw.order_datetime, utc=True).dt.tz_localize(None).dt.normalize()
    raw = raw.loc[raw.order_status.isin(cfg['sales_statuses'])]
    routes = sorted(set(raw[ROUTE].itertuples(index=False, name=None)))
    grid = pd.MultiIndex.from_tuples([(date, *route) for route in routes
        for date in pd.date_range(cfg['observation_start'], cfg['observation_end'])], names=['date'] + ROUTE)
    daily = raw.groupby(['date'] + ROUTE).agg(sales_qty=('quantity', 'sum'),
        order_count=('order_id', 'nunique')).reindex(grid, fill_value=0).reset_index()
    checked, fits, scaler_checks = 0, 0, 0
    for phase in ['validation', 'test', 'future']:
        frame = pd.read_csv(folder / ('weekly_forecast.csv' if phase == 'future' else f'{phase}_weekly_predictions.csv'), parse_dates=['as_of_date'])
        frame = frame.loc[frame.model.isin(new_ids)].copy()
        prepared = prepare(daily.loc[daily.date.le(cfg['validation_end'])] if phase == 'validation' else daily, settings)
        if phase == 'future':
            frame['fit_cutoff'] = frame.as_of_date
        else:
            start = pd.Timestamp(cfg[f'{phase}_start']) - pd.Timedelta(days=1)
            frame['fit_cutoff'] = start + pd.to_timedelta(((frame.as_of_date - start).dt.days // settings['refit_days']) * settings['refit_days'], unit='D')
        for ident, group in frame.groupby('model'):
            spec = settings['models'][ident]
            assert spec['kind'] == 'local_week'
            # First/last cutoffs are fixed checkpoints, regardless of errors.
            for cutoff in sorted({group.fit_cutoff.min(), group.fit_cutoff.max()}):
                model, log = fit(prepared, cutoff, spec, cfg, settings)
                assert log['max_label_end'] <= cutoff
                fits += 1
                if spec['estimator'] == 'annual_median':
                    train = pd.concat([inputs(table, spec, np.flatnonzero((table['ends'] <= cutoff)
                        & (table['ends'] >= cutoff - pd.Timedelta(days=settings['training_window_days'] - 1))))
                        for table in prepared.values()], ignore_index=True)
                    for route, estimator in model.models.items():
                        if isinstance(estimator, DummyRegressor):
                            continue
                        z = model.inputs(train.loc[train.route_index.eq(route)]).to_numpy(float)
                        expected = np.array([np.median(col[np.isfinite(col)]) if np.isfinite(col).any() else 0. for col in z.T])
                        np.testing.assert_allclose(estimator[0].statistics_, expected, atol=1e-10, rtol=0)
                        filled = np.where(np.isnan(z), expected, z)
                        indicators = np.isnan(z[:, estimator[0].indicator_.features_]).astype(float)
                        transformed = np.column_stack([filled, indicators])
                        np.testing.assert_allclose(estimator[1].mean_, transformed.mean(axis=0), atol=1e-10, rtol=0)
                        scaler_checks += 1
                for origin, rows in group.loc[group.fit_cutoff.eq(cutoff)].groupby('as_of_date'):
                    values = predict_batch(model, prepared, origin, spec)
                    expected = [values[((row.destination_country, row.carrier), row.week_block)] for row in rows.itertuples()]
                    np.testing.assert_allclose(rows.forecast_qty_7d, expected, atol=1e-8, rtol=0)
                    checked += len(rows)
                print(f'{phase}: reproduced {ident} at {cutoff.date()}', flush=True)
    validate_weekly(folder); validate_weekly(parent)
    assert sha256(source) == summary['source_sha256']
    daily_manifest = validate_run(ROOT / 'outputs' / daily_run)
    assert daily_manifest['source_sha256'] == summary['source_sha256']
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    result = {'status': 'verified', 'inherited_validation_pairs_unchanged': len(joined),
        'local_forecast_checkpoint_pairs_reproduced': checked, 'local_fits_reproduced': fits,
        'imputer_and_scaler_train_statistics_checked': scaler_checks, 'source_unchanged': True,
        'daily_sealed_files_unchanged': len(daily_manifest['files']),
        'weekly_summary_sha256': sha256(folder / 'summary.json'),
        'checkpoint_scope': 'First and last refit per new selected/candidate model in each phase; inherited validation all pairs',
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
