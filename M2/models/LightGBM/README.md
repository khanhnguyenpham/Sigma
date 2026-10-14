# LightGBM final — pooled top 10

[model.py](model.py) `phase` chuẩn bị toàn bộ top10 để học pooled, refit mỗi7 origin, rồi chỉ xuất tuyến chọn cấu hình đó. [weekly.py](../weekly.py) giữ nguyên feature, nhãn tổng7, loss và cách quy đổi quantity.

[variants.json](variants.json) giữ đúng 5 spec: `lgbm_annual_ratio7`, `lgbm_weighted_l1`, `lgbm_poisson`, `lgbm_annual_l1_15`, `lgbm_annual_l1_15_min50`. LG U+ dùng annual ratio với override trong [focus.py](../focus.py), không học riêng tuyến. [Bảng 10 tuyến và tham số](../../../M2_CODE_MAP.md#10-tuyến--cấu-hình--chỗ-mở-code).

150 cây, learning_rate0,03, reg_lambda10, seed42; leaves7/15 và min_child100/50 theo spec. Cửa sổ học365 ngày kết thúc nhãn, riêng LG U+540; mức bán nền ratio90, riêng LG U+56. Forecast hai block tổng7, không chia thành 10 estimator riêng. Các biến thể thử nghiệm cũ xem nhánh `backup/m2-before-cleanup`; kết quả và giải thích nghiên cứu vẫn ở reports/docs.
