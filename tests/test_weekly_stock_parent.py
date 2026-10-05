"""A snapshot must use balances from its own authenticated policy and source."""
import json

import pytest

import sigma.inventory.snapshot as stock
from src.common import sha256, write_json


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(stock, 'ROOT', tmp_path)
    folder = tmp_path / 'outputs' / 'policy'
    folder.mkdir(parents=True)
    cfg = {'inventory': {'lead_time_days': 3}}
    write_json(folder / 'protocol.json', {'config': cfg})
    write_json(folder / 'summary.json', {'weekly_run': 'week', 'daily_run': 'day', 'source_sha256': 'digest'})
    monkeypatch.setattr(stock, 'validate_policy', lambda path: json.loads((path / 'summary.json').read_text()))
    return folder, cfg


def test_stock_parent_records_own_policy_and_preserves_legacy_daily(tmp_path, monkeypatch):
    folder, cfg = fixture(tmp_path, monkeypatch)
    path, info = stock.stock_parent('policy', 'week', 'day', cfg, 'digest')
    assert path == folder and info['stock_source_run'] == 'policy'
    assert info['stock_policy_summary_sha256'] == sha256(folder / 'summary.json')
    path, info = stock.stock_parent(None, 'week', 'day', cfg, 'digest')
    assert path == tmp_path / 'outputs' / 'day' and info['stock_policy_run'] is None


@pytest.mark.parametrize('change', ['week', 'day', 'source', 'supplier_lead_time'])
def test_stock_parent_blocks_mixed_or_changed_protocols(tmp_path, monkeypatch, change):
    _, cfg = fixture(tmp_path, monkeypatch)
    week, day, digest = 'week', 'day', 'digest'
    if change == 'week':
        week = 'other'
    elif change == 'day':
        day = 'other'
    elif change == 'source':
        digest = 'other'
    else:
        cfg = {'inventory': {'lead_time_days': 7}}
    with pytest.raises(ValueError, match='does not match'):
        stock.stock_parent('policy', week, day, cfg, digest)


def test_stock_parent_rejects_path_escape_and_propagates_integrity_failure(tmp_path, monkeypatch):
    _, cfg = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='Invalid'):
        stock.stock_parent('../policy', 'week', 'day', cfg, 'digest')
    def reject(path):
        raise ValueError('Policy evidence changed')
    monkeypatch.setattr(stock, 'validate_policy', reject)
    with pytest.raises(ValueError, match='changed'):
        stock.stock_parent('policy', 'week', 'day', cfg, 'digest')
