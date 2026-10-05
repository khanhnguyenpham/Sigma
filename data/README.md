# Dữ liệu cục bộ

**Nguồn cập nhật CHG-024 ngày 05/10/2026:** người dùng mô tả CSV order được cung cấp là dữ liệu giả định. Không nhận đã kiểm chứng cơ chế sinh; vẫn coi snapshot là riêng tư, giữ byte/hash và không push. Tồn/nhập/mapping tiếp tục có nhãn mô phỏng. Các mô tả “order thực” ở lịch sử trước đó phản ánh thông tin người dùng cung cấp tại thời điểm cũ.

CSV nguồn `sigma_sim_data_orders.csv` là dữ liệu riêng tư, không được đưa vào Git hoặc GitHub. Tệp được giữ nguyên trên máy; `.gitignore` loại dữ liệu trong thư mục này khỏi các commit thông thường.

Khi clone repository để làm việc trên một máy hoặc thư mục khác, người có quyền sử dụng dữ liệu tự đặt bản CSV được cấp phép tại `data/sigma_sim_data_orders.csv`. Không dùng dữ liệu khách hàng trong issue, notebook công khai hoặc ví dụ minh họa.

Hợp đồng dữ liệu và giới hạn nguồn nằm trong [data-contract](../docs/data-contract.md). Hiện chưa có pipeline hoặc bộ dữ liệu demo được triển khai.
