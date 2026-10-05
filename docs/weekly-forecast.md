# Dự báo tổng quantity bán trong 7 ngày

Theo CHG-023 ngày 05/10/2026, người dùng yêu cầu làm mô hình dự báo tổng bán 7 ngày. Đã triển khai và chạy thật phương án tuần riêng, không ghi đè run ngày `sigma_scaled_v11`. Đơn vị là **tổng quantity sản phẩm bán**, không phải số đơn, số kích hoạt, doanh thu hoặc trung bình ngày.

## Sử dụng

Tại thư mục project, mở PowerShell:

```powershell
.\start_weekly_dashboard.ps1 -RunId sigma_weekly_v1
```

Mở `http://127.0.0.1:8502`. Dashboard có bốn tab: dự báo tuần, sai số và baseline, phân bổ về ngày, kiểm chứng. Run được kiểm hash trước hiển thị; trang không tự huấn luyện hoặc upload. Dashboard ngày/tồn cũ vẫn mở bằng `start_dashboard.ps1` tại cổng 8501.

Tạo run tuần mới bằng cùng CSV local và môi trường đã khóa trong README:

```powershell
.\.venv\Scripts\python.exe weekly_forecast.py --run-id sigma_weekly_new
.\.venv\Scripts\python.exe verify_weekly.py --run-id sigma_weekly_new --output-id sigma_weekly_new_verify
.\start_weekly_dashboard.ps1 -RunId sigma_weekly_new
```

Tên run/output phải mới; chương trình không ghi đè thư mục tồn tại. Verifier mặc định so sánh run ngày local `sigma_scaled_v11`, có thể chỉ định `--daily-run` khi đã có run ngày khác phù hợp. Máy clone chỉ có mã, không có CSV/run riêng tư; không nhận clone xong đã có các kết quả thật này.

## Phương pháp và điều kiện thực tế

- Sau chốt ngày UTC D, dự báo trực tiếp hai tổng riêng: D+1…D+7 và D+8…D+14. Không chỉ cộng dự báo ngày để gọi là mô hình mới.
- Target vẫn A08 success quantity tại order_datetime, không phụ thuộc activation. Top 10 vẫn từ train 01/01/2024–30/06/2025; validation và test giữ nguyên tháng 7–9/tháng 10–12 năm 2025.
- `config.weekly.json` đăng ký chín mô hình trước khi fit: tổng 7 ngày trước, moving average 28/90 ngày nhân 7, weighted median tổng tuần lịch sử 90/365 ngày và bốn LightGBM trực tiếp. LightGBM pooled có nhận diện tuyến/khối tuần; mô hình được chọn riêng từng tuyến.
- Feature chỉ gồm lịch đã biết và lịch sử tại origin: tổng 7/14/28/90 ngày, tuần trước, độ biến động, tỷ lệ ngày dương, số đơn và basket. Chuẩn hóa ratio bằng mean90×7 tại origin, trả forecast về quantity. Không dùng đơn hoặc tín hiệu trong tuần tương lai.
- Nhãn học phải có **ngày cuối tuần ≤cutoff**; refit mỗi 7 ngày. Chọn bằng MAPE tổng tuần dương của validation, rồi MAE, rồi tên mô hình; full coverage bắt buộc. Selection được lưu/hash trước tổng hợp/chấm test.
- Cửa sổ không đủ bảy ngày trong split không chấm thành tuần đủ. Thiếu ngày/NaN/quantity âm bị chặn. Tuần actual bằng 0 vẫn giữ cho MAE/WAPE/bias và đếm zero; MAPE dương không có mẫu số 0.
- Báo cáo cả chạy mỗi ngày (cửa sổ chồng lấn) và chạy mỗi 7 ngày (cửa sổ không chồng lấn của cùng khối). Không coi 86 cửa sổ chồng lấn như 86 tuần độc lập; lịch tuần neo vào đầu split, không chọn ngày neo sau xem kết quả.
- Phân bổ về ngày bằng tỷ trọng weekday của 90 ngày quá khứ, fallback đều nếu lịch sử bằng 0. Tổng bảy phần giữ đúng tổng tuần. Đây là phân bổ cho bước tích hợp tồn, chưa tự thay thế pipeline tồn hoặc chứng minh dự báo ngày đạt.

