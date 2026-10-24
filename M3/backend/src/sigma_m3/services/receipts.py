from datetime import datetime, timezone
from sqlalchemy import select
from sigma_m3.core.errors import DomainError
from sigma_m3.models import Replenishment, InventoryEvent


def receive_due(session, order_id, day, balance_before, event_sequence):
    """Worker primitive: caller owns the item's serialized daily transaction."""
    from sigma_m3.services.inventory import quantity

    balance_before, event_sequence = quantity(balance_before), quantity(event_sequence)
    order = session.scalar(
        select(Replenishment).where(Replenishment.id == order_id).with_for_update()
    )
    if order is None:
        raise DomainError("not_found", "Replenishment does not exist", 404)
    if order.status == "received":
        return None
    if day != order.eta:
        raise DomainError(
            "invalid_input",
            "The fixed lead-time profile receives only at the exact ETA",
        )
    event = InventoryEvent(
        run_id=order.run_id,
        window_origin=order.window_origin,
        item_id=order.item_id,
        event_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
        event_sequence=event_sequence,
        event_kind="receipt",
        replenishment_order_id=order.id,
        quantity=order.ordered_qty,
        fulfilled_qty=0,
        shortage_qty=0,
        balance_after=balance_before + order.ordered_qty,
        is_simulated=True,
    )
    session.add(event)
    order.received_qty = order.ordered_qty
    order.status = "received"
    session.flush()
    return event
