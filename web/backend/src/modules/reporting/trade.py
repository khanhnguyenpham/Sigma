"""Read stored trade results; only rights metadata is resolved from frozen history."""
from datetime import date
from collections import defaultdict
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from core.errors import DomainError
from modules.catalog.provider import trade_state
from modules.alerts.models import Alert
from modules.purchasing.models import Replenishment
from modules.inventory.models import InventoryDaily
from modules.catalog.trade_service import TRADE_PROFILE as PROFILE, TRADE_RULES

RIGHT_FILTERS = ('internal_status','provider_status','replenishment_allowed','sales_allowed')
CAP_FIELDS = ('q_policy','q_final','cap_reason','sellable_budget','provider_stop_on','eta','forecast_coverage_complete')
PROJECTION_QUANTITIES = ('forecast_demand_qty','forecast_input_qty','projected_sales_qty','sales_blocked_qty',
    'unserved_stock_qty','unserved_demand_qty','closing_forecast','receipts_qty','available_total','sellable_qty',
    'blocked_stock_before_sale','closing_total','closing_sellable','closing_blocked')


def is_trade(run):
    snap = run.config_snapshot
    profile = snap.get('trade_lifecycle_profile')
    if profile is None:
        if any(k in snap for k in ('trade_rules','internal_supply_snapshot','provider_notice_snapshot')):
            raise DomainError('invalid_trade_history','Trade snapshot is missing its profile',409)
        return False
    if profile != PROFILE:
        raise DomainError('invalid_trade_history','Unsupported trade lifecycle profile',409)
    if (not isinstance(snap.get('internal_supply_snapshot'),list) or not isinstance(snap.get('provider_notice_snapshot'),list)
        or snap.get('trade_rules') != TRADE_RULES or 'supply_lifecycle_profile' in snap or 'supply_lifecycle_snapshot' in snap):
        raise DomainError('invalid_trade_history','Frozen trade snapshot is incomplete',409)
    return True


def validate_filters(run, filters, inventory=True):
    requested = any(getattr(filters,k,None) is not None for k in RIGHT_FILTERS)
    if requested and not inventory:
        raise DomainError('invalid_input','Trade rights filters require inventory results')
    if requested and not is_trade(run):
        raise DomainError('feature_not_in_run','Trade rights are not available in this historical plan',409)


def matches(row, filters):
    return all(getattr(filters,k,None) is None or row.get(k) == getattr(filters,k) for k in RIGHT_FILTERS)


def frozen_rights(run, item, origin, target):
    snap = run.config_snapshot
    try:
        return jsonable_encoder(trade_state(snap['internal_supply_snapshot'],snap['provider_notice_snapshot'],item,origin,target))
    except (KeyError,TypeError,ValueError):
        raise DomainError('invalid_trade_history','Frozen trade history is incomplete',409) from None


def notice_metadata(run,item,cutoff):
    visible = [n for n in run.config_snapshot['provider_notice_snapshot'] if item in n['item_ids']
        and any(e['known_on'] <= str(cutoff) for e in n['events'])]
    return dict(provider_notice_ids=[n['id'] for n in visible],
        provider_sources=[dict(notice_id=n['id'], **{k:e[k] for k in ('action','known_on','effective_on','source_description','source_ref','is_assumed')})
            for n in visible for e in n['events'] if e['known_on'] <= str(cutoff)])


def row_rights(run, item, window, target):
    cutoff = window if run.kind == 'alert_replay' else min(target,run.period_end or run.as_of_date)
    state = frozen_rights(run,item,cutoff,target)
    reasons = ([] if state['internal_status'] != 'stopped' else ['internal_stopped'])
    if not state['sales_allowed']:
        reasons.append('provider_blocked')
    return dict(state, trade_lifecycle_profile=PROFILE, decision_origin=cutoff, rights_on=target,
        supply_status=state['internal_status'], replenishment_block_reason=reasons[0] if reasons else None,
        replenishment_block_reasons=reasons, **notice_metadata(run,item,cutoff),
        provider_reasons=[b['reason'] for b in state['provider_blockers']],
        )


