"""Private, chronological simulated inventory events from audited sales.

Only local run outputs may contain order_id. Never log source records.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from src.common import ITEM

EVENT_COLUMNS = ['date', 'scenario_id'] + ITEM + [
    'event_sequence', 'event_type', 'event_datetime', 'order_id',
    'historical_quantity', 'scenario_quantity', 'received_quantity',
    'stock_before', 'fulfilled', 'shortage', 'stock_after',
    'is_simulated', 'assumption_version']


def whole_quantity(value):
    """Reject truncation, negative quantities and non-finite declarations."""
    if isinstance(value, (bool, np.bool_)):
        raise ValueError('Invalid integer inventory quantity')
    try:
        valid = np.isfinite(value) and value >= 0 and value == int(value)
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not valid:
        raise ValueError('Invalid integer inventory quantity')
    return int(value)


def prepare_transactions(sales, cfg):
    """Order all item transactions globally within each UTC policy day."""
    frame = sales.loc[sales.date.between(cfg['test_start'], cfg['test_end']),
                      ['date', 'order_datetime', 'order_id', 'quantity'] + ITEM].copy()
    frame['order_datetime'] = pd.to_datetime(frame.order_datetime, utc=True)
    frame['order_id'] = frame.order_id.astype(str)
    if frame.order_id.duplicated().any() or frame.order_datetime.isna().any():
        raise ValueError('Transactions must be audited and uniquely identified')
    normalized = frame.order_datetime.dt.tz_localize(None).dt.normalize()
    if not normalized.eq(pd.to_datetime(frame.date)).all():
        raise ValueError('Transaction UTC day disagrees with audited day')
    frame = frame.sort_values(['order_datetime', 'order_id'], kind='stable')
    days = defaultdict(list)
    for row in frame.itertuples(index=False):
        quantity = whole_quantity(row.quantity)
        if not quantity:
            raise ValueError('Audited sales quantity must be positive')
        days[pd.Timestamp(row.date)].append({
            'key': tuple(getattr(row, field) for field in ITEM),
            'order_datetime': row.order_datetime,
            'order_id': row.order_id, 'quantity': quantity})
    return dict(days)


def apportion_quantities(quantities, demand):
    """Exact largest remainders; ties follow the prior chronological order.

    Preserve the predeclared integer item-day stress total. This creates
    simulated demand per order and never edits historical order quantity.
    """
    quantities = [whole_quantity(value) for value in quantities]
    demand = whole_quantity(demand)
    total = sum(quantities)
    if not total:
        if demand:
            raise ValueError('Scenario demand has no transaction basis')
        return [0] * len(quantities)
    quotients, remainders = zip(*(divmod(value * demand, total) for value in quantities))
    result = list(quotients)
    remaining = demand - sum(result)
    for index in sorted(range(len(result)), key=lambda i: (-remainders[i], i))[:remaining]:
        result[index] += 1
    return result


def replay_transactions(day, opening, received, quantities, transactions,
                        scenario_id, assumption_version, writer=None):
    """Receive at start of day, then consume in timestamp/order-id order.

    quantities maps item -> (historical total, simulated demand). The day
    ledger remains the explicit opening/closing record, including no-event
    days. Events contain only positive receipts and every historical sale,
    including zero simulated demand during a declared shock.
    """
    day = pd.Timestamp(day)
    keys = sorted(quantities)
    historical = {}; demand = {}
    for key, values in quantities.items():
        historical[key], demand[key] = map(whole_quantity, values)
    by_item = defaultdict(list)
    ordered = sorted(transactions, key=lambda row: (row['order_datetime'], row['order_id']))
    for row in ordered:
        if row['key'] not in quantities:
            raise ValueError('Transaction item is absent from the day ledger')
        stamp = pd.Timestamp(row['order_datetime'])
        if stamp.tzinfo is None or stamp.tz_convert('UTC').tz_localize(None).normalize() != day:
            raise ValueError('Transaction is outside the UTC ledger day')
        by_item[row['key']].append(row)
    assigned = {}
    for key in keys:
        records = by_item[key]
        source = [whole_quantity(row['quantity']) for row in records]
        if sum(source) != historical[key]:
            raise ValueError('Transaction totals disagree with historical sales')
        for row, quantity in zip(records, apportion_quantities(source, demand[key])):
            if row['order_id'] in assigned:
                raise ValueError('Duplicate transaction identifier')
            assigned[row['order_id']] = quantity
    stocks = {key: whole_quantity(opening.get(key, 0)) for key in keys}
    fulfilled = dict.fromkeys(keys, 0); shortage = dict.fromkeys(keys, 0)
    sequence = 0

    def event(key, event_type, stamp, order_id, observed, requested, receipt, before, fill, missing, after):
        nonlocal sequence
        sequence += 1
        if writer is not None:
            writer.writerow({'date': day.date().isoformat(), 'scenario_id': scenario_id,
                **dict(zip(ITEM, key)), 'event_sequence': sequence,
                'event_type': event_type, 'event_datetime': stamp.isoformat(), 'order_id': order_id,
                'historical_quantity': observed, 'scenario_quantity': requested,
                'received_quantity': receipt, 'stock_before': before,
                'fulfilled': fill, 'shortage': missing, 'stock_after': after,
                'is_simulated': True, 'assumption_version': assumption_version})

    for key in keys:
        amount = whole_quantity(received.get(key, 0))
        before = stocks[key]; stocks[key] += amount
        if amount:
            event(key, 'receipt', day.tz_localize('UTC'), '', 0, 0, amount, before, 0, 0, stocks[key])
    for row in ordered:
        key = row['key']; requested = assigned[row['order_id']]
        before = stocks[key]; fill = min(before, requested); missing = requested - fill
        stocks[key] -= fill; fulfilled[key] += fill; shortage[key] += missing
        event(key, 'sale', pd.Timestamp(row['order_datetime']).tz_convert('UTC'), row['order_id'],
              row['quantity'], requested, 0, before, fill, missing, stocks[key])
    return {key: (stocks[key], fulfilled[key], shortage[key]) for key in keys}


def verify_events(event_path, ledger_path, sales, cfg):
    """Independently reconcile private events; failures never include row IDs."""
    events = pd.read_csv(event_path, dtype={'order_id': str}, keep_default_na=False)
    if events.empty:
        raise ValueError('Inventory event ledger is empty')
    events['date'] = pd.to_datetime(events.date)
    events['event_datetime'] = pd.to_datetime(events.event_datetime, utc=True)
    groups = ['scenario_id', 'date']
    keys = groups + ITEM
    quantity_cols = ['historical_quantity', 'scenario_quantity', 'received_quantity',
                     'stock_before', 'fulfilled', 'shortage', 'stock_after']
    numbers = events[quantity_cols].to_numpy()
    if not (np.isfinite(numbers).all() and (numbers >= 0).all() and (numbers == np.floor(numbers)).all()):
        raise ValueError('Event quantities are not nonnegative integers')
    if not events.event_type.isin(['sale', 'receipt']).all() or not events.is_simulated.all():
        raise ValueError('Invalid or unlabeled event type')
    if not events.event_sequence.eq(events.groupby(groups, sort=False).cumcount() + 1).all():
        raise ValueError('Event sequence is not consecutive within each scenario/day')
    if not events.event_datetime.dt.tz_localize(None).dt.normalize().eq(events.date).all():
        raise ValueError('Event timestamp is outside its UTC day')
    sales_events = events.loc[events.event_type.eq('sale')]
    receipts = events.loc[events.event_type.eq('receipt')]
    if not receipts.event_datetime.eq(receipts.date.dt.tz_localize('UTC')).all():
        raise ValueError('Receipts must arrive at beginning of UTC day')
    if not receipts.order_id.eq('').all() or not receipts.received_quantity.gt(0).all():
        raise ValueError('Invalid receipt event identity or quantity')
    # Compare positions, never print or embed source identifiers on failure.
    ordered = sales_events.sort_values(groups + ['event_datetime', 'order_id'], kind='stable')
    observed = sales_events.sort_values(groups + ['event_sequence'], kind='stable')
    if not np.array_equal(ordered.index, observed.index):
        raise ValueError('Sales were not processed in timestamp/order-id order')
    first_sale = sales_events.groupby(groups).event_sequence.min()
    if not receipts.empty:
        receipt_last = receipts.groupby(groups).event_sequence.max()
        paired = receipt_last.to_frame('receipt').join(first_sale.rename('sale'))
        if not (paired.receipt < paired.sale.fillna(np.inf)).all():
            raise ValueError('Receipt appeared after a sale within the UTC day')
    if not (events.stock_after == events.stock_before + events.received_quantity - events.fulfilled).all():
        raise ValueError('Event stock balance failed')
    if not events.scenario_quantity.eq(events.fulfilled + events.shortage).all():
        raise ValueError('Event demand balance failed')
    if not sales_events.fulfilled.eq(np.minimum(sales_events.stock_before, sales_events.scenario_quantity)).all():
        raise ValueError('Transaction partial fulfillment failed')
    previous = events.groupby(keys, sort=False).stock_after.shift()
    if not events.loc[previous.notna(), 'stock_before'].eq(previous.dropna()).all():
        raise ValueError('Stock chain between item events failed')
    source = sales.loc[sales.date.between(cfg['test_start'], cfg['test_end'])].copy()
    source['order_id'] = source.order_id.astype(str)
    source = source.set_index('order_id')
    if source.index.has_duplicates:
        raise ValueError('Verification requires audited unique sales')
    expected_ids = set(source.index)
    for _, group in sales_events.groupby('scenario_id'):
        if group.order_id.duplicated().any() or set(group.order_id) != expected_ids:
            raise ValueError('Scenario omitted or duplicated historical transactions')
    matched = source.reindex(sales_events.order_id)
    if not np.array_equal(sales_events.historical_quantity, matched.quantity):
        raise ValueError('Historical transaction quantities changed')
    for field in ITEM:
        if not np.array_equal(sales_events[field], matched[field]):
            raise ValueError('Historical transaction item changed')
    stamps = pd.to_datetime(matched.order_datetime, utc=True)
    if not np.array_equal(sales_events.event_datetime.to_numpy(), stamps.to_numpy()):
        raise ValueError('Historical transaction timestamp changed')
    aggregate = events.groupby(keys, sort=False).agg(
        historical_quantity=('historical_quantity', 'sum'), scenario_quantity=('scenario_quantity', 'sum'),
        received_quantity=('received_quantity', 'sum'), fulfilled=('fulfilled', 'sum'), shortage=('shortage', 'sum'),
        first_stock=('stock_before', 'first'), final_stock=('stock_after', 'last')).reset_index()
    event_keys = set(map(tuple, aggregate[keys].itertuples(index=False, name=None)))
    matched_keys = set(); scenarios = set()
    for chunk in pd.read_csv(ledger_path, parse_dates=['date'], chunksize=50000):
        scenarios.update(chunk.scenario_id.unique())
        joined = chunk.merge(aggregate, on=keys, how='left', suffixes=('_day', '_event'), validate='one_to_one')
        has_events = joined.first_stock.notna()
        for day_name, event_name in [('historical_sales', 'historical_quantity'), ('scenario_demand', 'scenario_quantity'),
                                     ('receipts', 'received_quantity'), ('fulfilled_day', 'fulfilled_event'),
                                     ('shortage_day', 'shortage_event')]:
            if not joined[day_name].eq(joined[event_name].fillna(0)).all():
                raise ValueError('Event totals differ from daily ledger')
        if not (joined.loc[has_events, 'opening'].eq(joined.loc[has_events, 'first_stock']).all()
                and joined.loc[has_events, 'closing'].eq(joined.loc[has_events, 'final_stock']).all()):
            raise ValueError('Event opening or closing differs from daily ledger')
        if not joined.loc[~has_events, 'opening'].eq(joined.loc[~has_events, 'closing']).all():
            raise ValueError('No-event day changed inventory')
        matched_keys.update(map(tuple, joined.loc[has_events, keys].itertuples(index=False, name=None)))
    if matched_keys != event_keys or set(events.scenario_id.unique()) != scenarios:
        raise ValueError('Event/day coverage differs')
    return {'event_rows': len(events), 'sale_event_rows': len(sales_events),
            'receipt_event_rows': len(receipts), 'scenarios': len(scenarios),
            'chronological_order_verified': True, 'transaction_day_reconciliation': True}
