# Dự báo trực tiếp tổng quantity 7 ngày

Cấu hình sản phẩm: [configs/weekly.json](../data/configs/weekly.json),58 ứng viênV13; code tại [forecasting/weekly](../sigma/forecasting/weekly.py). Run `sigma_weekly_boost_v13` giữ52 ứng viênV10 và thêm2 booster300cây+4 hiệu chỉnh causal. Cache394.680 validationpairs được authenticate,6 ứng viên mới fitvalidation; khóa selection trước fresh test/future. Generic kiểm447.810pairs và calibration replay42.136factors đạt. V12 trước đó giữ nguyên artifact, cấu hình gốc lưu ở [weekly-organized-v12](../data/configs/experiments/weekly-organized-v12.json).

**Test hồi cứu 9/10≤20%, mean16,17%, LG U+21,19%; coverage100%. R05 ngày vẫn0/10**, chưa xác nhận mentor thay bằng metric tuần. Các lần V1–V13 có version riêng, không sửa run cũ. [Hướng dẫn cũ](history/weekly-forecast-before-code-organization.md) giữ làm lịch sử.

## Dùng và kiểm

```powershell
.\start_product.ps1
.\.venv\Scripts\python.exe -m sigma weekly --config configs/weekly.json --run-id weekly_new
.\.venv\Scripts\python.exe -m sigma verify-weekly --run-id weekly_new --daily-run sigma_scaled_v11 --output-id weekly_new_verified
```

Mở sản phẩm cổng8503, trang “Dự báo tổng7 ngày”. Để xem run mới, tạo bản sao config.delivery.json với weekly_run đúng rồi truyền -DeliveryConfig; không tự chọn run nghiên cứu. Launcher riêng start_weekly_dashboard.ps1 nhận -RunId và vẫn mở cổng8502. Máy clone phải chạy demo/pipeline trước vì outputs không trên GitHub.

## Phương pháp

- Sau chốt D, dự báo **hai tổng riêng** quantity bán D+1…D+7 vàD+8…D+14, không phải trung bình ngày, số đơn, activation hay doanh thu.
- Target success/order_datetime UTC theo A08 thực nghiệm; train2024-01-01–2025-06-30, validation2025-07-01–09-30, test2025-10-01–12-31; top10 chỉ trong train.
- Feature lịch đã biết, lịch sử quantity/basket/weekday/cùng kỳ năm trước/macro tại origin. Ratio chia mean90×7 causal, model trả về quantity. Median tuyến tính scaler/imputer chỉ fit train tại cutoff; mô hình từng tuyến tách fit, không điền annual bằng tương lai.
- Head hiệu chỉnh hoặc phối hợp chỉ dùng teacher được fit với label≤teacher origin và tuần đã kết thúc≤head cutoff. Trọng số convex/factor có giới hạn khai báo; không lựa chọn riêng tuyến khó bằng test.
- Refit7 ngày; chọn riêng tuyến bằng MAPE validation h1–7 tuần dương rồi MAE rồi model ID, full coverage; lưu/hash selection trước test. Mỗi run tự giữ selection lock; hash CSV có thể khác do round-trip float dù numeric parity1e-8, không sửa run để ép hash.
- Chỉ chấm cửa sổ đủ7 ngày; zero-week giữ trong MAE/WAPE/bias và đếm riêng, MAPE chỉ actual dương. Ngày thiếu/nhãn tương lai không là0.
- h1–7:86 cửa sổ rolling/tuyến hoặc13 không chồng lấp; h8–14:79/12 riêng. Lịch neo split, không đổi ngày neo sau thấy kết quả. Rolling windows không phải các tuần độc lập.
- Phân bổ xuống ngày dùng tỷ trọng weekday90 ngày quá khứ, fallback đều nếu toàn0; bảo toàn tổng từng tuần, không coi phân bổ là dự báo ngày đạt R05.

## Tích hợp và tái lập

Forecast tương lai:46 tuyến×2 khối=92 tổng,644 phần ngày, actual thiếu. Policy có đủH14 tại93 origins, kể cả tail chưa có actual; cùng model đã khóa và refit neo split, không dùng dữ liệu sau origin. Stock snapshot lấy đúng policy của cùng forecast/source/config.

Cấu hình nghiên cứu ở [configs/experiments](../configs/experiments); V10 có52 ứng viên, top10 test giốngV9 nhưng một số tuyến khác thay selection validation. V10 giữ riêng, không trộn với sổpolicyV9. Boosting E46 đã triển khai theo CHG-028/E51–E53: mặc định150cây, override300cây được kiểm trước fit, không đổi learning rate/split/metric. Bản tích hợpV13 được chọn theo validation trước xem kết quả testV13, không chọn phiên bản bằng test.

Cache validation phải được authenticate hash/artifacts/source/base protocol/spec/settings. Lệnh --reuse-validation-from tính lại selection rồi fit test/future mới, không cache test. Bỏ tùy chọn này để huấn luyện validation đầy đủ.

[So sánh ngày/tuần](day-week-comparison.md) và [bản đồ mã](code-map.md) có tiêu chí/cấu trúc. Test đã từng xem, không gọi kiểm định độc lập hoặc nghiệm thu10/10. Không tạo lại Word/slide.
