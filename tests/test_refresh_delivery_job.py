"""Refresh isolation and failure handling; no model runs or real input data."""
import json

import refresh_delivery_job as job


def test_refresh_skips_unchanged_inputs_after_one_success(tmp_path, monkeypatch):
    monkeypatch.setattr(job, 'ROOT', tmp_path)
    calls = []
    worker = lambda run_id: calls.append(run_id)
    first = job.refresh(worker=worker, get_fingerprint=lambda: 'A', validator=lambda p: {})
    second = job.refresh(worker=worker, get_fingerprint=lambda: 'A', validator=lambda p: {})
    assert first['status'] == 'complete' and second['status'] == 'skipped_unchanged'
    assert first['last_good_run'] == second['last_good_run'] and len(calls) == 1
    assert not (tmp_path / 'outputs/jobs/customer_delivery/refresh.lock').exists()


def test_refresh_failure_retains_state_and_never_logs_private_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(job, 'ROOT', tmp_path)
    folder = tmp_path / 'outputs/jobs/customer_delivery'; folder.mkdir(parents=True)
    state = {'fingerprint': 'old', 'last_good_run': 'fake_known_good'}
    path = folder / 'state.json'; path.write_text(json.dumps(state))
    before = path.read_bytes()
    def worker(run_id):
        raise RuntimeError('PRIVATE_TEST_VALUE_MUST_NOT_BE_LOGGED')
    result = job.refresh(worker=worker, get_fingerprint=lambda: 'changed', validator=lambda p: {})
    assert result['status'] == 'failed' and result['last_good_run'] == 'fake_known_good'
    assert path.read_bytes() == before
    assert 'PRIVATE_TEST_VALUE' not in (folder / 'last_attempt.json').read_text()


def test_refresh_existing_lock_prevents_overlap_and_is_not_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(job, 'ROOT', tmp_path)
    folder = tmp_path / 'outputs/jobs/customer_delivery'; folder.mkdir(parents=True)
    lock = folder / 'refresh.lock'; lock.write_text('another_worker')
    calls = []
    result = job.refresh(worker=lambda name: calls.append(name), get_fingerprint=lambda: 'A', validator=lambda p: {})
    assert result['status'] == 'skipped_running' and not calls
    assert lock.read_text() == 'another_worker'


def test_refresh_changed_inputs_during_run_cannot_advance_good_state(tmp_path, monkeypatch):
    monkeypatch.setattr(job, 'ROOT', tmp_path)
    changes = iter(['before', 'after'])
    result = job.refresh(worker=lambda name: {}, get_fingerprint=lambda: next(changes), validator=lambda p: {})
    assert result['status'] == 'failed' and result['last_good_run'] is None
    assert not (tmp_path / 'outputs/jobs/customer_delivery/state.json').exists()


def test_refresh_revalidates_cached_run_before_skipping(tmp_path, monkeypatch):
    monkeypatch.setattr(job, 'ROOT', tmp_path)
    folder = tmp_path / 'outputs/jobs/customer_delivery'; folder.mkdir(parents=True)
    state = {'fingerprint': 'A', 'last_good_run': 'tampered_fake'}
    (folder / 'state.json').write_text(json.dumps(state))
    def validator(path):
        raise ValueError('changed artifact')
    result = job.refresh(worker=lambda name: {}, get_fingerprint=lambda: 'A', validator=validator)
    assert result['status'] == 'failed'
