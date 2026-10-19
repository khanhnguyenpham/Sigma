# SIGMA trên Streamlit

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

Từ root implementation, có nguồn và run local hợp lệ theo [hướng dẫn M3](../IMPLEMENTATION.md), [benchmark30](../MONTHLY.md):

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

Test giả tại [test_public_streamlit.py](../backend/tests/test_public_streamlit.py); kiểm cả ngưỡng strict, pending covers, MOQ/ETA, độ nhạy, source không bị sửa, checksum/schema, CSV null và công thức. AppTest dữ liệu nguồn giữ local, không đưa bảng riêng vào CI. URL hoạt động không thay thế mentor nghiệm thu hoặc holdout độc lập.
