# Phát triển, kiểm tra và bàn giao SIGMA

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo pages, layouts và component dùng chung (CHG-069), sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Cổng từng bước: kiểm phạm vi diff và dữ liệu riêng tư; chạy kiểm phù hợp; commit riêng; push nhánh; so HEAD với remote và chờ CI liên quan đạt. Lỗi thì sửa trong bước, không đi tiếp. Tests nguồn thật/replay local; CI synthetic. Không sửa snapshot/config hash cũ để khớp code mới; thay đổi cấu hình tạo run mới.

[Kế hoạch CHG-068 và cổng từng bước](planning/PLAN.md#chg-068).

**CHG-045/E73 — 14/10/2026:** nhánh `cleanup/m2-final` chỉ giữ code M2 final. Xem [bản đồ code hiện hành](../M2/README.md) và [khôi phục code cũ](review-log.md#removed-docs-chg070). Các lệnh/đường code M1, M3, V13 và thử nghiệm bên dưới là lịch sử, cần nhánh backup để chạy; dữ liệu, kết quả, bằng chứng và tiêu chí nghiệm thu không đổi.

**CHG-042/E70 — 11/10/2026:** M2 final fit mới/verify đạt tổng7 test10/10<20%, mean15,745366%; chín tuyến parity0. Full suite291 đạt+1 skip trước xuất báo cáo, sau đó4 final tests (gồm AppTest đã skip) đều đạt; pip check/notebook2 code cells/12 public hashes/privacy đạt. [Bộ final](../M2/reports/final_m2_20261011/README.md), [cấu hình10 tuyến](../M2/reports/final_m2_20261011/model_configurations.md). Raw/771 tệp protected nguyên; hai run sandbox lỗi giữ failed. Đã push nhánh M2-final-report, CI Windows của commit mã0cbeaf0 đạt. Test hồi cứu/LG U+ test-selected, h8–14/R05 ngày/R07/T14 còn mở.

**CHG-034/E62 — 06/10/2026:** nhánh M2 local `codex/m2-report-20261007`, launcher hiện ở scripts, cấu hình ở data/configs, planning ở docs/planning. Full suite262 tests đạt; M2 AppTest3 tab và kiểm độc lập401.600 dòng/9.160 metric đạt. Kết quả9/10 giữ nguyên, LG U+ hoãn tối ưu; [guide báo cáo](../M2/reports/presentation-guide.md). Các cập nhật bên dưới là lịch sử.

**Hiện hành CHG-028/E53–E55 — 06/10/2026:** sản phẩm mặc định dùng V13 với 58 ứng viên chọn bằng validation, cùng policy V4, stock V7, customer V6 và comparison V3. Bộ báo cáo đã khóa tại sigma_m2m3_checkpoint_v3; mở start_m2m3.ps1 ở cổng 8504. **214 tests và CI Windows của commit 183ed10 đạt**; đã đối soát 447.810 cặp dự báo, 42.136 hệ số hiệu chỉnh, 1.100.320 dòng sổ, 267.908 giao dịch/nhập và 920 mặt hàng. AppTest sáu trang, bốn kịch bản và bộ lọc SKU/loại đạt. Job Windows 07:00 đã cài, chạy thử mã 0. Tuần đạt 9/10, MAPE trung bình 16,17%, LG U+ 21,19%; R05 ngày vẫn 0/10, tỷ lệ báo sớm 33,73% trên 2.867 sự kiện. **Chưa nghiệm thu toàn bài.** Dữ liệu gốc và 59 artifact v11 nguyên; src/ và run.py không đổi, app.py chỉ thêm khóa bộ run. Word/slide chưa làm lại; các cập nhật cũ bên dưới là lịch sử.

**Lịch sử CHG-027/E43–E49 — 05/10/2026:** sản phẩm mặc định dùng sigma_weekly_refactored_v12; đã hoàn tất bản so sánh ngày/tổng7 ngày và tổ chức mã sigma/ +29 entry points legacy/ +configs/experiments. 192 tests đạt; parity364.320 validation cache/7.590 fresh test/92 future/644 daily rows ở1e-8, cùng46 lựa chọn; raw/59 v11 files nguyên. Full policyV3 kiểm13 kịch bản/1.100.320 ledger/267.812 events; snapshotV6 kiểm920 items từ đúng policy; customerV5 kiểmD+7; AppTest6 trang và4 bộ lọc scenario đạt. Tuần9/10, mean16,19%, LG U+21,19%; R05 ngày0/10, early≥7 ngày33,80% cùng2867 events; chưa nghiệm thu toàn bài. CHG-027 thay thứ tự hoãn CHG-025; Word/slide không làm lại. Các cập nhật bên dưới E37–E41 là lịch sử.

**Cập nhật 05/10/2026 — CHG-024/025, E37–E39:** đã áp dụng **khách đặt D → giao D+7 ngày lịch UTC**, không trễ giao, gồm cuối tuần; không đổi lead time nhập kho. Người dùng mô tả snapshot order là giả định; đây là nguồn thuật lại, vẫn giữ dữ liệu/outputs private và raw nguyên. [Sản phẩm chung và lịch giao](customer-delivery.md) mở bằng `start_product.ps1` tại cổng 8503. Run tuần hiện hành `sigma_weekly_calibrated_v5`: test hồi cứu **9/10**, mean **15,97%**, LG U+ **21,36%**; chọn validation rồi khóa trước test. 920 khuyến nghị tồn từ phân bổ tuần đã đối soát, replay cùng 5.520 cửa sổ báo sớm **33,73%**; chưa chạy lại toàn bộ chính sách liên tục bằng tuần. 150 tests đạt, AppTest năm trang/không exception; job refresh/skip chạy thật, script đăng ký lịch nền được chuẩn bị nhưng chưa cài. R05 ngày **0/10**, R07/T14 vẫn mở. **Sau khi đủ điều kiện nghiệm thu mới làm bản so sánh chính thức ngày/tổng 7 ngày và tổ chức lại code**, đúng thứ tự người dùng yêu cầu; chưa làm lại Word/slide. Những cập nhật E36/v1 bên dưới là lịch sử.

**Kiểm CHG-023/E36 — tổng tuần:** [lệnh và protocol](weekly-forecast.md), `weekly_forecast.py`, `verify_weekly.py`, `weekly_app.py`; cấu hình riêng, không thêm phụ thuộc. 125 tests toàn suite đạt; đối soát 75.900 cặp từ raw độc lập, selection/metric/full coverage và nhãn fit≤cutoff, tổng phân bổ tuần; raw và 59 tệp sealed v11 nguyên. AppTest run thật0 exception/4 tab/6 bảng, kiểm Thailand/AIS/khối 8–14/lịch 7 ngày. Weekly test9/10≤20%, mean 17,19%; không nâng R05 ngày hoặc R07. Source/split/top10/seed giữ nguyên; test đã xem không độc lập. Kết quả giữ local, Git chỉ mã/cấu hình/tests/tài liệu. Nguồn kickoff đã xem tại E35, PDF/M01/M02 vẫn thiếu. T09/T10 tiếp tục accuracy và chính sách tồn từ forecast tuần; không chỉnh Word/slide.

**Cập nhật 05/10/2026:** Mã và quy trình chạy đã triển khai; lệnh thật tại README. Python 3.14.7, phiên bản khóa trong requirements.txt; config chứa seed 42 và dung sai số thực 1e-8. Kiểm tra release và báo cáo M2 ghi ở E13–E15/TASK. Phần ghi “chưa có/dự kiến” ngày 02/10 dưới đây là bối cảnh lịch sử và checklist thiết kế, không phải hiện trạng triển khai. Git root hiện nằm trong project; không sửa cấu hình Git toàn cục.

**Bản hướng dẫn:** 1.0 — 02/10/2026 (Asia/Saigon), dựa trên [PLAN 2.0](planning/PLAN.md), [requirements](requirements.md), [review-log](review-log.md). **Hiện trạng:** tài liệu và CSV; chưa có mã, config, phụ thuộc được khóa, tests hoặc run. Quy trình kỹ thuật dưới đây là **dự kiến, chưa triển khai**. Lượt tạo tài liệu không cài đặt, huấn luyện, mô phỏng hay nghiệm thu kỹ thuật.

## 1. Bắt đầu và trình tự task

Đọc [AGENTS](../AGENTS.md), [TASK](planning/TASK.md) và phần [PROJECTMAP](planning/PROJECTMAP.md) liên quan; kiểm tra tệp thực tế và phạm vi yêu cầu mới trước khi hành động. Với task đang làm, đọc mục Txx trong PLAN, Rxx liên quan và quyết định/giả định có ảnh hưởng. Không cần đọc lại mọi nguồn cho sửa lỗi chính tả hoặc nhãn đơn giản.

| Giai đoạn | Trình tự theo PLAN | Điều kiện / mục đích |
|---|---|---|
| Nền tảng | T01 → T02 → T03 → T04 → T05 | Rà soát yêu cầu trước môi trường local; audit sales trước chuỗi ngày/EDA; sau đó top 10 train và ba baseline |
| MVP và mô hình | Sau T05: T06 và T07; T07 → T08 nếu có điều kiện | T06 có run xuyên suốt để kiểm tra giao diện; T07 thử SARIMA; T08 chỉ khi còn top 10 chưa đạt validation ≤20% sau SARIMA, hoặc lưu biên bản không kích hoạt |
| Khóa M2 | T09 sau T06, T07, T08 hoặc biên bản không kích hoạt | Khóa lựa chọn bằng validation rồi chấm test; không chọn lại bằng test |
| Tồn và dashboard | T10 phát triển sau T06, kết quả cuối nhận T09; T11 sau T06/T09/T10 | Hoàn thiện ngưỡng đối tác/ledger/replay và dashboard khớp run |
| Kiểm tra và bàn giao | T12 sau T09/T10/T11; T13 sau T09–T12; T14 sau T12/T13 | Tái lập, bảo mật, báo cáo truy run và nghiệm thu có bằng chứng |

T12 là giai đoạn tổng hợp/tái lập; kiểm tra dữ liệu và phép tính được thực hiện ngay khi phát triển từng task. Không trì hoãn mọi test tới T12. E06 activation chỉ là lịch sử; T05 phải tạo baseline sales mới. Không yêu cầu thêm tồn/lead time thật để bắt đầu đường mô phỏng đã có giả định.

T02 chỉ thực hiện khi được giao kỹ thuật và T01 đủ bằng chứng. Tạo môi trường riêng, kiểm tra tương thích rồi khóa phiên bản thực tế; không chốt thư viện vì runtime khảo sát đang có. CLI/notebook local dùng cùng mã `src/` theo cây dự kiến trong PLAN; demo Streamlit đọc gói run, không cần train lại. Chưa có lệnh cài/chạy/test được kiểm chứng để sao chép ở đây; [README](../README.md) chỉ có ví dụ CLI dự kiến từ PLAN.

<a id="runs"></a>
## 2. Cấu hình, phiên bản và run dự kiến

| Thành phần | Quy tắc triển khai và bằng chứng |
|---|---|
| Nguồn | Chỉ đọc CSV gốc; ghi path, kích thước, SHA-256 byte thực trước/sau xử lý. Hash nền hiện tại tại [data-contract](data-contract.md#source-check); không sửa newline để khớp E02. Nguồn ảnh/PDF thiếu ghi thiếu, không nhận đã kiểm tra hash cũ |
| `config.json` dự kiến | Tập trung target/status, UTC, split, horizon/origin/refit, ứng viên mô hình, seed, mapping và tham số đầy đủ từng đối tác, cách sinh tồn đầu và phiên bản. Không giấu giá trị nghiệp vụ trong notebook hoặc dashboard |
| Giả định | Lấy A08–A17 từ PLAN mục 3.2, giữ trạng thái đề xuất, nguồn/lý do/phạm vi/đơn vị và độ nhạy. M01/M02 thuật lại mentor không xác nhận success, Vina→Vinaphone hay con số tồn |
| Seed | A17 đề xuất 42 cho thành phần ngẫu nhiên; ghi seed và thư viện sử dụng. Mô phỏng cơ sở xác định; seed không thay bằng chứng tái lập |
| Phiên bản | `target_definition_version` cho định nghĩa nhãn; `config_version` cho cấu hình; `assumption_version` cho giả định; lưu phiên bản mã và phụ thuộc. Đổi giá trị phải truy được, không chỉ sửa file tại chỗ rồi giữ run cũ như còn hợp lệ |
| Run | Đầu ra dự kiến trong `outputs/<run_id>/`, cùng manifest; giữ lịch sử run thay vì ghi đè kết quả được báo cáo. Tách lần chạy/kịch bản; trạng thái từng bước rõ, lỗi không được gắn thành hoàn tất |
| Manifest | Hash/kích thước nguồn hiện có, config/mã, Python/thư viện, seed, cutoff, phiên bản target/config/assumption, bước thành công/thất bại. Nếu không lấy được Git revision do ownership/kho cha, ghi giới hạn và dấu vết mã thực có; không bịa commit |
| Hợp đồng đầu ra | Theo [data-contract](data-contract.md#outputs). Trước khi xuất bảng phải ghi rõ tên ngày mục tiêu và mapping `forecast_date`/`target_date`; dùng `sku` đúng CSV, kiểm tra khóa/đơn vị và các bảng cùng run |
| Bàn giao/demo | Một run hoàn tất và manifest khớp; dashboard từ chối thiếu/trộn phiên bản/hết hiệu lực. Phân biệt gói riêng tư local với gói dữ liệu giả theo quyền chia sẻ |

Thiếu đối tác báo `missing_partner_config`, không dùng ngưỡng chung/0 để lấp. Thiếu inventory khác tồn 0; thiếu receipts khác danh sách rỗng được khai báo. Forecast tháng 01/2026 chưa có actual order phải để trống. Ví dụ mô phỏng hoặc fixture dùng dữ liệu giả, không sao chép định danh nguồn.

Khi Git có thể dùng, kiểm tra root trước và giới hạn thao tác trong project. Với trạng thái hiện nay, Git đã báo ownership ở kho cha: không đổi global config/safe.directory, không quét kho cha hoặc tự xác nhận tracked/deleted. Dùng danh sách tệp và hash làm bằng chứng cục bộ, nêu rõ không thay thế Git diff.

<a id="checks"></a>
## 3. Chọn kiểm tra theo thay đổi

Danh mục sau lấy từ PLAN mục 8 và R01–R09, là ca phải triển khai về sau, **chưa được chạy như tests pipeline**. Kiểm tra cần có kỳ vọng độc lập/tính tay, không chỉ lặp lại công thức của mã đang kiểm tra.

| Thay đổi | Ca kiểm tra và kết quả cần chứng minh |
|---|---|
| Chỉ Markdown/nhãn | Link/anchor tồn tại; đúng tên tệp và số cột bảng, đóng khối mã; target/split/task/status nhất quán; phần dự kiến không bị gọi là có thật. Nếu chỉ đổi trình bày, không fit lại mô hình |
| Audit/target/dedup | UTC và 29/02/2024; order timestamp thiếu/sai; quantity>1 được cộng đúng, không lấy số dòng; quantity lỗi; duplicate cùng ID giống/mâu thuẫn, khác ID không tự xóa; đối soát quantity trước/sau xử lý; nguồn không đổi hash |
| Activation/trạng thái | Fixture giả success chưa active và activation muộn vẫn tính ngày đặt; sửa activation không đổi sales, feature, top 10 hoặc tiêu thụ mô phỏng. Refunded riêng; không tự tạo hủy/hoàn nhập |
| Chuỗi ngày/missing | Ngày không giao dịch trong phạm vi quan sát có 0; dữ liệu mất và chưa actual vẫn thiếu; lưới 731 ngày/46 tuyến theo thiết kế và số ngày tính từ lịch, không hardcode 730 |
| Feature/backtest | Sửa dữ liệu sau origin không đổi forecast tại origin; sửa test không đổi top 10 train hoặc tỷ trọng tại origin trước test. Mọi nhãn huấn luyện nhiều horizon ≤ cutoff fit; không dùng actual trung gian trong horizon, activation hoặc trạng thái cuối tương lai |
| Baseline/mô hình | Tính tay naive/MA7/seasonal naive 7; cùng cặp origin–horizon và quy tắc refit 7 ngày/cập nhật actual đã qua. SARIMA không hội tụ có log/lý do loại, không bỏ riêng dự báo xấu. LightGBM chỉ kích hoạt từ validation, không tìm cấu hình bằng test |
| Metric | Ví dụ actual 0/toàn 0, forecast 0, thiếu nhãn, nhiều origin cùng ngày; đúng dấu bias và mẫu số. Metric truy predictions, không làm tròn forecast trước chấm; âm chặn 0 có thống kê |
| Phân bổ | Tỷ trọng sales 30 ngày kết thúc origin; thiếu tổng dùng 90; cả hai 0 ghi thiếu cơ sở. Tổng chi tiết khớp forecast tuyến; không chuyển nước/carrier; không dùng tỷ trọng toàn kỳ |
| Tồn/ngưỡng | Cùng forecast/tồn, hai partner có tham số khác cho cảnh báo khác; ROP−1 kích hoạt, =ROP và +1 không. Trigger closing_on_hand < ROP; IP chỉ tính Q; Q=0 không áp MOQ; thiếu cấu hình báo rõ; H≥L+R |
| Ledger/ETA | Nhận lô đầu ngày theo ETA, giao dịch theo order_datetime/order_id, quyết định đặt sau chốt ngày. ETA sớm/đúng/muộn; hàng chưa tới không tăng on_hand; đã đặt đủ không đặt trùng. Tồn không âm; closing=opening+receipts−fulfilled; historical_sales=fulfilled+shortage; không sửa sales gốc |
| Cảnh báo | Cạn ngày 10 có cảnh báo tại origin báo trước ≥7 ngày; ngày 3 là muộn. Đã tồn 0 ở origin không là cảnh báo sớm tương lai; không bịa ngày ngoài H. Event đầu tiên/mặt hàng/đợt duy nhất, TP/FP/FN và mẫu số đúng; không có sự kiện/cảnh báo thì tỷ lệ tương ứng không xác định |
| Tích hợp/run | Thiếu gói/manifest, trộn version hoặc run hết hiệu lực phải báo rõ; dashboard khớp CSV; tái lập từ cùng input/config/seed. A12 chỉ tính lại tồn/cảnh báo nếu forecast độc lập; A08 tính lại mọi đầu ra target phụ thuộc |
| Bảo mật | Gói chia sẻ theo allowlist, kiểm cả raw/ID/notebook output/run thật và lịch sử Git. `.gitignore` không xóa dữ liệu đã tracked theo ghi nhận cũ; trạng thái tracked hiện tại vẫn chưa kiểm chứng. Không tự upload, push, publish hoặc sửa lịch sử |

### Quy ước metric phải kiểm chứng

Đặt `error = forecast − actual`, trên các cặp có actual hợp lệ:

```text
MAPE ngày dương = 100 × mean(abs(error) / actual), chỉ actual > 0
MAE             = mean(abs(error)), mọi cặp có nhãn
WAPE            = 100 × sum(abs(error)) / sum(actual), mọi cặp có nhãn
bias            = mean(error), mọi cặp có nhãn
```

Báo số cặp dương/tổng có nhãn và độ phủ; mẫu thiếu phải công khai. Toàn actual=0 thì MAPE/WAPE không xác định, không trả 0%; vẫn báo MAE và số ngày 0. Nhiều origin cùng target_date không là nhiều ngày độc lập. R05 chỉ đạt độ chính xác khi cả 10 tuyến đạt MAPE ngày dương ≤20% trên test chính h1–7; h8–14 riêng, kèm MAE/WAPE/bias mọi ngày. Không đổi quy ước hoặc ngưỡng để đóng task.

### Tách hai loại đánh giá tồn

- **Cảnh báo:** đợt 14 ngày không chồng lấn, origin đầu 30/09/2025 rồi tăng 14 ngày, chỉ đợt đủ nhãn tới 31/12/2025. Khởi tạo từ lịch sử tới origin; không đặt mới sau cảnh báo, vẫn nhận lô đã khai báo. Mỗi mặt hàng/đợt chấm lần cạn đầu tiên; báo precision/recall, tỷ lệ báo trước ≥7 ngày, ca muộn, sai số ngày cạn và mẫu số.
- **Chính sách:** chạy riêng liên tục 01/10/2025–31/12/2025, có đặt mới/ETA; báo shortage, tỷ lệ đáp ứng, tồn bình quân cuối ngày. Không gọi cảnh báo được bổ sung hàng ngăn cạn là báo sai.
- **Độ nhạy:** thay từng trục tồn đầu cover {3,7,14}, L {1,3,7}, safety-days multiplier {0,5;1;1,5}, giữ trục khác cơ sở. Ghi kết luận có đảo chiều; không tự thêm ngưỡng precision/recall nghiệm thu hoặc suy hiệu quả vận hành thật.

Số nguyên đối soát tuyệt đối; số thực dùng dung sai được ghi **trước** kiểm tra theo phép tính/thư viện khi triển khai, không chọn sau để vượt lỗi. Hiện chưa có runtime dự án để tuyên bố dung sai hoặc tái lập đã được kiểm chứng.

## 4. Cập nhật yêu cầu và kết quả hết hiệu lực

Thực hiện theo [quy trình thay đổi hiện hành](review-log.md#change-process): ghi nguồn/ngày/mã → chỉ rõ phần thay thế → phân tích Rxx/Axx/Txx và đầu ra → sửa tài liệu/config trong phạm vi được giao → đánh dấu cần tính lại → kiểm tra lại trước khi đóng.

| Đổi gì | Cập nhật / vô hiệu hóa |
|---|---|
| Mục tiêu, A08, timezone hoặc định nghĩa ngày | requirements/PLAN/data-contract; tăng target/config version; tính lại chuỗi, EDA, top 10, mô hình/metric, phân bổ, tồn và báo cáo phụ thuộc |
| Split/feature/ứng viên/chọn mô hình | PLAN/config/protocol; đánh dấu forecast/metric/selection và kết quả phía sau. Nếu đã xem test, công khai test đã dùng; không gọi đánh giá lại cùng tập là kiểm định độc lập |
| A09–A16 hoặc tham số tồn | assumption/config version, scenario, ledger/alerts/độ nhạy/dashboard/báo cáo; giữ forecast chỉ khi không phụ thuộc thay đổi |
| Tiến độ hoặc phát hiện lỗi | Đồng bộ TASK/PLAN; bằng chứng/quyết định vào review-log. Đổi nghiệm thu thì requirements phải cùng cập nhật; không tạo task song song thay T01–T14 |
| Nhãn/diễn giải | Sửa tài liệu/hình có liên quan, kiểm nguồn/đơn vị; không vô hiệu hóa phép tính không đổi |

Chỉ chuyển giả định từ đề xuất sang thống nhất/xác nhận khi có nguồn. Giữ lịch sử, không ghi đè kết quả cũ thành kết quả mới hoặc cho dashboard dùng run hết hiệu lực. Task chưa làm không phải task “đã xong cần sửa”. Lượt bổ sung sáu tài liệu này giữ nguyên PLAN/requirements/review-log; phát hiện mới ở PROJECTMAP/data-contract. Quy trình đồng bộ trên áp dụng cho các lượt thay đổi được giao tiếp theo.

<a id="done"></a>
## 5. Checklist hoàn thành task kỹ thuật

- [ ] Đúng Txx, phụ thuộc và phạm vi được giao; các Rxx/Axx liên quan có nguồn/trạng thái rõ.
- [ ] Đầu ra thật tồn tại theo cấu trúc thực tế, schema/đơn vị/cutoff có mô tả; phần chưa có không được đánh dấu đã triển khai.
- [ ] CSV bảo toàn hash; dữ liệu quan sát/dẫn xuất/giả định/mô phỏng/dự báo phân biệt; không lộ định danh.
- [ ] Kiểm tra phù hợp đã thực chạy, ghi lệnh hoặc thao tác, đầu vào/fixture, kỳ vọng, kết quả và lỗi còn mở. Nếu chưa chạy phải nói lý do, không suy thành đạt.
- [ ] Config/target/assumption/mã và môi trường được ghi trong manifest/run nếu task tạo run; lựa chọn không nhìn test, phép tính bảo toàn đúng.
- [ ] Kết quả báo cáo truy về run; phần bị ảnh hưởng mất hiệu lực đã đánh dấu. Không đạt MAPE/cảnh báo vẫn công bố đúng, không sửa tiêu chí.
- [ ] TASK/PLAN và tài liệu liên quan đồng bộ trong phạm vi được giao; review-log có bằng chứng mới khi phù hợp; lịch sử và mã cũ được giữ.
- [ ] Có bàn giao việc còn lại/bước tiếp theo; hoàn thành phương pháp, đạt metric và chứng minh vận hành thật được phân biệt.

Các ô trên là mẫu cho kỹ thuật tương lai, không phải kết quả đã kiểm tra. Nếu sản phẩm bàn giao còn tiêu chí chưa đạt, dùng đúng diễn đạt trong requirements: “đã bàn giao sản phẩm; còn tiêu chí chưa đạt”.

<a id="handoff"></a>
## 6. Bàn giao sang phiên Codex mới

Đặt bản bàn giao ngắn trong báo cáo cuối hoặc bổ sung đúng mục liên quan của tài liệu được phép sửa; không tạo thêm tệp nhật ký song song mặc định. Không dán raw CSV, định danh hoặc toàn bộ log riêng tư.

```text
Thời điểm (Asia/Saigon) và thư mục project:
Task Txx / trạng thái / phạm vi được giao:
Nguồn Rxx, Axx, quyết định và phiên bản liên quan:
Tệp đã đọc / tạo / sửa; phần thực có và phần dự kiến:
Việc đã hoàn thành và đầu ra/run/hash làm bằng chứng:
Kiểm tra thực chạy: lệnh hoặc thao tác, phạm vi, kết quả:
Kiểm tra chưa chạy, lỗi/giới hạn còn mở:
Kết quả bị vô hiệu hóa hoặc cần tính lại:
Thay đổi tiến độ đã đồng bộ ở đâu:
Bước tiếp theo, phụ thuộc và điều kiện bắt đầu:
```

Phiên nhận bàn giao xác minh lại tệp/hash/config/manifest hiện có và Git nếu kiểm tra được trong project; không suy trạng thái từ cây dự kiến hoặc lời “đã chạy” thiếu bằng chứng. Đọc phần yêu cầu/nhật ký liên quan nếu đổi nghiệp vụ. T02–T12 nay đã có triển khai; kiểm tra trạng thái/run hiện hành ở TASK và README, không dùng bước tiếp theo ngày 02/10 để suy tiến độ.

### Bàn giao trực tiếp ngày 05 tháng 10 năm 2026

- Phạm vi: phần mềm T01–T12 và Word/slide tiến độ M2 của T13 theo CHG-008–011. T14 chưa nghiệm thu toàn bài.
- Sản phẩm: src/tests/config/CLI/notebook/dashboard đã có; run sigma_release_v4 complete với 43 tệp sealed; báo cáo local reports/M2. E14/E15 ghi hash và kết quả trực tiếp.
- Kiểm tra: 37 tests, pip check hai môi trường, 14 bảng demo tái lập, ledger số nguyên và không âm, AppTest release 0 exception/10 bảng; Word 10 trang và PPTX 16 slide đã render/kiểm tra. CI chỉ chạy dữ liệu giả.
- Giới hạn: R05 0/10 đạt, MAPE 40,93–61,96%; early-event-rate 31,67%; test đã dùng lại; tồn/nhập giả định; thiếu ảnh/PDF nguồn; chưa diễn tập run thật máy thứ hai/mentor nghiệm thu. Kết quả activation cũ không chứng minh sales.
- Tiến độ: TASK, PLAN, requirements, README, PROJECTMAP và review-log đồng bộ. Bước tiếp: rà mentor A08–A17, chẩn đoán R05/cảnh báo và diễn tập demo theo README. Không đổi actual/tiêu chí hoặc công khai dữ liệu local.

### Phạm vi mới theo CHG-012/013 — 05/10/2026

Ưu tiên project: T09/R05, T10/R07 chưa đạt; chưa làm tiếp Word/slide cho tới yêu cầu mới của người dùng. Bàn giao CHG-011 ở trên là lịch sử. Đã thêm thử nghiệm context validation-only, kiểm tra future mutation ở mọi tuyến và căn chỉnh training/inference; tổng 45 tests đạt. Không sửa run v4: mã mới cần run mới nếu tích hợp sản xuất. Chẩn đoán cơ hội cảnh báo là phân tích sau replay, không làm feature hoặc thay mẫu số nghiệm thu.

### Run tích hợp và xác minh v5/v6 — CHG-014/015

V5 qua 53 tests và `verify_release.py`, 48 tệp sealed, 1.100.320 ledger, 84 pins, AppTest 0 exception/10 bảng; demo môi trường thứ hai tái lập 14 bảng. V6 tích hợp count model theo validation, 59 tests đạt, run thật complete, 50 tệp sealed; verify_release kiểm 1.100.320 ledger/84 pins và AppTest 0 exception/10 bảng. Ledger giao dịch R06 còn bổ sung riêng; kỹ thuật chạy đúng không thay nghiệm thu R05. Các bằng chứng v5 E17 vẫn thuộc mã/run v5, không gọi hash của mã mới là mã v5. Word/slide chưa làm tiếp. Xác minh lưu JSON ngoài sealed run; ghi manifest/source/code/requirements lock và package versions; code khác phải tạo run mới.

### Nghiên cứu E32: giữ production, kiểm giả thuyết trước tích hợp

`validation_campaign.py` là entry point nghiên cứu riêng, không thuộc core hash run production. Protocol đăng ký trước fit ghi source/config/tool hash, seed/package/specs và quy tắc chọn trong train; không nhập test vào bảng daily/features/training/scoring. Chọn cấu hình trên tháng 5–6, khóa trước chấm validation tháng 7–9. Đây không thay split nghiệm thu và không tạo holdout độc lập mới sau nhiều đợt dùng validation. Forecast ratio dùng mean90 đến origin và trả về quantity gốc. Feature cùng kỳ năm trước chỉ lấy ngày đã qua; centered window lịch sử kết thúc trước origin, không centered smoothing target tương lai.

Bốn tests riêng kiểm future mutation cho feature/model fit, căn ngày năm nhuận, đơn vị quantity sau ratio và từ chối chọn bằng validation/test. Full suite hiện hành 111 pass. Đối soát độc lập direct raw CSV kiểm quantity, top10, đủ cặp origin–horizon, forecast hữu hạn, metric và inner lock; so sánh ghép cùng pairs, bootstrap theo toàn bộ 92 target days (kể cả ngày zero có trọng số MAPE 0), block7/draws2000/seed42. Protocol phân tích được sửa lỗi tên cột rồi căn full calendar trước khi phân tích; v1/v2 protocol giữ local, kết quả cuối v3, không chọn lại block/seed theo kết quả.

E32 chưa đạt: inner-locked outer validation 0/10, MAPE 36,29–52,09%. Không đưa ứng viên vào production chỉ vì fit/test kỹ thuật chạy thành công. 59 hashes sealed v11, core model hash và raw hash được kiểm lại nguyên; không cần refit hay lặp kiểm toàn ledger cho entry point nghiên cứu tách riêng này. Bước tiếp T09: dùng các bảng ablation/error-contribution để xác định giả thuyết có tín hiệu ngoài mẫu; giữ R05/R07 mở, không đổi mẫu số/target/split hoặc gọi chuẩn hóa là bảo đảm độ chính xác.

### Kiểm giao dịch v7 — CHG-016/E21

`pytest -q`: 75 tests đạt, gồm receipt trước midnight sale, timestamp/ID tiebreak toàn ngày, stock chain/partial fulfillment từng item, shock apportionment số nguyên, ngày nhận không sale, thiếu/trùng transaction bị chặn, event tamper và fractional config. Verification v7 đối chiếu private events với nguồn audited rồi ledger chunks; không log source IDs/records. 51 hashes sealed, 84 pins, AppTest 0 exception/10 bảng, bảy bảng forecast/selection/metric/mô phỏng khớp v6 tại 1e-8. Demo .venv-verify tái lập 14 bảng và chronology/event/day, không thay diễn tập máy khác. README clone đúng nhánh draft có mã, chưa nhận main/PR merged.

### Kiểm cohort v8 — CHG-017/E23

83 tests đạt; mới kiểm first-seen/giá/basket/validity proxy tính tay, horizon không dùng đơn sau origin, training/inference alignment, future mutation không đổi X/y/forecast, activation không ảnh hưởng và invalid covariate không loại sales. 51.520 validation predictions khớp prototype 1e-8. V8 verify 53 hashes/84 pins/265.985 events; AppTest 0 exception/10 bảng. Verification thêm code_file SHA-256 của run.py/app.py/src để truy đúng mã hiện hành; file ngoài sealed run và hash ở E23, không sửa bằng chứng cũ.

### Kiểm v9 — CHG-018/019/E25

92 tests đạt. Kiểm monthly calendar/future mutation/dispatch, origin stale/missing/non-midnight, demo failed resume không đổi nguồn và không khôi phục nguồn mất, orphan-dir không ghi đè, allocation plan không dùng matrix/forecast/window cũ. Real base replay từ locked forecast v8 tái lập ledger/recommendations 84.640 rows mỗi bảng ở 1e-8, events khớp source; phép dùng lại allocation không đổi công thức. Verify_release tái tính nguồn→daily/train top/validation-only selection/actual test và forecast trước chấm metric. CSV None/blank ở validation_target_met được chuẩn hóa nullable boolean, không thay kết quả. V9 real/demo verified; 14 bảng demo tái lập, AppTest 0 exception/10 bảng ở cả hai. Hash chi tiết E25.

### Kiểm v10 — CHG-020/E27

100 tests đạt; hierarchical kiểm future mutation, tỷ trọng 3:1 tính tay và tổng shares=1 khi tháng chưa có lịch sử, missing actual/count, all-zero, future fit và dispatch H14. Verify_release tái tính quantity labels/metric validation từ predictions của mọi family kể cả cache; fixtures chặn nhãn số đơn thay quantity, metric tự sửa dù được seal và missing forecast không có log excluded fit failure. SARIMA failed có NaN được giữ trong evidence/coverage nhưng loại khỏi selection, không coi là forecast hợp lệ. V10 real/demo verified; 25.760 fresh validation pairs khớp prototype 1e-8, 14 bảng demo tái lập, AppTest real/demo không exception/10 bảng. Các cải thiện validation không bảo đảm cải thiện test; không thay selection đã khóa.

**Độ nhạy E28:** Sau verify, tổng hợp ledger theo scenario/tuyến, kiểm fill không nhất thiết đơn điệu từng tuyến khi đổi cover/L/safety; tổng demand/fulfilled/shortage giữ nguồn sealed. Phân tích riêng ngoài sealed run, hashes/parent manifest ở E28; không dùng chọn model/tham số từ test.

**Kiểm E29:** 101 tests đạt; fixture missing origin–horizon pair bị chặn dù CSV/manifest đã seal. Verifier kiểm mọi model/tuyến đủ origin và H, không dùng số dòng thiếu làm mẫu số coverage. Re-verify real/demo v10 đạt; mã core/forecast/run sealed không thay. Verification v1 ngoài run được lưu riêng trước khi tạo kết quả kiểm bổ sung, hashes tại E29.

### Kiểm chuẩn hóa/loss v11 — CHG-021/E31

107 tests đạt: scaler mean bằng đúng feature history tới cutoff, future quantity mutation không đổi fit/forecast, quantity units giữ 30 sau scaler, all-zero/missing/future-fit guards và dispatch H14. check_data.py được kiểm bằng quantity tính tay 3, invalid validity không mất sale, export không IDs, raw/old output hashes nguyên. Verify real/demo và fresh validation numerical parity đạt; CI thêm independent data check với synthetic only. Test v11 kém hơn v10 ở AIS/SKT dù validation tốt hơn, không dùng test chọn lại.


### Kiểm sản phẩm chung E37–E39

150 tests đạt; raw và v11 giữ byte/hash. Verifier tuần kiểm 235.290 cặp dự báo; kiểm lại 27.876 hệ số từ dự báo quá khứ và 136.620 cặp validation không đổi. Lịch D+7 bảo toàn 118.296 quantity, có 1.885 đơn vị đã đặt cho tuần tới, 966 dòng tuyến/ngày và chưa có actual giao. Verifier tồn kiểm 920 items và 5.520 cửa sổ replay từ raw. AppTest năm trang không exception; health cổng 8503 trả HTTP 200/ok. CLI refresh complete rồi skipped_unchanged; run tốt đã verify, lịch Windows chưa cài. Bản so sánh chính thức và tổ chức lại code theo CHG-025 chưa đóng; R05 ngày, LG U+ tuần, R07 và T14 còn mở. Không sửa reports hoặc sealed run; sau thay mã/config tạo run-id mới và kiểm nguồn/cha/protocol/metric/quantity theo [hướng dẫn sản phẩm](customer-delivery.md).


### Bàn giao CHG-027/E47–E50 — 05/10/2026 (Asia/Saigon)

- Project: C:/Users/nguye/OneDrive/Desktop/TTDN_Sigma; T09/T10/T11/T12/T14. Bản so sánh và tổ chức mã đã thực hiện ngay theo yêu cầu mới; R05/R07/T14 chưa nghiệm thu toàn bài.
- Nguồn: quantity success UTC A08 thực nghiệm, split/top 10 train giữ nguyên; khách D+7 theo CHG-024, tách supplier lead time. Raw nguyên và run ngày v11/59 files nguyên.
- Tệp: sigma/ theo forecasting/inventory/delivery/jobs/ui/verification/analysis/experiments; configs/weekly.json và configs/experiments; 29 alias legacy; README/code-map/day-week-comparison/TASK/PLAN/requirements/review-log/TXT đã cập nhật. Word/slide không sửa.
- Run/hash: weekly_refactored_v12 summary ee0f61d065e009381bcaacb06fdf76967f3af895f68c67457ee80793c450f7d1; policy_v3 43f1ec2986babba4dcc3a4ef30b1392bbd1d289eac7ad3bb9817bdd10a3a3095; stock_v6/customer_v5/comparison_v2 và các verification ở outputs local. Prefix đầy đủ sigma_ như E49. config.delivery.json mặc định V12.
- Kiểm thực: 192 tests; generic 371.910 pairs; parity 364.320 validation cache/7.590 fresh test/92 future/644 allocations ở 1e-8 và cùng model choices; full policy 1.100.320 ledger/267.812 events; snapshot 920 items; D+7 raw quantity; six-page QA nguồn bài và demo; refresh complete rồi skipped_unchanged; health 200. Windows CI push và PR của code commit043cf85 đều success, xem E50.
- Giới hạn: tuần9/10, mean16,19%, LG U+21,19%; ngày R05 vẫn0/10. Test đã xem, cảnh báo early33,80% cùng2867 events chưa đạt mọi ca. Lịch Windows chưa cài, nguồn PDF/ảnh M01–M02 thiếu. SHA selection giữa hai run có thể khác do float CSV, không sửa sealed run; mỗi run giữ lock riêng, parity numeric đã kiểm.
- Kết quả lịch sử: V5/V9/V10 và bản docs cũ được giữ lịch sử; khi sửa thuật toán/config cần run mới, không dùng số tests thay accuracy. E46 boosting chỉ đăng ký/chưa triển khai/chưa chạy, proposal ignored local.
- Tiến độ đã đồng bộ TASK/PLAN/requirements/data-contract/PROJECTMAP/README/review-log. Mã đã push nhánh codex/sigma-local-pipeline, PR1 vẫn draft. PR body update chưa được thực hiện vì automated approval review từ chối external disclosure; câu hỏi quyền riêng đang chờ người dùng.
- Bước tiếp: tiếp tục giả thuyết đăng ký và lựa chọn validation để xử lý LG U+/R05; chốt metric ngày/tuần với mentor, kiểm giới hạn cảnh báo; giữ dữ liệu/run local. Chỉ cập nhật PR body sau cho phép trực tiếp; không tự nhận 100% hoặc làm Word/slide.


### Bàn giaoCHG-028/E53–E54 — 06/10/2026 Asia/Saigon

- Project C:/Users/nguye/OneDrive/Desktop/TTDN_Sigma; T09–T12/T14. Đã tinhchỉnh boosterV13 và đónggói phầnmềm dùngdemoM2–M3; T14/R05/R07 cònmở,không làmWord/slide.
- Code mới boosting.py/release.py/product_catalog.py/ui/bundle.py,CLIrelease-check,launcherstart_m2m3.ps1,SKU/typefilters,joblast_attempttime; app.py3dòngkhóarun; src/run.pynguyên. Configmặcđịnh58ứngviênV13; tổchức sigma/ +legacy giữ nguyên.
- Run mới: weekly_boost_v13,policy_v4,inventory_v7,delivery_v6,comparison_v3,checkpoint_v3,fullverifiers/calibration/6-pageQA; tấtcảoutputsprivate. SummarySHA ởE54.214tests đạt; generic447810pairs/calibration42136/fullpolicy1100320ledger267908events/920items/D+7; sourceSHA6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b/59sealedv11 nguyên.
- Tình trạng: tuần9/10mean16,17%,LG U+21,19%; ngày0/10; early33,73%. Test hồi cứu,tuầnchưamentorxácnhậnthayngày; thiếuPDF/ảnhM01–M02; tham sốtồn/nhập/mappinggiảđịnh; Word/slidetrướcđólàlịchsử.
- JobWindows07:00đãcài/chạythửmã0; job chỉrefreshD+7,khôngtựhuấnluyệnCSVmới. Bảnreportkhóarun nênkhôngbịjobđổiquanhsốliệu. CI commitmới và healthV13 sẽbổsungE55,saupush/chạyserver.
- Bước tiếp: mentor xácnhậnmetricngày/tuần,review giảđịnh/nguồnthiếu,tiếptụchypothesismodelbằngvalidation vànguồn dữliệukịpthời,nêuđúnggiớihạn khi báo cáo; khôngsửatest/rawhoặcsốchấmlàmđẹp. PRbodykhônggửi khi chưađượchumancho phép.


### Kiểm kết thúc E55 — 06/10/2026

Code 183ed10 đã push, hai CI Windows (push/PR) của đúng code đều success; full local 214 tests đạt sau chuyển config/job. Commit tiếp theo chỉ đồng bộ tài liệu và ghi bằng chứng CI, không đổi implementation/test/config/run. Default job V13 complete→skip được đối soát; Scheduler mã0; server report8504/checkpointV3 health200. Browser/file Codex queued nên mở URL8504 trực tiếp khi cần. R05 ngày0/10, tuần9/10/LG U+21,19%, cảnh báo sớm33,73% và nguồn/giả định thiếu vẫn giữ nguyên giới hạn. PR body không cập nhật theo E50; dữ liệu và outputs local. Tiếp tục phần chất lượng bằng giả thuyết validation, không dùng test để chọn lại hoặc nhận nghiệm thu toàn bài.

<a id="handoff-chg068-step4"></a>
### Bàn giao CHG-068 sau bước4 — 24/10/2026 (Asia/Saigon)

**Dừng theo yêu cầu người dùng, không bắt đầu bước5–15.** Task T01/T02/T10–T12 trong phạm vi cập nhật MD/baseline/gỡ Streamlit; không refactor module/feature hoặc triển khai mode/cảnh báo mới. R05 giữ M05 tổng30 hồi cứu, H14/L7/R1 giữ cho tồn; R07/T14 chưa nghiệm thu.

- Checkout: `C:/Users/Admin/.codex/worktrees/m3-modular-config/Sigma`, nhánh `m3-implementation`, nền b1357cd. Workspace M2 và4tệp sửa dở được giữ nguyên. Giữ worktree này để tiếp tục; không restore file đã xóa, merge hoặc force-push.
- Commit từng bước: `4ccf11e` tài liệu, `35bce8b` baseline, `542321c` gỡ M3Streamlit, `db201de` gỡ M2Streamlit/dependency. Mỗi commit đã push/SHAremote khớp và2workflowCI success trước bước sau. CI mã bước4: [M3 integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40078308858), [M2 synthetic](https://github.com/khanhnguyenpham/Sigma/actions/runs/40078308935).
- Kiểm mới trong môi trường sạch `.venv-m3`, Python3.12.14:102pytest/0fail-error-skip (BE71+M2 31);26React/9files; clean npmci141package/build; pipcheck và không có Streamlit; CLIhelp;2codecell notebook dùng load_report với10route/10config/40metric; test export synthetic/overwrite guard và smoke HTTP/CSV local đạt. Baseline26APIroute/13bảng còn khớp. M2 giữ60pin/BE23pin, version cũ giữ nguyên;8pin server được chuyển từ root sang backend.
- SHA845tệp raw/artifact/report và tài liệu M2 bảo vệ không đổi. Chỉ hash/bằng chứng tổng hợp ở đây; chi tiết ở `outputs/protected-before.json`, `outputs/step4-verification.json`, `outputs/step4-clean-python.xml` trong checkout, không Git. Lượt baseline đầu gặp21setup-error do PG dừng; sau khởi động cụm cũ121test đạt, không sửa thuật toán để vượt test.
- `.venv-m3`, frontend node_modules/dist và `M3/.env` đã chuẩn bị local, ignored. Env tái dùng DB/source/output đã có từ checkout trước; không copy raw/run hoặc in credential. PostgreSQL cũ127.0.0.1:55432 đã chạy lại; không cài service toàn máy. Đã dọn đúng helper chờ stdout; chưa mở nền API/worker/Vite mới. Nạp env bằng `M3/scripts/load_env.ps1`; chạy theo README khi cần.
- Giới hạn: chưa browser tương tác trong lượt này, chưa fullmodel/refit/policy-alert replay/benchmark30 mới; bundle tổng30 thiếu vẫn monthly_not_prepared. Deprecation TestClient/httpx là cảnh báo đã biết, không đổi pin để tắt. Website Streamlit online cũ không thay đổi/xóa; code runtime Streamlit đã gỡ và tài liệu cũ có nhãn lịch sử.

**Lần tiếp tục:** kiểm branch/status/remote/CI và hash hiện có, đọc PLAN#chg-068 cùng yêu cầu mới. Bắt đầu bước5 core/catalog/configuration, giữ API/schema/transaction/versioning/snapshot và baseline; chỉ sau local→commit→push→remoteSHA→CI mới bước6. Không tự làm bước5 khi người dùng chưa yêu cầu tiếp. Lượt bàn giao chỉ cập nhật MD sau CI mã bước4; CI commit MD cuối kiểm riêng trước báo hoàn tất.

<a id="handoff-chg068-step5"></a>
### Bàn giao CHG-068 bước5 — 24/10/2026 (Asia/Saigon)

Người dùng yêu cầu bắt đầu riêng bước5 sau điểm dừng bước4. Nhánh `m3-implementation`, worktree `C:/Users/Admin/.codex/worktrees/m3-modular-config/Sigma`, checkpoint đầu lượt992b8f5 đã đối chiếu GitHub/CI. Chưa bắt đầu bước6–15; R05/M05/H14/L7/R1/A08 và R07/T14 giữ trạng thái.

- Đã làm: core DB/Base/settings/errors/DTO/hash/run context/HTTP; module catalog và configuration có model/schema/service/router, configuration giữ freeze_inventory. main391→45dòng chỉ bootstrap; api/runs.py tách route run khỏi main để chờ bước6. models.py là registry13bảng và8domain model còn lại; schemas.py còn RunCreate. Mọi import CLI/worker/services/tests/scripts/research cập nhật; không thêm wrapper, dependencies, migration hoặc nghiệp vụ mới.
- Kiểm mới:107Python/0failure-error-skip (XML `outputs/step5-final-python.xml`);26React/9files/build đạt, không sửa source FE. SHA256 canonical OpenAPI đầy đủ và DDL table/index đúng golden ghi từ992b8f5 trước sửa;6contract tests riêng đạt. Alembic check không có upgrade operation trên sigma_m3_test;22định nghĩa di chuyển giữ AST,3fresh-process import orders/CLIhelp/pipcheck đạt. Router session của2app cô lập; defaults source/output root giữ đúng checkout.
- Smoke chỉ đọc qua TestClient trên app DB local: React build/health/catalog/workspace/inventory/alerts/3purchasingview/CSV đạt. Không business-write/import/refit/fullreplay thật; tests forecast dùng fixture giả.845protectedfile giữ hash gồm raw/run/report và4tài liệu M2 sửa dở. Không sửa artifact/manifest/snapshot cũ để khớp code mới; code_digest ghi source mới cho run mới.
- Evidence local: `outputs/step5-contract.xml`, `outputs/step5-final-python.xml`, `outputs/step5-verification.json`; code hash local e4a2d28b69e73ae26584195a6b27bc843b014d7c775a76449a0fc4e4718e4115. Không đưa các output/DB/env/raw vào Git. Bộ golden công khai chỉ schema/DDL, không có dữ liệu người dùng.
- Giới hạn: chưa browser tương tác, chưa replay/model/benchmark30 mới; monthly_not_prepared vẫn là trạng thái đúng khi thiếu bundle. Cảnh báo TestClient/httpx đã biết; không đổi pin để tắt. Không chạy nền API/worker/Vite mới hoặc deploy; không đánh dấu nghiệm thu R07/T14.

Cổng mã bước5 đã kiểm: commitdb6c1d5 đã push/remoteSHA khớp, [M3 integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40082349301) và [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40082349353) đều completed/success; không suy từ CI992b8f5. Bàn giao cuối chỉ MD, CI commit MD sẽ kiểm riêng trước kết thúc. Kết thúc bước5 rồi chờ yêu cầu bước6 (forecast/runs/reporting). Khi tiếp tục, kiểm lại branch/status/remote/code/hash, đọc PLAN/TASK/PROJECTMAP và source thực; CLI/factory/start script vẫn giữ giao diện cũ.

<a id="handoff-chg069"></a>
### Bàn giao CHG-069 — đặc tả FE, 24/10/2026 (Asia/Saigon)

- Phạm vi: yêu cầu mới chỉ cập nhật Markdown và push m3-implementation; checkpointc74d80e sau bước5. Bước6–15 chưa bắt đầu. [Cấu trúc FE đích](../M3/docs/04-frontend-spec.md#frontend-target-chg069) thay feature/shared bằng pages/layouts/components và config/hooks/services/types/utils, bỏ thư mục chưa cần.
- Sản phẩm: đặc tả04, kiến trúc05, kiểm thử06, PLAN/TASK/PROJECTMAP, AGENTS và hai README đồng bộ; E103 ghi nguồn ảnh/quyền/truy vết. Không tạo thư mục hoặc di chuyển source/config/tests/CSS. Giữ frontend/tests, sáu màn hình/URL/context và hành vi HTTP/keyboard/CSV trong kế hoạch bước8–9.
- Kiểm local trước commit đã đạt: link/anchor mới, fence/bảng, bảng15bước, git diff --check và danh sách thay đổi chỉ Markdown. Commit/SHA/CI thực được kiểm riêng và báo trong thông điệp bàn giao cuối lượt. Không chạy pytest/FE build/model/replay local cho thay đổi tài liệu; CI commit mới vẫn phải đạt trước báo hoàn tất.
- Giới hạn: đây là thiết kế, không phải cây source đang triển khai. Code FE thực vẫn api/components/pages/App/main/styles.css. Giữ nguyên dữ liệu/run/snapshot/manifest và trạng thái R05/M05/H14/L7/R1/R07/T14; không deploy/merge/force-push.
- Tiếp theo khi được giao: bước6 forecasting/runs/reporting, tiếp bước7 BE rồi bước8–9 FE theo đặc tả mới. Mỗi bước giữ local→commit→push→SHAremote→CI, không tự chuyển sang triển khai vì đã sửa MD.

<a id="handoff-chg070"></a>
### Bàn giao CHG-070 — chuyển backend và dọn MD, 24/10/2026 (Asia/Saigon)

- Phạm vi được giao: gom code web, trước mắt chỉ backend và MD; xóa thêm M2_CODE_MAP.md theo tin nhắn bổ sung. Nhánh m3-implementation từ e18bda0. Đã chuyển68file M3/backend→web/backend và xóa7MD; FE/configs/scripts/research/env còn M3. Worker/CLI vẫn sigma_m3, không tách service hoặc queue.
- Đổi cần thiết: CI/cache/install/test/Alembic command sang web/backend; code_digest theo source mới, API static và acceptance/profile đọc đúng M3. Hai script nghiên cứu chỉ đổi đường dependency hash. Cài lại editable bằng pip install --no-deps -e web/backend đã đạt; --no-build-isolation không dùng được vì venv thiếu setuptools, không thay lock runtime.
- Kiểm trước/sau:107→109Python0failure/error/skip;26React/9file, TypeScript/Vite build/pipcheck/CLI M2-M3 đạt. API/DDL golden không đổi, Alembiccheck0upgrade,3freshimport worker/CLI/monthly đạt. TestClient đọc DB local health/catalog và React build đạt; không business-write. Hai test mới kiểm static từ M3/frontend/dist và fingerprint bắt thay đổi BE ở web/backend.
- Bảo toàn:63/68file backend giữ byte; chỉ4file production sửa path/import và1test thêm ca. Worker/CLI/migration/lock và toàn bộ FE/configs/launcher giữ nguyên;845protectedhash gồm raw/artifact/report và sửa dở workspace M2 nguyên. Xóa MD chỉ tại worktree này; file M2_CODE_MAP.md sửa dở của workspace M2 khác giữ nguyên. Danh sách7file và tra Git ở [E104](review-log.md#removed-docs-chg070).
- Evidence local ignored: outputs/chg070-before.xml, chg070-after.xml, chg070-backend-before.json, chg070-verification.json. Code digest mới09692eaf98de364786f80239b2bed19f761b3cc24c578764c77b8a3ed013ca44 dùng cho run mới; không sửa sealed run/manifest cũ. Markdown kiểm link/anchor/fence/bảng15bước, staged diff và phạm vi trước commit.
- Giới hạn: chưa browser tương tác/fullmodel/refit/replay/benchmark30 mới; không migrate DB app/deploy/merge/force-push. Cảnh báo TestClient/httpx cũ còn, không đổi pin. Giữ M05/R05/H14/L7/R1 và R07/T14 chưa nghiệm thu. Commit/push/remoteSHA/CI được kiểm đúng commit mới trước thông điệp bàn giao cuối lượt.
- Bước tiếp khi được giao: tiếp tục module bước6–7, rồi chuyển/refactor FE vào web/frontend theo CHG-069 ở bước8–9; bước6–15 vẫn chưa bắt đầu trong lượt này. Không tạo frontend/worker rỗng ở web hoặc copy code hai nơi.

<a id="handoff-chg071"></a>
### Bàn giao CHG-071 — source phẳng và launcher trong backend, 24/10/2026 (Asia/Saigon)

- Phạm vi: yêu cầu mới bỏ wrapper sigma_m3 và gom worker còn lại vào web; làm tại C:/Users/Admin/OneDrive/Desktop/WorksSpace/Sigma, nhánh m3-implementation từ e0c5843.44file source chuyển vào web/backend/src,6launcher/helper vào web/backend/scripts; PROFILE từ __init__ wrapper vào core/settings giữ nguyên giá trị. Worker cùng BE, không thêm service/queue/shim. M2 root src và FE/configs/research/env M3 giữ vị trí. Bước6–15 chưa bắt đầu; R07/T14 chưa nghiệm thu.
- Packaging/import:5py-modules main/worker/cli/models/schemas và4package api/core/modules/services. API main:create_app, worker python -m worker, CLI python -m cli; chạy từ root hoặc launcher PowerShell. Distribution sigma-m3 và DB/env giữ tên cũ, không đổi bảng/API/schema. CI có kiểm hai entry point CLI/worker mới. PROJECT_ROOT/cache source hash/ingestion/adapter và launcher root cập nhật; không nhân bản M2.
- Môi trường: tạo Desktop .venv-m3 riêng Python3.12.14, cài đúng lock và editable; giữ .venv M2. M3/.env ignored tái dùng cấu hình local có sẵn ở worktree cũ, không ghi đè env hiện có hoặc copy raw/run; npmci141package theo lock. Wheel có44Pythonfile và đủ top-level module/package, không chứa package sigma_m3 hoặc root src của M2.
- Kiểm mới: baseline109Python bằng venv đã khóa ở worktree trước, source Desktop; sau110Python0failure/error/skip bằng venv Desktop.26React/9file/TypeScript/build/pipcheck/wheel/CLI-workerhelp đạt. OpenAPI/DDL golden không đổi, Alembiccheck0upgrade,5freshimport không shadow M2 src;40module AST nguyên ngoài import và4module hạ tầng đã rà path/PROFILE.5PSscript parse/load_env đạt.
- Smoke: dùng stack helper mới với state/log riêng outputs/chg071-smoke và sigma_m3_test đã làm trống, không chạy queue/DB app. API+worker khởi động hidden, health và React build200; stop đúng PID và state đã xóa. Không giữ server/worker smoke nền. No browser/fullmodel/refit/replay/benchmark30 mới; cảnh báo TestClient/httpx lịch sử còn, không đổi pin.
- Bảo toàn:906hash raw/artifact/report/M2 src/FE/configs không đổi.4sửa dở M2 vẫn stash fab40326 và outputs/local-backups/m2-before-m3-20261024-2b633f18, không khôi phục map vào root. Source digest mới be3a0cee181a2ab20d89dc9ceef8f99b9f4895ffdb76d47468ba57db03672930 cho run mới; sealed manifest/snapshot/run cũ nguyên.
- Evidence local ignored: outputs/chg071-before.xml, chg071-after.xml, chg071-protected.json, chg071-before-files.json, chg071-verification.json, chg071-ast.json và tmp/chg071-wheels. Markdown/link/anchor/fence/bảng15bước và staged scope kiểm trước commit; commit/push/SHA/CI chỉ xác nhận sau kiểm đúng commit mới trong thông điệp cuối lượt.
- Tiếp theo khi được giao: bước6–7 module BE, bước8–9 chuyển/refactor FE theo CHG-069; không tự triển khai tính năng hoặc nâng nghiệm thu vì đã đổi cấu trúc. Không merge/force-push/deploy hoặc đưa private outputs/DB/env lên Git.

<a id="handoff-chg068-step6"></a>
### Bàn giao CHG-068 bước6 — 25/10/2026 (Asia/Saigon)

- Phạm vi: người dùng yêu cầu tiếp tục bước kế tiếp và push GitHub. Làm trực tiếp Desktop/m3-implementation từ4abdc8a; đã xác minh remoteSHA checkpoint này và cả2workflowCI success trước sửa. T08–T12 chỉ thực hiện bước6, không bước7–15; M05 tổng30/H14/L7/R1 và R07/T14 chưa nghiệm thu giữ nguyên.
- Sản phẩm: modules/forecasting chứa ingestion/service/allocation/M2adapter và3model; modules/runs chứa Run/RunCreate/enqueue/progress/router/verification; modules/reporting chứa DTO/filter/dataset/metric/CSV/monthly. clean_json chuyển core/serialization để API/research/simulation dùng chung. models.py giữ registry13bảng và4model tồn; bỏ root schemas.py, packaging còn4py-modules. Worker/CLI dùng trực tiếp cùng module,6launcher giữ byte. [Cây thực](../M3/docs/05-source-architecture.md#step6-actual).
- Kiểm mới bằng .venv-m3 Python3.12.14: baseline110Python, sau111Python,0failure/error/skip, gồm PostgreSQL test thật và M2 golden1e-8;26React/9file/TypeScript/Vite build/pipcheck/CLI-workerhelp đạt. Thêm nhánh kiểm import dedup qua worker tới complete/verified và manifest; kiểm các model module cùng registry/Base. OpenAPI canonical/DDL13bảng golden không sửa, Alembiccheck0upgrade.138định nghĩa class/hàm giữ AST ngoài import;5thứ tự freshimport không vòng lặp/shadow src M2. Wheel sạch chứa đúng52Pythonfile, không mang source cũ hoặc schemas.py ở root.
- Smoke: launcher API+worker khởi động trên sigma_m3_test đã làm trống, source/output riêng outputs/step6-smoke; health/React/runs/items/suppliers HTTP200 và danh mục trống. Dừng đúng2PID/state do launcher tạo. Worker success đã kiểm trong suite với synthetic; không chạy queue app thật.906hash raw/artifact/report/M2src/FE/configs và tài liệu M2 được bảo vệ nguyên; stash/bản sao M2 giữ nguyên. Không import/refit/fullreplay/benchmark30 thật hoặc sửa sealed run/snapshot để khớp source mới.
- Giới hạn môi trường: lần baseline đầu sandbox chặn TCP/temp; dừng lượt lỗi, khởi động cụm PG portable hiện có ngoài sandbox rồi baseline110 và suite111 đều đạt. Lần smoke contract ban đầu bắt thiếu import DateTime, đã sửa và toàn suite đạt. Wheel đầu lẫn file build ignored từ checkpoint cũ; xóa đúng web/backend/build đã xác minh, build sạch và đối chiếu toàn bộ file wheel. Cảnh báo TestClient/httpx cũ vẫn có; không đổi dependency lock.
- Bằng chứng local ignored: outputs/step6-before.xml, step6-after.xml, step6-protected.json, step6-before-source.json, step6-ast.json, step6-verification.json, step6-smoke.json; wheel tại tmp/step6-wheels. Markdown/link/fence/bảng15bước và staged scope kiểm trước commit; commit/push/remoteSHA/CI chỉ xác nhận sau khi kiểm đúng commit trong thông điệp cuối lượt.
- Tiếp theo: bước7 tách inventory/purchasing/alerts khi người dùng giao; giữ cổng từng bước. Không merge/force-push/deploy hoặc đưa raw/run/DB/env lên Git.

**Cổng GitHub đã kiểm cho mã bước6:** commit `7023c722e9ba9de931e64e340eb0721884389b7a` push thường lên m3-implementation, remoteSHA khớp. [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40155370081) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40155370071) đều completed/success, đủ4job test/backend/m2-regression/frontend. Bước6 hoàn tất; bước7–15 chưa bắt đầu. Commit tài liệu bằng chứng sau mốc này được kiểm SHA/CI riêng trước bàn giao cuối.

<a id="handoff-chg068-step7"></a>
### Bàn giao CHG-068 bước7 — 25/10/2026 (Asia/Saigon)

- Phạm vi: yêu cầu trực tiếp tiếp tục bước7; Desktop/m3-implementation từ203e506, checkpoint đã kiểm remoteSHA khớp và2CI success trước sửa. T10–T12 chỉ bước7, không bước8–15/tính năng cấu hình mới; M05 tổng30/H14/L7/R1 và R07/T14 chưa nghiệm thu giữ nguyên.
- Sản phẩm: modules/inventory có2model ledger/event, phép tính L7/R1/H14, simulation/seeding và workspace/filter/router; modules/purchasing có Replenishment/receipt/filter/read service/router/CSV; modules/alerts có Alert/project/metric/diagnostic/router/DTO. Reporting giữ dataset/metric/CSV dùng chung, runs giữ verifier độc lập. Main thêm router alerts; worker/CLI đổi import. models.py chỉ registry13model trên một Base; bỏ source/package api/services cũ, packaging chỉ core/modules và4py-modules. [Cây thực](../M3/docs/05-source-architecture.md#step7-actual).
- Kiểm mới: `.venv-m3/Scripts/python.exe -B -m pytest web/backend/tests tests M2/models/tests --junitxml=outputs/step7-after.xml -q` đạt120test,0failure/error/skip; baseline111test trước sửa đạt. Thêm9snapshot canonical từ203e506 trước tách: policy/alert replay và projection × base/pending/zero-stock; kiểm toàn ledger/event/order/alert/case/summary. Fixture tại web/backend/tests/fixtures/inventory_step7_baseline.json không tái sinh sau sửa. Suite gồm MOQ/ROPstrict/pending, ETA/receipt trước sale/idempotent receipt concurrency, as-of history/CSV/null, parent/snapshot/worker và M2golden1e-8.
- Kiểm khác:26React/9file/TypeScript/Vite build, pipcheck, CLI-workerhelp đạt; OpenAPI canonical/26route/DDL13bảng golden nguyên, Alembiccheck0upgrade.137định nghĩa class/hàm giữ AST ngoài import; main.create_app chỉ thêm alerts_router trong tuple và đã kiểm OpenAPI.5freshimport không vòng lặp/shadow src M2. Editable install và wheel sạch61Pythonfile đạt, không chứa source api/services hoặc namespace sigma_m3 cũ.6launcher không đổi byte.
- Smoke: API+worker trên sigma_m3_test đã làm trống, source/output riêng outputs/step7-smoke; health/React/runs/items/suppliers HTTP200, dữ liệu test trống. Dừng đúng2PID/state launcher tạo; không xử lý queue app thật.906protectedhash raw/artifact/report/M2src/FE/configs nguyên, stash/bản sao M2 giữ local. Không refit/fullreplay/benchmark30 thật hoặc sửa sealed artifact/snapshot.
- Giới hạn: lần collection đầu bắt thiếu import Text ở inventory model, đã sửa trước suite120đạt; không đổi golden/API/DDL để vượt test. Cảnh báo TestClient/httpx cũ còn; không đổi dependency lock. Wheel được build sau khi dọn đúng web/backend/build ignored đã xác minh, không mang file cũ.
- Bằng chứng local ignored: outputs/step7-before.xml, step7-after.xml, step7-protected.json, step7-before-source.json, step7-ast.json, step7-verification.json, step7-smoke.json; tmp/step7-wheels. Markdown/link/fence/bảng15bước và staged scope kiểm trước commit; commit/push/remoteSHA/CI chỉ xác nhận sau kiểm đúng commit trong thông điệp cuối lượt.
- Tiếp theo: bước8 tách shared components/hooks/services/types/utils/config FE khi người dùng giao; bước9 tổ chức pages/layouts. Không tự triển khai bước8–15, merge/force-push/deploy hoặc đưa raw/run/DB/env lên Git.

**Cổng GitHub đã kiểm cho mã bước7:** commit `e445b11b0c6a8be883fdf1fdab0788145d32fde9` push thường lên m3-implementation, remoteSHA khớp; [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40157107231) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40157107229) đều completed/success, đủ4job test/backend/m2-regression/frontend. Bước7 hoàn tất; bước8–15 chưa bắt đầu. Commit tài liệu bằng chứng sau mốc này được kiểm SHA/CI riêng trước bàn giao cuối.

<a id="handoff-chg068-step8"></a>
### Bàn giao CHG-068 bước8 — 25/10/2026 (Asia/Saigon)

- Phạm vi: yêu cầu trực tiếp tiếp tục bước8; Desktop/m3-implementation từc5b0e5b đã remoteSHA khớp và2CI success trước sửa. Chỉ T11/T12 bước8, không bước9–15; FE vẫn M3/frontend. Backend/API/13bảng/M2/model/data/config/lock giữ nguyên; M05/H14/L7/R1 và R07/T14 chưa nghiệm thu không đổi.
- Sản phẩm: tách common.tsx thành11UIcomponent (gồm Icon/PageBoundary đã chuyển),2hook useResource/useDialogFocus; chuyển HelpDialog/RunDialog, MonthlyForecast/AlertOpportunity vào dialogs/forecast/alerts. api/client.ts tách services/http (api/ApiError), types/api/context, utils/format/labels/url và config/http/navigation. WorkspaceData/PurchasingView dùng trực tiếp từ types; PAGES/inventoryKinds/readPurchasingView chuyển khỏi App, không tách state/effect/layout/form lớn. Không shim/barrel/dependency mới. [Cây thực](../M3/docs/04-frontend-spec.md#step8-actual).
- Giữ hành vi: Fetch API prefix/api/v1, deadline đọc30s/ghi90s, abort cleanup, không tự retry write, Idempotency-Key/body giữ khi retry. useResource giữ refresh/chặn stale; focus giữ Tab/Escape/topmost/return; Table/Pager/CSV/null khác0 giữ nguyên. App và6page giữ JSX/state/effect; main chỉ đổi import PageBoundary. styles.css giữ byte và import ở App, chưa index.css/layouts/useAppContext của bước9.
- Kiểm mới: baseline `npm test`26React/9file và build đạt; sau `npm test -- --reporter=default --reporter=junit --outputFile=../../outputs/step8-after-react.xml`30React/10file, TypeScript/Vite build đạt.4ca mới kiểm Enter/Space trên bảng, biên phân trang50dòng, URL/filter CSV cùng prefix, focus trap/Escape/trả focus của drawer. Suite cũ kiểm timeout/abort/late response/refresh/error/idempotency/null/loading/scenario và monthly.120Python baseline0failure/error/skip trước sửa; sau chạy9test modular/contract/static React0failure/error/skip, pipcheck đạt. Không sửa backend nên không lặp lại toàn suite Python local sau refactor FE; CI vẫn kiểm Python đầy đủ.
- Đối chiếu độc lập:53khai báo/câu lệnh TypeScript/JSX giữ AST sau chuẩn hóa xuống dòng, bỏ import/export và thay3tham chiếu hằng HTTP bằng đúng literal cũ; không đổi JSX/hook/thân App. Dùng parser đã có trong Rolldown của Vite, không thêm package. Graph import không vòng; không còn common.tsx/client.ts.970protectedhash của raw/artifact/report/M2/backend/migration/BEtests/FElock/CSS/config nguyên; TS/TSX FE được giao sửa loại khỏi baseline protected. CSS SHA256 `9505f1be628ca0e8cb251c77baf46b4006a24b6f52bdf8e355e353f8cb3cc88e`, asset CSS build giữ tên/hash cũ.
- Browser smoke: build do FastAPI phục vụ trên sigma_m3_test đã làm trống, source/output riêng outputs/step8-smoke; mở đủ6màn hình qua sidebar, lazy pages tải xong, trạng thái trống đúng và bảng/pager cấu hình hiện. Help nhận focus vào nút đóng; Escape đóng và focus về trigger. Không submit form hoặc xử lý queue app thật; tab tạm và2PID/state stack smoke đã dừng. Đây là smoke DB trống, các ca dữ liệu dùng fixture RTL; chưa nhận full business E2E/mobile mới hoặc chạy model/replay thật.
- Giới hạn môi trường: TestClient contract kẹt thread trong sandbox, đã dừng và9test ngoài sandbox đạt; cảnh báo TestClient/httpx cũ còn, không đổi lock. Lệnh build đầu gọi nhầm root không có script, đã chạy đúng M3/frontend và đạt. AST lượt đầu khác CRLF/LF trong JSXText do snapshot Python chuẩn hóa, đã chuẩn hóa xuống dòng chỉ trong verifier; không sửa JSX để ép khớp.
- Bằng chứng local ignored: outputs/step8-before-react.xml, step8-after-react.xml, step8-before-python.xml, step8-contract-python.xml, step8-before-source.json, step8-protected.json, step8-ast.json, step8-verification.json, step8-checks.json và step8-smoke logs. Markdown/link/fence/bảng15bước và staged scope kiểm trước commit; commit/push/remoteSHA/CI chỉ xác nhận sau kiểm đúng commit trong thông điệp cuối.
- Tiếp theo: bước9 tách layouts/useAppContext/form/drawer lớn, tổ chức6pages và styles.css→index.css theo CHG-069 khi được giao. Không tự thực hiện bước9–15, deploy/merge/force-push hoặc đưa raw/run/DB/env lên Git.

**Cổng GitHub đã kiểm cho mã bước8:** commit `3fbebabb31f6507326b3e48901fd8bd62a87bf01` push thường lên m3-implementation, remoteSHA khớp; [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40158351493) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40158351455) đều completed/success, đủ4job test/backend/m2-regression/frontend. Bước8 hoàn tất; bước9–15 chưa bắt đầu. Commit tài liệu bằng chứng sau mốc này được kiểm SHA/CI riêng trước bàn giao cuối.


<a id="handoff-chg068-step9"></a>
### Bàn giao CHG-068 bước9 — 25/10/2026 (Asia/Saigon)

- Phạm vi: yêu cầu trực tiếp tiếp tục bước9; Desktop/m3-implementation từd83e778 đã kiểm remoteSHA/2CI success. FE giữ M3/frontend, chỉ T11/T12 bước9; không tính năng bước10–15. Backend/API/13bảng/M2/model/data/config/lock và M05/H14/L7/R1 giữ nguyên; R07/T14 chưa nghiệm thu.
- Sản phẩm: App ghép6page với AppLayout; Sidebar/Header/ContextFilters riêng, useAppContext giữ state/effect/handler. useConfiguration giữ controller/lưu phiên bản; ConfigurationDialog/ItemSelect/PolicyForm/ScenarioForm/PolicyOverrideEditor/ReceiptEditor và PolicyFields dùng chung. InventoryDetails/PurchasingDetails/AlertDetails nhận selection từ page; query/refresh/stale guard và URL cũ giữ ở page/context. Overview/Forecast đã ghép component từ trước nên không đổi source. styles.css đổi index.css giữ byte, main import CSS. [Cây thực](../M3/docs/04-frontend-spec.md#step9-actual).
- Kiểm mới: baseline30React/10file và build đạt; sau34React/11file, TypeScript/Vite build đạt.4ca mới kiểm Back/reload/run-change reset filters, mobile menu Escape/return focus, policy409giữ form/retry đúng body và batched override update; suite cũ kiểm abort/late response/loading/error/focus/receipt batching/Idempotency-Key/CSV/null.120Python baseline0failure/error/skip trước sửa; sau9modular/OpenAPI/DDL/static React contract0failure/error/skip và pipcheck đạt. Backend nguyên nên không lặp toàn suite Python local sau refactor FE; CI kiểm đầy đủ riêng.
- Đối chiếu độc lập: dùng parser Rolldown đã có trong Vite,29câu lệnh App/context và11câu lệnh configuration giữ AST/thứ tự; JSX layout giống sau inline3layout con.3drawer giữ DOM/handler sau ánh xạ onClose, alert derivation giữ nguyên,3PolicyFields input giữ native constraint.969protectedhash (backend/migration/BEtests/M2/raw/artifact/report/FElock/config) nguyên; CSS kiểm riêng khi đổi tên. CSS SHA256 `9505f1be628ca0e8cb251c77baf46b4006a24b6f52bdf8e355e353f8cb3cc88e`, asset index-DR7ZeqKr.css giữ tên/hash; graph import không vòng/không unresolved.
- Browser smoke: build phục vụ qua API/worker local trên sigma_m3_test, seed fixture synthetic từ test workspace sẵn có; nguồn/output ở outputs/step9-smoke.6page mở đúng; tồn7/ROP20/pending20/Q0, lô1 có20đơn vị/received0/ETA04-11; liên kết tồn→nhập cùng run/kho/SKU/ngày.3drawer mở/đóng Escape/focus, policy/scenario mở đúng trường. Back+reload giữ view incoming và context; mobile390 menu Escape trả focus, screenshot bố cục kiểm cùng desktop1440. Forecast thiếu monthly bundle hiển thị trạng thái thiếu nguồn, không coi là kiểm dữ liệu thật. Không submit form/queue thật; tab tạm đóng, viewport reset, đúng2PID/state stack đã dừng, PostgreSQL giữ chạy.
- Giới hạn: không chạy model/replay hoặc full business E2E dữ liệu thật; form submit/conflict/batching kiểm bằng RTL. TestClient cần chạy ngoài sandbox như lượt trước; cảnh báo httpx/TestClient cũ còn, không đổi lock. Định dạng bằng prettier tạm từ registry, không thêm dependency; không sửa cài đặt toàn cục.
- Bằng chứng local ignored: outputs/step9-before-react.xml, step9-after-react.xml, step9-before-python.xml, step9-contract-python.xml, step9-before-source.json, step9-protected.json, step9-verification.json, step9-checks.json và smoke logs. Kiểm Markdown/link/anchor/fence/bảng15bước và staged scope trước commit; cổng commit/push/remoteSHA/CI xác nhận đúng commit sau đó.
- Tiếp theo: bước10 persist configurable inventory policies (migration/DTO/version/override và bảo toàn snapshot) khi người dùng giao. Không tự làm bước10–15, deploy/merge/force-push hoặc đưa raw/run/DB/env lên Git.

**Cổng GitHub đã kiểm cho mã bước9:** commit `62a97e4436c31845c37a3fc19827ea98f4ff6771` push thường lên m3-implementation, remoteSHA khớp; [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40160122665) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40160122704) đều completed/success, đủ4job test/backend/m2-regression/frontend. Bước9 hoàn tất; bước10–15 chưa bắt đầu. Commit tài liệu bằng chứng sau mốc này được kiểm SHA/CI riêng trước bàn giao cuối.


<a id="handoff-chg068-step10"></a>
### Bàn giao CHG-068 bước10 — 25/10/2026 (Asia/Saigon)

- Phạm vi/nguồn: người dùng giao trực tiếp bước10; Desktop/m3-implementation từ64908da đã kiểm remoteSHA/2CI success trước sửa. Chỉ T10/T12 persistence policy, không tính toán/cảnh báo/UI bước11–14. Giữ M05 tổng30/H14/L7/R1,13bảng, M2/FE/dữ liệu/lock/dependency và R07/T14 chưa nghiệm thu.
- Sản phẩm: modules/configuration/{models,schemas,service,context}.py lưu safety_mode, safety_lookback_days, safety_factor, rop_mode, warning_horizon_days; PolicyCreate có default tương thích, PolicyOverride thiếu/null kế thừa. Policy version/expected_version/lock/effective intervals giữ; scenario version bất biến; freeze_inventory mang5giá trị hiệu lực/override vào run mới. core/run_context.snapshot_maps thêm default vào bản sao khi đọc legacy, không ghi config_snapshot/config_sha256. [Schema/default/command migrate](../M3/docs/02-data-model.md#policy-persistence-step10), [API](../M3/docs/03-backend-api.md#policy-api-step10).
- Migration:0002_configurable_inventory_policies.py (revision0002_policy, parent0001_m3) thêm5cột NOT NULL/server default và5check tên rõ trên supplier_item_policies, không đổi bảng khác/JSON cũ. Test DB thực hiện head→0001→seed legacy→head→head, kiểm backfill, reject NULL/enum/range/NaN/±Infinity,13bảng và Alembic compare_metadata0diff kể cả type/server_default. Không sửa migration0001 hoặc golden cũ; contract so OpenAPI/DDL còn lại sau loại đúng5trường/5check được giao thêm.
- Kiểm mới: baseline120Python BE/M2,34React/11file/TypeScript/Vite build đạt. Sau sửa144Python BE/M2 (0failure/error/skip), gồm24ca mới trong test_policy_persistence và kiểm concurrency hiện hữu được mở rộng với mode/factor khác nhau. Kiểm bốn tổ hợp mode lưu/đọc; min/max/zero; partial override; version/supplier/effective date; new run nhận config mới, run/scenario cũ không đổi; idempotency; invalid HTTP lỗi an toàn; DB constraints; legacy snapshot copy; guard không chạy nhầm công thức.9inventory golden và M2 parity1e-8 giữ nguyên, OpenAPI/DDL golden trước refactor không sửa. pipcheck/CLI-workerhelp đạt; toàn bộ FE source/tests/package/lock và956protectedhash raw/artifact/report/M2/config/env/golden/migration0001 nguyên. FE không sửa nên không lặp34test/build local sau BE; CI kiểm lại toàn bộ FE riêng.
- DB app local: xác nhận loopback127.0.0.1:55432/sigma_m3, revision0001_m3,0queued/running trước sửa. Đã pg_dump custom vào outputs/local-backups/step10-before-0002-20261025-141946.dump (ignored), kiểm pg_restore --list đọc được; SHA256 ed0b7ad6c19240ca629441a36f82e4cce63415c1e70ec5c1dfb5e1ad77e2d37d. Nâng0002_policy, so hash từng dòng theo PK của toàn bộ cột cũ13bảng trước/sau khớp:3run/920policy/920inventory giữ nguyên; cả config JSON/checksum/manifest nằm trong fingerprint runs.920policy nhận đúng days/forecast/28/1/7; metadata0diff. Không replay/refit/ghi đè run, không đưa DB/backup/raw lên Git. Backup đã kiểm danh mục, chưa nhận restore toàn DB đã chạy.
- Smoke: API+worker launcher trên sigma_m3_test trống, health/catalog/runs/React built root trả đúng; process ownership và stop đúng2PID/state đạt, không xử lý queue app thật. PostgreSQL portable giữ chạy. Mode fixed/volatility lưu/đóng băng được nhưng policy_at trả stage_not_implemented trước quyết định, bảo toàn công thức days/forecast đến bước11. warning_horizon hiện chỉ lưu, chưa có cảnh báo mới bước12.
- Giới hạn/sửa trong lượt: PostgreSQL ban đầu chưa chạy, baseline đầu lỗi kết nối; đã khởi động instance portable loopback có sẵn và baseline120đạt. Helper startup bị giữ stdout đã dừng riêng PID Python, giữ postgres. Test mới đầu dùng nhầm id thay run_id của response enqueue; sửa fixture theo API cũ và32targeted/144full đạt. Cảnh báo TestClient/httpx cũ còn, không thay lock. Không nhận đã nghiệm thu công thức volatility/fixed, FE mới hoặc full replay mới; các việc này ở bước sau.
- Bằng chứng local ignored: outputs/step10-before-python.xml, step10-before-react.xml, step10-targeted-python.xml, step10-after-python.xml, step10-protected.json, step10-app-before.json, step10-app-migration.json, step10-smoke.json, step10-checks.json và bản backup. Link/anchor/fence/bảng15bước, diff và staged scope kiểm trước commit; cổng GitHub xác nhận riêng đúng SHA trước bàn giao cuối.
- Tiếp theo: bước11 tính SS hai mode/ROP hai mode, lịch sử causal và kiểm default parity/biên/overflow khi người dùng giao. Bước11–15 chưa bắt đầu; không merge/force-push/deploy hoặc nâng R07/T14.

**Cổng GitHub đã kiểm cho mã bước10:** commit `dbc3038e96759994fb9ce62efa7b3c5e317768b3` push thường lên m3-implementation, remoteSHA khớp; [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40172662624) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40172662605) đều completed/success, đủ4job test/backend/m2-regression/frontend. Bước10 hoàn tất; bước11–15 chưa bắt đầu, R07/T14 chưa nghiệm thu. Commit tài liệu bằng chứng sau mốc này được kiểm SHA/CI riêng trước bàn giao cuối.


<a id="handoff-chg072"></a>
### Bàn giao CHG-072 — 25/10/2026 (Asia/Saigon)

- Nguồn/phạm vi: người dùng giao chuyển FE vào web trước bước11 để M3 chỉ giữ tài liệu. Desktop/m3-implementation từ28a475e đã kiểm remoteSHA/2CI success trước sửa. Đây là chuẩn bị thêm sau bước10, thay ràng buộc vị trí FE/configs/research/env trước đó; bước11–15 chưa bắt đầu, R07/T14/M05/H14/L7/R1 giữ nguyên.
- Sản phẩm:69file tracked frontend nguyên byte sang web/frontend, gồm source/tests/public/package-lock/TS/Vite; node_modules/dist ignored chuyển cùng thư mục.2config JSON và .env.example sang web/backend/configs; .env ignored chuyển nguyên byte sang web/backend/.env, load_env.ps1 đọc ../.env.2script research sang web/backend/research, import namespace web.backend.research và PROJECT_ROOT dùng chung; README protocol sang M3/docs/research.md. M3 còn12Markdown; không shim/symlink/dependency mới. [Cây thực](../M3/docs/05-source-architecture.md#web-layout-chg072), [vị trí FE](../M3/docs/04-frontend-spec.md#frontend-web-chg072).
- Caller đổi: main.py phục vụ web/frontend/dist; local_stack kiểm build mới; m3.yml npm working-directory/cache mới; runs/service.py và reporting/monthly.py đọc config mới. Tests static serving/research imports cập nhật đúng vị trí, golden không sửa. Hai script research giữ output ở root/outputs/research và đọc requirements tại root, không chạy nghiên cứu hoặc đổi model/selection/metric. Lệnh npm/env và link protocol trong README/M3 docs cập nhật; nhật ký/path checkpoint cũ giữ lịch sử, trạng thái mới đặt ở đầu tài liệu.
- Kiểm mới: baseline144Python BE/M2 và34React/11file/TypeScript/Vite build đạt; sau chuyển cùng144Python/34React/build (0failure/error/skip).1005protectedhash raw/M2/artifact/report/backend/migration/golden/FE/config/env nguyên theo ánh xạ vị trí; FE69file tracked không đổi byte.10file dist trước/sau khớp SHA256, gồm index/assets/favicon; không chỉ giữ tên asset. AST9file Python khớp sau đúng phép thay string path/import/PROJECT_ROOT, không đổi thân thuật toán khác. pipcheck và hai lệnh python -m web.backend.research.daily_validation/daily_panel --help đạt.
- Smoke local: API+worker launcher trên sigma_m3_test đã làm trống, health/catalog/runs/React root trả đúng từ build mới; stop đúng2PID/state và ownership đạt. Không chạy queue app thật, không mở/deploy dịch vụ công khai. PostgreSQL portable giữ chạy. Env/DB app chỉ đọc; hash toàn bộ3row runs (gồm config snapshot/SHA/manifest) khớp bằng chứng bước10, revision0002_policy giữ. Không migrate/refit/replay hoặc ghi đè run/DB, không push raw/run/backup/env.
- Bằng chứng local ignored: outputs/chg072-before-python.xml, chg072-after-python.xml, chg072-before-react.xml, chg072-after-react.xml, chg072-protected.json, chg072-before-source.json, chg072-before-dist.json, chg072-verification.json, chg072-smoke.json, chg072-app-readonly.json và chg072-checks.json. Kiểm Markdown/link/anchor/fence/bảng15bước và staged scope trước commit; commit/push/remoteSHA/CI xác nhận riêng đúng SHA.
- Giới hạn: không cần kiểm browser giao diện mới vì FE và build giữ nguyên byte; hành vi giữ suite34React, static serving thật và API-worker smoke. CI vẫn kiểm npm ci từ checkout mới. Cảnh báo TestClient/httpx cũ còn; không thay lock. Bước11 (SS/ROP2mode và causal history) là tiếp theo khi được giao; không tự triển khai bước11–15, merge/force-push/deploy hoặc nâng R07/T14.

**Cổng GitHub CHG-072 đã kiểm:** commit `8868740cdb2b283c84bee09dfaeb58cf7213624d` push thường lên m3-implementation, remoteSHA khớp; [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40173675195) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40173675194) đều completed/success, đủ4job test/backend/m2-regression/frontend; frontend npm ci/test/build từ web/frontend đạt. CHG-072 hoàn tất, M3 chỉ giữ12Markdown. Bước11–15 chưa bắt đầu, R07/T14 chưa nghiệm thu. Commit tài liệu bằng chứng sau mốc này được kiểm SHA/CI riêng trước bàn giao cuối.


<a id="handoff-chg068-step11"></a>
### Bàn giao CHG-068 bước11 — 25/10/2026 (Asia/Saigon)

- Nguồn/phạm vi: người dùng giao bước11; Desktop/m3-implementation từ8143cca đã kiểm remoteSHA/2CI success trước sửa. Chỉ T10/T12 SS2mode/ROP2mode và causal history; không cảnh báo/UI bước12–14, không migration sau0002_policy. Giữ web/backend/frontend, M3 chỉ Markdown, M05 tổng30/H14/L7/R1; R07/T14 chưa nghiệm thu.
- Sản phẩm: inventory/service.PolicyValues nhận mode/lookback/factor/multiplier với default legacy và validation; history_quantities kiểm cửa sổ count đầy đủ/finite/nonnegative/integer/bigint; recommend tính days hoặc population volatility, chọn fixed=floor hoặc forecast=max(floor,ceil(f1…7+SS)). SS days giữ thứ tự nhân và ceiling trước. rop_forecast vẫn diagnostic cả mode fixed; S/IP/Q/MOQ/ETA/timing receipts giữ. Chặn overflow cả diagnostic/SS/ROP/S/IP/Q, không fallback0. [Công thức/ví dụ](../M3/docs/01-functional-spec.md#configurable-calculation-step11).
- Simulation/cutoff: policy_at bỏ guard tạm của bước10; history_at lấy đúng calendar window kết thúc ngày quyết định, từ matrix DailySales chứ không dùng fulfilled. Policy replay cutoff cuốn theo ngày, alert replay giữ origin; initial stock vẫn28ngày. daily actual_available=false được giữ missing trong Int64 nullable; không chặn cả run vì nhãn chưa biết ngoài ngày thực dùng. Replay ngày actual thiếu vẫn fail, không bù0. Giữ số đếm int khi chuyển DB→Pandas, tránh mất phương sai nhỏ gần bigint max. Không sửa snapshot/run cũ.
- Independent verifier: runs/verification đọc lại actual_available/history/forecast/frozen policy, tính SS/ROP/S/IP/Q riêng, không gọi recommend/history_at. Kiểm initial history đủ và forecast cutoff đúng kind/window, policy đúng item/ngày hiệu lực; giữ đối soát ledger/event/receipt/depletion/metric cũ. Dùng cùng thư viện stdlib statistics.pstdev cho phép toán population, không dùng lại hàm tính nghiệp vụ của simulator.
- Kiểm mới: baseline144Python BE/M2 và34React/11file/build đạt. Sau214Python BE/M2 (0failure/error/skip), gồm70ca mới;98targeted trước bổ sung5ca multiplier và định dạng cũng đạt.4mode tính tay,12biên closing< /= />ROP và pending,0/constant history,lookback7/28/90, missing/NaN/Infinity/âm/phân số/bool/trùng/mất ngày,zero multiplier/factor,phương sai sát bigintmax,overflow,mutation tương lai và prefix, policy/alert cutoff.3ca guard tạm của test_policy_persistence chuyển sang kiểm mode thực thi.9inventory golden giữ hash tuyệt đối, M2 golden1e-8 nguyên; OpenAPI/DDL13bảng/golden/schema/config/FE/lock không sửa,1012protectedhash nguyên. FE không sửa nên34React/build chạy baseline, CI kiểm lại FE trên HEAD riêng. pipcheck đạt.
- Worker/API/CSV:12tổ hợp4mode×stock_projection/policy_replay/alert_replay dùng DB sigma_m3_test, source CSV hoàn toàn synthetic20cột, parent/forecast injected rõ ràng, không fit ML. Policy→scenario override→enqueue→worker→simulate→independent verify→complete/manifest verified thực chạy; SS/ROP và pending/API/CSV đối chiếu tính tay. Có unknown future label ngoài cửa sổ vẫn complete; thiếu actual trong lookback90 (ngoài28ngày tồn đầu) failed/insufficient_history và không ghi ledger dở. Cố ý sửa SS/cutoff ở fixture bị verifier chặn. API/worker TCP launcher test DB trống/serve React build/dừng đúng2PID/state cũng đạt.
- App cũ chỉ đọc: helper dùng connection PostgreSQL readonly, gọi verifier với allow_running để không ghi output verification. Projection đã khóa của app verified920ngưỡng,920events,1order,1714alerts; hash cả3row runs (snapshot/configSHA/manifest) trước/sau khớp bằng chứng bước10, schema0002_policy giữ. Không enqueue/replay/refit/migrate hoặc ghi artifact app. Helper đầu thiếu root import src M2, sửa sys.path của helper và kiểm lại đạt; không sửa M2 để xử lý lỗi helper.
- Bằng chứng local ignored: outputs/step11-before-python.xml, step11-before-react.xml, step11-pure-python.xml, step11-targeted-python.xml, step11-after-python.xml, step11-protected.json, step11-before-source.json, step11-app-readonly.json, step11-smoke.json, step11-checks.json. Link/anchor/fence/bảng15bước/diff/staged scope kiểm trước commit; commit/push/remoteSHA/CI xác nhận riêng đúng SHA trước thông điệp cuối.
- Giới hạn/tiếp theo: chưa chạy full replay dữ liệu thật bằng mode mới (bước15), chưa có projected_below_rop/ngày xuống ngưỡng (bước12) hoặc control FE mode mới (bước13–14). warning_horizon chỉ tiếp tục lưu. Không đổi source/target/split/model/metric/acceptance; cảnh báo TestClient/httpx cũ còn, không thay lock. Tiếp theo bước12 khi được giao; không tự làm bước12–15, merge/force-push/deploy hoặc nâng R07/T14.

**Cổng GitHub đã kiểm cho mã bước11:** commit `588b8f6226c0857f7faef6cd5b00ffee1f29782a` push thường lên m3-implementation, remoteSHA khớp; [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40175388904) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40175388909) đều completed/success, đủ4job test/backend/m2-regression/frontend. Bước11 hoàn tất; bước12–15 chưa bắt đầu, R07/T14 chưa nghiệm thu. Commit tài liệu bằng chứng sau mốc này được kiểm SHA/CI riêng trước bàn giao cuối.


<a id="handoff-chg073"></a>
### Bàn giao CHG-073 — Mục tiêu cảnh báo 45%, chỉ Markdown

- Ngày25/10/2026 (Asia/Saigon), workspace Desktop/WorksSpace/Sigma, nhánh m3-implementation. T01/T10/T12/T14: người dùng giao sửa MD trước, chưa đụng code, rồi yêu cầu push GitHub. [Nguồn E113](review-log.md#chg073), [PLAN](planning/PLAN.md#chg073), [R07](requirements.md#r07-target-chg073).
- Ghi lời mentor do người dùng thuật lại “đạt 45% theo cấu hình” thành mục tiêu làm việc early rate≥45% với báo trước≥7ngày, còn cần làm rõ tính bắt buộc/phạm vi nghiệm thu. Tách N ngày xuống ROP khỏi lead≥7ngày và tỷ lệ45%; giữ mẫu số/sự kiện, số muộn/ca loại và precision/recall. Baseline34,391350% và trần riêng45,936519% giữ đúng nguồn lịch sử, chưa là run mới.
- Tệp sửa: AGENTS.md; docs/requirements.md; docs/planning/PLAN.md, TASK.md, PROJECTMAP.md; docs/review-log.md, development.md; M3/ACCEPTANCE.md, IMPLEMENTATION.md; M3/docs/01-functional-spec.md,06-testing-delivery.md. Ca kiểm45% trong test plan chỉ là dự kiến; không thêm hoặc sửa test code.
- Kiểm local đã chạy:11file UTF-8; rà530link,32link mới/anchor mới đạt;62bảng/fence và bảng15bước giữ đúng, bước12–15 vẫn chưa bắt đầu; phép tính986/2.867,1.317/2.867,ceil(45%×2.867)=1.291 và chênh305 khớp. git diff --check đạt, diff chỉ11Markdown.232hash ngoài MD (tệp tracked ngoài MD, CSV gốc và slide nguồn) nguyên. Có6tham chiếu lịch sử thiếu nguồn từ trước (4link tới cùng bản bàn giao M2 đã dọn, ảnh kickoff/PDF cũ), giữ lịch sử và không khôi phục. Bằng chứng kiểm chi tiết/baseline hash lưu ngoài repo tại workspace visualizations của chat. Không chạy lại pytest/FE/build/model/replay local cho sửa tài liệu; số test lịch sử không dùng như kết quả mới. Cổng GitHub kiểm riêng sau commit/push trước bàn giao cuối.
- Không đổi code/config/schema/dữ liệu hoặc run/snapshot; kết quả cũ vẫn là baseline, không bị ghi đè hoặc nhận thành kết quả cấu hình mới. R05/M05 và A08–A17 giữ trạng thái. Bước11 CHG-068 hoàn tất, bước12–15 chưa bắt đầu; R07/T14 chưa nghiệm thu. Tiếp theo làm rõ ý nghĩa/phạm vi45% trước chốt nghiệm thu; chỉ tiếp tục kỹ thuật khi người dùng giao, giữ cổng từng bước hiện có.

<a id="handoff-chg068-step12"></a>
### CHG-068 bước12 — 26/10/2026 (Asia/Saigon)

- Phạm vi người dùng giao: tiếp tục riêng bước12 và push GitHub từ8233a96597cb168afc1ce81c8198c6709134fbed, Desktop/Sigma, nhánh m3-implementation. Thay phạm vi chỉ Markdown tại checkpoint CHG-073; không tự triển khai bước13–15. R07/T14 vẫn chưa nghiệm thu, mục tiêu làm việc45% chưa được chứng minh bởi lượt này.
- Sản phẩm: alerts/service/model/DTO/router, inventory/simulation, reporting/filter và independent runs/verifier; migration0003_threshold và28ca synthetic mới. Projection strict<ROP trong N ngày dùng ROP decision origin/known receipts, không thêm Q mới; below_rop riêng projected, depletion/metric/lead ngày cạn giữ nguyên. [Công thức/đánh giá](../M3/docs/01-functional-spec.md#threshold-alerts-step12), [schema](../M3/docs/02-data-model.md#threshold-persistence-step12), [API/CSV](../M3/docs/03-backend-api.md#threshold-api-step12).
- Kiểm thực chạy: baseline214Python từ HEAD source snapshot trong tmp; sau `.venv-m3/Scripts/python.exe -B tmp/step12_check.py python -m pytest web/backend/tests tests M2/models/tests -q --tb=short --junitxml=outputs/step12-after.xml` đạt242/0failure/error/skip.9golden inventory và M2 parity1e-8 giữ;28ca mới có3worker kind, API/filter/CSV/manifest và tamper ngày/xóa tín hiệu/mẫu số. OpenAPI/DDL golden cũ không đổi; contract chỉ bỏ phần additive được giao rồi so toàn phần còn lại.
- FE nguyên mã: npm test lượt song song33/34 do timeout5000ms; chạy lại `npm test -- --maxWorkers=1` đạt34/34, TypeScript/Vite build đạt. pip check đạt; local launcher smoke API/worker/React trên sigma_m3_test đạt, dừng đúng tiến trình test.1024protectedhash nguyên. PostgreSQL18.6 local đã khởi động lại tại loopback55432; DB test riêng, app không có run active khi nâng schema.
- DB app: backup pg_dump local ignored trước0003; toàn bộ cột cũ13bảng giữ hash,3run và920policy/snapshot nguyên, metadata0diff. File bằng chứng ignored: outputs/step12-protected.json, step12-baseline.xml, step12-after.xml, step12-app-before.json, step12-app-migration.json, step12-smoke.json và step12-app-readonly.json. Backup SHA256 e769d010514e92e9e20d1e9651896687e1450b49757cb373e5a92c51acc0b6d9; không upload dữ liệu/backup/env/run. Projection cũ được kiểm lại trong transaction PostgreSQL readonly, không enqueue hoặc ghi lại artifact.
- Giới hạn: synthetic kiểm cơ chế, không có replay thật mới hoặc chỉnh mô hình/policy theo test cũ. Các số early rate CHG-073/E112 là lịch sử. Các run cũ không có threshold_warning_version vẫn kiểm theo hợp đồng cũ; chỉ run mới sinh tín hiệu/metric threshold. Giao diện/config form và cách đếm item trình bày vẫn chờ bước13–14. Các cảnh báo StarletteDeprecationWarning của dependency khóa giữ như baseline.
- Tiến độ đồng bộ TASK/PLAN/AGENTS/PROJECTMAP/requirements/README và đặc tả/kiểm M3; bước12 local đạt, cổng commit/push/SHA/CI được xác nhận riêng trước thông điệp cuối. Bước tiếp theo13 chỉ bắt đầu khi người dùng giao.

**Cổng GitHub bước12 đã kiểm:** commit `14b18415014ee2867fac436e6bd7530d74b12188` push thường m3-implementation, remoteSHA khớp; [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/40254759600) và [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/40254759610) completed/success, đủ4job test/backend/m2-regression/frontend. Người dùng sau đó giao chuyển bước13 khi bước12 không lỗi; cổng này đã đủ trước khi sửa code bước13. R07/T14 chưa nghiệm thu.

<a id="handoff-chg068-step13"></a>
### CHG-068 bước13 — 26/10/2026 (Asia/Saigon)

- Phạm vi: người dùng giao sau khi bước12 commit/push không lỗi thì tiếp tục13. Bước12 mã14b18415014ee2867fac436e6bd7530d74b12188 đã remoteSHA khớp và2CI completed/success trước sửa code13. Làm riêng form React; chưa bước14–15, R07/T14 chưa nghiệm thu, chưa chứng minh45%.
- Tệp: config/policy.ts, PolicyFields/PolicyForm/PolicyOverrideEditor, useConfiguration, Configuration và layout-configuration.test.tsx; không sửa BE/DB/HTTP/worker/metric. [Giao diện và quy tắc](../M3/docs/04-frontend-spec.md#policy-forms-step13). Policy có5tham số mới với defaults đúng backend; scenario override chỉ gửi trường khai báo/đang hoạt động, trống kế thừa,0giữ. Version/effective date/409/form values và frozen run giữ; bảng lịch sử phân biệt tham số áp dụng.
- Kiểm: npm test mặc định và npm test -- --maxWorkers=1 đều43/43 (9ca mới), TypeScript/Vite build đạt.242Python BE/M2 hiện tại đạt0failure/error/skip; baseline là242 đã chạy ở bước12. Native constraint chặn trước POST; payload5trường/version/conflict/history và partial override/0/inactive được kiểm. Backend/golden/API/schema/pip lock giữ1029protectedhash; dist và tsbuildinfo sinh lại được loại đúng khỏi danh sách nguồn phải giữ.
- Browser713×615 trên sigma_m3_test: policyv2 volatility/fixed/lookback90/factor0/N14 lưu qua API thật, reload đọc lại đúng, giữ tham sốv1 và ngày kết thúc; scenario chỉ gửi item/safety_mode/safety_factor0/N1, trường trống kế thừa. Escape/focus/scroll tới nút lưu đạt. Ảnh/evidence local ignored ở outputs/step13-browser/policy-saved.png và evidence.json; stack test/tab đã dừng/đóng. Không nhận đã kiểm1366/390px hoặc UI→run forecast thật trong lượt này.
- App DB chỉ đọc kiểm3run hash nguyên, revision0003_threshold; không migrate/ghi app/khởi tạo run thật, không upload raw/DB/env/ảnh fixture/run. Không replay/refit hoặc thay target/model/metric; giới hạn CHG-073 giữ. Kết quả cũ không bị vô hiệu hóa, policy/scenario mới chỉ dùng cho run mới.
- TASK/PLAN/AGENTS/PROJECTMAP/README, frontend-spec/testing và review-log đồng bộ; local đạt, commit/push/remoteSHA/CI được kiểm trước thông điệp cuối. Bước14 chỉ tiếp tục khi người dùng giao.
