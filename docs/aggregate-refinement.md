# Cải tiến sau bàn giao M3 — CHG-049/E77

Ngày 16/10/2026, người dùng cho phép tiếp tục hoàn thiện sản phẩm và muốn hạn chế việc phải chấp thuận từng lệnh. Phiên có xét duyệt tự động theo môi trường; không thay cấu hình quyền của ứng dụng. Các thử nghiệm dưới đây chạy local, không làm Word/slide hoặc push/upload dữ liệu.

## Hai thử nghiệm đã chạy

Giữ nguyên raw, target A08, top 10 train, train/validation/test, ngưỡng 20% và công thức metric. Test đã được xem từ trước nên là hồi cứu. Mỗi lượt đăng ký cấu hình trước validation, khóa lựa chọn trước khi chấm test; không thay lựa chọn bằng điểm test.

| Bộ kết quả | Tổng 7 đạt ≤20% | MAPE trung bình tổng 7 | Tổng 30 đạt ≤20% | MAPE trung bình tổng 30 |
|---|---|---|---|---|
| Sản phẩm đang dùng | 9/10 | 15,485424% | 9/10 | 11,786316% |
| Hiệu chỉnh nhân quả | 8/10 | 16,332325% | 7/10 | 14,527343% |
| Rút ngắn lịch sử học | 9/10 | 15,485424% | 8/10 | 12,552199% |

Độ phủ đều 100%, tổng 7 có 86 cửa sổ đủ nhãn/tuyến, tổng 30 có 63. Hai lượt mới giúp một số tuyến trên validation nhưng không ổn định khi sang test; chúng là kết quả nghiên cứu, không được đưa vào cấu hình mặc định. Không chọn lại từng tuyến theo điểm test. Sản phẩm giữ `sigma_aggregate_30d_20261016` và `sigma_m3_30d_20261016_precision_v2`, China Mobile tổng 30 vẫn 20,333443%.

**Hiệu chỉnh nhân quả:** [cấu hình](../data/configs/aggregate-calibration.json) đăng ký 13 phương án: identity và hai estimator × ba lookback 28/56/84 × hai shrinkage 0,5/1. Ước lượng bằng tỷ lệ tổng actual/forecast hoặc weighted median tối ưu MAPE; giới hạn hệ số 0,75–1,25, cần ít nhất 14 cửa sổ dương đã hoàn tất. Tại origin D, chỉ dùng cửa sổ có target_date ≤ D. Các nhãn bằng 0/thiếu vẫn giữ trong bảng đánh giá theo hợp đồng metric. Validation chọn 10 lựa chọn có hiệu chỉnh trong 92 tuyến×cửa sổ. China Mobile không thắng identity trên validation nên không bị đổi. Cấu hình/model mặc định cũ không bị sửa.

**Lịch sử học ngắn:** [cấu hình](../data/configs/aggregate-recent.json) đăng ký 12 LightGBM: lịch sử 180/270/365 ngày × 7/15 leaves × có/không feature cùng kỳ năm trước. Chỉ thử tổng 30, giữ tổng 7 làm đối chứng nguyên vẹn. Giữ feature, seed, refit 7 ngày, ratio/MAPE weights và các tham số khác. Validation chọn 5 tuyến mới; China Mobile vẫn chọn champion cũ. Không dùng test chọn thêm biến thể.

## Bằng chứng local

- `outputs/sigma_aggregate_calibration_20261016`: summary SHA `40d27b267b8f586b5462ec1ba178b067561bef1aae3675dc6378e2d0ae61bc9f`; verifier kiểm 30.544 dòng validation/664 nhóm metric, 8.464 test/184 nhóm, 92 future, 92 lựa chọn và 8.556 nhóm phân bổ.
- `outputs/sigma_aggregate_recent_20261016`: summary SHA `7678d4bfd6396e651abac8526f877a957c5711adb3de45e0dac37b2a15fa4fbf`; verifier kiểm 19.504 dòng validation/424 nhóm metric, 8.464 test/184 nhóm, 92 future, 92 lựa chọn và 8.556 nhóm phân bổ.
- Audit khác cách tính đã tái tính 39.100 hệ số từ prefix sum lượng bán, kiểm base forecast khớp tuyệt đối, support/nhãn cuối không vượt origin; kiểm 228 fit mới đúng số cặp và cửa sổ học. Bằng chứng `.tools/m3_20261016/refinement_audit.json` đi kèm hash script và hai summary.
- Verifier đọc ngày hỗn hợp thành datetime trước so sánh cutoff; không dựa vào thứ tự chuỗi. Hai receipt `*_verification_dates_v2.json` được ghi riêng, giữ nguyên receipt và run trước.
- Kiểm thử bao gồm future mutation, nhãn tổng 30, zero/missing, MAPE weighted median, phạm vi đường dẫn, cache đổi khi parent/receipt đổi và phân biệt hết hàng/tồn thấp/hàng đang về. Full suite native: **332 tests đạt**, không lỗi/skip; bằng chứng `.tools/m3_20261016/refinement_tests_final.xml`. Lượt sandbox trước phải dừng do treo, không tính là đạt.

```powershell
# Chọn run-id mới khi tái tạo. Không chạy test lặp lại trong cùng run.
.\.venv\Scripts\python.exe -m sigma aggregate-calibration --run-id calibration_new --phase validation
.\.venv\Scripts\python.exe -m sigma aggregate-calibration --run-id calibration_new --phase test
.\.venv\Scripts\python.exe -m sigma verify-aggregate --run-id calibration_new
.\.venv\Scripts\python.exe -m sigma aggregate-recent --run-id recent_new --phase validation
.\.venv\Scripts\python.exe -m sigma aggregate-recent --run-id recent_new --phase test
.\.venv\Scripts\python.exe -m sigma verify-aggregate --run-id recent_new
```

## Giao diện M3 đã cải thiện

- Tab tồn có hướng xử lý: hết hàng, xem xét đặt bổ sung, hàng đã đặt đang về, hoặc theo dõi định kỳ. Không tự gửi đơn nhập thật.
- Bảng và biểu đồ so sánh 13 kịch bản nêu tỷ lệ đáp ứng, thiếu hụt và tồn bình quân; có nhãn mô phỏng. Chưa gọi đây là tối ưu chi phí vì chưa có chi phí lưu kho/thiếu hàng được xác nhận.
- Tab cảnh báo giải thích 1.550/2.867 sự kiện cạn trước ngày thứ 7 của đợt; 1.317 ca có cơ hội báo trước 7 ngày, phát hiện 1.053 và bỏ sót 264. Đây là phân tích sau replay; tỷ lệ chính vẫn 1.053/2.867 = 36,728287%, không đổi mẫu số để tăng điểm.
- Chỉ rõ bảng nào theo tuyến, bảng nào theo SKU, KPI nào là toàn bộ kịch bản. Cache xét cả parent và hai receipt, nên thay đổi bằng chứng không tiếp tục dùng cache cũ trên lượt tải kế.
- AppTest 7 tab/11 ca lọc đạt; đã xem trực tiếp phần cảnh báo trong trình duyệt. [Ảnh local](../reports/M3_2026-10-16/canh_bao_giai_thich.png). Job chạy lại trả `skipped_unchanged`, giữ đúng M3 v2.

R05 ngày, China Mobile tổng 30, R07 và nghiệm thu T14 vẫn mở. Bước tiếp là nghiên cứu tín hiệu có thể kiểm chứng bằng train/validation; không sửa nhãn, ép dữ liệu hoặc đổi tiêu chí để nhận đạt. Bộ sản phẩm đang dùng không thay số liệu bởi hai thử nghiệm này.