def decorate_rows(session, run, rows, name, view_date=None):
    ids = {r['item_id'] for r in rows}
    dates = {r.get('date') or r.get('as_of_date') for r in rows} - {None}
    decisions = {}
    if name == 'inventory_daily' and dates:
        decisions = {(a.window_origin,a.item_id,a.as_of_date):a.explanation for a in session.scalars(select(Alert).where(
            Alert.run_id==run.id,Alert.alert_type=='depletion',Alert.item_id.in_(ids),Alert.as_of_date.in_(dates)))}
    lots = defaultdict(list)
    if name=='inventory_daily':
        for lot in session.scalars(select(Replenishment).where(Replenishment.run_id==run.id,Replenishment.item_id.in_(ids))):
            lots[(lot.window_origin,lot.item_id)].append(lot)
    stocks={}
    if name=='replenishments':
        days={max(view_date or r['ordered_on'],r['window_origin']) for r in rows}
        stocks={(w,i,d):q for w,i,d,q in session.execute(select(InventoryDaily.window_origin,InventoryDaily.item_id,
            InventoryDaily.date,InventoryDaily.closing_qty).where(InventoryDaily.run_id==run.id,
                InventoryDaily.item_id.in_(ids),InventoryDaily.date.in_(days)))}
    for row in rows:
        target = row.get('date') or row.get('as_of_date') or max(view_date or row['ordered_on'],row['window_origin'])
        state = row_rights(run,row['item_id'],row['window_origin'],target)
        exp = row.get('explanation') if name == 'alerts' else decisions.get((row['window_origin'],row['item_id'],target))
        exp = exp or {}
        row.update(state)
        row.update({('cap_eta' if k=='eta' else k):exp.get(k) for k in CAP_FIELDS})
        row['quantity_diagnostics_available'] = all(k in exp for k in CAP_FIELDS)
        row['stock_below_rop'] = row['closing_qty'] < row['rop'] if name == 'inventory_daily' else exp.get('stock_below_rop')
        row['sell_through_state'] = None
        if name == 'inventory_daily':
            if row.get('source_sales_qty') is None or row.get('actual_blocked_qty') is None:
                raise DomainError('feature_not_in_run','Trade source quantities are missing from this plan',409)
            row.update(total_qty=row['closing_qty'],sellable_qty=row['closing_qty'] if state['sales_allowed'] else 0,
                blocked_qty=0 if state['sales_allowed'] else row['closing_qty'],scenario_sales_qty=row['sales_qty'],
                q_final=row['recommended_qty'])
            known_lots = [lot for lot in lots[(row['window_origin'],row['item_id'])] if lot.eta > target
                and (lot.is_initial or lot.ordered_on < target)]
            row['needs_supplier_action'] = row['blocked_qty'] > 0 or any(not frozen_rights(run,row['item_id'],state['decision_origin'],lot.eta)['sales_allowed'] for lot in known_lots)
            row['actionable'] = bool(row['recommended_qty']) and state['replenishment_allowed']
        elif name == 'replenishments':
            eta_cutoff = min(state['decision_origin'],row['eta'])
            eta_state = frozen_rights(run,row['item_id'],eta_cutoff,row['eta'])
            row['sales_allowed_at_eta'] = eta_state['sales_allowed']
            stock=stocks.get((row['window_origin'],row['item_id'],target))
            row['stock_impact_available']=stock is not None
            row['needs_supplier_action'] = (not eta_state['sales_allowed'] if row['eta']>target else
                not state['sales_allowed'] and stock>0 if stock is not None else None)
            row['actionable'] = False
        else:
            row.update({k:exp.get(k) for k in ('total_qty','sellable_qty','blocked_qty','needs_supplier_action','actionable')})
        cap = row.get('cap_reason')
        if cap and cap not in row['replenishment_block_reasons']:
            row['replenishment_block_reasons'].append(cap)
            row['replenishment_block_reason'] = row['replenishment_block_reason'] or cap
        row['metric_basis'] = 'allowed_scenario_sales'
    return rows


def counters(rows):
    internal = {r['item_id'] for r in rows if r.get('internal_status')=='stopped'}
    provider = {r['item_id'] for r in rows if r.get('sales_allowed') is False}
    limited = {r['item_id'] for r in rows if r.get('cap_reason')}
    return dict(internal_stopped_items=len(internal),provider_blocked_items=len(provider),
        blocked_stock_items=len({r['item_id'] for r in rows if (r.get('blocked_qty') or 0)>0}),
        purchase_limited_items=len(limited),affected_items=len(internal|provider|limited),
        needs_supplier_action_items=len({r['item_id'] for r in rows if r.get('needs_supplier_action')}),
        total_units=sum(r['total_qty'] for r in rows) if rows else None,
        sellable_units=sum(r['sellable_qty'] for r in rows) if rows else None,
        blocked_units=sum(r['blocked_qty'] for r in rows) if rows else None)


