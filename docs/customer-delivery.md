# Lịch giao khách D+7, tồn tuần và job local

CHG-024: mentor được người dùng thuật lại và người dùng xác nhận **khách đặt D → lịch khách nhận D+7 ngày lịch UTC**, gồm cuối tuần, không trễ. Đây là giả định cho lịch giao khách; không đổi lead time nhà cung cấp nhập về kho. Actual giao chưa được cung cấp.

```powershell
.\start_product.ps1
```

Sản phẩm ở http://127.0.0.1:8503 có6 trang: tổng quan, tuần, giaoD+7, tồn tuần, so sánh ngày/tuần, ngày/tồn/cảnh báo. [config.delivery.json](../config.delivery.json) chọn cặp forecast/daily; không tự trộn run hoặc chọn kết quả nghiên cứu tốt hơn. Bundle mới chỉ dùng sau kiểm source/protocol/cha/artifacts/UI.

## Lịch đã biết và lượng dự báo

[delivery/customer](../sigma/delivery/customer.py) gộp success quantity theo ngàyUTC×tuyến×SKU×product_type, không export order/customer ID. Lịch delivery_date=order_date+7 và customer_delay_days=0, có nhãn is_assumed_delivery.

Sau chốt D, các ngày giao D+1…D+7 thuộc đơn đã đặt D−6…D: quantity cam kết đã biết theo giả định, không phải đoán đơn chưa đặt. Forecast bán D+1…D+14 chuyển sang giao D+8…D+21; phân biệt trong CSV/biểu đồ. Tổng quantity được bảo toàn; actual_delivered_qty để thiếu.

```powershell
.\.venv\Scripts\python.exe -m sigma delivery --run-id delivery_new
.\.venv\Scripts\python.exe -m sigma verify-delivery --run-id delivery_new --output-id delivery_new_verified
```

Nguồn/order snapshot do người dùng mô tả là giả định, chưa xác minh phát sinh độc lập. Raw giữ nguyên. Run phải mới; cha khác nguồn/target/split/H14/origin hoặc thiếu forecast sẽ chặn. LịchD+7 không chứng minh tồn đủ và không làm MAPE bán bằng0.

## Tồn tuần xuyên suốt

Policy theo forecast tuần chạy13 kịch bản trong01/10–31/12/2025,93 origins×H14,59.892 forecast rows/1.100.320 ledger rows; có sổ giao dịch timestamp/ID và nhập đầu ngày. CustomerD+7 không trừ tồn lần thứ hai. SKU shares/SS/ROP/Q/IP/ETA và replay được đối soát độc lập.

```powershell
.\.venv\Scripts\python.exe -m sigma policy --weekly-run sigma_weekly_refactored_v12 --run-id policy_new
.\.venv\Scripts\python.exe -m sigma verify-weekly-policy --run-id policy_new --output-id policy_verified
.\.venv\Scripts\python.exe -m sigma stock --weekly-run sigma_weekly_refactored_v12 --stock-policy-run policy_new --run-id stock_new
.\.venv\Scripts\python.exe -m sigma verify-weekly-inventory --run-id stock_new --output-id stock_verified
```

Snapshot lấy closing/pending từ đúng policy của forecast/source/config, không lẫn sổ ngày baseline. Nếu bỏ --stock-policy-run, chế độ legacy lấy sổ ngày và ghi rõ provenance. Chỉ khuyến nghị, chưa gửi/áp dụng đơn đặt thật. Policy mô phỏng và snapshot/replay là các evidence riêng.

Base fill84,97%; nhập50%42,29%; trễ nhập3 ngày72,43%; không nhập7,69%. Replay sớm≥7 ngày33,80%, precision71,09%, recall72,13%, cùng5.520 cửa sổ/2.867 sự kiện/1.099 đã cạn loại trước. Giữ ca cạn trước7 ngày trong mẫu số; không nhận mọi cảnh báo đều đạt. [So sánh](day-week-comparison.md) giữ tiêu chí ngày/tuần tách biệt.

## Refresh và lịch nền

```powershell
.\.venv\Scripts\python.exe -m sigma refresh --delivery-config config.delivery.json
```

[jobs/refresh](../sigma/jobs/refresh.py) kiểm fingerprint nguồn/config/cha/implementation thật, skip khi không đổi, khóa chống chạy trùng, lỗi chỉ ghi loại lỗi và giữ last-good. Bundle demo có namespace job riêng. Đổi raw cần forecast/cha mới; job không tự thay split hoặc học tương lai. Nếu worker bị dừng đột ngột và còn lock, kiểm không còn worker trước xử lý khóa; không tự cướp lock.

Script Windows [install_refresh_task.ps1](../install_refresh_task.ps1) dùng pythonw và cwd của project, chạy daily07:00 theo timezoneWindows, StartWhenAvailable/IgnoreNew. Script đã parse-check; **chưa cài lịch nền** khi chưa có bằng chứng đăng ký. Có thể cài theo hướng dẫn:

```powershell
.\install_refresh_task.ps1 -At '07:00'
```

Lịch chỉ refreshD+7 từ dự báo cha đã kiểm, không tự huấn luyện toàn pipeline. [README](../README.md) có demo6 trang trên máy clone. R05 ngày0/10 và tuần9/10 còn mở; không nhận hoàn thành toàn bài. CHG-027 cho phép làm ngay so sánh/tổ chức mã, thay thứ tự hoãn củaCHG-025. [Hướng dẫn cũ](history/customer-delivery-before-code-organization.md) giữ lịch sử; Word/slide chưa làm lại.