## Kết quả thực chạy E36

Run `outputs/sigma_weekly_v1/`, Python 3.14.7/seed42, cùng raw hash của v11. Chín mô hình chấm validation; lựa chọn riêng 46 tuyến khóa trước test. Test đã được xem trong nghiên cứu ngày trước đây, nên kết quả này là đánh giá hồi cứu, **chưa phải kiểm định độc lập mới**.

| Phép đánh giá top 10, khối ngày 1–7 | Kết quả |
|---|---|
| Validation, chọn theo tổng tuần, chạy mỗi ngày | 8/10 ≤20%; MAPE 12,93–20,41% |
| Test hồi cứu, chạy mỗi ngày | **9/10 ≤20%**, MAPE 13,42–22,14%, mean tuyến **17,19%** |
| Test hồi cứu, chạy mỗi 7 ngày | **9/10 ≤20%**; AIS 24,59% |
| Coverage của các cửa sổ đủ tuần | 100%; h1–7 có 86 cặp/tuyến chạy mỗi ngày hoặc 13 cặp chạy mỗi 7 ngày |
| Khối ngày 8–14 | Báo riêng trong CSV/dashboard; không gộp vào kết quả h1–7 |
| Forecast tương lai | 92 tổng tuần =46 tuyến×2 khối; 644 phần ngày, actual chưa có để trống |

| Tuyến chưa đạt test tuần h1–7 | Mô hình đã khóa | MAPE chạy mỗi ngày |
|---|---|---|
| Thailand · AIS | week_lgbm_l1_ratio | **22,14%** |

So sánh cùng 86 cửa sổ/tuyến trên test, mean MAPE tuần của top 10: mô hình trực tiếp **17,19%**, cộng dự báo ngày v11 **29,90%**, naive ngày cộng tuần **40,37%**, MA7 ngày cộng tuần **19,18%**, MA28 ngày cộng tuần **18,09%**. Các số này đều là metric tổng tuần; không so trực tiếp với MAPE từng ngày 41,89–58,13% để nhận cải thiện cùng một tiêu chí.

Đối soát độc lập `outputs/sigma_weekly_verification_v2/`: 75.900 cặp dự báo validation/test khớp nhãn raw→quantity→UTC→tổng tuần, đủ từng tuyến/mô hình/khối/origin; metric tính tay khớp, fit label≤cutoff, selection đúng validation; nguồn và 59 sealed files v11 nguyên. Phân bổ 644 ngày bảo toàn từng tuần và không đọc tương lai. Chẩn đoán phân bổ ngày trên **các cửa sổ đủ tuần** có mean MAPE ngày top 10 51,11% (41,30–71,06%), cho thấy metric tuần tốt chưa đủ bảo đảm từng ngày. Đây chưa phải lưới nghiệm thu ngày R05 đầy đủ.

125 tests toàn suite đạt, gồm tính tổng độc lập, future-mutation, thiếu ngày/nhãn âm, zero-week metric, conservation, tamper/path traversal. AppTest run thật có 4 tab/6 bảng, không exception, kiểm cả Thailand/AIS, khối 8–14 và lịch mỗi 7 ngày. Không đổi hoặc tạo lại Word/slide M2 trong lượt này.

## Phạm vi nghiệm thu

Người dùng đã cho phép **làm phương án dự báo tổng 7 ngày**. Ảnh kickoff vẫn nói theo ngày; chưa có xác nhận mentor cho phép thay phép chấm ngày bằng phép chấm tổng tuần. Vì vậy R05 ngày vẫn mở; R05 tuần cũng còn AIS chưa đạt. Cảnh báo trước ≥7 ngày cần chuỗi phân bổ/kiểm replay riêng và không tự nhận đạt từ MAPE tuần.

Tiếp theo: phân tích độ ổn định validation của mô hình tuần và thử giả thuyết mới trước chấm; giữ AIS là ca chưa đạt, không chọn lại dựa trên test. Tích hợp và kiểm chính sách tồn từ phân bổ tuần trước khi thay đường chạy tồn; lịch cập nhật local còn cần hoàn thiện. Chưa đóng T14.
