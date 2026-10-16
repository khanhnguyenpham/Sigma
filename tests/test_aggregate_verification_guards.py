import pytest


@pytest.mark.parametrize('module',['sigma.verification.aggregate','sigma.verification.product30'])
@pytest.mark.parametrize('run_id,output',[('../outside',None),('synthetic','../../outside.json')])
def test_verification_rejects_path_traversal_before_io(module,run_id,output):
    import importlib
    with pytest.raises(ValueError,match='Invalid local evidence name'):
        importlib.import_module(module).execute(run_id,output)
