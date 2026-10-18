# Cải tiến sau bàn giao M3 — CHG-049/E77

**CHG-054/E84–E85 kết quả18/10/2026:** `sigma_aggregate_focus_20261018` đã chấm test sau khóa validation: **tổng30 đạt10/10**, MAPE trung bình **11,621356%**, coverage100%, 63cửa sổ đủ nhãn/tuyến. ChinaMobile dùng `mix_lgbm_annual_ratio7_w25`: validation10,972012% so với11,720299% cũ; test **18,683841%** so với20,333443% cũ. Tổ hợp75%champion LightGBM ratio +25%LightGBM annual ratio, không chọn trọng số từ test. Chín tuyến30 khác và toàn bộ tổng7 giữ nguyên (7vẫn9/10/15,485424%). M3 đã chạy/đối soát lại và [webPublic](https://sigma-demand-inventory.streamlit.app/) đã dùng bộ mới; chưa nhận hoàn tất toàn bài hoặc tiêu chí R05ngày/R07.

Verifier độc lập: raw100.000dòng/118.296quantity, top10train, 92lựa chọn, 12.880validation/8.464test/92future, 8.556nhóm phân bổ và1.048cutoff hợp lệ. Summary SHA `a8e90ec29ea154c34ac9d54fcf0a224767fe37a2435ab1ba0d57453359878c38`; receipt `outputs/sigma_aggregate_focus_20261018_verification.json`. [Audit bổ sung](../reports/portable_20261018/focus-independent-audit.json) tái tính2.208mixture, 2.208harmonic bằng NumPy normal equations, freshfit93forecast component test/future; 8.463control forecast khớp chính xác và241tệp protected nguyên. Không sửa sealed run cũ. Vì focus được chọn sau biết test cũ, đây là cải thiện trên benchmark hồi cứu, chưa có đánh giá dữ liệu mới độc lập.

**CHG-054/E84 đăng ký18/10/2026:** người dùng làm rõ mục tiêu cả10tuyến đạtMAPE≤20%, không chỉ đủforecast. Nghiên cứu mới giữ target/split/top10/ngưỡng và tổng7 nguyên, chỉ cho phép thay champion tổng30 của ChinaMobile; route focus do đã xem test cũ nên toàn bộ kết quả là hồi cứu. [Cấu hình đăng ký](../data/configs/aggregate-focus.json): 24mixture champion+8mô hình ×trọngsố0,1/0,25/0,5; 24Ridge mùa vụ Fourier1/2/3 ×daily-sum/end-total ×alpha1/10 ×raw/log-smear. Lịch sử540ngày, refit7ngày, chỉ fit nhãn đã kết thúc tại cutoff. Không có trend/lịch sự kiện suy từ test; Fourier dùng lịch biết trước. Champion cũ luôn đủ điều kiện, xếp validation MAPE/MAE/modelid; khóa lựa chọn trước một lần test. Chín tuyến còn lại và toàn bộ tổng7 giữ đúng forecast/metric cũ. Protocol được ghi trước đọc/fit validation; 13tests causal/tổng/mixture đã đạt. Chưa có kết quả mới tại lúc đăng ký; web vẫn9/10.

Ngày 16/10/2026, người dùng cho phép tiếp tục hoàn thiện sản phẩm và muốn hạn chế việc phải chấp thuận từng lệnh. Phiên có xét duyệt tự động theo môi trường; không thay cấu hình quyền của ứng dụng. Các thử nghiệm dưới đây chạy local, không làm Word/slide hoặc push/upload dữ liệu.

M3 mới `sigma_m3_focus_20261018`, summary SHA `cb3d72a3e4c4f454c3384da39f0d15a887e2068997ea3760a18b88a21bf5f902`:13kịch bản/920mặt hàng, 1.100.320ledger và khuyến nghị, 85.560ngưỡngSKU, 266.111sự kiện và8.280cửa sổ cảnh báo đã đối soát. Fillcơ sở85,978206%, early1053/2867=36,728287%. 357tests đạt,16checks sau promotion đạt; AppTest13kịch bản+7đối chứng/China/futureactual và7tabcloud đạt. Joblocal dùng config mới adopted_existing rồi skipped_unchanged, giữ job/run cũ. Cloud source78d06a6; [chi tiết triển khai](portable-hosting.md). Chỉ gói mã+11bảng tổng hợp đã được phép đưa lên repo hostingPrivate/appPublic; raw và run đầy đủ giữ local.

## Hai thử nghiệm16/10 — lịch sử trước tổ hợp mới

Giữ nguyên raw, target A08, top 10 train, train/validation/test, ngưỡng 20% và công thức metric. Test đã được xem từ trước nên là hồi cứu. Mỗi lượt đăng ký cấu hình trước validation, khóa lựa chọn trước khi chấm test; không thay lựa chọn bằng điểm test.

| Bộ kết quả | Tổng 7 đạt ≤20% | MAPE trung bình tổng 7 | Tổng 30 đạt ≤20% | MAPE trung bình tổng 30 |
|---|---|---|---|---|
| Mốc bàn giao16/10 | 9/10 | 15,485424% | 9/10 | 11,786316% |
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
