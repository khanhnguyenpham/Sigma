# SIGMA — Dự báo nhu cầu, tồn kho và lịch giao khách

Sản phẩm Streamlit chạy local trên Windows. Menu gồm tổng quan, dự báo tổng 7 ngày, giao khách D+7, tồn từ dự báo tuần, so sánh ngày/tuần và phần dự báo ngày/tồn/cảnh báo. Mã được gom theo chức năng; bắt đầu từ [bản đồ mã](docs/code-map.md).

**Chưa nghiệm thu toàn bài:** tuần đạt 9/10 top 10, LG U+ 21,19%; R05 ngày vẫn 0/10. Test đã từng được xem, là đánh giá hồi cứu. Giữ nguyên nguồn, target, split, top 10 và metric. [Bảng so sánh](docs/day-week-comparison.md) chấm các phương án trên cùng cửa sổ, giữ riêng tiêu chí ngày.

## Mở trên máy hiện tại

```powershell
.\start_product.ps1
```

Mở `http://127.0.0.1:8503`. Bộ run chọn trong [config.delivery.json](config.delivery.json). Dashboard đọc artifact đã seal; từ chối thiếu/sai hash và không tự huấn luyện khi mở. Dữ liệu/outputs giữ local.

## Cài và chạy demo trên máy mới

```powershell
git clone --branch codex/sigma-local-pipeline https://github.com/khanhnguyenpham/Sigma.git
cd Sigma
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m sigma demo --prefix demo_team
.\.venv\Scripts\python.exe -m sigma check-product --delivery-config outputs/demo_team_bundle/delivery.json --output-id demo_team_ui_qa
.\start_product.ps1 -DeliveryConfig outputs/demo_team_bundle/delivery.json
```

Đã kiểm môi trường Python 3.14.7/Windows 64-bit, phụ thuộc được khóa. Demo tự sinh ba tuyến riêng, tạo pipeline ngày/tuần, D+7, policy 13 kịch bản, snapshot đúng policy, so sánh và đối soát độc lập. Demo 3/3 không chứng minh top 10 của nguồn bài đạt. Dùng prefix mới, không ghi đè run.

