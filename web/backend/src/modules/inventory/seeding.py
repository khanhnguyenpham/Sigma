
"""Explicit assumption generation, never a missing-policy runtime fallback."""
from core.run_context import source_data_id
from datetime import timedelta
import math
from sqlalchemy import select, func
from core.errors import DomainError
from modules.catalog.models import Item, Warehouse, Supplier
from modules.configuration.models import Policy, Scenario
from modules.forecasting.models import DailySales
from modules.configuration.schemas import PolicyCreate
from modules.configuration.service import create_policy
from core.run_context import required_run


def seed_simulation(session, source_run_id, origin):
    source = required_run(session, source_run_id, "source_import", complete=True)
    if origin > source.observation_end:
        raise DomainError("invalid_input", "Seed origin exceeds source coverage")
    # Serialize all seed calls. Normal policy editing still locks each item.
    from sqlalchemy import text

    session.execute(text("SELECT pg_advisory_xact_lock(734100720)"))
    rows = session.execute(
        select(Item, Warehouse)
        .join(Warehouse, Item.warehouse_id == Warehouse.id)
        .where(Item.first_seen_date <= origin)
        .order_by(Item.id)
    ).all()
    suppliers = {s.code: s.id for s in session.scalars(select(Supplier))}
    start = origin - timedelta(days=27)
    stats = {
        i: (count, available, qty)
        for i, count, available, qty in session.execute(
            select(
                DailySales.item_id,
                func.count(),
                func.count().filter(DailySales.actual_available),
                func.sum(DailySales.sales_qty),
            )
            .where(
                DailySales.source_import_run_id == source_data_id(source),
                DailySales.date.between(start, origin),
            )
            .group_by(DailySales.item_id)
        )
    }
    created = reused = 0
    for item, warehouse in rows:
        if item.id not in stats or stats[item.id][0:2] != (28, 28):
            raise DomainError(
                "insufficient_history",
                "Seed requires 28 complete calendar days",
                item_id=item.id,
            )
        avg = float(stats[item.id][2]) / 28
        ordinal = int(warehouse.code.split("-")[-1])
        floor = math.ceil((6 if ordinal % 2 else 8) * avg)
        safety = 2 if ordinal % 2 else 3
        supplier = suppliers.get(f"SUP-{ordinal:03}")
        if not supplier:
            raise DomainError(
                "missing_partner_config",
                "Seed supplier mapping is incomplete",
                item_id=item.id,
            )
        existing = session.scalar(
            select(Policy)
            .where(Policy.item_id == item.id)
            .order_by(Policy.version.desc())
            .limit(1)
        )
        if existing:
            if (
                existing.assumption_source not in {"synthetic_seed_v1", "synthetic_fixed_lot_seed_v1"}
                or existing.effective_from != origin
                or existing.supplier_id != supplier
                or existing.configured_rop_floor != floor
                or float(existing.safety_days) != safety
            ):
                raise DomainError(
                    "version_conflict",
                    "Policy already exists; seed does not overwrite user configuration",
                    409,
                    item_id=item.id,
                )
            reused += 1
            continue
        request = PolicyCreate(
            item_id=item.id,
            supplier_id=supplier,
            effective_from=origin,
            configured_rop_floor=floor,
            fixed_order_qty=5 if item.product_type == "eSIM" else 10,
            safety_days=safety,
            expected_version=0,
        )
        policy = create_policy(session, request)
        policy.assumption_source = "synthetic_fixed_lot_seed_v1"
        created += 1
    for code, name, cover, multiplier in [
        ("base", "Cơ sở", 7, 1),
        ("cover_3", "Tồn đầu 3 ngày", 3, 1),
        ("cover_14", "Tồn đầu 14 ngày", 14, 1),
        ("safety_05", "Safety ×0,5", 7, 0.5),
        ("safety_15", "Safety ×1,5", 7, 1.5),
    ]:
        if session.scalar(
            select(Scenario.id).where(Scenario.code == code, Scenario.version == 1)
        ):
            continue
        session.add(
            Scenario(
                code=code,
                version=1,
                name=name,
                description="Explicit local simulated assumptions; no supplier contract",
                settings=dict(
                    cover_days=cover,
                    safety_multiplier=multiplier,
                    policy_overrides=[],
                    receipts_initial=[],
                    receipts_declared=True,
                    seed_origin=origin.isoformat(),
                    source_import_run_id=str(source_run_id),
                ),
                assumption_version="synthetic_seed_v1",
            )
        )
    session.flush()
    return dict(
        policies_created=created,
        policies_reused=reused,
        eligible_items=len(rows),
        scenario_count=5,
        source_import_run_id=str(source_run_id),
        as_of_date=origin.isoformat(),
        is_simulated=True,
    )
