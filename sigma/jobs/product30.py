"""Refresh sealed M3 inputs, skip unchanged runs and preserve the last good run."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from src.common import ROOT, sha256
from sigma.forecasting.aggregate import validate_aggregate
from sigma.inventory.product30 import execute, validate_product
from sigma.jobs.refresh import refresh


class SourceChangedError(ValueError):
    """A new observed snapshot requires its own validated forecast parent."""


def settings(path='data/configs/product30-focus.json'):
    path=Path(path)
    if not path.is_absolute():path=ROOT/path
    path=path.resolve()
    if not path.is_relative_to(ROOT):raise ValueError('Configuration must be in this project')
    cfg=json.loads(path.read_text(encoding='utf-8'))
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+',cfg[k]) for k in ['aggregate_run','product_run']):
        raise ValueError('Invalid configured run')
    if cfg['window_days']!=30 or cfg['customer_delivery_days']!=7:raise ValueError('Unexpected M3 protocol')
    return path,cfg


def current_fingerprint(path):
    path,cfg=settings(path);parent=ROOT/'outputs'/cfg['aggregate_run']
    info=validate_aggregate(parent)
    receipt=ROOT/'outputs'/(cfg['aggregate_run']+'_verification.json')
    checked=json.loads(receipt.read_text(encoding='utf-8'))
    if checked.get('status')!='verified' or checked['summary_sha256']!=sha256(parent/'summary.json'):
        raise ValueError('Aggregate forecast must have matching independent verification')
    protocol=json.loads((parent/'protocol.json').read_text(encoding='utf-8'))
    raw=ROOT/protocol['config']['source']
    if sha256(raw)!=info['source_sha256']:
        raise SourceChangedError('Create and verify a fresh forecast run before refreshing M3')
    paths=[path,raw,parent/'summary.json',ROOT/'sigma/inventory/product30.py',ROOT/'src/inventory.py',
        ROOT/'src/transactions.py',ROOT/'sigma/delivery/customer.py',ROOT/'sigma/jobs/product30.py']
    digest=hashlib.sha256()
    for p in paths:
        digest.update(p.relative_to(ROOT).as_posix().encode());digest.update(sha256(p).encode())
    return digest.hexdigest()


def execute_refresh(config='data/configs/product30-focus.json'):
    path,cfg=settings(config)
    def worker(run_id):
        execute(run_id,cfg['aggregate_run'],cfg['window_days'])
        from sigma.verification.product30 import execute as verify
        verify(run_id)
    def validator(folder):
        info=validate_product(folder)
        if info['aggregate_run']!=cfg['aggregate_run'] or info['forecast_window_days']!=cfg['window_days']:
            raise ValueError('Job forecast parent differs')
        protocol=json.loads((folder/'protocol.json').read_text())
        if any(sha256(ROOT/f)!=v for f,v in protocol['implementation_modules_sha256'].items()):
            raise ValueError('M3 implementation changed; create a new product run')
        receipt=ROOT/'outputs'/(info['run_id']+'_verification.json')
        verified=json.loads(receipt.read_text(encoding='utf-8'))
        if verified.get('status')!='verified' or verified['summary_sha256']!=sha256(folder/'summary.json'):
            raise ValueError('M3 independent verification is missing or stale')
    existing=ROOT/'outputs'/cfg['product_run']/'summary.json'
    initial=None
    if existing.is_file():
        info=json.loads(existing.read_text())
        if info.get('aggregate_run')==cfg['aggregate_run']:initial=cfg['product_run']
    namespace=hashlib.sha256(path.relative_to(ROOT).as_posix().encode()).hexdigest()[:12]
    return refresh(job_folder=ROOT/'outputs/jobs'/('m3_'+namespace),worker=worker,
        get_fingerprint=lambda:current_fingerprint(path),validator=validator,
        initial_run=initial,run_prefix='sigma_m3_job_')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',default='data/configs/product30-focus.json')
    a=p.parse_args();result=execute_refresh(a.config);print(json.dumps(result));raise SystemExit(result['status']=='failed')
