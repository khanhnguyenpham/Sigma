# Phát triển, kiểm tra và bàn giao SIGMA

**Hiện hành CHG-027/E43–E49 — 05/10/2026:** sản phẩm mặc định dùng sigma_weekly_refactored_v12; đã hoàn tất bản so sánh ngày/tổng7 ngày và tổ chức mã sigma/ +29 entry points legacy/ +configs/experiments. 192 tests đạt; parity364.320 validation cache/7.590 fresh test/92 future/644 daily rows ở1e-8, cùng46 lựa chọn; raw/59 v11 files nguyên. Full policyV3 kiểm13 kịch bản/1.100.320 ledger/267.812 events; snapshotV6 kiểm920 items từ đúng policy; customerV5 kiểmD+7; AppTest6 trang và4 bộ lọc scenario đạt. Tuần9/10, mean16,19%, LG U+21,19%; R05 ngày0/10, early≥7 ngày33,80% cùng2867 events; chưa nghiệm thu toàn bài. CHG-027 thay thứ tự hoãn CHG-025; Word/slide không làm lại. Các cập nhật bên dưới E37–E41 là lịch sử.

**Cập nhật 05/10/2026 — CHG-024/025, E37–E39:** đã áp dụng **khách đặt D → giao D+7 ngày lịch UTC**, không trễ giao, gồm cuối tuần; không đổi lead time nhập kho. Người dùng mô tả snapshot order là giả định; đây là nguồn thuật lại, vẫn giữ dữ liệu/outputs private và raw nguyên. [Sản phẩm chung và lịch giao](customer-delivery.md) mở bằng `start_product.ps1` tại cổng 8503. Run tuần hiện hành `sigma_weekly_calibrated_v5`: test hồi cứu **9/10**, mean **15,97%**, LG U+ **21,36%**; chọn validation rồi khóa trước test. 920 khuyến nghị tồn từ phân bổ tuần đã đối soát, replay cùng 5.520 cửa sổ báo sớm **33,73%**; chưa chạy lại toàn bộ chính sách liên tục bằng tuần. 150 tests đạt, AppTest năm trang/không exception; job refresh/skip chạy thật, script đăng ký lịch nền được chuẩn bị nhưng chưa cài. R05 ngày **0/10**, R07/T14 vẫn mở. **Sau khi đủ điều kiện nghiệm thu mới làm bản so sánh chính thức ngày/tổng 7 ngày và tổ chức lại code**, đúng thứ tự người dùng yêu cầu; chưa làm lại Word/slide. Những cập nhật E36/v1 bên dưới là lịch sử.

**Kiểm CHG-023/E36 — tổng tuần:** [lệnh và protocol](weekly-forecast.md), `weekly_forecast.py`, `verify_weekly.py`, `weekly_app.py`; cấu hình riêng, không thêm phụ thuộc. 125 tests toàn suite đạt; đối soát 75.900 cặp từ raw độc lập, selection/metric/full coverage và nhãn fit≤cutoff, tổng phân bổ tuần; raw và 59 tệp sealed v11 nguyên. AppTest run thật0 exception/4 tab/6 bảng, kiểm Thailand/AIS/khối 8–14/lịch 7 ngày. Weekly test9/10≤20%, mean 17,19%; không nâng R05 ngày hoặc R07. Source/split/top10/seed giữ nguyên; test đã xem không độc lập. Kết quả giữ local, Git chỉ mã/cấu hình/tests/tài liệu. Nguồn kickoff đã xem tại E35, PDF/M01/M02 vẫn thiếu. T09/T10 tiếp tục accuracy và chính sách tồn từ forecast tuần; không chỉnh Word/slide.

**Cập nhật 05/10/2026:** Mã và quy trình chạy đã triển khai; lệnh thật tại README. Python 3.14.7, phiên bản khóa trong requirements.txt; config chứa seed 42 và dung sai số thực 1e-8. Kiểm tra release và báo cáo M2 ghi ở E13–E15/TASK. Phần ghi “chưa có/dự kiến” ngày 02/10 dưới đây là bối cảnh lịch sử và checklist thiết kế, không phải hiện trạng triển khai. Git root hiện nằm trong project; không sửa cấu hình Git toàn cục.

**Bản hướng dẫn:** 1.0 — 02/10/2026 (Asia/Saigon), dựa trên [PLAN 2.0](../PLAN.md), [requirements](requirements.md), [review-log](review-log.md). **Hiện trạng:** tài liệu và CSV; chưa có mã, config, phụ thuộc được khóa, tests hoặc run. Quy trình kỹ thuật dưới đây là **dự kiến, chưa triển khai**. Lượt tạo tài liệu không cài đặt, huấn luyện, mô phỏng hay nghiệm thu kỹ thuật.

## 1. Bắt đầu và trình tự task

Đọc [AGENTS](../AGENTS.md), [TASK](../TASK.md) và phần [PROJECTMAP](../PROJECTMAP.md) liên quan; kiểm tra tệp thực tế và phạm vi yêu cầu mới trước khi hành động. Với task đang làm, đọc mục Txx trong PLAN, Rxx liên quan và quyết định/giả định có ảnh hưởng. Không cần đọc lại mọi nguồn cho sửa lỗi chính tả hoặc nhãn đơn giản.

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
