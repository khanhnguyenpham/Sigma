# M2 final

Trên nhánh `m3-implementation`, M2 final giữ mô hình/CLI/notebook/HTML đã khóa: [model implementation](models/README.md).

- [Báo cáo final 11/10](reports/final_m2_20261011/README.md), [HTML offline](reports/final_m2_20261011/index.html), [cấu hình](reports/final_m2_20261011/model_configurations.md).
- [Tài liệu học cho 16/10](reports/mentor_prep_20261014/README.md), [Word](reports/mentor_prep_20261014/SIGMA_M2_Tai_lieu_hoc_va_bao_cao.docx).
- [Notebook final](notebooks/final_report.ipynb) đọc báo cáo khóa, không refit.

```powershell
.\.venv\Scripts\python.exe -m M2.final_report --help
```

10 lựa chọn dùng 7 cấu hình; 9 tuyến LightGBM pooled top10, Prophet cho au (KDDI). Chín lựa chọn giữ validation, LG U+ chọn sau test-sweep. Tổng7 h1–7 đạt 10/10 hồi cứu; h8–14 có 8/10; M05 hiện hành chấm R05 tổng30; số tuần ở đây chỉ mô tả M2, R07/T14 mở. Không thay số liệu hoặc nghiệm thu trong lượt dọn.

`artifacts/` và `reports/` giữ toàn bộ bằng chứng cũ. [Báo cáo published 07/10](reports/published_m2_20261007/README.md) và [guide cũ](reports/presentation-guide.md) là lịch sử. Code/sweep/CLI nghiên cứu đã chuyển về quyền khôi phục qua nhánh Git backup, không lưu archive code trong project. Các lệnh hoặc link code trong báo cáo khóa mô tả phiên bản trước dọn; xem [cách khôi phục](../docs/review-log.md#removed-docs-chg070).

CHG-068 bước4 gỡ dashboard/launcher/dependency Streamlit. Xem HTML offline hoặc notebook; CLI fit/verify/export giữ nguyên. Báo cáo khóa và artifact cũ được bảo toàn.
