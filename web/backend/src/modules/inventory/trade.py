"""Frozen trade rights, constrained H14 sales and whole-lot purchase limits."""
from datetime import date, timedelta
import math

from fastapi.encoders import jsonable_encoder
from modules.catalog.provider import trade_state
from modules.inventory.service import vector14, quantity


def rights(snapshot, item, origin, target):
    return jsonable_encoder(trade_state(snapshot['internal_supply_snapshot'],
        snapshot['provider_notice_snapshot'], item, origin, target))


def project_trade(snapshot, item, origin, decision_origin, on_hand, forecast, receipts):
    stock = float(quantity(on_hand))
    path, depletion = [], None
    # Fixed-origin alert windows only retain the remaining targets of that H14.
    offset = (origin-decision_origin).days
    for h, demand in enumerate(vector14(forecast)[offset:], 1):
        day = origin + timedelta(days=h)
        state = rights(snapshot, item, decision_origin, day)
        received = quantity(receipts.get(day, 0))
        available = stock + received
        sold = min(float(demand), available) if state['sales_allowed'] else 0.0
        blocked = 0.0 if state['sales_allowed'] else float(demand)
        stock = available - sold
        path.append(dict(date=str(day), closing_forecast=stock, receipts_qty=received,
            forecast_demand_qty=float(demand), forecast_input_qty=float(demand),
            projected_sales_qty=sold, sales_blocked_qty=blocked,
            unserved_stock_qty=float(demand)-sold-blocked, unserved_demand_qty=float(demand)-sold,
            available_total=available, sellable_qty=available if state['sales_allowed'] else 0.0,
            blocked_stock_before_sale=0.0 if state['sales_allowed'] else available,
            closing_total=stock, closing_sellable=stock if state['sales_allowed'] else 0.0,
            closing_blocked=0.0 if state['sales_allowed'] else stock, **state))
        if depletion is None and stock == 0:
            depletion = day
    lead = (depletion-origin).days if depletion else None
    state = 'not_within_horizon' if lead is None else 'early' if lead >= 7 else 'urgent'
    if on_hand == 0:
        state, depletion, lead = 'already_depleted', origin, 0
    return dict(projection=path, state=state, predicted_depletion_date=depletion, lead_days=lead)


def limit_order(snapshot, item, decision_origin, day, policy_qty, path):
    state = rights(snapshot, item, decision_origin, day)
    arrival = day + timedelta(days=7)
    # Earliest known stop across overlapping notices, even beyond H14 coverage.
    deadlines = [max(day, date.fromisoformat(r['stop_on'])) for r in state['provider_restrictions']]
    deadline = min(deadlines) if deadlines else None
    budget = None
    coverage_end = date.fromisoformat(path[-1]['date']) if path else day
    coverage = deadline is None or deadline-timedelta(days=1) <= coverage_end
    reason = None
    if not state['replenishment_allowed']:
        reason = 'provider_blocked' if not state['sales_allowed'] else 'internal_stopped'
    elif deadline is not None:
        if arrival >= deadline:
            reason = 'eta_at_or_after_provider_stop'
        elif not coverage:
            reason = 'insufficient_forecast_coverage'
        else:
            budget = math.floor(math.fsum(r['unserved_stock_qty'] for r in path
                if arrival <= date.fromisoformat(r['date']) < deadline))
            if policy_qty > budget:
                reason = 'fixed_lot_exceeds_sellable_budget'
    final = 0 if reason else policy_qty
    return dict(q_policy=policy_qty, q_final=final, cap_reason=reason, sellable_budget=budget,
        provider_stop_on=str(deadline) if deadline else None, eta=str(arrival),
        forecast_coverage_complete=coverage, **state)


def excluded_window(snapshot, item, origin, end):
    periods = []
    for offset in range((end-origin).days+1):
        day = origin + timedelta(days=offset)
        state = rights(snapshot, item, origin, day)
        if not state['sales_allowed']:
            periods.append(dict(date=str(day), notice_ids=[r['notice_id'] for r in state['provider_blockers']],
                reasons=[r['reason'] for r in state['provider_blockers']]))
    return dict(item_id=item, window_origin=str(origin), window_end=str(end),
        reason='provider_sales_blocked', blocked_dates=periods) if periods else None


def trade_totals(ledger, exclusions):
    exclusions = sorted(exclusions, key=lambda r:(r['window_origin'], r['item_id']))
    rows = [r for r in ledger if r['date'] > r['window_origin']]
    source = sum(r['source_sales_qty'] for r in rows)
    blocked = sum(r['actual_blocked_qty'] for r in rows)
    allowed = sum(r['sales_qty'] for r in rows)
    fulfilled = sum(r['fulfilled_qty'] for r in rows)
    return dict(source_sales_qty=source, scenario_sales_qty=allowed, actual_blocked_qty=blocked,
        fill_allowed=fulfilled/allowed if allowed else None, blocked_source_rate=blocked/source if source else None,
        metric_basis='allowed_scenario_sales', metric_exclusions=exclusions,
        excluded_item_windows=len(exclusions))
