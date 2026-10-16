import json

import pytest

from src.common import ROOT
from sigma.forecasting.aggregate import load_settings
from sigma.experiments.aggregate_recent import candidate_settings, check_run_id


def test_twelve_registered_settings_do_not_mutate_parent():
    _,parent=load_settings()
    before=json.dumps(parent,sort_keys=True)
    options=json.loads((ROOT/'data/configs/aggregate-recent.json').read_text())
    assert len(options['models'])==12
    for name,spec in options['models'].items():
        derived=candidate_settings(parent,name,spec)
        assert derived['training_window_days'] in [180,270,365]
        assert list(derived['models'])==[name]
        assert derived['refit_days']==7 and derived['lightgbm']==parent['lightgbm']
    assert json.dumps(parent,sort_keys=True)==before


@pytest.mark.parametrize('name',['../escape','x/y','x\\y','', 'bad name'])
def test_research_run_paths_stay_in_outputs(name):
    with pytest.raises(ValueError):check_run_id(name)
