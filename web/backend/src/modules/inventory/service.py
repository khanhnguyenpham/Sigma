"""Pure L7/R1/H14 policy and transaction arithmetic; no forecast padding."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from numbers import Real
import math
from statistics import pstdev
import numpy as np
from core.errors import DomainError


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
    safety_mode: str = "days"
    rop_mode: str = "forecast"
    safety_lookback_days: int = 28
    safety_factor: float = 1.0
    safety_multiplier: float = 1.0

    def __post_init__(self):
        quantity(self.configured_rop_floor)
        if (
            quantity(self.moq) < 1
            or self.safety_mode not in ("days", "volatility")
            or self.rop_mode not in ("fixed", "forecast")
        ):
            raise DomainError("invalid_input", "Invalid supplier item policy")
        if (
            isinstance(self.safety_lookback_days, bool)
            or not isinstance(self.safety_lookback_days, (int, np.integer))
            or not 7 <= self.safety_lookback_days <= 90
        ):
            raise DomainError("invalid_input", "Safety lookback must be 7 to 90 days")
        for value in (self.safety_days, self.safety_factor, self.safety_multiplier):
            if (
                isinstance(value, bool)
                or not isinstance(value, (Real, Decimal))
                or not math.isfinite(value)
                or value < 0
            ):
                raise DomainError(
                    "invalid_input", "Policy parameters must be finite and nonnegative"
                )
        if self.safety_multiplier > 10:
            raise DomainError("invalid_input", "Safety multiplier exceeds scenario range")


def history_quantities(history, days):
    """Validate observed daily counts; neither missing values nor fractions are zero."""
    values = np.asarray(history, dtype=object)
    if values.shape != (days,):
        raise DomainError(
            "insufficient_history", "A complete observed safety window is required"
        )
    counts = []
    for value in values:
        try:
            valid = (
                not isinstance(value, bool)
                and isinstance(value, (Real, Decimal))
                and math.isfinite(value)
                and value == int(value)
                and 0 <= int(value) <= 2**63 - 1
            )
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            raise DomainError(
                "insufficient_history",
                "Safety history requires observed nonnegative integer quantities",
            )
        counts.append(int(value))
    return counts


def recommend(forecast, closing, pending, policy, history=None):
    f = vector14(forecast)
    closing, pending = quantity(closing), quantity(pending)
    with np.errstate(over="ignore", invalid="ignore"):
        total = float(f.sum())
    if not math.isfinite(total):
        raise DomainError(
            "numeric_overflow", "Forecast exceeds supported inventory arithmetic"
        )
    if policy.safety_mode == "days":
        raw_ss = (
            float(policy.safety_days) * float(policy.safety_multiplier) * float(f.mean())
        )
    else:
        counts = history_quantities(history, policy.safety_lookback_days)
        sigma = pstdev(counts)  # Population std; Python ints avoid int64 square overflow.
        raw_ss = (
            float(policy.safety_multiplier)
            * float(policy.safety_factor)
            * sigma
            * math.sqrt(7)
            if policy.safety_multiplier and policy.safety_factor and sigma
            else 0.0
        )
    if not math.isfinite(raw_ss) or raw_ss > 2**63 - 1:
        raise DomainError("numeric_overflow", "Safety stock exceeds bigint capacity")
    ss = math.ceil(raw_ss)
    rop_forecast = math.ceil(float(f[:7].sum()) + ss)
    rop = (
        policy.configured_rop_floor
        if policy.rop_mode == "fixed"
        else max(rop_forecast, policy.configured_rop_floor)
    )
    target = rop + math.ceil(float(f[7]))
    ip = closing + pending
    trigger = closing < rop
    raw = max(0, target - ip) if trigger else 0
    q = max(math.ceil(raw), policy.moq) if raw > 0 else 0
    if max(ss, rop_forecast, rop, target, ip, q) > 2**63 - 1:
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
