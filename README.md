# SIGMA — Tổng 30 ngày và sản phẩm M3

**Bản dùng kết quả nguồn bài đã online:** [Mở SIGMA](https://sigma-demand-inventory.streamlit.app/) · app/repo Private; dùng Share để cấp quyền xem. [Phạm vi, bằng chứng và giới hạn](docs/portable-hosting.md). Bản online đọc release đã tính, chưa huấn luyện/cập nhật nguồn trên cloud; kết quả tổng30 vẫn9/10.

**Xem từ máy khác:** [Dashboard SIGMA online](https://sigma-demand-inventory.cuddly-grebe-5666.chatgpt.site) đã bật public, dùng hoàn toàn dữ liệu tự sinh 10 tuyến/13 kịch bản. [Phạm vi và cách trình diễn](docs/share-web.md); kết quả nguồn bài vẫn được giữ riêng local.

**Trình diễn mentor:** mở dashboard tại `http://127.0.0.1:8507/` và dùng [kịch bản demo 5–7 phút](docs/mentor-demo.md). Giao diện đã tổ chức theo nhu cầu → kho hàng → kịch bản → cảnh báo/giao khách → kiểm chứng; có minh họa từng SKU và xuất phiếu đề xuất nhập.

[Cập nhật sau bàn giao](docs/aggregate-refinement.md): thêm hướng xử lý tồn, so sánh kịch bản và giải thích cảnh báo; các thử nghiệm hiệu chỉnh/học ngắn giữ riêng, kết quả mặc định vẫn 9/10 tổng 30.

Đã kiểm tra phần Khang trên GitHub, hợp nhất `M2-final-report` vào nhánh local `codex/30day-m3`, giữ lại luồng M3. Mở sản phẩm:

```powershell
.\scripts\start_m3.ps1
```

Địa chỉ `http://127.0.0.1:8507`. Có 7 phần: tổng quan, dự báo 7/30, tồn/đặt hàng, cảnh báo, lịch giao D+7, biến động quantity/doanh thu, cập nhật/nguồn. [Hướng dẫn và kết quả](docs/30day-m3.md).

**Kết quả nguồn bài:** tổng 30 đạt **9/10**, MAPE trung bình **11,79%**, China Mobile **20,33%** chưa đạt; coverage 100%. M3 chạy 13 kịch bản/920 mặt hàng, đáp ứng cơ sở85,97%, báo trước≥7 ngày 1053/2867 sự kiện (36,73%). Đây là sản phẩm dùng snapshot lịch sử và tồn giả định; còn tiêu chí chưa đạt, không nghiệm thu toàn bài. Bộ final 7 của Khang giữ riêng, không bị thay bằng đối chứng7 mới.

Trên máy clone mới không có CSV riêng tư, chạy demo tự sinh:

```powershell
.\.venv\Scripts\python.exe -m sigma demo 30 --prefix demo_m3_team
.\scripts\start_m3.ps1 -Config outputs/demo_m3_team_bundle/product30.json
```

Demo ở cổng 8508 dùng 3 tuyến riêng; không chứng minh chất lượng nguồn bài. Mỗi lần tạo demo chọn prefix mới. Code/config/tests/tài liệu mới đang local; raw/run/ảnh/báo cáo riêng vẫn ignored, chưa push.

---

## SIGMA — M2 final

Nhánh `M2-final-report` · 11/10/2026. **10/10 tuyến đạt MAPE tổng quantity7 ngày test <20%, trung bình 15.745366%, coverage100%.** LG U+19,265900%; chín tuyến còn lại giữ cấu hình và tái lập dự báo cũ. Bộ gồm9 cấu hình LightGBM và1 Prophet.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.\scripts\start_m2.ps1
```

Mở http://127.0.0.1:8505. Dashboard đọc bảng tổng hợp đã kiểm hash, không cần raw để xem.

[Báo cáo final](M2/reports/final_m2_20261011/README.md) · [Cấu hình 10 mô hình](M2/reports/final_m2_20261011/model_configurations.md) · [HTML offline](M2/reports/final_m2_20261011/index.html) · [Lệnh tái chạy](M2/README.md).

Test hồi cứu: LG U+ được chọn qua test-sweep; chín tuyến giữ lựa chọn validation. Lượt mới kiểm tái lập trên cùng test. H8–14 LG U+ còn20,255792%; R05 theo ngày/R07/T14 vẫn mở. Bộ tồn/M3 giữ phạm vi riêng.

GitHub chỉ có mã, cấu hình, tài liệu và bảng tổng hợp được cho phép. Raw, chuỗi ngày, dự báo từng origin, draft Word/PDF và scratch giữ local. Báo cáo cũ và lịch sử thử nghiệm vẫn được bảo toàn.

<details>
<summary>Lịch sử và sản phẩm M2–M3 trước bộ final</summary>

Các số liệu và lệnh dưới đây ghi theo từng thời điểm. Launcher M2 mặc định nay mở final; muốn xem run cũ phải truyền `-RunId`.

## SIGMA — Báo cáo M2 ngày 07/10/2026

**Tái hiện local09/10/2026:** đã chạy lại26 biến thể/50 cấu hình từ CSV gốc;20 lựa chọn và90 kết quả từng họ/tuyến khớp báo cáo cũ. Tổng7:9/10,15,89%; ngày:0/10,46,74%; LG U+20,69% chưa đạt. [Báo cáo mới](M2/reports/m2_reproduce_20261009_full_review/README.md), [CSV đầu vào từng biến thể](data/training/m2_reproduce_20261009_full/README.md). Mở bằng `.\scripts\start_m2.ps1 -RunId m2_reproduce_20261009_full`. Raw/Word/báo cáo published giữ nguyên; run mới và CSV chỉ local, không push. Báo cáo07/10 bên dưới là bộ lịch sử đã xuất bản.

Nhánh này tập trung **M2: dữ liệu, ba họ mô hình, phương pháp dự báo và kết quả từng tuyến**.
Kết quả đã khóa: **tổng 7 đạt 9/10 tuyến, MAPE trung bình 15,89%**; LG U+ **20,69%**, để tối ưu sau.
Chọn LightGBM cho 9 tuyến và Prophet cho au (KDDI) bằng validation. Dự báo ngày 0/10; R05 vẫn chưa đạt. Test là đánh giá hồi cứu.

```powershell
.\scripts\start_m2.ps1
```

Mở `http://127.0.0.1:8505`; chỉ đọc bộ kết quả đã khóa, không train khi báo cáo.
[Bắt đầu từ M2](M2/README.md) · [Kịch bản trình bày](M2/reports/presentation-guide.md) · [Bản đồ thư mục](docs/code-map.md).
[Đọc báo cáo M2 trên GitHub](M2/reports/published_m2_20261007/README.md): dữ liệu tổng hợp, mô hình từng tuyến, hai phương pháp, kết quả và biểu đồ.
[Bản HTML offline](M2/reports/published_m2_20261007/index.html) có biểu đồ nhúng; tải về mở bằng trình duyệt.
Dữ liệu gốc và artifact train/forecast giữ local; báo cáo tổng hợp được đưa lên Git theo yêu cầu người dùng.


Sản phẩm Streamlit chạy local trên Windows. Menu gồm tổng quan, dự báo tổng 7 ngày, giao khách D+7, tồn từ dự báo tuần, so sánh ngày/tuần và phần dự báo ngày/tồn/cảnh báo. Mã được gom theo chức năng; bắt đầu từ [bản đồ mã](docs/code-map.md).

Thử nghiệm M2 theo ba họ **LightGBM / SARIMA / Prophet** được gom tại [M2](M2/README.md), gồm artifacts, models, notebooks và reports. Mỗi họ có kết quả ngày và trực tiếp tổng7; pool mới chọn bằng validation. Sản phẩm V13 bên dưới vẫn có phạm vi riêng.

**Sản phẩm V13 — chưa nghiệm thu toàn bài:** tuần đạt 9/10 top 10, LG U+ 21,19%; R05 ngày vẫn 0/10. Test đã từng được xem, là đánh giá hồi cứu. Giữ nguyên nguồn, target, split, top 10 và metric. [Bảng so sánh](docs/day-week-comparison.md) chấm các phương án trên cùng cửa sổ, giữ riêng tiêu chí ngày.

## Bản dùng báo cáo M2–M3

```powershell
.\scripts\start_m2m3.ps1
```

Mở `http://127.0.0.1:8504`, bộ run V13 đã khóa, bảng tình trạng HTML và bộ lọc SKU/loại. [Hướng dẫn demo 8–10 phút](docs/m2m3-demo.md). Thiếu/sai hash dừng, không đổi sang run khác. Clone mới dùng cấu hình demo được tự sinh/khóa.

## Mở sản phẩm trên máy hiện tại

```powershell
.\scripts\start_product.ps1
```

Mở `http://127.0.0.1:8503`. Bộ run chọn trong [config.delivery.json](data/configs/config.delivery.json). Dashboard đọc artifact đã seal; từ chối thiếu/sai hash và không tự huấn luyện khi mở. Dữ liệu/outputs giữ local.

## Cài và chạy demo trên máy mới

Áp dụng cho checkout của nhánh báo cáo được cung cấp hợp lệ. Nhánh GitHub dành cho báo cáo là `m2-forecast-report`; không gửi kèm raw/artifact trong gói mã.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m sigma demo --prefix demo_team
.\.venv\Scripts\python.exe -m sigma check-product --delivery-config outputs/demo_team_bundle/delivery.json --output-id demo_team_ui_qa
.\scripts\start_product.ps1 -DeliveryConfig outputs/demo_team_bundle/delivery.json
```

Đã kiểm môi trường Python 3.14.7/Windows 64-bit, phụ thuộc được khóa. Demo tự sinh ba tuyến riêng, tạo pipeline ngày/tuần, D+7, policy 13 kịch bản, snapshot đúng policy, so sánh và đối soát độc lập. Demo 3/3 không chứng minh top 10 của nguồn bài đạt. Dùng prefix mới, không ghi đè run.

GitHub có mã/config/fixture giả/notebook không output/tài liệu và bộ báo cáo M2 tổng hợp được cho phép trong `M2/reports/published_m2_20261007`. Chỉ CSV metric/lựa chọn tổng hợp của bộ này được chia sẻ; raw, train, outputs, run riêng tư, môi trường và job state giữ local. Nhánh báo cáo `m2-forecast-report`; nhánh sản phẩm `codex/sigma-local-pipeline`; [PR1](https://github.com/khanhnguyenpham/Sigma/pull/1) còn draft, chưa merge.

## Pipeline với CSV được cung cấp

Nguồn riêng tư `data/sigma_sim_data_orders.csv` không có trong clone; giữ nguyên byte và đọc [data-contract](docs/data-contract.md). Người dùng mô tả nguồn là giả định, chưa xác minh độc lập.

```powershell
.\.venv\Scripts\python.exe -m sigma daily --run-id day_new
.\.venv\Scripts\python.exe -m sigma weekly --config data/configs/weekly.json --run-id week_new
.\.venv\Scripts\python.exe -m sigma verify-weekly --run-id week_new --daily-run day_new --output-id week_new_verified
.\.venv\Scripts\python.exe -m sigma policy --weekly-run week_new --daily-run day_new --run-id policy_new
.\.venv\Scripts\python.exe -m sigma verify-weekly-policy --run-id policy_new --output-id policy_new_verified
.\.venv\Scripts\python.exe -m sigma stock --weekly-run week_new --daily-run day_new --stock-policy-run policy_new --run-id stock_new
.\.venv\Scripts\python.exe -m sigma verify-weekly-inventory --run-id stock_new --output-id stock_new_verified
.\.venv\Scripts\python.exe -m sigma delivery --weekly-run week_new --daily-run day_new --run-id delivery_new
.\.venv\Scripts\python.exe -m sigma verify-delivery --run-id delivery_new --output-id delivery_new_verified
.\.venv\Scripts\python.exe -m sigma compare --weekly-run week_new --daily-run day_new --policy-run policy_new --output-id comparison_new
```

Để mở bộ run mới, tạo bản sao config.delivery.json với đúng weekly_run/daily_run, rồi truyền `-DeliveryConfig` cho launcher sau đối soát. Weekly config sản phẩm có 58 ứng viên V13; chọn từng tuyến bằng validation rồi khóa trước test. Cache `--reuse-validation-from` phải cùng nguồn/protocol/ứng viên, có hash nguyên; luôn tính lại selection và test/future, không gọi cache là fit mới.

CLI `python -m sigma --help` liệt kê lệnh; `python -m sigma weekly --help` xem tham số. 29 lệnh/import cũ nằm trong legacy/, ví dụ `python legacy/weekly_forecast.py --help`; implementation nằm trong sigma/. Pipeline ngày ở src/pipeline.py, giao diện ở sigma/ui/daily.py; entry point cũ trong legacy. Cấu hình đầu vào ở data/configs, launcher ở scripts; snapshot nguồn giữ bằng chứng các run lịch sử.

## Quy tắc và kết quả

| Phần | Quy tắc/kết quả |
|---|---|
| Target | Quantity success/ngày đặt UTC/tuyến; A08 thực nghiệm, không lọc activation |
| Split | Train 01/01/2024–30/06/2025; validation 01/07–30/09/2025; test 01/10–31/12/2025; top 10 từ train |
| Dự báo | H14, hai tổng 7 ngày; h1–7 chính/h8–14 riêng; refit 7 ngày; nhãn chỉ tới cutoff |
| Tuần | 9/10 ≤20%, mean 16,17%, LG U+ 21,19%; coverage100%, MAPE/MAE/WAPE/bias/zero báo kèm |
| Ngày R05 | 0/10 ≤20%, MAPE41,89–58,13%; chưa xác nhận mentor đổi sang metric tuần |
| Giao khách | Đặt D → lịch D+7 ngày lịch UTC, cuối tuần/không trễ theo người dùng; chưa có actual giao |
| Tồn | Tuyến×SKU×product_type, giả định riêng đối tác; closing_on_hand<ROP; IP chỉ tính Q |
| Giao dịch | Nhập đầu ngày UTC, bán theo timestamp/ID; đối soát sổ ngày; trừ tồn một lần khi đặt |
| 13 kịch bản | Cơ sở, bán sụt một ngày, giảm/tăng nhiều ngày, nhập50%, nhập trễ3 ngày, không nhập, 6 biến thể độ nhạy |
| So sánh policy | Base fill83,52%→85,02%; shortage2631→2392; early≥7 ngày33,10%→33,73%, cùng2867 sự kiện |

Tồn/nhập/mapping/lead time nhà cung cấp là mô phỏng, tách thời gian giao khách7 ngày. Chưa actual khác số0. Snapshot trạng thái cuối không tái dựng thông tin có tại origin vận hành thật. Không khẳng định dự đoán mọi cú sốc hoặc cảnh báo đạt mọi ca.

## Kiểm tra và cập nhật

225 tests local đã qua sau bổ sung nghiên cứu mùa vụ và giải thích cảnh báo; CI Windows push/PR của commit `183ed10` đạt với 214 tests trước bổ sung này. Các ca kiểm gồm: fixture giả, leakage, metric, quantity/chronology, cache/tamper, alias và provenance. Verifier toàn run và AppTest được lưu riêng; số tests không thay nghiệm thu accuracy. [Chẩn đoán M2–M3](docs/model-diagnostics.md) giải thích biến động ngày/tuần, thử nghiệm bị loại và các ca cảnh báo muộn/bỏ sót.

```powershell
.\.venv\Scripts\python.exe -m sigma refresh --delivery-config data/configs/config.delivery.json
```

Job cập nhật lịch D+7 từ forecast đã kiểm; skip input không đổi, chống chạy trùng, giữ last-good khi lỗi. Đổi raw cần pipeline mới. [Hướng dẫn giao/job](docs/customer-delivery.md) có lịch Windows07:00 đã cài và chạy thử mã0; pythonwẩn/IgnoreNew/StartWhenAvailable. Job chỉ refreshD+7, không tự huấn luyện toàn bộ với CSV mới; ghi last_attempt ngay cả khi skipped_unchanged.

Đọc [TASK](docs/planning/TASK.md), [requirements](docs/requirements.md), [PLAN](docs/planning/PLAN.md), [development](docs/development.md), [review-log](docs/review-log.md#evidence). [README lịch sử](docs/history/README-before-code-organization.md) giữ số liệu trước CHG-027. Word/slide M2 lịch sử giữ local, không làm lại trong đợt này.


</details>
