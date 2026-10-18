# Nhóm bắt đầu từ đây — dự báo tổng 30 ngày và M3

Nhánh cần đọc: **`codex/30day-m3`** trong repo **khanhnguyenpham/Sigma**. Đây là phần tổng30 và sản phẩm M3 mới; bộ M2 final của Khang vẫn được giữ riêng. Trang này chứa kết quả tổng hợp và đường dẫn mã, không cần CSV riêng tư để đọc.

## 1. Xem sản phẩm ngay

[Mở SIGMA công khai](https://sigma-demand-inventory.streamlit.app/) → Tổng quan → Dự báo → Kho hàng → Kịch bản → Cảnh báo → Giao khách → Kiểm chứng. Ở Kho hàng mở **Thử phương án nhập hàng và biến động nhu cầu**; ở Kiểm chứng mở bảng so sánh baseline. [Hướng dẫn thao tác chi tiết](mentor-demo.md).

## 2. Kết quả cần hiểu trước

Mỗi origin D dự báo **tổng quantity từ D+1 đến D+30**, không phải tháng lịch. Chạy đối chứng tổng7 riêng. Target cơ sở A08 là quantity theo `success`/ngày đặt UTC, vẫn là đề xuất cần chốt nghiệp vụ; không dùng activation lọc sale. Top10 theo quantity train. Train01/01/2024–30/06/2025; validation01/07–30/09/2025; test01/10–31/12/2025.

Release18/10/2026: **10/10 tuyến tổng30 đạt MAPE≤20%; trung bình11,621356%, coverage100%**. Mỗi tuyến có63cửa sổ test hoàn tất, tất cả nhãn dương; báo cáo cả MAE/WAPE/bias, bias âm là dự báo thấp. Các cửa sổ chồng lấn, không phải63thử nghiệm độc lập. Bảng tổng hợp được trích nguyên từ run đã kiểm `sigma_aggregate_focus_20261018`:

| Quốc gia | Nhà mạng | Mô hình đã chọn | MAPE tổng30 (%) | MAE | WAPE (%) | Bias |
|---|---|---|---:|---:|---:|---:|
| South Korea | LG U+ | `lgbm_annual_ratio15` | 10.1097 | 24.5457 | 10.4754 | -9.9613 |
| Thailand | dtac | `lgbm_annual_ratio15` | 13.4787 | 37.4189 | 13.2326 | -10.6434 |
| Japan | NTT Docomo | `lgbm_annual_ratio7` | 4.3994 | 11.1108 | 4.4235 | -2.4126 |
| Thailand | TrueMove H | `lgbm_annual_ratio7` | 13.8363 | 35.3152 | 13.7244 | 2.8448 |
| Japan | SoftBank | `lgbm_poisson7` | 10.4075 | 27.6619 | 10.4535 | -27.4605 |
| South Korea | KT | `lgbm_poisson7` | 5.6851 | 13.6071 | 5.8245 | -12.5118 |
| South Korea | SKT | `lgbm_poisson7` | 7.0687 | 16.4478 | 7.1227 | 0.0147 |
| Thailand | AIS | `lgbm_ratio7` | 16.9873 | 46.8225 | 16.8590 | -7.7899 |
| China | China Mobile | `mix_lgbm_annual_ratio7_w25` | 18.6838 | 21.8347 | 17.4191 | 6.4622 |
| Japan | au (KDDI) | `prophet_annual3` | 15.5569 | 42.6320 | 15.3589 | 5.8804 |

China Mobile dùng75%champion LightGBM và25%LightGBM mùa vụ năm, trọng số được chọn validation rồi khóa trước lượt test này. Focus đã được xác định từ test cũ nên toàn bộ kết quả là **đánh giá hồi cứu**, chưa là holdout mới độc lập. Chín tuyến còn lại và tổng7 đối chứng được giữ nguyên. Tổng7 cùng pipeline đạt9/10, mean15,485424%; không trộn với bộ M2 final7 riêng của Khang. [Protocol nghiên cứu và bằng chứng](aggregate-refinement.md).

So sánh tổng30 cùng63origin/tuyến: Naive MAPE37,871734% và0/10đạt; MA7 18,287797% và5/10; MA28 17,403218% và7/10; mô hình đã chọn11,621356% và10/10. Đây là so sánh cùng mẫu, không dùng điểm test để chọn lại.

## 3. Đọc mã theo thứ tự này

| Phần | File cần đọc | Nội dung |
|---|---|---|
| Chuẩn hóa | [src/data.py](../src/data.py) | Audit, quantity/ngày UTC, chuỗi ngày và toptrain |
| Cấu hình tổng | [aggregate.json](../data/configs/aggregate.json) | Cửa sổ7/30, mô hình và giới hạn fit |
| Dự báo trực tiếp | [aggregate.py](../sigma/forecasting/aggregate.py) | Nhãn tổng, feature quá khứ, fit/validation/test, phân bổ ngày |
| Cải thiện China Mobile | [aggregate_focus.py](../sigma/experiments/aggregate_focus.py) và [aggregate-focus.json](../data/configs/aggregate-focus.json) | Lựa chọn validation và tổ hợp khóa |
| Đối soát forecast | [verification/aggregate.py](../sigma/verification/aggregate.py) | Kiểm run/nhãn/split/metric/phân bổ |
| Tồn kho M3 | [inventory/product30.py](../sigma/inventory/product30.py) | SKU×type×tuyến, policy và13kịch bản |
| Đối soát M3 | [verification/product30.py](../sigma/verification/product30.py) | Ledger/sự kiện/ngưỡng/cảnh báo |
| Mặc định sản phẩm | [product30-focus.json](../data/configs/product30-focus.json) | Hai run nguồn đã đối soát, D+7 giao khách |
| Thử phương án | [planning.py](../sigma/analysis/planning.py) và [product30_planner.py](../sigma/ui/product30_planner.py) | Mô phỏng nhìn tới từ forecast cố định |
| Baseline | [benchmark.py](../sigma/analysis/benchmark.py) | Naive/MA7/MA28 cùng mẫu với mô hình |
| Dashboard | [product30.py](../sigma/ui/product30.py) và [product30_pages.py](../sigma/ui/product30_pages.py) | Nạp kết quả, bộ lọc và7tab |
| Job local | [jobs/product30.py](../sigma/jobs/product30.py) | Adopt/skip/refresh bộ đã kiểm |

## 4. Lấy mã về máy

Nếu chưa có repo:

```powershell
git clone --branch codex/30day-m3 https://github.com/khanhnguyenpham/Sigma.git
cd Sigma
```

Nếu đã có repo, kiểm `git status` và lưu thay đổi đang làm trước khi đổi nhánh, sau đó:

```powershell
git fetch origin
git switch codex/30day-m3
git pull --ff-only origin codex/30day-m3
```

Nếu chưa có nhánh local, Git sẽ tự tạo tracking branch từ `origin/codex/30day-m3`. Không dùng reset/force để làm mất phần đang sửa. Nhóm muốn sửa code thì tạo nhánh riêng từ nhánh này và mở pull request để review.

## 5. Chạy trên máy mới không có dữ liệu riêng tư

Ưu tiên xem bản online ở mục1 để thấy kết quả nguồn bài10/10. Clone GitHub có mã/config/tests/tài liệu/bảng tổng hợp đã được cho phép; **không có CSV gốc hoặc run nguồn đầy đủ**. Không chạy launcher mặc định rồi coi thiếu run là lỗi mô hình.

Cài Python3.14 và tạo môi trường; không cần kích hoạt venv:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m sigma demo30 --prefix team30_first
.\scripts\start_m3.ps1 -Config outputs/team30_first_bundle/product30.json
```

Demo tự sinh chạy riêng trên cổng8508 với3tuyến, dùng để đọc luồng và thử giao diện, **không phải bằng chứng10/10 của dữ liệu nguồn bài**. Mỗi lần tạo chọn prefix mới, không ghi đè run sealed. Muốn tái lập nguồn bài phải có bản dữ liệu/run hợp lệ được nhóm quản lý local; không đưa dữ liệu vào commit. Lệnh chi tiết/tái lập ở [hướng dẫn tổng30/M3](30day-m3.md).

## 6. Giới hạn phải trình bày đúng

- R05 dự báo theo từng ngày vẫn mở; MAPE tổng30 không tự thay tiêu chí ngày trong kickoff.
- Tồn/nhập/đối tác/lead time là mô phỏng. Trigger đóng ngày<ROP; IP chỉ dùng tính lượng đặt. D+7 giao khách khác lead time nhập kho.
- M3 có13kịch bản/920mặt hàng; fill cơ sở85,978206%; cảnh báo trước≥7ngày1053/2867sự kiện=36,728287%, chưa đạt mọi trường hợp.
- Công cụ thử phương án là mô phỏng tất định, có lượng dự kiến số lẻ; không gửi đơn nhập thật, không làm đổi benchmark. ETA hàng đang chờ về là giả định vì snapshot chưa có lịch lô đầy đủ.
- Cloud dùng kết quả đã tính, chưa tự train/nhận CSV mới/job nền. Chưa actual01/2026; không ghi số dự báo thành doanh số thực.
- 373tests local đạt ở E87,7tab cloud đã kiểm; CI của commit mới phải xem kết quả GitHub riêng. R05/R07/T14 và review mentor còn mở, không tự nhận100% kickoff.

[Kế hoạch và tiến độ](planning/TASK.md) · [Bản đồ mã đầy đủ](planning/PROJECTMAP.md) · [Triển khai](portable-hosting.md).
