# SIGMA — React / FastAPI local

**Cấu trúc hiện hành CHG-071:** code BE nằm thẳng trong `web/backend/src/` với main.py, worker.py, cli.py và api/core/modules/services; không còn thư mục sigma_m3. Worker dùng cùng nghiệp vụ; các launcher đã gom về `web/backend/scripts/`. Chạy từ root repo: API `python -m uvicorn main:create_app --factory`, worker `python -m worker`, CLI `python -m cli`. FE/configs/research/env vẫn ở M3, tên DB/env không đổi; M2 giữ package src riêng ở root.

**Cấu trúc hiện hành CHG-070:** backend, migration, tests và entry point worker/CLI ở `web/backend/`; FE còn ở `M3/frontend/`, cấu hình và launcher ở `M3/configs/`, `web/backend/scripts/`. Đích tiếp theo là gom FE vào `web/frontend/` khi được giao. Worker dùng chung package, không có worker service riêng. [Tài liệu cũ đã bỏ và cách tra lịch sử](docs/review-log.md#removed-docs-chg070).

**FE dự kiến CHG-069:** bước8–9 sẽ tổ chức theo pages/layouts/components và config/hooks/services/types/utils, cùng App.tsx/main.tsx/index.css. [Cấu trúc và cách chuyển mã](M3/docs/04-frontend-spec.md#frontend-target-chg069). Hiện chỉ cập nhật tài liệu, chưa đổi code FE; bước6–15 chưa bắt đầu.

Nhánh hiện hành: **`m3-implementation`**, nền `b1357cd`. CHG-068 đã cập nhật tài liệu và baseline, gỡ runtime/build/dependency Streamlit M3 và M2. React gọi HTTP `/api/v1`; FastAPI phục vụ bản build, PostgreSQL và worker chạy local.

**Lượt mới24/10/2026:** người dùng giao riêng bước5: nền BE đã tách `core/`, `modules/catalog/`, `modules/configuration/`; API/schema/phép tính giữ nguyên, commitdb6c1d5 đã push/remoteSHA khớp/CI đạt. Bước6–15 chưa bắt đầu; FE và mode SS/ROP/cảnh báo mới thuộc các bước sau. [Kế hoạch15bước](docs/planning/PLAN.md#chg-068) · [Bàn giao bước5](docs/development.md#handoff-chg068-step5).

## Cài và chạy

Dùng **Python3.12**, Node24 và PostgreSQL18. Trong PowerShell, `python` bên dưới phải trỏ Python3.12; kiểm phiên bản trước khi tạo môi trường. Git không kèm raw/DB/env/run hoặc bundle riêng tư. [Quy trình nguồn/forecast/mô phỏng](M3/IMPLEMENTATION.md) dùng dữ liệu local của nhóm.

```powershell
python --version
python -m venv .venv-m3
.\.venv-m3\Scripts\python.exe -m pip install -r web/backend/requirements.txt
.\.venv-m3\Scripts\python.exe -m pip install --no-deps -e web/backend
.\.venv-m3\Scripts\python.exe -m pip check
npm.cmd --prefix M3/frontend ci
npm.cmd --prefix M3/frontend run build
```

Tạo `M3/.env` từ `M3/configs/.env.example` nếu chưa có; điền PostgreSQL/source/output root local, không ghi đè env hiện có. Tests dùng riêng **`sigma_m3_test`**; tài khoản app không phải superuser.

```powershell
. ./web/backend/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -m alembic -c web/backend/alembic.ini upgrade head
. ./web/backend/scripts/start_m3.ps1
# Dừng đúng API/worker do launcher này tạo:
. ./web/backend/scripts/stop_m3.ps1
```

Bản build ở `http://127.0.0.1:8000`, OpenAPI ở `http://127.0.0.1:8000/docs`. Dev React: `npm.cmd --prefix M3/frontend run dev`, proxy tới API8000. Xem [M3](M3/README.md), [implementation](M3/IMPLEMENTATION.md) và [nghiệm thu](M3/ACCEPTANCE.md).

## Kiểm tra

```powershell
. ./web/backend/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -B -m pytest tests M2/models/tests web/backend/tests --tb=short
npm.cmd --prefix M3/frontend test
npm.cmd --prefix M3/frontend run build
.\.venv-m3\Scripts\python.exe -m pip check
.\.venv-m3\Scripts\python.exe -m M2.final_report --help
```

Integration chỉ dùng DB test riêng; CI chỉ dữ liệu giả. Log/credential/raw/ID đơn khách giữ private local. [Bằng chứng CHG-068](docs/review-log.md#e101) ghi từng bước; số kiểm lịch sử không thay kiểm mới.

## M2 và giới hạn

[M2 final](M2/README.md) giữ model, CLI fit/verify/export, [notebook](M2/notebooks/final_report.ipynb) và [HTML offline](M2/reports/final_m2_20261011/index.html). [Hướng dẫn M2](M2/README.md) ghi cấu hình và giới hạn hồi cứu. Dashboard/launcher Streamlit đã gỡ.

R05 theo **M05 tổng30**; H14/L7/R1 phục vụ tồn. Không đổi model/target/split hoặc chọn lại bằng test. Thiếu bundle tổng30 đã kiểm thì giữ `monthly_not_prepared`; không lấy số trong Markdown thay dữ liệu. Tồn/nhập/supplier có nhãn mô phỏng; A08–A17 không tự thành mentor xác nhận, R07/T14 chưa nghiệm thu.

Các bản sao README, hướng dẫn Streamlit và demo cũ đã bỏ; [tra cứu lịch sử Git](docs/review-log.md#removed-docs-chg070).
