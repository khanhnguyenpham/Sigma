"""The report retains the approved shortfall; synthetic evidence only."""
import json
import pandas as pd
import pytest
from M2 import presentation
from src.common import config_path, seal_manifest, sha256, write_csv, write_json


def test_config_move_resolves_historical_bundle_paths_without_changing_values(tmp_path):
    path = tmp_path / 'data/configs/config.json'
    path.parent.mkdir(parents=True)
    path.write_text('{"synthetic": true}')
    assert config_path('config.json', root=tmp_path) == path
    assert config_path(path, root=tmp_path) == path
    assert config_path('custom.json', root=tmp_path) == tmp_path / 'custom.json'
    assert config_path(tmp_path.parent/'config.json', root=tmp_path) == tmp_path.parent/'config.json'


def test_report_requires_the_approved_deferred_route_and_complete_coverage(tmp_path, monkeypatch):
    folder = tmp_path / 'M2/artifacts' / presentation.RUN_ID
    review = tmp_path / 'M2/reports' / presentation.REVIEW_ID
    folder.mkdir(parents=True); review.mkdir(parents=True)
    carriers = ['LG U+'] + [f'Synthetic{i}' for i in range(9)]
    choices = pd.DataFrame([{'destination_country': 'South Korea', 'carrier': carrier,
                            'family': 'LightGBM', 'model': 'synthetic', 'target': target,
                            'validation_mape_positive_pct': 10.}
                           for target in ('daily', 'direct_7d') for carrier in carriers])
    metrics = choices.drop(columns='validation_mape_positive_pct').copy()
    metrics['block'] = 1; metrics['cadence'] = 'daily_origins'; metrics['coverage'] = 1.
    metrics['mape_positive_pct'] = [40.]*10 + [20.69] + [10.]*9
    metrics['passes_20_pct'] = metrics.mape_positive_pct.le(20)
    write_csv(folder/'overall_selected_models.csv', choices)
    write_csv(folder/'overall_test_metrics.csv', metrics)
    write_csv(folder/'summary.csv', pd.DataFrame({'synthetic': [True]}))
    write_json(folder/'data_audit.json', {'synthetic': True})
    monthly = metrics.copy(); monthly['month'] = '2025-07'
    write_csv(review/'validation_monthly_selected.csv', monthly)
    def seal():
        seal_manifest(folder, {'status': 'complete'})
        digest = sha256(folder/'manifest.json')
        monkeypatch.setattr(presentation, 'MANIFEST_SHA', digest)
        write_json(review/'summary.json', {'status':'verified', 'run_manifest_sha256':digest,
                   'files':{'validation_monthly_selected.csv':sha256(review/'validation_monthly_selected.csv')}})
    seal()
    evidence = presentation.load_checkpoint(tmp_path)
    assert len(evidence['weekly']) == 10 and evidence['weekly'].passes_20_pct.sum() == 9
    assert evidence['daily'].passes_20_pct.sum() == 0
    metrics.loc[metrics.target.eq('direct_7d'), 'coverage'] = .5
    write_csv(folder/'overall_test_metrics.csv', metrics); seal()
    with pytest.raises(ValueError, match='coverage or acceptance'):
        presentation.load_checkpoint(tmp_path)
    metrics['coverage'] = 1.
    mask = metrics.target.eq('direct_7d')
    metrics.loc[mask, 'passes_20_pct'] = [True,False]+[True]*8
    write_csv(folder/'overall_test_metrics.csv', metrics); seal()
    with pytest.raises(ValueError, match='Deferred M2 route'):
        presentation.load_checkpoint(tmp_path)
