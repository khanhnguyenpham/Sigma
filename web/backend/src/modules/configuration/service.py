from sqlalchemy import select, func, text
from core.errors import DomainError
from core.http import record
from modules.inventory.models import InventoryDaily
from modules.runs.models import Run
from modules.catalog.models import Item, Supplier, Warehouse
from modules.configuration.models import Policy, Scenario
from modules.configuration.schemas import POLICY_DEFAULTS


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
        fixed_order_qty=request.fixed_order_qty,
        safety_days=request.safety_days,
        **{name: getattr(request, name) for name in POLICY_DEFAULTS},
        is_assumed=True,
        assumption_source="user_configured_simulation_v1",
    )
    session.add(row)
    session.flush()
    return row


def list_policies(sessions, item_id, supplier_id, effective_on, page, page_size):
    filters = []
    if item_id:
        filters.append(Policy.item_id == item_id)
    if supplier_id:
        filters.append(Policy.supplier_id == supplier_id)
    if effective_on:
        filters.extend(
            [
                Policy.effective_from <= effective_on,
                (Policy.effective_to.is_(None))
                | (Policy.effective_to > effective_on),
            ]
        )
    with sessions() as s:
        query = (
            select(Policy, Item, Warehouse, Supplier)
            .join(Item, Item.id == Policy.item_id)
            .join(Warehouse, Warehouse.id == Item.warehouse_id)
            .join(Supplier, Supplier.id == Policy.supplier_id)
            .where(*filters)
        )
        total = s.scalar(select(func.count()).select_from(query.subquery()))
        rows = s.execute(
            query.order_by(Policy.item_id, Policy.version.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return dict(
            items=[
                {
                    **record(p),
                    "item_label": f"{w.destination_country} / {w.carrier} · {i.sku} · {i.product_type}",
                    "supplier_code": supplier.code,
                }
                for p, i, w, supplier in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )


def create_scenario(s, request):
    s.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:code))"),
        {"code": request.code},
    )
    if (
        request.base_scenario_id
        and s.get(Scenario, request.base_scenario_id) is None
    ):
        raise DomainError("not_found", "Base scenario does not exist", 404)
    ids = {o.item_id for o in request.settings.policy_overrides} | {
        r.item_id for r in request.settings.receipts_initial
    }
    if ids - set(s.scalars(select(Item.id).where(Item.id.in_(ids)))):
        raise DomainError("not_found", "Scenario contains an unknown item", 404)
    version = (
        s.scalar(
            select(func.max(Scenario.version)).where(
                Scenario.code == request.code
            )
        )
        or 0
    ) + 1
    row = Scenario(
        code=request.code,
        version=version,
        name=request.name,
        description=request.description,
        settings=request.settings.model_dump(mode="json", exclude_none=True),
        assumption_version="user_scenario_v1",
    )
    s.add(row)
    s.flush()
    return row
