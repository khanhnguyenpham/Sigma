"""Weekly stock decisions: conservation, pending ETA and causal snapshots."""
import copy

import numpy as np
import pandas as pd
import pytest

from src.common import ITEM, read_config
from sigma.inventory.snapshot import pending_orders, snapshot_recommendations, complete_replay_forecasts


def inputs():
    cfg = copy.deepcopy(read_config())
    cfg['inventory']['partner_map'] = {'A': 'P'}
    cfg['inventory']['partners'] = {'P': {'lead_time_days': 3, 'review_days': 1, 'safety_days': 2, 'moq': 1}}
    cfg['inventory']['initial_receipts'] = []
    origin = pd.Timestamp('2025-12-31')
    key = ('Fake', 'A', 'S', 'data')
    matrix = pd.DataFrame(10., index=pd.date_range('2025-01-01', '2026-01-14'),
        columns=pd.MultiIndex.from_tuples([key], names=ITEM))
    forecast = pd.DataFrame({'destination_country': 'Fake', 'carrier': 'A',
        'as_of_date': origin, 'horizon_day': range(1, 15), 'forecast_qty': 30.})
    ledger = pd.DataFrame([{**dict(zip(ITEM, key)), 'date': origin, 'scenario_id': 'base', 'closing': 100}])
    prior = pd.DataFrame([{**dict(zip(ITEM, key)), 'as_of_date': origin - pd.Timedelta(days=1),
        'scenario_id': 'base', 'Q': 50, 'eta': origin + pd.Timedelta(days=2)}])
    return matrix, forecast, ledger, prior, cfg, origin


def test_weekly_snapshot_hand_calculation_and_no_double_deduction():
    row = snapshot_recommendations(*inputs()).iloc[0]
    assert (row.on_hand, row.pending_quantity, row.SS, row.ROP, row.S, row.IP, row.Q) == (100, 50, 60, 150, 180, 150, 30)
    assert row.needs_replenishment and not row.decision_applied
    assert row.eta_if_ordered == pd.Timestamp('2026-01-03')


def test_pending_orders_excludes_received_future_decisions_and_other_scenarios():
    _, _, _, prior, cfg, origin = inputs()
    rows = pd.concat([prior, prior.assign(eta=origin),
        prior.assign(as_of_date=origin + pd.Timedelta(days=1)), prior.assign(scenario_id='stress')])
    result = pending_orders(rows, cfg, origin)
    assert len(result) == 1 and result[0]['quantity'] == 50
    with pytest.raises(ValueError, match='Duplicate'):
        pending_orders(pd.concat([prior, prior]), cfg, origin)


def test_weekly_snapshot_future_mutation_and_stale_forecast():
    args = list(inputs())
    a = snapshot_recommendations(*args)
    args[0].loc[args[0].index > args[-1]] = 999999.
    pd.testing.assert_frame_equal(a, snapshot_recommendations(*args))
    args[1]['as_of_date'] = args[-1] - pd.Timedelta(days=1)
    with pytest.raises(ValueError, match='Stale'):
        snapshot_recommendations(*args)


def test_weekly_replay_requires_both_blocks_and_conserves_totals():
    _, _, _, _, cfg, _ = inputs()
    cfg['test_start'], cfg['test_end'] = '2025-10-01', '2025-10-14'
    daily = pd.DataFrame({'date': pd.date_range('2025-01-01', '2025-10-14'),
        'destination_country': 'Fake', 'carrier': 'A', 'sales_qty': 10., 'order_count': 1})
    predictions = pd.DataFrame({'destination_country': 'Fake', 'carrier': 'A',
        'as_of_date': pd.Timestamp('2025-09-30'), 'week_block': [1, 2], 'forecast_qty_7d': [70., 140.]})
    result = complete_replay_forecasts(predictions, daily, cfg)
    assert len(result) == 14
    np.testing.assert_allclose(result.forecast_qty.to_numpy(), [10.] * 7 + [20.] * 7, rtol=0, atol=1e-8)
    with pytest.raises(ValueError, match='Missing complete'):
        complete_replay_forecasts(predictions.iloc[:1], daily, cfg)
