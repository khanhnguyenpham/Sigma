# M2 — dự báo nhu cầu

**Bản báo cáo ngày 07/10/2026:** nhánh `codex/m2-report-20261007`, kết quả đã khóa **9/10 tổng7, MAPE15,89%**. LG U+20,69% chưa đạt và để tối ưu sau; ngày0/10, R05 còn mở. [Kịch bản trình bày](reports/presentation-guide.md).

```powershell
.\scripts\start_m2.ps1
```

Chạy từ gốc repo, mở `http://127.0.0.1:8505`. Bản offline local: `M2/reports/m2_report_20261007/index.html`. Hai bản chỉ đọc dữ liệu đã khóa, không train khi trình bày. Raw/cấu hình đầu vào/bảng split nằm trong data; mã mô hình vẫn ở M2/models.

```text
M2/
├── artifacts/    # Các run, CSV dự báo/metric, lựa chọn, logs và snapshot nguồn
├── models/       # Mã, cấu hình và hướng dẫn riêng từng mô hình
│   ├── LightGBM/
│   ├── SARIMA/
│   └── Prophet/
├── notebooks/    # Notebook xem kết quả và so sánh mô hình
└── reports/      # Báo cáo, biểu đồ, bảng tổng hợp và hướng dẫn
```

- [Báo cáo cải tiến và lựa chọn từng tuyến](reports/m2_improved_models_20261006_handoff.md).
- [Đối soát độc lập, biểu đồ và bảng tháng](reports/m2_improved_models_20261006_fixed_review/M2_three_models.md).
- [Đối chứng 12 biến thể cũ](reports/m2_three_models_20261006_modular/M2_three_models.md).
- [Protocol và hướng dẫn chạy](reports/model-families.md).
- [Cấu trúc mã và cách thêm mô hình/biến thể](models/README.md).
- [Cấu hình](models/model_families.json), [pipeline](models/families.py), [verifier](models/verify.py).
- [Notebook so sánh](notebooks/model_comparison.ipynb).
- [LightGBM](artifacts/m2_improved_models_20261006_fixed/LightGBM), [SARIMA](artifacts/m2_improved_models_20261006_fixed/SARIMA), [Prophet](artifacts/m2_improved_models_20261006_fixed/Prophet).

Chạy từ thư mục gốc dự án, cùng cấp với `M2`:

```powershell
.venv\Scripts\python.exe -m sigma model-families --run-id ten_run_moi
.venv\Scripts\python.exe -m sigma verify-model-families --run-id m2_improved_models_20261006_fixed --output-id ten_bao_cao_moi
.venv\Scripts\python.exe -m pytest M2/models/tests
```

Run mới được ghi vào `M2/artifacts/<run-id>`, báo cáo đối soát vào `M2/reports/<output-id>`. Mỗi họ có `daily` và `direct_7d`. Tên run/báo cáo phải mới để bảo toàn kết quả đã khóa.

Các bộ run M2 cũ được chuyển nguyên bộ, kể cả đầu ra mô phỏng đi kèm trong cùng manifest. CSV, metric, lựa chọn và manifest giữ nguyên byte. `artifacts/relocation_before.json` và `artifacts/relocation_checked.json` ghi bằng chứng chuyển tệp; `artifacts/source_snapshots` giữ đúng mã nguồn lúc run lịch sử được chạy để kiểm hash.

Đường dẫn cũ trong `outputs` là junction/hardlink tương thích, dữ liệu chính nằm trong M2. Hai entry point cũ ở `sigma` chuyển tới implementation trong `M2/models`. Dữ liệu gốc, xử lý chung ở `src`, pipeline sản phẩm và tồn kho dùng chung ở `sigma` vẫn là phụ thuộc của M2. Kết quả cũ trong báo cáo lịch sử có thể dùng đường dẫn tương thích.

M2 chưa đạt R05 ngày; các kết quả test là hồi cứu. Việc tổ chức thư mục không thay target, split, mô hình chọn hoặc kết quả.

Pool cải tiến v2 đã đối soát:26 biến thể/50 cấu hình; tổng7 lựa chọn theo validation đạt9/10 test hồi cứu,15,89%, LG U+20,69%; ngày0/10. Notebook đọc run sửa đã seal, báo cả lựa chọn phối hợp và độ ổn định tháng. Lượt đầu có lỗi metadata actual của calibration được giữ nguyên để truy vết, không dùng để bàn giao. Chi tiết tại báo cáo cải tiến.

`presentation.py` đóng gói các bảng/HTML từ run đã seal; `report_app.py` là giao diện báo cáo. `data/training/m2_report_20261007` có daily_sales/top10/audit cùng train/validation/test riêng; `data/configs` giữ cấu hình và các bản lịch sử. Không đổi file/selection/metric trong run nguồn.
