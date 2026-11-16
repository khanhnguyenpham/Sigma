"""Audited snapshot import. Source IDs are neither persisted nor exported."""

import json
import pandas as pd
from sqlalchemy import select, func
from core.errors import DomainError
from core.settings import PROJECT_ROOT
from modules.catalog.models import Warehouse, Item, Supplier
from modules.catalog.locations import seed_cities
from modules.runs.models import Run
from modules.forecasting.models import DailySales
from src.data import audit_orders, daily_sales, route_top
from src.common import ROUTE, ITEM


def _quantity_rows(frame):
    return {(*key, day.date(), int(qty), int(orders)) for *key, day, qty, orders
            in frame[[*ITEM, "date", "sales_qty", "order_count"]].itertuples(index=False, name=None) if qty > 0}


def require_imported_source(session, source_run_id, sales):
    """Replaces the file checksum: the audited orders must give exactly the item x day quantities and order counts
    this import loaded. The M2 tie is checked by the fixed top10/46 routes and replay test-metric parity."""
    source = session.get(Run, source_run_id)
    catalog = {i["item_id"]: tuple(i[k] for k in ITEM) for i in source.config_snapshot["catalog_snapshot"]}
    rows = session.execute(
        select(DailySales.item_id, DailySales.date, DailySales.sales_qty, DailySales.order_count,
               DailySales.actual_available).where(DailySales.source_import_run_id == source_run_id)).all()
    stored = {(*catalog[i], day, qty, orders) for i, day, qty, orders, known in rows if known and qty > 0}
    # Days the import declared missing (not zero) are not compared.
    missing = {(*catalog[i], day) for i, day, _, _, known in rows if not known}
    current = sales.groupby(ITEM + ["date"]).agg(
        sales_qty=("quantity", "sum"), order_count=("order_id", "nunique")).reset_index()
    if stored != {row for row in _quantity_rows(current) if row[:5] not in missing}:
        raise DomainError("parent_mismatch", "Order source differs from the imported daily quantities")


