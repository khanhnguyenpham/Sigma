"""A complete M3 demo on generated orders, independent of the private snapshot."""
import argparse
from pathlib import Path
import re

from src.common import ROOT, read_config, write_json
from src.reporting import generate_synthetic
from sigma.forecasting.aggregate import load_settings, execute as forecast
from sigma.verification.aggregate import execute as check_forecast
from sigma.inventory.product30 import execute as product
from sigma.verification.product30 import execute as check_product


def execute(prefix):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',prefix):raise ValueError('Invalid fresh demo prefix')
    folder=ROOT/'outputs'/(prefix+'_bundle');folder.mkdir(exist_ok=False)
    base=read_config('data/configs/config.original.json')
    source=folder/'synthetic_orders.csv'
    base.update(source=source.relative_to(ROOT).as_posix(),top_n=3,demo_source_generated=True)
    generate_synthetic(source,base,route_count=3)
    write_json(folder/'base.json',base)
    _,settings=load_settings()
    settings.update(version='generated-3-route-m3-demo-v1',base_config=(folder/'base.json').relative_to(ROOT).as_posix(),
                    workers=1,training_window_days=365)
    settings['models']={k:v for k,v in settings['models'].items() if k in ['last7_mean','last28_mean','lgbm_ratio7']}
    settings['non_top10_models']=['last7_mean','last28_mean']
    settings['lightgbm'].update(trees=20,min_child_samples=20)
    write_json(folder/'aggregate.json',settings)
    aggregate_run=prefix+'_aggregate';product_run=prefix+'_m3'
    forecast(aggregate_run,folder/'aggregate.json');check_forecast(aggregate_run)
    product(product_run,aggregate_run);check_product(product_run)
    config={'version':'generated-m3-demo-v1','aggregate_run':aggregate_run,'product_run':product_run,
        'window_days':30,'customer_delivery_days':7,'port':8508,'source_generated_by_this_program':True}
    write_json(folder/'product30.json',config)
    result={'status':'verified','kind':'generated_synthetic_m3_demo','routes':3,
        'config':(folder/'product30.json').relative_to(ROOT).as_posix(),
        'supplied_snapshot_read':False,'certifies_supplied_snapshot_accuracy':False}
    write_json(folder/'summary.json',result);print(result,flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prefix',required=True)
    a=p.parse_args();execute(a.prefix)
