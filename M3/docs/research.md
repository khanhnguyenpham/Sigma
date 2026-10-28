# Nghiên cứu bổ sung, tách khỏi mô hình M3 đang phục vụ

**CHG-075 — 28/10/2026, đã công bố riêng nghiên cứu49%:** mã `1c0c63c` đã push nhánh `codex/early-warning-opportunity-audit`, remoteSHA khớp/hai workflowCI completed/success.115targeted mới/help/protocol/pip/17link-anchor/703hash đạt; chỉ code/protocol/tests/tài liệu và thuộc tính giữ byte nghiên cứu lên Git. S25test285/578=49,3080%,validation228/486=46,9136% vẫn early hồi cứu có đánh đổi; không BE/FE/model/default/DB hoặc thay `m3-implementation`. [Hướng dẫn nhóm](49-warning-study.md), [bàn giao](../../docs/development.md#handoff-chg075-publish49). Raw/run/env/Word/ảnh giữ local; giới hạn không GitHub bên dưới là checkpoint lịch sử. R07/T14 chưa nghiệm thu.

**Hiện hành CHG-075 — 27/10/2026, hoàn tất phân tích tải cảnh báo local:** [báo cáo hậu kiểm C00/S25](#forecast-alarm-burden) đã đối soát từng nhãn, bảng tuyến/item/ngày và chuỗi liên tiếp. Test tăng 933 FP item-ngày, 3.603 item-ngày cảnh báo trong 64 ngày chấm; 92 early mới/0 mất giữ nguyên từ F4. 35 kiểm tra đạt, 1.644 protected/239 tracked ngoài MD nguyên. Chỉ nghiên cứu, chưa dùng S25 thay phương án chính `m3-implementation`, không GitHub; R07/T14 chưa nghiệm thu. Các checkpoint F1–F4 bên dưới giữ lịch sử.

<a id="forecast-alarm-burden"></a>
## CHG-075 — Phân tích cảnh báo sai và tải cảnh báo, 27/10/2026

**Phạm vi người dùng giao:** bắt đầu phân tích đánh đổi sau F4, nhưng chưa dùng làm phương án thay thế phương án chính bên `m3-implementation`. Chỉ đọc các output C00/S25 đã khóa; không chạy forecast/replay/fit, chọn lại, thử hệ số hoặc tích hợp ứng dụng. Giữ code/protocol/parameters/selection và toàn bộ output F1–F4. Không DB, commit/push/merge/deploy/CI; giữ nhánh audit/HEAD `ce738c4`. Ref local và remote-tracking `m3-implementation` vẫn `86a0162970bf45e4129ae61e14fe29185e7f32ed`; không gọi đây là kiểm SHA mới trên GitHub.

**Đơn vị và cách chấm:** một signal là một item-ngày có dự báo cạn hợp lệ, không phải một công việc của nhân viên. Item là tuyến × SKU × product_type, không gộp SKU trùng tên giữa tuyến. Nhãn giữ đúng scorer frozen: có sự kiện đầu tiên trong H14 là TP; nếu không, xét can thiệp → right-censor → FP. Không gộp can thiệp/thiếu nhãn thành FP. Early vẫn một episode tính một lần, báo trước ≥7 ngày; không dùng mẫu số item-ngày cho early. Tồn/đơn/receipts/episode gốc giữ nguyên. FP chỉ nói không thấy sự kiện theo luật H14 trên đường vận hành frozen, không chứng minh forecast điểm sai hoặc tác động nhân quả.

| Chỉ số trong 64 ngày chấm | Validation C00 | Validation S25 | Test C00 | Test S25 |
|---|---:|---:|---:|---:|
| Early episode | 151/486 | 228/486 | 193/578 | 285/578 |
| Precision item-ngày | 76,2585% | 60,6383% | 80,6202% | 66,7646% |
| TP item-ngày | 1.227 | 2.109 | 1.768 | 2.728 |
| FP item-ngày | 382 | 1.369 | 425 | 1.358 |
| Can thiệp | 1.665 | 2.743 | 1.990 | 3.038 |
| Right-censor | 332 | 726 | 625 | 1.287 |
| Tổng signal item-ngày | 3.606 | 6.947 | 4.808 | 8.411 |
| Trung bình signal/ngày UTC | 56,3438 | 108,5469 | 75,1250 | 131,4219 |
| P95 số signal/ngày, nội suy tuyến tính | 96,70 | 158,00 | 98,40 | 168,40 |
| Số signal trong ngày cao nhất | 100 | 160 | 108 | 184 |
| Item có signal | 483 | 527 | 522 | 551 |
| Item có FP | 141 | 277 | 141 | 267 |
| Chuỗi signal liên tiếp: số chuỗi / dài nhất | 1.477 / 26 | 1.592 / 52 | 1.725 / 37 | 1.814 / 64 |
| Chuỗi chỉ FP: số chuỗi / dài nhất | 173 / 14 | 435 / 17 | 175 / 11 | 412 / 17 |

Chuỗi tính riêng từng item, ngắt khi thiếu ngày; chuỗi FP ngắt cả khi ngày giữa có TP/can thiệp/censor. Chuỗi chấm được cắt tại đầu/cuối cửa sổ chấm, không phải số episode, số lần cần xử lý hoặc cơ chế dedup mới. Chuỗi dài không tự chứng minh mức tải nhân sự chấp nhận được. Biểu đồ FP cuối kỳ về 0 vì các ca không sự kiện có thể bị right-censor/can thiệp, không suy ra chất lượng tăng.

**Tính đủ giai đoạn trước chấm:** `pre_score` gồm origin khởi tạo và 28 ngày warmup, tổng 29 origin. Validation trước 29/07 vẫn dùng forecast gốc nên hai cấu hình cùng 2.822 signal/263 FP; toàn kỳ C00 6.428 so S25 9.769 signal. Test có tham số khóa từ tháng 7 nên áp S25 cả pre_score: 1.645→2.771 signal, 178→595 FP; toàn kỳ 6.453→11.182 signal và 603→1.953 FP. Chênh toàn kỳ là +4.729 signal/+1.350 FP, gồm +1.126 signal/+417 FP trước chấm. Trong 92 early mới test, cảnh báo hợp lệ sớm nhất của 14 event nằm trước chấm và 78 nằm trong chấm; không so toàn bộ lợi ích này với riêng tải 64 ngày mà bỏ phần trước chấm. Validation có 77 early mới đều bắt đầu trong chấm; cả hai kỳ không mất early cũ.

**Phân bố FP mới:** test có 933 item-ngày FP mới trên 236 item. Top 5 tuyến chiếm 275/933 = 29,4748%; top 10 item chiếm 131/933 = 14,0407%, nên không tập trung vào một vài item. Validation tương ứng 987 FP mới/251 item; top 5 tuyến 27,8622%, top 10 item 13,2725%. Bảng đầy đủ giữ cả tuyến/item có số đếm 0: 46 tuyến và 920 item mỗi kỳ.

| Tuyến test, xếp theo FP mới để mô tả | C00 FP | S25 FP | FP mới | Signal tăng trong chấm | Early mới |
|---|---:|---:|---:|---:|---:|
| Japan / NTT Docomo | 24 | 85 | 61 | 196 | 0 |
| Thailand / AIS | 24 | 79 | 55 | 181 | 6 |
| Japan / SoftBank | 33 | 87 | 54 | 213 | 5 |
| Japan / au (KDDI) | 10 | 64 | 54 | 225 | 4 |
| Malaysia / CelcomDigi | 17 | 68 | 51 | 171 | 5 |

Không dùng bảng test này để bỏ tuyến, chọn lại cấu hình hoặc đặt ngưỡng riêng. Trong 933 FP mới test: tồn tại origin là 1/2/3–5/>5 lần lượt 49/125/424/335 item-ngày; 341 có receipts H14 đã biết trước quyết định, 592 không có. Dự báo cạn sau 12–14 ngày chiếm 865/933; đây là lead dự báo của FP, không phải early lead của event thật. Các lát cắt chỉ mô tả, không xác định nguyên nhân hoặc cho phép đổi H14/tồn/nhập. Không suy ra toàn bộ model dự báo thấp.

**Sản phẩm và kiểm mới thực chạy:** thêm [bộ phân tích](../../web/backend/research/forecast_alarm_burden.py) và [18 ca kiểm mới](../../web/backend/tests/test_forecast_alarm_burden.py). 35 targeted = 18 mới + 17 audit đạt; help đạt. Một lượt đầu bị lỗi tạo thư mục tạm của pytest; chuyển `--basetemp` vào checkpoint local rồi chạy đủ 35 đạt, không sửa source cũ. Không lấy 97 test hoặc verifier F4 lịch sử làm kiểm mới. Runner pin manifest/receipt F3/F4 và audit, kiểm artifact/parent snapshot; gọi scorer độc lập chỉ chấm lại output có sẵn, không replay. Bộ kiểm báo cáo riêng còn đối chiếu từng signal/nhãn bằng quét trực tiếp, scorer gốc, tổng bảng/ngày/chuỗi; đạt 2 kỳ × 2 cấu hình, 14 artifact báo cáo khớp hash. Biểu đồ PNG đã xem trực tiếp.

- [Báo cáo HTML và CSV local](../../outputs/research/forecast-alarm-burden/alarm-burden-44a58840-4b39-4c8f-a89a-cd4784a23862/report.html), [summary](../../outputs/research/forecast-alarm-burden/alarm-burden-44a58840-4b39-4c8f-a89a-cd4784a23862/summary.json), [manifest](../../outputs/research/forecast-alarm-burden/alarm-burden-44a58840-4b39-4c8f-a89a-cd4784a23862/manifest.json).
- Manifest SHA256 `dde1649d283e83c1257d6f894c4bcfdb658dc0ac4244c9b671af4d8a4bf30e5b`; [kiểm báo cáo](../../outputs/research/forecast-alarm-burden-checkpoint/verification.json), [bảo toàn](../../outputs/research/forecast-alarm-burden-checkpoint/preservation.json), code-lock/preflight/command/log trong cùng checkpoint. Bảo toàn 1.644 file protected, 239 tracked ngoài MD, mã ứng dụng và toàn bộ F1–F4; không truy cập DB nên không nhận vừa kiểm lại bảng DB.

**Kết luận và điểm dừng:** phân tích đánh đổi hoàn tất local. S25 đạt mục tiêu early hồi cứu với FP/tải tăng và chuỗi lặp dài; chưa có mức FP, tần suất hay tải nhân sự được nghiệp vụ chấp nhận. Giữ S25 là kết quả nghiên cứu bổ sung, chưa thay phương án chính `m3-implementation`, không tích hợp hoặc sửa tham số sau test. Bước tiếp có thể dùng bảng này để thảo luận đánh đổi; triển khai ứng dụng hay thử hướng mới cần phạm vi riêng. R07/T14 tiếp tục chưa nghiệm thu. [Bàn giao](../../docs/development.md#handoff-chg075-alarm-burden).

**Hiện hành CHG-075 F4 — 27/10/2026, hoàn tất local:** [C00+S25 khóa từ F3 đã kiểm độc lập](#forecast-postprocessing-f4):S25test285/578=49,3080% so C00193/578=33,3910%;precision66,7646% so80,6202%,FP1.358 so425. F3validationS25=228/486=46,9136%; không reselect/refit hoặc gọi stress là accuracy điểm tăng.97targeted vàbảo toàn đạt; F1/F2/F3/app/model/default/DB nguyên, không GitHub. Chỉ đạt mục tiêu làm việc trên hai tập hồi cứu; R07/T14 chưa nghiệm thu. Các mục F1–F3 bên dưới giữ checkpoint lịch sử.

**Hiện hành CHG-075 F3 — 27/10/2026, hoàn tất local:** [đủ13validation đã kiểm độc lập](#forecast-postprocessing-f3), khóa S25 stress×1,25:228/486=46,9136%, precision60,6383%,FP1.369 so C00:151/486,76,2585%,FP382. Không gọi stress là accuracy điểm tăng; F1/F2/app/model/default giữ nguyên,88targeted đạt và1.406protected/239tracked ngoàiMD nguyên. Người dùng đã giao làm F4 sau F3; tại checkpoint này F4 chưa chạy. Không DB/refit/commit/push/CI, R07/T14 chưa nghiệm thu.

**Hiện hành CHG-075 F2 — 27/10/2026, hoàn tất local:** [protocol/hậu xử lý/verifier độc lập](#forecast-postprocessing-f2) đã có,72targeted đạt gồm40ca F2 mới. Chỉ kiểm synthetic; chưa tính tham số hoặc chạy ứng viên validation/test thật, chưa có kết quả mới đạt45%. F1/model/app/default giữ nguyên; không DB/refit/commit/push, F3–F4 chưa bắt đầu, R07/T14 chưa nghiệm thu. Mục F1 ngay dưới giữ vai trò checkpoint trước F2.

**Hiện hành CHG-075 F1 — 27/10/2026, hoàn tất local:** [kiểm đầu vào/identity](#forecast-identity-f1) giữ validation151/486 và test193/578, 171.120đường/2.395.680bước H14 khớp. Chỉ thêm checker nghiên cứu và tests, không chạy ứng viên hoặc F2–F4; không commit/push GitHub theo yêu cầu mới. Model/app/default giữ nguyên, không truy cập DB; R07/T14 chưa nghiệm thu.

**Checkpoint kế hoạch trước F1:** [Hậu xử lý forecast đã khóa](#forecast-postprocessing-v1) mở rộng hướng chỉ thử bốn alpha thành13cấu hình, khóa tham số sau warmup. Kế hoạch này giữ nguyên cho các mốc chưa được giao; kết quả F1 chỉ chứng minh identity, không chứng minh phương pháp tối ưu đạt45%.

E92 bổ sung web/backend/research/daily_panel.py, protocol daily-panel-validation-v2:3ứng viên LightGBM (pooled Poisson, pooled weightedL1, riêng tuyến weightedL1),350cây/leaves15/minchild60/lr0,04/lambda10/seed42. Reuse evaluator chung; v1 giữ predictions/metrics/selection giống byte. V2 thêm count/units-per-order từ order đã audit, tín hiệu thị trường/country đến origin, weekday56/182/365 và lag364/365/366 của ngày target. Lag năm chưa có giữ NaN feature, không thay actual thiếu bằng0. Lịch target biết trước; không đưa actual/forecast target vào feature.

Chạy từ root sau load_env.ps1 bằng Python .venv-m3: python -B -m web.backend.research.daily_panel --source-run SOURCE. SQL chỉ≤30/09/2025; bảng đầu vào phải đủ lịch quan sát. Chọn H1–7 MAPE→MAE→ID/coverage100%, không dùng test. V2 đã chạy168fits/35.910forecast/60nhóm metric; validation mean45,971604%,0/10≤20%, cải thiện9/10tuyến so v1 nhưng còn bias âm. Chưa thay serving hoặc đưa vào sổ tồn. [Ma trận cổng chưa đóng](../ACCEPTANCE.md).

web/backend/research/daily_validation.py kiểm tra dự báo trực tiếp từng ngày trên top10 theo quantity **train**, đối chiếu danh sách final đã khóa. Không sửa M2, target/split/MAPE, bảng forecast hoặc selection ứng dụng.

Protocol daily-validation-v1 ghi manifest trước truy vấn/fit. SQL chỉ đọc aggregate đến30/09/2025; yêu cầu lịch quan sát đầy đủ01/01/2024–30/09/2025, từ chối thiếu ngày/null. Origin validation30/06–29/09; horizon1–14, chỉ chấm target trong validation. Giữ mọi ngày0 trong MAE/WAPE/bias/coverage; MAPE chỉ actual dương. Đây là validation đã sử dụng, không là holdout độc lập.

Tám phương pháp cố định: last, seasonal7, mean28, mean90, MAPE-weighted median90, weekday median90, LightGBM Poisson và LightGBM weighted L1. Baseline median MAPE dùng actual dương trong lịch sử để tối ưu loss MAPE, không loại ngày0 khỏi bảng đánh giá. Weighted L1 dùng trọng số1/max(y,1), vẫn giữ nhãn0. Hai model pooled top10 dùng150cây/leaves15/minchild100/lr0,03/lambda10/seed42; rolling365/refit7. Features từ prefix kết thúc origin: lag/mean/std, weekday lịch sử, tuyến, horizon và lịch target biết trước. Training target≤fit_cutoff.

Chọn model/tuyến bằng MAPE H1–7 → MAE → ID, coverage100%; H8–14 báo riêng cùng model. Manifest có status/protocol/code/input/requirements hashes, runtime/seed, fitlog cutoff và clipping, CSV predictions/metrics/selection; tất cả trong **outputs/research ignored local**.

Chạy từ root sau load_env.ps1: python -B -m web.backend.research.daily_validation --source-run SOURCE, dùng Python của .venv-m3. Thay SOURCE bằng UUID source_import complete thật. Mỗi lần tạo thư mục mới, giữ run trước. Đây không phải command thay model ứng dụng.

E91:28fits/95.760forecast/160nhóm metric. Lựa chọn validation H1–7 mean49,451918%,0/10≤20%; so phân bổ M3 cùng623cặp/tuyến mean51,905954%, tốt hơn ở7/10tuyến nhưng vẫn thiếu mục tiêu. Model mới có bias âm; chưa kiểm độc lập/test, chưa đưa vào chính sách tồn hoặc dashboard forecast. Không suy ra dữ liệu không thể dự báo dưới20% chỉ từ tám phương pháp này. [Phạm vi và bằng chứng](../IMPLEMENTATION.md).

<a id="early-warning-risk-v1"></a>
## CHG-075 — Hướng thử cảnh báo rủi ro trên đường tồn cố định

**Kế hoạch trước đó, giữ để tra cứu:** hướng chỉ thử bốn alpha và quy tắc lựa chọn bên dưới được mở rộng bởi [forecast-postprocessing-v1](#forecast-postprocessing-v1). Alpha vẫn là nhóm đối chứng stress trong ma trận mới; không tự chạy riêng mốc cũ. Phần audit đã hoàn tất ở mục kế tiếp giữ nguyên giá trị bằng chứng.

**Checkpoint kế hoạch trước lượt mới: chưa có code/run/kết quả mới.** Người dùng chọn ưu tiên báo trước ít nhất7ngày cho≥45% sự kiện và chưa thay cấu hình mặc định. Đây là hướng tiếp theo sau CHG-074; [báo cáo đã kiểm ở nhánh nghiên cứu67d2ab6](https://github.com/khanhnguyenpham/Sigma/blob/67d2ab6a19f86101acdc58af7fec788c3a48b093/M3/docs/research.md#inventory-alert-safety-step5). Không đưa code nghiên cứu hoặc output cũ vào nhánh ứng dụng trong lượt lập kế hoạch này.

### Vì sao không triển khai lại SS days×1

Code ứng dụng hiện đã có SS=ceil(mean forecast14 × safety_days × multiplier), mặc định safety_mode=days/multiplier1/ROP forecast. policy_replay nối tồn, cập nhật quyết định và cảnh báo mỗi ngày, ETA7. Chọn lại cùng cấu hình không tạo thuật toán hoặc kết quả mới: toàn kỳ01/10–31/12/2025 cả policy cũ và D-days×1 đáp ứng14437/15968, thiếu1531, fill90,412074%,3245đơn.

33,3910% (193/578) là early của D-days×1 **sau warmup**; 34,391350% (986/2867) thuộc alert replay theo đợt **không đặt mới**. Chúng khác đơn vị sự kiện, kỳ chấm và can thiệp nhập, không phải trước/sau của cùng phép thử. D-SS0 đạt45,7944% nhưng thay đường tồn và làm thiếu1753 so969 của days×1 trong cùng kỳ chấm D; không dùng việc bỏ SS như bằng chứng phát cảnh báo tốt hơn trên cùng sự kiện.

Cập nhật cảnh báo hằng ngày trên A/B cùng sự kiện chỉ thêm3ca test (986→989/2867). Muốn đạt45% trên A/B cần1291ca, tức thêm302ca soB trong khi chỉ1317ca đủ khoảng cách thời gian; không trông chờ đổi tần suất đơn thuần. Vì ứng dụng có nhập hàng, hướng đề xuất lấy **D-days×1** làm đối chứng chính và tách thử quyết định cảnh báo khỏi chính sách tồn.

### Phép thử được đề xuất

1. Dùng nguồn/forecast/policy/cohort đã frozen của CHG-074, không refit hoặc phân bổ lại. Dựng đường tồn D-days×1 một lần bằng policy cơ sở; khóa ledger, đơn đặt, receipts/ETA và các episode cạn. Mọi cấu hình cảnh báo phải đối chiếu nguyên hash các bảng này. Không tự tái đặt hàng theo cảnh báo thử nghiệm.
2. Giữ dự báo điểm chính để trình bày và đánh giá dự báo. Tạo riêng **đường tiêu thụ rủi ro = forecast từng ngày × alpha**, bốn alpha cố định: **1,00 / 1,10 / 1,25 / 1,50**. Dùng tồn hiện tại và chỉ receipts đã biết trước quyết định ngày đó để chiếu cạn trongH14. Alpha1 là đối chứng. Số ngày SS, lượng tồn, ROP/MOQ/ETA và lệnh nhập vẫn lấy từ đường cơ sở, không lấy từ đường rủi ro.
3. Phát cảnh báo rủi ro khi đường stress cho thấy cạn trongH14, đánh giá lại mỗi ngày. Mức alpha lớn có thể đưa cảnh báo xuất hiện sớm hơn, nhưng cũng có thể tăng cảnh báo sai. Alpha không phải xác suất, khoảng tin cậy hay dự báo đã cải thiện; không tự gắn nhãn xác suất80/90/95%. Forecast bằng0 vẫn bằng0 khi nhân, nên hướng này có giới hạn và có thể không đạt45%.
4. Chỉ dùng thông tin có ở ngày quyết định; actual sau đó chỉ được dùng chấm. Không dùng ngày cạn thực tế để đặt alpha, chọn ngày cảnh báo hoặc khởi tạo đường tồn. Causal test thay actual tương lai phải giữ nguyên cảnh báo trước cutoff. Cảnh báo mới không làm thay đổi lịch nhập đã khóa; không nhận đã ngăn cạn từ phép thử này.

### Chấm trên cùng sự kiện

- Episode cạn dương→0, chỉ episode mới sau tồn dương trở lại; giữ các ca receipts rồi cạn cùng ngày. Khóa cùng ID/ngày/số episode ở mọi alpha, không đổi mẫu số vì thay cảnh báo.
- Cảnh báo gắn sự kiện đầu tiên trong14ngày tiếp theo; một episode chỉ tính một lần bằng cảnh báo hợp lệ sớm nhất. Early khi ngày cạn−ngày phát≥7; không dùng predicted_lead thay actual_lead và không hạ mốc7.
- Precision theo item/ngày cảnh báo, tách với recall/early theo episode. Nếu không có sự kiện, early=null và không nhận đạt45%. Stock0 hiện tại không được biến thành dự báo một sự kiện tương lai.
- Giữ28ngày warmup: validation chạy01/07–30/09, chấm29/07–30/09; test chạy01/10–31/12, chấm29/10–31/12. Cảnh báo warmup được đối chiếu với episode thuộc kỳ chấm. Giữ can thiệp nhập/chưa chấm và right-censor như CHG-074, không tự chuyển thành FP/TP; sự kiện đã quan sát vẫn chấm.
- Đối chứng kỳ test đã biết có193/578=33,3910%;45% tương ứng ít nhất261/578, cần thêm68episode báo sớm nếu giữ nguyên tập này. Validation có151/486, cần219/486, cũng thêm68. Đây là số cần đạt từ kết quả cũ, **không phải dự đoán thử mới sẽ đạt**; runner/verifier phải tái lập counts trước so sánh.
- Chẩn đoán riêng trần cơ hội: một episode chỉ có cơ hội báo sớm nếu tồn tại ngày quyết định hợp lệ trước nó7–14ngày, tồn lúc đó dương và episode đó là sự kiện đầu tiên trong14ngày sau ngày cảnh báo. Đếm cơ hội từ actual chỉ làm chẩn đoán hậu kiểm, không cấp cho thuật toán. Nếu trần validation dưới45%, ghi giới hạn protocol/đường tồn và dừng, không gán cảnh báo khi tồn0 hoặc bỏ các episode khó khỏi mẫu số để ép đạt.
- Báo thêm precision/recall, TP/FP, cảnh báo/ngày, item-ngày được cảnh báo, ngày báo trước và sai số ngày cạn; ca can thiệp/thiếu nhãn, chênh lệch episode được báo sớm và cảnh báo sai soalpha1. Fill/thiếu/tồn/đặt/pending phải giữ nguyên giữa alpha, vì không đổi vận hành. ROP N7 giữ riêng, không cộng numerator hoặc nhận đạt R07 cũ.

### Validation, lựa chọn và điểm dừng

Khóa bốn alpha, công thức, nguồn/forecast/cohort và code trước đọc kết quả mới. Chạy đủ bốn trên validation. Trong các alpha có early≥45%, chọn tối đa **một đại diện có precision cao nhất**; hòa thì ít item-ngày cảnh báo hơn rồi alpha thấp hơn. Nếu không có alpha đạt45%, báo chưa đạt và dừng ở chẩn đoán validation, không tự mở rộng grid. Không dùng test chọn hoặc sửa alpha. Việc chọn theo precision chỉ là quy tắc khóa đại diện nghiên cứu, không là xác nhận mức FP phù hợp kinh doanh.

Nếu có đại diện, test chỉ alpha1 và đại diện đã khóa; mọi kết quả vẫn là hồi cứu vì test đã được xem. Không tuyên bố bằng chứng holdout độc lập hoặc chắc chắn hiệu quả tương lai. Nếu test không đạt45%, ghi chưa đạt; không đổi mẫu số/SS/tồn đầu để làm đẹp. Nếu đạt, báo rõ mức tăng FP/số cảnh báo trước khi người dùng quyết định có đưa vào ứng dụng. Chưa có mức FP hoặc tần suất cảnh báo được chấp nhận, nên chưa tự đặt giới hạn hoặc nâng nghiệm thu.

Đầu ra dự kiến: thư mục local mới, protocol/source/code/selection hashes; đường cơ sở frozen; cảnh báo và đối chiếu episode từng alpha; metrics/CSV/HTML và verifier tính độc lập. Tái sử dụng hàm projection hiện có nhưng verifier không dùng helper sản xuất làm kỳ vọng. Không thêm dependency, API/schema/run kind hoặc cài lịch ở giai đoạn nghiên cứu. Công thức/đường stress phải mang nhãn nghiên cứu riêng, không thay forecast và các run cũ. Chỉ code/tests/docs không nhạy cảm được push nếu sau này được giao triển khai; raw/DB/run luôn local.

Lượt này chỉ lập kế hoạch và bảo toàn; chưa tạo protocol máy đọc, viết runner/verifier, chạy validation/test mới hoặc thay mặc định. Giữ R07/T14 chưa nghiệm thu. [Kế hoạch từng mốc](../../docs/planning/PLAN.md#chg-075).

<a id="opportunity-audit-v1"></a>
## CHG-075 — Audit đối chứng và trần cơ hội, chưa thử alpha

Người dùng giao riêng bước1–2 ngày27/10/2026. Nhánh codex/early-warning-opportunity-audit từ86a0162 của m3-implementation; nhánh ứng dụng và research CHG-074 cũ không thay đổi. Protocol máy đọc web/backend/configs/inventory-alert-opportunity-audit.json, SHA256caa57e2d16c20cb9013b7603e3001a75b3a9a090ed4df0ae5861b6cc99226530. Khóa D-days-m1-cover7, period/warmup và hashes manifest/receipt/input/result của hai bundle CHG-074.

CLI web/backend/research/inventory_alert_opportunity_audit.py tái dùng pure_window của app trên inputs frozen. Snapshot chỉ giữ date/source sequence, không timestamp gốc; adapter dùng timestamp đại diện trong cùng ngày và giữ thứ tự source sequence của từng item. Đây là tái lập tồn/cảnh báo cuối ngày UTC, không nhận tái dựng timestamp giao dịch gốc. So từng trường ledger/SS/ROP/IP/Q, initialization, từng transaction, orders, episode và depletion alarms với kết quả đã sealed; đối chiếu cả cases và metric precision/recall/MAE/intervention/censor, không chỉ193/578.

Verifier riêng inventory_alert_opportunity_verification.py không import runner hoặc helper inventory/alerts. Tự tái dựng stock/fulfill/shortage/episode từ initial history/sales/receipts frozen, tính projection với receipts biết trước Q mới và chấm event-first. Ledger SS/ROP/Q đối chiếu kết quả đã được verifier CHG-074 kiểm độc lập; không nhận đã viết lại toàn bộ thuật toán nhập. Bằng chứng nguồn là previously_verified_frozen_inputs_and_results, không raw CSV/DB re-audit. App code hash phải giữ2a02ba9e9069e83c25e0588da0b19c228ffbb550662b85644d6abcf872992dda.

Trần cơ hội day-first được đối chiếu event-first: có ít nhất một ngày quyết định trước episode7–14ngày, closing>0 và episode đó là sự kiện đầu tiên sau ngày quyết định. Lưu từng candidate day/episode và lý do không đủ cơ hội: không có ngày quyết định, bị episode trước chặn, hoặc không có tồn dương. Ngày có nhiều cảnh báo không nhân episode; tồn0 kéo dài không tạo event; warmup vẫn được dùng. Trần là hậu kiểm theo đường tồn/protocol này, không là forecast, early rate thực đạt hoặc bảo đảm alpha sẽ đạt nó. Không dùng trần để chọn alpha bằng test.

```powershell
python -m web.backend.research.inventory_alert_opportunity_audit audit --validation-run <frozen-validation-run> --test-run <frozen-test-run> --output-root outputs/research/early-opportunity-audit
python -m web.backend.research.inventory_alert_opportunity_audit verify --run-dir <new-audit-run>
```

Mỗi audit tạo UUID mới, không ghi đè parent hoặc run cũ; JSON gzip deterministically sealed. Có replay/cases/opportunities từng split, metrics/report.html và manifest. Manifest giữ calculated_unverified; chỉ có receipt riêng verification.json sau kiểm độc lập, kiểm lại giữ timestamp/bytes. Parent hashes được pin trong protocol; sửa/xóa parent/artifact hoặc reseal phép tính sai phải bị chặn. Không thêm thư viện hoặc gọi DB trong CLI.

262Python BE/M2 (17ca mới) đạt trước native audit, pipcheck/help đạt. Ca6/7/14, prior episode, same-day episode, stock0/recovery/receipt rồi cạn, warmup/repeat alarm, intervention/censor, no-event/null, future mutation và forged physical ledger. Lượt targeted đầu có lỗi date object/ISO boundary và một fixture tmp bị sandbox chặn; đã chuẩn hóa date ở adapter, chạy quyền local, không đổi phép tính app. Full262 và targeted17 cuối đạt. Code/protocol khóa trước kết quả tại outputs/research/early-audit-checkpoint/code-lock.json; kết quả và cổng ghi sau kiểm thực. Chưa thử alpha hoặc nghiệm thu R07/T14.

Lượt native đầu dừng trước kết quả do policy seed validation không có ID DB. Adapter đã thêm ID đại diện âm chỉ để đáp ứng metadata của pure_window, không dùng trong phép tính hoặc ghi DB; ca hồi quy xác nhận đường tồn/đơn/cảnh báo giống nhau khi có hoặc không có ID. Giữ nguyên code-lock/command/stdout lần đầu và folder/log lỗi local; khóa lại code trước lượt audit mới, không chỉnh thuật toán theo kết quả. Full262 và targeted-v2.xml17ca đạt trước lượt audit mới.

### Kết quả hai bước đã kiểm độc lập

Native audit tại `early-warning-opportunity-audit-v1-8e5028c3-a382-4502-8c4e-50e8536903ba`, từ app code không đổi. Verifier chạy thành công trên cả validation và test, tự dựng physics/projection/scoring theo event và đối chiếu trần event-first với day-first. Kiểm lại receipt giữ bytes/timestamp và 10artifact gốc; sửa replay rồi reseal, sửa candidate day rồi reseal và xóa artifact đều bị chặn.

| Kỳ | Đối chứng báo sớm | Episode có cơ hội | Trần cấu trúc | Cần để ≥45% | Cần thêm so đối chứng | Cơ hội còn chưa báo sớm |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 151/486 = 31,0700% | 449/486 | 92,3868% | 219 | 68 | 298 |
| Test hồi cứu | 193/578 = 33,3910% | 524/578 | 90,6574% | 261 | 68 | 331 |

Giữ nguyên denominator486/578, không loại các episode không có cơ hội. Test có54episode không đủ điều kiện:42bị episode trước chặn mọi ngày cần báo sớm,12không có tồn dương trên các ngày còn hợp lệ; không có ca thiếu ngày quyết định. Validation có37ca:18bị episode trước chặn,19không tồn dương,0thiếu ngày. Cách chia lý do có thứ tự: ngày quyết định → không bị episode trước chặn → closing>0; không cộng trùng các lý do.

**45% chưa bị trần cấu trúc này ngăn chặn.** Trên test cần thêm68trong331cơ hội chưa báo sớm, nhưng việc có ngày cảnh báo hợp lệ **không bảo đảm** forecast hoặc bốn alpha đề xuất sẽ phát hiện đúng. Số524/578=90,6574% sử dụng ngày cạn thực tế để chẩn đoán hậu kiểm; không được đưa ngày/cờ cơ hội vào feature, policy hay cảnh báo, không quảng bá thành early rate dự báo. Trần của A/B cũ45,936519% và trần D90,6574% khác protocol/đường tồn, không phải model cải thiện.

Bước1 đạt: test tái lập193/578, precision80,6202%, recall81,1419%, MAE4,9808ngày, alarmTP1768/FP425, can thiệp1990, thiếu nhãn625; validation151/486, precision76,2585%, recall79,0123%, MAE4,8542ngày, alarmTP1227/FP382, can thiệp1665, thiếu nhãn332. Precision theo item/ngày cảnh báo, early/recall theo episode; không gộp số alarmTP vào numerator193. Các bảng ledger/SS/ROP/IP/Q, orders và transaction/episode/depletion alarms đã khớp artifact frozen, không chỉ khớp metric tổng.

262Python BE/M2 (17ca mới) và targeted-v2 17/17, pipcheck/help đạt. Bằng chứng native dùng source/parent đã verified và pinned hashes; không nhận đã đọc lại raw CSV hoặc đối soát nguồn DB như một nghiên cứu mới. Đối soát bảo toàn riêng sau audit xác nhận14bảng/1.336hash raw/artifact/protocol cũ và application code nguyên. Không chạy lại React/browser vì chỉ research/config/tests/docs thay đổi; CI vẫn kiểm ứng dụng theo workflow sẵn có.

- Audit manifest SHA256: `23ed307ea2e3fdf86d3f91c2759bc4c6f52deaccc6e199e1c1bb97ee928a35e9`.
- Verification receipt SHA256: `5af9a8bf253d7fa6fe0973de2e77b6016fab226c2e9a167c36b34670a622b8d7`.
- Protocol SHA256: `caa57e2d16c20cb9013b7603e3001a75b3a9a090ed4df0ae5861b6cc99226530`.
- Runner/verifier hashes nằm trong code-lock/manifest/receipt; freeze cuối trước kết quả, không đổi code sau xem trần.

Evidence private outputs/research/early-audit-checkpoint: before/preservation, all-python/targeted-v2 XML, code-lock/command/stdout của native, integrity-checks, summary.json/csv, verified-summary.html và sealed-files. Bundle audit trong outputs/research/early-opportunity-audit/<UUID> có replay/cases/opportunities2split, metrics/report/manifest/verification. Báo cáo gốc giữ nhãn pending ở thời điểm tạo; receipt và verified-summary là bằng chứng kiểm sau đó, không sửa tệp sealed. Giữ folder/log lỗi của lần native đầu và freeze-attempt1 để phân biệt lỗi adapter với kết quả thành công. Dữ liệu/đầu ra không đưa Git.

Lượt này hoàn tất riêng đối chứng và trần. **Chưa thử hoặc chọn alpha, chưa đạt mục tiêu45% bằng thuật toán mới, chưa thay ứng dụng/default hoặc nghiệm thu R07/T14.** Nếu được giao bước kế tiếp, có thể triển khai thử bốn alpha trên validation, đồng thời đo precision/FP/số cảnh báo; test chỉ được chạy sau khóa đại diện. Không dùng kết quả trần test này để mở rộng/chọn lại grid.

<a id="forecast-postprocessing-v1"></a>
## CHG-075 — Kế hoạch hậu xử lý forecast đã khóa, 27/10/2026

**Checkpoint kế hoạch trước F1:** thiết kế dự kiến đã soạn, lúc đó chưa triển khai các mốc kỹ thuật; nay F1 đã hoàn tất riêng tại [kết quả identity](#forecast-identity-f1), F2–F4 vẫn chưa bắt đầu. Người dùng duyệt kế hoạch tài liệu và chọn khóa tham số hậu xử lý sau warmup. Mục tiêu làm việc là early rate ≥45% với báo trước ≥7 ngày trên cùng sự kiện D-days×1; không bảo đảm đạt, không sửa tiêu chí hoặc nâng R07/T14. [Mốc và phạm vi](../../docs/planning/PLAN.md#chg075-forecast-postprocessing), [kiểm/bàn giao kế hoạch](../../docs/development.md#handoff-chg075-forecast-postprocessing).

### Bằng chứng được dùng và giới hạn

Đã đọc code allocation, projection, runner/verifier audit và artifact local; đối chiếu 8 artifact với manifest, hash manifest/receipt và manifest/receipt/input hai parent frozen. Không chạy lại audit, nghiên cứu, fit hoặc nguồn CSV/DB. Đây là kiểm tra bằng chứng đã lưu, không phải kết quả thử nghiệm mới.

| Kỳ | Báo sớm | Có cảnh báo trước 1–6 ngày | Chưa có cảnh báo hợp lệ | Có cơ hội hậu kiểm | Cần để ≥45% | Cần thêm |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 151/486 = 31,0700% | 233 | 102 | 449/486 = 92,3868% | 219 | 68 |
| Test hồi cứu | 193/578 = 33,3910% | 276 | 109 | 524/578 = 90,6574% | 261 | 68 |

Test có 331 sự kiện có cơ hội nhưng chưa báo sớm, với 2.508 ngày quyết định hợp lệ; validation tương ứng 298 sự kiện/2.261 ngày. Đếm trực tiếp từ cases/opportunities đã lưu. Không dùng ngày cạn hoặc cờ cơ hội để tạo, hiệu chỉnh, chọn hay lọc forecast. Mẫu số vẫn 486/578, gồm cả sự kiện không có cơ hội. Trần là hậu kiểm, không là early rate dự báo thực đạt.

Bundle bằng chứng: `outputs/research/early-opportunity-audit/early-warning-opportunity-audit-v1-8e5028c3-a382-4502-8c4e-50e8536903ba`; manifest SHA256 `23ed307ea2e3fdf86d3f91c2759bc4c6f52deaccc6e199e1c1bb97ee928a35e9`, receipt SHA256 `5af9a8bf253d7fa6fe0973de2e77b6016fab226c2e9a167c36b34670a622b8d7`. Receipt có trạng thái verified; manifest gốc giữ calculated_unverified như lúc tạo, không sửa sealed artifact. [Bằng chứng audit chi tiết](#opportunity-audit-v1).

### Phạm vi cố định và chẩn đoán dự kiến

Không sửa/refit/huấn luyện/chọn lại hoặc thay model; không đổi raw, target/A08, split/top10, công thức SS/ROP, safety days, lead time, MOQ, tồn đầu, policy nhập hoặc receipts/ETA. Không sửa API/schema/UI/scheduler/default. Forecast và model gốc bảo toàn; đầu ra ứng viên sau này lưu riêng ở thư mục ignored local mới, không ghi lại run/DB/manifest cũ. Không tạo protocol máy đọc trong lượt tài liệu này.

Code `web/backend/src/modules/forecasting/allocation.py` đang phân bổ hai tổng tuần: trọng số thứ từ 90 ngày, tỷ trọng item từ 30 ngày, dự phòng 90 ngày; chỉ item first_seen ≤origin. Code `web/backend/src/modules/alerts/service.py` chiếu stock/receipts và tìm ngày closing bằng 0 trong H14. Đây là mô tả code đã đọc, chưa là kết luận nguyên nhân bỏ lỡ.

Chẩn đoán đủ bốn tầng, trên cùng tập origin/target có nhãn:

| Tầng | So sánh dự kiến | Giới hạn diễn giải |
|---|---|---|
| Tổng tuyến | Cộng forecast item về tuyến, so actual tổng H1–7/H8–14/H14; tách fixed10 và 36 tuyến còn lại | Không chạy pipeline fit hoặc thay lựa chọn model; không suy mọi tuyến bias âm |
| Phân bổ item | So tỷ trọng forecast và actual trong cùng tuyến/khối tuần, giữ tổng tuyến khi thử phân bổ | Nhu cầu thưa có thể gây sai tỷ trọng dù tổng tuyến đúng |
| Phân bổ ngày | So nhịp theo thứ và các ngày trong từng tuần, giữ tổng item/tuần | Tổng tuần đúng không bảo đảm ngày cạn đúng |
| Nhu cầu trước cạn | So sai số nhu cầu tích lũy H1…H14, sau đó phân tầng early/late/missed | Ngày cạn/cơ hội chỉ dùng hậu kiểm, không dùng tạo forecast hoặc chọn grid |

Đo trên toàn bộ mẫu có nhãn trước khi xem nhóm bỏ lỡ. Nhóm theo kết quả đối chứng chỉ hỗ trợ giải thích; không chọn tập dễ để báo metric. Cơ hội 2.508 ngày có thể chỉ ra chỗ cần kiểm, không xác định hệ số điều chỉnh.

### Tập hiệu chỉnh và chống sử dụng tương lai

- Tập hiệu chỉnh chung: 15 origin 30/06–14/07/2025, chỉ target có nhãn thật từ 01–28/07; tất cả H14 đã quan sát hết ngày 28/07. Dùng mọi tuyến/item hợp lệ, không chỉ nhóm cạn/bỏ lỡ. Không lấy residual in-sample hoặc tự dựng forecast train khi chưa có artifact.
- Khóa hệ số bias, phân tầng nhu cầu, scale và quantile sau cuối ngày 28/07/2025; áp dụng từ 29/07. Mọi cấu hình dùng forecast gốc trước 29/07 để giữ causal warmup. Test dùng đúng tham số này cho các origin của kỳ test, không hiệu chỉnh lại bằng validation cuối kỳ hoặc nhãn test.
- Công thức phân bổ được khóa trước chạy; cửa sổ bán quá khứ 14/28 ngày được đọc cuốn theo origin. Đây là cập nhật đầu vào quá khứ theo công thức cố định, không chọn lại cửa sổ/hệ số. Không dùng ngày >origin, first_seen tương lai hoặc actual thiếu như 0.
- Snapshot daily validation bao phủ 03/06–30/09/2025; test 03/09–31/12/2025, có 28 ngày trước ngày chạy đầu. Không đủ để tái dựng cửa sổ 90 ngày ở đầu kỳ. Vòng đầu chỉ dùng cửa sổ 14/28 ngày; hướng dài hơn phải xác minh nguồn aggregate/hash/provenance trước, không tự đọc thêm raw, refit hoặc giả định đã có dữ liệu.
- Nhãn sau origin chỉ dùng tính residual của tập hiệu chỉnh đã trưởng thành hoặc chấm đầu ra, không cấp cho hàm tạo forecast. Tham số fit từ warmup không được áp ngược vào ngày trước khóa. Thay actual sau cutoff phải giữ nguyên forecast/cảnh báo đã phát trước cutoff theo thời điểm tham số có hiệu lực.
- Các cửa sổ H14 chồng lấn và chỉ có 15 origin hiệu chỉnh; số item lớn không tạo hàng nghìn quan sát thời gian độc lập. Báo rõ rủi ro mẫu ngắn, không suy bảo đảm xác suất hoặc ý nghĩa thống kê từ số dòng.

### Ma trận dự kiến khóa trước chạy: 13 cấu hình

Ký hiệu: `f[i,o,h]` là forecast gốc item i tại origin o, h=1…14; `F[r,o,h]` là tổng item của tuyến r; b là khối H1–7 hoặc H8–14. Các nhóm áp độc lập lên forecast gốc, không nối hoặc ghép tổ hợp. ID theo bảng cũng là thứ tự phá hòa cuối cùng.

| ID | Vai trò | Phép thử |
|---|---|---|
| C00 | Đối chứng | Vector forecast gốc |
| S10 | Stress | Nhân 1,10 |
| S25 | Stress | Nhân 1,25 |
| S50 | Stress | Nhân 1,50 |
| B00 | Forecast điểm ứng viên | Hiệu chỉnh bias toàn cục |
| B07 | Forecast điểm ứng viên | Hiệu chỉnh bias theo hai khối horizon |
| BND | Forecast điểm ứng viên | Hiệu chỉnh bias theo khối × mức nhu cầu tuyến |
| I14 | Forecast điểm ứng viên | Trộn tỷ trọng item quá khứ 14 ngày |
| I28 | Forecast điểm ứng viên | Trộn tỷ trọng item quá khứ 28 ngày |
| D14 | Forecast điểm ứng viên | Trộn trọng số thứ quá khứ 14 ngày |
| D28 | Forecast điểm ứng viên | Trộn trọng số thứ quá khứ 28 ngày |
| R75 | Đường rủi ro | Bù quantile sai số tích lũy 0,75 |
| R90 | Đường rủi ro | Bù quantile sai số tích lũy 0,90 |

#### C00 — Identity

| Nội dung | Thiết kế dự kiến |
|---|---|
| Giả thuyết/cơ chế | Không cải thiện; chứng minh đường so sánh không đổi khi thay forecast bằng chính nó |
| Đầu vào/phép biến đổi | Input forecast frozen, closing/receipts và lịch quyết định frozen; giữ từng giá trị vector |
| Tham số/chống tương lai | Không học tham số; cùng thông tin receipts đã biết trước quyết định mới |
| Đối chứng/metric | Khớp projection/cảnh báo/cases/metric baseline, không chỉ khớp 151/193; hash ledger/orders/events nguyên |
| Rủi ro/điều kiện dừng | Lệch bất kỳ identity, provenance, cohort hoặc vector coverage: dừng toàn bộ, không chạy ứng viên |

#### S10/S25/S50 — Đối chứng stress

| Nội dung | Thiết kế dự kiến |
|---|---|
| Giả thuyết/cơ chế | Nhu cầu dự phóng lớn hơn có thể làm projection nhìn thấy cạn sớm hơn |
| Đầu vào/phép biến đổi | `f' = alpha × f`, alpha cố định 1,10/1,25/1,50; alpha 1 là C00, không thêm cấu hình |
| Tham số/chống tương lai | Hệ số đăng ký trước chạy, không suy từ ngày cạn/cơ hội; chỉ áp từ ngày hiệu lực chung |
| Đối chứng/metric | C00; early/precision/FP/tần suất, MAE/WAPE/bias chỉ để mô tả đường stress |
| Rủi ro/điều kiện dừng | Forecast 0 vẫn 0; có thể tăng FP, quy tắc ghép sự kiện đầu tiên vẫn giới hạn cơ hội. Không gọi tăng cảnh báo là tăng accuracy; không tăng alpha ngoài grid nếu chưa đạt |

#### B00/B07/BND — Hiệu chỉnh bias điểm

| Nội dung | Thiết kế dự kiến |
|---|---|
| Giả thuyết/cơ chế | Sai lệch tổng mức hoặc khác nhau theo horizon/nhu cầu có thể làm nhu cầu tích lũy sai; sửa cả bias âm lẫn dương |
| Đầu vào/phép biến đổi | Với các cặp tuyến-origin-khối thuộc tập hiệu chỉnh, `g = sum(actual) / sum(forecast)`; nhân vector item bằng hệ số nhóm, không sửa model |
| Ma trận/tham số | B00 dùng g toàn cục. B07 dùng hai nhóm b; BND dùng b × thấp/cao, mức tuyến từ mean actual/ngày 01–28/07 so trung vị giữa các tuyến, bằng trung vị thuộc nhóm thấp; khóa nhóm sau warmup |
| Co hệ số/fallback | Nhóm B07/BND dùng `0,5 × g_nhóm + 0,5 × g_toàn_cục`. Mẫu số nhóm bằng 0 kế thừa tỷ lệ nhóm cha: khối rồi toàn cục; toàn cục không xác định dùng 1. Không co thêm lần nữa sau kế thừa |
| Chống tương lai/đối chứng | Chỉ 15 origin đủ nhãn; hệ số giữ nguyên qua validation/test; so C00 trên cùng mẫu |
| Metric/rủi ro/dừng | MAE/WAPE/bias và early/FP; mẫu ngắn, có thể làm xấu tuyến khác và không cứu forecast 0. Giá trị thiếu/không hữu hạn hoặc âm ngoài định nghĩa: dừng cấu hình, không tự clip/tune; không gọi là cải thiện điểm nếu metric không chứng minh |

Không dùng tỷ lệ thực bán trên nhóm bỏ lỡ hoặc nhu cầu ngay trước ngày cạn để tính hệ số. Đây là hậu xử lý tỷ lệ thống kê, không thêm hồi quy, model mới hoặc cơ chế chọn lại model.

#### I14/I28 — Phân bổ xuống item

| Nội dung | Thiết kế dự kiến |
|---|---|
| Giả thuyết/cơ chế | Tổng tuyến có thể hợp lý nhưng tỷ trọng SKU gần đây lệch với tỷ trọng gốc; sửa cơ cấu có thể phát hiện item rủi ro sớm hơn |
| Đầu vào/phép biến đổi | Tại mỗi tuyến-origin-ngày forecast, tỷ trọng gốc `s0 = f/F`; tỷ trọng lịch sử `sW` từ tổng quantity item trong W=14/28 ngày kết thúc origin. `f' = F × (0,5 × s0 + 0,5 × sW)` |
| Tham số/chống tương lai | W và mức trộn 0,5 khóa trước; chỉ item first_seen ≤origin, chỉ actual_available trong lịch sử ≤origin; không học lại W bằng test |
| Bảo toàn/fallback | Giữ tổng forecast tuyến/ngày và từng khối tuần. Tuyến có tổng lịch sử bằng 0 hoặc F=0 giữ vector gốc; missing actual không phải lịch sử 0 |
| Metric/rủi ro/dừng | So C00: sai số item/tỷ trọng, early/FP, tổng tuyến phải nguyên trong dung sai 1e-8. Có thể chuyển lượng khỏi item khác; thiếu lịch sử, sai eligibility hoặc không bảo toàn: dừng, không đổi cohort |

#### D14/D28 — Phân bổ xuống ngày

| Nội dung | Thiết kế dự kiến |
|---|---|
| Giả thuyết/cơ chế | Sai nhịp ngày có thể làm ngày cạn dự báo muộn dù tổng tuần đúng |
| Đầu vào/phép biến đổi | Trong từng item/khối tuần, chuẩn hóa forecast gốc thành trọng số ngày; trộn đều với trọng số thứ từ tổng bán tuyến W=14/28 ngày đến origin, rồi nhân lại tổng tuần gốc của item |
| Tham số/chống tương lai | W và trộn 0,5 khóa trước; lịch thứ target biết trước, lượng bán chỉ từ quá khứ; cùng eligibility item |
| Bảo toàn/fallback | Giữ tổng từng item/tuần và tuyến/tuần; tổng tuần 0 hoặc tuyến không bán trong W thì giữ vector gốc |
| Metric/rủi ro/dừng | So C00: MAE/WAPE/bias ngày và ngày cạn, early/FP; nhịp ngắn có thể nhiễu hoặc chuyển đỉnh sai. Thiếu nhãn lịch sử hoặc tổng không bảo toàn trong 1e-8: dừng |

#### R75/R90 — Đường rủi ro từ sai số tích lũy

| Nội dung | Thiết kế dự kiến |
|---|---|
| Giả thuyết/cơ chế | Phần nhu cầu vượt forecast đã quan sát có thể cung cấp đường tiêu thụ thận trọng hơn, kể cả forecast gốc bằng 0 |
| Đầu vào/scale | `C = cumsum(f)`; tại mỗi h tính residual `e = (cumsum(actual) - C) / s_i` trên 15 origin hiệu chỉnh. `s_i = max(mean actual/ngày item 01–28/07, 1)`, khóa sau warmup |
| Ma trận/tham số | Với từng h, lấy quantile q=0,75 hoặc 0,90 gộp item-origin có đủ nhãn; quantile nội suy tuyến tính tại vị trí (n−1)q trong mẫu tăng dần; giữ nguyên scale/quantile qua test |
| Phép biến đổi | `C'[0]=0`; `C'[h]=max(C'[h-1], C[h] + s_i × max(quantile_h, 0))`; lấy `f'[h]=C'[h]-C'[h-1]`. Không âm, không thay forecast điểm hoặc tồn; đường này không bắt buộc bảo toàn tổng tuyến |
| Chống tương lai/đối chứng | Chỉ residual đủ nhãn đến 28/07; không dùng cờ sự kiện/cơ hội. So C00, không ghép với nhóm bias/phân bổ |
| Metric/rủi ro/dừng | Early/precision/FP/tần suất; coverage thực nghiệm và pinball loss theo horizon tích lũy. Quantile gộp, cửa sổ chồng lấn và phép ép đơn điệu không tạo bảo đảm coverage; thiếu scale/nhãn hoặc kết quả không hữu hạn: dừng, không tự điền 0 |

Stress và R75/R90 không phải forecast điểm đã cải thiện hoặc xác suất cạn đã hiệu chỉnh. Một quantile residual gộp không đồng nghĩa xác suất cạn 75%/90%. Các ý tưởng thay model/loss/features/selection, tái huấn luyện, thay SS/ROP/nhập, dùng actual tương lai hoặc đổi tần suất cảnh báo để đổi bài toán nằm ngoài phạm vi.

### Phép so sánh công bằng và cơ chế cảnh báo giữ nguyên

Đọc đường D-days×1 đã sealed; không chạy lại `pure_window/policy_replay` bằng forecast ứng viên để tính đơn, ngưỡng hoặc tồn. Mỗi ngày/item lấy closing stock thực hiện trong mô phỏng cơ sở; đưa duy nhất vector ứng viên vào hàm projection hiện có. Ledger, initialization, transactions, SS/ROP/IP/Q, orders/receipts và event ID/date/sequence phải giữ nguyên hash. Fill/shortage/tồn/pending/lượng nhập không đổi; phép thử không chứng minh đã ngăn cạn.

Receipts trong projection chỉ gồm lượng có ETA thuộc H14 và đã biết trước quyết định mới ngày đó: `ordered_on < decision_date` hoặc lot ban đầu hợp lệ, chưa nhận tại origin. Không cộng đơn mới cùng ngày, đơn tương lai hoặc dùng trạng thái received cuối kỳ suy ngược. Điều kiện này phải khớp identity với code hiện có; receipts giả định vẫn mang nhãn mô phỏng.

Giữ stock=0 là already_depleted, không tạo sự kiện tương lai; lần chuyển dương→0 theo giao dịch là episode, phục hồi rồi cạn mới có episode mới, gồm receipt rồi cạn cùng ngày. Gắn cảnh báo với sự kiện đầu tiên trong 14 ngày tiếp theo; một event chỉ tính một lần bằng cảnh báo hợp lệ sớm nhất. Early dùng actual lead ≥7 ngày, không dùng predicted lead để thay. Không gộp ROP N7 vào numerator depletion.

Giữ kỳ chạy validation 01/07–30/09, chấm sự kiện 29/07–30/09; test chạy 01/10–31/12, chấm 29/10–31/12. Cảnh báo warmup vẫn được ghép với sự kiện thuộc kỳ chấm; trước ngày hiệu lực hậu xử lý dùng forecast gốc. Tham số từ tháng 7 có sẵn cho toàn bộ origin test; nêu rõ khác biệt thời điểm sẵn có này, không áp ngược tham số vào đầu validation để làm đẹp kết quả.

Giữ logic can thiệp/right-censor của scorer audit: có sự kiện quan sát trong H14 thì chấm theo sự kiện; không có sự kiện thì xét đơn mới can thiệp theo quy tắc baseline, rồi thiếu nhãn đuôi kỳ, sau đó mới FP. Không tự chuyển ca can thiệp thành FP/TP hoặc bỏ event cuối kỳ đã quan sát. Alarm precision chấm ngày thuộc kỳ score; ghép event có thể dùng alarm warmup như baseline. Không thay denominator 486/578 vì forecast ứng viên.

### Metric, lựa chọn và điều kiện dừng

| Nhóm metric | Báo cáo bắt buộc dự kiến |
|---|---|
| Event | Early numerator/denominator/rate; recall = event có alarm hợp lệ / tổng event; early/late/no-alarm; số event mới được báo sớm và số mất báo sớm so C00 |
| Alarm | Precision = TP/(TP+FP) theo item/ngày; TP/FP; can thiệp và right-censor riêng; tổng alarm, item-ngày alarm, bình quân/ngày, số item bị tác động và phân bố theo tuyến |
| Ngày cạn | MAE và signed bias = predicted date − actual date từ alarm sớm nhất ghép event, kèm số cặp; thêm cùng tập event ghép chung với C00 để tránh so khác mẫu |
| Forecast điểm | MAE, WAPE = sum(abs(f−y))/sum(y), signed bias lượng và bias tỷ lệ; tuyến/item, ngày, H1–7/H8–14/H14 và tích lũy H1…H14; coverage origin-target và số cặp |
| Đường rủi ro | Metric cảnh báo như trên; coverage thực nghiệm `actual cumulative ≤ C'` và pinball loss của C' tại q đăng ký; accuracy điểm chỉ để tham khảo, không dùng làm nhãn cải thiện forecast điểm |
| Bảo toàn | Hash các bảng frozen và forecast gốc; tổng phân bổ đúng cho từng nhóm; fill/thiếu/tồn/đơn không đổi |

MAE và bias lượng giữ các ngày actual=0 có quan sát; actual thiếu không chấm và không điền 0. WAPE/bias tỷ lệ có tổng actual=0 thì null kèm số cặp, vẫn báo MAE. Forecast score dùng cùng mask origin-target có nhãn của đối chứng; không xem nhãn ngoài split hoặc coi đuôi H14 thiếu actual là 0. Không có event thì early/recall null; không có alarm đánh giá được thì precision null. Báo cả tổng và từng tuyến, không tự đặt ngưỡng đạt riêng từng tuyến/item.

Khóa đủ 13 ID, công thức/fallback/ngày hiệu lực, tập hiệu chỉnh, nguồn/hash, cohort, metric và quy tắc chọn trước khi chạy validation. Không loại nhóm vì đã biết trần hoặc lỗi trên test; không thêm tổ hợp/cửa sổ/alpha sau khi xem kết quả. Đầu ra invalid không được chọn; báo lý do thay vì âm thầm đổi công thức hoặc bỏ item khó.

Chạy toàn bộ ma trận validation. Trong ứng viên có đầy đủ forecast/nhãn hiệu chỉnh bắt buộc, bảo toàn đạt và early ≥219/486, chọn tối đa một đại diện: precision hợp lệ cao nhất → ít item-ngày cảnh báo hơn → thứ tự ID trong bảng. Precision null không đủ điều kiện chọn. Công bố cả bảng đánh đổi và so C00; không tự đặt mức FP/tần suất chấp nhận được. Quy tắc chọn đại diện nghiên cứu không phải quyết định đưa vào vận hành.

Nếu không có ứng viên đủ điều kiện đạt 45%, ghi **chưa đạt**, dừng trước test, không mở grid. Nếu có, lưu selection/parameter lock cùng hash trước test; test chỉ C00 và đại diện đã khóa, không chọn lại hoặc hiệu chỉnh bằng test. Test cần ít nhất 261/578; chưa đạt thì ghi chưa đạt dù cải thiện. Nếu đạt, báo rõ FP/tần suất/sai số và chờ quyết định riêng về triển khai ứng dụng; chưa nâng R07/T14.

Test đã được xem; validation cũng đã được sử dụng trước đây, model gốc có giới hạn lịch sử fixed LG U+ test-selected. Không gọi kết quả tiếp theo là holdout độc lập hoặc bảo đảm tương lai. Không cam kết chắc chắn đạt 45%, không lấy trần hậu kiểm thay kết quả.

### Triển khai sau này và sản phẩm dự kiến

Chỉ khi được giao mốc kỹ thuật: bước đầu là kiểm đầu vào/identity trên bundle frozen, không thử ứng viên. Sau identity đạt mới tạo protocol máy đọc, hậu xử lý độc lập khỏi app và verifier không dùng helper sản xuất làm kỳ vọng; kiểm synthetic trước validation thật. Không thêm dependency, API/schema/run kind hoặc scheduler trong nghiên cứu.

Mỗi lượt thực thi sau này dùng thư mục local mới, giữ forecast gốc riêng với forecast điểm ứng viên/đường stress/rủi ro, hash source/code/protocol/parameter/selection, provenance cutoff, bảng cảnh báo/cases/metric/coverage và báo cáo đánh đổi. Không sửa receipt/manifest/output cũ, không đưa raw/DB/env/CSV/private output lên Git. Mốc code/config/tests cần giao riêng và tuân thủ cổng Git hiện có, không tự mở rộng quyền push nhánh ứng dụng.

Nhánh đề xuất sau này: `codex/forecast-postprocessing-study` kế thừa checkpoint audit `ce738c4` cùng commit tài liệu nếu có. Lượt này giữ nhánh `codex/early-warning-opportunity-audit`, chỉ sửa Markdown; không tạo/chuyển nhánh, commit/push, merge hoặc deploy. [Mốc tiếp theo và kiểm tra](../../docs/development.md#handoff-chg075-forecast-postprocessing).

<a id="forecast-identity-f1"></a>
## CHG-075 F1 — Kiểm đầu vào và identity, 27/10/2026

**Nguồn/phạm vi mới:** người dùng giao riêng F1, không cần đẩy GitHub. Hoàn tất local trên `codex/early-warning-opportunity-audit`/`ce738c4`; giữ sáu MD chưa commit từ lượt trước. Không tạo/chuyển nhánh hoặc commit/push; không triển khai hậu xử lý/protocol ứng viên F2, không chạy13cấu hình F3/F4, fit/model/policy replay/DB/app/default.

Thêm [checker F1](../../web/backend/research/inventory_forecast_identity.py) và [15ca synthetic](../../web/backend/tests/test_inventory_forecast_identity.py). Checker pin manifest/receipt audit cũ và protocol cũ, kiểm hash/code/provenance/parent artifacts, cohort920item và toàn bộ lưới ngày quyết định; từ chối duplicate/missing/forecast không đủ14giá trị/âm/nonfinite/bool hoặc lịch sử actual thiếu. Không tạo protocol máy đọc mới; manifest kết quả F1 là bằng chứng kiểm, không là protocol thử ứng viên.

Mỗi split có93origin kể cả origin khởi tạo, 85.560vector forecast và110.400dòng actual lịch sử120ngày×920item. Mọi vector được sao chép identity, không đổi giá trị; forecast origin phải khớp ngày ledger, actual lịch sử28ngày đầu đầy đủ. Chỉ lấy closing và orders từ đường frozen; không gọi `pure_window/policy_replay` để sinh lại đơn trong F1. Orders cùng ngày quyết định không cấp receipts mới, trừ lot ban đầu hợp lệ; chỉ ETA tương lai trongH14. Không dùng actual tương lai hoặc cờ cơ hội làm input projection.

Checker tái sử dụng bộ đọc/chấm audit đã khóa và hàm project của app, đối chiếu từng trường của14bước projection với phép tính scalar độc lập về receipt→demand→closing/state/date/lead, gồm stock0 và forecast lẻ. Verifier audit cũ tái dựng vật lý từ inputs frozen và chấm event-first độc lập; kết quả so với audit replay/cases và parent frozen, không chỉ so tử số. Các bảng ledger/SS/ROP/IP/Q, initialization, transactions, orders và events được giữ hash; không cập nhật policy hoặc chấm lại threshold ROP như một ứng viên.

**Giới hạn bằng chứng projection:** audit/parent cũ lưu ngày dự kiến cạn và alarm tóm tắt, không có toàn bộ path14ngày để so byte. F1 kiểm full path mới giữa project app và scalar reference, rồi đối chiếu ngày cảnh báo/cases/metric với artifact cũ. Không nhận đã so full path mới với một artifact lịch sử không tồn tại. Lần này không tái đọc raw CSV hoặc đối soát DB; lớp bằng chứng vẫn `previously_verified_frozen_inputs_and_results`.

| Kỳ | Item | Vector/alarm rows kiểm | Bước projection kiểm | Early đối chứng khớp | Precision / recall | MAE ngày cạn |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 920 | 85.560 | 1.197.840 | 151/486 = 31,0700% | 76,2585% / 79,0123% | 4,8542 |
| Test hồi cứu | 920 | 85.560 | 1.197.840 | 193/578 = 33,3910% | 80,6202% / 81,1419% | 4,9808 |

Native thành công trên cả hai split sau khóa mã; tổng171.120path/2.395.680bước. Case gzip của cả hai kỳ còn khớp hash case audit cũ. Đây là tái lập đối chứng, **chưa có cải thiện early rate hoặc kết quả mới đạt45%**. Không thay numerator/denominator hoặc dùng trần524/578 làm kết quả dự báo.

### Cách kiểm và đầu ra F1 đã chạy

Từ root, dùng Python `.venv-m3` đã cài project; lệnh sau đã chạy, không nạp env DB. Mỗi lần chạy tạo UUID mới, không ghi đè bundle cũ:

```powershell
.venv-m3/Scripts/python.exe -B -m web.backend.research.inventory_forecast_identity --audit-run outputs/research/early-opportunity-audit/early-warning-opportunity-audit-v1-8e5028c3-a382-4502-8c4e-50e8536903ba --output-root outputs/research/forecast-identity-f1
```

32Python targeted đạt, gồm15F1 mới và17audit cũ; CLI help/pip check đạt. Các ca mới kiểm identity không gọi policy replay, bảo toàn input, vector coverage/duplicate/âm/nonfinite/bool/missing, receipts trước/cùng/sau quyết định, biên6/7/14/stock0, forecast lẻ và path giữa kỳ bị sửa dù ngày cạn không đổi; audit giả bị chặn trước tạo output. Lần đầu29đạt/2lỗi setup do sandbox không tạo được thư mục temp; chuyển `--basetemp` vào workspace cho31đạt, rồi bổ sung kiểm receipt-before-demand với lượng lẻ và chốt32đạt trước native. Giữ XML từng lần, không sửa thuật toán theo kết quả native. Không chạy lại toàn bộ BE/M2/React hoặc browser vì app không đổi; không dùng262tests/CI lịch sử làm kiểm mới.

- Bundle mới: `outputs/research/forecast-identity-f1/forecast-identity-f1-00bc3bcc-7c2b-4f6f-a7ee-aef68ecc13b5`, gồm7artifact sealed và manifest; projections JSONL gzip đủ14bước/row, alarms/cases mỗi kỳ và summary. [Summary local](../../outputs/research/forecast-identity-f1/forecast-identity-f1-00bc3bcc-7c2b-4f6f-a7ee-aef68ecc13b5/summary.json).
- Manifest SHA256: `06d3078e9a221fbf7e15df9a2b4da0b5bf26a8ce1414ed049d010ca584fb90e8`; summary SHA256: `6390df22c542108e1b6f850a1791e0a312d6645b56dfd15b4b32751a420f8d44`.
- Checkpoint mới `outputs/research/forecast-identity-f1-checkpoint`: before/backup sáu MD và diff lượt trước, targeted XML, code-lock/command/native stdout/stderr và integrity. Code F1 SHA256 `4b3ada9487d9745ffd59e96e706b975ed3ad41bc9e47d9cd005156b5a283635f` khóa trước native; app hash vẫn `2a02ba9e9069e83c25e0588da0b19c228ffbb550662b85644d6abcf872992dda`.
- Kiểm sau chạy:7artifact output đúng hash, quét toàn bộ JSONL đủ ngày/path; 52file audit/parent được checker giữ nguyên, kiểm ngoài xác nhận1.346file protected và239file tracked ngoàiMD nguyên. Không truy cập DB nên không nhận đã kiểm lại14bảng. Dữ liệu/path chi tiết private chỉ lưu ignored local, không đưa Git.

**Điểm dừng:** F1 hoàn tất local; F2–F4 chưa bắt đầu, chưa có protocol ứng viên, chưa refit hoặc thay model/app/default/DB. Bước tiếp theo khi người dùng giao là F2 khóa triển khai và kiểm synthetic trước validation; không tự chạy ma trận hoặc push. R07/T14 giữ chưa nghiệm thu. [Bàn giao F1](../../docs/development.md#handoff-chg075-f1).

<a id="forecast-postprocessing-f2"></a>
## CHG-075 F2 — Protocol và hậu xử lý đã kiểm synthetic, 27/10/2026

**Nguồn/phạm vi mới:** người dùng giao tiếp F2; tiếp tục giữ local theo yêu cầu không GitHub của F1. Giữ nhánh audit/HEAD`ce738c4` và mọi thay đổi chưa commit của lượt trước. Thêm4file nghiên cứu, cập nhật6MD; không sửa checker/test F1 hoặc app/model/API/schema/FE/scheduler/default, không refit, tính lại đường tồn/nhập bằng ứng viên hoặc truy cập DB. Không chạy lại native F1, không tính tham số trên bundle thật và không chạy ứng viên thật F3/F4.

### Sản phẩm và giao diện nghiên cứu đã có

| Thành phần | Sản phẩm/khả năng đã triển khai F2 |
|---|---|
| [Protocol máy đọc](../../web/backend/configs/forecast-postprocessing-v1.json) | Khóa13ID/thứ tự/kind, H14/L7, ngày hiệu lực29/07,15origin hiệu chỉnh đủ nhãn đến28/07, trộn0,5/cửa sổ14–28/fallback/quantile, giữ đường frozen và chọn validation trước test; pin audit/F1/app |
| [Hậu xử lý](../../web/backend/research/forecast_postprocessing.py) | Hàm thuần `calibrate`, `transform`; evaluator trong bộ nhớ dùng project/scorer hiện có trên đường frozen; quy tắc `select_validation`; CLI chỉ kiểm protocol |
| [Verifier độc lập](../../web/backend/research/forecast_postprocessing_verification.py) | Tự tính tham số/forecast bằng scalar, fsum/median/quantile nội suy; kiểm projection và event-first score; không import NumPy, postprocessor hay arithmetic app/F1 |
| [Kiểm synthetic](../../web/backend/tests/test_forecast_postprocessing.py) | 40ca F2 mới: đủ13ứng viên, causal/cutoff/fallback/conservation/tamper/selection và nguồn hiệu chỉnh tách khỏi kỳ chấm |

Protocol canonical SHA256: `a4259ef7fbd1cfc7d484efdf757102a40298fca7a84c3f7a7d91ac3d18ff2410`, được kiểm ở cả hậu xử lý và verifier. Giữ nguyên13ID C00/S10/S25/S50/B00/B07/BND/I14/I28/D14/D28/R75/R90, không ghép tổ hợp hoặc mở grid. `kind` phân biệt point/stress/risk, không gọi stress/risk là accuracy điểm đã cải thiện hoặc xác suất cạn đã hiệu chỉnh.

`calibrate(catalog, daily, forecasts)` chỉ nhận3nhóm thông tin dự báo, không nhận ledger/event/cơ hội. Chỉ chọn15origin30/06–14/07 và nhãn01–28/07 trước khi kiểm giá trị; trường ngoài whitelist và dữ liệu sau cutoff không đi vào tham số/checksum. Khóa global/block/level factors, route level, scale và residual quantile cùng protocol/cutoff/effective/calibration-input SHA256 và checksum tham số. Thiếu nhãn trưởng thành, duplicate, horizon sai, bool ID hoặc first_seen sau origin bị chặn; không điền actual thiếu thành0.

`transform(candidate_id, origin, catalog, daily, forecasts, parameters)` trả mapping item→vector14, không sửa input và không nhận ngày cạn/cờ cơ hội. Trước29/07 mọi ID giữ forecast gốc; sau đó B/R dùng tham số đã khóa, I/D chỉ đọc lịch sử ≤origin và giữ tổng tương ứng. Nhóm tỷ lệ mẫu số0 kế thừa hệ số cha cuối cùng, không co thêm lần nữa. Risk chỉ bù quantile không âm, ép đường tích lũy không giảm rồi sai phân, nên không tạo nhu cầu ngày âm. Không bổ sung model/dependency mới.

Evaluator trả `candidate_id/kind/fixed_input_sha256`, forecast riêng, full path14ngày, alarms/cases/metric cảnh báo; chỉ gọi project trên closing và receipts frozen. Tests tạo đường cơ sở synthetic bằng replay trước khi kiểm, rồi chặn mọi lời gọi policy replay khi đánh giá ứng viên. Không có CLI chạy validation/test thật hoặc writer run ứng viên trong F2. Việc nối reader/writer native, xuất metric MAE/WAPE/bias theo tuyến/item/horizon/tích lũy và bảng đánh đổi đầy đủ thuộc F3 khi được giao; không nhận các báo cáo nghiên cứu thật đã có. Protocol đã khóa mask forecast metric: origin từ ngày hiệu lực, target trong score_start…end; cùng mask cho ứng viên/C00, không thay target/split hoặc điền nhãn thiếu.

### Verifier, chống leakage và lựa chọn

Verifier tự tính từ prefix hợp lệ, kiểm checksum tham số rồi so với phép tính độc lập. Với kỳ khác, `verify_candidate` **bắt buộc truyền riêng `calibration_inputs`** khi có tham số: F3/F4 phải dùng nguồn warmup validation đã pin để kiểm tham số, không cố fit từ snapshot test vốn không có tháng7. Có ca synthetic riêng cho kỳ sau thiếu warmup, dùng đúng lock cũ và không hiệu chỉnh lại bằng nhãn kỳ chấm.

Forecast xuất được kiểm với reference độc lập trong dung sai1e-8 trước. Sau đó reference projection dùng đúng các giá trị forecast đã xuất và đã kiểm để tránh đổi điều kiện exact-zero chỉ vì khác thứ tự cộng số thực; tự tính receipts→demand→closing/state/date/lead, không gọi project sản xuất. Cases/metric dùng scorer event-first độc lập của audit cũ. Metadata kind và hash baseline cũng phải khớp; F3 native sau này vẫn phải xác thực source/F1 pins trước khi dùng các hàm thuần này, không coi hash tự khai là provenance đủ.

Selection đã khóa: đủ13summary cùng denominator486 và coverage/bảo toàn/kiểm độc lập đạt mới đặt valid; đạt ≥219/486 và precision hữu hạn không null → precision cao hơn → ít item-ngày cảnh báo → thứ tự protocol. Không có đại diện thì trả null/dừng trước test; denominator578 không được đưa vào hàm chọn validation. Chặn precision NaN/ngoài0–1 hoặc numerator/count không hợp lệ; không đặt ngưỡng FP được chấp nhận. F2 chỉ kiểm quy tắc bằng số synthetic, chưa chọn đại diện thật.

### Kiểm thực chạy và bảo toàn

- **72/72Python targeted đạt,0fail/error/skip**:40F2 mới+15F1+17audit. Đủ13ID khớp tham số/forecast/path/cases/metric với reference; kiểm tổng tuyến/ngày và item/tuần, zero history/zero forecast/mẫu số0/nhóm thiếu và quantile âm/đường risk phẳng; tham số qua JSON giữ ổn định.
- Đổi actual/forecast sau cutoff không đổi tham số; đổi actual sau origin không đổi forecast tại origin, trước hiệu lực giữ gốc. Thêm cờ event/cơ hội vào daily không lọt vào tham số. Nhãn chưa trưởng thành hoặc lịch sử phân bổ thiếu phải fail. Kiểm timestamp receipts, biên6/7/14/stock0 và episode/intervention/censor tiếp tục được kiểm trong32ca F1/audit hiện chạy.
- Sửa tham số rồi reseal, sửa forecast, path giữa kỳ, tử số hoặc đơn frozen đều bị verifier chặn. Kiểm AST không import arithmetic sản xuất/postprocessor vào verifier. Fixture lần đầu thiếu metadata effective_from làm29ca lỗi setup/35đạt; đã bổ sung fixture, giữ XML lỗi; không sửa app hoặc protocol để né lỗi. Lượt32F2 cơ sở,71ca mở rộng và72ca cuối đều giữ XML riêng, chỉ dùng số72cuối làm kết quả hiện tại.
- CLI `--check-protocol`, help và pip check đạt. Không chạy full BE/M2/React/browser hoặc CI vì app không đổi; không dùng số262/CI lịch sử thay kiểm mới. App hash giữ `2a02ba9e9069e83c25e0588da0b19c228ffbb550662b85644d6abcf872992dda`;1.377file protected gồm F1 code/artifact và239file tracked ngoàiMD cũ nguyên. Không truy cập DB nên không nhận kiểm lại14bảng.

Lệnh kiểm protocol đã chạy từ root, không nạp env DB và không chạy ứng viên:

```powershell
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_postprocessing --check-protocol
```

Evidence mới chỉ ở `outputs/research/forecast-postprocessing-f2-checkpoint`: before/backup/diff6MD, targeted-attempt1/attempt2/final/final-calibration XML, [code-lock](../../outputs/research/forecast-postprocessing-f2-checkpoint/code-lock.json), [preservation](../../outputs/research/forecast-postprocessing-f2-checkpoint/preservation.json), protocol-check và pip-check. Lock cuối gắn hash4file mới với72test, source pins F1/audit và cờ real_parameters_fitted/real_candidate_runs=false; lập trước F3, không sửa artifact F1/audit cũ. Không đưa private output lên Git.

**Điểm dừng:** F2 hoàn tất local, không commit/push/GitHub/CI; chưa có tham số hiệu chỉnh thật, kết quả ứng viên, lựa chọn thật hoặc early rate mới đạt45%. F3–F4 chưa bắt đầu; chỉ khi được giao F3 mới nối bộ thực thi native, dùng calibration source đã pin, chạy đủ13validation và xuất metric/đánh đổi/verifier trước khóa một đại diện. Test vẫn hồi cứu, R07/T14 chưa nghiệm thu. [Bàn giao F2](../../docs/development.md#handoff-chg075-f2).

<a id="forecast-postprocessing-f3"></a>
## CHG-075 F3 — Validation native trên đường frozen, 27/10/2026

**Nguồn/phạm vi mới:** người dùng giao tiếp F3. Giữ nhánh audit/HEAD`ce738c4`, local không commit/push/CI. Không mở test F4, fit/chọn lại model, thay raw/target/split/SS/ROP/MOQ/lead time/đường tồn/đơn/receipts, app/API/schema/FE/scheduler/default. F1/F2 code/tests/protocol và mọi output cũ được bảo toàn; chỉ thêm adapter native/verifier/report/tests cùng cập nhật6MD. Trước sửa backup6MD/diff và1.406file protected,239tracked ngoàiMD trong checkpoint mới.

Thêm [runner validation](../../web/backend/research/forecast_postprocessing_validation.py), [verifier báo cáo/stream độc lập](../../web/backend/research/forecast_postprocessing_validation_verification.py), [16ca adapter/metric](../../web/backend/tests/test_forecast_postprocessing_validation.py). Giữ nguyên protocol F2 SHA256 `a4259ef7fbd1cfc7d484efdf757102a40298fca7a84c3f7a7d91ac3d18ff2410`, không thay công thức/tham số grid. Source gate kiểm app hash, manifest/receipt audit, F1 manifest/summary/artifacts và F2 code-lock SHA`deb5dcec7417a2134a6d58695d96bc50fe41156d34683666fa122030d668c934`; chỉ nạp parent validation để tính, không nạp dữ liệu test để hiệu chỉnh/chấm/chọn.

Runner dùng đúng `calibrate/transform` F2:15origin30/06–14/07 đủ nhãn đến28/07, tham số cố định và kiểm scalar độc lập trước khi ghi parameters.json; trước29/07 mọi ID giữ forecast gốc. Mã/định nghĩa báo cáo khóa trước native. Đọc source/ledger frozen, kiểm identity coverage và baseline151/486 trước chạy đủ13ID; không gọi policy replay với ứng viên. Xử lý từng origin để giới hạn bộ nhớ; lưu forecast/path ứng viên riêng, giữ cùng event ID và hash toàn bộ baseline. Không loại nhóm hoặc mở grid theo test đã xem.

### Cách chấm và báo cáo đã khóa trước kết quả

- Alarm/event giữ scorer cũ H14/L7, event đầu tiên/alarm hợp lệ sớm nhất/event-once, warmup/intervention/right-censor nguyên. Precision theo alarm item-ngày, recall/early theo486event; threshold ROP không gộp vào numerator. Alarm-item-days dùng phá hòa chỉ tính kỳ score; cả all-period count và histogram từng ngày vẫn báo riêng.
- Forecast mask theo protocol: origin từ29/07, target trong score_start…end; cùng mask C00/ứng viên. Nhãn thiếu không điền0, denominator0 trảnull cho WAPE/bias ratio nhưng MAE còn báo. Tổng theo tuyến được cộng forecast/actual item trước lấy trị tuyệt đối, không gọi tổng sai số item là MAE tuyến.
- Báo4scope: từng item, từng route, items_pooled và routes_pooled; daily H1–7/H8–14/H1–14 và cumulative H1…H14. Cumulative chỉ chấm khi mọi target trong prefix thuộc mask và nhãn đầy đủ; báo expected/observed/coverage, MAE/WAPE/bias/bias_ratio. Risk thêm empirical cumulative coverage và pinball ở q đã khóa; không diễn giải thành xác suất cạn đã hiệu chỉnh hoặc forecast điểm tốt hơn.
- Báo late/no-alarm, event mới được early và event mất early, FP/intervention/right-censor, số alarm/item/tần suất ngày, signed date bias và MAE; kiểm date error cả trên tập event ghép chung với C00 để tránh so khác mẫu. Fill/tồn/thiếu/nhập không thay vì đường vận hành được giữ cố định.
- CSV/HTML tổng hợp13ID liên kết với JSON chi tiết theo ứng viên; verifier kiểm cả forecast/path và nội dung bảng CSV/HTML. Kết quả tính giữ `calculated_unverified`; selection chỉ được chấp nhận sau receipt độc lập. Nếu không có đại diện đủ điều kiện đạt219/486 thì ghi chưa đạt và dừng trước test; không mở rộng cấu hình hoặc đổi tiêu chí/FP limit.

### Kiểm trước native và bằng chứng thực thi

88targeted/0fail/error/skip đạt trước native, gồm16F3 mới và72F1/F2/audit; help/pip check/diff check đạt. Ca mới kiểm aggregation tuyến trước trị tuyệt đối, cumulative risk pinball/coverage, zero/missing/tail/warmup mask, adapter stream khớp F2 trên C00/I28/R90, và tamper forecast/interior path/duplicate/metric/summary/case. CLI chỉ có validation/verify, không có mode test; verifier không import postprocessor/runner/app arithmetic. Không dùng số test/CI lịch sử thay kiểm mới.

Checkpoint mới `outputs/research/forecast-postprocessing-f3-checkpoint`: before/backup/diff, preflight.xml, code-lock và evaluation-lock trước native, command/stdout/stderr. Run mới `outputs/research/forecast-postprocessing-f3/forecast-validation-v1-da6db434-8afa-40ac-a8ad-f5830924a44a`; mỗi ID có paths JSONL gzip/alarms/cases/forecast metrics/summary. Parameters khóa trước grid; artifact cũ không được ghi đè. Không đưa private output lên Git.

**Trạng thái kết quả:** đã hoàn tất13/13và receipt độc lập, khóa S25; bảng và hash dưới đây là kết quả thực chạy. [Bàn giao F3](../../docs/development.md#handoff-chg075-f3). Người dùng giao tiếp F4 sau F3, chưa chạy tại checkpoint này; R07/T14 chưa nghiệm thu.

### Kết quả F3 đã kiểm độc lập và lựa chọn khóa

| ID | Loại | Early /486 | Early % | Precision % | FP | Alarm item-days | Mới early | Mất early |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| C00 | point | 151/486 | 31.0700 | 76.2585 | 382 | 3606 | 0 | 0 |
| S10 | stress | 195/486 | 40.1235 | 69.6850 | 693 | 4921 | 44 | 0 |
| S25 | stress | 228/486 | 46.9136 | 60.6383 | 1369 | 6947 | 77 | 0 |
| S50 | stress | 267/486 | 54.9383 | 50.4824 | 2720 | 10196 | 116 | 0 |
| B00 | point | 209/486 | 43.0041 | 65.9733 | 916 | 5631 | 58 | 0 |
| B07 | point | 209/486 | 43.0041 | 65.9970 | 914 | 5626 | 58 | 0 |
| BND | point | 209/486 | 43.0041 | 66.0223 | 914 | 5617 | 58 | 0 |
| I14 | point | 172/486 | 35.3909 | 69.7808 | 579 | 4088 | 41 | 20 |
| I28 | point | 152/486 | 31.2757 | 76.6871 | 380 | 3648 | 6 | 5 |
| D14 | point | 151/486 | 31.0700 | 76.0991 | 386 | 3612 | 0 | 0 |
| D28 | point | 151/486 | 31.0700 | 76.4596 | 379 | 3606 | 0 | 0 |
| R75 | risk | 281/486 | 57.8189 | 51.0356 | 2695 | 10345 | 130 | 0 |
| R90 | risk | 390/486 | 80.2469 | 31.3410 | 10511 | 24679 | 239 | 0 |

Có4ứng viên đạt219/486: S25/S50/R75/R90, coverage forecast đều100%. **Khóa S25 (stress forecast×1,25)** vì precision60,6383% cao nhất trong nhóm đạt mục tiêu; không chọn R90 dù early cao nhất80,2469%, do precision31,3410% vàFP10.511. Không đổi quy tắc chọn sau kết quả, không đặt mức FP chấp nhận được hoặc dùng test để mở/chọn lại grid.

S25 tăng77event early (68từ nhóm late,9từ nhóm no-alarm cũ), không mất event early; early151→228, +15,8436điểm%. FP382→1.369 (+987), alarm-item-days3.606→6.947 (+3.341), trung bình56,34375→108,546875alarm/ngày score; precision76,2585%→60,6383%. Can thiệp1.665→2.743, right-censor332→726 báo riêng, không ép thànhFP/TP. Recall79,0123%→83,9506%, S25 late180/no-alarm78. Chưa có ngân sách cảnh báo sai hoặc tần suất được nghiệm thu.

Không gọi stress là cải thiện forecast điểm: item dailyH1–14 WAPE143,8460%→156,5747%, MAE0,273339→0,297527; route daily WAPE50,3241%→54,8950%. Trên384event ghép chung, MAE ngày cạn4,854167→3,901042 và signed bias3,994792→2,244792ngày; MAE toàn bộ408cặp S25 là4,056373ngày, không so như cùng mẫu384cặp C00.

Nhóm bias B00/B07/BND chỉ209/486=43,0041%, chưa đạt45%, và WAPE điểm tăng trên validation. Global factor warmup1,152243; hai khối1,145692/1,158829 phản ánh tập hiệu chỉnh15origin chồng lấn, không chứng minh mọi tuyến/model dự báo thấp. I14 net+21early (41mới/20mất) dù giữ nguyên tổng tuyến/ngày; I28 chỉnet+1, D14/D28 không tăng early. Đây là chẩn đoán trên toàn mẫu đã khóa, không dùng riêng nhóm missed để kết luận toàn model hoặc loại nhóm khỏi kết quả.

Risk R75/R90 đạt281/390early nhưng FP2.695/10.511 và alarm10.345/24.679; empirical coverage cumulativeH14 là79,5283%/92,7848%, pinball ở q riêng0,770146/0,503745. Không so pinball khác q như cùng loss hoặc suy xác suất cạn75/90%. Toàn13ID có727.720cặp item-horizon daily được chấm cùng mask,16.456metric rows/ID trên4scope và17horizon; không dùng daily H8–14 như MAE tổng tuần. Có1.112.280forecast/path và15.571.920bước projection được kiểm, cohort486 và đường tồn/đơn/receipts/event giữ nguyên.

- [Bảng13ID đã kiểm](../../outputs/research/forecast-postprocessing-f3-checkpoint/verified-summary.html), [summary gốc](../../outputs/research/forecast-postprocessing-f3/forecast-validation-v1-da6db434-8afa-40ac-a8ad-f5830924a44a/summary.json), [selection khóa](../../outputs/research/forecast-postprocessing-f3/forecast-validation-v1-da6db434-8afa-40ac-a8ad-f5830924a44a/selection.json), [receipt verifier](../../outputs/research/forecast-postprocessing-f3/forecast-validation-v1-da6db434-8afa-40ac-a8ad-f5830924a44a/verification.json).
- Manifest SHA256 `f53a99ad5e38929af10e5203a2110f38ad353ca0d68e19247bbce0d25c9fcf51`; receipt `a5bf676a77f03d0b566bb657791917df373173268a49ac53578f8b84b69799fd`; parameters-file `58052b211c908e1b9c3f19c4e04f455d968d35ed285979c3afc1f07380bdd737`; selection-file `33087505d977c046efa5f9f5e86e283caa0aefbf9e685bf5c1c4d636a1d9e4db`. Parameter payload SHA256 `71eedfe8b752c05b60f8d217a34ea3ed9ba85e54a560b7b5faa99a977b36cf03` giữ cho F4, không cập nhật theo test.
- Verifier độc lập13/13đạt một lượt, kiểm71artifact, selection vàCSV/HTML; manifest/HTML sealed giữ nhãn pending lúc tạo, receipt xác nhận sau. verified-summary là bản trình bày dẫn từ JSON đã kiểm, không sửa sealed output.1.406protected/239tracked ngoàiMD/F1/F2/app hash và3file mã F3 đúng lock trước native; không truy cập DB nên không nhận kiểm lại14bảng. Python3.12.14/NumPy2.5.3, requirements hashes vàenvironment/checkpoint giữ riêng, không đổi dependency.

**Kết luận F3:** đạt mục tiêu làm việc45% trên validation bằng đường stress S25 với đánh đổi nêu trên, chưa là kết quả test hoặc accuracy model cải thiện, không nâng R07/T14. Người dùng đã giao tiếp F4 sau khi F3 hoàn tất; tại checkpoint này chưa chạy F4. F4 chỉ C00+S25, không chọn lại/hệ số mới hoặc refit; mọi đánh giá vẫn hồi cứu vì cả validation/test đã được sử dụng và model gốc có lịch sử test-selected. App/default/model/DB và GitHub giữ nguyên.

<a id="forecast-postprocessing-f4"></a>
## CHG-075 F4 — Test hồi cứu C00 và S25 khóa từ validation, 27/10/2026

**Nguồn/quyền mới:** người dùng giao làm F4 ngay sau khi F3 hoàn tất. F3 đã hoàn tất13/13verifier và bàn giao/bảo toàn trước F4; selection S25 không đổi. Giữ local/nhánh audit/HEADce738c4, không commit/push/CI, model/app/default/DB hoặc policy/đường tồn/đơn/receipts/scoring. F4 chỉ được chạy C00 và S25; không cập nhật tham số/hệ số, mở grid hoặc chọn lại theo test.

Thêm runner/test verifier riêng và9test; giữ nguyên toàn bộ F1/F2/F3 code/protocol/output. Source gate pin F3 manifest/receipt/selection/parameter bytes; đọc tham số từ F3, kiểm kỳ hiệu chỉnh từ validation tách khỏi snapshot test. Không gọi calibrate hoặc select_validation trong F4. Native test chỉ C00+S25×1,25; cùng578event, horizon14/lead7/event-once và intervention/censor cũ. Report/metric mask giống F3, không thay tiêu chí để gọi đạt.

97targeted=9F4 mới+88cũ đạt trước native,0fail/error/skip; help/pip check/diff check đạt. Ca mới kiểm260chưađạt/261đạt trên578, chặn thêm/đổi ứng viên/denominator/coverage, F3 giả hoặc candidate/alpha override; AST chặn fit/select và arithmetic producer import trong verifier. Tham số giữ nguyên byte từ F3; kiểm scalar từ nguồn warmup validation là đối soát lock, không hiệu chỉnh lại bằng test.

Run mới `outputs/research/forecast-postprocessing-f4/forecast-test-v1-e5a6d3b2-5e9f-4a00-aff5-e4ba05652c5a`, checkpoint `outputs/research/forecast-postprocessing-f4-checkpoint` có before/backup6MD/diff, code-lock/preflight/command/log. Trước F4 pin1.553protected/239tracked ngoàiMD gồm F3 code/output; không sửa sealed artifact. **Đã hoàn tất native vàverifier độc lập2/2**, không chọn lại hoặc cập nhật tham số theo test. F3 đã khóa S25 dựa validation, mọi kết quả test vẫn hồi cứu; không nâng R07/T14. [Bàn giao F4](../../docs/development.md#handoff-chg075-f4).

### Kết quả F4 đã kiểm độc lập

| Kỳ / ID | Early | Tỷ lệ % | Precision % | Recall % | FP | Alarm item-days |
|---|---:|---:|---:|---:|---:|---:|
| Validation C00 | 151/486 | 31,0700 | 76,2585 | 79,0123 | 382 | 3.606 |
| Validation S25 | 228/486 | 46,9136 | 60,6383 | 83,9506 | 1.369 | 6.947 |
| Test hồi cứu C00 | 193/578 | 33,3910 | 80,6202 | 81,1419 | 425 | 4.808 |
| Test hồi cứu S25 | 285/578 | 49,3080 | 66,7646 | 86,6782 | 1.358 | 8.411 |

**S25 đạt mục tiêu làm việc45% trên test**:285≥261, hơn đối chứng92event early (+15,9170điểm%), không mất early;87từ late và5từ no-alarm cũ chuyển early. Late276→216/no-alarm109→77, event có alarm469→501. Không đổi denominator578, không dùng kết quả test chọn S25 hoặc thử ứng viên khác; `reselection=false`, hệ số1,25 vàparameters giữ nguyên từ F3.

Đánh đổi trên test:precision80,6202%→66,7646%,FP425→1.358 (+933),alarm-item-days4.808→8.411 (+3.603),75,125→131,421875alarm/ngày score. Intervened1.990→3.038 vàright-censor625→1.287 giữ riêng, không ép vào TP/FP. Chưa có ngưỡngFP/tần suất được chấp nhận; không tự chuyển nghiên cứu thành vận hành được nghiệm thu.

Không gọi đây là accuracy forecast điểm tốt hơn: item dailyH1–14 WAPE137,7015%→148,8596%,MAE0,280735→0,303483;route daily WAPE49,7955%→51,3230%,MAE2,030383→2,092666. Bias bình quân item đổi−0,030243→+0,013164 nhưng MAE/WAPE tăng. Trên469event ghép chung, MAE ngày cạn4,980810→3,972281 vàsigned bias4,179104→2,172708ngày; MAE tất cả501cặp S25=4,315369ngày, không coi là cùng mẫu469cặp C00. Mọi sai số điểm là metric chẩn đoán của đường stress, không thay tiêu chí M05/R05 hoặc forecast gốc.

F4kiểm171.120path/2.395.680bước H14,16.456metric rows/ID trên4scope; coverage100% của824.320cặp item-horizon thuộc mask test, không phải khẳng định mọi target tương lai có nhãn. Mask/cutoff giữ nguyên F2/F3: tham số đã có trước mọi origin test nên S25áp cả warmup test; validation trước29/07giữforecast gốc. Không áp ngược tham số vào validation hoặc diễn giải chênh hai kỳ như holdout độc lập.

- [Bảng F3/F4 đã kiểm](../../outputs/research/forecast-postprocessing-f4-checkpoint/verified-summary.html), [summary test](../../outputs/research/forecast-postprocessing-f4/forecast-test-v1-e5a6d3b2-5e9f-4a00-aff5-e4ba05652c5a/summary.json), [evaluation](../../outputs/research/forecast-postprocessing-f4/forecast-test-v1-e5a6d3b2-5e9f-4a00-aff5-e4ba05652c5a/evaluation.json), [receipt verifier](../../outputs/research/forecast-postprocessing-f4/forecast-test-v1-e5a6d3b2-5e9f-4a00-aff5-e4ba05652c5a/verification.json).
- Test manifest SHA256 `c5df347726d4e446082c72bd7f1bf2f7ed7f505bdb4eb40b41bebaa16ed846da`; receipt `314794eb2fe75465cf78d5d58052ef0b108d0c4588222de3fd267c98bbc1a718`;evaluation `4ea288bac21dfc16bb22103176abc692bd9c9aab818f1c3b53fa5a17905ddcd8`.Parameters-file giữ byte SHA`58052b211c908e1b9c3f19c4e04f455d968d35ed285979c3afc1f07380bdd737`,payload SHA`71eedfe8b752c05b60f8d217a34ea3ed9ba85e54a560b7b5faa99a977b36cf03` như F3.
- Native vàverifier đạt lần đầu,16artifact sealed được kiểm; source F3 manifest/receipt/selection được pin trước test. Mã/tiêu chí/hệ số không đổi sau kết quả.1.553protected/239tracked ngoàiMD/F1/F2/F3/app nguyên và3file F4 khớp code-lock trước native. Không DB/refit hoặc raw-source re-audit, không sửa sealed output;97targeted là kiểm trước chạy thật, không dùng số CI/test cũ. HTML/manifest gốc giữ pending tại lúc tạo, receipt vàverified-summary ghi kiểm sau.

**Kết luận và điểm dừng:** F3/F4 được giao đã hoàn tất local. Đường cảnh báo stress S25đạt early≥45% trên cả validation vàtest hồi cứu theo protocol đã khóa, kèm precision giảm/FP vàtần suất tăng/accuracy điểm không cải thiện. Không bảo đảm tương lai hoặc tuyên bố holdout độc lập; test đã xem vàmodel gốc có lịch sử test-selected. Chưa đưa S25vào app/default, chưa thay model/DB, không commit/push/merge/deploy/CI vàkhông tự nâng R07/T14. Việc tích hợp/đánh giá mứcFP chấp nhận được cần yêu cầu riêng, không tự chọn lại theo test. [Bàn giao F4](../../docs/development.md#handoff-chg075-f4).
