"""Presentation helpers; no changes to forecast or inventory mathematics."""
import re

import pandas as pd

from src.common import ROUTE, ITEM


def evidence_stamps(root, run_id, parent_id):
    """Invalidate the UI cache if either sealed bundle or receipt changes."""
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in [run_id, parent_id]):
        raise ValueError('Invalid evidence run')
    output = root / 'outputs'
    paths = []
    for name in [run_id, parent_id]:
        folder = output / name
        if not folder.is_dir():
            raise FileNotFoundError('Missing result bundle')
        paths.extend(p for p in folder.rglob('*') if p.is_file())
        paths.append(output / (name + '_verification.json'))
    return tuple((p.relative_to(output).as_posix(), p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(paths))


def recommendation_action(row):
    if row['on_hand'] <= 0:
        return 'Hết hàng · ưu tiên xử lý'
    if row['Q'] > 0:
        return 'Xem xét đặt bổ sung'
    if row['needs_replenishment']:
        return 'Đã có hàng đang về · theo dõi ETA'
    return 'Theo dõi định kỳ'


def number(value, decimals=0):
    if value is None or pd.isna(value):
        return '—'
    return f'{float(value):,.{decimals}f}'.translate(str.maketrans(',.', '.,'))


def ranked_recommendations(frame):
    """Present empty/urgent items first; never change policy decisions."""
    result = frame.copy()
    result['priority'] = result.depletion_state.map({
        'already_empty': 0, 'urgent': 1, 'early': 3,
        'no_depletion_within_horizon': 4}).fillna(5)
    result.loc[result.needs_replenishment & result.priority.gt(2), 'priority'] = 2
    return result.sort_values(['priority', 'Q'] + ITEM,
        ascending=[True, False] + [True] * len(ITEM)).reset_index(drop=True)


def demand_chart_data(daily, forecast, origin, history_days=45):
    """Observed history and daily allocation are distinct series with no future zero fill."""
    origin = pd.Timestamp(origin)
    actual = daily.groupby('date', as_index=False).sales_qty.sum(min_count=1)
    actual = actual.loc[actual.date.between(origin-pd.Timedelta(days=history_days-1), origin)]
    actual = actual.rename(columns={'sales_qty': 'quantity'})
    actual['series'] = 'Số bán đã quan sát'
    future = forecast.groupby('target_date', as_index=False).forecast_qty.sum(min_count=1)
    future = future.rename(columns={'target_date': 'date', 'forecast_qty': 'quantity'})
    future['series'] = 'Phân bổ từ dự báo tổng'
    return pd.concat([actual, future], ignore_index=True)


def complete_actual(daily, start, end):
    """No partial actual total: every selected route must have every requested day."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    routes = daily[ROUTE].drop_duplicates()
    expected = len(routes) * ((end-start).days+1)
    part = daily.loc[daily.date.between(start, end)]
    if not expected or len(part) != expected or part.sales_qty.isna().any():
        return None
    if part.duplicated(ROUTE+['date']).any():
        raise ValueError('Duplicate daily actual')
    return float(part.sales_qty.sum())


def scenario_comparison(metrics):
    result = metrics.loc[metrics.evaluation.eq('continuous_replenishment_policy')].copy()
    if result.scenario_id.duplicated().any() or not result.scenario_id.eq('base').any():
        raise ValueError('Ambiguous scenario metrics')
    base = result.loc[result.scenario_id.eq('base')].iloc[0]
    result['fill_change_pp'] = (result.fill_rate-base.fill_rate)*100
    result['shortage_change'] = result.shortage-base.shortage
    return result


def item_parameters(scenario_config, row):
    """Use the actual per-scenario partner settings, including sensitivity cases."""
    configs = {x['scenario']['name']: x['inventory'] for x in scenario_config}
    return configs[row['scenario_id']]['partners'][row['partner_id']]


def filter_frame(frame, country='Tất cả', carrier='Tất cả', sku='Tất cả', ptype='Tất cả'):
    result=frame.copy()
    for column, value in [('destination_country',country),('carrier',carrier),('sku',sku),('product_type',ptype)]:
        if column in result and value != 'Tất cả':
            result=result.loc[result[column].eq(value)]
    return result


def ledger_timeline(path, chunksize=100_000):
    keys=['scenario_id','date']+ROUTE
    values=['scenario_demand','fulfilled','shortage','closing']
    parts=[]
    for chunk in pd.read_csv(path,usecols=keys+values,chunksize=chunksize,parse_dates=['date']):
        parts.append(chunk.groupby(keys,as_index=False)[values].sum())
    return pd.concat(parts,ignore_index=True).groupby(keys,as_index=False)[values].sum()


def timeline_metrics(timeline):
    totals=timeline.groupby('scenario_id',as_index=False)[['scenario_demand','fulfilled','shortage']].sum()
    closing=timeline.groupby(['scenario_id','date']).closing.sum().groupby('scenario_id').mean()
    totals['mean_closing_on_hand']=totals.scenario_id.map(closing)
    totals['fill_rate']=totals.fulfilled.div(totals.scenario_demand.where(totals.scenario_demand.gt(0)))
    totals['evaluation']='continuous_replenishment_policy'
    return totals.rename(columns={'scenario_demand':'demand'})
