# Demo sản phẩm SIGMA cho M2–M3

Đây là hướng dẫn trình diễn phần mềm, không phải biên bản đạt toàn bộ yêu cầu. Bản nguồn bài đang dùng V13: tuần9/10, ngày R05 0/10; cảnh báo sớm≥7 ngày33,73% trên2867 sự kiện mô phỏng. Test đã xem, đánh giá hồi cứu. Không nói “đã đạt100%”. Word/slide cũ chưa được cập nhật.

## Mở bộ demo đã khóa trên máy hiện tại

```powershell
.\start_m2m3.ps1
```

Mở `http://127.0.0.1:8504`. Bộ khóa local `outputs/sigma_m2m3_checkpoint_v3/delivery.json` chọn chính xác run ngàyV11, tuầnV13, policyV4, stockV7, customerV6 và comparisonV3. Khi có run mới, bộ này giữ nguyên; thiếu/sai hash báo lỗi, không dùng run khác thay thế. Launcher sản phẩm thường vẫn là `start_product.ps1`.

## Trình diễn khoảng 8–10 phút

| Bước | Trang/thao tác | Nội dung cần nói và bằng chứng |
|---|---|---|
|1|Tổng quan, bảng tình trạng M2–M3|Một sản phẩm tích hợp, sáu trang. Có bảng phần đã triển khai/chỉ tiêu chưa đạt; tải HTML tình trạng. Ngày snapshot31/12/2025, không phải dữ liệu hôm nay.|
|2|Dự báo tổng7 ngày; Thailand/AIS, h1–7|Tổng quantity cho hai tuần riêng; lựa chọn mô hình từ validation. Xem forecast, model chọn, metric và baseline. Đổi sang cadence7 ngày rồi h8–14 để phân biệt các phép chấm.|
|3|So sánh ngày và tuần|Cộng mô hình ngày thành đúng tổng7 ngày rồi chấm cùng cửa sổ với tuần trực tiếp và naive/MA7/MA28. Ngày và tuần khác target; không dùng kết quả tuần nhận đạt R05.|
|4|Giao kháchD+7|Tuần đầu từ đơn đã đặt, ngày8–21 từ dự báo đơn mới. D+7 gồm cuối tuần, không trễ theo giả định. Actual giao còn trống.|
|5|Tồn từ dự báo tuần|Tồn theo tuyến×SKU×loại sản phẩm. Xem on_hand, hàng đang về, SS, ROP, IP, Q. Trigger on_hand<ROP; IP chỉ tính lượng đặt. Chưa gửi đơn đặt thật.|
|6|Chọn base→partial_receipt→late_receipt→no_receipt|So tỷ lệ đáp ứng/shortage/receipts/closing. Giảm nhập50%, muộn3 ngày và không nhận hàng là stress nhà cung cấp; không đổi D+7 của khách. Có các kịch bản bán sụt/tăng và6 biến thể độ nhạy.|
|7|Trang dự báo ngày/tồn/cảnh báo|Cho xem số liệu ngày, sai số thực tế hồi cứu, cảnh báo khẩn/sớm và ca không đạt. Nhập đầu ngày, bán theo timestamp/ID, đối soát closing=opening+receipts−fulfilled.|
|8|Quay tổng quan|Nêu kết quả chưa đạt và giới hạn, chỉ ra job07:00 cập nhật lịch giao local; không nói job tự huấn luyện toàn bộ khi dữ liệu mới.|

## Chuẩn bị và kiểm tra trước buổi báo cáo

Đọc [chẩn đoán mô hình](model-diagnostics.md) để giải thích số bán ngày/tổng tuần và các ca cảnh báo. Ở bước 5, mở **Giải thích từng ca cảnh báo trong replay**, lọc nhóm bỏ sót hoặc cạn trước ngày 7; bảng áp dụng cả bộ lọc tuyến/SKU/loại. Replay có 1.550 ca cạn trước ngày 7 và 350 ca bỏ sót dù còn cơ hội ≥7 ngày. Giữ tỷ lệ chính 33,73% trên 2.867 sự kiện; chẩn đoán nhóm đủ thời gian không thay mẫu số nghiệm thu.

```powershell
.\.venv\Scripts\python.exe -m sigma check-product --delivery-config outputs/sigma_m2m3_checkpoint_v3/delivery.json --country Thailand --carrier AIS --output-id demo_before_meeting_qa
```

Dùng output-id mới mỗi lần. AppTest kiểm đủ sáu trang, forecast/lịch giao, bộ lọc và bốn kịch bản tồn, không thay kiểm định mô hình độc lập. File `outputs/sigma_m2m3_checkpoint_v3/readiness.html` mở được offline. Không gửi CSV/run nguồn bài vào GitHub; xuất bảng theo tuyến vẫn giữ local.

Nếu demo trên máy mới: làm các bước cài môi trường và `python -m sigma demo --prefix demo_team` trong [README](../README.md), rồi mở `start_m2m3.ps1 -DeliveryConfig outputs/demo_team_bundle/delivery.json`. Demo mới được tự khóa, có3 tuyến giả do phần mềm sinh; kết quả demo không chứng minh top10 nguồn bài.

## Tạo bộ khóa mới sau khi đã đối soát các run

```powershell
.\.venv\Scripts\python.exe -m sigma release-check --delivery-config config.delivery.json --delivery-run sigma_delivery_v6 --policy-run sigma_weekly_policy_v4 --stock-run sigma_weekly_inventory_v7 --comparison-run sigma_day_week_comparison_v3 --output-id presentation_new
.\start_m2m3.ps1 -DeliveryConfig outputs/presentation_new/delivery.json
```

Lệnh kiểm hash toàn bộ artifact, cùng nguồn/toptrain/cha, snapshot phải lấy đúng policy, comparison phải dùng đúng forecast. Sinh config đã khóa, CSV/HTML tình trạng và summary. Lệnh không tự chạy lại tests/AppTest/đối soát chi tiết; chạy các verifier theo README trước khi dùng. Kiểm hash không biến một run có sai số lớn thành đạt accuracy.

Lịch Windows `SIGMA-Customer-Delivery-Refresh` đã cài07:00 theo múi giờWindows+07, pythonwẩn, IgnoreNew/StartWhenAvailable. Lần chạy thử Scheduler06/10/2026 trả0; CLI refresh kiểm `skipped_unchanged`, giữ last-good. Máy tắt/ngủ không chạy đúng phút; StartWhenAvailable chạy khi có thể. Bộ báo cáo khóa customerV6 nên không bị job đổi run đang trình diễn.
