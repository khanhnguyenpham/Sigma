# Lịch sử trước CHG-027 — không dùng làm hướng dẫn hiện hành

# Dự báo tổng quantity bán trong 7 ngày

**Hiện hành E38 ngày 05/10/2026:** `sigma_weekly_calibrated_v5`, 30 ứng viên đăng ký trước fit, validation 9/10 và test hồi cứu 9/10; mean test **15,97%**, LG U+ **21,36%** còn chưa đạt. `config.weekly-calibrated.json` là cấu hình đang dùng trong sản phẩm chung. V1/E36 bên dưới giữ lịch sử, AIS không còn là tuyến test chưa đạt của V5. [Sản phẩm, D+7 và job](../customer-delivery.md); R05 ngày chưa đổi.

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

Người dùng đã cho phép **làm phương án dự báo tổng 7 ngày**. Ảnh kickoff vẫn nói theo ngày; chưa có xác nhận mentor cho phép thay phép chấm ngày bằng phép chấm tổng tuần. Vì vậy R05 ngày vẫn mở; Tại E36/V1, R05 tuần còn AIS chưa đạt; hiện V5 còn LG U+. Cảnh báo trước ≥7 ngày cần chuỗi phân bổ/kiểm replay riêng và không tự nhận đạt từ MAPE tuần.

Bước tiếp tại E36/V1 (lịch sử): phân tích độ ổn định validation của mô hình tuần và thử giả thuyết mới trước chấm; giữ AIS là ca chưa đạt, không chọn lại dựa trên test. Tích hợp và kiểm chính sách tồn từ phân bổ tuần trước khi thay đường chạy tồn; lịch cập nhật local còn cần hoàn thiện. Chưa đóng T14.


## Nghiên cứu mở rộng V2–V5 và bằng chứng E38

V2 thêm lịch sử cùng kỳ năm trước theo DateOffset năm (xử lý năm nhuận), tuần cũ và mean 28/90 centered quanh ngày **quá khứ**, đầu ra ratio giữ quantity. V3 thêm ba phối hợp cố định 25/50/75% đã đăng ký; V4 thêm lịch sử quốc gia/toàn tuyến và tỷ trọng route causal. V5 thêm 12 head: ba parent × lịch sử 28/56 ngày × identity prior 0/4 tuần. Teacher fit nhãn≤origin dự báo quá khứ; head chỉ dùng tuần có ngày cuối≤head cutoff, không chồng lấn trong cùng block. Factor là weighted median y/p với trọng số p/y, identity prior, giới hạn 0,5–1,5. Zero tuần giữ trong metric; nếu lịch sử không đủ điều kiện tính hệ số thì dùng 1. Refit 7 ngày và lựa chọn mỗi tuyến bằng validation không đổi.

| Run | Ứng viên | Mean MAPE test tuần top10 | Tuyến test chưa đạt |
|---|---:|---:|---|
| sigma_weekly_v1 | 9 | 17,19% | AIS 22,14% |
| sigma_weekly_annual_v2 | 12 | 16,09% | LG U+ 21,08% |
| sigma_weekly_blend_v3 | 15 | 16,18% | LG U+ 21,08% |
| sigma_weekly_macro_v4 | 18 | 16,00% | LG U+ 21,08% |
| sigma_weekly_calibrated_v5 | 30 | 15,97% | LG U+ 21,36% |

V5 được dùng vì validation mean 15,4065% tốt hơn V4 15,4409%, không chọn phiên bản theo test. Không đổi LG U+ về một mô hình cũ chỉ vì mô hình cũ đạt test. Lịch không chồng lấn V5 vẫn 9/10, LG U+ 21,03%. Kiểm độc lập raw/coverage/metric của V5 đối soát 235.290 cặp; replay teacher và công thức head độc lập kiểm 27.876 hệ số, 136.620 cặp validation của 18 ứng viên V4 giữ nguyên tại dung sai 1e−8. Raw và 59 tệp sealed v11 nguyên. Test vẫn đã xem, không holdout độc lập.

Lệnh tạo run mới (không ghi đè các run đã seal):

```powershell
.\.venv\Scripts\python.exe weekly_forecast.py --config config.weekly-calibrated.json --run-id weekly_new
.\.venv\Scripts\python.exe verify_weekly.py --run-id weekly_new --output-id weekly_new_verify
.\.venv\Scripts\python.exe verify_weekly_calibration.py --run-id weekly_new --output-id weekly_head_verify
```

Phần “so sánh cùng cửa sổ” E36 là đối soát nghiên cứu lịch sử. Bản so sánh chính thức theo CHG-025 và tổ chức lại code chỉ thực hiện sau khi đủ điều kiện nghiệm thu; không nhận hai việc đó đã xong từ các CSV kiểm chứng.