def aggregate_projection(rows):
    groups = {}
    for row in rows:
        key = (row['window_origin'],row['as_of_date'],row['warehouse_id'],row['target_date'])
        group = groups.setdefault(key, {**{k:row[k] for k in ('window_origin','as_of_date','warehouse_id','city','display_city','destination_country','carrier','target_date','horizon_day')},
            **{k:0 for k in PROJECTION_QUANTITIES},'item_count':0,'internal_stopped_items':0,'provider_blocked_items':0,'affected_items':0,
            'replenishment_allowed_items':0,'sales_allowed_items':0,'provider_notice_ids':[],
            'provider_reasons':[],'provider_sources':[],'internal_reasons':[],
            'internal_status_counts':{},'provider_status_counts':{}})
        group['item_count'] += 1
        internal, provider = row['internal_status']=='stopped', not row['sales_allowed']
        group['internal_stopped_items'] += internal
        group['provider_blocked_items'] += provider
        group['affected_items'] += internal or provider
        group['replenishment_allowed_items'] += row['replenishment_allowed']
        group['sales_allowed_items'] += row['sales_allowed']
        for field in ('provider_notice_ids','provider_reasons','provider_sources'):
            for value in row[field]:
                if value not in group[field]:group[field].append(value)
        if row['internal_reason'] and row['internal_reason'] not in group['internal_reasons']:
            group['internal_reasons'].append(row['internal_reason'])
        for field in ('internal_status','provider_status'):
            counts=group[field+'_counts'];counts[row[field]]=counts.get(row[field],0)+1
        for k in PROJECTION_QUANTITIES:
            group[k] += row[k]
    return list(groups.values())


def sell_through(session, run, filters, items, warehouses, selected, paginate):
    if any(getattr(filters,k) is not None for k in ('split','block','state','alert_type','granularity','cadence')):
        raise DomainError('invalid_input','Unsupported sell-through filter')
    origin = filters.as_of_date or run.as_of_date
    query = select(Alert).where(Alert.run_id==run.id,Alert.alert_type=='depletion',Alert.as_of_date==origin,Alert.item_id.in_(selected))
    if filters.window_origin:
        query = query.where(Alert.window_origin==filters.window_origin)
    rows = []
    for alert in session.scalars(query):
        path = alert.explanation.get('projection')
        if not isinstance(path,list) or len(path)!=14 or any(not set(PROJECTION_QUANTITIES+RIGHT_FILTERS) <= set(p) for p in path):
            raise DomainError('feature_not_in_run','Stored trade projection is incomplete; create a new plan',409)
        item = items[alert.item_id];warehouse=warehouses[item['warehouse_id']]
        sources=notice_metadata(run,alert.item_id,origin)
        for h, projected in enumerate(path,1):
            target = date.fromisoformat(projected['date'])
            if (filters.date_from and target<filters.date_from) or (filters.date_to and target>filters.date_to):
                continue
            row = dict(item,city=warehouse['city'],display_city=warehouse['display_city'],window_origin=alert.window_origin,
                as_of_date=origin,target_date=target,horizon_day=h,**{k:v for k,v in projected.items() if k!='date'})
            row.update(sources,supply_status=row['internal_status'],provider_reasons=[b['reason'] for b in row['provider_blockers']])
            row.update({('cap_eta' if k=='eta' else k):alert.explanation.get(k) for k in CAP_FIELDS},recommendation_as_of_date=origin)
            if matches(row,filters):rows.append(row)
    if filters.aggregate=='route_day':rows=aggregate_projection(rows)
    rows.sort(key=lambda r:(r['target_date'],r['window_origin'],r['warehouse_id'],r.get('item_id',0)))
    return (rows[(filters.page-1)*filters.page_size:filters.page*filters.page_size] if paginate else rows),len(rows)


