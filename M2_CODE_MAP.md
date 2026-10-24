# Bản đồ code M2 final — chuẩn bị báo cáo 16/10/2026

**CHG-068 bước4:** nhánh `m3-implementation` đã gỡ dashboard/launcher/dependency Streamlit; CLI/notebook/HTML và mô hình được giữ. Các số kiểm E73 phía dưới là lịch sử, không phải kết quả mới.

Bản dọn trên `M2-final-cleanup` chỉ chạy bộ final đã chốt: **10 lựa chọn theo tuyến, 7 cấu hình khác nhau**. LightGBM học **pooled trên toàn bộ top 10 train**, kể cả khi chỉ xuất kết quả cho một tuyến; Prophet học riêng au (KDDI). Không tìm lại model hoặc thay feature, loss, cửa sổ, lịch refit và metric.

Chín tuyến giữ lựa chọn validation; LG U+ chọn sau test-sweep. Kết quả tổng D+1…D+7 là 10/10 dưới 20%, mean 15,745366%, coverage 100% trên test hồi cứu. H8–14 có 8/10; R05 ngày/R07/T14 còn mở. Nguồn là snapshot trạng thái cuối, A08 vẫn là phương án thực nghiệm, không phải xác nhận mentor hoặc quy tắc kế toán.

## Cấu trúc còn chạy

```text
src/
  common.py                 cấu hình, hash, manifest và ghi đầu ra an toàn
  data.py                   audit order, chuỗi ngày, top 10 train
  evaluation.py             công thức metric quantity
M2/
  final_report.py           CLI chung: fit/refit, forecast, verify, export
  models/
    weekly.py               feature, nhãn tổng 7, fit pooled, predict batch
    LightGBM/model.py       chạy 5 cấu hình dùng cho 8 tuyến
    LightGBM/variants.json  đúng 5 spec gốc cần thiết
    focus.py                LG U+: cấu hình pooled thứ 6 và đầu nhân
    calibration.py          weighted median cho đầu nhân LG U+
    Prophet/model.py        fit và predict riêng au (KDDI)
    Prophet/variants.json   đúng spec annual3/weekly/window540
    families.py            replay Prophet, metric theo block/cadence/tháng
    common.py              nhãn trượt 7 cho Prophet, schema forecast
    registry.py            nạp 2 họ và cấu hình; hash implementation
    verify.py              tính độc lập nhãn và metric
    tests/test_final_report.py
  notebooks/final_report.ipynb
  artifacts/                giữ nguyên mọi run/forecast/manifest cũ, riêng tư
  reports/                  giữ nguyên báo cáo và bằng chứng nghiên cứu
data/configs/
  config.json               nguồn, target UTC, split, seed, ngưỡng metric
  m2-final.json             10 lựa chọn cố định, override LG U+, nguồn đối chiếu
  m2-reproduce.json         tham số dùng chung, dẫn tới 2 variants.json
tests/                      audit, metric, feature/leakage, parity và CLI
  fixtures/m2_final_parity.csv  300 forecast chuẩn từ dữ liệu giả trước dọn
requirements.txt            phiên bản cũ của các dependency còn dùng
```

`M2/models/SARIMA/README.md` chỉ giữ tài liệu giải thích nghiên cứu cũ. Không còn implementation SARIMA trong nhánh này. Không có thư mục archive chứa code bị loại.

## 10 tuyến → cấu hình → chỗ mở code

