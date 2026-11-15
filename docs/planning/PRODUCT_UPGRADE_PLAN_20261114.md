# PLAN nâng cấp sản phẩm SIGMA theo góp ý nhóm

Ngày: **14/11/2026, Asia/Saigon**. Nền: `main` **`2d0d5f1052a3a3bea1711e2635822ca3cc6f9915`**.

## 1. Trạng thái và ranh giới

**Checkpoint cuối15/11 hiện hành:** người dùng giao tự chốt kỹ thuật và làm tại main. Có tư vấn sổ kho toàn mạng, QR phiếu giao, đổi/recovery mật khẩu, Redis Streams/durable queued intent, release identity và index forecast một lần. Main52a96e2 đã qua hai workflow:581backend (Redis thật),163React/build, M2 regression và Compose startup/backup–restore synthetic. [Ma trận hiện hành](../PRODUCT_STATUS.md), [bàn giao](../development.md#handoff-main-verified-20261115). Các ma trận khảo sát ban đầu phía dưới giữ để truy vết, không phải danh sách phần mới chưa viết. Chưa có public host24/7 hoặc bằng chứng mới trên nguồn nhóm để đóng R05/R07/T14.

**Cập nhật15/11 — vận hành theo chứng từ:** Theo yêu cầu dùng như phần mềm quản lý, đã thêm [sổ kho riêng](../WAREHOUSE_OPERATIONS.md), migration0011 và màn hình React. Đơn nhập/nhận từng phần/xuất/kiểm kê có ghi sổ/audit, version và retry. Lead time mặc định supplier áp cho đơn mới; chưa nối vào forecast/ROP L7/H14.552backend,156React/TypeScript/build qua trên synthetic; chưa host hoặc nhận toàn PLAN hoàn tất. [Bàn giao hiện hành](../development.md#handoff-operational-ledger).

**Bổ sung15/11 về FE:** P2 có modal snapshot chia mục, header/menu gọn, filter mobile có draft Apply/Cancel, bảng giữ cột/header và focus/keyboard.147React,14nhóm browser, TypeScript/build và đo trước–sau4viewport qua. [Bàn giao UX](../development.md#handoff-compact-management-ux). Vẫn chưa có UAT đầy đủ hoặc hoàn tất toàn PLAN; số541backend bên dưới thuộc lượt triển khai trước.

Người dùng đã gửi góp ý ngày14/11 và giao triển khai theo PLAN. **Cập nhật15/11: đã triển khai một phần P1/P2**, gồm auth admin/supplier chỉ đọc, nền loading/table/filter và snapshot. [Bàn giao](../development.md#handoff-product-upgrade-p2). Các dòng hiện trạng trong ma trận bên dưới mô tả nền main lúc khảo sát, không phải danh sách chức năng mới đã hoàn thành.

Các yêu cầu mới về authentication, QR nhập kho, Redis và ETA mở rộng phạm vi demo cũ. Những mô tả cũ như không cần đăng nhập, chỉ dùng PostgreSQL queue hoặc ETA luôn bằng ngày đặt +7 **không còn là ràng buộc thiết kế cho phần mới được yêu cầu**. Snapshot/run cũ vẫn cần đọc được theo quy tắc đã lưu. Không chỉnh lại dữ liệu lịch sử để khớp thiết kế mới.

Lượt lập PLAN ban đầu không chạy ứng dụng. Lượt triển khai tiếp đã cài dependency và migrate/chạy kiểm trên PostgreSQL18 riêng với dữ liệu synthetic. Chưa migrate demo cũ, chạy dữ liệu nguồn, commit/push hoặc deploy bản nâng cấp. Những chỗ chưa rõ vẫn là quyết định chờ; không coi đề xuất kỹ thuật là đã được người dùng chốt.

## 2. Ma trận đủ các góp ý

Hai ý “chỉnh worker (thêm Redis)” và “thêm Redis cho queue” được gộp vào FB-13, không triển khai hai queue chồng nhau.

| ID | Góp ý | Hiện trạng đã đọc từ main | Công việc / điều kiện nghiệm thu |
| --- | --- | --- | --- |
| FB-01 | Làm lại UI chuẩn chỉnh | React đã có layout và các màn hình nghiệp vụ | Chuẩn hóa bố cục, màu/font, điều hướng, form, bảng và thông báo theo workflow quản lý; thiết kế một luồng mẫu trước khi áp dụng toàn app. |
| FB-02 | Nhập SIM vật lý bằng QR | Purchasing hiện là read model của lô mô phỏng; chưa thấy luồng QR nhập kho trong router/model đã khảo sát | Thiết kế phiếu nhập và định danh QR; quét, kiểm trùng, xem trước, xác nhận, ghi sổ một lần; có nhập mã thủ công dự phòng. Chờ mẫu QR/phạm vi ở D01. |
| FB-03 | Host | Launcher hiện phụ thuộc máy cá nhân, DB/disk/prepared riêng; kế hoạch hosting cũ không chứng minh đã deploy bản main này | Triển khai FE/API/worker/PostgreSQL/Redis cùng release; bền dữ liệu qua restart, HTTPS, URL ổn định. Chốt tài khoản, hạ tầng và ngân sách trước provision. |
| FB-04 | Authentication nhà cung cấp và admin | Chưa có module users/login/authz ở source đã khảo sát; app demo trước cho dùng chung | Đăng nhập, đăng xuất, hết hạn phiên; admin toàn hệ thống, supplier theo phạm vi của mình. Kiểm quyền tại API, query, export, snapshot và worker; không chỉ ẩn menu. |
| FB-05 | Chỉnh thời gian hàng về | `eta()` cộng7; ReceiptInput kiểm đúng7; Replenishment có CHECK `eta=ordered_on+7`; UI/verifier cũng hiểu L7 | Migration, API, UI, snapshot, mô phỏng, cảnh báo và verifier hỗ trợ ETA mới đồng bộ. Đề xuất chỉnh ETA từng lô; ảnh hưởng công thức theo lead time phải chốt ở D05. |
| FB-06 | Skeleton và loading | `State.tsx` đã có khối skeleton chữ; useResource có hủy request | Skeleton theo hình dạng bảng/thẻ/form; phân biệt initial load, lọc lại, submit, job chạy nền; không chớp “không có” khi đang tải. |
| FB-07 | Xem snapshot cấu hình trên FE | Scenarios đã có “Thiết lập đã chốt”; product có current/frozen | Hoàn thiện trình xem chỉ đọc: mốc, nguồn, version, tham số, kho, ETA, lịch ngừng và tác giả/phạm vi; so sánh current/frozen dễ hiểu, che secret và lọc quyền supplier. |
| FB-08 | Bỏ hash trong BE | Có hash code, request, source, config, selection, artifact; gắn DB, readiness, worker và verifier | Phân loại và thay cơ chế theo D03; không xóa đồng loạt import/cột. Giữ idempotency, snapshot/version và khả năng đọc run cũ. Password hashing của auth mới là cơ chế khác. |
| FB-09 | Tối ưu DB | Có constraint, JSONB snapshot, index theo run/ngày; reporting đọc rồi xử lý nhiều phần trong Python | Đo query, EXPLAIN trên DB thử; đẩy lọc/aggregate/paging phù hợp xuống SQL, batch insert/read, index theo workload. Migrate có kiểm dữ liệu, không bỏ constraint toàn vẹn để nhanh hơn. |
| FB-10 | Tối ưu chạy kịch bản | Kịch bản dùng forecast cha đã lưu; worker vẫn audit nguồn và thực hiện nhiều bước đối chiếu | Đo thời gian từng phase, tái dùng đầu vào bất biến, tránh pivot/đọc/phân bổ lặp; giới hạn concurrency theo bộ nhớ. Chỉ nhận nhanh hơn sau so cùng input và đối chiếu đầu ra. |
| FB-11 | Table kéo riêng, không kéo cả trang | Table đã có `.table-scroll`/overflow-x; có bảng min-width lớn | Sửa containment toàn chuỗi flex/grid, cuộn ngang và dọc trong khung, header cố định khi cần; điều khiển bàn phím/touch, không mất nút thao tác. |
| FB-12 | Chỉnh thanh query ở tồn kho và trong kho | ContextFilters và bộ lọc trong Inventory hiện tách; URL giữ context | Một quy ước bộ lọc rõ ràng ở danh sách kho và chi tiết; áp dụng/xóa, phạm vi đang xem, đổi run reset hợp lý, Back/reload giữ đúng; CSV cùng query. |
| FB-13 | Worker + Redis queue | PostgreSQL queue, SKIP LOCKED, advisory lock, heartbeat, supervised process; chưa có dependency Redis | Redis làm queue vận chuyển, PostgreSQL giữ trạng thái/kết quả; outbox, ack/reclaim, retry, chống hiệu ứng trùng và giới hạn tài nguyên. Không chạy hai cơ chế cùng claim một run. |
| FB-14 | Tổng90/phân bổ xuống thứ chỉ tính một lần ở ngày chốt | allocate lấy 90 ngày lịch sử tính weekday weights, 30/90 ngày tính item share; đầu vào **hai tổng tuần**, chưa phải tổng forecast90 ngày | Xác nhận nghĩa 90 ngày ở D02; nếu là trọng số lịch sử, tính/lưu một lần theo origin và tái sử dụng. Không tự đổi horizon, mô hình hoặc reuse trọng số tương lai. |
| FB-15 | Table thiếu dữ liệu ghi “không có” | State có empty chung; Table chưa tự dựng dòng rỗng; format null hiện “—” | Bảng rỗng có dòng đầy đủ colSpan “Không có dữ liệu”; bộ lọc rỗng ghi “Không có kết quả phù hợp”; ô null/undefined ghi “Không có”. Giữ nguyên số0/false hợp lệ. |

## 3. Các quyết định ở mốc lập PLAN

**Cập nhật theo ủy quyền15/11:** D01 chọn QR phiếu giao/lô; D02 giữ lịch sử90ngày theo origin, không đổi horizon; D03 dùng immutable release reference trong image; D04 supplier chỉ đọc; D05 lead time1–365 cho đơn mới, tư vấn chặn khi forecast thiếu; D06 tách ledger vận hành và tư vấn read-only. Đây là lựa chọn triển khai, không phải xác nhận mentor. D07 đã đóng gói local; public host chưa có cấu hình. Bảng câu hỏi sau đây ghi phương án tại lúc lập PLAN, không yêu cầu hỏi lại người dùng các lựa chọn kỹ thuật đã được ủy quyền.

| ID | Câu hỏi còn mở | Đề xuất để xem xét | Phần bị phụ thuộc |
| --- | --- | --- | --- |
| D01 | QR nhận diện một SIM hay cả lô; đã có mẫu nội dung chưa? | Một QR cho một SIM vật lý, thuộc phiếu nhập; parser có version và danh sách trường cho phép. Nếu QR theo lô, thiết kế số lượng và unique receipt khác. Không đoán QR có ICCID hay mã kích hoạt. | Parser, schema SIM/phiếu nhập và nghiệm thu FB-02. |
| D02 | 90 ngày là lịch sử tính tỷ trọng hay forecast90 ngày tới; “một lần” theo ngày chốt của forecast hay cố định cả replay? | Theo code hiện tại: lịch sử90 ngày, trọng số theo thứ chốt ở từng origin; không tính lại khi người dùng xem ngày kết quả. Origin mới hợp lệ có thể cần basis mới. | Cache/allocation, profile và phạm vi ML. |
| D03 | Bỏ hash là bỏ tính/so fingerprint runtime hay chỉ bỏ hiển thị; có giữ audit/checksum offline không? | Thay runtime fingerprint bằng release/schema/engine/input version và quan hệ ID rõ ràng; bỏ rehash tệp ở request/job thường. Giữ trình đọc trường hash lịch sử, idempotency theo request chuẩn hóa, không trả hash không cần thiết ra FE. Chờ xác nhận phạm vi. | Core/run/worker/launcher/verifier và migration cột. |
| D04 | Supplier được xem/chỉnh những gì; có tài khoản nhiều supplier không? | Admin tạo/khóa tài khoản. Một supplier account thuộc một supplier; chỉ xem sản phẩm/lô của mình, đề xuất/cập nhật giao hàng của mình. Admin nhận hàng và quản lý toàn bộ. Không public signup trong bản đầu. | Ownership query, API quyền, màn hình và nhập QR. |
| D05 | Người dùng chọn **đổi thời gian nhập mặc định theo nhà cung cấp** ngày15/11. Còn chờ phạm vi tối đa dưới14 hay từ14ngày trở lên. | Không triển khai theo đề xuất ETA override từng lô ban đầu. Mặc định7 nếu chưa cấu hình; version theo supplier/mốc hiệu lực, chốt vào run mới. Ngưỡng nhập và ETA dùng cùng lead time; không âm thầm giữ công thức7ngày khi lead time khác7. Lead time vượt dự báo hiện có cần mở rộng forecast/horizon, không tự nối hoặc nhân dự báo. | Migrations supplier/ETA, profile ROP/horizon, snapshot, mô phỏng/cảnh báo/verifier và FE quản lý supplier. |
| D06 | QR nhập kho là tồn vận hành hay chỉ thêm lô giả định trong kịch bản? | Tách chứng từ/ledger nhập vận hành khỏi kết quả mô phỏng. Phiếu nhập không viết trực tiếp vào inventory_daily của run cũ. Kế hoạch mới dùng snapshot đầu kỳ nếu được chọn. | Transaction nhận kho, số dư và nguồn tồn của run mới. |
| D07 | Host ở đâu, tài khoản nào, ngân sách bao nhiêu? | Đóng gói Docker Compose cho local/staging trước; chọn nơi có persistent DB/disk, Redis và worker dài hạn. Dùng URL trung tính/HTTPS. Không chọn gói trả phí hoặc public dữ liệu khi chưa có cấu hình cụ thể. | Provision và public production/staging. |

Đã hỏi D01–D03, còn chờ trả lời; bổ sung câu hỏi D05/D06 trong lượt triển khai. D04 hiện chỉ triển khai quyền tối thiểu: một tài khoản/một supplier, chỉ đọc sản phẩm/lô của mình; không cấp quyền sửa ETA hoặc nhận hàng. Quyền ghi supplier, nghiệp vụ QR/ETA và hạ tầng D07 còn chờ chốt. Khảo sát, chuẩn UI và baseline không phải chờ các quyết định đó.

## 4. Kiến trúc đích đề xuất

```text
React / TypeScript
  -> FastAPI: authentication + authorization + validation
       -> PostgreSQL: users, scope, runs, snapshots, nhập kho, audit, outbox
       -> Dispatcher đọc outbox -> Redis Streams
                                    -> Worker -> PostgreSQL + artifact storage

Các mặt đọc: sản phẩm, tồn, lô, cảnh báo, snapshot, CSV đều qua kiểm quyền API.
Redis cache có thể mất; run/snapshot/phiếu nhập đã xác nhận không được chỉ nằm trong cache.
```

### 4.1 Authentication và scope dữ liệu

- Tạo `users`, role admin/supplier, liên kết supplier và session; tên bảng chi tiết chốt trong migration design. Tài khoản legacy/run không có chủ sở hữu mặc định chỉ admin đọc, không cấp đại trà cho supplier.
- Đề xuất phiên đăng nhập server-side với cookie HttpOnly/Secure và CSRF cho mutation; khi chốt auth adapter phải kiểm CORS, session rotation/logout/expiry và chính sách mật khẩu. Dùng thư viện chuẩn để lưu password hash, không lưu mật khẩu thuần. Việc bỏ hash artifact không bao gồm bỏ bảo vệ mật khẩu.
- Scope supplier phải áp dụng trước paging/aggregate/export. Supplier A đổi item_id/run_id trên URL hoặc request cũng không được đọc/sửa B. Run global có snapshot nhiều supplier không được trả nguyên JSON cho tài khoản supplier.
- Các thao tác chạy source/forecast toàn cục, quản trị tài khoản, duyệt/nhận kho và config hệ thống mặc định thuộc admin. Quyền supplier sửa ETA/tạo phiếu cần D04. UI route guard chỉ bổ trợ, không thay kiểm quyền server.

### 4.2 QR và nghiệp vụ nhận kho

- Luồng: tạo phiếu nháp → chọn supplier/kho/SKU/type → quét hoặc nhập mã → kiểm payload/định danh/trùng → xem trước → xác nhận → ghi nhận kho và audit trong cùng transaction.
- Quét chỉ thêm dòng nháp, **chưa cộng tồn**. Xác nhận hai lần, gửi lại request hoặc hai người quét cùng mã không được tạo hai lần tăng tồn; cần unique constraint đúng định danh và idempotency.
- Mỗi QR chỉ xử lý như dữ liệu có schema, không tự mở URL, chạy mã hay lấy nội dung ngoài. Không đưa mã kích hoạt/định danh SIM vào log hoặc ảnh công khai.
- Thiết kế đề xuất `goods_receipts`, `goods_receipt_lines`, `sim_units` và ledger/audit vận hành; số bảng cuối phụ thuộc D01/D06. Không đổi PK item hoặc suy “một lượt quét = một đơn bán”.
- Phiếu đã nhận không sửa số lượng trực tiếp; xử lý điều chỉnh bằng chứng từ bù và quyền phù hợp. Phần xuất/bán từng SIM không tự nằm trong scope inbound nếu nhóm chưa yêu cầu.
- Chấp nhận cả quét camera có quyền người dùng và máy quét dạng bàn phím; nhập mã thủ công khi camera không dùng được. Chọn thư viện sau khi có mẫu QR và kiểm thiết bị thực tế.

### 4.3 ETA linh hoạt

**Quyết định15/11:** người dùng chọn lead time mặc định theo supplier, thay cho đề xuất sửa ETA từng lô. Cần màn hình admin quản lý supplier với version/ngày hiệu lực; supplier chỉ xem cho tới khi chốt quyền ghi. Run mới chốt lead time đã biết tại mốc; lô đã đặt và run hoàn tất không đổi ETA khi sửa default. Chưa viết code phần này khi chưa rõ miền ngày và forecast coverage tương ứng.

Đã hỏi liệu cần từ14ngày trở lên vì forecast vận hành hiện là H14, còn target M2 tổng30 không tự trở thành forecast theo ngày dài hơn. ROP theo nhu cầu trong lead time, target theo lead time + chu kỳ xét nhập; kiểm đủ vector dự báo trước khi chạy, không padding. Hợp đồng cảnh báo7ngày và giao đơn đến khách7ngày là các quy tắc khác, không tự đổi cùng thời gian nhập supplier.

- Thay constraint cứng bằng hợp đồng của profile mới, có ETA dự kiến/nhận thực tế/metadata chỉnh sửa nếu cần. Ngày nhận không trước ngày đặt; quyền sửa, lý do và phiên bản chống ghi đè phải rõ. Lô đã nhận không đổi lịch sử bằng edit thông thường.
- Sửa đồng bộ `ReceiptInput`, `eta()`, model/DDL, freeze, nhận đầu ngày, pending, projection, ETA cap khi ngừng dịch vụ, API/CSV/UI và verifier. Không chỉ bỏ CHECK trong DB.
- Lịch ETA mới chỉ có tác dụng theo thông tin đã biết tại origin hoặc run mới. Run hoàn tất không tự chạy lại hoặc thay số. ETA nằm ngoài H14 phải hiển thị ngoài cửa sổ, không giả đã về hoặc đã đủ dự báo.
- Profile variable-ETA phải phân biệt với profile L7 lịch sử; quyết định công thức lead-time/horizon ở D05 được ghi trong snapshot và tests.

### 4.4 Redis và worker

- Lựa chọn đề xuất: Redis Streams consumer group, một cơ chế enqueue/consume rõ ràng; chưa quyết định thêm Celery/RQ. Job payload chứa run ID/attempt/version, không chứa raw/secret.
- Trong một transaction, PostgreSQL lưu run queued và outbox. Dispatcher publish có retry; nếu publish lặp thì worker vẫn chỉ thực hiện một hiệu ứng cho cùng run/attempt. Không cố đồng bộ DB và Redis bằng hai lệnh ghi không có recovery.
- Delivery có thể lặp. Worker cần claim bằng lease/attempt token trong DB, heartbeat, điều kiện commit đúng owner; ack sau khi kết quả DB được chốt. Worker chết sau commit trước ack phải đọc lại complete rồi ack, không chạy mô phỏng/nhập kho lần hai.
- Reclaim chỉ với lease hết hạn thật; heartbeat/timeout phải bảo vệ job mô hình dài. Worker cũ không được commit đè sau khi ownership chuyển. Retry có giới hạn/backoff và trạng thái lỗi rõ ràng.
- Giữ quota/memory limit hiện có; bắt đầu concurrency1, tăng sau benchmark. Không giữ advisory lock toàn hệ thống khiến nhiều worker chỉ chạy một job nếu mục tiêu sau đó là song song.
- Khi Redis lỗi, outbox/run queued vẫn còn trong DB, UI hiển thị đang chờ hoặc lỗi dịch vụ; không báo complete hoặc âm thầm dùng PostgreSQL worker cũ chạy song song.

### 4.5 Tối ưu allocation và hash

- Hiện forecast service gọi allocation theo từng `(origin, route)`. `allocate()` tính một bộ weekday weights90 và item shares30/90, rồi dùng cho 14 ngày; **không có bằng chứng hàm này đang tính lại weights cho từng target day trong cùng lần gọi**. Cần tìm phần lặp giữa run/verify/đọc dữ liệu trước khi sửa.
- Nếu D02 xác nhận lịch sử90 ngày: tách `build_allocation_basis` khỏi `apply_weekly_totals`, lưu/reuse basis theo source version, origin, route, catalog eligibility và allocation version. Nhiều run tồn với cùng forecast cha đọc `item_forecasts` đã lưu; không pivot/audit/allocate lại không cần thiết.
- “Chỉ một lần” là một basis hợp lệ cho cùng khóa; đổi input/version/origin phải tính lại. Nhiều scenario khác safety không làm thay đổi basis. Backtest origin riêng không được dùng một basis tính từ cuối kỳ.
- Nếu D02 là forecast tổng90 ngày, lập nhánh thiết kế model/metric/horizon riêng; không biến hai tổng tuần hiện tại thành90 bằng nhân hệ số hoặc nối lại số để đạt yêu cầu.
- Nếu D03 bỏ fingerprint runtime: thay từng nhóm kiểm bằng release/input/config version, immutable snapshot và so body chuẩn hóa cho idempotency. Giữ đọc hash nullable legacy; lược bỏ rehash file khỏi hot path sau benchmark. Bỏ hash không được bỏ phép kiểm tổng quantity, receipt một lần, ledger hoặc policy đúng item.

### 4.6 Database và giao diện

- DB: đo thời gian/count query, EXPLAIN các đường inventory/workspace/alerts/purchasing/snapshot trước đổi index. Index theo khóa scope thực tế (supplier/run/ngày/item/trạng thái), FK/unique chống trùng và batch IO được giữ. Chưa tự partition hoặc đổi database engine.
- FE: chuẩn các trạng thái loading/error/empty/partial/ready; dữ liệu cũ không được hiện dưới context mới. Skeleton đúng layout và có aria-busy, giảm motion theo thiết lập thiết bị; tránh spinner kéo dài không giải thích.
- Table: vùng cuộn riêng với chiều cao phù hợp, header cố định và nút thao tác dễ thấy; wrapper/flex child có min-width phù hợp. Kiểm document không tràn ngang khi bảng tràn. Hỗ trợ thanh cuộn, touch và bàn phím; kéo chuột chỉ bổ sung, không cản chọn chữ/bấm nút.
- Empty: phân biệt bảng không có dữ liệu, lọc không khớp, chưa chọn kế hoạch, đang tải và không có quyền. Null/undefined hiển thị “Không có”; số0 và false không biến thành thiếu thông tin. Date/quantity thiếu không được thay bằng giá trị giả.
- Snapshot: trình xem read-only có summary và chi tiết, phân biệt “cấu hình hiện tại”/“cấu hình lượt này”; lọc dữ liệu nhạy cảm theo role, không serialize toàn bộ config/private path ra FE. Có phiên bản/nguồn/mốc dù bỏ hash.

## 5. Thứ tự làm và điều kiện xong

| Bước | Hạng mục | Phụ thuộc | Kết quả có thể review | Cổng kiểm |
| --- | --- | --- | --- | --- |
| P0 | Chốt D01–D07, baseline/test env, đo performance và rà schema/API | Source main, góp ý gốc | Ma trận FB, quyền, dữ liệu QR/ETA, baseline thời gian/kết quả | Không có quyết định phụ thuộc bị mặc định thành đã chốt. |
| P1 | Thiết kế data/API version, migration, ownership, snapshot contracts, auth | D04 và phần rõ của D01/D05/D06 | Schema proposal, permission matrix, API contract, migration trên DB copy | Legacy chạy đọc được; test supplier A/B/admin và dữ liệu cũ. |
| P2 | Auth end-to-end; UI shell, skeleton/loading/empty, table/filter, snapshot view | P1; không chờ mọi backend tối ưu | Luồng admin/supplier đăng nhập và một vertical slice sản phẩm→tồn→snapshot | API từ chối truy cập trái quyền; desktop/mobile/keyboard; loading/empty0/null đúng. |
| P3 | ETA linh hoạt và QR nhập kho | P1/P2, D01/D05/D06 đã chốt | Phiếu QR nháp/xác nhận, pending/ETA mới, audit và kế hoạch mới | Scan trùng/concurrency không tăng tồn hai lần; ETA đổi tác động đúng run mới. |
| P4 | Tách version/fingerprint theo D03 và tối ưu allocation/IO theo D02 | Baseline, quyết định và profile rõ | Diff hot path, cache/basis/version, benchmark trước–sau | Quantity/metric parity trong cùng hợp đồng; tách riêng thay đổi nghiệp vụ có chủ đích. |
| P5 | Redis outbox/dispatcher/worker; tối ưu DB theo số đo | P1, P4; release/version contract ổn định | Queue chạy thật, recovery, query/index và số đo tài nguyên | Không mất job khi Redis/worker lỗi, không hiệu ứng trùng, owner cũ không commit đè. |
| P6 | E2E và rehearsal deploy | P2–P5 | Bộ ca mục6, môi trường sạch, snapshot/CSV/UI, cấu hình triển khai | Auth/ETA/QR/queue và run cũ cùng đạt; dữ liệu/secret được giữ đúng phạm vi. |
| P7 | Host và bàn giao | D07, gói concrete đã kiểm | URL HTTPS, tài khoản admin/supplier, health/queue/backup và rollback | Không phụ thuộc máy cá nhân; restart không mất dữ liệu; remote SHA/CI khi có push. |

P2 được làm theo từng luồng mẫu, không dàn trải thay CSS toàn app rồi mới kiểm. P4 và P5 chỉ nhận hoàn tất sau benchmark; Redis không tự làm mô hình dự báo chạy nhanh hơn. Trước P7 cần rà gói và quyền publish theo tài khoản/hạ tầng được chọn, không tự mua dịch vụ.

## 6. Ca nghiệm thu bổ sung theo góp ý

Các ca đều **chưa chạy trong lượt lập PLAN**. Bổ sung vào [UAT nền](MAIN_REVIEW_PLAN_20261114.md#7-bộ-ca-bắt-buộc-cho-lần-triển-khai-tiếp), không nhận test cũ đã bao phủ nghiệp vụ mới.

| Ca | Điều phải chứng minh |
| --- | --- |
| N01 — quyền | Chưa login không đọc/sửa nghiệp vụ; supplier A không đọc/sửa/export/snapshot/run của B dù đoán ID; admin được làm theo permission matrix; logout/expiry có hiệu lực. |
| N02 — QR | Mã hợp lệ thêm nháp; mã sai/supplier sai/type eSIM bị từ chối; quét lại/thao tác hai tab/hai thiết bị không ghi tồn hai lần; xác nhận rollback toàn bộ khi lỗi. |
| N03 — chứng từ | Phiếu nháp không cộng tồn; phiếu đã nhận có actor/thời điểm; không sửa lịch sử bằng edit trực tiếp; run cũ không đổi sau nhận lô mới. |
| N04 — ETA | ETA mặc định, đổi ngày, trước ngày đặt, ngoài H14, trùng thời điểm ngừng cung cấp, lô đã nhận và hai người cập nhật; snapshot cũ L7 đọc đúng. |
| N05 — Redis | Mất Redis trước publish, sau publish/trước ack, worker chết trước/sau DB commit, duplicate message, stale owner, retry/quota, job dài có heartbeat. Mỗi run/receipt có một hiệu ứng đã chốt. |
| N06 — allocation | Cùng source/origin/route/version chỉ build basis một lần dù nhiều scenario; đổi version/origin tạo basis mới; đổi dữ liệu tương lai không đổi basis quá khứ; tổng item/ngày bảo toàn tổng tuần. |
| N07 — hash/version | Theo D03: chạy bản mới không cần fingerprint hot path; run cũ có hash vẫn đọc được; cùng request key/body khác trả409 bằng cơ chế thay thế; không vô tình bỏ password hashing hoặc ledger verification. |
| N08 — FE | Skeleton theo vùng; loading không hiện empty; 0 không hiện “Không có”; bảng rỗng có dòng giải thích; lỗi có retry; tab/keyboard/touch và desktop/màn hình hẹp hoạt động. |
| N09 — query/table | Danh sách kho và chi tiết không kéo ngang cả trang; bảng cuộn được riêng; filter apply/clear/Back/reload đúng và CSV cùng scope; supplier scope trước paging/total. |
| N10 — snapshot | Chỉ đọc, có version/mốc; current khác frozen không nhầm; tài khoản supplier không thấy config supplier khác/secret/private path; đổi live không đổi run đã chốt. |
| N11 — hiệu năng | Cùng input, scope, số item/origin, môi trường và concurrency; đo wall time từng phase, RAM đỉnh, số/query SQL, API p50/p95 và thời gian bảng sẵn sàng. Công bố số trước–sau và chênh lệch đầu ra, không hứa phần trăm khi chưa đo. |
| N12 — host | Clean startup/migrate/bootstrap account; FE/API/worker cùng version; Redis/DB không public tùy ý; HTTPS; worker outage/recovery; backup restore và rollback giữ receipt/run. |

## 7. Mốc rà soát schema và tệp

| Nhóm | Điểm sửa/đọc sâu dự kiến |
| --- | --- |
| Auth/scope mới | Module mới `modules/auth`, model registry và migration; dependency/API guard; FE auth/session context và route/menu theo role. Tên mới là dự kiến, chưa là file đã có. |
| QR mới | Module chứng từ/nhận kho đề xuất, catalog item/type/supplier, inventory ledger vận hành, màn hình nhận hàng/scanner; không nhồi vào read-only purchasing router cũ. |
| ETA | `modules/configuration/schemas.py`, `modules/purchasing/models.py`, `modules/inventory/service.py`, simulation, trade/alert projection, snapshot/verifier và các form receipt. |
| Queue/version | `core/hashes.py`, `core/run_context.py`, `core/demo.py`, `runs/models.py`, service, worker, launcher; thêm dispatcher/outbox/Redis adapter sau contract. |
| Allocation/DB | forecasting/allocation/service/verification, reporting/workspace/purchasing read models và query plan; bulk IO và index theo số đo. |
| UI | `Table.tsx`, `State.tsx`, `index.css`, ContextFilters/useAppContext, Inventory/Products/Scenarios và components snapshot/alerts. |
| Host | Dockerfiles/Compose/env examples/readiness/migration command, worker shutdown, persistent mounts và tài liệu deployment mới. Không chứa credentials hoặc raw. |

## 8. Nguồn kỹ thuật đã đối chiếu

Đây là tài liệu tham khảo cho thiết kế đề xuất, không phải bằng chứng tính năng SIGMA đã triển khai.

- [FastAPI: OAuth2, JWT và password hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/): tham khảo cách xác thực và thư viện password hash; không tự coi tutorial là giải pháp phân quyền supplier hoặc thu hồi phiên hoàn chỉnh.
- [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/): consumer group, ack và pending/reclaim; delivery lặp cần được xử lý bởi nghiệp vụ/DB. Không nhận queue exactly-once.
- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html): đo và đọc query plan trước khi thêm index/đổi query. Chỉ EXPLAIN ANALYZE trên môi trường thử phù hợp.

## 9. Bàn giao tài liệu

Mục9.0 và9.1 ghi checkpoint sổ kho trước khi có QR/Redis/release identity. Đọc [mục9.2](#92-phạm-vi-thực-có-sau-ủy-quyền-tự-chọn) và [trạng thái sản phẩm](../PRODUCT_STATUS.md) cho hiện trạng; không lấy các dòng “chưa thêm” ở checkpoint cũ làm công việc còn thiếu hiện nay.

Checkpoint hiện hành: [sổ kho vận hành15/11](../development.md#handoff-operational-ledger). Các số541/143 ở hàng P1/P2 dưới đây thuộc lượt trước; hiện đã kiểm552backend và156React, kèm20ca chạy lại sau rà cuối và10nhóm browser. Không coi tổng số test là nghiệm thu toàn P3 hoặc production.

| Bước | Hiện trạng15/11 |
| --- | --- |
| P0 | Đã lấy main đúng SHA, đọc source, có baseline FE và môi trường thử PG18/Python3.12 riêng. Quyết định nghiệp vụ và benchmark dữ liệu thật chưa đủ. |
| P1/P2 | Đã có auth/session/migration0010, portal supplier chỉ đọc, tài khoản admin, snapshot business allowlist và nền bảng/loading/filter.541 backend,143 React qua kiểm tra;17 kiểm browser thực trên fixture synthetic qua. Snapshot28/90 được kiểm thêm12 ca liên quan. Chưa nhận toàn bộ P2 hoặc FB01/06/12 đã xong ở mọi màn hình. |
| P3 | Có sổ kho/đơn nhập/nhận từng phần/xuất/kiểm kê, lead time supplier1–365 cho đơn mới. Chưa tích hợp forecast/ROP/horizon mới, QR còn chờ D01; supplier chỉ đọc. Hướng sổ kho thực hiện theo yêu cầu sản phẩm vận hành, chưa coi D06 hoặc định dạng QR được mentor chốt. |
| P4 | Chưa bỏ hash runtime hoặc đổi/cache allocation; chờ D02/D03. |
| P5 | Chưa thêm Redis/outbox hoặc công bố tối ưu DB/kịch bản. Chưa có số đo trước–sau. |
| P6/P7 | Đã kiểm browser phần auth/tồn/snapshot; chưa E2E nghiệp vụ mới QR/ETA/Redis, chưa host/public bản nâng cấp. |

Chi tiết vận hành auth ở [AUTHENTICATION](../AUTHENTICATION.md). Không dùng số test kỹ thuật làm bằng chứng R05/R07/T14 hoặc tính năng chưa triển khai đạt yêu cầu.

Tiếp theo: tích hợp sổ kho/lead time vào profile kế hoạch mới có đủ dự báo, chốt QR/hash/allocation, hoàn thiện auth recovery, Redis/outbox, đo DB và host theo P3–P7. Không dùng đơn vận hành mới làm bằng chứng mô hình cũ đã hỗ trợ ETA khác7; không để đề xuất thành xác nhận nghiệp vụ ngầm.

### 9.1 Ca nghiệm thu sổ kho đã kiểm

| Ca | Bằng chứng / trạng thái |
| --- | --- |
| Kho/SKU trống và tồn đầu | Không seed hàng giả; đăng ký danh mục, count0/current position và kho vật lý riêng được kiểm API/React/browser. |
| Nháp→xác nhận→nhận thiếu→đủ | API và browser nhận4+6 trên đơn10; status và số dư đúng, không ghi vào run cũ. |
| Xuất/kiểm kê | Chặn vượt tồn, kiểm kê nhập số đếm thực tế, có0; ledger sum=balance qua test. |
| Lỗi mạng/gửi trùng/cùng sửa | Retry không ghi hai lần, key khác body409;2request đồng thời và version stale được kiểm PostgreSQL. |
| Lỗi ghi audit | Inject lỗi cuối transaction, không có phiếu/số dư/nhận dở; retry phục hồi qua test. |
| Ngày và hủy | Future/backdate bị chặn; hủy phần thiếu giữ tồn đã nhận, đơn đóng không nhận thêm. |
| Supplier | API tách A/B/anonymous và read-only; browser own order, không có nút admin. |
| Migration/lịch sử | Metadata parity, guard downgrade và trigger bất biến qua test; HTTP/DDL golden cũ giữ riêng. |
| UX |4viewport, footer form luôn thấy, bảng28kho cuộn trong vùng/phân trang25; chưa là kiểm tải/UAT sản xuất. |

Các ca tích hợp forecast dùng số dư vận hành, QR, Redis recovery và hosting bền dữ liệu chưa đạt/chưa chạy; không đánh dấu bằng các ca trên.

### 9.2 Phạm vi thực có sau ủy quyền tự chọn

| Phần | Hiện có và giới hạn |
| --- | --- |
| UI/auth/snapshot/table | React/admin/supplier scoped, skeleton, bảng cuộn riêng, URL bộ lọc, modal snapshot; có React/browser/CI. Không coi là UAT mọi thiết bị. |
| QR | QR phiếu giao/lô SIM vật lý, preview và xác nhận; kiểm API/browser/trùng/sai đơn/eSIM. Chưa camera/ICCID hoặc parser nhà mạng. |
| Lead time/tồn thực | Đơn mới freeze mặc định supplier1–365. Tư vấn cộng tồn/pending và ROP theo lead thực, chặn khi forecast không đủ. Không giả H14 bao được lead30; snapshot tư vấn/đơn tự động còn thiếu. |
| Hash runtime | Release-version mode cho image bất biến, giữ local source guard và checksum audit/password. Không xóa cột/manifest cũ hoặc nói mọi hash đều bị bỏ. |
| Phân bổ/hiệu năng | Cơ sở90ngày tính theo từng origin, không chạy lại cho từng target day. Index/group lookup/input tuyến tính một lần; có parity và số đo lookup, chưa số đo toàn ML/DB tải lớn. |
| Redis | Có Streams, PG queued làm durable outbox, ACK/reclaim/gián đoạn, một owner; Redis thật và Compose startup qua CI71f846e. Không quảng cáo multi-worker/exactly-once. |
| Đóng gói/host | Có image/Compose PostgreSQL/Redis bền volume, role app không superuser, source-only runtime. CI52a96e2 đã kiểm startup và restore DB/artifact synthetic. Chưa có public host/HTTPS24/7 hoặc nguồn bán thật trên checkout này. |

R05/R07/T14 và dữ liệu nguồn không đổi. Test synthetic không thay bằng chứng mô hình đạt10/10 hoặc chứng minh đã chạy dataset riêng của nhóm.
