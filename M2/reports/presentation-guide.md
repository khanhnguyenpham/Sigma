# Báo cáo M2 ngày 07/10/2026

Nhánh làm việc: `codex/m2-report-20261007`. Dùng kết quả đã khóa **9/10 tuyến tổng 7 đạt ≤20%, MAPE trung bình 15,89%**, độ phủ100%. **LG U+20,69% chưa đạt, hoãn tối ưu** theo quyết định người dùng. Ngày0/10, R05 còn mở; test là hồi cứu.

## Đọc báo cáo từ GitHub

[Báo cáo M2 và bảng kết quả](published_m2_20261007/README.md) đọc được ngay trên GitHub, không cần dữ liệu gốc hoặc train lại. [Bản HTML offline](published_m2_20261007/index.html) tải về và mở bằng trình duyệt. Đây là bản tổng hợp được người dùng yêu cầu xuất bản; raw và artifact run vẫn giữ local.

## Mở báo cáo trên máy hiện tại

Từ thư mục gốc repo:

```powershell
.\scripts\start_m2.ps1
```

Mở `http://127.0.0.1:8505`. Có ba phần dữ liệu, mô hình/phương pháp và kết quả từng tuyến, cùng bảng tháng7–8–9 và tải CSV. Dashboard đọc run đã seal; thiếu/sai hash dừng và không train khi báo cáo.

Bản offline local: `M2/reports/m2_report_20261007/index.html`, mở bằng trình duyệt, có biểu đồ nhúng nên không cần server. Các CSV và checkpoint nằm cùng thư mục. Bản HTML chứa kết quả tổng hợp riêng tư, giữ local như các artifact.

Lệnh tạo bộ này lần đầu:

```powershell
.venv\Scripts\python.exe -m M2.presentation
```

Lệnh từ chối ghi đè bộ đã có. Clone mới có mã/cấu hình/hướng dẫn và báo cáo tổng hợp offline; cần người có quyền cung cấp raw và bộ run local đã khóa để mở cùng báo cáo. Không train lại trước buổi trình bày chỉ để tạo bản giống.

## Trình bày 7–10 phút

1. **Dữ liệu (1–2 phút):** snapshot order người dùng mô tả là giả định; quantity success theo ngày đặt UTC, không activation. Top10 lấy từ train; giải thích train/validation/test và giữ raw nguyên.
2. **Phương pháp (2 phút):** ba họ LightGBM/SARIMA/Prophet,26 biến thể/50 cấu hình. Phân biệt dự báo từng ngày rồi cộng với trực tiếp tổng7; SARIMA/Prophet dùng S(D+7), không lấy S(D+1). H14, refit7, chỉ dùng nhãn hoàn tất tại cutoff.
3. **Chọn mô hình (1–2 phút):** mỗi tuyến chọn bằng validation rồi khóa trước test. LightGBM cho9 tuyến, Prophet cho au(KDDI); SARIMA là đối chứng. Không chọn mô hình bằng kết quả test.
4. **Kết quả (2 phút):** tổng7 đạt9/10,15,89%, độ phủ100%. Cho thấy LG U+20,69% trong bảng, không bỏ tuyến. Ngày0/10 chưa đạt R05. Tháng9 validation tổng7 yếu hơn tháng7–8.
5. **Kiểm chứng và bước sau (1 phút):** đối soát401.600 dòng/9.160 nhóm metric, kiểm nhãn/cutoff/khóa. Giữ LG U+ để tối ưu sau; không cam kết10/10 hoặc thay nghiệm thu ngày bằng tuần.

## Tuyến và mô hình tổng 7 đã khóa

| Tuyến | Họ | Biến thể | MAPE test |
|---|---|---|---:|
| China / China Mobile | LightGBM | lgbm_annual_l1_15 | 19,73% |
| Japan / NTT Docomo | LightGBM | lgbm_annual_ratio7 | 17,00% |
| Japan / SoftBank | LightGBM | lgbm_weighted_l1 | 15,36% |
| Japan / au (KDDI) | Prophet | prophet_annual3_weekly_w540 | 17,87% |
| South Korea / KT | LightGBM | lgbm_weighted_l1 | 13,69% |
| South Korea / LG U+ | LightGBM | lgbm_cal_ratio7_56_p4 | **20,69% — chưa đạt** |
| South Korea / SKT | LightGBM | lgbm_poisson | 13,88% |
| Thailand / AIS | LightGBM | lgbm_annual_ratio7 | 12,67% |
| Thailand / TrueMove H | LightGBM | lgbm_annual_l1_15_min50 | 16,46% |
| Thailand / dtac | LightGBM | lgbm_annual_ratio7 | 11,53% |

## Tệp cần mở khi được hỏi

- [Cấu trúc M2](../README.md), [mã/biến thể](../models/README.md).
- `data/configs/config.json`: target/split/horizon/seed dùng chung; config lịch sử và cấu hình tuần ở cùng data/configs. Các tên config cũ trong bundle lịch sử được resolver đọc từ vị trí mới, không sửa bundle đã khóa.
- `data/training/m2_report_20261007`: daily_sales/top_routes/audit và ba bảng split top10. Train kết thúc30/06/2025, validation07–09/2025, test10–12/2025; không dùng validation/test làm nhãn train trước cutoff.
- `M2/artifacts/m2_improved_models_20261006_fixed`: dự báo, metric, fit logs và khóa lựa chọn theo từng họ/mục tiêu; manifest SHA `6407c68e9f520da51924fb021a275a947ada9cca15fbde06f35287218f3561dc`.
- `M2/reports/m2_report_20261007`: HTML, bảng mô hình ngày/tổng7, metric tháng và checkpoint.
- [Báo cáo cải tiến và so sánh hai phương pháp](published_m2_20261007/README.md).

Snapshot source theo SHA phục vụ kiểm run lịch sử; đợt clean không đổi forecast/selection/metric/raw. Sản phẩm46 tuyến/tồn/cảnh báo V13 vẫn có launcher riêng trong scripts. Báo cáo này là M2 nghiên cứu top10.
