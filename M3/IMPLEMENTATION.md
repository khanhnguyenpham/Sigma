# M3 — ứng dụng đã triển khai và cách chạy

Ngày kiểm: 19/10/2026. Nhánh: `codex/m3-implementation`, nền `M3-design-plan` tại `20a3c45`. Phạm vi là **ứng dụng local FastAPI + React/TypeScript + PostgreSQL18**, 46 kho giả định, 920 mặt hàng, L7/R1/H14. Đây là implementation mới, riêng với Streamlit/tổng30 của nhánh khác. Không cần thay M2 final để chạy M3.

## Phần mềm và kết quả nghiên cứu

| Thành phần | Bằng chứng trực tiếp |
|---|---|
| Nguồn | Import100.000 dòng, quantity118.296, 46 tuyến, 920 item, 672.520 item-day. Raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. |
| Database | PostgreSQL18.6, app role không superuser, migration0001 tạo đúng13 bảng nghiệp vụ; Alembic check không drift. |
| Forecast | Chạy validation/khóa/test/future thật:185 origin,17.020 tổng tuần,2.382.800 item-day forecast. Mỗi origin đủ46 tuyến ×2 khối. |
| M2 final10 | Pooled LightGBM chỉ top10; Prophet riêng au(KDDI); LG U+ giữ override.40 nhóm metric test khớp báo cáo đã khóa trong1e-8. Không có bundle per-origin lịch sử ở checkout này nên **không tuyên bố đã so từng dòng với bundle cũ**. |
| Mở rộng36 | 5 LightGBM gốc học pooled46, Prophet riêng từng tuyến; chọn bằng validation đủ coverage, MAPE→MAE→ID.36 lựa chọn và1.799 dòng fit log kiểm lại; không dùng test chọn lại. |
| Phân bổ | Tính độc lập17.020 nhóm bảo toàn tổng,2.382.800 dòng weekday90/share30→90 và eligibility first_seen≤origin; đạt. |
| Policy replay cơ sở | 01/10–31/12/2025;85.560 ledger,16.423 sự kiện,3.245 lô; fill90,4121%, thiếu1.531/15.968 quantity. Receipt trước bán, ETA D+7, không âm, bán=đáp ứng+thiếu. |
| Alert replay cơ sở | 6 cửa sổ14 ngày không chồng, không đặt mới;82.800 ledger. TP2098/FP852/FN769/TN702; loại1099 ca đã cạn tại origin; early986/2867=34,3913%;8 ngày cuối ngoài cửa sổ đủ nhãn. |
| Snapshot | 31/10 và31/12 có920 dòng khởi tạo; không thêm actual tương lai vào ledger. Projection14 ngày dùng forecast và lô đã biết. |
| API/React | Sáu màn hình, bộ lọc/URL, bảng/biểu đồ, giải thích ROP/IP/MOQ, config có version, tạo job nền, tải CSV cùng context. API/CLI dùng cùng services. |
| Kiểm phần mềm |E91:86 ca Python:54 M3 +32 M2;9 ca Vitest/RTL và production build đạt. Nền E90 đã kiểm npm ci/pip check/Alembic check. Kết quả chi tiết private trong outputs, không đưa source orders vào CI. |

| Metric test, daily origins | Số tuyến MAPE≤20% | MAPE trung bình tuyến | Coverage |
|---|---:|---:|---:|
| Tổng7 H1–7, fixed10 |10/10|15,745366%|100%|
| Tổng7 H8–14, fixed10 |8/10|16,600553%|100%|
| Tổng7 H1–7, new36 |2/36|35,400179%|100%|
| Tổng7 H8–14, new36 |2/36|35,521325%|100%|
| Tổng7 H1–7, all46 |12/46|31,127393%|100%|
| Ngày **phân bổ từ tổng tuần**, fixed10 H1–7 |0/10|51,919555%|100%|

