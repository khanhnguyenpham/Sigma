import csv
import io

import numpy as np
import pandas as pd
import pytest

from src.transactions import EVENT_COLUMNS, apportion_quantities, prepare_transactions, replay_transactions, verify_events
from src.inventory import declared_receipts, replenishment, run_policy
from tests.test_inventory import policy_fixture, params


FIRST = ('A', 'C', 'S', 'eSIM')
SECOND = ('A', 'C', 'S2', 'eSIM')


def record(ident, quantity, stamp='2025-10-01T00:00:00Z', key=FIRST):
    return {'order_id': ident, 'quantity': quantity,
            'order_datetime': pd.Timestamp(stamp), 'key': key}


def writer():
    stream = io.StringIO()
    output = csv.DictWriter(stream, fieldnames=EVENT_COLUMNS)
    output.writeheader()
    return stream, output


def test_receipts_then_global_timestamp_id_order_and_partial_fulfillment():
    stream, output = writer()
    # Deliberately shuffled: receipt precedes even a midnight sale, IDs break ties.
    records = [record('fake-z', 2), record('fake-c', 4, '2025-10-01T01:00:00Z'),
               record('fake-a', 3), record('fake-b', 1, key=SECOND)]
    actual = replay_transactions('2025-10-01', {FIRST: 1, SECOND: 2}, {FIRST: 3},
        {FIRST: (9, 9), SECOND: (1, 1)}, records, 'base', 'fixture', output)
    assert actual == {FIRST: (0, 4, 5), SECOND: (1, 1, 0)}
    events = list(csv.DictReader(io.StringIO(stream.getvalue())))
    assert [event['event_type'] for event in events] == ['receipt', 'sale', 'sale', 'sale', 'sale']
    assert [event['order_id'] for event in events[1:]] == ['fake-a', 'fake-b', 'fake-z', 'fake-c']
    assert [int(event['fulfilled']) for event in events[1:]] == [3, 1, 1, 0]
    assert [int(event['shortage']) for event in events[1:]] == [0, 0, 1, 4]
    assert [int(event['event_sequence']) for event in events] == list(range(1, 6))


def test_stress_rounding_conserves_and_keeps_historical_quantities():
    assert apportion_quantities([3, 1], 2) == [2, 0]  # Equal remainders: earlier order wins.
    assert apportion_quantities([3, 1], 0) == [0, 0]
    assert apportion_quantities([3, 1], 8) == [6, 2]
    stream, output = writer()
    actual = replay_transactions('2025-10-01', {FIRST: 1}, {}, {FIRST: (4, 2)},
        [record('fake-a', 3), record('fake-b', 1)], 'drop', 'fixture', output)
    assert actual[FIRST] == (0, 1, 1)
    events = pd.read_csv(io.StringIO(stream.getvalue()))
    assert events.historical_quantity.tolist() == [3, 1]
    assert events.scenario_quantity.tolist() == [2, 0]


def test_no_sales_receipt_day_still_records_event_and_closing():
    stream, output = writer()
    actual = replay_transactions('2025-10-01', {FIRST: 0}, {FIRST: 4}, {FIRST: (0, 0)},
                                 [], 'base', 'fixture', output)
    assert actual[FIRST] == (4, 0, 0)
    assert len(list(csv.DictReader(io.StringIO(stream.getvalue())))) == 1


def test_prepare_utc_tiebreak_and_reject_wrong_day(cfg):
    sales = pd.DataFrame([dict(zip(['date', 'order_datetime', 'order_id', 'quantity'] +
                                  ['destination_country', 'carrier', 'sku', 'product_type'], row))
        for row in [('2025-10-01', '2025-10-01T07:00:00+07:00', 'fake-z', 2, *FIRST),
                    ('2025-10-01', '2025-10-01T00:00:00Z', 'fake-a', 1, *FIRST)]])
    sales['date'] = pd.to_datetime(sales.date)
    days = prepare_transactions(sales, cfg)
    assert [row['order_id'] for row in days[pd.Timestamp('2025-10-01')]] == ['fake-a', 'fake-z']
    sales.loc[0, 'date'] = pd.Timestamp('2025-10-02')
    with pytest.raises(ValueError, match='UTC day'):
        prepare_transactions(sales, cfg)


@pytest.mark.parametrize('fraction,delay,multiplier', [(1., 0, 1.), (.5, 0, 1.), (0., 0, 1.),
                                                       (1., 3, 1.), (1., 0, .3), (1., 0, 2.)])
