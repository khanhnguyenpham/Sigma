# SARIMA / SARIMAX

- [model.py](model.py): fit, cập nhật state và dự báo riêng từng tuyến.
- [variants.json](variants.json): order, seasonal_order và tùy chọn biến thể.

| Biến thể | (p,d,q) | (P,D,Q,s) | Biến đổi / biến ngoại sinh |
|---|---|---|---|
| sarima_100_100_7 | (1,0,0) | (1,0,0,7) | Nhu cầu gốc |
| sarima_111_011_7 | (1,1,1) | (0,1,1,7) | Nhu cầu gốc |
| sarima_log_100_100_7 | (1,0,0) | (1,0,0,7) | log1p, hoàn nguyên expm1 |
| sarimax_annual_100_100_7 | (1,0,0) | (1,0,0,7) | sin/cos năm |

## Biến thể cải tiến v2

| Biến thể | Cấu hình / cửa sổ |
|---|---|
| arima_101 | (1,0,1),không thành phần mùa vụ,365 ngày |
| arima_111 | (1,1,1),không thành phần mùa vụ,365 ngày |
| sarima_100_100_7_window180 | (1,0,0)(1,0,0,7),180 ngày |
| sarimax_annual_100_100_7_window540 | Cùng SARIMA với sin/cos năm,540 ngày |

Cửa sổ là số ngày nhãn tối đa đã quan sát; dùng toàn bộ lịch sử hiện có khi chưa đủ540 ngày, vẫn yêu cầu minimum_history_days. Các biến thể giữ update/extend, warm start, kiểm hội tụ và hợp đồng nhãn hiện hành; áp dụng cho cả ngày và tổng7.

`daily` fit chuỗi nhu cầu ngày. `direct_7d` fit chuỗi tổng trượt kết thúc tại t, rồi dự báo S(D+7) và S(D+14). Thành phần sin/cos năm chỉ phụ thuộc lịch đã biết. Biến thể log1p chưa hiệu chỉnh bias khi hoàn nguyên.

Module cung cấp `ROUTE_MODEL = True`, `fit`, `update`, `predict`. `update` gọi `extend` để bổ sung quan sát mới giữa hai lần refit. Lần refit sau dùng parameters trước để khởi tạo; nếu chưa hội tụ, thử lại từ khởi tạo mặc định. Candidate không hội tụ bị đánh dấu lỗi để runner loại khỏi lựa chọn có yêu cầu độ phủ đầy đủ.

Kết quả: `M2/artifacts/<run-id>/SARIMA/{daily,direct_7d}`. Xem [hướng dẫn thêm biến thể/mô hình](../README.md).
