"""Build a reproducible ten-route M3 demo without reading private orders."""
import argparse
from pathlib import Path
import re

import pandas as pd

from src.common import ROOT, read_config, sha256, write_csv, write_json
from src.reporting import generate_synthetic
from sigma.forecasting.aggregate import load_settings, execute as forecast
from sigma.verification.aggregate import execute as check_forecast
from sigma.inventory.product30 import execute as product
from sigma.verification.product30 import execute as check_product

ROUTES=[('Vietnam','Vinaphone'),('Thailand','AIS'),('Japan','NTT Docomo'),
    ('South Korea','KT'),('China','China Mobile'),('Singapore','Singtel'),
    ('Australia','Optus'),('Indonesia','Telkomsel'),('United States','T-Mobile'),
    ('United Kingdom','Vodafone')]


def generated_source(path,cfg):
    """The display names are illustrative; every order and quantity is generated."""
    generate_synthetic(path,cfg,route_count=len(ROUTES))
    frame=pd.read_csv(path,dtype=str,keep_default_na=False)
    labels={'Vinaphone':ROUTES[0],**{f'SyntheticCarrier-{i}':pair for i,pair in enumerate(ROUTES) if i}}
    original=frame.carrier.copy()
    frame['destination_country']=original.map(lambda x:labels[x][0])
    frame['carrier']=original.map(lambda x:labels[x][1])
    write_csv(path,frame)
    return Path(path)


def execute(prefix):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',prefix):raise ValueError('Invalid fresh demo prefix')
    out=ROOT/'outputs'/(prefix+'_bundle');out.mkdir(exist_ok=False)
    base=read_config('data/configs/config.original.json')
    source=out/'synthetic_orders.csv'
    base.update(source=source.relative_to(ROOT).as_posix(),top_n=len(ROUTES),demo_source_generated=True)
    generated_source(source,base)
    write_json(out/'generation.json',{'kind':'entirely_generated_synthetic','seed':base['seed'],
        'source_sha256':sha256(source),'routes':ROUTES,'generator_sha256':sha256(__file__),
        'uses_private_orders':False,'business_results_claimed':False})
    write_json(out/'base.json',base)
    _,settings=load_settings()
    settings.update(version='public-ten-route-demo-v1',base_config=(out/'base.json').relative_to(ROOT).as_posix(),
        workers=1,training_window_days=365)
    settings['models']={k:v for k,v in settings['models'].items() if k in ['last7_mean','last28_mean','lgbm_ratio7']}
    settings['non_top10_models']=['last7_mean','last28_mean']
    settings['lightgbm'].update(trees=20,min_child_samples=20)
    write_json(out/'aggregate.json',settings)
    agg=prefix+'_aggregate';m3=prefix+'_m3'
    forecast(agg,out/'aggregate.json');check_forecast(agg)
    product(m3,agg);check_product(m3)
    write_json(out/'product30.json',{'version':'public-ten-route-demo-v1','aggregate_run':agg,'product_run':m3,
        'window_days':30,'customer_delivery_days':7,'port':8509,'source_generated_by_this_program':True})
    print('Ten-route generated demo complete and independently checked.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prefix',required=True)
    execute(parser.parse_args().prefix)
