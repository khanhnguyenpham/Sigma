# M2 — bộ báo cáo final

Nhánh `M2-final-report`, ngày 11/10/2026. Chạy lại mới 10 cấu hình cố định từ CSV gốc: **10/10 tuyến có MAPE tổng D+1…D+7 test <20%, trung bình 15.745366%, coverage100%**. LG U+ đạt19,265900%; chín tuyến còn lại tái lập dự báo cũ trong dung sai1e-8.

- [Báo cáo kết quả 10 tuyến](reports/final_m2_20261011/README.md), [HTML offline](reports/final_m2_20261011/index.html).
- [Cấu hình 10 mô hình](reports/final_m2_20261011/model_configurations.md): lịch sử học, mốc chuẩn hóa, loss, feature, refit và hiệu chỉnh.
- [JSON đầy đủ](reports/final_m2_20261011/model_configurations.json), [metric test](reports/final_m2_20261011/test_metrics.csv), [trước/sau](reports/final_m2_20261011/before_after_routes.csv).
- [Nắm M2 trong 4 giờ](reports/mentor_prep_20261014/README.md): dữ liệu thực sự dùng để học, model từng tuyến, ví dụ cửa sổ/refit, thử nghiệm không được chọn và luyện phản biện cho buổi báo cáo.

```powershell
.\scripts\start_m2.ps1
```

Mở http://127.0.0.1:8505. Giao diện chỉ đọc bộ bảng tổng hợp đã kiểm hash; clone không cần CSV riêng tư để xem báo cáo. [Notebook final](notebooks/final_report.ipynb) dùng cùng bộ này.

## Tái chạy và kiểm tra

```powershell
.venv/Scripts/python.exe -B -m M2.final_report --run-id NEW_UNIQUE_RUN_ID
.venv/Scripts/python.exe -B -m pytest M2/models/tests
```

Cấu hình khóa tại [m2-final.json](../data/configs/m2-final.json). Runner fit mới validation/test/future; audit raw, top10 train, đủ nhãn/cặp, cutoff, metric, hiệu chỉnh và parity chín tuyến. Run, chuỗi ngày và forecast từng origin giữ local trong `M2/artifacts/<run-id>`. Khi xuất báo cáo lần mới, đổi `report_id` trong bản cấu hình trước run; không ghi đè bộ đã seal.

## Phạm vi kết quả

Chín tuyến giữ lựa chọn validation; LG U+ dùng `tune56_w540_mul56p4` từ test-sweep theo yêu cầu người dùng. Đây là test hồi cứu, rerun xác minh tái lập, chưa có holdout độc lập. H8–14 LG U+ còn20,255792%. MAPE tổng7 không thay nghiệm thu R05 theo ngày; R05/R07/T14 vẫn mở. Tồn/M3 chưa đổi.

Bộ final chỉ có cấu hình và bảng tổng hợp phục vụ báo cáo. Các bản thử nghiệm, run lỗi và báo cáo cũ giữ trong [lịch sử M2](HISTORY.md) để truy vết. Mở lịch sử local bằng `.\scripts\start_m2.ps1 -RunId m2_reproduce_20261009_full`; published07/10 giữ nguyên byte.
