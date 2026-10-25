"""Read-only recommendations and receipt history using frozen as-of knowledge."""
from core.errors import DomainError
from core.run_context import required_run
from modules.reporting.schemas import Filters
from modules.reporting.service import context, dataset

def purchasing_data(session, key, filters):
    run = required_run(session, key, complete=True)
    if run.kind not in {"stock_projection", "policy_replay", "alert_replay"}:
        raise DomainError("parent_mismatch", "Choose an inventory plan", 409)
    day = filters.as_of_date
    base = Filters(
        **filters.model_dump(
            include={"warehouse_id", "item_id", "supplier_id", "product_type"}
        )
    )
    inventory, _ = dataset(
        session,
        run,
        "inventory_daily",
        base.model_copy(update={"date_from": day, "date_to": day}),
        paginate=False,
    )
    lots, _ = dataset(session, run, "replenishments", base, paginate=False)
    recorded_end = (
        run.as_of_date
        if run.kind == "stock_projection"
        else run.period_end or run.as_of_date
    )
    known_on = min(day, recorded_end)
    words = filters.search.casefold().split()

    def matches(row):
        haystack = " ".join(
            str(row.get(k, ""))
            for k in ["sku", "product_type", "carrier", "destination_country"]
        ).casefold()
        return all(word in haystack for word in words)

    inventory = [row for row in inventory if matches(row)]
    recommendations = [
        {**row, "operational_status": "low_stock"}
        for row in inventory
        if row["needs_replenishment"] and row["recommended_qty"] > 0
    ]
    history = []
    for row in lots:
        if row["ordered_on"] > known_on or not matches(row):
            continue
        # Final replay status must not expose a later receipt at an earlier date.
        received = row["eta"] <= known_on and row["received_qty"] > 0
        history.append(
            {
                **row,
                "status": "received" if received else "ordered",
                "received_qty": row["received_qty"] if received else 0,
            }
        )
    incoming = [row for row in history if row["eta"] > known_on]
    summary = dict(
        inventory_available=bool(inventory),
        recommended_items=len(recommendations),
        recommended_units=sum(row["recommended_qty"] for row in recommendations),
        incoming_lots=len(incoming),
        pending_units=sum(row["ordered_qty"] for row in incoming),
        historical_lots=len(history),
    )
    rows = {
        "recommendations": recommendations,
        "incoming": incoming,
        "history": history,
    }[filters.view]
    quantity = "recommended_qty" if filters.view == "recommendations" else "ordered_qty"
    eta = "eta_if_ordered" if filters.view == "recommendations" else "eta"
    if filters.sort == "ordered_desc":
        if filters.view == "recommendations":
            raise DomainError(
                "invalid_input", "Order-date sorting requires receipt lots"
            )
        rows.sort(key=lambda row: (row["ordered_on"], row["id"]), reverse=True)
    elif filters.sort == "eta_asc":
        rows.sort(
            key=lambda row: (
                row.get(eta) is None,
                str(row.get(eta)),
                row["item_id"],
                row["id"],
            )
        )
    else:
        direction = -1 if filters.sort == "quantity_desc" else 1
        rows.sort(
            key=lambda row: (direction * row[quantity], row["item_id"], row["id"])
        )
    return dict(
        context={
            **context(run),
            "view_date": day.isoformat(),
            "known_orders_through": known_on.isoformat(),
            "view": filters.view,
            "search": filters.search,
            "sort": filters.sort,
        },
        summary=summary,
        items=rows,
        total=len(rows),
    )
