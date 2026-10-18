"""Prospective what-if planning from a frozen forecast, never actual sales.

This small runtime module needs no raw orders, training dependencies, or disk
writes. It does not change the sealed historical benchmark or place orders.
"""
from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Assumptions:
    on_hand: int
    pending_quantity: int
    pending_due_days: int
    lead_time_days: int
    review_days: int
    safety_days: float
    moq: int = 1
    demand_multiplier: float = 1.
    receipt_fraction: float = 1.
    receipt_delay_days: int = 0


def validate(assumptions, horizon):
    for name in ['on_hand','pending_quantity','pending_due_days','lead_time_days',
                 'review_days','moq','receipt_delay_days']:
        value=getattr(assumptions,name)
        if isinstance(value,bool) or not isinstance(value,(int,np.integer)):
            raise ValueError('Planning quantities and days must be integers')
        minimum=1 if name in ['pending_due_days','lead_time_days','review_days','moq'] else 0
        if value<minimum:raise ValueError('Invalid planning quantity or day')
    if assumptions.lead_time_days+assumptions.review_days>horizon:
        raise ValueError('Forecast must cover lead time plus review period')
    for name in ['safety_days','demand_multiplier','receipt_fraction']:
        if not np.isfinite(getattr(assumptions,name)) or getattr(assumptions,name)<0:
            raise ValueError('Invalid planning factor')
    if assumptions.receipt_fraction>1:raise ValueError('Receipt fraction cannot exceed one')


def thresholds(on_hand,forecast,pending,assumptions):
    """Same strict ROP/IP/Q rule as the historical policy; no zero padding."""
    forecast=np.asarray(forecast,dtype=float)
    lead,review=assumptions.lead_time_days,assumptions.review_days
    if len(forecast)<lead+review:
        return {'SS':np.nan,'ROP':np.nan,'S':np.nan,'IP':on_hand+pending,
            'Q':np.nan,'needs_replenishment':None,'decision_status':'insufficient_forecast'}
    safety=math.ceil(assumptions.safety_days*forecast.mean())
    rop=math.ceil(forecast[:lead].sum()+safety)
    target=math.ceil(forecast[:lead+review].sum()+safety)
    ip=on_hand+pending
    trigger=on_hand<rop
    quantity=math.ceil(max(0,target-ip)) if trigger else 0
    if quantity>0:quantity=max(quantity,assumptions.moq)
    return {'SS':safety,'ROP':rop,'S':target,'IP':ip,'Q':quantity,
        'needs_replenishment':trigger,'decision_status':'forecast_available'}


def simulate(forecast,origin,assumptions):
    """Dated expected-value ledger with receipts first and orders after close.

    Initial pending ETA is an explicit assumption: the released snapshot only
    gives the quantity. Pending promises are removed in full on receipt even
    when modeled delivery is partial; undelivered quantity is not restocked.
    """
    vector=np.asarray(forecast,dtype=float)
    if vector.ndim!=1 or not 1<=len(vector)<=90 or not np.isfinite(vector).all() or (vector<0).any():
        raise ValueError('Invalid complete planning forecast')
    origin=pd.Timestamp(origin)
    if pd.isna(origin):raise ValueError('Invalid planning origin')
    validate(assumptions,len(vector))
    demand=vector*assumptions.demand_multiplier
    if not np.isfinite(demand).all():raise ValueError('Invalid projected demand')
    outstanding=[];orders=[];rows=[]
    if assumptions.pending_quantity:
        outstanding.append({'due_day':assumptions.pending_due_days+assumptions.receipt_delay_days,
            'promised_quantity':assumptions.pending_quantity,'initial':True})
    stock=float(assumptions.on_hand)

    def order_after_close(day):
        pending=sum(x['promised_quantity'] for x in outstanding)
        decision=thresholds(stock,demand[day:],pending,assumptions)
        quantity=decision['Q']
        if pd.notna(quantity) and quantity>0:
            due=day+assumptions.lead_time_days+assumptions.receipt_delay_days
            outstanding.append({'due_day':due,'promised_quantity':int(quantity),'initial':False})
            orders.append({'placed_date':origin+pd.Timedelta(days=day),
                'modeled_eta':origin+pd.Timedelta(days=due),'ordered_quantity':int(quantity),
                'modeled_receipt_quantity':math.floor(quantity*assumptions.receipt_fraction),
                'within_forecast_horizon':due<=len(vector),'is_assumed_plan':True})
        return decision

    first=order_after_close(0)
    rows.append({'date':origin,'day':0,'opening':stock,'receipts':0.,'demand':0.,
        'fulfilled':0.,'shortage':0.,'closing':stock,**first,'actual_qty':np.nan,'is_assumed_plan':True})
    for day,quantity in enumerate(demand,1):
        opening=stock
        arriving=[x for x in outstanding if x['due_day']==day]
        received=sum(math.floor(x['promised_quantity']*assumptions.receipt_fraction) for x in arriving)
        outstanding=[x for x in outstanding if x['due_day']!=day]
        stock+=received
        fulfilled=min(float(quantity),stock)
        shortage=float(quantity)-fulfilled
        stock-=fulfilled
        decision=order_after_close(day)
        rows.append({'date':origin+pd.Timedelta(days=day),'day':day,'opening':opening,
            'receipts':float(received),'demand':float(quantity),'fulfilled':fulfilled,
            'shortage':shortage,'closing':stock,**decision,'actual_qty':np.nan,'is_assumed_plan':True})
    ledger=pd.DataFrame(rows)
    order_frame=pd.DataFrame(orders,columns=['placed_date','modeled_eta','ordered_quantity',
        'modeled_receipt_quantity','within_forecast_horizon','is_assumed_plan'])
    horizon=ledger.loc[ledger.day.gt(0)]
    total=float(horizon.demand.sum())
    summary={'expected_demand':total,'expected_fulfilled':float(horizon.fulfilled.sum()),
        'expected_shortage':float(horizon.shortage.sum()),
        'expected_fill_rate':float(horizon.fulfilled.sum()/total) if total>0 else None,
        'mean_closing_on_hand':float(horizon.closing.mean()),
        'planned_order_quantity':int(order_frame.ordered_quantity.sum()),'planned_order_lines':len(order_frame),
        'first_shortage_date':horizon.loc[horizon.shortage.gt(1e-9),'date'].min(),
        'horizon_days':len(vector),'is_expected_projection':True,'benchmark_metric':False}
    return {'ledger':ledger,'orders':order_frame,'summary':summary}
