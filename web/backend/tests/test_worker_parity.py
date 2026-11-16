"""M7 worker optimisation: W2-W4 keep every result; W1 reuses the allocation basis on purpose."""
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from core.errors import DomainError
from core.hashes import digest
from modules.inventory.simulation import pure_window

ORIGIN = date(2025, 9, 30)
END = ORIGIN + timedelta(days=28)


def rich_inputs():
    """Several items, a mid-window policy version, volatility safety, a pending lot and zero-sale days."""
    days = pd.date_range("2025-06-01", "2025-11-30")
    rng = np.random.default_rng(7)
    matrix = pd.DataFrame({i: rng.poisson(lam, len(days)) for i, lam in [(1, 9), (2, 3), (3, 0.4), (4, 6)]}, index=days)
    matrix = matrix.astype("Int64")
    catalog = [dict(item_id=i, destination_country="Demo", carrier="DemoNet", sku=f"S{i}", product_type="eSIM",
                    first_seen_date="2024-01-01") for i in (1, 2, 3, 4)]
    switch = (ORIGIN + timedelta(days=10)).isoformat()
    policies = [
        dict(id=1, item_id=1, supplier_id=1, version=1, effective_from="2025-01-01", effective_to=switch,
             configured_rop_floor=40, moq=20, safety_days=2),
        dict(id=5, item_id=1, supplier_id=1, version=2, effective_from=switch, effective_to=None,
             configured_rop_floor=80, moq=30, safety_days=3),
        dict(id=2, item_id=2, supplier_id=2, version=1, effective_from="2025-01-01", effective_to=None,
             configured_rop_floor=10, moq=5, safety_days=1, safety_mode="volatility", safety_lookback_days=14,
             safety_factor=1.5),
        dict(id=3, item_id=3, supplier_id=3, version=1, effective_from="2025-01-01", effective_to=None,
             configured_rop_floor=3, moq=None, safety_days=0, fixed_order_qty=4, rop_mode="fixed"),
        dict(id=4, item_id=4, supplier_id=2, version=1, effective_from="2025-01-01", effective_to=None,
             configured_rop_floor=30, moq=10, safety_days=2, safety_mode="volatility", safety_lookback_days=60),
    ]
    vectors = {(ORIGIN + timedelta(days=d), i): [float(1 + (i * d + h) % 7) for h in range(14)]
               for d in range(29) for i in (1, 2, 3, 4)}
    events = {}
    for d in range(1, 29):
        day = ORIGIN + timedelta(days=d)
        for i in (1, 2, 3, 4):
            q = int(matrix.at[pd.Timestamp(day), i])
            if q:
                events[(day, i)] = [dict(event_at=datetime(day.year, day.month, day.day, 9, tzinfo=timezone.utc),
                                         source_sequence=d * 10 + i, quantity=q)]
    scenario = dict(cover_days=5, safety_multiplier=1.2, receipts_declared=True, receipts_initial=[
        dict(item_id=2, lot_key="pending", ordered_on=str(ORIGIN - timedelta(days=2)),
             eta=str(ORIGIN + timedelta(days=3)), ordered_qty=25)])
    return matrix, events, catalog, vectors, policies, scenario


# Recorded from the pre-M7 pure_window (policy_at scan, history slice, pending re-sum).
GOLDEN = {
    "policy_replay": "206d6d18c9317fda1f48175f5ff60745f0d05128eb20ca6df81d93242ac10b1d",
    "alert_replay": "09e2df1feff547ebb1738a57426102afe6b9dd76dbc8219ee321ac1454d70f20",
    "stock_projection": "ea604f68583f962367921ffef3499ce5ceca929d0b248c93bc59f53bea2cc43b",
}


def run(kind, matrix=None):
    args = list(rich_inputs())
    if matrix is not None:
        args[0] = matrix
    end = ORIGIN if kind == "stock_projection" else (ORIGIN + timedelta(days=14) if kind == "alert_replay" else END)
    return pure_window(*args, kind, ORIGIN, end, initial_stock_fallback_days=90,
                       lead_times={"1": 4, "2": 9, "3": 1})