| Tuyến | Cấu hình final | File/hàm thực thi | Cửa sổ học / mức bán nền |
|---|---|---|---|
| Thailand / dtac | `lgbm_annual_ratio7` | [LightGBM/model.py](M2/models/LightGBM/model.py) `phase` → [weekly.py](M2/models/weekly.py) `fit`, `inputs`, `predict_batch` | 365 / 90 ngày |
| South Korea / LG U+ | `tune56_w540_mul56p4` | [focus.py](M2/models/focus.py) `prepare_parent`, `phase`, `verify_heads`; [calibration.py](M2/models/calibration.py) `relative_factor` | 540 / 56; đầu nhân lịch sử 56 ngày, prior 4 tuần |
| South Korea / KT | `lgbm_weighted_l1` | `LightGBM.model.phase` → `weekly.fit` | 365 / không chia tỷ lệ |
| Thailand / AIS | `lgbm_annual_ratio7` | `LightGBM.model.phase` → `weekly.fit` | 365 / 90 |
| Japan / au (KDDI) | `prophet_annual3_weekly_w540` | [families.py](M2/models/families.py) `ts_job` → [Prophet/model.py](M2/models/Prophet/model.py) `fit`, `update`, `predict` | 540 / không chia tỷ lệ |
| South Korea / SKT | `lgbm_poisson` | `LightGBM.model.phase` → `weekly.fit` | 365 / không chia tỷ lệ |
| Thailand / TrueMove H | `lgbm_annual_l1_15_min50` | `LightGBM.model.phase` → `weekly.fit` | 365 / không chia tỷ lệ |
| Japan / NTT Docomo | `lgbm_annual_ratio7` | `LightGBM.model.phase` → `weekly.fit` | 365 / 90 |
| Japan / SoftBank | `lgbm_weighted_l1` | `LightGBM.model.phase` → `weekly.fit` | 365 / không chia tỷ lệ |
| China / China Mobile | `lgbm_annual_l1_15` | `LightGBM.model.phase` → `weekly.fit` | 365 / không chia tỷ lệ |

Đọc [m2-final.json](data/configs/m2-final.json) để biết tuyến chọn gì. Đọc [m2-reproduce.json](data/configs/m2-reproduce.json) và [LightGBM variants](M2/models/LightGBM/variants.json)/[Prophet variants](M2/models/Prophet/variants.json) để biết tham số. Tên `m2-reproduce.json` được giữ để giảm thay đường dẫn; file này nay chỉ còn hai họ final. [final_report.configurations](M2/final_report.py) ghép các tham số thành bảng hiệu lực 10 tuyến.

LightGBM: 150 cây, learning rate 0,03, lambda 10, seed 42. Weighted L1 dùng trọng số 1/y trên y dương, y=0 có trọng số 0; Poisson dùng trọng số 1. Leaves 7 cho ratio/weighted/Poisson, leaves 15 cho hai cấu hình annual L1; min child 100, riêng TrueMove H là 50. LG U+ dùng spec annual ratio rồi override scale 56 và train 540. Prophet: additive, yearly Fourier 3, weekly bật, changepoint prior 0,01, 10 changepoints, uncertainty samples 0, seed 42.

## Khi được hỏi luồng tính toán

| Nội dung | File/hàm | Giải thích ngắn |
|---|---|---|
| Đọc/làm sạch | [src/data.py](src/data.py) `audit_orders` | Kiểm schema/quantity/UTC, dedup ở bản dẫn xuất có audit, không sửa CSV gốc hoặc dùng activation lọc sale |
| Tổng hợp | `daily_sales` | Cộng quantity success theo ngày đặt UTC và tuyến; ngày mất nguồn khác ngày 0 |
| Top 10 | `route_top` | Chỉ tổng quantity trong train đến 30/06/2025; không xếp hạng bằng test |
| Feature LightGBM | [weekly.py](M2/models/weekly.py) `prepare`, `inputs` | Route/block/lịch, tổng bán 7/14/28/90, tuần trước, std28, tỷ lệ ngày dương, orders28/basket28; bản annual thêm cùng kỳ năm trước |
| Nhãn và cửa sổ học | `prepare`, `fit` | Nhãn là tổng 7 ngày kết thúc tại `ends`; chỉ lấy `ends ≤ cutoff` và trong 365/540 ngày cuối |
| Nhãn Prophet | [common.py](M2/models/common.py) `target_history` | Chuỗi tổng trượt 7 được gắn ngày kết thúc, cắt 540 nhãn gần nhất đã hoàn tất |
| Refit và forecast | [final_report.py](M2/final_report.py) `replay`; `LightGBM.model.phase`, `focus.phase`, `families.ts_job` | Fit tại origin đầu split rồi mỗi 7 origin; cập nhật feature theo actual đã quan sát, giữ hệ số giữa các lần refit |
| Đầu nhân LG U+ | `focus.phase`, `calibration.relative_factor` | Teacher pooled fit tại origin quá khứ; chỉ dùng cặp đã đủ nhãn ở cutoff; weighted median có prior tại 1, clip hệ số [0,5; 1,5] |
| Metric | [src/evaluation.py](src/evaluation.py) `score`; `families.metrics`, `monthly_metrics` | MAPE chỉ actual dương; MAE/WAPE/bias dùng mọi cặp có nhãn; coverage và nhịp origin được báo riêng |
| Đối soát | [verify.py](M2/models/verify.py) `reconcile_labels`, `reconcile_metrics`; `final_report.verify_run` | Tính lại từ raw/daily/forecast, kiểm đủ cặp, causal fitlog, hash và parity với run cha |
| Báo cáo | `final_report.export_report`, `load_report` và notebook final | Export sang thư mục mới; HTML/notebook chỉ đọc bảng aggregate đã kiểm hash |

