"""Forecast-floor C00 uses the app kernel and separate physical/event checks."""
from copy import deepcopy

import pytest

from test_fixed_lot_baseline import fixture
from web.backend.research.forecast_floor_c00 import evaluate
from web.backend.research import fixed_lot_verification as independent


def test_c00_forecast_floor_replay_and_independent_reconstruction():
    source=fixture()
    policies=[dict(p,moq=None,fixed_order_qty=5) for p in source['policies']]
    original=deepcopy((source,policies))
    result,cases,metrics=evaluate(source,policies,dict(cover=7,multiplier=1))
    assert all(r['ss']==3 and r['rop']==13 for r in result['ledger'])
    assert all(o['ordered_qty']==5 for o in result['orders'])
    assert metrics['event_denominator']==len(cases)
    assert (source,policies)==original
    adapted={**source,'policies':policies}
    for section,field in [('ledger','rop'),('orders','ordered_qty'),('alarms','origin_on_hand')]:
        changed=deepcopy(result)
        changed[section][0][field]+=1
        with pytest.raises(ValueError):
            independent.reconstruct(adapted,policies,dict(cover=7,multiplier=1),changed)
