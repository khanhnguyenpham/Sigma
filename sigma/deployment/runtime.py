"""Read a reviewed result release without raw orders or training dependencies."""
import hashlib
import json
from pathlib import Path

import pandas as pd


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(folder, expected_digest=None):
    folder=Path(folder).resolve(); manifest=folder/'manifest.json'
    if expected_digest and digest(manifest)!=expected_digest:
        raise ValueError('Release manifest differs from the approved package')
    meta=json.loads(manifest.read_text(encoding='utf-8'))
    if (meta.get('kind')!='sigma_verified_portable_v1' or meta.get('raw_orders_included') is not False
            or meta.get('data_kind')!='provided_order_snapshot'):
        raise ValueError('Unsupported release provenance')
    summary=meta['summary']
    if summary.get('project_fully_accepted') is not False:
        raise ValueError('Unexpected acceptance claim')
    if set(meta['files'])!={x['file'] for x in meta['tables'].values()}:
        raise ValueError('Release tables do not match sealed files')
    for name,expected in meta['files'].items():
        path=(folder/name).resolve()
        if Path(name).name!=name or not path.is_relative_to(folder) or digest(path)!=expected:
            raise ValueError('Release table missing or changed')
    bundle={key:meta[key] for key in ['summary','verification','protocol','scenario_configs']}
    for key,spec in meta['tables'].items():
        frame=pd.read_csv(folder/spec['file'],float_precision='round_trip')
        if list(frame.columns)!=spec['columns'] or len(frame)!=spec['rows']:
            raise ValueError('Release table shape differs')
        if set(frame)&{'order_id','customer_id','event_id','order_datetime','activation_datetime','email','phone','token'}:
            raise ValueError('Private identifiers are forbidden')
        for col in frame:
            if col in ['date','eta','as_of_date','target_date','order_date','delivery_date','selection_cutoff'] or col.endswith('_depletion_date'):
                frame[col]=pd.to_datetime(frame[col])
        bundle[key]=frame
    return bundle