**Ba khoảng thời gian khác nhau:**

- **Cửa sổ học 365/540 ngày** giới hạn *ngày kết thúc nhãn*, không phải chỉ số dòng raw. Ở cutoff 30/06/2025, cửa sổ 365 bắt đầu 01/07/2024. Feature có thể đọc lịch sử sớm hơn để tạo mẫu trong cửa sổ này.
- **Mức bán nền 90/56 ngày** là `max(1, mean(quantity/ngày trong N ngày đến origin) × 7)`. Ratio chia feature lượng bán và nhãn cho mức nền rồi nhân forecast trở lại quantity. Đây không phải cửa sổ học. LG U+ tính mức nền 56 bằng `prepare_parent`.
- **Cửa sổ forecast 7 ngày** là D+1…D+7 hoặc D+8…D+14. LightGBM học trực tiếp hai block; Prophet dự báo chuỗi tổng trượt rồi lấy ngày kết thúc D+7/D+14. Refit 7 ngày và lịch sử đầu nhân 56 ngày là hai khái niệm khác nữa.

Code hiện hữu fit model trong bộ nhớ rồi lưu forecast, cấu hình, log và manifest. Manifest final không có trọng số model serialize để load; lượt dọn không bổ sung cơ chế lưu/nạp mới. Mọi artifact/trọng số có sẵn trong workspace được giữ nguyên. Dự báo `future` của nguồn này là 01–14/01/2026 vì nguồn dừng 31/12/2025, không phải tuần báo cáo tháng 10/2026.

## Lệnh dùng tại root project

Trên nhánh `m3-implementation`, dashboard/launcher Streamlit đã gỡ ở CHG-068 bước4. Dùng HTML offline hoặc notebook đọc cùng `load_report`; CLI giữ nguyên, không tự train khi mở React/báo cáo.

```powershell
.\.venv-m3\Scripts\python.exe -m M2.final_report --help
.\.venv-m3\Scripts\python.exe -m M2.final_report --run-id m2_final_20261011_local --stage verify-artifacts
```

`verify-artifacts` cần artifact local gốc, không refit/ghi đè receipt cũ. Nó kiểm bằng chứng lịch sử, không nhận code hiện tại khớp source cũ. [Notebook](M2/notebooks/final_report.ipynb) dùng chung hàm đọc; [HTML final](M2/reports/final_m2_20261011/index.html) mở offline.

Nếu chủ động cần tái huấn luyện, dùng run-id/report-id mới:

```powershell
.\.venv-m3\Scripts\python.exe -m M2.final_report --run-id m2_final_new --stage run
.\.venv-m3\Scripts\python.exe -m M2.final_report --run-id m2_final_new --stage verify
.\.venv-m3\Scripts\python.exe -m M2.final_report --run-id m2_final_new --stage export --report-id m2_final_new
```

Run mới dùng raw/artifact cha đã khóa, giữ model/feature/refit và manifest riêng. Không chạy refit trong lượt gỡ Streamlit. Bằng chứng E73 phía dưới là lịch sử; kiểm mới ghi CHG-068. Lệnh dashboard trong báo cáo cũ chỉ áp dụng source cũ.

## Bằng chứng được bảo toàn

- [Final report 11/10](M2/reports/final_m2_20261011/README.md), [cấu hình hiệu lực](M2/reports/final_m2_20261011/model_configurations.json), [metric test](M2/reports/final_m2_20261011/test_metrics.csv), [report manifest](M2/reports/final_m2_20261011/report_manifest.json).
- Run riêng tư `M2/artifacts/m2_final_20261011_local`: daily, top_routes, selection_lock, validation/test/future forecast, fitlog, metric và manifest. SHA manifest: `7be713a8389d487bb4d9f7aa70df45896c98d933549d722bd0136052a18e0976`.
- Báo cáo nghiên cứu, mọi run cũ, bản published 07/10, Word/PDF và [tài liệu học](M2/reports/mentor_prep_20261014/README.md) vẫn giữ byte gốc. Lệnh và link code trong báo cáo cũ mô tả phiên bản trước dọn; dùng nhánh backup để xem/chạy lại chúng.