Không nhầm ngày phân bổ M3 với mô hình trực tiếp từng ngày trong thử nghiệm M2 cũ. MAPE chỉ actual dương; có MAE/WAPE/bias/counts/coverage ở API. Kết quả tuần không thay R05 ngày. M2 test hồi cứu, LG U+ đã chọn sau test-sweep; đây không là holdout độc lập. **R05/R07/T14 còn mở**, không nhận bảo đảm điểm hoặc mọi sự kiện đều báo sớm. Tồn, receipt, supplier/city/policy đều giả định; A08 là đề xuất success/orderUTC, không là kế toán đã xác nhận.

## Độ nhạy đã chạy

Cùng nguồn/forecast/L7, đổi một trục, không dùng để chọn lại model hoặc che lỗi:

| Kịch bản | Fill policy replay | Thiếu quantity | Tồn cuối trung bình/item-day | Số lô | Early alert replay |
|---|---:|---:|---:|---:|---:|
| Cover7, safety1 (cơ sở) |90,4121%|1.531|5,3836|3.245|34,3913%|
| Cover3, safety1 |89,4790%|1.680|5,3141|3.278|25,9549%|
| Cover14, safety1 |90,5686%|1.506|5,2487|3.114|17,6083%|
| Cover7, safety0,5 |89,1971%|1.725|5,2710|3.168|34,3913%|
| Cover7, safety1,5 |91,5018%|1.357|5,5357|3.317|34,3913%|

Đủ10 run cho5 kịch bản ×2 loại replay, tất cả complete/đối soát. Alert replay không đặt mới nên đổi safety không đổi đường tồn/projection cạn; thay đổi chỉ ảnh hưởng tín hiệu dướiROP. Đổi cover thay mẫu sự kiện tương lai, không được so early như cùng mẫu số. Tăng safety giảm shortage trong policy replay nhưng tăng tồn/lô, không là bảo đảm hết hàng bằng0.

Fresh future run `d57975c8-3d14-40a2-bee6-b3b8e20575ad` qua mã worker cuối:46tuyến/92tuần/12.880itemforecast,43fitlog,actual sau31/12 null; giữ nguyên selectionSHA từ replay. Source reuse run `6db3901f-b6f5-4ee9-a2e3-129d3407ba55` giữ tổng daily672.520 dòng, không nhân đôi nguồn. Manifest của hai run mới có full config/runtime/seed. Warning Prophet thiếu plotly chỉ liên quan plot tùy chọn; chart ứng dụng dùng React, fit/verification không phụ thuộc plotly.

## Cây mã để thành viên đọc

| Đường dẫn | Trách nhiệm |
|---|---|
| `backend/src/sigma_m3/models.py`, `backend/migrations/` |13 bảng, FK/unique/check/index và migration. |
| `settings.py`, `schemas.py`, `errors.py` |Env local, DTO strict, lỗi không echo dữ liệu nhạy cảm. |
| `services/ingestion.py`, `seeding.py`, `catalog.py` |Audit nguồn, hash-dedup, danh mục và giả định có version. |
| `services/m2_adapter.py`, `forecast.py`, `allocation.py` |Tái dùng M2, validation/selection/forecast46 và phân bổ causal. |
| `services/context.py`, `inventory.py`, `simulation.py`, `alerts.py`, `receipts.py` |Snapshot policy, sổ giao dịch/ngày, lượng nhập, ETA và hai replay riêng. |
| `services/runs.py`, `worker.py`, `cli.py` |Parent DAG/config hash, idempotency, queue một worker, heartbeat30s, verify trước complete. |
| `services/verification.py` |Tính lại allocation/actual/threshold/event/receipt/mẫu số cảnh báo; receipt kiểm ngoài run đã khóa. |
| `main.py`, `api/results.py` |Catalog/config/run/status/summary/result/metric/export và serve React đã build. |
| `frontend/src/api/`, `components/`, `pages/` |Client typed, hủy response cũ, sáu trang; hai trang chart được lazy load. |
| `backend/tests/`, `frontend/tests/`, `.github/workflows/m3.yml` ở root |Fixture giả PostgreSQL, unit/integration, RTL và CI. |

## Cài trên máy thành viên

Clone đúng nhánh; không cần merge main để đọc/chạy:

