# Nghiên cứu bổ sung, tách khỏi mô hình M3 đang phục vụ

E92 bổ sung web/backend/research/daily_panel.py, protocol daily-panel-validation-v2:3ứng viên LightGBM (pooled Poisson, pooled weightedL1, riêng tuyến weightedL1),350cây/leaves15/minchild60/lr0,04/lambda10/seed42. Reuse evaluator chung; v1 giữ predictions/metrics/selection giống byte. V2 thêm count/units-per-order từ order đã audit, tín hiệu thị trường/country đến origin, weekday56/182/365 và lag364/365/366 của ngày target. Lag năm chưa có giữ NaN feature, không thay actual thiếu bằng0. Lịch target biết trước; không đưa actual/forecast target vào feature.

Chạy từ root sau load_env.ps1 bằng Python .venv-m3: python -B -m web.backend.research.daily_panel --source-run SOURCE. SQL chỉ≤30/09/2025; bảng đầu vào phải đủ lịch quan sát. Chọn H1–7 MAPE→MAE→ID/coverage100%, không dùng test. V2 đã chạy168fits/35.910forecast/60nhóm metric; validation mean45,971604%,0/10≤20%, cải thiện9/10tuyến so v1 nhưng còn bias âm. Chưa thay serving hoặc đưa vào sổ tồn. [Ma trận cổng chưa đóng](../ACCEPTANCE.md).

web/backend/research/daily_validation.py kiểm tra dự báo trực tiếp từng ngày trên top10 theo quantity **train**, đối chiếu danh sách final đã khóa. Không sửa M2, target/split/MAPE, bảng forecast hoặc selection ứng dụng.

Protocol daily-validation-v1 ghi manifest trước truy vấn/fit. SQL chỉ đọc aggregate đến30/09/2025; yêu cầu lịch quan sát đầy đủ01/01/2024–30/09/2025, từ chối thiếu ngày/null. Origin validation30/06–29/09; horizon1–14, chỉ chấm target trong validation. Giữ mọi ngày0 trong MAE/WAPE/bias/coverage; MAPE chỉ actual dương. Đây là validation đã sử dụng, không là holdout độc lập.

Tám phương pháp cố định: last, seasonal7, mean28, mean90, MAPE-weighted median90, weekday median90, LightGBM Poisson và LightGBM weighted L1. Baseline median MAPE dùng actual dương trong lịch sử để tối ưu loss MAPE, không loại ngày0 khỏi bảng đánh giá. Weighted L1 dùng trọng số1/max(y,1), vẫn giữ nhãn0. Hai model pooled top10 dùng150cây/leaves15/minchild100/lr0,03/lambda10/seed42; rolling365/refit7. Features từ prefix kết thúc origin: lag/mean/std, weekday lịch sử, tuyến, horizon và lịch target biết trước. Training target≤fit_cutoff.

Chọn model/tuyến bằng MAPE H1–7 → MAE → ID, coverage100%; H8–14 báo riêng cùng model. Manifest có status/protocol/code/input/requirements hashes, runtime/seed, fitlog cutoff và clipping, CSV predictions/metrics/selection; tất cả trong **outputs/research ignored local**.

Chạy từ root sau load_env.ps1: python -B -m web.backend.research.daily_validation --source-run SOURCE, dùng Python của .venv-m3. Thay SOURCE bằng UUID source_import complete thật. Mỗi lần tạo thư mục mới, giữ run trước. Đây không phải command thay model ứng dụng.

E91:28fits/95.760forecast/160nhóm metric. Lựa chọn validation H1–7 mean49,451918%,0/10≤20%; so phân bổ M3 cùng623cặp/tuyến mean51,905954%, tốt hơn ở7/10tuyến nhưng vẫn thiếu mục tiêu. Model mới có bias âm; chưa kiểm độc lập/test, chưa đưa vào chính sách tồn hoặc dashboard forecast. Không suy ra dữ liệu không thể dự báo dưới20% chỉ từ tám phương pháp này. [Phạm vi và bằng chứng](../IMPLEMENTATION.md).


<a id="inventory-alert-safety-v1"></a>
## CHG-074 — Thử cảnh báo hằng ngày và tồn an toàn

Người dùng duyệt kế hoạch và giao thực hiện ngày 27/10/2026 trên nhánh `codex/alert-safety-stock-experiments`, từ `a2241dbe`. Sau đó người dùng yêu cầu làm từng bước nhỏ: lượt này hoàn tất riêng **mốc 1**, qua local/commit/push/SHA/CI rồi dừng. Mốc 2–5 chỉ tiếp tục khi được giao.

Protocol máy đọc nằm tại `web/backend/configs/inventory-alert-experiments.json`. Mục tiêu nghiên cứu là xác định tác động riêng của cảnh báo hằng ngày, giả định tồn đầu và chính sách nhập hàng có SS. Giữ nguyên dự báo, mô hình và phân bổ; không đổi API, schema, run kind, React hoặc cài lịch tự chạy. Giữ baseline 986/2.867 = 34,391350% và trạng thái R07/T14 chưa nghiệm thu.

### Các nhóm thử nghiệm đã khóa

