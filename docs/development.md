# Phát triển, kiểm tra và bàn giao SIGMA

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