```powershell
git clone --branch codex/m3-implementation https://github.com/khanhnguyenpham/Sigma.git
cd Sigma
py -3.12 -m venv .venv-m3
.\.venv-m3\Scripts\python.exe -m pip install -r M3/backend/requirements.txt
.\.venv-m3\Scripts\python.exe -m pip install --no-deps -e M3/backend
Copy-Item M3/configs/.env.example M3/.env
```

Cần PostgreSQL18 và Node24/npm11. Tạo app role **không superuser**, hai database riêng `sigma_m3`/`sigma_m3_test` do role đó sở hữu. Dùng tài khoản quản trị PostgreSQL của máy để thực hiện; ví dụ trong psql:

```sql
CREATE ROLE sigma_m3_app LOGIN;
\password sigma_m3_app
CREATE DATABASE sigma_m3 OWNER sigma_m3_app;
CREATE DATABASE sigma_m3_test OWNER sigma_m3_app;
```

Điền mật khẩu/port/local paths trong `M3/.env`, không commit. `M3_SOURCE_ROOT` trỏ workspace đang giữ nguyên CSV tại `data/sigma_sim_data_orders.csv`; raw không nằm trong Git, thành viên dùng nguồn bài nhóm đã có. Không cần gửi lại dữ liệu doanh nghiệp. `M3_OUTPUT_ROOT` là thư mục private; không chọn M2/artifacts hoặc thư mục run cũ. DB trên máy kiểm là portable127.0.0.1:55432, không cài service toàn máy; đây không là yêu cầu port của mọi thành viên.

```powershell
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -m alembic -c M3/backend/alembic.ini upgrade head
.\.venv-m3\Scripts\python.exe -m pip check
cd M3/frontend
npm ci
npm test
npm run build
cd ../..
. ./M3/scripts/start_m3.ps1
```

Mở `http://127.0.0.1:8000/`, OpenAPI `/docs`, health `/api/v1/health`. Launcher chạy API+worker ẩn, log ở outputs; dừng bằng `M3/scripts/stop_m3.ps1`, chỉ dừng PID mà launcher tạo và đúng creation time. PostgreSQL quản lý riêng. Đây là app local, chưa có auth/hosting nhiều người; push GitHub không xuất bản database hoặc ứng dụng lên Internet.

Để phát triển FE: chạy `start_api.ps1`, `start_worker.ps1` trong hai terminal; tại M3/frontend dùng `npm run dev` port5173 proxyAPI8000. Không đồng thời mở worker dev và launcher; worker thứ hai bị advisory lock chặn.

## Tạo dữ liệu và lượt chạy

```powershell
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -m sigma_m3.cli import-orders --as-of-date 2025-12-31 --request-key import-v1 --wait
# Thay SOURCE bằng UUID trả về ở lệnh trên, không dùng chuỗi ví dụ nguyên trạng.
.\.venv-m3\Scripts\python.exe -m sigma_m3.cli seed-simulation --source-run SOURCE --as-of-date 2025-09-30
.\.venv-m3\Scripts\python.exe -m sigma_m3.cli forecast --source-run SOURCE --as-of-date 2025-12-31 --mode replay --request-key forecast-v1 --wait
# Thay FORECAST bằng UUID forecast complete và SCENARIO bằng ID kịch bản đã seed.
.\.venv-m3\Scripts\python.exe -m sigma_m3.cli simulate --kind policy_replay --forecast-run FORECAST --scenario-id SCENARIO --as-of-date 2025-09-30 --period-start 2025-10-01 --period-end 2025-12-31 --wait
.\.venv-m3\Scripts\python.exe -m sigma_m3.cli simulate --kind alert_replay --forecast-run FORECAST --scenario-id SCENARIO --as-of-date 2025-09-30 --period-start 2025-10-01 --period-end 2025-12-31 --wait
.\.venv-m3\Scripts\python.exe -m sigma_m3.cli simulate --kind stock_projection --forecast-run FORECAST --scenario-id SCENARIO --as-of-date 2025-10-31 --wait
.\.venv-m3\Scripts\python.exe -m sigma_m3.cli verify --run-id RUN
```

