"""Local refresh job: skip unchanged inputs, prevent overlap, retain last good run.

Consumes completed forecast/inventory parents. Changed raw data require a new
forecast run rather than silently extending splits or fitting on future labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from delivery import execute, delivery_settings, validate_delivery
from src.common import ROOT, read_config, sha256, write_json


def fingerprint():
    settings = delivery_settings()
    cfg = read_config(settings['base_config'])
    paths = [ROOT / 'config.delivery.json', ROOT / settings['base_config'], ROOT / cfg['source'],
        ROOT / cfg['output_root'] / settings['weekly_run'] / 'summary.json',
        ROOT / cfg['output_root'] / settings['daily_run'] / 'manifest.json', ROOT / 'delivery.py']
    digest = hashlib.sha256()
    for path in paths:
        path = path.resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Refresh input missing or outside project')
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(sha256(path).encode())
    return digest.hexdigest()


def refresh(job_folder=None, worker=execute, get_fingerprint=fingerprint, validator=validate_delivery):
    folder = Path(job_folder) if job_folder else ROOT / 'outputs' / 'jobs' / 'customer_delivery'
    folder = folder.resolve()
    if not folder.is_relative_to(ROOT.resolve()):
        raise ValueError('Job state must remain local to this project')
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / 'refresh.lock'
    token = uuid4().hex
    try:
        with lock.open('x', encoding='utf-8') as stream:
            stream.write(token)
    except FileExistsError:
        return {'status': 'skipped_running', 'last_good_run_modified': False}
    previous = {}
    state_path = folder / 'state.json'
    try:
        if state_path.is_file():
            previous = json.loads(state_path.read_text(encoding='utf-8'))
            if previous.get('last_good_run') and not re.fullmatch(r'[A-Za-z0-9_-]+', previous['last_good_run']):
                raise ValueError('Invalid cached run id')
        current = get_fingerprint()
        if previous.get('fingerprint') == current and previous.get('last_good_run'):
            validator(ROOT / 'outputs' / previous['last_good_run'])
            return {'status': 'skipped_unchanged', 'last_good_run': previous['last_good_run']}
        run_id = 'sigma_delivery_job_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        worker(run_id)
        if get_fingerprint() != current:
            raise ValueError('Inputs changed during refresh')
        validator(ROOT / 'outputs' / run_id)
        state = {'fingerprint': current, 'last_good_run': run_id,
            'updated_at_utc': datetime.now(timezone.utc).isoformat()}
        write_json(state_path, state)
        write_json(folder / 'last_attempt.json', {'status': 'complete', 'run_id': run_id})
        return {'status': 'complete', 'last_good_run': run_id}
    except Exception as error:
        # Exception text could include private values; only store the category.
        result = {'status': 'failed', 'error_category': type(error).__name__,
            'last_good_run': previous.get('last_good_run'), 'last_good_run_modified': False}
        write_json(folder / 'last_attempt.json', result)
        return result
    finally:
        if lock.is_file() and lock.read_text(encoding='utf-8') == token:
            lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = refresh()
    print(json.dumps(result))
    raise SystemExit(1 if result['status'] == 'failed' else 0)