def test_transactional_policy_matches_daily_balances_for_stress(cfg, fraction, delay, multiplier):
    matrix, forecasts = policy_fixture(cfg)
    transactions = {day: [record('fake-' + day.strftime('%d') + '-a', 2, day.tz_localize('UTC').isoformat()),
                           record('fake-' + day.strftime('%d') + '-b', 1, (day + pd.Timedelta(hours=1)).tz_localize('UTC').isoformat())]
                    for day in pd.date_range(cfg['test_start'], cfg['test_end'])}
    scenario = {'name': 'fixture', 'demand_multiplier': multiplier,
                'receipt_fraction': fraction, 'receipt_delay_days': delay}
    expected, expected_recommendations, _ = run_policy(matrix, forecasts, cfg, scenario)
    stream, output = writer()
    actual, actual_recommendations, _ = run_policy(matrix, forecasts, cfg, scenario,
                                                  transactions=transactions, event_writer=output)
    pd.testing.assert_frame_equal(expected, actual)
    pd.testing.assert_frame_equal(expected_recommendations, actual_recommendations)
    events = pd.read_csv(io.StringIO(stream.getvalue()))
    sales = events.loc[events.event_type.eq('sale')]
    assert sales.historical_quantity.sum() == 12
    assert sales.scenario_quantity.sum() == actual.scenario_demand.sum()
    assert sales.fulfilled.sum() == actual.fulfilled.sum()
    assert sales.shortage.sum() == actual.shortage.sum()
    assert events.received_quantity.sum() == actual.receipts.sum()


def test_missing_or_duplicate_transaction_blocks_reconciliation():
    with pytest.raises(ValueError, match='totals disagree'):
        replay_transactions('2025-10-01', {}, {}, {FIRST: (3, 3)}, [], 'base', 'fixture')
    with pytest.raises(ValueError, match='Duplicate'):
        replay_transactions('2025-10-01', {}, {}, {FIRST: (2, 2)},
                            [record('fake-a', 1), record('fake-a', 1)], 'base', 'fixture')


@pytest.mark.parametrize('bad', [1.5, np.inf, -1, True])
def test_no_silent_fractional_policy_or_receipt_truncation(cfg, bad):
    with pytest.raises(ValueError):
        replenishment(1, np.ones(14), 0, {**params(), 'lead_time_days': bad})
    cfg['inventory']['initial_receipts'] = [dict(zip(
        ['destination_country', 'carrier', 'sku', 'product_type'], FIRST), quantity=bad, eta='2025-10-01')]
    with pytest.raises(ValueError):
        declared_receipts(cfg, '2025-09-30')


def test_independent_event_verifier_and_tamper_detection(cfg, tmp_path):
    matrix, forecasts = policy_fixture(cfg)
    rows = [{'date': day, 'order_datetime': day.tz_localize('UTC') + pd.Timedelta(hours=h),
             'order_id': f'fake-{day.day}-{h}', 'quantity': quantity,
             **dict(zip(['destination_country', 'carrier', 'sku', 'product_type'], FIRST))}
            for day in pd.date_range(cfg['test_start'], cfg['test_end']) for h, quantity in [(0, 2), (1, 1)]]
    sales = pd.DataFrame(rows)
    stream, output = writer()
    ledger, _, _ = run_policy(matrix, forecasts, cfg,
        {'name': 'base', 'demand_multiplier': 1., 'receipt_fraction': .5, 'receipt_delay_days': 0},
        transactions=prepare_transactions(sales, cfg), event_writer=output)
    event_path = tmp_path/'events.csv'; event_path.write_text(stream.getvalue(), encoding='utf-8')
    ledger_path = tmp_path/'days.csv'; ledger.to_csv(ledger_path, index=False)
    stats = verify_events(event_path, ledger_path, sales, cfg)
    assert stats['sale_event_rows'] == 8 and stats['receipt_event_rows'] == 3
    assert stats['transaction_day_reconciliation']
    events = pd.read_csv(event_path, keep_default_na=False)
    first_sale = events.event_type.eq('sale').idxmax()
    events.loc[first_sale, 'historical_quantity'] += 1
    events.to_csv(event_path, index=False)
    with pytest.raises(ValueError, match='Historical transaction quantities changed'):
        verify_events(event_path, ledger_path, sales, cfg)
    event_path.write_text(stream.getvalue(), encoding='utf-8')
    events = pd.read_csv(event_path, keep_default_na=False)
    events.loc[0, 'event_sequence'] = 8
    events.to_csv(event_path, index=False)
    with pytest.raises(ValueError, match='sequence'):
        verify_events(event_path, ledger_path, sales, cfg)
