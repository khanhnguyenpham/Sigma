# LightGBM

- [model.py](model.py): feature, fit và dự báo pooled top 10 tuyến.
- [variants.json](variants.json): cấu hình riêng cho các biến thể.

| Biến thể | Objective | Lá | Feature năm |
|---|---|---:|---|
| lgbm_poisson | poisson | 7 | Không |
| lgbm_weighted_l1 | regression_l1, trọng số 1/y khi y>0 | 7 | Không |
| lgbm_annual_l1 | regression_l1, trọng số 1/y khi y>0 | 7 | Có |
| lgbm_annual_l1_15 | regression_l1, trọng số 1/y khi y>0 | 15 | Có |

## Biến thể cải tiến v2

| Biến thể | Thay đổi so với cấu hình chung |
|---|---|
| lgbm_annual_ratio7 | Chuẩn hóa theo mức bán90 ngày tại origin;7 lá,150 cây |
| lgbm_annual_ratio7_n300 | Cùng chuẩn hóa,300 cây |
| lgbm_annual_l1_15_min50 | Quantity gốc,15 lá,min_child_samples50 |
| lgbm_annual_l1_15_window180 | Quantity gốc,15 lá,cửa sổ nhãn180 ngày |
| lgbm_cal_ratio7_56_p4 | Hiệu chỉnh parent ratio150 bằng lịch sử56 ngày,prior4 tuần;chỉ tổng7 |
| lgbm_cal_ratio7_n300_56_p4 | Cùng hiệu chỉnh cho parent ratio300;chỉ tổng7 |

Các biến thể mới đều giữ weighted L1 và feature năm. Scale ngày là `max(mean90,1)`; scale tuần là `max(mean90*7,1)`, chỉ dùng90 ngày đã quan sát tại origin. Feature quantity và nhãn được chuẩn hóa, dự báo hoàn nguyên trước khi chấm. Daily ratio chỉ fit hàng có đủ lịch sử90 ngày; hàng của các biến thể cũ giữ nguyên.

Hiệu chỉnh tái sử dụng `sigma.forecasting.calibration.fit_factors`: teacher fit nhãn≤teacher origin, head dùng cửa sổ kết thúc≤cutoff, teacher origins cách7 ngày, hệ số0.5..1.5. Chu kỳ refit7 ngày áp dụng cho cả parent và head. Log có teacher origin/nhãn, từng cặp ngoài mẫu, factor và dự báo trước/sau để verifier tái tính độc lập. Không dùng dự báo in-sample hoặc actual tương lai để fit factor.

`daily` học nhãn nhu cầu cho từng horizon h1–14. `direct_7d` học trực tiếp nhãn tổng D+1…D+7 và D+8…D+14, dùng feature/fit theo hợp đồng tuần dùng chung ở `sigma.forecasting.weekly`. Nhãn huấn luyện chỉ được dùng khi ngày cuối nhãn không vượt cutoff.

Module cung cấp `ROUTE_MODEL = False` và `phase(...)`; runner gọi một pha pooled cho toàn bộ tuyến. Tham số fit chung như số cây và learning rate nằm trong [model_families.json](../model_families.json).

Kết quả: `M2/artifacts/<run-id>/LightGBM/{daily,direct_7d}`. Xem [hướng dẫn thêm biến thể/mô hình](../README.md).
