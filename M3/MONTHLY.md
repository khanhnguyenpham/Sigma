# Tổng 30 ngày — tiêu chí R05 hiện hành

Ngày 20/10/2026, người dùng thuật lại mentor **đã chốt chấm tổng 30 ngày thay cho từng ngày** (M05, CHG-061). Đây là nguồn xác nhận qua người dùng; chưa có biên bản mentor độc lập. Ngưỡng vẫn là MAPE ≤20% cho **từng tuyến top 10**, xếp theo quantity train. Không đổi raw, target, split hoặc tuyến để đạt ngưỡng.

## Kết quả đã đối soát

Run nguồn `sigma_aggregate_focus_20261018` được kiểm lại ngày 20/10 giờ Việt Nam bằng verifier gốc, sau đó đối chiếu **33.626 route-day** với PostgreSQL M3, tính lại nhãn và metric. Không fit hoặc chọn lại mô hình trong bước tích hợp này.

| Phương pháp tổng 30 | MAPE trung bình top 10 (%) | Số tuyến ≤20% |
|---|---:|---:|
| Naive: lượng ngày cuối ×30 | 37,871734 | 0/10 |
| MA7: trung bình 7 ngày ×30 | 18,287797 | 5/10 |
| MA28: trung bình 28 ngày ×30 | 17,403218 | 7/10 |
| Mô hình đã chọn | 11,621356 | 10/10 |

Mỗi tuyến có **63 cửa sổ test đủ nhãn, coverage 100%**. Cửa sổ D+1…D+30, không phải tháng dương lịch. Origin test đầy đủ từ 30/09 đến 01/12/2025; các origin sau đó vẫn có dự báo nhưng không tham gia metric test. Cửa sổ chồng nhau nên không phải 63 mẫu độc lập. MAE/WAPE/bias dùng cả actual 0; MAPE chỉ dùng actual dương; chưa actual giữ null.

| Tuyến | Mô hình | MAPE tổng 30 (%) |
|---|---|---:|
| South Korea / LG U+ | lgbm_annual_ratio15 | 10,1097 |
| Thailand / dtac | lgbm_annual_ratio15 | 13,4787 |
| Japan / NTT Docomo | lgbm_annual_ratio7 | 4,3994 |
| Thailand / TrueMove H | lgbm_annual_ratio7 | 13,8363 |
| Japan / SoftBank | lgbm_poisson7 | 10,4075 |
| South Korea / KT | lgbm_poisson7 | 5,6851 |
| South Korea / SKT | lgbm_poisson7 | 7,0687 |
| Thailand / AIS | lgbm_ratio7 | 16,9873 |
| China / China Mobile | mix_lgbm_annual_ratio7_w25 | 18,6838 |
| Japan / au (KDDI) | prophet_annual3 | 15,5569 |

China Mobile phối 75% champion cũ và 25% LightGBM mùa vụ năm; trọng số chọn validation, khóa trước lượt test này. Hướng focus được xác định sau test cũ, nên **toàn bộ đánh giá là hồi cứu**, không phải holdout độc lập. Không dùng thay đổi M05 để xóa giới hạn này.

## Hai luồng trong sản phẩm

**Dự báo → Tổng 30 · R05:** đọc gói kết quả thật đã kiểm chứng, cùng SHA nguồn/target/observation_end với run đang chọn. Có dự báo 46 tuyến tại 185 origin, bảng sai số test từng tuyến, baseline, cadence không chồng để chẩn đoán, CSV và context. Mặc định chỉ top 10; bỏ chọn để xem 46 tuyến. Tổng kết 10/10 luôn là toàn bộ top 10, không phụ thuộc bộ lọc một kho. SKU/đối tác không áp dụng cho tổng theo tuyến.

**Vận hành → Tổng 7 / ngày, Tồn, Cảnh báo:** vẫn dùng forecast H14, phân bổ theo dữ liệu quá khứ và policy L7/R1. Không đưa tổng 30 vào cột tổng 7 hoặc thay forecast của các run tồn đã khóa. Tổng 30 không tự chứng minh chất lượng cảnh báo; R07 tiếp tục công bố replay, giả định và giới hạn riêng.

Gói tổng 30 là **benchmark chỉ đọc**, chưa phải worker huấn luyện tổng 30 cho mọi nguồn mới. Đổi nguồn/target/cấu hình nghiệm thu làm API từ chối gói cũ. Dự báo tương lai trong gói có origin 31/12/2025 và actual tháng 01/2026 null. Không nhận đã có doanh số hoặc dự báo mới thời gian thực năm 2026.

## Chuẩn bị gói local