## Khôi phục code cũ

Nhánh gốc `M2-final-report` ở `b1415289614a9793c6ff4a6ee1e350fc0a49014c`. Nhánh `backup/m2-before-cleanup` ở checkpoint `5271d0b9d0411506f1a22ada9c2fe337be00ec84` đã lưu bốn tài liệu người dùng đang sửa. Nhánh cleanup bắt đầu từ checkpoint này; người dùng cho phép push nhánh M2-final-cleanup ngày14/10/2026; không merge/deploy hoặc xóa backup.

```powershell
git diff --stat backup/m2-before-cleanup..M2-final-cleanup
git diff backup/m2-before-cleanup..M2-final-cleanup -- M2/final_report.py
git show backup/m2-before-cleanup:src/models.py
# Lấy từng file; lưu chỉnh sửa hiện tại của file đó trước nếu có.
git restore --source=backup/m2-before-cleanup -- src/models.py
# Chạy lại cả luồng M1/M3/sweep cũ cần checkout backup đầy đủ cùng dependency cũ.
```

Bản sao ngoài codebase: `C:\Users\Admin\OneDrive\Desktop\WorksSpace\SIGMA-m2-backup-20261014`. `local-untracked-and-private.zip` chứa 466 tệp local/ignored (gồm công cụ trong tmp và tài liệu học/Word), `tracked-working-tree.zip` giữ byte tệp tracked trước dọn, `user-working-tree.patch` lưu thay đổi tài liệu đã checkpoint, `before.json` ghi hash 960 tệp dữ liệu/bằng chứng. Không sao lưu môi trường ảo, cache hoặc secrets. Không cần đưa dữ liệu lớn vào Git để khôi phục code.

## Kiểm tra trực tiếp lượt dọn

Ngày 14/10/2026, Python local **3.12.14**: **32 tests đạt**, gồm AppTest ba tab/bộ lọc, export vào thư mục mới/từ chối ghi đè, metric tính tay, nguồn/activation/dedup/UTC/missing, leakage, 7.300 nhãn fit pooled tại cutoff, Prophet rolling7/window540, đầu nhân và manifest. Fixture giả có 300 forecast/10 tuyến/7 cấu hình/ba lần refit khớp trước dọn **chênh tối đa 0**. Bảng tham số hiệu lực và từng spec còn giữ khớp bản backup.

`verify-artifacts` kiểm 3.700 forecast, 80 nhóm metric, 58 đầu hiệu chỉnh; parity với run cha không đổi. **960 tệp raw/dữ liệu/báo cáo/artifact giữ hash**. `pip check`, import nội bộ, parse Python/PowerShell, notebook không lưu output và kiểm link/anchor/bảng/fence tài liệu đạt trong phạm vi sửa; không tạo liên kết lỗi mới. Các nguồn thiếu/link lịch sử đã thiếu trước lượt này vẫn được ghi rõ trong review-log.

Code tracked `.py/.ps1/.ipynb` giảm **193 → 28 tệp**; xóa 244 tệp gồm 205 tracked và 39 công cụ `.py` ignored trong tmp. Dependency bỏ: statsmodels, patsy, formulaic, interface_meta, wrapt; 83 phiên bản còn lại giữ nguyên, gồm dependency trực tiếp và dependency bắc cầu theo metadata cài local. Không gỡ package khỏi môi trường hiện có.

Không chạy lại full training trên raw, sweep, CI hoặc cài môi trường sạch trong lượt dọn. Lệnh refit thật được truy vết và các thành phần được chạy bằng fixture; chưa nhận đã tái huấn luyện full final sau dọn. Kiểm artifact lịch sử không xác nhận source hiện tại giống source cũ; không sửa manifest/receipt khóa để làm khớp hash. Prophet có thông báo thiếu Plotly tùy chọn và AppTest có cảnh báo context bare mode; các checks vẫn đạt, không thêm dependency để tắt thông báo.
