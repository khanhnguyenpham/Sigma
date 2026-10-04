"""Verify a sealed local run without modifying its evidence or exposing IDs."""
from __future__ import annotations

import argparse
import importlib.metadata
from pathlib import Path

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, ITEM, code_hash, sha256, validate_run, write_json
from src.evaluation import metric_table, select_models
from src.data import audit_orders, daily_sales, route_top
from src.transactions import verify_events


def verify(folder):
    folder = Path(folder).resolve()
    manifest = validate_run(folder)
    cfg = manifest['config']
    if manifest['code_sha256'] != code_hash():
        raise ValueError('Verification requires the code used by this run')
    source = (ROOT / (manifest.get('source_relative_path') or cfg['source'])).resolve()
    if not source.is_relative_to(ROOT):
        raise ValueError('Source path escapes the project')
    if sha256(source) != manifest['source_sha256']:
        raise ValueError('Raw input hash differs')
    sales, _ = audit_orders(source, cfg)
    truth_daily = daily_sales(sales, cfg)
    daily = pd.read_csv(folder / 'daily_sales.csv', parse_dates=['date'])
    try:
        pd.testing.assert_frame_equal(daily, truth_daily, check_dtype=False, atol=cfg['numeric_tolerance'], rtol=0)
        top = pd.read_csv(folder/'top_routes.csv')
        pd.testing.assert_frame_equal(top, route_top(truth_daily,cfg), check_dtype=False, atol=0, rtol=0)
    except AssertionError:
        raise ValueError('Daily sales or train top routes differ from the audited source') from None
    selected = pd.read_csv(folder / 'selected_models.csv')
    invalid = set()
    if (folder/'sarima_log.csv').is_file():
        log = pd.read_csv(folder/'sarima_log.csv')
        invalid = {((row.destination_country,row.carrier),row.model)
                   for row in log.loc[log.status.eq('failed')].itertuples(index=False)}
    expected_selection = select_models(pd.read_csv(folder/'validation_metrics.csv'), top, cfg, invalid)
    # CSV blanks deserialize as NaN; the selector returns None for non-top routes.
    for frame in (selected, expected_selection):
        frame['validation_target_met'] = frame['validation_target_met'].astype('boolean')
    try:
        pd.testing.assert_frame_equal(selected, expected_selection, check_dtype=False,
                                      atol=cfg['numeric_tolerance'], rtol=0)
    except AssertionError:
        raise ValueError('Locked selection differs from the declared validation-only rule') from None
    if sha256(folder / 'selected_models.csv') != manifest['selection_sha256_before_test']:
        raise ValueError('Model selection differs from the pre-test lock')
    predictions = pd.read_csv(folder / 'predictions.csv', parse_dates=['as_of_date','target_date'])
    assert not predictions.duplicated(ROUTE + ['as_of_date','horizon_day']).any()
    assert (predictions.target_date == predictions.as_of_date + pd.to_timedelta(predictions.horizon_day,unit='D')).all()
    assert predictions.groupby(ROUTE + ['as_of_date']).size().eq(cfg['horizon']).all()
    assert predictions.loc[predictions.split.eq('outside_test'),'actual_qty'].isna().all()
    assert predictions.forecast_qty.ge(0).all() and np.isfinite(predictions.forecast_qty).all()
    origins = set(pd.date_range(pd.Timestamp(cfg['test_start'])-pd.Timedelta(days=1),
                                pd.Timestamp(cfg['test_end'])-pd.Timedelta(days=1)))
    assert set(predictions.as_of_date) == origins
    assert len(predictions.groupby(ROUTE+['as_of_date'])) == len(selected)*len(origins)
    actual_truth = truth_daily[['date']+ROUTE+['sales_qty']].rename(columns={'date':'target_date','sales_qty':'truth_qty'})
    aligned = predictions.merge(actual_truth,on=ROUTE+['target_date'],how='left',validate='many_to_one')
    expected_actual = aligned.truth_qty.where(aligned.target_date.le(pd.Timestamp(cfg['test_end'])))
    if not np.allclose(aligned.actual_qty,expected_actual,atol=0,rtol=0,equal_nan=True):
        raise ValueError('Backtest actual quantities differ from the audited daily sales or split visibility')
    recomputed = metric_table(predictions.loc[predictions.split.eq('test')])
    actual_metrics = pd.read_csv(folder / 'metrics.csv')
    pd.testing.assert_frame_equal(recomputed,actual_metrics,check_dtype=False,atol=cfg['numeric_tolerance'],rtol=0)
    for name in ('forecast.csv','demo_forecast.csv'):
        forecast = pd.read_csv(folder / name,parse_dates=['target_date'])
        assert len(forecast)==len(selected)*cfg['horizon']
        assert forecast.groupby(ROUTE).horizon_day.nunique().eq(cfg['horizon']).all()
        assert not forecast.duplicated(ROUTE + ['horizon_day']).any()
        assert forecast.forecast_qty.ge(0).all()
        aligned_forecast = forecast.merge(actual_truth,on=ROUTE+['target_date'],how='left',validate='many_to_one')
        if not np.allclose(aligned_forecast.actual_qty,aligned_forecast.truth_qty,atol=0,rtol=0,equal_nan=True):
            raise ValueError('Forecast actual quantities do not match available audited sales')
    expected_sales = daily.loc[daily.date.between(cfg['test_start'],cfg['test_end']),'sales_qty'].sum()
    scenario_sales = {};rows=0
    for chunk in pd.read_csv(folder / 'inventory_ledger.csv',chunksize=50000):
        quantities = chunk[['opening','receipts','historical_sales','scenario_demand','fulfilled','shortage','closing']].to_numpy()
        assert np.isfinite(quantities).all() and (quantities>=0).all()
        assert (quantities==np.floor(quantities)).all()
        np.testing.assert_array_equal(chunk.closing,chunk.opening+chunk.receipts-chunk.fulfilled)
        np.testing.assert_array_equal(chunk.scenario_demand,chunk.fulfilled+chunk.shortage)
        assert chunk.is_simulated.all()
        for scenario,total in chunk.groupby('scenario_id').historical_sales.sum().items():
            scenario_sales[scenario]=scenario_sales.get(scenario,0)+total
        rows += len(chunk)
    assert all(total==expected_sales for total in scenario_sales.values())
    event_verification = verify_events(folder/'inventory_events.csv', folder/'inventory_ledger.csv', sales, cfg)
    recommendations = 0
    for chunk in pd.read_csv(folder / 'inventory_recommendations.csv',chunksize=50000,low_memory=False):
        np.testing.assert_array_equal(chunk.needs_replenishment,chunk.on_hand.lt(chunk.ROP))
        moq=chunk.partner_id.map(lambda partner:cfg['inventory']['partners'][partner]['moq']).to_numpy()
        expected_q=np.where(chunk.needs_replenishment,np.ceil(np.maximum(0,chunk.S-chunk.IP)),0)
        expected_q=np.where(expected_q>0,np.maximum(expected_q,moq),0)
        np.testing.assert_array_equal(chunk.Q,expected_q)
        assert (chunk.IP>=chunk.on_hand).all()
        recommendations += len(chunk)
    alerts = pd.read_csv(folder / 'alerts.csv')
    assert alerts.event_id.is_unique
    assert not alerts.duplicated(ITEM+['as_of_date']).any()
    np.testing.assert_array_equal(alerts.reported_early,alerts.tp & alerts.actual_days.ge(7))
    assert not alerts.loc[alerts.already_empty,['tp','fp','fn','reported_early']].any().any()
    acceptance = pd.read_csv(folder / 'accuracy_acceptance.csv')
    assert manifest['accuracy_criterion_passed']==bool(acceptance.accuracy_passed.all())
    packages = {}
    for line in (ROOT/'requirements.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):continue
        package,pin=line.split('==')
        actual=importlib.metadata.version(package)
        assert actual==pin, f'Environment differs for {package}'
        packages[package]=actual
    return {'run_id':manifest['run_id'],'run_manifest_sha256':sha256(folder/'manifest.json'),
        'code_sha256':code_hash(),
        'audited_daily_top_selection_actuals_verified':True,
        'code_files_sha256':{path.relative_to(ROOT).as_posix():sha256(path)
                            for path in [ROOT/'run.py',ROOT/'app.py']+sorted((ROOT/'src').glob('*.py'))},
        'checks_passed':True,'product_fully_accepted':False,
        'acceptance_limit':'Technical invariants verified; R05 and external academic acceptance evaluated separately',
        'top10_accuracy_passed':int(acceptance.accuracy_passed.sum()),
        'forecast_rows':len(selected)*cfg['horizon'],'prediction_rows':len(predictions),
        'ledger_rows':rows,'recommendation_rows':recommendations,
        'alert_windows':len(alerts),'scenarios':len(scenario_sales),
        'environment_pins_verified':len(packages),'environment_packages':packages,
        'requirements_lock_sha256':sha256(ROOT/'requirements.txt'),
        'entrypoint_sha256':sha256(Path(__file__)), 'transaction_events':event_verification}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    folder=(ROOT/'outputs'/args.run_id).resolve()
    if folder.parent != (ROOT/'outputs').resolve():raise ValueError('Invalid run path')
    result=verify(folder)
    # Keep verification outside the sealed source run so its history stays intact.
    target=ROOT/'outputs'/f'{args.run_id}_verification.json'
    write_json(target,result)
    print(f"Verified {result['ledger_rows']} ledger rows, {result['environment_pins_verified']} pins; "
          f"R05 passes {result['top10_accuracy_passed']}/10. Verification: {target.name}")


if __name__=='__main__':
    main()
