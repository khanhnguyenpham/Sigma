"""Give actionable product errors without falling back to a different run."""
import streamlit as st

from sigma.product_catalog import candidate_folders
from sigma.delivery.customer import delivery_settings


def settings_for_ui():
    try:
        return delivery_settings()
    except (OSError, ValueError, KeyError, TypeError):
        st.error('Không mở được cấu hình sản phẩm. Chọn file delivery.json hợp lệ trong project; giao khách phải là D+7 và không thay lead time nhập kho.')
        st.stop()


def folders_for(bundle, role):
    try:
        return candidate_folders(bundle, role)
    except (OSError, ValueError, KeyError):
        st.error('Bộ demo đã khóa bị thiếu hoặc thay đổi ở phần ' + role + '. Chạy lại release-check với bộ run đã đối soát; không dùng run khác thay thế.')
        st.stop()
