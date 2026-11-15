import pytest
from core import hashes


def test_immutable_release_does_not_scan_source_or_invoke_git(monkeypatch,tmp_path):
    monkeypatch.setenv('M3_RELEASE_VERSION','v1.2.3')
    monkeypatch.setattr(hashes,'PROJECT_ROOT',tmp_path/'no-source-files')
    first=hashes.code_digest()
    assert len(first)==64 and hashes.revision()=='v1.2.3'
    monkeypatch.setenv('M3_RELEASE_VERSION','v1.2.4')
    assert hashes.code_digest()!=first
    assert hashes.runtime_reference()['mode']=='immutable-release-v1'


def test_editable_local_keeps_source_change_detection(monkeypatch,tmp_path):
    monkeypatch.delenv('M3_RELEASE_VERSION',raising=False)
    monkeypatch.setattr(hashes,'PROJECT_ROOT',tmp_path)
    for name in ['M2/final_report.py','web/backend/scripts/demo_stack.py','web/backend/src/example.py']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('before')
    before=hashes.code_digest()
    (tmp_path/'web/backend/src/example.py').write_text('after')
    assert hashes.code_digest()!=before and hashes.runtime_reference() is None


@pytest.mark.parametrize('version',['not-a-release','https://example.invalid','v1.2.3\nTOKEN','x'*100])
def test_invalid_runtime_reference_fails_without_echoing_input(monkeypatch,version):
    monkeypatch.setenv('M3_RELEASE_VERSION',version)
    with pytest.raises(ValueError,match='requires a commit SHA or semantic release'):
        hashes.code_digest()
