"""Final bundle guards: completeness, fixed configuration and aggregate-only loading."""
import json

import pandas as pd
import pytest

from src.common import ROOT, ROUTE, write_csv, write_json, sha256
from M2.final_report import CONFIG, check_pairs, configurations, load_report
from M2.models.common import prediction_rows
from M2.models.registry import load_settings


def test_fixed_bundle_has_route_specific_training_and_normalization():
    exp = json.loads((ROOT/CONFIG).read_text(encoding='utf-8'))
    table = configurations(exp, load_settings(ROOT/exp['model_config'])).set_index('carrier')
    assert len(table) == 10
    assert table.loc['LG U+', ['training_window_days', 'normalization_days']].tolist() == [540, 56]
    assert table.loc['AIS', ['training_window_days', 'normalization_days']].tolist() == [365, 90]
    assert table.loc['TrueMove H', 'min_child_samples'] == 50
    assert table.loc['au (KDDI)', 'training_population'] == 'own_route'
    assert pd.isna(table.loc['au (KDDI)', 'normalization_days'])


def test_final_bundle_rejects_missing_route_and_pair():
    dates = pd.date_range('2025-09-01', '2025-11-01')
    series = pd.Series(2., index=dates)
    cfg = {'test_start': '2025-10-01', 'test_end': '2025-10-14'}
    exp = {'routes': [{'destination_country': 'Synthetic', 'carrier': f'C{i}', 'model': 'fixed'} for i in range(10)]}
    rows, days = [], []
    for route in exp['routes']:
        key = tuple(route[name] for name in ROUTE)
        days.append(pd.DataFrame({'date': dates, **dict(zip(ROUTE, key)), 'sales_qty': 2., 'order_count': 1.}))
        for origin in pd.date_range('2025-09-30', '2025-10-13'):
            rows.extend(prediction_rows(series, key, 'LightGBM', 'direct_7d', 'fixed', 'test',
                                       origin, pd.Timestamp(cfg['test_end']), [14., 14.]))
    frame, daily = pd.DataFrame(rows), pd.concat(days, ignore_index=True)
    assert check_pairs(frame, daily, cfg, exp, 'test') == 280
    with pytest.raises(AssertionError): check_pairs(frame.loc[frame.carrier.ne('C0')], daily, cfg, exp, 'test')
    with pytest.raises(AssertionError, match='Missing or duplicate'): check_pairs(frame.iloc[1:], daily, cfg, exp, 'test')


def test_public_report_loads_without_raw_and_rejects_modified_metrics(tmp_path):
    choices = pd.DataFrame({'destination_country': 'Synthetic', 'carrier': [f'C{i}' for i in range(10)],
                            'family': 'LightGBM', 'target': 'direct_7d', 'model': 'fixed'})
    write_csv(tmp_path/'selected_models.csv', choices)
    write_csv(tmp_path/'test_metrics.csv', choices.assign(block=1, cadence='daily_origins', coverage=1., mape_positive_pct=19.))
    write_json(tmp_path/'model_configurations.json', choices.to_dict(orient='records'))
    write_json(tmp_path/'report_manifest.json', {'status': 'complete',
        'files': {path.name: sha256(path) for path in tmp_path.iterdir()}})
    assert len(load_report(tmp_path)['routes']) == 10
    with (tmp_path/'test_metrics.csv').open('a', encoding='utf-8') as stream: stream.write('\n')
    with pytest.raises(ValueError, match='changed'): load_report(tmp_path)


def test_final_dashboard_reads_approved_aggregate_bundle():
    from streamlit.testing.v1 import AppTest
    from M2.final_report import REPORT
    if not REPORT.exists(): pytest.skip('Final bundle is generated after the fresh replay')
    app = AppTest.from_file(str(ROOT/'M2/final_app.py'), default_timeout=60).run()
    assert not app.exception
    assert app.metric[0].value == '10/10'
    assert len(app.tabs) == 3
    app.selectbox[0].select('nonoverlapping_7d')
    app.selectbox[1].select(2).run()
    assert not app.exception and len(app.dataframe[1].value) == 10
