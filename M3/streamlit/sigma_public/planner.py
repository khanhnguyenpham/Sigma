"""Session-only what-if. Reuses the exact M3 policy and projection functions."""

from datetime import date, timedelta
import math
import pandas as pd
from sigma_m3.services.inventory import PolicyValues, recommend, eta, quantity, vector14
from sigma_m3.services.alerts import project


def plan(
    origin,
    forecast,
    on_hand,
    pending,
    arrival_days,
    floor,
    moq,
    safety_days,
    demand_factor=1.0,
    shock_days=7,
    receipt_fraction=1.0,
):
    if not isinstance(origin, date):
        raise ValueError("Origin date is required")
    quantity(on_hand)
    quantity(pending)
    if not 1 <= arrival_days <= 7 or not 1 <= shock_days <= 14:
        raise ValueError("Invalid pending ETA or shock interval")
    if not math.isfinite(demand_factor) or not 0 <= demand_factor <= 5:
        raise ValueError("Demand factor must be finite and within 0..5")
    if not math.isfinite(receipt_fraction) or not 0 <= receipt_fraction <= 1:
        raise ValueError("Receipt fraction must be within 0..1")
    f = vector14(forecast).copy()
    f[:shock_days] *= demand_factor
    decision = recommend(f, on_hand, pending, PolicyValues(floor, moq, safety_days))
    receipts = (
        {origin + timedelta(days=arrival_days): math.floor(pending * receipt_fraction)}
        if pending
        else {}
    )
    q = decision["recommended_qty"]
    proposed = receipts.copy()
    if q:
        proposed[eta(origin)] = proposed.get(eta(origin), 0) + math.floor(
            q * receipt_fraction
        )
    before, after = (
        project(origin, on_hand, f, receipts),
        project(origin, on_hand, f, proposed),
    )
    rows = []
    for h, (a, b) in enumerate(zip(before["projection"], after["projection"]), 1):
        rows.append(
            dict(
                date=a["date"],
                forecast_qty=float(f[h - 1]),
                receipts_existing_qty=a["receipts_qty"],
                receipts_with_order_qty=b["receipts_qty"],
                closing_without_order=a["closing_forecast"],
                closing_with_order=b["closing_forecast"],
            )
        )
    return dict(
        decision=decision,
        proposed_eta=eta(origin).isoformat(),
        before=before,
        after=after,
        timeline=pd.DataFrame(rows),
        is_simulated=True,
        demand_factor=demand_factor,
        receipt_fraction=receipt_fraction,
    )
