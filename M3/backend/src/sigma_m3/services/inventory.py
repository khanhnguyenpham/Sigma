"""Pure L7/R1/H14 policy and transaction arithmetic; no forecast padding."""

from dataclasses import dataclass
from datetime import date, timedelta
import math
import numpy as np
from sigma_m3.core.errors import DomainError


def quantity(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, np.integer))
        or not 0 <= value <= 2**63 - 1
    ):
        raise DomainError("invalid_input", "Quantity must be a nonnegative integer")
    return int(value)


def vector14(forecast):
    f = np.asarray(forecast, dtype=float)
    if f.shape != (14,) or not np.isfinite(f).all() or (f < 0).any():
        raise DomainError(
            "insufficient_forecast", "A complete finite H14 vector is required"
        )
    return f


@dataclass(frozen=True)
class PolicyValues:
    configured_rop_floor: int
    moq: int
    safety_days: float

    def __post_init__(self):
        quantity(self.configured_rop_floor)
        if (
            quantity(self.moq) < 1
            or not math.isfinite(self.safety_days)
            or self.safety_days < 0
        ):
            raise DomainError("invalid_input", "Invalid supplier item policy")


def recommend(forecast, closing, pending, policy):
    f = vector14(forecast)
    closing, pending = quantity(closing), quantity(pending)
    if not np.isfinite(f.sum()) or not math.isfinite(
        float(policy.safety_days) * float(f.mean())
    ):
        raise DomainError(
            "numeric_overflow", "Forecast exceeds supported inventory arithmetic"
        )
    ss = math.ceil(float(policy.safety_days) * float(f.mean()))
    rop_forecast = math.ceil(float(f[:7].sum()) + ss)
    rop = max(rop_forecast, policy.configured_rop_floor)
    target = rop + math.ceil(float(f[7]))
    ip = closing + pending
    trigger = closing < rop
    raw = max(0, target - ip) if trigger else 0
    q = max(math.ceil(raw), policy.moq) if raw > 0 else 0
    if max(ss, rop, target, ip, q) > 2**63 - 1:
        raise DomainError(
            "numeric_overflow", "Inventory decision exceeds bigint capacity"
        )
    return dict(
        ss=ss,
        rop_forecast=rop_forecast,
        rop=rop,
        target_stock=target,
        inventory_position=ip,
        pending_qty=pending,
        needs_replenishment=trigger,
        recommended_qty=q,
        state="pending_covers"
        if trigger and q == 0
        else "low_stock"
        if trigger
        else "sufficient",
    )


def eta(ordered_on):
    if not isinstance(ordered_on, date):
        raise DomainError("invalid_input", "Order date is required")
    return ordered_on + timedelta(days=7)


def fulfill_day(opening, receipts, sales):
    """sales is already in audited timestamp/source-sequence order."""
    balance = quantity(opening) + quantity(receipts)
    events = []
    for demand in sales:
        demand = quantity(demand)
        fulfilled = min(demand, balance)
        balance -= fulfilled
        events.append(
            dict(
                quantity=demand,
                fulfilled_qty=fulfilled,
                shortage_qty=demand - fulfilled,
                balance_after=balance,
            )
        )
    return dict(
        opening_qty=int(opening),
        receipts_qty=int(receipts),
        sales_qty=sum(e["quantity"] for e in events),
        fulfilled_qty=sum(e["fulfilled_qty"] for e in events),
        shortage_qty=sum(e["shortage_qty"] for e in events),
        closing_qty=balance,
        events=events,
    )
