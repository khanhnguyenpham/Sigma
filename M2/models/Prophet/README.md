# Prophet

- [model.py](model.py): fit và dự báo riêng từng tuyến.
- [variants.json](variants.json): cấu hình trend và seasonality theo biến thể.

| Biến thể | Seasonality mode | Changepoint prior scale | Tuần |
|---|---|---:|---|
| prophet_additive | additive | 0.05 | Có |
| prophet_multiplicative | multiplicative | 0.05 | Có |
| prophet_smooth | additive | 0.01 | Có |
| prophet_no_weekly | additive | 0.05 | Không |

Bốn biến thể đối chứng trên dùng yearly seasonality Fourier bậc3. Mọi biến thể không seasonality trong ngày,10 changepoint và dự báo điểm không lấy mẫu uncertainty. Seed lấy từ cấu hình chung.

## Biến thể cải tiến v2

| Biến thể | Năm | Tuần | Cửa sổ |
|---|---|---|---:|
| prophet_no_annual_weekly_w365 | Tắt | Có | 365 |
| prophet_no_annual_no_weekly_w365 | Tắt | Tắt | 365 |
| prophet_annual3_weekly_w540 | Fourier3 | Có | 540 |
| prophet_annual3_no_weekly_w540 | Fourier3 | Tắt | 540 |

Bốn biến thể đều additive và changepoint_prior_scale0.01, áp dụng cả ngày/tổng7. Cửa sổ540 là tối đa lịch sử hiện có tại origin; dữ liệu ban đầu chưa cung cấp hai chu kỳ năm đầy đủ. So sánh bật/tắt năm nhằm kiểm chứng độ ổn định, không mặc định cửa sổ dài hơn sẽ tốt hơn.

`daily` fit nhu cầu ngày. `direct_7d` fit tổng trượt kết thúc tại t, rồi dự báo S(D+7) và S(D+14). Với cửa sổ 365 ngày, tách trend và mùa vụ năm có giới hạn nhận dạng.

Module cung cấp `ROUTE_MODEL = True`, `fit`, `update`, `predict`. `update` giữ coefficients giữa các lần refit; runner vẫn dịch origin và các ngày cần dự báo. Không fit dữ liệu mới ngoài chu kỳ refit chung.

Kết quả: `M2/artifacts/<run-id>/Prophet/{daily,direct_7d}`. Xem [hướng dẫn thêm biến thể/mô hình](../README.md).
