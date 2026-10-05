# Đối chiếu ảnh kickoff nhận ngày 05/10/2026

Đã xem trực tiếp ảnh JPG do người dùng gửi trong cuộc trò chuyện, tên gốc `f43397dd-bd00-4bd4-b239-f1daa267ced2.jpg`. Bản sao nguyên byte giữ local tại `reports/requirements/kickoff_received_2026-10-05.jpg`, không đưa ảnh lên Git. SHA256: `ee6b9837b60d5321683b1e452204f22b188a5a43f11f8072a4fca9fb82f1b7b2`.

Đây là nguồn S01 được đọc lại trực tiếp tại E35. Không phục hồi ảnh cũ đã xóa, không nhận đã đọc PDF hoặc hai ảnh mentor M01/M02 còn thiếu. Ghi nhận E34 rằng ảnh thiếu đúng tại thời điểm E34; phần này cập nhật nguồn nhận sau đó.

## Nội dung nhìn thấy trên ảnh

**T2 — Dự báo nhu cầu & tối ưu tồn kho kho số SIM / gói data.**

“Dự báo lượng kích hoạt SIM / gói data theo ngày và theo tuyến (quốc gia, nhà mạng), từ đó đề xuất mức đặt hàng và ngưỡng cảnh báo cạn kho số.”

| Mốc trên ảnh | Yêu cầu nguyên văn | Đối chiếu hiện hành |
|---|---|---|
| M1 đến 19/09 | Chuẩn hóa dữ liệu đơn hàng & kích hoạt | R01/T03: đã audit; activation không lọc sales theo M01 thuật lại |
| M1 | Phân tích mùa vụ: tuần, lễ tết, mùa du lịch | R02/T04: EDA có nguồn và giới hạn diễn giải |
| M1 | Baseline naive & moving average | R03/T05: đã chạy baseline ngoài mẫu |
| M2 đến 17/10 | Mô hình chuỗi thời gian theo từng tuyến (SARIMA / Prophet / LightGBM) | R04/T07–T09: SARIMA và LightGBM đã chạy; dấu `/` không tự diễn giải thành bắt buộc đủ ba thư viện |
| M2 | MAPE ≤20% ở top 10 tuyến chủ lực | R05/T09: chưa đạt tiêu chí ngày; phương án tổng tuần là CHG-023 do người dùng yêu cầu, chưa được mentor xác nhận thay nghiệm thu |
| M2 | So sánh với baseline, chọn mô hình cho từng tuyến | R03–R05/T09: lựa chọn validation, khóa trước test; tách metric ngày/tuần |
| M3 đến 07/11 | Chuyển dự báo thành chính sách tồn kho (safety stock, điểm đặt hàng lại) | R06/T10: triển khai mô phỏng, tham số đối tác là giả định |
| M3 | Cảnh báo cạn kho trước ≥7 ngày | R07/T10: replay có ca sớm/muộn/bỏ sót, chưa bảo đảm toàn bộ ca |
| M3 | Dashboard theo dõi dự báo và sai số thực tế | R08/T11: dashboard ngày và màn hình tuần local; actual tương lai để trống |

Dòng “KỸ NĂNG RÈN ĐƯỢC”: Pandas · feature engineering; SARIMA / Prophet; LightGBM; Job chạy định kỳ; Dashboard sai số. E37 đã chạy job local refresh/skip, kiểm lỗi/khóa/last-good; phần này là lịch sửE37. E54 ngày06/10 đã cài lịchWindows07:00 và chạy thử mã0; jobchỉrefresh lịchD+7, không tự refit toàn bộ forecast khiCSVđổi. Ảnh không cung cấp lịch chạy cụ thể.

Ảnh không ghi năm, split, cách xử lý MAPE khi actual bằng 0, horizon hoặc ngưỡng precision/recall. Giữ protocol hiện hành; không suy diễn thông tin không có trên ảnh. Năm 2026 có nguồn lựa chọn người dùng/báo cáo lịch sử. M01 số bán và M02 ngưỡng riêng đối tác vẫn là mentor do người dùng thuật lại, không phải xác nhận được chứng minh bởi ảnh này.