def metric_records(session, run, filters):
    """Aggregate persisted replay cases/quantities, never forecast or simulate."""
    from datetime import timedelta
    from modules.reporting.service import dataset
    from modules.reporting.schemas import Filters
    from modules.alerts.service import replay_metrics, threshold_metrics
    if any(getattr(filters,k) is not None for k in ('split','block','cadence','aggregate','state','alert_type')):
        raise DomainError('invalid_input','Unsupported trade metric filter')
    if filters.granularity not in (None,'alert','policy','threshold'):
        raise DomainError('invalid_input','Trade metrics use policy, alert or threshold granularity')
    scope_fields=RIGHT_FILTERS+('sku','destination_country','carrier','window_origin','warehouse_id','item_id','supplier_id','product_type','as_of_date','date_from','date_to')
    if all(getattr(filters,k) is None for k in scope_fields):
        summary=run.result_summary
        quantities=('source_sales_qty','scenario_sales_qty','actual_blocked_qty','sales_qty','fulfilled_qty','shortage_qty','fill_allowed','fill_rate','blocked_source_rate')
        if not all(k in summary for k in quantities):
            raise DomainError('feature_not_in_run','Stored trade metrics are incomplete',409)
        return [dict(r,**{k:summary[k] for k in quantities},trade_lifecycle_profile=PROFILE,
            metric_basis='allowed_scenario_sales',filter_basis='whole_run',metric_exclusions=summary['metric_exclusions'],
            excluded_item_windows=summary['excluded_item_windows']) for r in summary['metrics'] if not filters.granularity or r['granularity']==filters.granularity]
    if run.kind == 'alert_replay':
        # Date filters select whole origins, never partial evaluation windows.
        scope = filters.model_copy(update={'as_of_date':None,'date_from':None,'date_to':None,'granularity':None})
        origins,_ = dataset(session,run,'inventory_daily',scope,paginate=False)
        origins = [r for r in origins if r['date']==r['window_origin']
            and (not filters.as_of_date or r['date']==filters.as_of_date)
            and (not filters.date_from or r['date']>=filters.date_from)
            and (not filters.date_to or r['date']<=filters.date_to)]
        if not origins:return []
        keys = {(r['window_origin'],r['item_id']) for r in origins}
        base = scope.model_copy(update={k:None for k in RIGHT_FILTERS})
        ledger,_ = dataset(session,run,'inventory_daily',base,paginate=False)
        ledger = [r for r in ledger if (r['window_origin'],r['item_id']) in keys]
        alerts = list(session.scalars(select(Alert).where(Alert.run_id==run.id)))
        signals = {(a.window_origin,a.item_id,a.alert_type):a for a in alerts if a.as_of_date==a.window_origin and (a.window_origin,a.item_id) in keys}
        cases,threshold_cases=[],[]
        exclusions = [e for e in run.result_summary.get('metric_exclusions',[])
            if (date.fromisoformat(e['window_origin']),e['item_id']) in keys]
        excluded = {(date.fromisoformat(e['window_origin']),e['item_id']) for e in exclusions}
        by_key=defaultdict(list)
        for r in ledger:by_key[(r['window_origin'],r['item_id'])].append(r)
        for origin in origins:
            key=(origin['window_origin'],origin['item_id'])
            depletion=signals.get((*key,'depletion'))
            if depletion is None:
                raise DomainError('feature_not_in_run','Stored replay cases are incomplete',409)
            cases.append(dict(as_of_date=depletion.as_of_date,predicted_depletion_date=depletion.predicted_depletion_date,
                actual_depletion_date=depletion.actual_depletion_date,is_evaluable=depletion.is_evaluable))
            predicted=signals.get((*key,'projected_below_rop'))
            n=origin['warning_horizon_days']
            eligible=origin['closing_qty']>=origin['rop'] and key not in excluded
            crossing=min((r['date'] for r in by_key[key] if key[0]<r['date']<=key[0]+timedelta(days=n)
                and r['closing_qty']<origin['rop']),default=None) if eligible else None
            threshold_cases.append(dict(is_evaluable=eligible,predicted_threshold_date=predicted.predicted_threshold_date if predicted else None,
                actual_threshold_date=crossing))
        result=[dict(granularity='alert',**replay_metrics(cases)),dict(granularity='threshold',**threshold_metrics(threshold_cases))]
        basis='whole_selected_item_windows'
    else:
        ledger,_=dataset(session,run,'inventory_daily',filters.model_copy(update={'granularity':None}),paginate=False)
        if not ledger:return []
        result=[dict(granularity='policy')]
        exclusions=[];basis='selected_recorded_dates'
    observed=[r for r in ledger if r['date']>r['window_origin']]
    source=sum(r['source_sales_qty'] for r in observed)
    blocked=sum(r['actual_blocked_qty'] for r in observed)
    allowed=sum(r['sales_qty'] for r in observed)
    fulfilled=sum(r['fulfilled_qty'] for r in observed)
    quantities=dict(source_sales_qty=source,scenario_sales_qty=allowed,actual_blocked_qty=blocked,
        sales_qty=allowed,fulfilled_qty=fulfilled,shortage_qty=allowed-fulfilled,
        fill_allowed=fulfilled/allowed if allowed else None,fill_rate=fulfilled/allowed if allowed else None,
        blocked_source_rate=blocked/source if source else None)
    for row in result:
        row.update(quantities,trade_lifecycle_profile=PROFILE,metric_basis='allowed_scenario_sales',
            filter_basis=basis,metric_exclusions=exclusions,excluded_item_windows=len(exclusions))
    return [r for r in result if not filters.granularity or r['granularity']==filters.granularity]