CLI `--wait` dùng worker thông thường; dừng worker nền trước khi dùng chế độ này. Cách dùng web: chọn nguồn/forecast/scenario, bấm Chạy phương án; worker nền nhận và cập nhật status. Không trộn hai cách để chạy hai worker. Forecast replay là việc nặng, không chạy lại chỉ để sửa thành phố hoặc xem dashboard. `forecast --mode future --forecast-run FORECAST` dùng selection khóa, origin không trước30/09/2025; không chọn lại bằng test. Missing vector/policy/history → failed, không tự điền0. Khi mã thay đổi, restart worker rồi tạo request mới; code mismatch không được ghi complete.

Seed chỉ tạo giả định rõ ràng: cover3/7/14 và safety×0,5/1/1,5, không ghi đè policy người dùng. Policy effective dates là [from,to); một supplier/item tại mỗi thời điểm. Policy mới không được đóng khoảng ảnh hưởng run đã khóa; muốn thử lịch sử dùng **scenario override** trong Cấu hình. Lô đầu kỳ có ETA đúng D+7, ordered_on≤origin. Snapshot không tự phát sinh đơn; khuyến nghị chưa là receipt.

## Cách trình diễn và kiểm

1. Chọn snapshot31/10 → kho Japan/NTT Docomo → SKU. Tồn kho: nhấn dòng xem SS/ROP floor/IP/MOQ/Q. Dòng snapshot là khởi tạo, không phải sales actual ngày31/10.
2. Dự báo → Tổng7 và Ngày phân bổ; xem H1–7/H8–14, sai số toàn cửa sổ test. Actual sau31/12 giữnull.
3. Nhập hàng → tách khuyến nghị và lô replay; Cảnh báo → nhấn dòng để thấy projection, chọn alert replay để xem confusion/early toàn lượt.
4. Cấu hình → tạo scenario với cover/safety, policy riêng và lô đang về; tạo run mới, run cũ giữ snapshot. URL giữ run/kho/item/origin, filter dùng chung bảng/CSV; KPI Tổng quan và tỷ lệ alert được ghi rõ là **toàn lượt**.
5. Xuất CSV: đối chiếu run/source/config/selection hashes, cutoff, phiên bản và nhãn mô phỏng. Export không có raw orders/customer/source IDs; đọc dữ liệu từng batch.

```powershell
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -B -m pytest M3/backend/tests tests M2/models/tests --basetemp=outputs/pytest-team
.\.venv-m3\Scripts\python.exe -m alembic -c M3/backend/alembic.ini check
```

Test DB phải đúng tên `sigma_m3_test`; fixture TRUNCATE chỉ database này, không dùng DB ứng dụng. Thiếu env thì tests PostgreSQL sẽ skip, không được báo là đã kiểm DB. CI chỉ dùng fixture giả; lần push phải xem kết quả GitHub riêng, không suy CI từ tests local. Workflow M3 tách Linux/PostgreSQL (54 tests M3), Windows/Python3.12 với toàn bộ dependency M3 (32 tests hồi quy M2, gồm golden300forecast ở ngưỡng1e-8), và frontend (9 tests/build). Golden được ghi trên Windows: lần CI đầu trên Linux có30giá trị Prophet lệch tối đa7,8783e-6; đây là giới hạn parity giữa hai nền tảng, chưa chứng minh Linux tái lập golden ở1e-8. Giữ nguyên fixture/ngưỡng/model M2; không bỏ test hoặc dùng CI xanh để nhận parity Linux.

Artifacts full/DB/env/raw giữ local. Complete chỉ sau verify; source-hash dedup giữ request identity nhưng tái dùng canonical daily dataset. Run đầu E89/E90 đã khóa không sửa manifest để thêm trường; phiên bản worker sau bổ sung runtime/seed/full config vào manifest của **run mới**. Receipt kiểm lại run cũ nằm ngoài thư mục đã khóa.


## Kiểm E2E kết thúc

Từ React tạo scenario `e2e_receipt_policy` v2 rồi run `950e6844-d611-48cf-b0ef-4e845ba0811a`, theo dõi queued→running→complete qua worker nền. Đã kiểm 920threshold/920events/1lô/1714alerts, CSV tải trực tiếp từ trình duyệt khớp1dòng đang lọc. Japan/NTT Docomo, D10G-10D eSIM: closing7, floor20/ROP20, pending20, IP27, S21, MOQ10, Q0; ETA04/11 từ ordered28/10. Cảnh báo dướiROP không tự đặt thêm khi pending đủ. Run và scenario v1 trước đó giữ nguyên.

