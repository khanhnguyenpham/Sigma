"""S25 only changes alarms, not fixed-lot state or source forecasts."""
import copy
import pytest
from test_fixed_lot_baseline import fixture
from core.hashes import digest
from web.backend.research import fixed_lot_baseline as base
from web.backend.research import fixed_lot_s25 as research
from web.backend.research import fixed_lot_verification as independent


@pytest.mark.parametrize('candidate,alpha', [('C00', 1), ('S25', 1.25)])
def test_projection_and_paired_scoring_on_identical_path(candidate, alpha):
    source = fixture(); p = base.read(base.PROTOCOL)
    lots = base.quantities(source, p['quantity_basis'])
    frozen = base.replay(base.fixed_snapshot(source, lots), p['scenarios'][0])
    before = digest(frozen); source_before = digest(source)
    projected = research.alarms(source, frozen, alpha, '2025-07-01')
    assert projected == research.reference_alarms(source, frozen, candidate, '2025-07-01')
    cases, metrics, _ = base.summarize({**frozen, 'alarms': projected}, source)
    expected_cases, _ = independent.check_summary({**frozen, 'alarms': projected}, source, metrics)
    assert cases == expected_cases
    baseline_cases, baseline_metrics, _ = base.summarize(frozen, source)
    change = research.paired(cases, baseline_cases)
    assert metrics['event_denominator'] == baseline_metrics['event_denominator']
    assert metrics['early_numerator'] - baseline_metrics['early_numerator'] == change['gained_early'] - change['lost_early']
    assert metrics['full_period'] == baseline_metrics['full_period']
    assert before == digest(frozen) and source_before == digest(source)
    if candidate == 'C00': assert projected == frozen['alarms']
    tampered = copy.deepcopy(cases); tampered[0]['date'] = '2025-12-31'
    with pytest.raises(ValueError): research.paired(tampered, baseline_cases)


def tiny(stock=8):
    source = dict(forecasts=[dict(as_of_date='2025-10-01', item_id=1, forecast=[1.0]*14)],
                  daily=[dict(date='2025-10-10', quantity=999)])
    frozen = dict(ledger=[dict(date='2025-10-01', item_id=1, closing_qty=stock)], orders=[])
    return source, frozen


def test_known_receipts_excludes_today_new_order():
    source, frozen = tiny()
    frozen['orders'] = [dict(item_id=1, ordered_on='2025-10-01', eta='2025-10-03', ordered_qty=100, is_initial=False)]
    assert research.alarms(source, frozen, 1.25, '2025-07-29')[0]['predicted_depletion_date'] == '2025-10-08'
    frozen['orders'][0]['ordered_on'] = '2025-09-30'
    assert research.alarms(source, frozen, 1.25, '2025-07-29')[0]['predicted_depletion_date'] is None


def test_already_empty_never_counts_future_early_alarm():
    source, frozen = tiny(0)
    assert research.alarms(source, frozen, 1.25, '2025-07-29')[0]['predicted_depletion_date'] is None
    assert research.reference_alarms(source, frozen, 'S25', '2025-07-29')[0]['predicted_depletion_date'] is None


def test_future_actual_unavailable_to_projection_and_effective_date():
    source, frozen = tiny()
    expected = research.alarms(source, frozen, 1.25, '2025-07-29')
    source['daily'][0]['quantity'] = 0
    assert research.alarms(source, frozen, 1.25, '2025-07-29') == expected
    assert research.alarms(source, frozen, 1.25, '2025-10-02') == research.alarms(source, frozen, 1, '2025-07-29')


def test_protocol_locks_only_historical_s25_no_reselection():
    p = base.read(research.PROTOCOL)
    assert p['candidates'] == {'C00': 1, 'S25': 1.25}
    assert p['effective_from'] == '2025-07-29'
    assert not p['selection'] and not p['application_change'] and p['test_retrospective']
