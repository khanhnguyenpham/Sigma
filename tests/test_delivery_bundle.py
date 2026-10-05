"""A synthetic bundle must not replace the configured snapshot or job state."""
import json

import pytest

import sigma.delivery.customer as delivery
import refresh_delivery_job as job
from src.common import ROOT


def test_environment_selects_local_bundle_and_explicit_argument_wins(tmp_path, monkeypatch):
    settings = json.loads((ROOT / 'config.delivery.json').read_text())
    (tmp_path / 'custom.json').write_text(json.dumps({**settings, 'weekly_run': 'fake_demo'}))
    (tmp_path / 'explicit.json').write_text(json.dumps({**settings, 'weekly_run': 'fake_other'}))
    monkeypatch.setattr(delivery, 'ROOT', tmp_path)
    monkeypatch.setenv('SIGMA_DELIVERY_CONFIG', 'custom.json')
    assert delivery.delivery_settings()['weekly_run'] == 'fake_demo'
    assert delivery.delivery_settings('explicit.json')['weekly_run'] == 'fake_other'


def test_delivery_bundle_cannot_escape_project(tmp_path, monkeypatch):
    monkeypatch.setattr(delivery, 'ROOT', tmp_path)
    monkeypatch.setenv('SIGMA_DELIVERY_CONFIG', '../outside.json')
    with pytest.raises(ValueError, match='local'):
        delivery.delivery_settings()


def test_custom_bundle_job_preserves_default_last_good_state(tmp_path, monkeypatch):
    monkeypatch.setattr(job, 'ROOT', tmp_path)
    monkeypatch.setattr(delivery, 'ROOT', tmp_path)
    monkeypatch.delenv('SIGMA_DELIVERY_CONFIG', raising=False)
    first = job.refresh(worker=lambda name: {}, get_fingerprint=lambda: 'default', validator=lambda path: {})
    state = tmp_path / 'outputs/jobs/customer_delivery/state.json'
    before = state.read_bytes()
    monkeypatch.setenv('SIGMA_DELIVERY_CONFIG', 'custom.json')
    second = job.refresh(worker=lambda name: {}, get_fingerprint=lambda: 'demo', validator=lambda path: {})
    assert first['status'] == second['status'] == 'complete'
    assert state.read_bytes() == before
    assert len(list((tmp_path / 'outputs/jobs').glob('customer_delivery_*/state.json'))) == 1


def test_explicit_default_bundle_shares_cli_and_scheduled_job_state(tmp_path, monkeypatch):
    monkeypatch.setattr(job, 'ROOT', tmp_path)
    monkeypatch.setattr(delivery, 'ROOT', tmp_path)
    monkeypatch.delenv('SIGMA_DELIVERY_CONFIG', raising=False)
    calls = []
    first = job.refresh(worker=lambda name: calls.append(name), get_fingerprint=lambda: 'same', validator=lambda path: {})
    monkeypatch.setenv('SIGMA_DELIVERY_CONFIG', 'config.delivery.json')
    scheduled = job.refresh(worker=lambda name: calls.append(name), get_fingerprint=lambda: 'same', validator=lambda path: {})
    assert scheduled['status'] == 'skipped_unchanged' and scheduled['last_good_run'] == first['last_good_run']
    assert len(calls) == 1
