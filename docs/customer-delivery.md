# Quy tắc giao khách D+7 và giao diện sản phẩm

CHG-024 ngày 05/10/2026: người dùng thuật lại mentor giao đến khách mặc định 7 ngày trong mọi trường hợp, không trễ; sau đó xác nhận rõ **từ ngày khách đặt đến ngày khách nhận**, không phải hàng nhập từ đối tác về kho. Áp dụng 7 ngày lịch UTC, bao gồm cuối tuần. Ngày đặt 05/10 có lịch giao 12/10.

Nguồn CSV hiện được người dùng mô tả là dữ liệu giả định. Đây là thông tin người dùng cung cấp; không nhận đã chứng minh nguồn phát sinh thật hoặc phát sinh bằng bộ sinh của phần mềm. Giữ nguyên snapshot, target quantity và cách xử lý riêng tư. Các mô tả “order thực” trước CHG-024 là lịch sử thông tin tại thời điểm đó.

## Cách dùng sản phẩm

Trong PowerShell tại project:

```powershell
.\start_product.ps1
```

Mở `http://127.0.0.1:8503`. Menu chung có tổng quan, dự báo tổng 7 ngày, giao khách D+7, tồn/cảnh báo và dự báo ngày. Các launcher cổng 8501/8502 giữ tương thích; `start_product.ps1` là điểm mở sản phẩm chung. Menu dùng cặp run khai báo trong `config.delivery.json`, không âm thầm chọn một run nghiên cứu khác để đổi kết quả.

Tạo và kiểm lịch giao mới:

```powershell
.\.venv\Scripts\python.exe delivery.py --run-id sigma_delivery_new
.\.venv\Scripts\python.exe verify_delivery.py --run-id sigma_delivery_new --output-id sigma_delivery_new_verify
```

Run phải mới; đầu vào và hai run forecast/tồn cha phải cùng hash nguồn, cùng target/split/horizon/origin. Nguồn/cha đổi hoặc forecast thiếu ngày thì chặn thay vì nối kết quả không khớp. Dữ liệu và outputs giữ local.

## Lịch giao được tính thế nào

- `delivery_commitments.csv`: gộp quantity success theo ngày đặt UTC × tuyến × SKU × product_type; `delivery_date = order_date + 7`, `customer_delay_days=0`, `is_assumed_delivery=true`. Không xuất order/customer ID.
- Sau chốt ngày D, ngày giao D+1…D+7 thuộc các đơn đã đặt D−6…D. Đây là lượng cam kết đã biết theo giả định, không phải mô hình đoán đơn khách chưa đặt.
- Dự báo bán D+1…D+14 được phân bổ từ tổng tuần và chuyển lịch giao sang D+8…D+21. Đây vẫn là quantity dự báo, không phải đơn thực đã nhận. Hai phần được tách trong biểu đồ và CSV.
- `actual_delivered_qty` luôn thiếu vì nguồn không cung cấp sự kiện giao hàng. Lịch tính theo giả định không được gọi là actual giao, hoặc dùng để nhận MAPE bán bằng0.
- Không tự đổi lead time nhập hàng về kho. L=3 của cấu hình tồn v11 vẫn là giả định cũ, ngưỡng đối tác và kịch bản nhập/thiếu hàng được kiểm riêng. Lịch cam kết D+7 chưa chứng minh tồn đủ; các shortage/alert còn hiển thị.

## Cập nhật local định kỳ

`refresh_delivery_job.py` nhận các run cha hoàn tất, kiểm fingerprint nguồn/config/cha/mã, bỏ qua khi không đổi, có khóa chống chạy chồng và giữ run tốt trước nếu lỗi. Lỗi chỉ ghi loại lỗi, không log nội dung có thể chứa định danh. Không tự kéo dài split, huấn luyện lại hoặc coi CSV mới là đã có forecast hợp lệ.

```powershell
.\.venv\Scripts\python.exe refresh_delivery_job.py
```

Có script đăng ký Windows Task Scheduler, lịch mặc định 07:00 theo timezone Windows của máy:

```powershell
.\install_refresh_task.ps1 -At '07:00'
```

Script đăng ký được chuẩn bị và parse-check; **chưa tự cài lịch nền trên máy người dùng**. Chỉ CLI refresh/skip đã chạy thật. Nếu máy/process bị dừng đột ngột và còn `refresh.lock`, job không tự cướp khóa; cần kiểm không có worker đang chạy trước khi xử lý khóa. Khi nguồn thay đổi, tạo forecast/cha mới phù hợp trước khi refresh lịch giao.

## Phần chưa nghiệm thu

Giao diện và lịch D+7 đã có code/run/kiểm chứng; không đồng nghĩa mọi điều kiện học thuật đều đạt. Theo CHG-025, sau khi đủ các điều kiện nghiệm thu mới làm bản so sánh chính thức dự báo ngày/tổng tuần và đợt tổ chức lại code. Những bảng đối soát nghiên cứu hiện tại phục vụ kiểm metric, chưa đóng hai công việc đó. Không tạo lại Word/slide trong lượt này.


## Tồn từ tổng tuần — snapshot và replay đã kiểm

Menu “Tồn từ dự báo tuần” dùng `sigma_weekly_inventory_v3`, vector phân bổ từ V5, tồn/pending mô phỏng base v11 ở 31/12/2025. Có 920 khuyến nghị theo item với SS/ROP/Q/ETA. Chưa áp dụng lượng đặt hoặc chạy lại toàn bộ policy liên tục bằng tuần; menu tồn/ngày giữ 13 kịch bản v11. Run này replay 5.520 cửa sổ cùng 2.867 sự kiện thực của mô phỏng: TP 2071/FP 836/FN 796, early 33,73%, precision 71,24%, recall 72,24%; chưa bảo đảm R07. Không đổi mẫu số hoặc lead time nhập kho.

```powershell
.\.venv\Scripts\python.exe weekly_inventory.py --run-id weekly_stock_new --weekly-run sigma_weekly_calibrated_v5
.\.venv\Scripts\python.exe verify_weekly_inventory.py --run-id weekly_stock_new --output-id weekly_stock_verify
```

Trong máy clone mới, tạo các run cha trước, cập nhật `weekly_run`/`daily_run` trong `config.delivery.json` bằng tên mới rồi tạo run lịch giao/tồn tuần; không thể tải outputs riêng tư từ GitHub. Lịch giao V3 kiểm 80.105 nhóm/118.296 quantity, 1.885 đơn vị đã đặt giao tuần tới và 966 route-day. Job local tạo run tốt, lần kế tiếp skip unchanged; nguồn và 59 tệp v11 giữ nguyên.
