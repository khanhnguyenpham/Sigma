from sqlalchemy import select
from sigma_m3.errors import DomainError
from sigma_m3.models import Item, Supplier, Policy, InventoryDaily, Run


def create_policy(session, request):
    # Lock the common item, not a supplier: changing suppliers must serialize too.
    item = session.scalar(
        select(Item).where(Item.id == request.item_id).with_for_update()
    )
    if item is None or session.get(Supplier, request.supplier_id) is None:
        raise DomainError("not_found", "Item or supplier does not exist", 404)
    latest = session.scalar(
        select(Policy)
        .where(Policy.item_id == item.id)
        .order_by(Policy.version.desc())
        .limit(1)
    )
    version = latest.version if latest else 0
    if request.expected_version != version:
        raise DomainError(
            "version_conflict",
            "Policy has changed; reload before saving",
            409,
            item_id=item.id,
        )
    if latest:
        if request.effective_from <= latest.effective_from or (
            latest.effective_to is not None
            and request.effective_from < latest.effective_to
        ):
            raise DomainError(
                "policy_overlap",
                "Policy intervals cannot overlap or be inserted retroactively",
                409,
                item_id=item.id,
            )
        used = session.scalar(
            select(InventoryDaily.id)
            .where(
                InventoryDaily.policy_id == latest.id,
                InventoryDaily.date >= request.effective_from,
            )
            .limit(1)
        )
        frozen = session.scalars(
            select(Run).where(Run.status.in_(["queued", "running", "complete"]))
        ).all()
        for run in frozen:
            if (
                latest.id in run.config_snapshot.get("policy_ids", [])
                and (run.period_end or run.as_of_date) >= request.effective_from
            ):
                used = True
        if used:
            raise DomainError(
                "version_conflict",
                "This date changes a frozen run; use a new scenario override",
                409,
                item_id=item.id,
            )
        if latest.effective_to is None:
            latest.effective_to = request.effective_from
    row = Policy(
        item_id=item.id,
        supplier_id=request.supplier_id,
        version=version + 1,
        effective_from=request.effective_from,
        configured_rop_floor=request.configured_rop_floor,
        moq=request.moq,
        safety_days=request.safety_days,
        is_assumed=True,
        assumption_source="user_configured_simulation_v1",
    )
    session.add(row)
    session.flush()
    return row
