import json

from sigma.jobs.refresh import refresh


def test_adopt_then_skip_without_rerunning_policy(tmp_path,monkeypatch):
    import sigma.jobs.refresh as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    folder=tmp_path/'job';validated=[];called=[]
    validator=lambda path:validated.append(path.name)
    worker=lambda run:called.append(run)
    result=refresh(folder,worker,lambda:'fixed',validator,initial_run='synthetic_m3',run_prefix='synthetic_m3_')
    assert result=={'status':'adopted_existing','last_good_run':'synthetic_m3'}
    result=refresh(folder,worker,lambda:'fixed',validator,initial_run='synthetic_m3')
    assert result['status']=='skipped_unchanged' and not called
    assert json.loads((folder/'state.json').read_text())['last_good_run']=='synthetic_m3'


def test_failed_new_input_keeps_last_good_and_overlap_skips(tmp_path,monkeypatch):
    import sigma.jobs.refresh as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    folder=tmp_path/'job'
    refresh(folder,lambda run:None,lambda:'first',lambda path:None,initial_run='synthetic_good')
    before=(folder/'state.json').read_bytes()
    def failing(run):raise ValueError('synthetic failure')
    result=refresh(folder,failing,lambda:'changed',lambda path:None,run_prefix='synthetic_m3_')
    assert result['status']=='failed' and result['last_good_run']=='synthetic_good'
    assert (folder/'state.json').read_bytes()==before
    (folder/'refresh.lock').write_text('another-worker')
    result=refresh(folder,failing,lambda:'changed',lambda path:None)
    assert result['status']=='skipped_running' and (folder/'state.json').read_bytes()==before
