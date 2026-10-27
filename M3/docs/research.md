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

Người dùng duyệt kế hoạch và giao thực hiện ngày 27/10/2026 trên nhánh `codex/alert-safety-stock-experiments`, từ `a2241dbe`. Người dùng yêu cầu làm từng bước nhỏ. Mốc 1–3 đã hoàn tất; lượt mới giao riêng **mốc 4**, qua local/commit/push/SHA/CI rồi dừng. Mốc 5 chờ giao tiếp.

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

- A/B chấm sự kiện cạn đầu tiên/item/đợt, dùng cảnh báo hợp lệ đầu tiên trước sự kiện. Các ca cạn D+1…D+6 giữ trong mẫu số; ca đã cạn tại origin loại riêng. B vẫn chịu trần theo thời điểm của chính tập sự kiện A: 45,936519% ở đối chứng test lịch sử; trần validation được tính riêng bên dưới.
- D xác định đợt cạn bằng chuyển tồn dương → 0 ở giao dịch. Chỉ có đợt mới sau khi tồn dương trở lại, bao gồm nhận rồi cạn lại cùng ngày. Cảnh báo gắn với sự kiện đầu tiên trong 14 ngày tiếp theo; mỗi sự kiện chỉ đếm một lần, dùng cảnh báo sớm nhất. Early khi thời gian thực từ cảnh báo đến cạn ≥7 ngày.
- Precision D ở cấp mặt hàng/ngày phát cảnh báo. Nếu không cạn nhưng có receipt từ đơn đặt sau cảnh báo, ghi `intervened/unscored`; không tự gọi là báo sai hoặc đã ngăn cạn. Không cạn và chưa đủ 14 ngày quan sát thì ghi `right-censored`; sự kiện đã quan sát vẫn chấm. Không có sự kiện thì tỷ lệ là null. Metric xuống ROP tách riêng depletion.
- Báo early/counts, precision/recall, sai số ngày cạn, fill/thiếu, số đợt/ngày hết hàng, tồn bình quân, lượng đặt/pending. C/D có mẫu số riêng; không quy đổi thành tiền hoặc nhận có phương án tối ưu khi chưa có ưu tiên kinh doanh.
- Validation chạy toàn ma trận. Chọn tối đa ba đại diện mỗi nhóm C/D: early cao nhất, shortage ít nhất, mean closing thấp nhất; bỏ trùng. Khi hòa, ưu tiên ordered quantity ít hơn rồi config ID. Early null không thắng tiêu chí early. Khóa selection/hash trước evaluate; test chỉ các đại diện và đối chứng A/B/C-days×1/D-days×1. Mọi kết quả là hồi cứu vì test đã được xem.

### CLI nghiên cứu ở mốc 2

CLI tại `web/backend/research/inventory_alert_experiments.py` có ba lệnh từ mốc 2 dưới đây; mốc 4 bổ sung `select` tại phần bên dưới. Mốc 2–3 chỉ chạy synthetic; mốc 4 đã chạy validation từ dữ liệu frozen local và kiểm độc lập. Test hồi cứu thuộc mốc 5, chưa chạy.

```powershell
python -m web.backend.research.inventory_alert_experiments validate
python -m web.backend.research.inventory_alert_experiments evaluate --selection-lock <path>
python -m web.backend.research.inventory_alert_experiments verify --run-dir <path>
```

Nạp env local như README. DB ứng dụng chỉ đọc; kiểm config/source/selection/artifact hash và đủ lịch sử/dự báo trước chạy. Mỗi lần tạo thư mục UUID mới trong `outputs/research`, không ghi đè run cũ. Manifest ghi code/runtime/protocol/input/output hashes. Verifier nghiên cứu phải tính độc lập từ frozen inputs, không dùng helper sản xuất làm kỳ vọng. Raw/run/DB/env và đầu ra nghiên cứu không push.

### Kiểm thử và bàn giao