def import_snapshot(settings, sessions, run_id):
    with sessions() as session:
        run = session.get(Run, run_id)
        request = run.config_snapshot["request"]
        cutoff = run.as_of_date
    source = settings.order_source(request["source_key"])
    cfg = json.loads(
        (PROJECT_ROOT / "data/configs/config.json").read_text(
            encoding="utf-8"
        )
    )
    sales, audit = audit_orders(source, cfg)
    # The single worker serializes source jobs. Each request key remains a distinct
    # technical run while an identical canonical dataset (same daily quantities) is reused.
    with sessions.begin() as session:
        from core.run_context import required_run, source_data_id

        candidates = session.scalars(
            select(Run)
            .where(
                Run.kind == "source_import",
                Run.status == "complete",
                Run.source_import_run_id.is_(None),
                Run.target_version == run.target_version,
                Run.as_of_date == cutoff,
            )
            .order_by(Run.created_at)
        ).all()
        for existing in candidates:
            try:
                require_imported_source(session, existing.id, sales)
            except DomainError:
                continue
            required_run(session, existing.id, "source_import", complete=True)
            row = session.get(Run, run_id)
            row.source_import_run_id = existing.id
            row.config_snapshot = {
                **row.config_snapshot,
                "catalog_snapshot": existing.config_snapshot["catalog_snapshot"],
                "warehouse_snapshot": existing.config_snapshot["warehouse_snapshot"],
                "resolved_source_import_run_id": str(source_data_id(existing)),
            }
            summary = {
                **existing.result_summary,
                "reused_source": True,
                "canonical_source_run_id": str(source_data_id(existing)),
            }
            row.result_summary = summary
            return summary
    observed = daily_sales(sales, cfg)
    top = route_top(observed, cfg)
    train = sales.loc[sales.date <= pd.Timestamp(cfg["train_end"])]
    routes = list(
        train[ROUTE]
        .drop_duplicates()
        .sort_values(ROUTE)
        .itertuples(index=False, name=None)
    )
    all_routes = set(sales[ROUTE].itertuples(index=False, name=None))
    if all_routes != set(routes):
        raise DomainError(
            "catalog_mismatch", "A source route is not in the declared train population"
        )
    cities = seed_cities(routes)
    if sales.empty:
        raise DomainError(
            "missing_partner_config", "Warehouse city assumptions are incomplete"
        )
    # Do not persist this frame: it contains private source identifiers.
    catalog = sales.groupby(ITEM, sort=True).date.min()
    expected_days = pd.date_range(cfg["observation_start"], cfg["observation_end"])
    if cutoff < expected_days[0].date() or cutoff > expected_days[-1].date():
        raise DomainError(
            "invalid_input", "Import cutoff lies outside declared observation coverage"
        )
    grouped = sales.groupby(ITEM + ["date"]).agg(
        sales_qty=("quantity", "sum"), order_count=("order_id", "nunique")
    )
    item_map = {}
    with sessions.begin() as session:
        warehouses = {
            (w.destination_country, w.carrier): w
            for w in session.scalars(select(Warehouse))
        }
        suppliers = {s.carrier: s for s in session.scalars(select(Supplier))}
        for ordinal, route in enumerate(routes, 1):
            if route[1] not in suppliers:
                supplier = Supplier(carrier=route[1])
                session.add(supplier)
                session.flush()
                suppliers[route[1]] = supplier
            if route not in warehouses:
                w = Warehouse(
                    code=f"WH-{ordinal:03}",
                    destination_country=route[0],
                    carrier=route[1],
                    city=cities[route],
                    is_assumed=True,
                    assumption_source="route_city_seed_v2",
                )
                session.add(w)
                session.flush()
                warehouses[route] = w
        known = {
            (i.warehouse_id, i.sku, i.product_type): i
            for i in session.scalars(select(Item))
        }
        for key, seen in catalog.items():
            country, carrier, sku, ptype = key
            wh = warehouses[(country, carrier)]
            item_key = (wh.id, sku, ptype)
            item = known.get(item_key)
            if item is None:
                item = Item(
                    warehouse_id=wh.id,
                    sku=sku,
                    product_type=ptype,
                    first_seen_date=seen.date(),
                )
                session.add(item)
                session.flush()
            elif item.first_seen_date != seen.date():
                raise DomainError(
                    "catalog_mismatch",
                    "An existing item has a different first-seen date",
                )
            item_map[key] = item.id
        session.get(Run, run_id).result_summary = {
            "phase": "import_daily_sales",
            "items": len(item_map),
            "routes": len(routes),
        }
    # COPY stays inside the SQLAlchemy transaction. No CSV/raw file is uploaded.
    with sessions.begin() as session:
        connection = session.connection().connection.driver_connection
        with (
            connection.cursor() as cursor,
            cursor.copy(
                "COPY daily_sales (source_import_run_id,item_id,date,sales_qty,order_count,actual_available) FROM STDIN"
            ) as copy,
        ):
            for key, item_id in item_map.items():
                try:
                    part = grouped.loc[key].reindex(expected_days, fill_value=0)
                except KeyError:
                    raise DomainError(
                        "catalog_mismatch", "Known item has no source aggregate"
                    )
                for day, row in part.iterrows():
                    copy.write_row(
                        (
                            run_id,
                            item_id,
                            day.date(),
                            int(row.sales_qty),
                            int(row.order_count),
                            True,
                        )
                    )
        count, quantity = session.execute(
            select(func.count(), func.sum(DailySales.sales_qty)).where(
                DailySales.source_import_run_id == run_id
            )
        ).one()
        if (
            count != len(item_map) * len(expected_days)
            or int(quantity or 0) != audit["sales_quantity"]
        ):
            raise DomainError(
                "source_reconciliation_failed", "Daily item quantities do not reconcile"
            )
        summary = dict(
            phase="verified",
            raw_rows=audit["rows_raw"],
            sales_quantity=audit["sales_quantity"],
            routes=len(routes),
            items=len(item_map),
            daily_rows=count,
            actual_available_through=cfg["observation_end"],
            audit={k: v for k, v in audit.items() if k != "source_sha256_before"},
            top10=[
                dict(zip(ROUTE, key))
                for key in top[ROUTE].itertuples(index=False, name=None)
            ],
            source_kind="retrospective_order_snapshot",
            inventory_created=False,
        )
        if settings.mode == "demo":
            summary.update(source_kind="derived_anonymized_demo")
        run = session.get(Run, run_id)
        run.result_summary = summary
        run.config_snapshot = {
            **run.config_snapshot,
            "catalog_snapshot": [
                dict(
                    item_id=item_map[key],
                    destination_country=key[0],
                    carrier=key[1],
                    sku=key[2],
                    product_type=key[3],
                    first_seen_date=catalog[key].date().isoformat(),
                )
                for key in item_map
            ],
            "warehouse_snapshot": [
                dict(
                    id=w.id,
                    code=w.code,
                    destination_country=w.destination_country,
                    carrier=w.carrier,
                    city=w.city,
                    is_assumed=True,
                )
                for w in warehouses.values()
            ],
        }
    return summary
