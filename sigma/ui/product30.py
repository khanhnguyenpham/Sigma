"""Verified local M3 dashboard, organized as a mentor-facing walkthrough."""
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.common import ROOT, sha256
from sigma.jobs.product30 import settings
from sigma.inventory.product30 import validate_product
from sigma.ui.product30_support import evidence_stamps, ledger_timeline
from sigma.ui.product30_pages import render

st.set_page_config(page_title='SIGMA · M3',layout='wide',initial_sidebar_state='collapsed')
st.markdown('<style>'+Path(__file__).with_suffix('.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)


@st.cache_data(show_spinner='Đang kiểm tra nguồn và chuẩn bị dashboard…')
def load_bundle(run_id, summary_digest, stamps):
    folder=ROOT/'outputs'/run_id
    summary=validate_product(folder)
    parent=ROOT/'outputs'/summary['aggregate_run']
    verification={}
    for name in [run_id,summary['aggregate_run']]:
        receipt=ROOT/'outputs'/(name+'_verification.json')
        info=json.loads(receipt.read_text(encoding='utf-8'))
        if info.get('status')!='verified' or info['summary_sha256']!=sha256(ROOT/'outputs'/name/'summary.json'):
            raise ValueError('Biên bản đối soát không khớp bộ kết quả.')
        verification[name]=info
    return {'summary':summary,'verification':verification,
        'protocol':json.loads((folder/'protocol.json').read_text(encoding='utf-8')),
        'scenario_configs':json.loads((folder/'scenario_configs.json').read_text(encoding='utf-8')),
        'metrics':pd.read_csv(folder/'simulation_metrics.csv',float_precision='round_trip'),
        'recommendations':pd.read_csv(folder/'recommendations_latest.csv',float_precision='round_trip'),
        'item_forecast':pd.read_csv(folder/'item_forecast_latest.csv',parse_dates=['target_date'],float_precision='round_trip'),
        'alerts':pd.read_csv(folder/'alerts_14d.csv',parse_dates=['as_of_date','actual_depletion_date','predicted_depletion_date']),
        'delivery':pd.read_csv(folder/'delivery_projection.csv',parse_dates=['delivery_date']),
        'signals':pd.read_csv(folder/'business_signals.csv',parse_dates=['date']),
        'forecasts':pd.read_csv(parent/'daily_allocation.csv',parse_dates=['as_of_date','target_date'],float_precision='round_trip'),
        'top':pd.read_csv(parent/'top10_results.csv',float_precision='round_trip'),
        'daily':pd.read_csv(parent/'daily_sales.csv',parse_dates=['date'],float_precision='round_trip'),
        'selections':pd.read_csv(parent/'selected_models.csv',float_precision='round_trip'),
        'timeline':ledger_timeline(folder/'inventory_ledger.csv')}


try:
    config,cfg=settings(os.environ.get('SIGMA_M3_CONFIG','data/configs/product30-focus.json'))
    namespace=hashlib.sha256(config.relative_to(ROOT).as_posix().encode()).hexdigest()[:12]
    state_dir=ROOT/'outputs/jobs'/('m3_'+namespace)
    state=json.loads((state_dir/'state.json').read_text()) if (state_dir/'state.json').is_file() else {}
    run_id=state.get('last_good_run',cfg['product_run'])
    folder=ROOT/'outputs'/run_id
    bundle=load_bundle(run_id,sha256(folder/'summary.json'),evidence_stamps(ROOT,run_id,cfg['aggregate_run']))
    if bundle['summary']['aggregate_run']!=cfg['aggregate_run']:
        raise ValueError('Bộ tồn kho không khớp cấu hình dự báo.')
    if sha256(ROOT/bundle['protocol']['config']['source'])!=bundle['summary']['source_sha256']:
        raise ValueError('Nguồn đã đổi; cần dự báo và đối soát snapshot mới.')
except (OSError,ValueError,KeyError) as error:
    st.title('SIGMA · M3')
    st.error('Chưa thể mở bộ kết quả đã kiểm tra. '+str(error))
    st.info('Hoàn tất dự báo, mô phỏng và đối soát trước khi trình diễn. Xem docs/30day-m3.md để chuẩn bị bộ local hoặc demo tự sinh.')
    st.stop()

render(bundle,cfg,state_dir,run_id)
