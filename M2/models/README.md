# Mã mô hình M2

```text
models/
├── LightGBM/
│   ├── model.py        # Huấn luyện và dự báo pooled nhiều tuyến
│   ├── variants.json   # Các biến thể LightGBM
│   └── README.md
├── SARIMA/
│   ├── model.py        # SARIMA/SARIMAX riêng từng tuyến
│   ├── variants.json
│   └── README.md
├── Prophet/
│   ├── model.py        # Prophet riêng từng tuyến
│   ├── variants.json
│   └── README.md
├── registry.py         # Đăng ký mô hình và đọc cấu hình biến thể
├── model_families.json # Chọn các họ và cấu hình chạy chung
├── families.py         # Backtest, chọn validation, khóa lựa chọn, lưu kết quả
├── common.py           # Nhãn ngày/tổng 7, mùa vụ năm, schema dự báo
├── reuse.py            # Cache validation được kiểm chứng, dựng lại nhãn từ audit
├── verify.py           # Đối soát độc lập và báo cáo
├── build_report.py     # Báo cáo phân tích M2 lịch sử
└── tests/
```

Đọc [LightGBM](LightGBM/README.md), [SARIMA](SARIMA/README.md) hoặc [Prophet](Prophet/README.md) để xem cách dự báo và các biến thể. Phần dùng chung giữ ở cấp `models`; mã riêng của mỗi họ nằm trong `model.py` của họ đó.

Đầu ra nằm trong `M2/artifacts/<run-id>/<tên-họ>/daily` và `direct_7d`. Mỗi nhánh có predictions, metrics, fit logs và selected_models. Thư mục mã và thư mục kết quả dùng cùng tên họ.

## Pool cải tiến v2

26 biến thể gồm12 đối chứng cũ và14 mới,50 cấu hình biến thể×mục tiêu: LightGBM8 ngày/10 tổng7,SARIMA8/8,Prophet8/8. Hai hiệu chỉnh chỉ tham gia tổng7. Cấu hình version và reference_run chỉ rõ đối chứng; dùng run-id mới, không sửa run cũ.

Biến thể có thể override `training_window_days`, `n_estimators`, `min_child_samples`; LightGBM có `units: "raw"|"ratio"`, Prophet có `yearly_seasonality`. `targets` mặc định cả hai mục tiêu, hoặc danh sách mục tiêu áp dụng. Registry kiểm tra tham số trước fit; runner và verifier dùng cùng bộ biến thể hoạt động. Các module không đổi giao diện fit/update/predict/phase.

Mỗi nhánh thêm `validation_monthly_metrics.csv`: ngày bắt đầu dự báo nằm trong tháng7/8/9 và toàn bộ nhãn kết thúc trong tháng, cadence7 ngày giữ anchor validation. Đây là chẩn đoán độ ổn định; lựa chọn vẫn dựa MAPE validation block1 toàn kỳ,MAE rồi model id, cần đầy đủ forecast cả hai block. Báo cáo có lựa chọn tháng và bảng trước/sau.

`--validation-cache-run` là tùy chọn, mặc định fit mới. Cache cần run đã seal, cùng nguồn/cấu hình/audit; mã estimator phải nguyên hash hoặc đúng sửa tên biến metadata được kiểm chứng, các hàm forecast/metric/selection phải nguyên AST. Cache chỉ lấy forecast và fit log validation; actual dựng lại từ audit mới, metric/lựa chọn tính lại, khóa trước test fit mới. Lineage và hash input nằm trong manifest. Không tái sử dụng lựa chọn hoặc test qua tùy chọn này.

## Thêm biến thể

Thêm một khóa có tên duy nhất vào `variants.json` của họ tương ứng. Giá trị là các tham số mà `model.py` của họ hỗ trợ. Nếu cần tham số mới, bổ sung xử lý trong chính module đó. Không cần sửa vòng backtest hoặc verifier khi chỉ thêm biến thể.

## Thêm họ mô hình

1. Tạo `M2/models/<Tên>/` với `__init__.py`, `model.py`, `variants.json` và `README.md`.
2. Import module mới trong [registry.py](registry.py) và thêm `'<Tên>': module` vào `REGISTRY`.
3. Thêm `"<Tên>": "M2/models/<Tên>/variants.json"` vào mục `models` của [cấu hình chạy](model_families.json).
4. Kiểm tra nhãn, giới hạn dữ liệu tại origin và dự báo cả hai mục tiêu trước khi chạy bằng một run-id mới.

Tên họ phải thống nhất giữa registry và cấu hình. Tên biến thể duy nhất trong họ. Cấu hình được nạp thành các tham số cụ thể trong manifest; nguồn triển khai của từng module được ghi hash. Runner và verifier duyệt các họ trong cấu hình, không cần thêm nhánh `if` cho từng tên mới.

## Giao diện module

Với mô hình riêng từng tuyến, đặt `ROUTE_MODEL = True` và cung cấp:

```python
fit(history, spec, cfg, settings, parameters=None)
# Trả về (state, parameters, warning_names).

update(state, history, spec)
# Trả về state cập nhật giữa các lần refit.

predict(state, dates, spec)
# Trả về numpy array dự báo ứng với toàn bộ dates.
```

`history` là Series đã cắt tại origin, chỉ có nhãn hoàn tất trong cửa sổ huấn luyện. Với `daily`, đó là nhu cầu ngày; với `direct_7d`, đó là tổng trượt kết thúc tại ngày t: `S(t) = sum(y[t-6:t])`. Module dự báo 14 ngày tiếp theo; runner lấy h1–14 cho ngày, hoặc S(D+7) và S(D+14) cho tổng 7. `update` không refit; Prophet giữ state, SARIMA bổ sung quan sát mới. Chu kỳ refit nằm trong cấu hình chung.

Với mô hình pooled nhiều tuyến, đặt `ROUTE_MODEL = False` và cung cấp:

```python
phase(daily, groups, cfg, settings, target, split, choices=None)
# Trả về (predictions_dataframe, fit_logs_dataframe).
```

Dùng [LightGBM/model.py](LightGBM/model.py) làm mẫu. Bảng dự báo phải theo `COLUMNS` trong [common.py](common.py), nên tạo hàng bằng `prediction_rows`. Module tự bảo đảm refit và nhãn không vượt origin. Khi có `choices`, chỉ xuất biến thể đã chọn cho từng tuyến.

Các module dùng chung chỉ chịu trách nhiệm protocol, metric và lựa chọn. Thay đổi thuật toán hoặc thêm biến thể là thử nghiệm mới; không ghi đè run đã khóa.
