# Nghiên cứu bổ sung, tách khỏi mô hình M3 đang phục vụ

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
