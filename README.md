# SIGMA — React / FastAPI local

## Xem tồn kho theo kho — CHG-080

Mở **Tồn kho → chọn thẻ thành phố → xem sản phẩm**. Tên kho chỉ là city; quốc gia/carrier ở thông tin riêng. Trong kho có lọc nhà mạng/loại/SKU và nút mở Nhập hàng/Dự báo cùng phạm vi. [Chi tiết và kiểm tra](docs/development.md#handoff-chg080).


## Cập nhật lượng nhập mỗi lần ngày 29 tháng 10

Ứng dụng mới dùng một lượng nhập cố định theo mặt hàng thay công thức lượng biến đổi theo MOQ. Cấu hình “Lượng nhập mỗi lần” trong policy hiện có; kịch bản không thay lượng này. Khi cần bổ sung Q bằng đúng lượng cấu hình, ETA7ngày; nếu hàng đang về đã đủ mức S thì Q=0. Không có module quản lý hợp đồng mới.

Máy thành viên sau khi kéo mã phải nâng schema trước khi chạy API:

```powershell
. web/backend/scripts/load_env.ps1
.venv-m3/Scripts/python.exe -B -m alembic -c web/backend/alembic.ini upgrade head
```

Policy/run lịch sử vẫn giữ MOQ. Cần cấu hình lượng mỗi lần cho policy dùng bởi run mới; không tự chuyển MOQ thành số hợp đồng. Kết quả33%/49% nghiên cứu trước đó thuộc policy cũ, chưa chứng minh hiệu quả policy mới. Không refit hoặc tích hợp S25 trong thay đổi này.

**CHG-068 bước 15 — 27/10/2026, hoàn tất:** đã chạy hai replay thật mới với cấu hình cơ sở khóa trước kết quả; worker và verifier độc lập đạt. Policy fill 90,4121%, thiếu 1.531/15.968; depletion báo sớm 986/2.867 = **34,391350%, chưa đạt mục tiêu làm việc 45%**. Metric xuống ROP giữ riêng (TP101/FP89/FN0/TN619). 245 Python, 50 React, build/pip check, API/CSV/browser đạt; 1.038 hash protected, 140 artifact sealed và hàng cũ của 13 bảng nghiệp vụ + Alembic nguyên. Schema 0003_threshold/0diff; chỉ thêm hai run local, không refit/tuning. R07/T14 chưa nghiệm thu. Commit `2658b8116accbed4354fdc18b55d7ed52f436f7c` đã push thường, remoteSHA khớp và2workflowCI completed/success. [Bằng chứng và cách kiểm lại](docs/development.md#handoff-chg068-step15). Các checkpoint bên dưới giữ vai trò lịch sử.

**CHG-068 bước14 — 26/10/2026, hoàn tất:** sau cổng13 mã73d6f39/remoteSHA/2CI success, người dùng giao14. React hiển thị ROP/SS/mode/N, ngày xuống ROP riêng ngày cạn, lý do/đường projection/bảng UTC; filter/export và metric threshold riêng depletion. Workspace thêm warning_items/projected_below_rop_items đếm item duy nhất; inventory API/CSV đọc5tham số từ policy frozen, công thức fixed hiển thị đúng.245Python (3ca mới),50React (7ca mới,1worker)/build/pipcheck và browser desktop/mobile390px trên2run synthetic đạt;1027protectedhash và3app run nguyên, schema0003_threshold giữ. Commit mã37c4525b90cb361d8eeabc23c46cfc82fb39f8dc đã push thường, remoteSHA khớp và2workflowCI completed/success; bước15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật mới chứng minh45%.

**CHG-068 bước13 — 26/10/2026, hoàn tất:** sau cổng bước12 mã14b1841/remoteSHA/2CI success, người dùng giao tiếp tục bước13. Form React policy/scenario có SS days/volatility, ROP fixed/forecast, lookback/factor/N; override trống kế thừa,0giữ đúng, chỉ trường phù hợp mode hiển thị/gửi. Giữ version/effective date/conflict/cấu hình cũ; bảng policy phân biệt tham số đang áp dụng.43React (9ca mới, chạy mặc định và1worker)/build/browser synthetic save-reload-Escape-focus đạt;1029protectedhash và3app run nguyên, schema0003_threshold giữ. 242Python BE/M2/pipcheck đạt; commit mã73d6f398de4fb069ab2484a85cecf71bc345147c đã push thường, remoteSHA khớp và2workflowCI completed/success; bước14–15 chưa bắt đầu, R07/T14 chưa nghiệm thu.

**CHG-068 bước12 — 26/10/2026, hoàn tất:** cảnh báo projected_below_rop/threshold_warning với predicted_threshold_date đã qua hàm thuần/simulation/worker, DTO/filter/CSV và verifier độc lập. Giữ ROP tại decision origin, chỉ receipts đã biết trước Q mới, strict < trong N ngày; metric threshold riêng depletion.242Python BE/M2 (28ca mới),34React chạy1worker/build/pipcheck/API-worker smoke đạt;9inventory golden/M2 parity và1024protectedhash nguyên. DB app đã backup/nâng0003_threshold, hash mọi cột cũ13bảng/3run nguyên, schema0diff. Commit mã14b18415014ee2867fac436e6bd7530d74b12188 đã push thường, remoteSHA khớp và2workflowCI completed/success; bước13–15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật chứng minh45%.

**Tính policy bước11 CHG-068 — 25/10/2026:** inventory/service có2mode SS và2mode ROP, simulation chọn lịch sử causal theo decision origin, independent verifier tự đối soát từng dòng. Mode đã lưu từ bước10 nay chạy được, không guard tạm; API/schema13bảng/FE/default legacy giữ, cấu trúc web của CHG-072 giữ. [Công thức và ví dụ](M3/docs/01-functional-spec.md#configurable-calculation-step11), [kiểm và bàn giao](docs/development.md#handoff-chg068-step11). Bước12–15 chưa bắt đầu; các trạng thái trước bước11 bên dưới là checkpoint lịch sử.

**Hiện hành CHG-072 — 25/10/2026:** frontend ở web/frontend, configs/research code/env ở web/backend; M3 chỉ giữ Markdown và protocol nghiên cứu. Backend serve/build/launcher/CI đã đổi đường; tên env/DB, FE/nghiệp vụ/API/13bảng/snapshot giữ nguyên. [Cây thực](M3/docs/05-source-architecture.md#web-layout-chg072), [bàn giao](docs/development.md#handoff-chg072). Bước11–15 chưa bắt đầu; các mốc đường M3/frontend/configs/research/env dưới đây là lịch sử trước chuyển vị trí, các lệnh chạy đã cập nhật.

**Policy persistence bước10 CHG-068 — 25/10/2026:** backend lưu mode SS/ROP, lookback/factor và horizon cảnh báo vào policy version/scenario override/run mới; Alembic0002_policy vẫn13bảng. Đã backup/migrate DB local, giữ toàn bộ cột cũ và snapshot/hash. Mode fixed/volatility chưa chạy công thức mới trước bước11; UI vẫn bước9. [Trường và migration](M3/docs/02-data-model.md#policy-persistence-step10), [kiểm và bàn giao](docs/development.md#handoff-chg068-step10). Bước11–15 chưa bắt đầu.

**Frontend sau bước9 CHG-068 — 25/10/2026:** FE vẫn M3/frontend; App ghép6pages với AppLayout/Sidebar/Header/ContextFilters, state/effect ở useAppContext. useConfiguration giữ ghi cấu hình; form policy/scenario và3drawer tách component. index.css giữ byte của styles.css, import tại main. Không dependency/nghiệp vụ mới. [Cây thực](M3/docs/04-frontend-spec.md#step9-actual), [kiểm và bàn giao](docs/development.md#handoff-chg068-step9). Backend/dữ liệu không đổi; bước10–15 chưa bắt đầu.

**Hiện hành CHG-068 bước7 — 25/10/2026:** BE tại `web/backend/src/` gồm main.py, worker.py, cli.py, models.py, core và8module catalog/configuration/forecasting/inventory/purchasing/alerts/runs/reporting. Source api/services cũ đã chuyển hết vào module, models.py chỉ giữ registry13model chung Base. API/DDL/phép tính và dữ liệu/snapshot giữ nguyên; [cây thực](M3/docs/05-source-architecture.md#step7-actual), [bàn giao](docs/development.md#handoff-chg068-step7). Launcher ở `web/backend/scripts/`; chạy API `python -m uvicorn main:create_app --factory`, worker `python -m worker`, CLI `python -m cli`. FE/configs/research/env vẫn M3, M2 giữ package src riêng ở root.

**Checkpoint CHG-070:** backend, migration, tests và entry point worker/CLI ở `web/backend/`; FE còn ở `M3/frontend/`, cấu hình và launcher ở `M3/configs/`, `web/backend/scripts/`. Đích tiếp theo là gom FE vào `web/frontend/` khi được giao. Worker dùng chung package, không có worker service riêng. [Tài liệu cũ đã bỏ và cách tra lịch sử](docs/review-log.md#removed-docs-chg070).

**Đích FE CHG-069:** bước8–9 đã tổ chức pages/layouts/components và config/hooks/services/types/utils. [Trách nhiệm các tầng](M3/docs/04-frontend-spec.md#frontend-target-chg069). Bước10–15 và mode SS/ROP/cảnh báo cấu hình mới chưa triển khai.

Nhánh hiện hành: **`m3-implementation`**, nền `b1357cd`. CHG-068 đã cập nhật tài liệu và baseline, gỡ runtime/build/dependency Streamlit M3 và M2. React gọi HTTP `/api/v1`; FastAPI phục vụ bản build, PostgreSQL và worker chạy local.

**Checkpoint bước5 ngày24/10/2026:** nền BE tách core/catalog/configuration, commitdb6c1d5 đã push/remoteSHA khớp/CI đạt. Bước6–7 đã triển khai tiếp sau checkpoint này; FE và mode SS/ROP/cảnh báo cấu hình mới thuộc các bước sau. [Kế hoạch15bước](docs/planning/PLAN.md#chg-068) · [Bàn giao bước5](docs/development.md#handoff-chg068-step5).

## Cài và chạy

Dùng **Python3.12**, Node24 và PostgreSQL18. Trong PowerShell, `python` bên dưới phải trỏ Python3.12; kiểm phiên bản trước khi tạo môi trường. Git không kèm raw/DB/env/run hoặc bundle riêng tư. [Quy trình nguồn/forecast/mô phỏng](M3/IMPLEMENTATION.md) dùng dữ liệu local của nhóm.

```powershell
python --version
python -m venv .venv-m3
.\.venv-m3\Scripts\python.exe -m pip install -r web/backend/requirements.txt
.\.venv-m3\Scripts\python.exe -m pip install --no-deps -e web/backend
.\.venv-m3\Scripts\python.exe -m pip check
npm.cmd --prefix web/frontend ci
npm.cmd --prefix web/frontend run build
```

Tạo `web/backend/.env` từ `web/backend/configs/.env.example` nếu chưa có; điền PostgreSQL/source/output root local, không ghi đè env hiện có. Tests dùng riêng **`sigma_m3_test`**; tài khoản app không phải superuser.

```powershell
. ./web/backend/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -m alembic -c web/backend/alembic.ini upgrade head
. ./web/backend/scripts/start_m3.ps1
# Dừng đúng API/worker do launcher này tạo:
. ./web/backend/scripts/stop_m3.ps1
```

Bản build ở `http://127.0.0.1:8000`, OpenAPI ở `http://127.0.0.1:8000/docs`. Dev React: `npm.cmd --prefix web/frontend run dev`, proxy tới API8000. Xem [M3](M3/README.md), [implementation](M3/IMPLEMENTATION.md) và [nghiệm thu](M3/ACCEPTANCE.md).

## Kiểm tra

```powershell
. ./web/backend/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -B -m pytest tests M2/models/tests web/backend/tests --tb=short
npm.cmd --prefix web/frontend test
npm.cmd --prefix web/frontend run build
.\.venv-m3\Scripts\python.exe -m pip check
.\.venv-m3\Scripts\python.exe -m M2.final_report --help
```

Integration chỉ dùng DB test riêng; CI chỉ dữ liệu giả. Log/credential/raw/ID đơn khách giữ private local. [Bằng chứng CHG-068](docs/review-log.md#e101) ghi từng bước; số kiểm lịch sử không thay kiểm mới.

## M2 và giới hạn

[M2 final](M2/README.md) giữ model, CLI fit/verify/export, [notebook](M2/notebooks/final_report.ipynb) và [HTML offline](M2/reports/final_m2_20261011/index.html). [Hướng dẫn M2](M2/README.md) ghi cấu hình và giới hạn hồi cứu. Dashboard/launcher Streamlit đã gỡ.

R05 theo **M05 tổng30**; H14/L7/R1 phục vụ tồn. Không đổi model/target/split hoặc chọn lại bằng test. Thiếu bundle tổng30 đã kiểm thì giữ `monthly_not_prepared`; không lấy số trong Markdown thay dữ liệu. Nhà cung cấp chính là carrier theo [CHG-079](M3/docs/02-data-model.md#supplier-carrier-chg079); tồn/nhập có nhãn mô phỏng; A08–A17 không tự thành mentor xác nhận, R07/T14 chưa nghiệm thu.

Các bản sao README, hướng dẫn Streamlit và demo cũ đã bỏ; [tra cứu lịch sử Git](docs/review-log.md#removed-docs-chg070).
