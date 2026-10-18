"""Provider-independent Python entrypoint for a reviewed SIGMA result release."""
import os
from pathlib import Path

import streamlit as st

from sigma.deployment.runtime import load,digest
from sigma.ui.product30_pages import render


@st.cache_data(show_spinner='Đang kiểm tra bộ kết quả SIGMA…')
def checked(folder,manifest_digest):
    return load(folder,manifest_digest)


def main():
    st.set_page_config(page_title='SIGMA · Điều phối nhu cầu & tồn kho',layout='wide',initial_sidebar_state='collapsed')
    root=Path(__file__).resolve().parents[2]
    folder=Path(os.environ.get('SIGMA_RELEASE_DIR',str(root/'release'))).resolve()
    try:
        # Validate on every rerun before using the cache, including individual file hashes.
        bundle=load(folder,os.environ.get('SIGMA_RELEASE_SHA256'))
        bundle=checked(str(folder),digest(folder/'manifest.json'))
    except (OSError,ValueError,KeyError):
        st.error('Chưa thể mở bộ kết quả đã kiểm tra. Kiểm tra release/manifest và các bảng đi kèm.')
        st.stop()
    st.markdown('<style>'+(root/'sigma/ui/product30.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)
    st.caption('Nguồn bài đã được xử lý · tồn kho/nhập hàng là mô phỏng · không gửi đơn nhập thật')
    bundle['hosted_release']=True
    render(bundle,{'window_days':30,'customer_delivery_days':7},folder/'job_state',bundle['summary']['run_id'])
