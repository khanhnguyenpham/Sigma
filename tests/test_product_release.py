"""Frozen run guards and honest readiness under failure or partial accuracy."""
import json

import pytest

from src.common import sha256
from sigma import product_catalog, release
from src.common import ROOT


def fixture():
    names = {role: role + '_fake' for role in ['weekly', 'daily', 'policy', 'stock', 'delivery', 'comparison']}
    hashes = {role: role + '_hash' for role in names}
    bundle = {'weekly_run': names['weekly'], 'daily_run': names['daily'], 'product_runs': names}
    summaries = {role: {'source_sha256': 'raw', 'weekly_run': names['weekly'], 'daily_run': names['daily']} for role in names}
    summaries['stock'].update(stock_policy_run=names['policy'], stock_policy_summary_sha256=hashes['policy'])
    summaries['comparison'].update(policy_run=names['policy'], weekly_parent_sha256=hashes['weekly'],
        daily_parent_sha256=hashes['daily'], policy_parent_sha256=hashes['policy'], policy_forecasts_equal_comparison_forecasts=True)
    summaries['delivery'].update(customer_delivery_days=7, customer_delay_days=0, supplier_lead_time_modified=False)
    return bundle, summaries, hashes


@pytest.mark.parametrize('change', ['source', 'weekly', 'stock_policy', 'comparison_hash', 'comparison_grid', 'delivery_delay'])
def test_release_refuses_mixed_or_changed_parents(change):
    bundle, summaries, hashes = fixture()
    release.verify_parents(bundle, summaries, hashes)
    if change == 'source': summaries['stock']['source_sha256'] = 'other'
    if change == 'weekly': summaries['delivery']['weekly_run'] = 'other'
    if change == 'stock_policy': summaries['stock']['stock_policy_run'] = 'other'
    if change == 'comparison_hash': summaries['comparison']['daily_parent_sha256'] = 'other'
    if change == 'comparison_grid': summaries['comparison']['policy_forecasts_equal_comparison_forecasts'] = False
    if change == 'delivery_delay': summaries['delivery']['customer_delay_days'] = 1
    with pytest.raises(ValueError): release.verify_parents(bundle, summaries, hashes)


def test_all_weekly_routes_passing_never_certifies_daily_r05():
    rows = release.acceptance(0, 10, 10, .34)
    assert rows[0]['status'] == 'Chưa đạt' and rows[1]['status'] == 'Đạt chỉ tiêu tuần'
    assert rows[3]['status'] == 'Còn ca chưa báo sớm'
    assert release.acceptance(3, 3, 3, .99)[0]['status'] == 'Chưa đạt'


def test_release_protocol_requires_exact_locked_forecast_hashes():
    hashes = {'weekly': 'week', 'daily': 'day'}
    protocols = {'policy': {'weekly_summary_sha256': 'week', 'daily_manifest_sha256': 'day'}}
    release.verify_protocol_links(protocols, hashes)
    protocols['policy']['weekly_summary_sha256'] = 'other'
    with pytest.raises(ValueError, match='protocol parent'):
        release.verify_protocol_links(protocols, hashes)


def test_frozen_catalog_rejects_tampering_instead_of_newer_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(product_catalog, 'ROOT', tmp_path)
    first = tmp_path / 'outputs/first'; first.mkdir(parents=True)
    second = tmp_path / 'outputs/newer'; second.mkdir()
    (first / 'summary.json').write_text('{}')
    (second / 'summary.json').write_text('{}')
    bundle = {'product_runs': {'weekly': 'first'}, 'product_summary_hashes': {'weekly': sha256(first / 'summary.json')}}
    assert product_catalog.candidate_folders(bundle, 'weekly') == [first]
    (first / 'summary.json').write_text('{"changed": true}')
    with pytest.raises(ValueError, match='changed'): product_catalog.candidate_folders(bundle, 'weekly')
    with pytest.raises(ValueError, match='no stock'): product_catalog.candidate_folders(bundle, 'stock')
    with pytest.raises(ValueError, match='Invalid'): product_catalog.candidate_folders({'product_runs': {'weekly': '../newer'}}, 'weekly')


def test_comparison_refuses_changed_export_and_path_escape(tmp_path):
    artifact = tmp_path / 'report.csv'; artifact.write_text('fake')
    summary = {'kind': 'matched_day_week_comparison', 'status': 'verified', 'files': {'report.csv': sha256(artifact)}}
    (tmp_path / 'summary.json').write_text(json.dumps(summary))
    assert release.comparison_summary(tmp_path) == summary
    artifact.write_text('modified')
    with pytest.raises(ValueError, match='changed'): release.comparison_summary(tmp_path)
    summary['files'] = {'../escape.csv': 'digest'}
    (tmp_path / 'summary.json').write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='changed'): release.comparison_summary(tmp_path)


def test_checkpoint_rejects_active_bundle_edit_and_report_tamper(tmp_path, monkeypatch):
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    folder = tmp_path / 'outputs/checkpoint'; folder.mkdir(parents=True)
    bundle = {'release_checkpoint': 'checkpoint', 'product_runs': {'weekly': 'fake'},
              'product_summary_hashes': {'weekly': 'digest'}, 'customer_delivery_days': 7}
    (folder / 'delivery.json').write_text(json.dumps(bundle))
    (folder / 'readiness.csv').write_text('fake')
    info = {'kind': 'local_product_release_checkpoint', 'status': 'integrity_verified',
            'product_runs': bundle['product_runs'], 'parent_hashes': bundle['product_summary_hashes'],
            'files': {p.name: sha256(p) for p in folder.iterdir()}}
    (folder / 'summary.json').write_text(json.dumps(info))
    assert release.load_checkpoint(bundle)[0] == folder
    with pytest.raises(ValueError, match='Active bundle'):
        release.load_checkpoint({**bundle, 'customer_delivery_days': 8})
    (folder / 'readiness.csv').write_text('changed')
    with pytest.raises(ValueError, match='changed'): release.load_checkpoint(bundle)


def test_bad_product_config_stops_with_helpful_message_without_artifact_fallback(tmp_path, monkeypatch):
    from sigma.delivery import customer
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(customer, 'ROOT', tmp_path)
    path = tmp_path / 'bad.json'; path.write_text('{"customer_delivery_days": 6}')
    monkeypatch.setenv('SIGMA_DELIVERY_CONFIG', str(path))
    at = AppTest.from_file(str(ROOT / 'sigma/ui/product.py')).run()
    assert not at.exception and len(at.error) == 1
    assert 'D+7' in at.error[0].value and not at.dataframe
