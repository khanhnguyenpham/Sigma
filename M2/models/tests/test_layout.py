"""Relocation preserves imports, sealed artifacts and historical source checks."""
import json
import pytest

from src.common import ROOT, sha256
from M2.models import families, verify, registry


def test_canonical_imports_configuration_and_registered_output_location():
    import sigma.forecasting.families as legacy_model
    import sigma.verification.model_families as legacy_verifier
    assert legacy_model is families and legacy_verifier is verify
    settings=json.loads((ROOT/'M2/models/model_families.json').read_text())
    assert settings['artifact_root']=='M2/artifacts'
    assert families.run.__defaults__==('M2/models/model_families.json',None)
    assert set(settings['models'])=={'LightGBM','SARIMA','Prophet'}


def test_registering_another_family_loads_its_own_variants(monkeypatch,tmp_path):
    monkeypatch.setattr(registry,'ROOT',tmp_path)
    monkeypatch.setitem(registry.REGISTRY,'Example',object())
    variant_path=tmp_path/'M2/models/Example/variants.json'
    variant_path.parent.mkdir(parents=True)
    variant_path.write_text(json.dumps({'example_v1':{'window':7}}))
    config=tmp_path/'config.json'
    config.write_text(json.dumps({'models':{'Example':'M2/models/Example/variants.json'}}))
    assert registry.load_settings(config)['models']=={'Example':{'example_v1':{'window':7}}}


def test_unknown_family_and_outside_variant_path_fail_before_fitting(monkeypatch,tmp_path):
    monkeypatch.setattr(registry,'ROOT',tmp_path)
    config=tmp_path/'config.json'
    config.write_text(json.dumps({'models':{'Unknown':{'x':{}}}}))
    with pytest.raises(ValueError,match='Unregistered model family'):
        registry.load_settings(config)
    config.write_text(json.dumps({'models':{'LightGBM':'outside.json'}}))
    with pytest.raises(ValueError,match='inside M2/models'):
        registry.load_settings(config)


def test_historical_source_requires_matching_content_not_a_new_hash(monkeypatch,tmp_path):
    monkeypatch.setattr(verify,'ROOT',tmp_path)
    current=tmp_path/'module.py'; current.write_text('old implementation')
    digest=sha256(current)
    assert verify.recorded_source('module.py',digest)==current
    current.write_text('moved implementation')
    with pytest.raises(ValueError,match='exact historical snapshot'):
        verify.recorded_source('module.py',digest)
    snapshot=tmp_path/'M2/artifacts/source_snapshots'/digest/'module.py'
    snapshot.parent.mkdir(parents=True); snapshot.write_text('old implementation')
    assert verify.recorded_source('module.py',digest)==snapshot
    snapshot.write_text('wrong snapshot')
    with pytest.raises(ValueError,match='exact historical snapshot'):
        verify.recorded_source('module.py',digest)
