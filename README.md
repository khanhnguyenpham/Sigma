# SIGMA — bộ code M2 final

**M3 — thiết kế ngày 19/10/2026:** đọc [bộ tài liệu M3](M3/README.md) cho nghiệp vụ, 13 bảng PostgreSQL, BE/API, FE, source dự kiến và kiểm thử. Nhánh `M3-design-plan` chỉ bổ sung/cập nhật Markdown; chưa có ứng dụng hoặc lệnh M3 chạy được. Hướng dẫn M2 bên dưới vẫn là đường chạy có thật.

Nhánh `M2-final-cleanup` chuẩn bị báo cáo thứ Sáu 16/10/2026. Điểm bắt đầu để tìm và giải thích code: [M2_CODE_MAP.md](M2_CODE_MAP.md). Có 10 lựa chọn theo tuyến, 7 cấu hình: LightGBM pooled top 10 cho 9 tuyến và Prophet riêng au (KDDI).

[Báo cáo final đã khóa](M2/reports/final_m2_20261011/README.md) · [HTML offline](M2/reports/final_m2_20261011/index.html) · [Tham số 10 tuyến](M2/reports/final_m2_20261011/model_configurations.md) · [Tài liệu học](M2/reports/mentor_prep_20261014/README.md).

```powershell
# Đã kiểm local bằng Python 3.12.14 trên Windows; CI cấu hình 3.14 chưa chạy lại.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\start_m2.ps1
```

Dashboard ở `http://127.0.0.1:8505`, chỉ đọc bảng aggregate đã kiểm hash, không cần raw để trình bày. Notebook [final_report.ipynb](M2/notebooks/final_report.ipynb) dùng cùng hàm đọc báo cáo. Có thể mở HTML offline trực tiếp.

```powershell
.\.venv\Scripts\python.exe -B -m pytest
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m M2.final_report --help
# Kiểm raw/nhãn/metric/log/hash của run lịch sử, không refit hoặc ghi đè receipt.
.\.venv\Scripts\python.exe -m M2.final_report --run-id m2_final_20261011_local --stage verify-artifacts
```

Lệnh fit/refit, forecast và export sang run mới tại [bản đồ code](M2_CODE_MAP.md#lệnh-dùng-tại-root-project). Raw và artifact cha chỉ có local; không chạy training/sweep tự động để mở dashboard. Mỗi run mới giữ manifest/source/code/config/seed/version riêng; run/báo cáo cũ không bị ghi đè.

Tổng D+1…D+7 có 10/10 tuyến dưới 20%, mean 15,745366%, coverage 100%; h8–14 có 8/10. Chín tuyến giữ lựa chọn validation; LG U+ được chọn sau test-sweep nên test hồi cứu. Metric tổng 7 không thay nghiệm thu R05 theo ngày. R05/R07/T14 còn mở; M01/M02 là xác nhận mentor do người dùng thuật lại, A08–A17 vẫn là đề xuất/giả định.

Các luồng M1/M3, SARIMA, sweep, notebook thử nghiệm và CLI cũ đã bỏ khỏi nhánh cleanup. Dữ liệu nguồn, run, forecast, manifest, Word/PDF và tài liệu nghiên cứu được bảo toàn. [Cách so sánh và khôi phục từng file](M2_CODE_MAP.md#khôi-phục-code-cũ) từ `backup/m2-before-cleanup`; hướng dẫn cũ còn trong tài liệu lịch sử chỉ áp dụng cho nhánh backup. Người dùng cho phép push nhánh M2-final-cleanup ngày14/10/2026; không merge/deploy.

[AGENTS](AGENTS.md) · [Tiến độ](docs/planning/TASK.md) · [PLAN](docs/planning/PLAN.md) · [Yêu cầu](docs/requirements.md) · [Hợp đồng dữ liệu](docs/data-contract.md) · [Nhật ký bằng chứng](docs/review-log.md).