GitHub chỉ có mã/config/fixture giả/notebook không output/tài liệu. CSV, outputs, reports, môi trường và job state không upload. Nhánh `codex/sigma-local-pipeline`; [PR1](https://github.com/khanhnguyenpham/Sigma/pull/1) còn draft, chưa merge.

## Pipeline với CSV được cung cấp

Nguồn riêng tư `data/sigma_sim_data_orders.csv` không có trong clone; giữ nguyên byte và đọc [data-contract](docs/data-contract.md). Người dùng mô tả nguồn là giả định, chưa xác minh độc lập.

```powershell
.\.venv\Scripts\python.exe run.py --run-id day_new
.\.venv\Scripts\python.exe -m sigma weekly --config configs/weekly.json --run-id week_new
.\.venv\Scripts\python.exe -m sigma verify-weekly --run-id week_new --daily-run day_new --output-id week_new_verified
.\.venv\Scripts\python.exe -m sigma policy --weekly-run week_new --daily-run day_new --run-id policy_new
.\.venv\Scripts\python.exe -m sigma verify-weekly-policy --run-id policy_new --output-id policy_new_verified
.\.venv\Scripts\python.exe -m sigma stock --weekly-run week_new --daily-run day_new --stock-policy-run policy_new --run-id stock_new
.\.venv\Scripts\python.exe -m sigma verify-weekly-inventory --run-id stock_new --output-id stock_new_verified
.\.venv\Scripts\python.exe -m sigma delivery --weekly-run week_new --daily-run day_new --run-id delivery_new
.\.venv\Scripts\python.exe -m sigma verify-delivery --run-id delivery_new --output-id delivery_new_verified
.\.venv\Scripts\python.exe -m sigma compare --weekly-run week_new --daily-run day_new --policy-run policy_new --output-id comparison_new
```

Để mở bộ run mới, tạo bản sao config.delivery.json với đúng weekly_run/daily_run, rồi truyền `-DeliveryConfig` cho launcher sau đối soát. Weekly config sản phẩm có 48 ứng viên V9; chọn từng tuyến bằng validation rồi khóa trước test. Cache `--reuse-validation-from` phải cùng nguồn/protocol/ứng viên, có hash nguyên; luôn tính lại selection và test/future, không gọi cache là fit mới.

CLI `python -m sigma --help` liệt kê lệnh; `python -m sigma weekly --help` xem tham số. 29 lệnh/import cũ nằm trong legacy/, ví dụ `python legacy/weekly_forecast.py --help`; implementation nằm trong sigma/. Pipeline ngày vẫn dùng src/, run.py và app.py; đợt tổ chức mã giữ nguyên byte ba phần này và sealed v11.

## Quy tắc và kết quả

| Phần | Quy tắc/kết quả |
|---|---|
| Target | Quantity success/ngày đặt UTC/tuyến; A08 thực nghiệm, không lọc activation |
| Split | Train 01/01/2024–30/06/2025; validation 01/07–30/09/2025; test 01/10–31/12/2025; top 10 từ train |
| Dự báo | H14, hai tổng 7 ngày; h1–7 chính/h8–14 riêng; refit 7 ngày; nhãn chỉ tới cutoff |
| Tuần | 9/10 ≤20%, mean 16,19%, LG U+ 21,19%; coverage100%, MAPE/MAE/WAPE/bias/zero báo kèm |
| Ngày R05 | 0/10 ≤20%, MAPE41,89–58,13%; chưa xác nhận mentor đổi sang metric tuần |
| Giao khách | Đặt D → lịch D+7 ngày lịch UTC, cuối tuần/không trễ theo người dùng; chưa có actual giao |
| Tồn | Tuyến×SKU×product_type, giả định riêng đối tác; closing_on_hand<ROP; IP chỉ tính Q |
| Giao dịch | Nhập đầu ngày UTC, bán theo timestamp/ID; đối soát sổ ngày; trừ tồn một lần khi đặt |
| 13 kịch bản | Cơ sở, bán sụt một ngày, giảm/tăng nhiều ngày, nhập50%, nhập trễ3 ngày, không nhập, 6 biến thể độ nhạy |
| So sánh policy | Base fill83,52%→84,97%; shortage2631→2400; early≥7 ngày33,10%→33,80%, cùng2867 sự kiện |

Tồn/nhập/mapping/lead time nhà cung cấp là mô phỏng, tách thời gian giao khách7 ngày. Chưa actual khác số0. Snapshot trạng thái cuối không tái dựng thông tin có tại origin vận hành thật. Không khẳng định dự đoán mọi cú sốc hoặc cảnh báo đạt mọi ca.

## Kiểm tra và cập nhật

192 tests đã qua: fixture giả, leakage, metric, quantity/chronology, cache/tamper, alias và provenance. Verifier toàn run và AppTest lọc bảng/kịch bản được lưu riêng; số tests không thay nghiệm thu accuracy.

```powershell
.\.venv\Scripts\python.exe -m sigma refresh --delivery-config config.delivery.json
```

Job cập nhật lịch D+7 từ forecast đã kiểm; skip input không đổi, chống chạy trùng, giữ last-good khi lỗi. Đổi raw cần pipeline mới. [Hướng dẫn giao/job](docs/customer-delivery.md) có script lịch Windows; không nhận đã cài khi chưa có bằng chứng.

Đọc [TASK](TASK.md), [requirements](docs/requirements.md), [PLAN](PLAN.md), [development](docs/development.md), [review-log](docs/review-log.md#evidence). [README lịch sử](docs/history/README-before-code-organization.md) giữ số liệu trước CHG-027. Word/slide M2 lịch sử giữ local, không làm lại trong đợt này.
