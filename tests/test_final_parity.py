"""Synthetic golden replay captured before cleanup; no private order rows."""
import json

import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, read_config
from M2.final_report import CONFIG, check_pairs, configurations, focus_experiment, parity, replay
from M2.models.focus import verify_heads
from M2.models.registry import load_settings


def synthetic_bundle():
    exp = json.loads((ROOT / CONFIG).read_text(encoding='utf-8'))
    settings = load_settings(ROOT / exp['model_config'])
    cfg = {**read_config(exp['base_config']), 'validation_end': '2025-07-15'}
    dates = pd.date_range('2024-01-01', '2025-12-31')
    t = np.arange(len(dates))
    parts = []
    for i, route in enumerate(exp['routes']):
        values = (4 + i + t % 7 + (t // 23) % 5).astype(float)
        values[(t + i) % 37 == 0] = 0
        parts.append(pd.DataFrame({'date': dates,
            **{name: route[name] for name in ROUTE},
            'sales_qty': values, 'order_count': np.ceil(values / 2)}))
    return pd.concat(parts, ignore_index=True), cfg, settings, exp


def test_final_replay_matches_pre_cleanup_forecasts():
    daily, cfg, settings, exp = synthetic_bundle()
    frame, logs = replay(daily, cfg, settings, exp, 'validation')
    expected = pd.read_csv(ROOT / 'tests/fixtures/m2_final_parity.csv',
        parse_dates=['as_of_date', 'target_date', 'window_start'], float_precision='round_trip')
    assert check_pairs(frame, daily, cfg, exp, 'validation') == 300
    comparison = parity(frame, expected, 1e-8)
    assert comparison['pairs'] == 300
    print('Pre-cleanup synthetic parity:', comparison)
    assert len(configurations(exp, settings)) == 10
    assert verify_heads(logs['focus'], focus_experiment(exp), daily) == 6
    for log in logs.values():
        assert not log.status.eq('failed').any()
        observed = log.loc[log.max_label_end.notna()]
        assert (observed.max_label_end <= observed.fit_cutoff).all()
