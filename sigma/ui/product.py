"""One local product entry point for forecasting, inventory and customer delivery."""
import json
import os

import pandas as pd
import streamlit as st

from src.common import ROOT, validate_run
from sigma.verification.weekly import validate_weekly
from sigma.delivery.customer import validate_delivery, delivery_settings
from sigma.inventory.policy import validate_policy


def overview():
    st.title('SIGMA · Dự báo bán, tồn kho và lịch giao')
    bundle = delivery_settings()
    source_label = 'Dữ liệu demo được phần mềm sinh' if bundle['source_description'] == 'generated_synthetic_demo' else 'Nguồn do người dùng mô tả là giả định'
    st.caption('Sản phẩm chạy local · Dữ liệu và đầu ra giữ tại máy · ' + source_label)
    st.success('Quy tắc đã chốt: khách đặt ngày D, lịch giao ngày D+7, không trễ giao, kể cả cuối tuần.')
    st.write('Dùng menu để xem dự báo tổng 7 ngày, lịch giao từ đơn đã đặt, tồn kho và cảnh báo. Thời gian giao cho khách được tính riêng với thời gian nhập hàng về kho.')
    rows = []
    weekly, delivery, policy = None, None, None
    for p in (ROOT / 'outputs').glob('*'):
        if not (p / 'summary.json').is_file():
            continue
        try:
            summary = json.loads((p / 'summary.json').read_text(encoding='utf-8'))
            if summary.get('kind') == 'weekly_quantity_run':
                validate_weekly(p)
                if p.name == bundle['weekly_run']:
                    weekly = (p, summary)
            elif summary.get('kind') == 'fixed_customer_delivery_run':
                validate_delivery(p)
                if (summary.get('weekly_run') != bundle['weekly_run']
                        or summary.get('daily_run') != bundle['daily_run']):
                    continue
                delivery = (p, summary) if delivery is None or summary['created_at_utc'] > delivery[1]['created_at_utc'] else delivery
            elif summary.get('kind') == 'weekly_continuous_inventory_run':
                validate_policy(p)
                if (summary.get('weekly_run') == bundle['weekly_run']
                        and summary.get('daily_run') == bundle['daily_run']):
                    if policy is None or p.stat().st_mtime_ns > policy[0].stat().st_mtime_ns:
                        policy = (p, summary)
        except (OSError, ValueError, KeyError):
            continue
    if delivery:
        rows.append({'Phần sản phẩm': 'Lịch giao khách D+7', 'Bằng chứng': delivery[0].name,
            'Kết quả': 'Đã triển khai; 0 ngày trễ theo giả định, actual giao chưa được cung cấp'})
        rows.append({'Phần sản phẩm': 'Phân biệt lịch đã biết / lượng dự báo', 'Bằng chứng': delivery[0].name,
            'Kết quả': f"{delivery[1]['known_next7_commitment_qty']} đơn vị đã đặt giao tuần tới; phần từ đơn mới dùng mô hình"})
    if weekly:
        n_routes = len(pd.read_csv(weekly[0] / 'top_routes.csv'))
        rows.append({'Phần sản phẩm': 'MAPE tổng bán 7 ngày, top 10', 'Bằng chứng': weekly[0].name,
            'Kết quả': f"Test hồi cứu {weekly[1]['top10_test_weekly_passed']}/{n_routes} ≤20%; chưa thay nghiệm thu theo ngày"})
    if policy:
        rows.append({'Phần sản phẩm': 'Nhập kho liên tục từ dự báo tuần', 'Bằng chứng': policy[0].name,
            'Kết quả': f"{policy[1]['scenarios']} kịch bản; tỷ lệ đáp ứng cơ sở {policy[1]['base_fill_rate']:.2%}, có thiếu hàng mô phỏng"})
        rows.append({'Phần sản phẩm': 'Cảnh báo từ dự báo tuần trước ≥7 ngày', 'Bằng chứng': policy[0].name,
            'Kết quả': f"{policy[1]['early_event_rate']:.2%} sự kiện replay; giữ các ca cạn trước ngày 7 trong mẫu số"})
    daily_folder = ROOT / 'outputs' / bundle['daily_run']
    try:
        validate_run(daily_folder)
        acceptance = pd.read_csv(daily_folder / 'accuracy_acceptance.csv')
        passed = int(acceptance.accuracy_passed.eq(True).sum())
        rows.append({'Phần sản phẩm': 'MAPE theo ngày R05', 'Bằng chứng': bundle['daily_run'],
            'Kết quả': f'{passed}/{len(acceptance)} đạt; ngày và tuần được chấm riêng'})
        simulation = pd.read_csv(daily_folder / 'simulation_metrics.csv')
        replay = simulation.loc[simulation.evaluation.eq('independent_no_new_order_alert_replay')]
        early = float(replay.early_event_rate.iloc[0]) if len(replay) else float('nan')
        rows.append({'Phần sản phẩm': 'Cảnh báo từ dự báo ngày trước ≥7 ngày', 'Bằng chứng': bundle['daily_run'],
            'Kết quả': f'{early:.2%} sự kiện replay; lịch D+7 không tự xác nhận cảnh báo đạt'})
    except (OSError, ValueError, KeyError):
        st.warning('Run tồn/ngày thiếu hoặc đã thay đổi; hãy kiểm tra trước khi dùng số liệu.')
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption('Kết quả dùng snapshot 2024–2025 và đánh giá hồi cứu. Trang không tự huấn luyện, gửi dữ liệu hoặc đổi mô hình khi mở.')


st.set_page_config(page_title='SIGMA · Sản phẩm', page_icon='📈', layout='wide')
bundle = delivery_settings()
os.environ['SIGMA_WEEKLY_RUN_ID'] = bundle['weekly_run']
os.environ['SIGMA_RUN_ID'] = bundle['daily_run']
page = st.navigation([
    st.Page(overview, title='Tổng quan', icon='🏠', default=True),
    st.Page('sigma/ui/weekly.py', title='Dự báo tổng 7 ngày', icon='📊'),
    st.Page('sigma/ui/delivery.py', title='Giao khách D+7', icon='📦'),
    st.Page('sigma/ui/inventory.py', title='Tồn từ dự báo tuần', icon='📋'),
    st.Page('sigma/ui/comparison.py', title='So sánh ngày và tuần', icon='⚖️'),
    st.Page('app.py', title='Tồn, cảnh báo và dự báo ngày', icon='📈'),
], position='sidebar')
page.run()
