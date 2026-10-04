import numpy as np
import pandas as pd
import pytest

from src.inventory import allocation, consume, partner_params, project_depletion, replenishment, run_policy, declared_receipts


def params(safety=2):
    return {"lead_time_days": 3, "review_days": 1, "safety_days": safety, "moq": 1}


def test_strict_trigger_partner_thresholds_and_ip():
    forecast = np.full(14, 10.)
    for stock, expected in [(49, True), (50, False), (51, False)]:
        assert replenishment(stock, forecast, 0, params())["needs_replenishment"] == expected
    assert replenishment(60, forecast, 0, params(4))["needs_replenishment"]
    assert not replenishment(60, forecast, 0, params(2))["needs_replenishment"]
    decision = replenishment(49, forecast, 100, params())
    assert decision["needs_replenishment"] and decision["Q"] == 0
    assert decision["IP"] == 149


def test_shortage_and_receipt_projection():
    assert consume(3, 8) == (0, 3, 5)
    forecast = np.ones(14)
    assert project_depletion(10, forecast, "2025-09-30")["state"] == "early"
    assert project_depletion(3, forecast, "2025-09-30")["state"] == "urgent"
    assert project_depletion(0, forecast, "2025-09-30")["state"] == "already_empty"
    assert project_depletion(3, forecast, "2025-09-30", [{"eta": "2025-10-02", "quantity": 20}])["days"] is None
    assert project_depletion(3, forecast, "2025-09-30", [{"eta": "2025-10-10", "quantity": 20}])["days"] == 3


def test_moq_only_positive_and_short_horizon():
    settings = {**params(), "moq": 20}
    assert replenishment(50, np.full(14, 10.), 0, settings)["Q"] == 0
    assert replenishment(49, np.full(14, 10.), 0, settings)["Q"] == 20
    with pytest.raises(ValueError):
        replenishment(0, [1, 1], 0, settings)


def test_missing_partner_no_fallback(cfg):
    with pytest.raises(ValueError, match="missing_partner_config"):
        partner_params("unconfigured", cfg)


def test_allocation_conserves_and_excludes_future(cfg):
    keys = pd.MultiIndex.from_tuples([("A", "C", "s1", "eSIM"), ("A", "C", "s2", "eSIM")])
    matrix = pd.DataFrame([[3., 1.], [3000., 0.]], index=pd.to_datetime(["2025-06-30", "2025-07-01"]), columns=keys)
    forecasts = pd.DataFrame({"destination_country": "A", "carrier": "C", "horizon_day": range(1, 15), "forecast_qty": 10.})
    allocated, issues = allocation(matrix, forecasts, "2025-06-30", cfg)
    assert not issues
    np.testing.assert_allclose(allocated[tuple(keys[0])], 7.5)
    np.testing.assert_allclose(sum(allocated.values()), 10)
    matrix.loc["2025-07-01"] = 99999
    changed, _ = allocation(matrix, forecasts, "2025-06-30", cfg)
    np.testing.assert_array_equal(allocated[tuple(keys[0])], changed[tuple(keys[0])])


def policy_fixture(cfg):
    cfg["test_start"] = "2025-10-01"; cfg["test_end"] = "2025-10-04"
    cfg["inventory"]["initial_cover_days"] = 0
    cfg["inventory"]["partner_map"] = {"C": "P"}
    cfg["inventory"]["partners"] = {"P": {"lead_time_days": 1, "review_days": 1, "safety_days": 0, "moq": 1}}
    keys = pd.MultiIndex.from_tuples([("A", "C", "S", "eSIM")])
    matrix = pd.DataFrame(3., index=pd.date_range("2025-09-01", "2025-10-04"), columns=keys)
    rows = [{"as_of_date": origin, "destination_country": "A", "carrier": "C", "horizon_day": h, "forecast_qty": 3.}
            for origin in pd.date_range("2025-09-30", "2025-10-04") for h in range(1, 15)]
    return matrix, pd.DataFrame(rows)


def test_partial_no_and_late_receipts_preserve_balance(cfg):
    matrix, forecasts = policy_fixture(cfg)
    base = {"name": "base", "demand_multiplier": 1., "receipt_fraction": 1., "receipt_delay_days": 0}
    original, _, _ = run_policy(matrix, forecasts, cfg, base)
    for name, fraction, delay in [("partial", .2, 0), ("none", 0, 0), ("late", 1, 3)]:
        ledger, _, _ = run_policy(matrix, forecasts, cfg, {**base, "name": name, "receipt_fraction": fraction, "receipt_delay_days": delay})
        assert ledger.shortage.sum() > original.shortage.sum()
        assert (ledger.closing >= 0).all()
        assert ledger.historical_sales.sum() == 12
        np.testing.assert_array_equal(ledger.scenario_demand, ledger.fulfilled + ledger.shortage)


def test_one_day_shock_does_not_edit_history(cfg):
    matrix, forecasts = policy_fixture(cfg)
    scenario = {"name": "drop", "demand_multiplier": 0., "demand_start": "2025-10-02", "demand_days": 1, "receipt_fraction": 1., "receipt_delay_days": 0}
    ledger, _, _ = run_policy(matrix, forecasts, cfg, scenario)
    assert ledger.loc[ledger.date.eq("2025-10-02"), "scenario_demand"].item() == 0
    assert ledger.loc[ledger.date.eq("2025-10-03"), "scenario_demand"].item() == 3
    assert ledger.historical_sales.sum() == 12


def test_missing_receipt_declaration_is_not_empty(cfg):
    del cfg["inventory"]["initial_receipts"]
    with pytest.raises(ValueError, match="declaration"):
        declared_receipts(cfg, "2025-09-30")


def test_alert_opportunity_keeps_early_events_in_denominator():
    from src.inventory import alert_opportunity_summary
    alerts = pd.DataFrame({'actual_days': [6, 7, 12, np.nan, np.nan],
        'already_empty': [False, False, False, False, True],
        'tp': [True, True, False, False, False],
        'fn': [False, False, True, False, False]})
    stats = alert_opportunity_summary(alerts)
    assert stats['actual_depletion_events'] == 3
    assert stats['events_before_day7'] == 1
    assert stats['events_with_7day_opportunity'] == 2
    assert stats['missed_events_with_7day_opportunity'] == 1
    assert stats['single_origin_opportunity_rate'] == 2/3
    assert stats['recall_with_7day_opportunity'] == .5


def test_alert_opportunity_no_events_is_unknown_not_perfect():
    from src.inventory import alert_opportunity_summary
    alerts = pd.DataFrame({'actual_days': [np.nan], 'already_empty': [True],
                          'tp': [False], 'fn': [False]})
    stats = alert_opportunity_summary(alerts)
    assert stats['actual_depletion_events'] == 0
    assert np.isnan(stats['single_origin_opportunity_rate'])
    assert np.isnan(stats['recall_with_7day_opportunity'])