@pytest.mark.parametrize("kind", list(GOLDEN))
def test_w3_inventory_worker_matches_pre_m7_result(kind):
    assert digest(run(kind)) == GOLDEN[kind]


def test_w4_scenario_reads_only_the_days_it_uses():
    from modules.inventory.simulation import daily_start
    matrix, *_, policies, _ = rich_inputs()
    start = daily_start(ORIGIN, policies, 90)
    assert start == ORIGIN - timedelta(days=89)
    for kind, end in [("policy_replay", END), ("alert_replay", ORIGIN + timedelta(days=14)), ("stock_projection", ORIGIN)]:
        assert digest(run(kind, matrix.loc[pd.Timestamp(start):pd.Timestamp(end)])) == GOLDEN[kind]
    assert daily_start(ORIGIN, policies, None) == ORIGIN - timedelta(days=59)
    with pytest.raises(DomainError):  # one day short of the 60-day volatility window
        run("stock_projection", matrix.loc[pd.Timestamp(ORIGIN - timedelta(days=58)):])


def legacy_rows(origin, eligible, weights, shares, window, label, totals):
    """The pre-M7 per-row dict loop, with weights/shares indexed by weekday/item."""
    origin = pd.Timestamp(origin)
    totals = np.asarray(totals, dtype=float)
    rows = []
    for h in range(1, 15):
        target = origin + pd.Timedelta(days=h)
        for item in eligible:
            rows.append(dict(item_id=item, as_of_date=origin, target_date=target, horizon_day=h,
                             forecast_qty=float(totals[(h - 1) // 7] * weights[target.dayofweek] * shares[item]),
                             item_share=float(shares[item]), weekday_weight=float(weights[target.dayofweek]),
                             share_window_days=window, allocation_basis=label))
    return pd.DataFrame(rows)


def legacy_basis(history, first_seen, origin):
    """Frozen pre-M7 basis arithmetic of allocate()."""
    origin = pd.Timestamp(origin)
    eligible = sorted(k for k, day in first_seen.items() if pd.Timestamp(day) <= origin)
    past = history.loc[history.index <= origin, eligible].reindex(pd.date_range(origin - pd.Timedelta(days=89), origin))
    route = past.sum(axis=1)
    weights = route.groupby(route.index.dayofweek).sum().reindex(range(7), fill_value=0).to_numpy(float)
    label = "weekday90" if weights.sum() > 0 else "uniform_zero_history"
    weights = weights / weights.sum() if weights.sum() > 0 else np.full(7, 1 / 7)
    item_totals, window = past.tail(30).sum(), 30
    if item_totals.sum() == 0:
        item_totals, window = past.sum(), 90
    return eligible, weights, item_totals / item_totals.sum(), window, label


def legacy_allocate(history, first_seen, origin, totals):
    return legacy_rows(origin, *legacy_basis(history, first_seen, origin), totals)


def history_cases():
    rng = np.random.default_rng(11)
    index = pd.date_range("2025-03-01", "2025-12-31")
    yield pd.DataFrame({i: rng.poisson(lam, len(index)) for i, lam in [(3, 4.2), (8, 0.3), (21, 17)]}, index=index)
    sparse = pd.DataFrame(0, index=index, columns=[5, 6])
    sparse.loc["2025-06-02", 6] = 3  # outside the 30-day window -> 90-day shares
    yield sparse
    single = pd.DataFrame(0, index=index, columns=[7, 9])
    single.loc["2025-07-15", 9] = 1  # weekday weights from a single sale
    yield single


@pytest.mark.parametrize("case", range(3))
def test_w2_vectorised_allocation_is_identical_to_dict_loop(case):
    from modules.forecasting.allocation import allocate
    history = list(history_cases())[case]
    first_seen = {k: "2024-01-01" for k in history.columns}
    checked = 0
    for origin in ["2025-07-01", "2025-08-17", "2025-09-25"]:
        for totals in [(70.0, 140.0), (0.0, 13.7), (1234.5678, 0.1)]:
            if legacy_basis(history, first_seen, origin)[2].isna().any():
                with pytest.raises(DomainError):
                    allocate(history, first_seen, origin, totals)
                continue
            pd.testing.assert_frame_equal(allocate(history, first_seen, origin, totals),
                                          legacy_allocate(history, first_seen, origin, totals), check_exact=True)
            checked += 1
    assert checked


def test_w1_basis_is_reused_until_a_new_item_appears():
    from modules.forecasting.allocation import apply_totals, reuse_basis
    history = list(history_cases())[0]
    first_seen = {3: "2024-01-01", 8: "2024-01-01", 21: "2025-08-20"}
    basis = None
    for origin in pd.date_range("2025-08-10", "2025-08-25"):
        basis = reuse_basis(basis, history, first_seen, origin)
        day = pd.Timestamp("2025-08-10" if origin < pd.Timestamp("2025-08-20") else "2025-08-20")
        assert basis["as_of_date"] == day
        rows = apply_totals(basis, origin, [70.0, 140.0])
        for block, total in [(rows.horizon_day.le(7), 70.0), (rows.horizon_day.gt(7), 140.0)]:
            assert np.isclose(rows.loc[block, "forecast_qty"].sum(), total, atol=1e-8, rtol=0)
        expected = legacy_rows(origin, *legacy_basis(history, first_seen, day), (70.0, 140.0))
        pd.testing.assert_frame_equal(rows, expected, check_exact=True)


def test_w1_w2_item_forecast_copy_matches_legacy_rows(pg):
    """COPY by block stores exactly what the per-row writer stored; later origins carry the basis date."""
    from sqlalchemy import text
    from modules.forecasting.service import write_item_forecasts
    from test_results_api import result_fixture
    _, sessions = pg
    _, run, item = result_fixture(sessions)
    history = pd.DataFrame({item: (np.arange(276) * 7) % 11}, index=pd.date_range("2025-04-01", periods=276)).astype("int64")
    catalog = [dict(item_id=item, destination_country="DemoLand", carrier="DemoCarrier", first_seen_date="2024-01-01")]
    origins = [pd.Timestamp("2025-12-20"), pd.Timestamp("2025-12-21")]
    totals = {(o, "DemoLand", "DemoCarrier"): np.array([33.3, 66.6]) for o in origins}
    with sessions.begin() as s:
        s.execute(text("DELETE FROM item_forecasts WHERE run_id=:r"), {"r": run})
    route = [("DemoLand", "DemoCarrier")]
    assert write_item_forecasts(sessions, run, history, catalog, route, totals, origins, lambda i: None) == 28
    with sessions() as s:
        stored = s.execute(text("""SELECT item_id, as_of_date, target_date, horizon_day, forecast_qty, actual_qty,
            actual_available, item_share, weekday_weight, share_window_days, allocation_basis, basis_as_of_date
            FROM item_forecasts WHERE run_id=:r ORDER BY as_of_date, horizon_day, item_id"""), {"r": run}).all()
    basis = legacy_basis(history, {item: "2024-01-01"}, origins[0])
    expected = []
    for origin in origins:
        for r in legacy_rows(origin, *basis, (33.3, 66.6)).itertuples(index=False):
            actual = int(history.at[r.target_date, r.item_id]) if r.target_date in history.index else None
            expected.append((r.item_id, r.as_of_date.date(), r.target_date.date(), r.horizon_day, r.forecast_qty, actual,
                             actual is not None, r.item_share, r.weekday_weight, r.share_window_days,
                             r.allocation_basis, origins[0].date()))
    assert [tuple(row) for row in stored] == expected
    assert {row.actual_available for row in stored} == {True, False}
    from alembic import command
    from test_trade_lifecycle import migration_config
    engine, _ = pg
    with pytest.raises(RuntimeError, match="lose their basis date"):
        command.downgrade(migration_config(engine), "0016_run_tables")
    with sessions() as s:
        assert s.scalar(text("SELECT version_num FROM alembic_version")) == "0017_item_forecast_basis_date"
