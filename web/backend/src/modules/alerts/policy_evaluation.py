"""Score the depletion warnings and stock trajectory of one completed purchasing plan."""
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import and_, select

from modules.alerts.models import Alert
from modules.inventory.models import InventoryDaily
from modules.purchasing.models import Replenishment


def policy_warning_metrics(days, receipts, period_end):
    """Walk item-days newest first so each warning can match only the next depletion."""
    received = defaultdict(list)
    for lot in receipts:
        received[lot.item_id].append((lot.ordered_on, lot.eta))

    next_depletion = {}
    next_sales_block = {}
    episodes, eligible = set(), set()
    first_warning = {}
    warnings_with_receipt = incomplete_followup = 0
    blocked_sales_item_days = warnings_with_sales_block = 0
    for row in sorted(days, key=lambda row: row.date, reverse=True):
        if row.sales_allowed is False:
            blocked_sales_item_days += 1
            next_sales_block[row.item_id] = row.date
            next_depletion.pop(row.item_id, None)
            continue
        if row.closing_qty == 0:
            if row.opening_qty + row.receipts_qty > 0:
                episode = row.item_id, row.date
                episodes.add(episode)
                next_depletion[row.item_id] = row.date
            continue
        depletion = next_depletion.get(row.item_id)
        horizon_end = row.date + timedelta(days=14)
        if depletion is not None and depletion <= horizon_end:
            episode = row.item_id, depletion
            if (depletion - row.date).days >= 7:
                eligible.add(episode)
            if row.predicted_depletion_date is not None:
                first_warning[episode] = row.date
        elif row.predicted_depletion_date is not None:
            observed_until = min(horizon_end, period_end)
            sales_block = next_sales_block.get(row.item_id)
            if sales_block is not None and sales_block <= observed_until:
                warnings_with_sales_block += 1
            elif any(row.date <= ordered and eta <= observed_until for ordered, eta in received[row.item_id]):
                warnings_with_receipt += 1
            elif horizon_end > period_end:
                incomplete_followup += 1

    early = sum((depletion - day).days >= 7 for (_, depletion), day in first_warning.items())
    return dict(
        observed_early_numerator=early,
        eligible_early_events=len(eligible),
        eligible_detection_rate=early / len(eligible) if eligible else None,
        event_denominator=len(episodes),
        observed_early_rate=early / len(episodes) if episodes else None,
        detected_events=len(first_warning),
        recall=len(first_warning) / len(episodes) if episodes else None,
        warnings_with_receipt=warnings_with_receipt,
        warnings_with_incomplete_followup=incomplete_followup,
        blocked_sales_item_days=blocked_sales_item_days,
        warnings_with_sales_block=warnings_with_sales_block,
    )


def evaluate_policy_warnings(session, run):
    days = session.execute(
        select(
            InventoryDaily.item_id, InventoryDaily.date, InventoryDaily.opening_qty,
            InventoryDaily.receipts_qty, InventoryDaily.closing_qty,
            Alert.predicted_depletion_date,
            Alert.explanation["sales_allowed"].as_boolean().label("sales_allowed"),
        ).outerjoin(Alert, and_(
            Alert.run_id == InventoryDaily.run_id,
            Alert.window_origin == InventoryDaily.window_origin,
            Alert.item_id == InventoryDaily.item_id,
            Alert.as_of_date == InventoryDaily.date,
            Alert.alert_type == "depletion",
        )).where(InventoryDaily.run_id == run.id)
    ).all()
    receipts = session.execute(
        select(Replenishment.item_id, Replenishment.ordered_on, Replenishment.eta).where(
            Replenishment.run_id == run.id, Replenishment.is_initial.is_(False),
            Replenishment.status == "received",
        )
    ).all()
    return policy_warning_metrics(days, receipts, run.period_end)
