# Điều phối công việc SIGMA

**Cập nhật:** 04/10/2026 (Asia/Saigon). **Căn cứ:** [PLAN 2.0](PLAN.md), [R01–R09](docs/requirements.md), [nhật ký 2.0](docs/review-log.md). T01 đang làm; T02–T14 chưa làm. Hiện người dùng chọn làm solo, được hỗ trợ từng phần và push tăng dần (CHG-006); phân công nhóm cũ giữ làm lịch sử, không còn áp dụng.

PLAN giữ toàn bộ mục tiêu, công việc, rủi ro, công sức và tiêu chí. Bảng dưới tóm tắt đúng mã/tên/phụ thuộc của PLAN; nhấp ID để đến nhiệm vụ chi tiết. “Chưa có” chỉ sản phẩm trong workspace hiện tại, không suy đoán nội dung các tệp cũ bị xóa. Giới hạn kiểm chứng tại [PROJECTMAP](PROJECTMAP.md#source-gaps).

## Bảng T01–T14

| ID / chi tiết | Tên | Trạng thái | Phụ thuộc | Rxx theo PLAN | Đầu ra chính | Tiêu chí hoàn thành tóm tắt | Bằng chứng hiện có / còn thiếu |
|---|---|---|---|---|---|---|---|
| [T01](PLAN.md#t01) | Chốt và cập nhật yêu cầu | Đang làm | Không | R01–R09 | PLAN, requirements, review-log; CHG-003 và tác động | Truy nguồn/tiêu chí/task; giữ lịch sử, giới hạn và nhãn đề xuất; tài liệu nhất quán | Có ba nguồn 2.0 và sáu tài liệu hỗ trợ; cần rà soát đóng T01. Ảnh/PDF thiếu; không nhận đã đọc lại |
| [T02](PLAN.md#t02) | Môi trường cục bộ và lệnh chạy | Chưa làm | T01 | R09 | Môi trường, phụ thuộc được khóa, CLI/notebook local, hướng dẫn | Môi trường sạch đọc nguồn local; phiên bản ghi lại; demo độc lập; dữ liệu thật không upload | Chưa có requirements, config, CLI, notebook hoặc bằng chứng môi trường sạch; Python khảo sát không thay nghiệm thu |
| [T03](PLAN.md#t03) | Audit và chuẩn hóa số bán | Chưa làm | T02 | R01, R09 | Audit, bảng lỗi/đối soát, dữ liệu processed | Hash nguyên; phân biệt dòng/đơn/quantity; success chưa active vẫn tính; duplicate có log, lỗi target chặn phần ảnh hưởng | Có khảo sát schema/hash trong data-contract; E03/E09 là lịch sử; thiếu pipeline audit và fixture |
| [T04](PLAN.md#t04) | Chuỗi số bán, lịch và EDA | Chưa làm | T03 | R02, R04 | daily_sales, calendar, bảng/hình EDA | Quantity bảo toàn theo A08; lưới 731 ngày/46 tuyến; hình có đơn vị/mẫu số/nguồn | Chưa có chuỗi ngày, lịch lễ hoặc EDA tái lập; không dùng bảng activation thay sản phẩm |
| [T05](PLAN.md#t05) | Top 10 và ba baseline | Chưa làm | T04 | R03–R05 | top_routes, predictions, metrics | Top 10 đúng sales train; baseline tính tay được; cùng cặp origin/horizon; đúng ngày 0/thiếu nhãn; không nhìn test xếp hạng | E09 có top 10 khảo sát lịch sử, cần sinh lại; E06 MA7 activation cần tính lại, không phải kết quả sales |
| [T06](PLAN.md#t06) | MVP xuyên suốt | Chưa làm | T05 | R03, R04, R06–R09 | Forecast → phân bổ → ledger → dashboard; run đầu tiên | Một lệnh tạo đầu ra nhất quán; màn hình khớp CSV; tồn có nhãn; thiếu config báo rõ | Chưa có run tích hợp, ledger hoặc dashboard |
| [T07](PLAN.md#t07) | SARIMA | Chưa làm | T05 | R04, R05 | Validation/predictions của 6 cấu hình top 10, log hội tụ | Cùng cặp origin/horizon; refit 7 ngày; ngoài mẫu; có lý do loại/chọn | Chưa có mô hình, log hội tụ hoặc metric SARIMA sales |
| [T08](PLAN.md#t08) | LightGBM có điều kiện | Chưa làm; có điều kiện | T07 | R04, R05 | Metric 4 cấu hình pooled/direct hoặc biên bản không kích hoạt | Chỉ kích hoạt nếu sau SARIMA còn top 10 chưa đạt validation ≤20%; feature tại origin, nhãn ≤ cutoff; chọn bằng validation | Chưa có validation T07 để xét điều kiện; không ghi “bỏ qua” hay hoàn thành trước khi có căn cứ |
| [T09](PLAN.md#t09) | Khóa và đánh giá M2 | Chưa làm | T06, T07, T08 hoặc biên bản không kích hoạt T08 | R04, R05, R09 | selected_models, test metrics, forecast, bảng đạt/chưa đạt | Đủ 46 tuyến; từng top 10 có MAPE/độ phủ/MAE/WAPE/bias truy về predictions; không chọn lại bằng test | Chưa có lựa chọn được khóa hoặc test sales; không suy ngưỡng 20% từ activation |
| [T10](PLAN.md#t10) | Đối tác, sổ tồn và cảnh báo | Chưa làm | T06 để phát triển; kết quả cuối nhận T09 | R06, R07 | Mapping/config, ledger, recommendations, alerts, simulation_metrics và độ nhạy | Phân bổ/cân bằng tồn; strict <; ngưỡng riêng; ETA/shortage đúng; event duy nhất; replay cảnh báo và chính sách riêng | A09–A16 là đề xuất trong PLAN; chưa có cấu hình/kịch bản hoặc kết quả mô phỏng; không chờ tồn thật |
| [T11](PLAN.md#t11) | Dashboard và cập nhật cục bộ | Chưa làm | T06, T09, T10 | R08, R09 | app.py, bộ lọc/bảng/hình, export và hướng dẫn | Manifest/phiên bản khớp; không trộn run/thật/mô phỏng; phân biệt 0/thiếu/chưa actual | Chưa có app hoặc gói demo; cutoff demo chỉ là thiết kế |
| [T12](PLAN.md#t12) | Kiểm thử, tái lập và bảo mật gói | Chưa làm | T09, T10, T11 | R01, R03–R09 | Tests, checks, run tái lập và kiểm tra gói | Hash nguyên; số nguyên khớp tuyệt đối, số thực theo dung sai ghi trước; input/config/seed tái lập; gói chia sẻ không riêng tư | Chưa có tests/pipeline hoặc môi trường demo kiểm chứng; kiểm tra Markdown không thay T12 |
| [T13](PLAN.md#t13) | Báo cáo, slide và bảo vệ | Chưa làm | T09–T12 | R01–R09 | report.md/PDF, slides, demo-script | Số/hình truy về run; rà RV01–RV16/CHG-003; đúng sales/giả định/giới hạn và bảo mật | Có sổ rà soát lịch sử; PDF nguồn chưa có trong workspace; chưa có báo cáo sửa/slide |
| [T14](PLAN.md#t14) | Nghiệm thu và đóng gói | Chưa làm | T12, T13 | R01–R09 | Ma trận nghiệm thu, biên bản, gói riêng tư hoặc giả, giới hạn | Người khác chạy theo README; demo tái hiện; mỗi yêu cầu có bằng chứng hoặc ghi chưa đạt; không tự công khai | Chưa có sản phẩm kỹ thuật, biên bản nghiệm thu hoặc gói bàn giao |

Các tham chiếu E03/E06/E09 và RVxx nằm trong [review-log](docs/review-log.md#evidence), thuộc bằng chứng lịch sử. Quan hệ Rxx ở bảng giữ nguyên PLAN; các chỗ chưa đối xứng với danh sách task trong requirements được ghi tại [sai khác nguồn](PROJECTMAP.md#source-gaps), không tự hợp nhất hoặc bỏ yêu cầu.

<a id="team-assignment"></a>
## Phân công nhóm 6 người — lịch sử, hết áp dụng theo CHG-006

**Phần dưới là lịch sử CHG-004/005.** Người dùng hiện làm solo theo mục tiếp theo; tên đầu mối/reviewer và việc nhỏ nhóm không còn là phân công hiện hành.

Người dùng cung cấp danh sách Nguyên, Khang, Du, Tuấn Anh, Hiếu, Cường. Sau đề xuất CHG-004, người dùng làm rõ muốn **cả nhóm cùng làm từng task, xong task hiện tại mới sang task tiếp theo** (CHG-005). Người phụ trách mỗi Txx ở bảng dưới là đầu mối chia việc nhỏ/tổng hợp; cả sáu người cùng đóng góp vào Txx đang mở. Chưa có thông tin thế mạnh/quỹ giờ hoặc xác nhận từng người nhận vai trò đầu mối. Mã task, phụ thuộc, nghiệm thu và trạng thái giữ nguyên; chi tiết reviewer ở từng Txx trong PLAN.

| Thành viên | Task làm đầu mối đề xuất | Đầu ra/phạm vi cần tổng hợp | Công sức task theo PLAN, không phải tải cá nhân |
|---|---|---|---|
| Nguyên | T01, T05, T09, T14 | Điều phối yêu cầu; top 10 train, baseline, evaluator/metric; khóa mô hình và test; nghiệm thu | 19–29 |
| Khang | T02, T06, T12 | Môi trường, cấu hình, CLI/notebook dùng chung mã; tích hợp MVP; tái lập và rà gói | 20–30 |
| Du | T03, T04 | Audit, xử lý dẫn xuất có log, daily sales, lịch và EDA | 14–22 |
| Tuấn Anh | T07, T08 nếu kích hoạt | SARIMA, log hội tụ; LightGBM theo điều kiện validation | 10–16; thêm 8–14 nếu T08 kích hoạt |
| Hiếu | T10 | Phân bổ SKU/product_type, ledger, ngưỡng từng đối tác, replay và độ nhạy | 16–24 |
| Cường | T11, T13 | Dashboard, bảng/hình, báo cáo, slide và kịch bản demo | 18–28 |

Công sức tổng giữ 97–149 người-giờ, hoặc 105–163 nếu kích hoạt T08; đây là ước lượng kế hoạch, chưa đo thời gian thực. Các số ở bảng là tổng công sức task do người đó làm đầu mối, nay được chia cho cả nhóm; **ước lượng tải cá nhân của CHG-004 cần phân bổ lại**, không coi còn hiệu lực. Nguyên tổng hợp tiến độ; mỗi PR vẫn phải có người khác review.

### Task đầu tiên cả nhóm cùng làm: T01

- **Nguyên:** đầu mối T01; tổng hợp kết quả rà soát, đối chiếu target sales/top 10/metric và các lựa chọn còn đề xuất; chưa tự xác nhận A08–A17.
- **Khang:** rà R09 và yêu cầu chạy local/tái lập; kiểm tra liên kết, bảng, trạng thái của tài liệu được sửa; chưa cài môi trường T02.
- **Du:** rà R01/R02 với data-contract; ghi rõ quy tắc quantity, duplicate, UTC và thiếu dữ liệu, không sửa CSV.
- **Tuấn Anh:** rà R03–R05 với PLAN: split, horizon, baseline, lựa chọn validation, điều kiện LightGBM và chống leakage; chưa huấn luyện.
- **Hiếu:** rà R06/R07 với PLAN: giả định tồn/ngưỡng, strict <, replay và độ nhạy; không gán tham số cho mentor.
- **Cường:** rà R08 và đầu ra dashboard/báo cáo; kiểm tra phân biệt actual/dự báo/giả định/mô phỏng và tệp hiện có/dự kiến; không tạo kết quả giả.

Mỗi người bàn giao ghi chú ngắn: tài liệu/mục đã rà, điểm khớp, sai khác còn mở và đề xuất sửa. Nguyên tổng hợp, Khang review; chỉ đóng T01 khi tiêu chí của PLAN có bằng chứng. Không mặc định tạo tài liệu phân công là hoàn thành T01.

### Cách chia việc nhỏ trong mỗi task tiếp theo

Đầu mối cùng nhóm chốt sáu phần nhỏ có đầu ra và người review, rồi mọi người làm trong **cùng Txx**. Các phần nhỏ là checklist của Txx, không tạo mã task mới. Có thể chia theo viết mã, viết ca tính tay, kiểm thử, đối soát, tích hợp và hướng dẫn; không bắt buộc sáu người cùng sửa một file.

Ví dụ **T03 sau khi T02 hoàn thành**, phân việc nhỏ đề xuất:

| Thành viên | Phần nhỏ trong T03 | Bàn giao/kiểm tra |
|---|---|---|
| Du | Đầu mối; audit schema và tổng hợp module dữ liệu | Audit đúng header/kiểu; giao diện dùng chung |
| Nguyên | Quy tắc sales/quantity và đối soát | Ca success chưa active vẫn tính; tổng dòng/đơn/quantity phân biệt |
| Khang | Nối stage audit vào CLI/config/manifest đã có từ T02 | Chạy audit local, hash nguồn không đổi, lỗi target báo rõ |
| Tuấn Anh | Ca kiểm thử thời gian/trạng thái/quantity | Fixture giả, UTC đúng, quantity không hợp lệ được phát hiện |
| Hiếu | Ca duplicate và đối soát sau xử lý | Trùng giống có log; trùng mâu thuẫn chặn phần ảnh hưởng; không ghi đè gốc |
| Cường | Hướng dẫn audit và kiểm tra bảng tổng hợp | Lệnh thật đã chạy; không lộ ID/log riêng tư; phần chưa đạt ghi rõ |

Đây là phân việc cho task tương lai, chưa có code/test hoặc kết quả T03. Đầu mối thống nhất người sửa từng file/section; phần đóng góp cùng file được ghép tuần tự để giảm conflict.

### Thứ tự tích hợp và mục tiêu điều phối

1. **Cả nhóm đi lần lượt T01 → T02 → T03 → T04 → T05 → T06 → T07.** Trong một task các phần nhỏ có thể làm đồng thời; tổng hợp, review và kiểm tra chung trước khi chuyển task.
2. **Xét T08 sau T07:** đủ điều kiện thì cả nhóm triển khai, không đủ thì ghi biên bản không kích hoạt. Sau đó T09 khóa/test khi đủ phụ thuộc.
3. **T10 → T11:** cả nhóm làm tồn/cảnh báo trên đầu ra T09 rồi dashboard; T10 vẫn giữ phụ thuộc gốc T06 để phát triển và T09 cho kết quả cuối.
4. **T12 → T13 → T14:** cả nhóm kiểm thử tích hợp/tái lập, chốt báo cáo theo run và diễn tập bàn giao. Kiểm thử từng module vẫn phải làm ngay trong task trước đó. Đây là thứ tự phối hợp người dùng chọn, không sửa đồ thị phụ thuộc kỹ thuật hoặc tiêu chí đạt metric.

Mốc M2 17/10/2026 và M3 07/11/2026 vẫn theo PLAN. Chưa có quỹ giờ, chưa cam kết đủ nguồn lực hoặc tự thêm deadline từng người. Ưu tiên có baseline và MVP chạy thật trước khi mở rộng mô hình; không bỏ tiêu chí nghiệm thu để kịp mốc.

### Quy ước bàn giao giữa thành viên

- Dùng đầu ra và đơn vị trong data-contract; Khang điều phối schema/API khi triển khai. Du bàn giao daily sales cho Nguyên; Nguyên bàn giao evaluator/baseline cho Tuấn Anh và Khang; forecast T09 cho Hiếu/Cường; Hiếu bàn giao ledger/alerts cho Cường. T06 trước T09 dùng baseline và kịch bản nhỏ có nhãn.
- Phạm vi file **dự kiến, chưa có code**: Du `src/data.py`; Nguyên `src/evaluation.py` và baseline; Tuấn Anh SARIMA/LightGBM trong `src/models.py`; Hiếu `src/inventory.py`; Cường `app.py`, `src/reporting.py`, báo cáo; Khang môi trường/config/CLI/notebook. Baseline và SARIMA cùng sửa models nên merge T05 trước T07; thống nhất người sửa config dùng chung.
- Trong cùng Txx, mỗi người có nhánh riêng theo phần nhỏ, ví dụ `codex/t03-du-schema`, `codex/t03-hieu-duplicates`; cùng lấy từ main đã cập nhật. PR nhỏ gắn cùng Issue T03 và ghi reviewer. Đầu mối ghép các PR theo phụ thuộc, cả nhóm pull main và kiểm tra chung trước chuyển task. Chưa có GitHub username nên chưa tạo/gán Issue hoặc mời tài khoản.
- PR ghi đầu ra, kiểm tra thực chạy/kết quả, giới hạn và bước tiếp theo theo mẫu development. Đồng bộ TASK/PLAN khi tiến độ thực sự đổi; không đóng task chỉ vì đã push.
- Dữ liệu thật/run thật giữ local; clone không tải CSV. Chỉ người được quyền sử dụng dữ liệu nhận bản local. Kiểm tra `.gitignore` trước chia sẻ; hướng dẫn Git chi tiết ở [file TXT](HUONG_DAN_LAM_VIEC_NHOM.txt).

<a id="solo-workflow"></a>
## Cách làm solo hiện hành — CHG-006 ngày 04/10/2026

Người dùng muốn tự làm, được hướng dẫn từng phần và push Git tăng dần. Người dùng là người thực hiện/tổng hợp T01–T14; trợ lý hỗ trợ code, giải thích, kiểm tra và thao tác Git trong phạm vi được giao. Review khi solo là tự rà diff và chạy kiểm tra; không gọi đó là review độc lập của thành viên khác. Giữ mã task, dữ liệu local, nghiệm thu và tổng công sức dự kiến; không coi solo tự làm giảm số người-giờ.

Một phần nhỏ gồm: mục tiêu và file cần sửa → thực hiện → kiểm tra phù hợp → xem diff và nội dung stage → commit → push code/tài liệu cho phép. Có thể push phần đang làm nhưng không đánh dấu cả Txx hoàn thành trước đủ tiêu chí. Ưu tiên một nhánh riêng cho một Txx, nhiều commit nhỏ trên nhánh; sau khi task đủ tiêu chí, review/merge qua PR rồi tạo nhánh task tiếp theo từ main đã cập nhật. Txx chưa hoàn thành có thể dùng Draft PR.

| Task hiện có | Các phần nhỏ triển khai/bàn giao theo thứ tự | Cửa kiểm tra trước chuyển task |
|---|---|---|
| T01 | Rà nguồn/target và A08–A17; đối chiếu Rxx–Txx–đầu ra; sửa sai khác trong phạm vi; kiểm tài liệu | Truy vết/giới hạn rõ; không tự xác nhận giả định hoặc nguồn thiếu |
| T02 | Môi trường và phụ thuộc khóa; config và manifest; CLI/notebook cùng mã; hướng dẫn/demo giả | Chạy trên môi trường sạch bằng lệnh thật, dữ liệu riêng tư local |
| T03 | Audit schema/UTC/quantity; trạng thái/duplicate; đầu ra dẫn xuất và log; stage audit/fixture | Hash gốc nguyên, đối soát, không loại sale vì activation |
| T04 | Daily sales và lịch; EDA; đối soát/hình có nguồn và đơn vị | Quantity bảo toàn, thiếu khác 0, sản phẩm tái lập |
| T05 | Top 10 train; ba baseline; rolling backtest; evaluator và metric | Ca tính tay/chống leakage, cùng cặp origin/horizon |
| T06 | Forecast baseline; phân bổ/tồn tối thiểu có nhãn; màn hình nhỏ; nối một lệnh | Một run xuyên suốt, khóa/đơn vị khớp, thiếu config báo rõ |
| T07 | SARIMA hữu hạn cấu hình; log hội tụ; validation so với baseline | Ngoài mẫu/cùng protocol; ghi thất bại và lý do chọn/loại |
| T08 | Xét điều kiện; LightGBM nếu kích hoạt hoặc biên bản không kích hoạt | Chọn bằng validation; không tự bỏ qua task thiếu căn cứ |
| T09 | Khóa lựa chọn; test cuối; forecast đủ tuyến; bảng đạt/chưa đạt | Không chọn lại bằng test, metric truy về predictions |
| T10 | Scenario/mapping; phân bổ và ledger; đặt/ETA/cảnh báo; replay/độ nhạy | Bảo toàn tồn/phân bổ, strict <, ngưỡng riêng, nhãn mô phỏng |
| T11 | Đọc một run; bộ lọc/hình; bảng metric/tồn/cảnh báo; export | Không trộn run, màn hình khớp đầu ra, thiếu actual khác 0 |
| T12 | Kiểm tra tích hợp; chạy lại môi trường sạch; kiểm gói chia sẻ | Tái lập/hash/dung sai đúng; không dữ liệu/ID/thông tin đăng nhập |
| T13 | Báo cáo theo run; slide; kịch bản demo và rà kết luận | Số/hình truy được, phân biệt quan sát/giả định/mô phỏng |
| T14 | Ma trận nghiệm thu; diễn tập hướng dẫn; gói và giới hạn | Mỗi yêu cầu có bằng chứng hoặc ghi chưa đạt |

Bảng này chia phần nhỏ bên trong T01–T14, không tạo task/mã mới và không phải bằng chứng đã triển khai. Đi T01–T07, xét T08, rồi T09–T14 theo phụ thuộc; trước tiên hoàn thiện phần yêu cầu T01, rồi mở môi trường T02. Chưa có code, test, notebook, dashboard hoặc run dự án.

Phần Git đầu tiên là tài liệu điều phối/hướng dẫn hiện hành trên nhánh riêng. Chỉ stage file được rà soát; trước push kiểm tra commit và dữ liệu đã tracked trong lịch sử. Dữ liệu/run thật vẫn không được đưa lên GitHub. Xem [hướng dẫn TXT](HUONG_DAN_LAM_VIEC_NHOM.txt), phần SOLO ở đầu file. Mốc M2/M3 giữ nguyên; quỹ giờ solo chưa biết, chưa cam kết đạt mốc hoặc ngưỡng metric.

## Bước tiếp theo và thứ tự ưu tiên

1. **T01 — rà soát phần tài liệu:** xác nhận truy vết và giới hạn nguồn đã được phản ánh, kiểm tra bộ Markdown. Đây là nền cho phụ thuộc T02; tạo tài liệu chưa tự đóng T01 hoặc xác nhận A08–A17.
2. **T02 — khi được giao kỹ thuật và T01 đủ bằng chứng:** tạo môi trường/lệnh local trước để T03–T05 có đường tái lập. Không cần chờ dữ liệu doanh nghiệp ngoài order.
3. **T03 → T04 → T05:** audit và chuẩn hóa sales trước khi tạo chuỗi, top 10 và baseline. E06 activation không thay kết quả cần tính lại.
4. Sau T05, phát triển T06 và T07 theo phụ thuộc; xét T08 rồi khóa T09. T10 có thể phát triển sau T06, kết quả cuối nhận T09. T11 → T12 → T13 → T14 theo bảng, không bỏ điều kiện T08 tại T09.

Mốc nguồn giữ nguyên: M1 19/09/2026 đã qua, M2 17/10/2026, M3 07/11/2026. Chưa có bằng chứng nghiệm thu các mốc; quỹ giờ/phân công chưa rõ, không coi ngày kế hoạch là cam kết nguồn lực.

## Đồng bộ và đóng nhiệm vụ

- Giữ hệ trạng thái của PLAN: chưa làm → đang làm → bị chặn / cần kiểm tra lại → hoàn thành; “bị thay thế” giữ lịch sử. Giữ nguyên T01–T14, không thêm bảng task cạnh tranh.
- Khi có thay đổi tiến độ trong phạm vi được giao, cập nhật cả TASK và mục Txx trong PLAN; ghi bằng chứng/quyết định vào review-log. Nếu đổi nghiệm thu, cập nhật requirements; nếu đổi dữ liệu/giao diện, cập nhật data-contract và PROJECTMAP liên quan.
- Một trạng thái hoàn thành cần đầu ra thật và lệnh/ca kiểm tra, kết quả, run/hash/phiên bản phù hợp. Kết quả hết hiệu lực chuyển cần kiểm tra lại. Chưa từng làm không chuyển thành “đã xong, cần sửa”.
- Phân biệt task hoàn thành phần phương pháp với tiêu chí độ chính xác hoặc cảnh báo đạt; không sửa tiêu chí để đóng task. Dùng [checklist và mẫu bàn giao](docs/development.md#done).
- Lượt tạo sáu tài liệu này giữ nguyên ba nguồn 2.0, không nâng trạng thái task. Kiểm tra tài liệu và giới hạn được ghi riêng tại [PROJECTMAP](PROJECTMAP.md#doc-checks).
