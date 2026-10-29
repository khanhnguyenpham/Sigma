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

**Trạng thái: kế hoạch, chưa có code/run/kết quả mới.** Người dùng chọn ưu tiên báo trước ít nhất7ngày cho≥45% sự kiện và chưa thay cấu hình mặc định. Đây là hướng tiếp theo sau CHG-074; [báo cáo đã kiểm ở nhánh nghiên cứu67d2ab6](https://github.com/khanhnguyenpham/Sigma/blob/67d2ab6a19f86101acdc58af7fec788c3a48b093/M3/docs/research.md#inventory-alert-safety-step5). Không đưa code nghiên cứu hoặc output cũ vào nhánh ứng dụng trong lượt lập kế hoạch này.

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


<a id="fixed-lot-baseline-chg077"></a>
## CHG-077 — Chạy lại hướng cũ với lượng mỗi lần cố định

Phạm vi29/10/2026 thay giới hạn chưa chạy ở CHG-075 cho riêng lần thử mới được người dùng giao: chạy cảnh báo point-forecast gốc trước, giữ S25/49% để sau. Không refit hoặc sửa forecast phục vụ, không ghi appDB/policy; không áp số33/49% cũ cho lô mới. Runner `web/backend/research/fixed_lot_baseline.py` tái sử dụng pure_window/scoring nghiên cứu trước; verifier `fixed_lot_verification.py` tự dựng giao dịch,SS/ROP/IP/Q/ETA/pending và projection, chấm event-first không dùng helper sản xuất.

Protocol `web/backend/configs/fixed-lot-baseline-v1.json` khóa nguồn CHG-074 đã verified và5scenario: base(cover7,SS×1),cover3,cover14,SS×0,5,SS×1,5. Chạy hết validation rồi test, không chọn model/scenario bằng test. Giữ period/warmup/scoring cũ: validation01/07–30/09,chấm29/07; test01/10–31/12,chấm29/10. Khởi tạo lại từng split như phép thử cũ, không nhận chuyển tồn validation→test liên tục.

Người dùng giao tự chọn nhóm cao/thấp và lô5/10 hoặc10/15. Tổng quantity03–30/06/2025 tính theo item, trung vị riêng product_type gồm0; cao khi>trung vị,thấp khi≤. Khóa trước kết quả và giữ mỗi item qua validation/test. eSIM ngưỡng6:234thấp Q5,226cao Q10; physical_SIM ngưỡng2:252thấp Q10,208cao Q15. Đây là giả định mô phỏng, không hợp đồng thực. Không tự chuyển MOQ cũ thành fixed quantity hoặc sửa920policy hiện có.

```powershell
# Từ root, dùng môi trường .venv-m3 đã cài editable backend.
& ./.venv-m3/Scripts/python.exe -B -m web.backend.research.fixed_lot_baseline run
& ./.venv-m3/Scripts/python.exe -B -m web.backend.research.fixed_lot_baseline verify --run-dir RUN_DIR
```

Thay RUN_DIR bằng thư mục mới mà runner trả về. Không cần DB cho replay này: đọc input frozen đã đối soát trước; receipt ghi rõ không phải audit raw/DB mới. Mỗi lần run tạo thư mục mới và lock protocol/code/quantities trước kết quả. Legacy reference phải khớp151/486 và193/578 trước5scenario fixed; ledger/episode mới không bắt khớp mẫu số cũ. Báo early≥7theo episode,precision theo item/ngày,các ca can thiệp/right-censor,fill/thiếu/tồn/đơn cả toàn kỳ và kỳ chấm; trần cơ hội chỉ hậu kiểm,không đưa actual tương lai vào cảnh báo. Các scenario thay đường tồn/mẫu số nên không phải so alarm trên cùng sự kiện.

Trạng thái: hoàn tất và verifier độc lập đã đạt855.600dòng/10scenario;270Python đạt. Test sau warmup: base129/400=32,25%,cover3 135/411=32,8467%,cover14 124/417=29,7362%,SS×0,5 184/456=40,3509%,SS×1,5 76/336=22,6190%. Cả5chưa45% ở validation/test. Base fixed đáp ứng94,2602%/thiếu689so91,9277%/969cũ trong kỳ chấm; tồn bình quân6,9416so5,6142tăng. Toàn kỳ basefixed92,5476%/thiếu1190so90,4121%/1531cũ. SS×0,5 có thiếu858/FP576so689/406của base,không tự chọn làm mặc định. Dữ liệu/Word/appDB giữ nguyên; S25 chưa chạy,R07/T14 chưa nghiệm thu. [Phạm vi](../../docs/planning/PLAN.md#chg077-fixed-baseline).


Run local `outputs/research/fixed-lot-baseline/fixed-lot-baseline-v1-b98b58f9-553e-4bc3-b8d5-be7f526ea062`; manifest SHA256 `7fd760ed4713f09e106cb5d1d5384c6ecccc31e15be235648bc50b3535f93f34`, receipt `verification.json` có independent_replay/independent_decisions/independent_scoring=true. Báo cáo riêng HTML/MD/CSV ở reports/fixed_lot_baseline_20261029; không cập nhật Word theo yêu cầu mới.

Runner dùng chỉ mục tra cứu history/policy trong process CLI riêng và phục hồi accessor bằng context manager; phép tính giữ pure_window.5fixture khớp native/indexed/independent; cả85.560dòng native cơ sở validation giữ riêng khớp byte với indexed và verifier. Lượt đầu bị dừng sau2kết quả validation chưa sealed vì runtime,giữ lock/output/trạng thái interrupted;không đổi tham số hoặc công thức theo kết quả. Lượt cuối tạo UUID mới và chạy lại đủ protocol; không sửa hoặc xóa lượt dở.

Nếu sau này được giao thử S25,hãy khóa đường basefixed mới,cùng400episode test;45% cần180ca,tức thêm51so129. Không giữ578mẫu số cũ hoặc hứa49%; chọn validation trước,đánh giá FP/tần suất và không nhận holdout độc lập.
