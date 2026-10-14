# Implementation bộ M2 final

[Bản đồ 10 tuyến và lệnh chạy](../../M2_CODE_MAP.md). Entrypoint duy nhất cho fit/refit/forecast/evaluate/export là `python -m M2.final_report`; không còn runner sweep hoặc chọn model lại.

| File | Vai trò |
|---|---|
| [LightGBM/model.py](LightGBM/model.py), [variants.json](LightGBM/variants.json) | 5 spec gốc phục vụ 8 tuyến, học pooled trên top10 |
| [focus.py](focus.py), [calibration.py](calibration.py) | Cấu hình LightGBM thứ 6 cho LG U+: scale56, học540, đầu nhân56/prior4; vẫn pooled top10 |
| [Prophet/model.py](Prophet/model.py), [variants.json](Prophet/variants.json) | Cấu hình thứ 7, riêng au (KDDI), annual3/weekly/window540 |
| [weekly.py](weekly.py) | Feature, nhãn tổng7, fit và predict pooled |
| [common.py](common.py), [families.py](families.py) | Nhãn trượt7, replay Prophet, metric block/cadence/tháng |
| [registry.py](registry.py), [verify.py](verify.py) | Đọc spec, hash dependency, đối soát nhãn/metric |

Không có daily estimator, SARIMA implementation, calendar/recent/composition feature, residual head, blend hoặc công cụ tuning trong nhánh cleanup. Các tài liệu [nghiên cứu ba họ](../../docs/model-families.md) và [SARIMA lịch sử](SARIMA/README.md) vẫn giữ nội dung giải thích; implementation cũ xem `git show backup/m2-before-cleanup:M2/models/SARIMA/model.py`.

Tham số dùng chung tại [m2-reproduce.json](../../data/configs/m2-reproduce.json); ánh xạ cố định/override LG U+ tại [m2-final.json](../../data/configs/m2-final.json). Tất cả thay đổi tổ chức đều giữ thuật toán và tham số final; test hồi cứu và giới hạn nghiệm thu không đổi.
