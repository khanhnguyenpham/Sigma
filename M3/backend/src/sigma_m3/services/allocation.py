"""Causal 90-day weekday and 30/90-day item allocation from audited aggregates."""
import numpy as np
import pandas as pd
from sigma_m3.errors import DomainError


def allocate(history, first_seen, origin, block_totals):
    origin = pd.Timestamp(origin)
    totals = np.asarray(block_totals, dtype=float)
    if totals.shape != (2,) or not np.isfinite(totals).all() or (totals < 0).any():
        raise DomainError("invalid_input", "Two complete weekly totals are required")
    eligible = sorted(k for k, day in first_seen.items() if pd.Timestamp(day) <= origin)
    if not eligible:
        raise DomainError("missing_allocation_basis", "No known item at this origin")
    if not isinstance(history.index,pd.DatetimeIndex) or history.index.has_duplicates or not set(eligible).issubset(history.columns):
        raise DomainError("insufficient_history", "History requires unique dates and every known item")
    expected = pd.date_range(origin-pd.Timedelta(days=89), origin)
    past = history.loc[history.index <= origin, eligible].reindex(expected)
    values = past.to_numpy(float)
    if past.index.has_duplicates or not np.isfinite(values).all() or (values < 0).any():
        raise DomainError("insufficient_history", "Observed history must cover 90 calendar days")
    route = past.sum(axis=1)
    weights = route.groupby(route.index.dayofweek).sum().reindex(range(7), fill_value=0).to_numpy(float)
    weekday_basis = "weekday90" if weights.sum() > 0 else "uniform_zero_history"
    weights = weights/weights.sum() if weights.sum() > 0 else np.full(7, 1/7)
    item_totals, window = past.tail(30).sum(), 30
    if item_totals.sum() == 0:
        item_totals, window = past.sum(), 90
    if item_totals.sum() == 0:
        raise DomainError("missing_allocation_basis", "No item sales in either the 30- or 90-day window")
    shares = item_totals/item_totals.sum()
    rows = []
    for h in range(1, 15):
        target = origin+pd.Timedelta(days=h)
        for item in eligible:
            rows.append(dict(item_id=item, as_of_date=origin, target_date=target, horizon_day=h,
                forecast_qty=float(totals[(h-1)//7]*weights[target.dayofweek]*shares[item]),
                item_share=float(shares[item]), weekday_weight=float(weights[target.dayofweek]),
                share_window_days=window, allocation_basis=weekday_basis))
    result = pd.DataFrame(rows)
    for b in range(2):
        actual = result.loc[result.horizon_day.between(1+7*b, 7+7*b), 'forecast_qty'].sum()
        if not np.isclose(actual, totals[b], atol=1e-8, rtol=0):
            raise DomainError("allocation_mismatch", "Weekly allocation does not conserve the total")
    return result
