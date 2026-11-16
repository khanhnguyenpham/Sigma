"""Causal 90-day weekday and 30/90-day item allocation from audited aggregates."""

import numpy as np
import pandas as pd
from core.errors import DomainError


def index_prediction_totals(predictions):
    """One grouping pass; no model selection, target or forecast quantity changes."""
    indexed = {}
    for (origin,country,carrier), group in predictions.groupby(['as_of_date','destination_country','carrier'],sort=False,dropna=False):
        group=group.sort_values('block')
        if group.block.tolist()!=[1,2]:
            raise DomainError('allocation_mismatch','Each route/origin must contain exactly two forecast blocks')
        totals=group.forecast_qty.to_numpy(dtype=float,copy=True)
        if not np.isfinite(totals).all() or (totals<0).any():
            raise DomainError('allocation_mismatch','Invalid forecast totals')
        totals.setflags(write=False)
        indexed[(pd.Timestamp(origin),country,carrier)]=totals
    return indexed


def eligible_items(first_seen, origin):
    return sorted(k for k, day in first_seen.items() if pd.Timestamp(day) <= origin)


def build_basis(history, first_seen, origin):
    """Weekday weights from the route's last 90 days and SKU shares from 30 (else 90) days, as of origin."""
    origin = pd.Timestamp(origin)
    eligible = eligible_items(first_seen, origin)
    if not eligible:
        raise DomainError("missing_allocation_basis", "No known item at this origin")
    if (
        not isinstance(history.index, pd.DatetimeIndex)
        or history.index.has_duplicates
        or not set(eligible).issubset(history.columns)
    ):
        raise DomainError(
            "insufficient_history", "History requires unique dates and every known item"
        )
    expected = pd.date_range(origin - pd.Timedelta(days=89), origin)
    past = history.loc[history.index <= origin, eligible].reindex(expected)
    values = past.to_numpy(float)
    if past.index.has_duplicates or not np.isfinite(values).all() or (values < 0).any():
        raise DomainError(
            "insufficient_history", "Observed history must cover 90 calendar days"
        )
    route = past.sum(axis=1)
    weights = (
        route.groupby(route.index.dayofweek)
        .sum()
        .reindex(range(7), fill_value=0)
        .to_numpy(float)
    )
    weekday_basis = "weekday90" if weights.sum() > 0 else "uniform_zero_history"
    weights = weights / weights.sum() if weights.sum() > 0 else np.full(7, 1 / 7)
    item_totals, window = past.tail(30).sum(), 30
    if item_totals.sum() == 0:
        item_totals, window = past.sum(), 90
    if item_totals.sum() == 0:
        raise DomainError(
            "missing_allocation_basis",
            "No item sales in either the 30- or 90-day window",
        )
    shares = item_totals / item_totals.sum()
    return dict(as_of_date=origin, items=np.asarray(eligible, dtype=np.int64), weights=weights,
                shares=shares.to_numpy(float), window=window, label=weekday_basis)


def reuse_basis(basis, history, first_seen, origin):
    """W1: keep the first origin's basis until the route's known SKUs change, then rebuild it."""
    if basis is not None and basis["items"].tolist() == eligible_items(first_seen, pd.Timestamp(origin)):
        return basis
    return build_basis(history, first_seen, origin)


def apply_totals(basis, origin, block_totals):
    """Spread the two weekly totals over day x SKU; same arithmetic order as the former per-row loop."""
    origin = pd.Timestamp(origin)
    totals = checked_totals(block_totals)
    items, shares = basis["items"], basis["shares"]
    targets = origin + pd.to_timedelta(np.arange(1, 15), "D")
    weights = basis["weights"][targets.dayofweek]
    qty = (np.repeat(totals, 7) * weights)[:, None] * shares[None, :]
    for b in range(2):
        if not np.isclose(qty[7 * b : 7 * b + 7].sum(), totals[b], atol=1e-8, rtol=0):
            raise DomainError(
                "allocation_mismatch", "Weekly allocation does not conserve the total"
            )
    n = len(items)
    return pd.DataFrame(dict(
        item_id=np.tile(items, 14),
        as_of_date=np.full(14 * n, origin),
        target_date=np.repeat(targets, n),
        horizon_day=np.repeat(np.arange(1, 15, dtype=np.int64), n),
        forecast_qty=qty.ravel(),
        item_share=np.tile(shares, 14),
        weekday_weight=np.repeat(weights, n),
        share_window_days=np.full(14 * n, basis["window"], dtype=np.int64),
        allocation_basis=np.full(14 * n, basis["label"], dtype=object),
    ))


def checked_totals(block_totals):
    totals = np.asarray(block_totals, dtype=float)
    if totals.shape != (2,) or not np.isfinite(totals).all() or (totals < 0).any():
        raise DomainError("invalid_input", "Two complete weekly totals are required")
    return totals


def allocate(history, first_seen, origin, block_totals):
    checked_totals(block_totals)
    return apply_totals(build_basis(history, first_seen, origin), origin, block_totals)
