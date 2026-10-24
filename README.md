# SIGMA — React / FastAPI local

Nhánh hiện hành: **`m3-implementation`**, nền `b1357cd`. CHG-068 đã cập nhật tài liệu và baseline, gỡ runtime/build/dependency Streamlit M3 và M2. React gọi HTTP `/api/v1`; FastAPI phục vụ bản build, PostgreSQL và worker chạy local.

**Theo yêu cầu ngày24/10/2026, dừng sau bước4 đã kiểm/commit/push/CI.** Bước5–15 chưa bắt đầu: BE/FE chưa refactor theo module/feature; chế độ SS/ROP và cảnh báo ngưỡng mới chưa triển khai. [Kế hoạch15bước](docs/planning/PLAN.md#chg-068) · [TASK](docs/planning/TASK.md).

## Cài và chạy

Dùng **Python3.12**, Node24 và PostgreSQL18. Trong PowerShell, `python` bên dưới phải trỏ Python3.12; kiểm phiên bản trước khi tạo môi trường. Git không kèm raw/DB/env/run hoặc bundle riêng tư. [Quy trình nguồn/forecast/mô phỏng](M3/IMPLEMENTATION.md) dùng dữ liệu local của nhóm.

```powershell
python --version
python -m venv .venv-m3
.\.venv-m3\Scripts\python.exe -m pip install -r M3/backend/requirements.txt
.\.venv-m3\Scripts\python.exe -m pip install --no-deps -e M3/backend
.\.venv-m3\Scripts\python.exe -m pip check
npm.cmd --prefix M3/frontend ci
npm.cmd --prefix M3/frontend run build
```

Tạo `M3/.env` từ `M3/configs/.env.example` nếu chưa có; điền PostgreSQL/source/output root local, không ghi đè env hiện có. Tests dùng riêng **`sigma_m3_test`**; tài khoản app không phải superuser.

```powershell
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -m alembic -c M3/backend/alembic.ini upgrade head
. ./M3/scripts/start_m3.ps1
# Dừng đúng API/worker do launcher này tạo:
. ./M3/scripts/stop_m3.ps1
```

Bản build ở `http://127.0.0.1:8000`, OpenAPI ở `http://127.0.0.1:8000/docs`. Dev React: `npm.cmd --prefix M3/frontend run dev`, proxy tới API8000. Xem [M3](M3/README.md), [implementation](M3/IMPLEMENTATION.md) và [nghiệm thu](M3/ACCEPTANCE.md).

## Kiểm tra

```powershell
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -B -m pytest tests M2/models/tests M3/backend/tests --tb=short
npm.cmd --prefix M3/frontend test
npm.cmd --prefix M3/frontend run build
.\.venv-m3\Scripts\python.exe -m pip check
.\.venv-m3\Scripts\python.exe -m M2.final_report --help
```

Integration chỉ dùng DB test riêng; CI chỉ dữ liệu giả. Log/credential/raw/ID đơn khách giữ private local. [Bằng chứng CHG-068](docs/review-log.md#e101) ghi từng bước; số kiểm lịch sử không thay kiểm mới.

## M2 và giới hạn

[M2 final](M2/README.md) giữ model, CLI fit/verify/export, [notebook](M2/notebooks/final_report.ipynb) và [HTML offline](M2/reports/final_m2_20261011/index.html). [Code map M2](M2_CODE_MAP.md) ghi cấu hình và giới hạn hồi cứu. Dashboard/launcher Streamlit đã gỡ.

R05 theo **M05 tổng30**; H14/L7/R1 phục vụ tồn. Không đổi model/target/split hoặc chọn lại bằng test. Thiếu bundle tổng30 đã kiểm thì giữ `monthly_not_prepared`; không lấy số trong Markdown thay dữ liệu. Tồn/nhập/supplier có nhãn mô phỏng; A08–A17 không tự thành mentor xác nhận, R07/T14 chưa nghiệm thu.

[README cũ](docs/history/README-before-streamlit-removal.md) và [Streamlit lịch sử](docs/history/m3-streamlit.md) chỉ mô tả phiên bản trước. Không thay đổi/xóa website online, deploy, merge hoặc force-push trong lượt này.
