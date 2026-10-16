# Dữ liệu cục bộ

Bộ M2 final dùng [m2-final.json](configs/m2-final.json); [tham số từng tuyến](../M2/reports/final_m2_20261011/model_configurations.md) công khai lịch sử học và mốc chuẩn hóa. Audit mới giữ raw SHA/118.296 quantity/46 tuyến; không đưa raw/daily/per-origin CSV lên GitHub.

**Lịch thử nghiệm ngày11/10/2026:** [calendar_features.csv](reference/calendar_features.csv),2.980 dòng ngày×điểm đến, phải đi cùng [catalog có ngày công bố](reference/calendar_features.events.json). CSV không chứa quantity; mô hình tính lại cờ lễ/khoảng cách theo thông tin có tại từng origin. [Protocol/kết quả](../docs/calendar-experiment.md); đầu ra vẫn local, không tích hợp dashboard.

**Tái hiện ngày09/10/2026:** CSV gốc đã được người dùng đưa lại, khớp SHA-256 nguồn báo cáo cũ. [Bảng xử lý](processed/m2_reproduce_20261009_full/manifest.json) gồm audit, chuỗi731 ngày×46 tuyến và top10 theo train. [Bộ dữ liệu học](training/m2_reproduce_20261009_full/manifest.json) có ba bảng split và [mục lục50 cấu hình](training/m2_reproduce_20261009_full/input_catalog.json). Mỗi biến thể có CSV đầu vào tại lần fit đầu30/06/2025 và JSON ghi cột/cấu hình; các lần refit tiếp dùng lịch sử tại cutoff tương ứng. Các thư mục này chỉ ở local, bị Git ignore; không phải bản phục hồi nguyên byte của run cũ.

**Nguồn cập nhật CHG-024 ngày 05/10/2026:** người dùng mô tả CSV order được cung cấp là dữ liệu giả định. Không nhận đã kiểm chứng cơ chế sinh; vẫn coi snapshot là riêng tư, giữ byte/hash và không push. Tồn/nhập/mapping tiếp tục có nhãn mô phỏng. Các mô tả “order thực” ở lịch sử trước đó phản ánh thông tin người dùng cung cấp tại thời điểm cũ.

CSV nguồn `sigma_sim_data_orders.csv` là dữ liệu riêng tư, không được đưa vào Git hoặc GitHub. Tệp được giữ nguyên trên máy; `.gitignore` loại dữ liệu trong thư mục này khỏi các commit thông thường.

Khi clone repository để làm việc trên một máy hoặc thư mục khác, người có quyền sử dụng dữ liệu tự đặt bản CSV được cấp phép tại `data/sigma_sim_data_orders.csv`. Không dùng dữ liệu khách hàng trong issue, notebook công khai hoặc ví dụ minh họa.

Hợp đồng dữ liệu và giới hạn nguồn nằm trong [data-contract](../docs/data-contract.md). Pipeline và demo đã triển khai; câu mô tả chưa có ở bản cũ là lịch sử.

## Đầu vào huấn luyện sau clean M2

```text
data/
├── sigma_sim_data_orders.csv     # Raw riêng tư, nguyên byte
├── configs/                     # Cấu hình đầu vào, ngày/tuần/lịch sử
└── training/m2_report_20261007/   # Daily/top10/audit và ba bảng train/validation/test
```

Chỉ các JSON cấu hình và README được Git theo dõi. Raw và bảng quantity dẫn xuất vẫn bị ignore. Mã huấn luyện nằm ở M2/models hoặc src/sigma; không trộn code vào thư mục dữ liệu.

Ba bảng top10 cắt từ run M2 đã seal theo split cố định. Train01/01/2024–30/06/2025; validation07–09/2025; test10–12/2025. Nhãn fit chỉ hoàn tất≤origin; không dùng nhãn validation/test trước cutoff. Manifest dẫn xuất ghi hash file và nguồn. [Hướng dẫn báo cáo](../M2/reports/presentation-guide.md).
