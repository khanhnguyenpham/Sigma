"""Trade reconciliation from frozen inputs; never imports a producer/resolver."""
from datetime import date, timedelta
import math
from urllib.parse import urlsplit
from core.errors import DomainError


def fail(message='Frozen trade history differs'):
    raise DomainError('verification_failed', message)


def day(value):
    if isinstance(value, date):
        return value.date() if hasattr(value, 'date') else value
    return date.fromisoformat(value)


def verify_trade_snapshot(run):
    snap = run.config_snapshot
    if snap.get('trade_lifecycle_profile') is None:
        if any(k in snap for k in ('trade_rules', 'internal_supply_snapshot', 'provider_notice_snapshot')):
            fail()
        return None
    expected = dict(version=2, calendar='UTC', policy_cutoff='rolling_day', alert_cutoff='window_origin',
        stock_cutoff='as_of_date', order_limit='full_fixed_lot', coverage_required=True,
        actual_blocking='known_effective_provider_only', metric_exclusion='whole_item_window')
    if snap.get('trade_lifecycle_profile') != 'internal_provider_trade_v2' or snap.get('trade_rules') != expected:
        fail()
    if 'supply_lifecycle_profile' in snap or 'supply_lifecycle_snapshot' in snap:
        fail()
    cutoff = run.as_of_date
    if run.kind == 'policy_replay':
        cutoff = run.period_end
    elif run.kind == 'alert_replay':
        cutoff += timedelta(days=max(0, ((run.period_end-cutoff).days//14-1)*14))
    try:
        catalog = {r['item_id']: r for r in snap['catalog_snapshot'] if day(r['first_seen_date']) <= cutoff}
        warehouses = {r['id']: r for r in snap['warehouse_snapshot']}
        internal, notices = snap['internal_supply_snapshot'], snap['provider_notice_snapshot']
        if not isinstance(internal, list) or not isinstance(notices, list):
            fail()
        histories, ids = {}, set()
        for r in internal:
            if r['item_id'] not in catalog or type(r['id']) is not int or r['id'] <= 0 or r['id'] in ids:
                fail()
            histories.setdefault(r['item_id'], []).append(r)
            ids.add(r['id'])
        for rows in histories.values():
            rows.sort(key=lambda r:r['version'])
            previous, stop = date.min, None
            for version, r in enumerate(rows, 1):
                known, effective = day(r['known_on']), day(r['effective_on'])
                if (type(r['version']) is not int or r['version'] != version or not previous <= known <= cutoff
                    or r['is_assumed'] is not True or r['assumption_source'] != 'user_declared_supply_simulation_v1'
                    or not r['reason'].strip() or len(r['reason']) > 1000):
                    fail()
                if r['action'] == 'stop':
                    if stop or r['target_change_id'] is not None or effective < known:
                        fail()
                    stop = r
                else:
                    if (not stop or r['target_change_id'] != stop['id'] or effective != known
                        or r['action'] != ('cancel_stop' if known < day(stop['effective_on']) else 'resume')):
                        fail()
                    stop = None
                previous = known
        notice_ids, event_ids = set(), set()
        for n in notices:
            if type(n['id']) is not int or n['id'] <= 0 or n['id'] in notice_ids or type(n['supplier_id']) is not int or n['supplier_id'] <= 0:
                fail()
            notice_ids.add(n['id'])
            members = n['item_ids']
            identities = {r['id']: r for r in n['item_snapshot']}
            if (not members or any(type(i) is not int or i <= 0 for i in members)
                or members != sorted(set(members)) or set(members) != set(identities)
                or len(identities) != len(n['item_snapshot']) or not set(members) & catalog.keys()):
                fail()
            if len({r['carrier'] for r in identities.values()}) != 1:
                fail()
            scope = n['scope_definition']
            if set(scope) != {'products'} or not isinstance(scope['products'], list) or not scope['products']:
                fail()
            resolved = set()
            for p in scope['products']:
                if (set(p) != {'sku', 'product_type', 'destination_countries', 'warehouse_ids'}
                    or not p['sku'].strip() or p['product_type'] not in {'eSIM', 'physical_SIM'}
                    or not p['destination_countries'] or not p['warehouse_ids']
                    or any(type(w) is not int or w <= 0 for w in p['warehouse_ids'])):
                    fail()
                matching = [r for r in identities.values() if r['sku'] == p['sku'] and r['product_type'] == p['product_type']
                    and r['destination_country'] in p['destination_countries'] and r['warehouse_id'] in p['warehouse_ids']]
                if ({r['warehouse_id'] for r in matching} != set(p['warehouse_ids'])
                    or {r['destination_country'] for r in matching} != set(p['destination_countries'])):
                    fail()
                resolved.update(r['id'] for r in matching)
                for iid, r in catalog.items():
                    warehouse = next((w for w in warehouses.values() if w['destination_country'] == r['destination_country'] and w['carrier'] == r['carrier']), None)
                    if (warehouse and warehouse['id'] in p['warehouse_ids'] and r['destination_country'] in p['destination_countries']
                        and r['sku'] == p['sku'] and r['product_type'] == p['product_type'] and r['carrier'] == next(iter(identities.values()))['carrier']
                        and iid not in members):
                        fail()
            if resolved != set(members):
                fail()
            for iid, r in identities.items():
                if r['supplier_id'] != n['supplier_id'] or type(r['warehouse_id']) is not int or r['warehouse_id'] <= 0:
                    fail()
                if iid in catalog:
                    original = catalog[iid]
                    if any(r[k] != original[k] for k in ('sku', 'product_type', 'destination_country', 'carrier')):
                        fail()
                    w = warehouses.get(r['warehouse_id'])
                    if not w or any(w[k] != r[k] for k in ('destination_country', 'carrier')):
                        fail()
                    if any(p['supplier_id'] != n['supplier_id'] for p in snap['policies'] if p['item_id'] == iid):
                        fail()
            events = n['events']
            if not isinstance(events, list) or not 1 <= len(events) <= 2:
                fail()
            previous = date.min
            for version, r in enumerate(events, 1):
                known, effective = day(r['known_on']), day(r['effective_on'])
                if (type(r['id']) is not int or r['id'] <= 0 or r['id'] in event_ids or r['notice_id'] != n['id']
                    or type(r['version']) is not int or r['version'] != version or not previous <= known <= cutoff
                    or r['is_assumed'] is not True or any(not isinstance(r[k], str) or not r[k].strip() or len(r[k]) > 1000 for k in ('reason', 'source_description'))):
                    fail()
                event_ids.add(r['id'])
                if r.get('source_ref') is not None:
                    url = urlsplit(r['source_ref'])
                    if (len(r['source_ref']) > 2048 or any(c.isspace() for c in r['source_ref'])
                        or url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password):
                        fail()
                if version == 1:
                    if r['action'] != 'stop' or r['target_event_id'] is not None:
                        fail()
                else:
                    stop = events[0]
                    if r['target_event_id'] != stop['id']:
                        fail()
                    if r['action'] == 'cancel_stop':
                        if effective != known or known >= day(stop['effective_on']):
                            fail()
                    elif r['action'] != 'resume_supply' or known < day(stop['effective_on']) or effective < known:
                        fail()
                previous = known
    except (KeyError, TypeError, ValueError, AttributeError, StopIteration):
        fail()
    return snap


def trade_rights(snap, item, origin, target):
    origin, target = day(origin), day(target)
    internal = sorted((r for r in snap['internal_supply_snapshot'] if r['item_id'] == item and day(r['known_on']) <= origin), key=lambda r:r['version'])
    stop = None
    for r in internal:
        stop = r if r['action'] == 'stop' else None
    status = 'active' if stop is None else 'scheduled_stop' if target < day(stop['effective_on']) else 'stopped'
    restrictions = []
    for n in sorted(snap['provider_notice_snapshot'], key=lambda n:n['id']):
        if item not in n['item_ids']:
            continue
        events = [r for r in n['events'] if day(r['known_on']) <= origin]
        if not events or (len(events) == 2 and events[1]['action'] == 'cancel_stop'):
            continue
        first = events[0]
        resume = events[1]['effective_on'] if len(events) == 2 else None
        provider = 'scheduled_stop' if target < day(first['effective_on']) else 'stopped'
        resume_on = None
        if provider == 'stopped' and resume:
            resume_on = resume
            provider = 'clear' if target >= day(resume) else 'scheduled_resume'
        if provider == 'clear':
            continue
        restrictions.append(dict(notice_id=n['id'], supplier_id=n['supplier_id'], provider_status=provider,
            sales_allowed=provider == 'scheduled_stop', stop_on=first['effective_on'], resume_on=resume_on,
            stop_event_id=first['id'], version=events[-1]['version'], reason=first['reason'], source_description=first['source_description']))
    blockers = [r for r in restrictions if not r['sales_allowed']]
    provider = 'stopped' if any(r['provider_status'] == 'stopped' for r in blockers) else 'scheduled_resume' if blockers else 'scheduled_stop' if restrictions else 'clear'
    return dict(internal_status=status, internal_reason=stop['reason'] if stop else None,
        internal_stop_change_id=stop['id'] if stop else None, internal_version=internal[-1]['version'] if internal else 0,
        provider_status=provider, provider_blockers=blockers, provider_restrictions=restrictions,
        sales_allowed=not blockers, replenishment_allowed=status != 'stopped' and not blockers)


def trade_path(snap, item, origin, cutoff, stock, forecast, receipts):
    origin = day(origin)
    rows = []
    offset = (origin-day(cutoff)).days
    for h, qty in enumerate(forecast[offset:], 1):
        target = origin + timedelta(days=h)
        state = trade_rights(snap, item, cutoff, target)
        received = receipts.get(target, 0)
        available = float(stock) + received
        sold = min(available, float(qty)) if state['sales_allowed'] else 0.0
        blocked = float(qty) if not state['sales_allowed'] else 0.0
        stock = available - sold
        rows.append(dict(date=str(target), closing_forecast=stock, receipts_qty=received,
            forecast_demand_qty=float(qty), forecast_input_qty=float(qty), projected_sales_qty=sold,
            sales_blocked_qty=blocked, unserved_stock_qty=float(qty)-sold-blocked, unserved_demand_qty=float(qty)-sold,
            available_total=available, sellable_qty=available if state['sales_allowed'] else 0.0,
            blocked_stock_before_sale=0.0 if state['sales_allowed'] else available,
            closing_total=stock, closing_sellable=stock if state['sales_allowed'] else 0.0,
            closing_blocked=0.0 if state['sales_allowed'] else stock, **state))
    return rows


def order_limit(snap, item, cutoff, decision_day, q, path):
    decision_day = day(decision_day)
    state = trade_rights(snap, item, cutoff, decision_day)
    deadlines = [max(decision_day, day(r['stop_on'])) for r in state['provider_restrictions']]
    deadline = min(deadlines) if deadlines else None
    arrival, budget, reason = decision_day+timedelta(days=7), None, None
    coverage_end = day(path[-1]['date']) if path else decision_day
    coverage = deadline is None or deadline-timedelta(days=1) <= coverage_end
    if not state['replenishment_allowed']:
        reason = 'provider_blocked' if not state['sales_allowed'] else 'internal_stopped'
    elif deadline:
        if arrival >= deadline:
            reason = 'eta_at_or_after_provider_stop'
        elif not coverage:
            reason = 'insufficient_forecast_coverage'
        else:
            budget = math.floor(math.fsum(r['unserved_stock_qty'] for r in path if arrival <= day(r['date']) < deadline))
            if q > budget:
                reason = 'fixed_lot_exceeds_sellable_budget'
    return dict(q_policy=q, q_final=0 if reason else q, cap_reason=reason, sellable_budget=budget,
        provider_stop_on=str(deadline) if deadline else None, eta=str(arrival), forecast_coverage_complete=coverage, **state)


def window_exclusion(snap, item, origin, end):
    origin, end = day(origin), day(end)
    blocked = []
    for h in range((end-origin).days+1):
        target = origin + timedelta(days=h)
        state = trade_rights(snap, item, origin, target)
        if not state['sales_allowed']:
            blocked.append(dict(date=str(target), notice_ids=[r['notice_id'] for r in state['provider_blockers']],
                reasons=[r['reason'] for r in state['provider_blockers']]))
    return dict(item_id=int(item), window_origin=str(origin), window_end=str(end), reason='provider_sales_blocked', blocked_dates=blocked) if blocked else None
