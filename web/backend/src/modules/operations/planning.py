"""Current network-stock advisory; never modifies historical runs or posts orders."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
import math
from sqlalchemy import select, func, text
from core.errors import DomainError
from modules.catalog.models import Item, Warehouse, Supplier
from modules.catalog.provider import trade_state
from modules.catalog.trade_service import provider_notices
from modules.catalog.supply_service import supply_rows
from modules.configuration.models import Policy
from modules.forecasting.models import ItemForecast
from modules.runs.models import Run
from modules.operations.models import OperationalProduct, StockBalance, SupplierSettings
from modules.operations.models import OperationalOrder, OperationalOrderLine
from modules.operations.schemas import MAX_QTY

PROFILE = "ops_network_fixed_lot_h14_v1"


def calculate(stock, receipts, forecast, lead, safety_days, floor, lot, origin):
    """All quantities cover this item across warehouses exactly once."""
    result = dict(rop=None, safety_stock=None, recommended_qty=None, decision="blocked", projection=[])
    horizon = (max(forecast)-origin).days if forecast else 0
    if not 1 <= lead < horizon <= 14:
        return {**result, "reason": "forecast_horizon_short", "required_days": lead + 1}
    dates = [origin + timedelta(days=i) for i in range(1, horizon+1)]
    if set(forecast) != set(dates) or any(not math.isfinite(float(v)) or v < 0 for v in forecast.values()):
        return {**result, "reason": "forecast_incomplete"}
    if stock < 0 or stock > MAX_QTY or not lot or lot > MAX_QTY:
        return {**result, "reason": "quantity_out_of_range"}
    demand = [Decimal(str(forecast[day])) for day in dates]
    ceil = lambda value: int(value.to_integral_value(rounding=ROUND_CEILING))
    ss = ceil(sum(demand) / horizon * Decimal(str(safety_days)))
    rop = max(floor, ceil(sum(demand[:lead]) + ss))
    overdue = sum(qty for day, qty in receipts.items() if day <= origin)
    pending = sum(receipts.values())
    timely = sum(qty for day, qty in receipts.items() if origin < day <= dates[lead - 1])
    position = stock + timely
    qty = lot if position <= rop else 0
    if max(rop, ss, position, pending, stock + pending) > MAX_QTY:
        return {**result, "reason": "quantity_out_of_range"}
    balance, first_shortage = Decimal(stock), None
    projection = []
    for day, expected in zip(dates, demand):
        received = receipts.get(day, 0)
        available = balance + received
        shortage = max(Decimal(0), expected - available)
        balance = max(Decimal(0), available - expected)
        if shortage > 0 and first_shortage is None:
            first_shortage = day
        projection.append(dict(date=str(day), demand=float(expected), receipts_qty=received,
                               closing_qty=float(balance), shortage_qty=float(shortage)))
    # An overdue delivery has no reliable future receipt date. Do not double-order automatically.
    decision = "review_overdue" if overdue else "order" if qty else "covered"
    return dict(rop=rop, safety_stock=ss, recommended_qty=None if overdue else qty,
        decision=decision, reason="overdue_receipt_unknown" if overdue else "fixed_lot_policy",
        on_hand_qty=stock, pending_qty=pending, eligible_pending_qty=timely, inventory_position=position,
        overdue_qty=overdue, first_shortage_date=str(first_shortage) if first_shortage else None,
        urgent=first_shortage is not None and (first_shortage-origin).days < 7,
        shortage_before_new_eta=first_shortage is not None and first_shortage <= origin+timedelta(days=lead),
        projection=projection, required_days=lead+1, available_days=horizon)


def recommendations(session, page, size, run_id=None):
    origin = datetime.now(timezone.utc).date()
    captured = datetime.now(timezone.utc)
    # One consistent read: balances, POs, policy, supplier defaults and forecast cannot mix commits.
    session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    query = select(OperationalProduct.item_id, OperationalProduct.name, Item.sku, Supplier.id.label("supplier_id"),
        Supplier.carrier).join(Item, Item.id == OperationalProduct.item_id).join(Warehouse, Warehouse.id == Item.warehouse_id).join(
        Supplier, Supplier.carrier == Warehouse.carrier).where(OperationalProduct.active.is_(True))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    products = session.execute(query.order_by(OperationalProduct.item_id).offset((page-1)*size).limit(size)).mappings().all()
    ids = [row['item_id'] for row in products]
    options = session.execute(select(Run.id, Run.created_at).where(Run.kind == 'forecast', Run.status == 'complete',
        Run.observation_end <= origin, Run.id.in_(select(ItemForecast.run_id).where(ItemForecast.as_of_date.between(origin-timedelta(days=1), origin))))
        .order_by(Run.created_at.desc()).limit(20)).all()
    selected_id = run_id or (options[0].id if options else None)
    run = session.get(Run, selected_id) if selected_id else None
    if run_id and (run is None or run.kind != 'forecast' or run.status != 'complete'):
        raise DomainError('invalid_forecast', 'Chọn lượt dự báo đã hoàn tất.', 409)
    source = session.get(Run, run.source_import_run_id) if run and run.source_import_run_id else None
    usable = bool(run and run.status == 'complete' and run.observation_end <= origin and
        source and source.kind == 'source_import' and source.status == 'complete' and source.observation_end <= origin)
    balances = dict(session.execute(select(StockBalance.item_id, func.sum(StockBalance.on_hand_qty)).where(
        StockBalance.item_id.in_(ids)).group_by(StockBalance.item_id)).all())
    leads = {row.supplier_id: row for row in session.scalars(select(SupplierSettings).where(
        SupplierSettings.supplier_id.in_([row['supplier_id'] for row in products])))}
    policies = {}
    for policy in session.scalars(select(Policy).where(Policy.item_id.in_(ids), Policy.effective_from <= origin,
            (Policy.effective_to.is_(None)) | (Policy.effective_to > origin)).order_by(Policy.version)):
        policies[policy.item_id] = policy
    receipts, forecasts = {}, {}
    incoming = session.execute(select(OperationalOrderLine.item_id, OperationalOrder.eta,
        func.sum(OperationalOrderLine.ordered_qty-OperationalOrderLine.received_qty)).join(
        OperationalOrder, OperationalOrder.id == OperationalOrderLine.order_id).where(
        OperationalOrderLine.item_id.in_(ids), OperationalOrder.status.in_(['ordered','partially_received']))
        .group_by(OperationalOrderLine.item_id, OperationalOrder.eta)).all()
    for iid, eta, amount in incoming:
        if amount > 0:
            receipts.setdefault(iid, {})[eta] = int(amount)
    basis = session.scalar(select(func.max(ItemForecast.as_of_date)).where(ItemForecast.run_id == selected_id,
        ItemForecast.as_of_date.between(origin-timedelta(days=1), origin))) if usable else None
    if usable and basis:
        for iid, day, qty in session.execute(select(ItemForecast.item_id, ItemForecast.target_date, ItemForecast.forecast_qty).where(
                ItemForecast.run_id == run.id, ItemForecast.item_id.in_(ids), ItemForecast.as_of_date == basis,
                ItemForecast.target_date > origin)):
            forecasts.setdefault(iid, {})[day] = qty
    changes = supply_rows(session, ids, origin)
    notices = provider_notices(session, ids, origin)
    result = []
    for product in products:
        iid = product['item_id']; lead = leads[product['supplier_id']].lead_time_days if product['supplier_id'] in leads else 7
        row = {**dict(product), 'lead_time_days':lead, 'on_hand_qty':int(balances.get(iid,0)),
               'decision':'blocked', 'recommended_qty':None, 'rop':None, 'safety_stock':None}
        policy = policies.get(iid)
        if not usable or iid not in forecasts:
            row['reason'] = 'current_forecast_missing'
        elif policy is None or policy.supplier_id != product['supplier_id'] or policy.fixed_order_qty is None:
            row['reason'] = 'fixed_policy_missing'
        elif any(not trade_state(changes, notices, iid, origin, origin+timedelta(days=day))['replenishment_allowed'] or
                 not trade_state(changes, notices, iid, origin, origin+timedelta(days=day))['sales_allowed'] for day in range(15)):
            row['reason'] = 'supply_restricted'
        else:
            row.update(calculate(row['on_hand_qty'], receipts.get(iid,{}), forecasts[iid], lead,
                policy.safety_days, policy.configured_rop_floor, policy.fixed_order_qty, origin))
            row.update(policy_version=policy.version, fixed_order_qty=policy.fixed_order_qty)
        if row['on_hand_qty'] > MAX_QTY:
            row['on_hand_qty'] = str(row['on_hand_qty'])
        result.append(row)
    return dict(items=result,total=total,page=page,page_size=size,profile=PROFILE,origin=str(origin),forecast_origin=str(basis) if basis else None,captured_at=captured,
        forecast_run_id=str(selected_id) if selected_id else None, forecast_options=[str(row.id) for row in options],
        assumptions=['network_stock_no_transfer_constraints','balance_held_to_next_utc_day','supplier_eta_calendar_date',
                     'safety_mean_available_days','no_automatic_purchase','overdue_eta_not_assumed_received'])