Cần source import M3 hoàn tất và bản run nghiên cứu đầy đủ local. Git chỉ chứa source/tests/docs/config; không chứa CSV/run/env. Mã nghiên cứu gốc ở [nhánh codex/30day-m3](https://github.com/khanhnguyenpham/Sigma/tree/codex/30day-m3); đọc `docs/30day-m3.md` và `docs/aggregate-refinement.md` tại nhánh đó nếu cần tái lập. Không khôi phục các module đó vào mã M2 final của nhánh implementation.

`M3_SOURCE_ROOT` trỏ checkout nghiên cứu chứa raw nguồn bài tại `data/sigma_sim_data_orders.csv` và `outputs/sigma_aggregate_focus_20261018`. Dùng môi trường nghiên cứu để chạy verifier gốc, output basename mới bên ngoài run sealed, ví dụ:

```powershell
.\.venv\Scripts\python.exe -B -m sigma.verification.aggregate --run-id sigma_aggregate_focus_20261018 --output sigma_aggregate_focus_20261018_e93_20261020_verification.json
```

Tại checkout implementation, nạp env local, rồi thay UUID bằng source import của máy:

```powershell
. ./M3/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -B -m sigma_m3.cli prepare-monthly --source-run 96e77f53-fa7c-46be-987f-50e308920dba --verification-receipt sigma_aggregate_focus_20261018_e93_20261020_verification.json
```

CLI kiểm summary/file/module hashes, receipt, selection lock trước test, train top 10, dữ liệu DB, origin/cutoff, nhãn và metric; tạo thư mục bất biến tại thư mục anh em `monthly_benchmarks` cạnh `M3_OUTPUT_ROOT`, sau đó đổi pointer nguyên tử. Không ghi vào run cũ hoặc thêm bảng DB. HTTP không nhận đường dẫn tệp và không gọi huấn luyện. Mỗi response kiểm checksum của manifest/config và ba CSV từ cùng byte đã đọc. Lỗi checksum trả 409, không hiển thị điểm cũ như hợp lệ.

Gói thực E93 có **8.510 forecast tổng 30**, **184 dòng metric** (46 tuyến ×2 split ×2 cadence). Gói ID `42dd7812e3b92ebddf781e9eaa0b0e2458e8f4dc764abce3db1c3888573940c0`; summary nguồn SHA `a8e90ec29ea154c34ac9d54fcf0a224767fe37a2435ab1ba0d57453359878c38`. Receipt kiểm gốc có trường `daily_R05_acceptance_replaced=false` theo tiêu chí lịch sử khi run tạo; giữ nguyên trường này. Cấu hình M05 hiện hành nằm trong [acceptance-30d.json](configs/acceptance-30d.json), không sửa ngược sealed run.

## API và mã liên quan

| Đường dẫn sau `/api/v1/runs/{run_id}` | Phạm vi |
|---|---|
| `/monthly-summary` | Toàn bộ top 10, baseline cùng 63 cửa sổ; từ chối filter để giữ mẫu số |
| `/monthly-forecasts` | Dự báo D+1…D+30; warehouse_id/as_of_date/split/top10_only và phân trang |
| `/monthly-metrics` | Toàn kỳ validation/test; warehouse_id/top10_only/cadence; không lọc metric theo origin |
| `/exports/monthly_forecasts` | CSV cùng filter forecast, đầy đủ dòng, không giới hạn theo trang UI |
| `/exports/monthly_metrics` | CSV cùng phạm vi metric và context checksum/nguồn/M05 |

Cadence chính `daily_origins`; chẩn đoán `nonoverlapping_30d` có 3 cửa sổ/tuyến. API từ chối item/supplier filter; dữ liệu thiếu gói trả `monthly_not_prepared`, gói lệch trả `monthly_invalid`. Run chưa complete hoặc parent không tương thích cũng bị chặn. CSV có BOM, escape chuỗi bắt đầu bằng ký tự công thức, null xuất ô trống.

Mã hiện hành sau bước6 CHG-068: [service](../web/backend/src/modules/reporting/monthly.py), [API](../web/backend/src/modules/reporting/monthly_router.py), [UI](frontend/src/components/MonthlyForecast.tsx), [test backend](../web/backend/tests/test_monthly.py), [test UI](frontend/tests/monthly.test.tsx). Hướng dẫn chạy stack tại [README root](../README.md).

R05 **đạt ngưỡng số học theo M05 trên bộ test hồi cứu**. Nghiệm thu toàn bài/T14 còn cần mentor rà target A08, phạm vi mô phỏng, kết quả R07 và giới hạn holdout; không tự nhận đã được mentor ký duyệt.

E93 kiểm local: **97 Python / 11 frontend đạt**, Python không fail/error/skip; TypeScript/build, pip check và Ruff đạt. API dữ liệu nguồn kiểm 10 metric/63 cửa sổ, 46 tuyến, 3 cửa sổ không chồng, actual tương lai null, CSV một kho và snapshot cùng nguồn. Trình duyệt đã mở tab Tổng30, hiện 10/10, 11,62%, coverage100%; đổi top10/46 và ngày 31/12 cho cửa sổ 01–30/01/2026 actual trống. Ảnh và receipt giữ local, không đưa vào Git.