Ca ngày cạn 6/7/14 hoặc không cạn; SS hai mode/hệ số 0; ETA/pending/MOQ; cộng SS một lần; cảnh báo lặp; tồn 0 kéo dài; nhận rồi cạn cùng ngày; warmup/intervention/censor; future mutation không đổi quyết định trước đó; sửa/xóa artifact bị phát hiện. Mỗi mốc qua local → commit → push thường nhánh thử → remote SHA khớp → hai CI success trước bước sau. Xem [PLAN](../../docs/planning/PLAN.md#chg-074) và [bàn giao](../../docs/development.md#handoff-chg074).

<a id="inventory-alert-safety-step2"></a>
### CHG-074 mốc 2 — Giao diện và giới hạn đã triển khai

- `validate`: đọc snapshot bằng `--snapshot <json hoặc json.gz>` hoặc đọc DB ứng dụng qua env nếu không truyền snapshot; tính toàn bộ 19 cấu hình. DB dùng một giao dịch REPEATABLE READ/READ ONLY; kiểm lineage/source/config/selection hash và hash sealed artifacts, không enqueue/ghi run mới.
- `evaluate --selection-lock <path>`: chỉ nhận lock gắn manifest validation và receipt `verification.json` có `status=verified`, `independent_replay=true`; kiểm code/protocol/lineage và tối đa ba đại diện mỗi nhóm C/D. Kiểm lock trước khi đọc dữ liệu test. Luôn thêm đối chứng A/B/C-days×1/D-days×1. Ở mốc 2 receipt được inject trong fixture; từ mốc 3 fixture cũng dùng verifier độc lập thật. Ở thời điểm mốc 2–3 chưa có receipt dữ liệu thật hoặc bộ chọn; mốc 4 đã bổ sung cả hai cho validation.
- Ở mốc 2, `verify --run-dir <path>` chỉ kiểm hash. Từ mốc 3, lệnh này chạy verifier độc lập và ghi receipt riêng `verification.json`; helper `verify_artifacts` vẫn chỉ là kiểm hash, không phải bằng chứng toán học.
- `--output-root` mặc định `outputs/research`; mỗi lần dùng UUID mới. `--baseline-root` mặc định `outputs/step15/runs`; source/forecast lấy sealed artifacts từ output root trong env. Không thêm dependency, API/schema/run kind hoặc thay ứng dụng đang dùng.

Snapshot version1 gồm `split`, `period` đúng protocol, `meta` (provenance synthetic/local_frozen_db và source/forecast/selection hashes), `catalog`, `daily`, `forecasts`, `sales`, `policies`, `receipts`. Ngày dùng ISO UTC; daily là quantity nguyên có actual_available=true; forecast có đủ14giá trị mỗi item/origin; sales giữ source sequence đã audit để xử lý giao dịch đúng thứ tự. Ngày thiếu khác0, trùng khóa hoặc dữ liệu không hợp lệ bị chặn. Validation seed dùng đúng28ngày quá khứ, không lấy floor test áp ngược. Cohort khóa tại đầu split, liệt kê mặt hàng/doanh số ngoài cohort.

Lock dự kiến cho mốc4 gồm `validation_run`, `validation_manifest_sha256`, `validation_verification_sha256`, `protocol_sha256`, `source_sha256`, `forecast_config_sha256`, `selection_sha256`, `selected_configs` (danh sách config ID). Tạo lock và chọn đại diện chưa triển khai trong mốc2.

Đầu ra có `inputs.json.gz`, `results/<config-id>.json.gz` (initialization, ledger, transactions, events, orders, alarms, cases, threshold_cases, metrics; D thêm alarm_evaluation, C thêm event_changes), `metrics.json`, `report.html`, `manifest.json`. Manifest ghi research/application code, Python/packages/requirements, protocol/input/output hashes. Trạng thái là `calculated_unverified`; báo cáo không nhận đạt nghiệm thu hoặc cải thiện model. Chạy lỗi ghi failed và diagnostic private, không in driver/credential/raw record ra console.

Ở D, đơn mới đặt cùng ngày sau cảnh báo cũng là receipt chưa biết tại thời điểm cảnh báo. Precision chỉ chấm ngày phát cảnh báo trong kỳ chấm; cảnh báo warmup vẫn được dùng tính lead của sự kiện trong kỳ. Một sự kiện có nhiều cảnh báo vẫn chỉ đếm một lần. Đây là quy tắc tính đã kiểm tính tay, chưa thay thế verifier độc lập.

Ví dụ kiểm CLI bằng snapshot synthetic (không dùng dữ liệu thật):

```powershell
python -m web.backend.research.inventory_alert_experiments validate --snapshot <synthetic.json.gz> --output-root outputs/research/ss-step2/smoke
python -m web.backend.research.inventory_alert_experiments verify --run-dir <thư-mục-UUID-vừa-tạo>
```

Mốc 2 có26ca mới: boundary6/7/14/no-event/zero, parity A với pure replay hiện có, B không đổi sự kiện và giới hạn ngày trong đợt, C SS2mode/ceil/cộng1lần/cover, D MOQ/pending/ETA/zero/recovery, warmup/dedup/intervention/censor, đầu vào thiếu/trùng/sai kiểu, CLI/integrity/evaluate guard và snapshot DB test chỉ đọc. Kết quả thực và cổng GitHub tại [bàn giao](../../docs/development.md#handoff-chg074-step2).

<a id="inventory-alert-safety-step3"></a>
### CHG-074 mốc 3 — Verifier độc lập

`web/backend/research/inventory_alert_verification.py` tự đọc snapshot và tái dựng từng mặt hàng theo thời gian. Không import runner hoặc gọi recommend/project/fulfill_day/scoring của inventory/alerts. Dùng NumPy cho cùng quy ước phép cộng float và statistics.pstdev cho population std; công thức và state machine được viết độc lập. Các test thay mọi helper nghiệp vụ của producer bằng hàm báo lỗi vẫn cho verifier chạy đạt.

- Kiểm đủ matrix/config/period/cohort/lineage, input hợp lệ, initialization, từng giao dịch, ledger/SS/ROP/IP/S/Q, lô và ETA, projection/ngày cạn/ngày xuống ROP, episode/cases/dedup/warmup/intervention/censor, metric và C-event changes. Metric tổng/HTML phải khớp kết quả độc lập; số nguyên/bool kiểm đúng kiểu và giá trị, float atol1e-8/rtol0. Hash được tính lại không che được sai phép tính.
- Provenance synthetic chỉ xác nhận toán học trên frozen synthetic inputs. Với local_frozen_db, verifier kiểm thêm raw CSV hash, sealed parents/config/selection và các hàng daily/forecast/policy/receipts trên DB qua REPEATABLE READ/READ ONLY; transactions đối chiếu nguồn bằng audit A08 chung. Không coi tồn/nhập mô phỏng là tồn kho doanh nghiệp thực.
- `verify --run-dir <path> [--baseline-root <path>]` chỉ tạo `verification.json` sau khi mọi kiểm đạt. Receipt ghi status=verified, independent_replay=true, evidence_class, anchor_scope, manifest/input/code/protocol hashes và counts. Artifact/manifest/HTML cũ không bị sửa; trạng thái calculated_unverified trong manifest là trạng thái lúc tính, receipt là bằng chứng kiểm độc lập sau đó.
- Kiểm lại receipt hợp lệ giữ nguyên bytes/timestamp. Receipt cũ sai binding hoặc kết quả sai bị từ chối; không ghi đè để hợp thức hóa. Các bundle mốc2 có hash runner cũ được bảo toàn, không tự viết lại hoặc nâng trạng thái; muốn kiểm bằng code mới phải tính một bundle mới.
- `evaluate` kiểm lại toán học của validation trước đọc test, không chỉ tin status/hash trong receipt. Receipt giả cùng output đã reseal vẫn bị chặn. Bằng chứng synthetic không cho phép gọi evaluate đọc DB thật hoặc nâng thành local_frozen_db. Không tạo selection lock ở mốc3.

Các ca mới bao phủ hash/tệp mất, forge+reseal ledger/SS/ROP/transactions/events/orders/initialization/alarms/cases/threshold/alarm evaluation/event changes/metrics/HTML, matrix/code/protocol/input binding, receipt giả; future actual/forecast/policy không sửa quyết định trước cutoff; item tương lai ngoài cohort; ngày6/7/14, N/N+1, equality ROP; std population/hệ số0/SS cộng1lần; receipt rồi cạn lại cùng ngày; warmup không nhân sự kiện hoặc gán nhầm sự kiện kế tiếp; can thiệp cùng ngày và thiếu nhãn cuối kỳ; receipt idempotent và JSON duplicate/NaN bị chặn. Lượt này chỉ synthetic/DB test riêng. [Bàn giao](../../docs/development.md#handoff-chg074-step3).

<a id="inventory-alert-safety-step4"></a>
### CHG-074 mốc 4 — Validation và khóa đại diện

Thêm lệnh `select --run-dir <validation-run> [--baseline-root <path>]`: từ chối split test trước đọc metric; chạy verifier độc lập, chọn đại diện C/D đúng protocol, rồi tạo `selection_lock.json` riêng. Không sửa manifest/receipt/input/result đã sealed. Tối đa3đại diện mỗi nhóm, bỏ trùng theo thứ tự criterion; early so bằng phân số từ counts (null không thắng,0 hợp lệ), shortage/mean closing tăng dần; hòa theo ordered_qty rồi configID. Verifier kiểm độc lập bằng phép nhân chéo cho tỷ lệ. Evaluate và verifier test cũng kiểm quy tắc này, không nhận danh sách đại diện tùy ý.

Lock có các binding mốc2–3 và thêm `selection_details` (group/criterion/config_id/value) cùng created_at UTC. Kiểm lại lock hợp lệ giữ nguyên bytes; sai nội dung bị từ chối, không ghi đè. Tạo các báo cáo dẫn xuất `validation-comparison.csv` và `validation-comparison.html` từ metric đã verify; manifest/receipt SHA gắn trong hồ sơ, báo cáo ghi rõ tồn mô phỏng, khác mẫu số C/D và chưa nghiệm thu R07/T14. Chưa chạy test hồi cứu.

```powershell
python -m web.backend.research.inventory_alert_experiments validate --output-root outputs/research/ss-step4/validation
python -m web.backend.research.inventory_alert_experiments select --run-dir <validation-run>
```

Code/source/forecast/protocol được khóa trước đọc kết quả tại outputs/research/ss-step4/code-lock.json; kiểm trước chạy325Python đạt. Matrix vẫn19cấu hình cũ, nguồn/forecast frozen, không refit hoặc tuning mới. Kết quả và lock private giữ local; chỉ aggregate Markdown được đưa lên Git. Kết quả validation đã được kiểm độc lập dưới đây và trong [bàn giao](../../docs/development.md#handoff-chg074-step4).

#### Kết quả validation đã kiểm độc lập

Run local `inventory-alert-safety-v1-2c212e05-c5ef-4c43-a7a4-c08b7777fe18`, provenance `local_frozen_db`, anchor `original_csv_and_readonly_db`; 920 mặt hàng trong cohort, không có mặt hàng/doanh số ngoài cohort. A/B/C chấm 6 đợt đủ 14 ngày (01/07–22/09), loại riêng đuôi 8 ngày; D chạy 01/07–30/09 và chỉ chấm 29/07–30/09 sau 28 ngày chuẩn bị. Báo sớm nghĩa là ít nhất 7 ngày. Tồn, đơn nhập và ETA đều mô phỏng; toàn bộ kết quả là hồi cứu.

| Cấu hình | Báo sớm/sự kiện | Early % | Fill % | Thiếu | Tồn cuối ngày BQ/item | Lượng đặt | Đại diện |
|---|---:|---:|---:|---:|---:|---:|---|
| A-base | 1047/3060 | 34.2157 | 51.5283 | 8135 | 0.9419 | 0 |  |
| B-daily | 1066/3060 | 34.8366 | 51.5283 | 8135 | 0.9419 | 0 |  |
| C-days-m0.5-cover7 | 757/2133 | 35.4899 | 65.3816 | 5810 | 1.6586 | 0 | Có |
| C-days-m1-cover7 | 717/2059 | 34.8227 | 68.2238 | 5333 | 1.7686 | 0 |  |
| C-days-m1.5-cover7 | 622/1949 | 31.9138 | 71.4354 | 4794 | 1.9273 | 0 |  |
| C-volatility-m0.5-cover7 | 685/2001 | 34.2329 | 67.5207 | 5451 | 1.7981 | 0 |  |
| C-volatility-m1-cover7 | 461/1663 | 27.7210 | 74.5874 | 4265 | 2.3084 | 0 |  |
| C-volatility-m1.5-cover7 | 314/1281 | 24.5121 | 80.6769 | 3243 | 2.8995 | 0 | Có |
| C-cover3 | 829/3550 | 23.3521 | 31.8596 | 11436 | 0.4947 | 0 | Có |
| C-cover14 | 429/2058 | 20.8455 | 74.5278 | 4275 | 2.1263 | 0 |  |
| D-days-m0.5-cover7 | 210/552 | 38.0435 | 92.3737 | 880 | 5.6563 | 9573 |  |
| D-days-m1-cover7 | 151/486 | 31.0700 | 93.6650 | 731 | 5.7951 | 9608 |  |
| D-days-m1.5-cover7 | 98/422 | 23.2227 | 95.0516 | 571 | 5.9803 | 9692 |  |
| D-volatility-m0.5-cover7 | 157/486 | 32.3045 | 93.7343 | 723 | 5.8646 | 9816 |  |
| D-volatility-m1-cover7 | 66/324 | 20.3704 | 95.8749 | 476 | 6.4587 | 10146 |  |
| D-volatility-m1.5-cover7 | 34/210 | 16.1905 | 97.5041 | 288 | 7.0810 | 10393 | Có |
| D-cover3 | 160/507 | 31.5582 | 93.6650 | 731 | 5.7355 | 9762 |  |
| D-cover14 | 175/509 | 34.3811 | 93.5956 | 739 | 5.7266 | 9822 |  |
| D-days-m0-cover7 | 360/786 | 45.8015 | 88.5692 | 1319 | 5.0050 | 9599 | Có |

A/B giữ cùng 3.060 sự kiện và 714 ca đã cạn tại origin bị loại; B thêm 19 ca báo sớm (+0,6209 điểm phần trăm), tồn và thiếu không đổi. Có 1.401/3.060 sự kiện đủ khoảng cách ≥7 ngày từ origin, nên trần thời điểm validation là 45,7843%; 1.659 ca sớm hơn vẫn nằm trong mẫu số. Đây là tập validation khác đối chứng test 986/2.867=34,391350%, không ghi đè kết quả đó.

C đổi tồn đầu nên đổi ngày cạn/mẫu số. Số xuất hiện/biến mất/đổi ngày so với B:

| Cấu hình C | Xuất hiện | Biến mất | Đổi ngày | Loại tại origin |
|---|---:|---:|---:|---:|
| C-days-m0.5-cover7 | 27 | 954 | 1315 | 660 |
| C-days-m1-cover7 | 27 | 1028 | 1347 | 660 |
| C-days-m1.5-cover7 | 27 | 1138 | 1348 | 660 |
| C-volatility-m0.5-cover7 | 0 | 1059 | 1324 | 714 |
| C-volatility-m1-cover7 | 0 | 1397 | 1284 | 714 |
| C-volatility-m1.5-cover7 | 0 | 1779 | 1077 | 714 |
| C-cover3 | 490 | 0 | 1264 | 714 |
| C-cover14 | 0 | 1002 | 1003 | 714 |

C-days×0,5 có early cao nhất nhóm C (35,4899%), chưa đạt 45%. C-volatility×1,5 giảm thiếu còn 3.243 nhưng giả định có sẵn thêm SS; không diễn giải thành mô hình dự báo chính xác hơn.

D chấm episode cạn duy nhất, khác đơn vị item/đợt của A/B/C; precision D theo item/ngày cảnh báo. D-SS0 đạt mục tiêu làm việc 45% **chỉ trên validation theo protocol D** (360/786=45,8015%), đồng thời thiếu 1.319 và fill 88,5692%. D-days×1: thiếu 731/fill 93,6650%/early 31,0700%; D-volatility×1,5: thiếu 288/fill 97,5041%/early 16,1905%, tồn bình quân 7,0810 so với 5,0050 ở D-SS0. Tăng SS làm giảm thiếu và đổi tập sự kiện còn xảy ra; early rate thấp hơn không đủ để kết luận vận hành kém hơn. Không chọn phương án tốt nhất khi chưa có ưu tiên chi phí/dịch vụ.

| Cấu hình D | Episode cạn | Ngày-item tồn 0 | Precision % | Recall % | MAE ngày | Pending BQ | Đang về cuối kỳ | Can thiệp nhập/chưa chấm | Thiếu nhãn cuối kỳ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D-days-m0.5-cover7 | 552 | 3885 | 75.4861 | 80.4348 | 4.7185 | 1.0218 | 722 | 1666 | 398 |
| D-days-m1-cover7 | 486 | 3665 | 76.2585 | 79.0123 | 4.8542 | 1.0233 | 702 | 1665 | 332 |
| D-days-m1.5-cover7 | 422 | 3382 | 78.1437 | 76.7773 | 5.1759 | 1.0298 | 737 | 1381 | 187 |
| D-volatility-m0.5-cover7 | 486 | 3623 | 80.6804 | 78.6008 | 4.8743 | 1.0458 | 687 | 1559 | 240 |
| D-volatility-m1-cover7 | 324 | 2926 | 85.4890 | 72.2222 | 5.3632 | 1.0761 | 771 | 1094 | 103 |
| D-volatility-m1.5-cover7 | 210 | 2507 | 89.8305 | 62.8571 | 5.0227 | 1.0966 | 820 | 598 | 58 |
| D-cover3 | 507 | 3745 | 77.4545 | 80.6706 | 4.8044 | 1.0328 | 792 | 1622 | 333 |
| D-cover14 | 509 | 3788 | 77.7977 | 77.9961 | 4.9018 | 1.0433 | 767 | 1586 | 342 |
| D-days-m0-cover7 | 786 | 5375 | 71.9032 | 80.7888 | 4.0724 | 1.0234 | 690 | 1591 | 611 |

Can thiệp và thiếu nhãn là số item/ngày phát cảnh báo không được chấm precision; không cộng vào FP hoặc khẳng định đã ngăn cạn. Các sự kiện đã quan sát vẫn được chấm. Metric xuống ROP vẫn nằm riêng trong metrics/results, không cộng vào tử số depletion.

Đã khóa đại diện đúng ba mục tiêu, bỏ trùng:

| Nhóm | Early cao nhất | Thiếu ít nhất | Tồn bình quân thấp nhất |
|---|---|---|---|
| C | C-days-m0.5-cover7 | C-volatility-m1.5-cover7 | C-cover3 |
| D | D-days-m0-cover7 | D-volatility-m1.5-cover7 | D-days-m0-cover7 (trùng) |

Tổng 5 đại diện; nếu người dùng giao mốc 5, evaluate sẽ chạy 9 cấu hình gồm 5 đại diện và 4 đối chứng A/B/C-days×1/D-days×1. Chưa gọi evaluate hoặc đọc kết quả test mới. Lock tạo lúc 07:36:16 UTC ngày 27/10/2026 sau kiểm độc lập validation; không chọn lại theo test.

- Manifest SHA256: `7508438701af4d1a404b78e55d9ff93e29477d3302ceb83a4fe168ea6a61aa32`.
- Verification receipt SHA256: `0cbd8d65a1e824966fb87c4be2d514c5f64e54d9b5dd236b1402ddc92aa04f71`.
- Selection lock SHA256: `69287d8dd46674b28943ef02308be5f5947c23ee9c0b9719bba334223e40aac8`.

Private evidence tại outputs/research/ss-step4: code-lock.json (trước kết quả), all-python.xml, validate/select-command.json và stdout, validation-summary.json, sealed-validation-files.json, preservation.json; bundle validation chứa inputs/results/metrics/report/manifest, verification.json, selection_lock.json và validation-comparison.csv/html. Artifact gốc vẫn ghi calculated_unverified theo thời điểm tính; receipt xác nhận verified độc lập, không sửa lại manifest/metric cũ. R07/T14 chưa nghiệm thu.