Form ngày đã được kiểm lại bằng thao tác nhập và state updates riêng cho từng trường; ngày đặt và ETA được giữ sau đổi quantity. Nút thêm lô/override chờ catalog đã tải.7tests FE gồm chống render dữ liệu run cũ khi đổi context, abort response cũ, gửi lặp/retry cùng key và lưu ngày/quantity. Dữ liệu thực được kiểm riêng, không gọi7tests này là full browser E2E tự động. Launcher stop/start đã chạy, giữ PostgreSQL và các ứng dụng khác; web vẫn tại8000.

## E91 — Chẩn đoán và thử nghiệm bổ sung

Màn Cảnh báo có phân tích **toàn lượt alert replay** qua GET /runs/{id}/alert-opportunities. Run complete/đúng kind, snapshot/hash và summary phải khớp; query filter bị từ chối để mẫu số không đổi. Actual chỉ dùng giải thích sau replay, không làm feature. Không cập nhật manifest/summary của run đã khóa.

Cơ sở:1.550/2.867 sự kiện cạn ởD+1…D+6; chỉ1.317ca có khoảng cách từ origin≥7. Do đó trần báo sớm tại chính các origin/tồn đầu này là45,936519%, so thực986/2867=34,391350%; còn331ca đủ thời gian nhưng không có cảnh báo. Trần này không áp cho mọi hệ thống/kịch bản, không xóa ca cạn sớm hoặc thay R07 bằng tỷ lệ có điều kiện. Không có sự kiện thì các tỷ lệ null. UI hiển thị phân bố14ngày và giữ mẫu số khi lọc bảng; đã kiểm trực tiếp chọnJapan/NTTDocomo:40dòng tại origin, mẫu số toàn lượt vẫn2867. Ảnh local outputs/m3-alert-opportunities.png.

[Nghiên cứu ngày validation](research/README.md) dùng8phương pháp/28fits,95.760forecast/160nhóm metric/6.390ngày-tuyến đầu vào≤30/09/2025; không đọc test. Best theo từng tuyến H1–7 mean49,451918%,0/10≤20%; phân bổ M3 cùng623cặp/tuyến mean51,905954%.7/10tuyến có MAPE thấp hơn, nhưng loss giảm kèm bias âm; chưa chọn để phục vụ hoặc dùng vào tồn. Không nhận là đã cải thiện test/sản phẩm. Cần bằng chứng tiếp trước thay profile.

Run nghiên cứu cuối: outputs/research/daily-validation-v1-560a112e-2452-4b7a-a0c7-1e16d0475351. SelectionSHA0608d7dcda479cfea1e051f610edbfa833130db0ed43635b28c2bade72057180. Lượt trước7811fb30 được giữ; bản cuối bổ sung runtime/input/requirements hashes và clipping log, predictions/metrics/selection giống byte. Đối soát độc lập160nhóm metric/28cutoff/hashes/10selection đạt; receipt outputs/e91-verification.json ngoài run đã khóa.

86tests Python (54M3+32M2),9FE và TypeScript/build đạt. Hai test research kiểm future mutation/nhãn fit/thiếu lịch/zero; ca API kiểm mẫu số/boundary6–7–14, null, sai summary/filter/kind/status; FE kiểm context cũ và snapshot không có metric giả. Launcher restart riêng API/worker, giữ PostgreSQL. Snapshot mới309cc381-70cf-4e6a-9c1e-5b1220c49950 complete/verify:920threshold/920events/1lot/1714alerts, backendSHA1acba62a5213d419b67e4fca56ddaa1f0052bd4c2cbc86bd899c6a3d293e4f0f. Dùng lại forecast cha đã khóa; không refit toàn forecast/replay. Run E90 giữ codeSHA lịch sử, không sửa thành SHA mới. R05/R07/T14 còn mở; CI của commit E91 phải kiểm riêng sau push.
