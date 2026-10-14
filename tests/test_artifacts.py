import json

import pandas as pd
import pytest

from src.common import ROOT, seal_manifest, validate_run, write_csv, write_json, sha256
from M2.final_report import verify_run


def test_incomplete_and_tampered_runs_rejected(tmp_path):
    write_csv(tmp_path / 'a.csv', pd.DataFrame({'quantity': [3]}))
    manifest = {'status': 'partial'}
    seal_manifest(tmp_path, manifest)
    with pytest.raises(ValueError, match='incomplete'): validate_run(tmp_path)
    manifest['status'] = 'complete'
    seal_manifest(tmp_path, manifest)
    assert validate_run(tmp_path)['status'] == 'complete'
    (tmp_path / 'a.csv').write_text('quantity\n4\n')
    with pytest.raises(ValueError, match='changed'): validate_run(tmp_path)


def test_manifest_rejects_path_escape(tmp_path):
    (tmp_path / 'manifest.json').write_text(json.dumps({'status': 'complete', 'files': {'../private.csv': 'fake'}}))
    with pytest.raises(ValueError, match='Invalid manifest path'): validate_run(tmp_path)


def test_notebook_has_no_outputs():
    import nbformat
    nb = nbformat.read(ROOT / 'M2/notebooks/final_report.ipynb', as_version=4)
    assert all(not cell.get('outputs') and cell.get('execution_count') is None for cell in nb.cells)


def test_verification_rejects_unsafe_run_id():
    with pytest.raises(ValueError, match='Invalid run ID'): verify_run('../outside')


def test_historical_code_is_not_certified_as_current(tmp_path, monkeypatch):
    import M2.final_report as final
    config = tmp_path / final.CONFIG
    config.parent.mkdir(parents=True)
    config.write_text('{}')
    folder = tmp_path / 'M2/artifacts/old'
    folder.mkdir(parents=True)
    seal_manifest(folder, {'status': 'complete', 'config': {}, 'experiment': {},
        'config_sha256': '0'*64, 'runner_sha256': '0'*64,
        'implementation_modules_sha256': {'removed.py': '0'*64}})
    monkeypatch.setattr(final, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='Recorded code differs'):
        final.verify_run('old')


def test_export_uses_new_report_folder_and_never_overwrites(tmp_path, monkeypatch):
    import M2.final_report as final
    from M2.models.families import metrics, monthly_metrics
    from tests.test_final_parity import synthetic_bundle
    _, cfg, settings, exp = synthetic_bundle()
    frame = pd.read_csv(ROOT / 'tests/fixtures/m2_final_parity.csv',
        parse_dates=['as_of_date', 'target_date', 'window_start'], float_precision='round_trip')
    cfg = {**cfg, 'test_start': cfg['validation_start'], 'test_end': cfg['validation_end']}
    folder = tmp_path / 'M2/artifacts/synthetic'
    folder.mkdir(parents=True)
    write_csv(folder / 'selected_models.csv', pd.DataFrame(exp['routes']).assign(target='direct_7d'))
    table = metrics(frame.assign(split='test'), cfg)
    write_csv(folder / 'test_metrics.csv', table)
    write_csv(folder / 'validation_metrics.csv', metrics(frame, cfg))
    write_csv(folder / 'validation_monthly_metrics.csv', monthly_metrics(frame, cfg))
    primary = table.loc[table.block.eq(1) & table.cadence.eq('daily_origins')]
    seal_manifest(folder, {'status': 'complete', 'experiment': exp, 'settings': settings, 'config': cfg,
        'source_sha256': 'synthetic-fixture', 'selection_limit': 'synthetic fixture only',
        'result': {'routes_below_20_pct': int(primary.mape_positive_pct.lt(20).sum()),
            'mean_mape_positive_pct': primary.mape_positive_pct.mean(), 'minimum_coverage': 1.}})
    write_json(folder.with_name('synthetic_review.json'),
        {'status': 'verified', 'run_manifest_sha256': sha256(folder / 'manifest.json')})
    monkeypatch.setattr(final, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='Invalid report ID'):
        final.export_report('synthetic', '../outside')
    output = final.export_report('synthetic', 'synthetic_report')
    assert len(final.load_report(output)['routes']) == 10
    with pytest.raises(FileExistsError): final.export_report('synthetic', 'synthetic_report')