| Nhóm | Thiết kế | Cách so sánh |
|---|---|---|
| A | Replay hiện tại: các đợt 14 ngày, cover 7, không đặt mới; đối soát thêm policy cơ sở | Mốc kỹ thuật: early 986/2.867, loại 1.099; policy đáp ứng 14.437/15.968, thiếu 1.531 |
| B | Giữ từng đợt, tồn đầu và hàng về của A; cập nhật cảnh báo cuối mỗi ngày | Cùng sự kiện/mẫu số; ngày cạn dự kiến phải nằm trong phần còn lại của đợt |
| C | Như B, cộng SS đúng một lần vào tồn đầu mỗi đợt | Mẫu số riêng; báo sự kiện xuất hiện, biến mất hoặc đổi ngày so với B |
| D | Nối tồn liên tục; nhận đầu ngày → bán theo giao dịch → chốt → cảnh báo/quyết định nhập; ETA 7 ngày | SS hình thành qua nhập hàng, không cộng trực tiếp vào tồn đầu; báo hiệu quả tồn kho và cảnh báo riêng |

- Giữ L7/R1/H14, N7, ROP theo dự báo, floor và MOQ theo quy tắc seed hiện có. SS `days` dùng b=2/3 theo nhóm tuyến; SS `volatility` dùng population std trên 28 ngày, k=1.
- Sáu cấu hình SS: hai mode × hệ số kịch bản 0,5/1/1,5. C dùng cover 7 cho sáu cấu hình; thêm cover 3/14 không cộng SS. D thêm đối chứng days×0 và cover 3/14 với days×1.
- D dùng 28 ngày chuẩn bị: validation 01–28/07/2025, chấm 29/07–30/09; test hồi cứu 01–28/10/2025, chấm 29/10–31/12. Cảnh báo từ giai đoạn chuẩn bị được gắn với sự kiện thuộc kỳ chấm.
- Validation tạo policy mô phỏng local tại 30/06 từ dữ liệu quá khứ; test lấy policy frozen tại 30/09. Khóa cohort ở đầu mỗi phép thử và thống kê riêng mặt hàng/doanh số xuất hiện sau origin.

### Quy tắc chấm và chọn cấu hình

- A/B chấm sự kiện cạn đầu tiên/item/đợt, dùng cảnh báo hợp lệ đầu tiên trước sự kiện. Các ca cạn D+1…D+6 giữ trong mẫu số; ca đã cạn tại origin loại riêng. B vẫn chịu trần theo thời điểm 45,936519% của chính tập sự kiện A.
- D xác định đợt cạn bằng chuyển tồn dương → 0 ở giao dịch. Chỉ có đợt mới sau khi tồn dương trở lại, bao gồm nhận rồi cạn lại cùng ngày. Cảnh báo gắn với sự kiện đầu tiên trong 14 ngày tiếp theo; mỗi sự kiện chỉ đếm một lần, dùng cảnh báo sớm nhất. Early khi thời gian thực từ cảnh báo đến cạn ≥7 ngày.
- Precision D ở cấp mặt hàng/ngày phát cảnh báo. Nếu không cạn nhưng có receipt từ đơn đặt sau cảnh báo, ghi `intervened/unscored`; không tự gọi là báo sai hoặc đã ngăn cạn. Không cạn và chưa đủ 14 ngày quan sát thì ghi `right-censored`; sự kiện đã quan sát vẫn chấm. Không có sự kiện thì tỷ lệ là null. Metric xuống ROP tách riêng depletion.
- Báo early/counts, precision/recall, sai số ngày cạn, fill/thiếu, số đợt/ngày hết hàng, tồn bình quân, lượng đặt/pending. C/D có mẫu số riêng; không quy đổi thành tiền hoặc nhận có phương án tối ưu khi chưa có ưu tiên kinh doanh.
- Validation chạy toàn ma trận. Chọn tối đa ba đại diện mỗi nhóm C/D: early cao nhất, shortage ít nhất, mean closing thấp nhất; bỏ trùng. Khi hòa, ưu tiên ordered quantity ít hơn rồi config ID. Early null không thắng tiêu chí early. Khóa selection/hash trước evaluate; test chỉ các đại diện và đối chứng A/B/C-days×1/D-days×1. Mọi kết quả là hồi cứu vì test đã được xem.

### Triển khai dự kiến từ mốc 2

CLI nghiên cứu sẽ nằm tại `web/backend/research/inventory_alert_experiments.py`, với các lệnh sau (chưa triển khai ở mốc 1):

```powershell
python -m web.backend.research.inventory_alert_experiments validate
python -m web.backend.research.inventory_alert_experiments evaluate --selection-lock <path>
python -m web.backend.research.inventory_alert_experiments verify --run-dir <path>
```

Nạp env local như README. DB ứng dụng chỉ đọc; kiểm config/source/selection/artifact hash và đủ lịch sử/dự báo trước chạy. Mỗi lần tạo thư mục UUID mới trong `outputs/research`, không ghi đè run cũ. Manifest ghi code/runtime/protocol/input/output hashes. Verifier nghiên cứu phải tính độc lập từ frozen inputs, không dùng helper sản xuất làm kỳ vọng. Raw/run/DB/env và đầu ra nghiên cứu không push.

### Kiểm thử và bàn giao

Ca ngày cạn 6/7/14 hoặc không cạn; SS hai mode/hệ số 0; ETA/pending/MOQ; cộng SS một lần; cảnh báo lặp; tồn 0 kéo dài; nhận rồi cạn cùng ngày; warmup/intervention/censor; future mutation không đổi quyết định trước đó; sửa/xóa artifact bị phát hiện. Mỗi mốc qua local → commit → push thường nhánh thử → remote SHA khớp → hai CI success trước bước sau. Xem [PLAN](../../docs/planning/PLAN.md#chg-074) và [bàn giao](../../docs/development.md#handoff-chg074).
