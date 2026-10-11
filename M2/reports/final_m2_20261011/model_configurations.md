# Cấu hình 10 mô hình cho 10 tuyến M2

| Điểm đến | Nhà mạng | Họ | Model | Lịch sử học (ngày) | Mốc bán (ngày) | Dữ liệu học | Refit (ngày) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Thailand | dtac | LightGBM | lgbm_annual_ratio7 | 365 | 90 | train_top10_pooled | 7 |
| South Korea | LG U+ | LightGBM | tune56_w540_mul56p4 | 540 | 56 | train_top10_pooled | 7 |
| South Korea | KT | LightGBM | lgbm_weighted_l1 | 365 | Không chuẩn hóa tỷ lệ | train_top10_pooled | 7 |
| Thailand | AIS | LightGBM | lgbm_annual_ratio7 | 365 | 90 | train_top10_pooled | 7 |
| Japan | au (KDDI) | Prophet | prophet_annual3_weekly_w540 | 540 | Không chuẩn hóa tỷ lệ | own_route | 7 |
| South Korea | SKT | LightGBM | lgbm_poisson | 365 | Không chuẩn hóa tỷ lệ | train_top10_pooled | 7 |
| Thailand | TrueMove H | LightGBM | lgbm_annual_l1_15_min50 | 365 | Không chuẩn hóa tỷ lệ | train_top10_pooled | 7 |
| Japan | NTT Docomo | LightGBM | lgbm_annual_ratio7 | 365 | 90 | train_top10_pooled | 7 |
| Japan | SoftBank | LightGBM | lgbm_weighted_l1 | 365 | Không chuẩn hóa tỷ lệ | train_top10_pooled | 7 |
| China | China Mobile | LightGBM | lgbm_annual_l1_15 | 365 | Không chuẩn hóa tỷ lệ | train_top10_pooled | 7 |

Mỗi dòng là một cấu hình theo tuyến; các tuyến có thể dùng chung biến thể. Mốc bán = max(1, trung bình quantity/ngày trong N ngày quá khứ ×7), cập nhật theo origin. Model tỷ lệ chia nhãn và feature lượng bán cho mốc này, rồi nhân dự báo trở lại quantity. Không có mốc bán nghĩa mô hình học quantity gốc. Lịch sử học là cửa sổ tối đa của nhãn hoàn tất trước cutoff; tối thiểu90 ngày đầu vào. Refit trượt7 ngày, được học thêm nhãn validation/test đã hoàn tất trước origin, không khóa mãi tại30/06/2025.

LightGBM học pooled trên top10 train, 150 cây, learning-rate0,03, lambda10, seed42. Bộ feature gồm route/block/thứ/tháng, sin/cos năm, ngày từ đầu chuỗi, tổng7/14/28/90, tuần trước, std28, tỷ lệ ngày bán dương28, số đơn và quantity/đơn28; bản annual thêm tổng7 và trung bình28/90 cùng kỳ năm trước. Không dùng lễ hoặc feature cơ cấu đơn trong bộ final.

| Điểm đến | Nhà mạng | Loss | Số lá | Min child | Feature năm | Lịch sử hiệu chỉnh | Prior tuần |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Thailand | dtac | regression_l1 | 7.0 | 100.0 | True | 0 | 0 |
| South Korea | LG U+ | regression_l1 | 7.0 | 100.0 | True | 56 | 4 |
| South Korea | KT | regression_l1 | 7.0 | 100.0 | False | 0 | 0 |
| Thailand | AIS | regression_l1 | 7.0 | 100.0 | True | 0 | 0 |
| Japan | au (KDDI) | Prophet MAP | — | — | True | 0 | 0 |
| South Korea | SKT | poisson | 7.0 | 100.0 | False | 0 | 0 |
| Thailand | TrueMove H | regression_l1 | 15.0 | 50.0 | True | 0 | 0 |
| Japan | NTT Docomo | regression_l1 | 7.0 | 100.0 | True | 0 | 0 |
| Japan | SoftBank | regression_l1 | 7.0 | 100.0 | False | 0 | 0 |
| China | China Mobile | regression_l1 | 15.0 | 100.0 | True | 0 | 0 |

Loss regression_l1 dùng inverse-target weights; poisson dùng weights=1. LG U+ chuẩn hóa56/học540 ngày, đầu nhân56 ngày/prior4 tuần. Prophet au(KDDI) học riêng tuyến từ tổng trượt7, cửa sổ540, additive, Fourier năm3, mùa vụ tuần bật, changepoint prior0,01, 10 changepoints; không chuẩn hóa tỷ lệ.

H14, h1–7 chính/h8–14 riêng, refit7, seed42. Chín tuyến giữ lựa chọn validation cũ; LG U+ chọn qua test-sweep theo yêu cầu người dùng. [Tham số máy đọc đầy đủ](model_configurations.json).
