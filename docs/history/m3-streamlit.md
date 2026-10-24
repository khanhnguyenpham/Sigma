# Streamlit M3 — lịch sử đã ngừng dùng

CHG-068 bước3 bỏ toàn bộ source/adapter/build Streamlit. Nội dung dưới đây chỉ ghi lại E94–E99, không là lệnh chạy của nhánh hiện tại. Ứng dụng online cũ không bị thay đổi.

# SIGMA trên Streamlit

**E99 — 21/10/2026:** bản deploy `10dd4e19af9fa26d1aeb05124a05bbd5fdcf78ce` bổ sung timeout đọc30s/write90s/handshake20s, không tự retry write, bỏ phản hồi trễ sau abort/timeout; có retry đọc, refresh giữ phiên, PageBoundary, hướng dẫn và điều hướng bàn phím/Back. Dropdown tạo phương án chỉ liệt kê93ngày được đối chiếu đủ closing920item và forecast. [Hướng dẫn nộp/kiểm web](../../M3/SUBMISSION.md). Data release/manifest v2 không đổi; commit E98 bên dưới là lịch sử.120Python+31React đạt.


## Bản hiện hành E98 — React quản lý

[Mở SIGMA công khai](https://sigma-demand-inventory.streamlit.app/). Repo deploy riêng tư `khanhnguyenpham/Sigma-M3-App/main`, entry `streamlit_app.py`, commit `77b0b3d9406ba2131f678466b86f6615af6636e4`. Cùng source React E97 được build riêng cho component Streamlit; bản FastAPI/PostgreSQL local vẫn dùng API gốc. Phần E94 bên dưới là bản Streamlit native lịch sử.

| Màn hình | Chức năng hiện hành |
|---|---|
| Tổng quan | Tồn, nhu cầu bổ sung, lô đang về, cảnh báo và thao tác nhanh theo cùng context |
| Tồn kho | Lọc, xem ngăn SKU với ROP/SS/pending/IP/MOQ/Q và CSV |
| Dự báo | Tổng30/tổng7/ngày phân bổ, actual null khi chưa quan sát, baseline/metric trong phần mở rộng |
| Nhập hàng | Cần bổ sung/Đang về/Lịch sử, tìm kiếm/sắp xếp trước phân trang, chi tiết và CSV toàn bộ bộ lọc |
| Cảnh báo | Ngưỡng/cạn, đường dự phóng14ngày và đánh giá replay đã công bố |
| Cấu hình | Kho, chính sách supplier-item có phiên bản, kịch bản và lô đầu kỳ; thay đổi riêng phiên |

**Tạo phương án online:** chọn forecast đã công bố → kịch bản → origin có forecast và tồn công khai đầy đủ → Bắt đầu. Chỉ `stock_projection`; lấy closing tại origin đã công bố, không dùng số ngày phủ để suy lại lịch sử. Danh sách lô đầu kỳ trong kịch bản là nguồn pending (trống nghĩa không có); không tự mang lô từ snapshot cũ sang. Dùng hàm recommend/project backend nguyên byte. Chỉ đề xuất Q, không gửi PO hoặc tự ghi nhận nhập. Phương án mới chưa có actual tương lai. Huấn luyện/import raw/replay giao dịch/worker/DB bền vững/auth nhiều người dùng vẫn local hoặc ngoài phạm vi.

**CSV:** bấm Xuất CSV để chuẩn bị, rồi Tải CSV. Khi đổi context, link tải cũ bị hủy; CSV xuất toàn bộ kết quả đã lọc và có context. Cấu hình/phương án mới tách theo phiên Streamlit; restart/ngủ/reset có thể làm mất. Kết quả đã công bố không thay đổi khi sửa cấu hình.

**Gói v2:** `m3-react-public-20261020-v2`, manifestSHA `61033b539804419dc2ff88279a8d8726f5b3b2ad49da5e3e4a788bd830964cd4`.11bảng+cube giữ nền E94, thêm7360đường projected stock14ngày đã làm sạch vào bảng alerts; payload data7.023.845byte. `projection_json` chỉ3trường date/closing_forecast/receipts_qty. `item_id=item_key+1` và warehouseID là số thứ tự công khai, không phải ID đơn/khách hoặc khóaDB gốc. Policy ngày hiệu lực mặc định2024-01-01 là giả định online, không khẳng định là ngày hiệu lực nguồn. Thành phố mặc định trống vì không có trong release cũ.

**Mã:** `sigma_public/react_host.py` phục vụ component và quản lý phiên; `react_api/bundle.py` kiểm pin/adapter, `state.py` cấu hình/phương án, `views.py` scope/ledger/CSV, `forecast.py` forecast/metric và `dispatcher.py` allowlist RPC. `metrics.py` giữ byte giống `src/evaluation.py`. Cache dữ liệu dùng chung chỉ đọc; trạng thái phiên deep-copy, không ghi CSV/run đã khóa.

```powershell
# Trong M3/frontend, sau npm ci
npm test
npm run build:streamlit
# Trở lại root, nguồn và run local đã kiểm như E94
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe M3/streamlit/build_react_release.py --base outputs/streamlit-m3-public-20261020-v1 --destination outputs/react-public-new --frontend outputs/streamlit-react
```

Builder yêu cầu destination mới và kiểm DB/run nguồn trước khi lấy các projection đã làm sạch. Chỉ copy allowlist đã rà vào repo deploy; không push `outputs`, env, DB, raw hoặc giải thích chứaID. Build assets tương đối là bắt buộc; không đưa dist của chế độ FastAPI vào component.117Python/23React đã đạt; browser/API/publication và giới hạn kiểm tại E98. R05 vẫn10/10 hồi cứu; không nhận mentor đã nghiệm thu R07/T14.

## Lịch sử E94 — Streamlit native

Bản công khai dùng giao diện Streamlit và kết quả **M3 L7/R1/H14** cùng benchmark tổng30 M05. Mã này không cần PostgreSQL, raw orders hoặc các thư viện huấn luyện khi phục vụ web. Địa chỉ triển khai: [sigma-demand-inventory.streamlit.app](https://sigma-demand-inventory.streamlit.app/).

## Phạm vi online

| Màn hình | Chức năng |
|---|---|
| Tổng quan | R05 10/10 hồi cứu, MAPE/coverage, lịch sử quantity theo tuyến, fill và early rate có mẫu số |
| Dự báo | Tổng30/tổng7/ngày phân bổ H14, origin, tuyến, top10/46, sai số và baseline, CSV |
| Tồn kho | Snapshot31/10 có lô đang về, snapshot31/12 và ledger policy cơ sở; ROP/SS/IP/MOQ/Q |
| Nhập hàng | Lịch đặt/ETA D+7/đã nhận/status của các run mô phỏng |
| Cảnh báo | Replay cơ sở không nhập mới, TP/FP/FN/TN, precision/recall/early/dateMAE, chẩn đoán cơ hội và độ nhạy |
| Thử phương án | Thay tồn đầu/pending/ETA lô đã biết/ROP/MOQ/safety/nhu cầu/nhận hàng; tính theo cùng hàm M3 và tải sổ dự kiến H14 |
| Kiểm chứng | Scope, source/manifest hash, dữ liệu từng bảng, M05/A08, phiên bản và giới hạn |

Phương án chỉ tồn tại trong phiên đang dùng, không ghi database/đơn thật hoặc thay điểm benchmark. Widget và kết quả khóa theo origin–mặt hàng; đổi context không giữ kết quả của mặt hàng trước. Giá trị số lẻ là nhu cầu/tồn dự kiến, không ghi thành actual. Pending đủ IP có thể Q=0 nhưng vẫn cần xem đường tồn trước ETA.

**Các tác vụ local:** huấn luyện, import raw, worker, DB bền vững, chỉnh cấu hình dùng chung và quản trị nhiều người dùng. Bản public không tự mở PostgreSQL/FastAPI local lên Internet. App online không giữ database thay đổi qua các lần ngủ/restart của Streamlit.

## Dữ liệu và kiểm tra

Gói E94: **11 bảng tổng hợp nén + 1 mảng forecast**, khoảng6,6MB, từ nguồn SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. ManifestSHA `004df66221186936ae46cd3dec3a9a14097f51d1dcfd8c3c7fd68924e20341fb`. Có920mặt hàng,33.626route-day,8.510tổng30,17.020tổng7,87.400dòng sổ tồn,3.246lô nhập giả định,8.941dòng cảnh báo và10lượt độ nhạy. Mảng185×920×14 giữ float64, kiểm bảo toàn17.020tổng tuần trong1e-8.

Không xuất raw/ID đơn/khách/chuỗi giao dịch/credentials/env/DB. `item_key` là số thứ tự mới của danh mục tổng hợp, không phải ID đơn hoặc ID item trong DB. Quantity ngày theo tuyến và SKU/config/tồn đều là bảng dẫn xuất hoặc giả định; không gọi tồn doanh nghiệp thật.

Builder kiểm complete/verified/config/source/target/artifact hashes, tổng30 đã kiểm, bảo toàn forecast, ledger, ETA và metric cảnh báo tính lại. Runtime kiểm manifest pin, schema, hash cùng byte đem parse; NPZ không cho pickle/object và mảng dùng chung chỉ đọc. CSV mang context phiên bản/source/scope, null trống và escape chuỗi công thức. Mã `inventory.py`/`alerts.py`/`errors.py`/`__init__.py` được đóng gói nguyên byte từ backend.

## Tạo và kiểm gói

Từ root implementation, có nguồn và run local hợp lệ theo [hướng dẫn M3](../../M3/IMPLEMENTATION.md), [benchmark30](../../M3/MONTHLY.md):

```powershell
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -B M3/streamlit/build_release.py --destination outputs/streamlit-m3-public-new
```

Destination phải mới; không ghi đè release/run sealed. Script dùng các run E90/E93 đã khóa trên máy này, không âm thầm chọn run mới hoặc fit lại. Máy nhóm khác phải đối chiếu run ID/source/hash trước khi điều chỉnh hằng số nguồn trong builder.

Sau khi rà payload, mở ứng dụng từ thư mục gói (cần dependencies trong `requirements.txt` của gói):

```powershell
python -m streamlit run streamlit_app.py
```

Triển khai repo riêng tư `khanhnguyenpham/Sigma-M3-App`, nhánh `main`, entrypoint `streamlit_app.py`. Chỉ đưa allowlist đã rà lên repo; bảo toàn byte `release_m3/**` qua `.gitattributes`. App công khai và repo riêng tư là hai quyền khác nhau. Không dùng `SIGMA_RELEASE_SHA256` của sản phẩm cũ làm pin gói mới; gói này có manifest/pin riêng tại `release_m3`.

Test giả lịch sử tại [test_public_streamlit.py ở phiên bản b1357cd](https://github.com/khanhnguyenpham/Sigma/blob/b1357cd/M3/backend/tests/test_public_streamlit.py); kiểm cả ngưỡng strict, pending covers, MOQ/ETA, độ nhạy, source không bị sửa, checksum/schema, CSV null và công thức. AppTest dữ liệu nguồn giữ local, không đưa bảng riêng vào CI. URL hoạt động không thay thế mentor nghiệm thu hoặc holdout độc lập.


**Cache khi cập nhật E99:** `react_host.ADAPTER_VERSION` là một phần khóa resourcecache và phiên. Khi đổi Pythonadapter, phải đổi revision này; phiên cũ được khởi tạo lại, bỏ command/response cũ để không phát lại write. Khi chỉ làm mới dữ liệu trong cùng revision, giữ cấu hình/phương án riêng phiên. Data manifest vẫn định danh dữ liệu công bố, không dùng để thay thế phiên bản mã adapter. Hai test riêng kiểm cache theo revision và giữ/reset session đúng phạm vi.
