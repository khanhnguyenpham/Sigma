"""Smoke-check all six pages and reconcile filters with their sealed CSVs."""
import argparse
import json
import os
import re

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from src.common import ROOT, sha256, write_json
from sigma.delivery.customer import delivery_settings, delivery_config_path
from sigma.verification.weekly import validate_weekly
from sigma.provenance import implementation_hashes


def check(output_id, config=None, country=None, carrier=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', output_id):
        raise ValueError('Invalid QA output id')
    path = delivery_config_path(config)
    os.environ['SIGMA_DELIVERY_CONFIG'] = path.relative_to(ROOT).as_posix()
    bundle = delivery_settings()
    wdir = ROOT / 'outputs' / bundle['weekly_run']
    weekly = validate_weekly(wdir)
    forecast = pd.read_csv(wdir / 'weekly_forecast.csv')
    if country is None:
        country = sorted(forecast.destination_country.unique())[0]
    if carrier is None:
        carrier = sorted(forecast.loc[forecast.destination_country.eq(country), 'carrier'].unique())[0]
    if not ((forecast.destination_country == country) & (forecast.carrier == carrier)).any():
        raise ValueError('QA route not present in bundle')
    at = AppTest.from_file(str(ROOT / 'sigma/ui/product.py'), default_timeout=90).run()
    assert not at.exception
    assert bundle['weekly_run'] in set(at.dataframe[0].value['Bằng chứng'])
    pages = [{'page': 'overview', 'tables': len(at.dataframe), 'exceptions': 0}]

    def filtered(page, chosen_country=country, chosen_carrier=carrier):
        at.switch_page(str(ROOT / page)).run()
        assert not at.exception
        next(w for w in at.sidebar.selectbox if w.label == 'Điểm đến').select(chosen_country).run()
        next(w for w in at.sidebar.selectbox if w.label == 'Nhà mạng').select(chosen_carrier).run()
        assert not at.exception
        pages.append({'page': page, 'tables': len(at.dataframe), 'route': chosen_country + '/' + chosen_carrier, 'exceptions': 0})

    filtered('sigma/ui/weekly.py')
    assert next(w for w in at.sidebar.selectbox if w.label == 'Run tuần').value == bundle['weekly_run']
    expected = forecast.loc[forecast.destination_country.eq(country) & forecast.carrier.eq(carrier)]
    np.testing.assert_allclose(at.dataframe[0].value.forecast_qty_7d, expected.forecast_qty_7d, rtol=0, atol=1e-8)
    next(w for w in at.sidebar.selectbox if w.label == 'Lịch đánh giá').select('seven_day_origins').run()
    next(w for w in at.sidebar.selectbox if w.label == 'Khối dự báo').select(2).run()
    assert not at.exception
    scores = at.dataframe[3].value
    assert scores.cadence.eq('seven_day_origins').all() and scores.week_block.eq(2).all()
    filtered('sigma/ui/delivery.py')
    delivery = at.dataframe[0].value
    assert len(delivery) == 21 and delivery.actual_delivered_qty.isna().all()
    assert (pd.to_datetime(delivery.delivery_date) - pd.to_datetime(delivery.order_date)).dt.days.eq(7).all()
    assert delivery.loc[delivery.delivery_horizon_day.le(7), 'forecast_from_future_orders_qty'].eq(0).all()
    np.testing.assert_allclose(delivery.forecast_from_future_orders_qty.sum(), expected.forecast_qty_7d.sum(), rtol=0, atol=1e-8)
    filtered('sigma/ui/inventory.py')
    assert len(at.dataframe) == 5
    event_table = at.dataframe[2].value
    assert event_table.destination_country.eq(country).all() and event_table.carrier.eq(carrier).all()
    assert 'diagnostic_group' in event_table and 'event_id' not in event_table
    groups = next(w for w in at.selectbox if w.label == 'Nhóm ca cảnh báo')
    if len(groups.options) > 1:
        chosen_group = list(groups.options)[1]
        groups.select(chosen_group).run()
        assert not at.exception and len(at.dataframe[2].value) > 0
        assert at.dataframe[2].value.diagnostic_group.eq(chosen_group).all()
        next(w for w in at.selectbox if w.label == 'Nhóm ca cảnh báo').select('Tất cả').run()
    scenario_rows = []
    for scenario in ['base', 'partial_receipt', 'late_receipt', 'no_receipt']:
        next(w for w in at.selectbox if w.label == 'Kịch bản tồn tuần').select(scenario).run()
        assert not at.exception
        ledger = at.dataframe[-1].value
        assert ledger.scenario_id.eq(scenario).all() and ledger.destination_country.eq(country).all() and ledger.carrier.eq(carrier).all()
        np.testing.assert_array_equal(ledger.opening + ledger.receipts - ledger.fulfilled, ledger.closing)
        np.testing.assert_array_equal(ledger.fulfilled + ledger.shortage, ledger.scenario_demand)
        scenario_rows.append({'scenario': scenario, 'route_ledger_rows': len(ledger)})
    # Item filters must affect both the recommendation and the policy ledger.
    chosen_sku = sorted(at.dataframe[0].value.sku.unique())[0]
    next(w for w in at.sidebar.selectbox if w.label == 'Mặt hàng SKU').select(chosen_sku).run()
    chosen_type = sorted(at.dataframe[0].value.product_type.unique())[0]
    next(w for w in at.sidebar.selectbox if w.label == 'Loại sản phẩm').select(chosen_type).run()
    assert not at.exception
    assert at.dataframe[0].value.sku.eq(chosen_sku).all() and at.dataframe[0].value.product_type.eq(chosen_type).all()
    assert at.dataframe[-1].value.sku.eq(chosen_sku).all() and at.dataframe[-1].value.product_type.eq(chosen_type).all()
    assert at.dataframe[2].value.sku.eq(chosen_sku).all() and at.dataframe[2].value.product_type.eq(chosen_type).all()
    assert len(at.dataframe[-1].value) == 92
    at.switch_page(str(ROOT / 'sigma/ui/comparison.py')).run()
    assert not at.exception and len(at.dataframe) == 4
    comparison_top = at.dataframe[0].value
    chosen = comparison_top.loc[comparison_top.destination_country.eq(country) & comparison_top.carrier.eq(carrier)]
    chosen = chosen.iloc[0] if len(chosen) else comparison_top.iloc[0]
    filtered('sigma/ui/comparison.py', chosen.destination_country, chosen.carrier)
    cmp_metrics = at.dataframe[1].value
    assert cmp_metrics.destination_country.eq(chosen.destination_country).all() and cmp_metrics.carrier.eq(chosen.carrier).all()
    assert {'direct_weekly', 'sum_daily_model', 'naive', 'ma7', 'ma28'} == set(cmp_metrics.method)
    assert cmp_metrics.coverage.eq(1).all()
    assert not at.dataframe[2].value.official_daily_R05.any()
    filtered('sigma/ui/daily.py')
    if bundle.get('product_runs'):
        assert list(next(w for w in at.sidebar.selectbox if w.label == 'Bộ kết quả').options) == [bundle['daily_run']]
    result = {'status': 'verified', 'pages': pages, 'scenario_filters': scenario_rows,
        'configured_weekly_run': bundle['weekly_run'], 'configured_daily_run': bundle['daily_run'],
        'weekly_summary_sha256': sha256(wdir / 'summary.json'), 'delivery_config_sha256': sha256(path),
        'product_entrypoint_sha256': sha256(ROOT / 'sigma/ui/product.py'),
        'implementation_modules_sha256': implementation_hashes('ui', 'verification', 'analysis'),
        'source_kind': bundle['source_description'], 'project_fully_accepted': False,
        'weekly_test_passed': weekly['top10_test_weekly_passed']}
    out = ROOT / 'outputs' / output_id
    out.mkdir(exist_ok=False)
    write_json(out / 'summary.json', result)
    print(json.dumps({key: value for key, value in result.items() if key != 'implementation_modules_sha256'}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-id', required=True)
    parser.add_argument('--delivery-config')
    parser.add_argument('--country')
    parser.add_argument('--carrier')
    args = parser.parse_args()
    check(args.output_id, args.delivery_config, args.country, args.carrier)
