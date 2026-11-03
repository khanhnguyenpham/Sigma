# CHG-087 — Demo đầy đủ chức năng trên Render và Vercel

**03/11/2026 — Kế hoạchCHG087, triển khai D1 theo CHG088.** Người dùng giao làmD1 và bỏ yêu cầu thông báo “demo dùng chung” trên giao diện. D1 đang kiểm nền settings/launcher/probes và cấu hình mẫu; D2–D6 chưa làm. Chốt nghiệp vụ vẫn là project thực tập đầy đủ chức năng, **mọi khách thao tác trên demo dùng chung**, dữ liệu đã ẩn danh. Không có giai đoạn chỉ đọc bắt buộc. [Yêu cầu](../requirements.md#chg087-shared-demo), [bàn giao kế hoạch](../development.md#handoff-chg087), [nền chạyD1](../../web/backend/configs/DEMO_RUNTIME.md), [kiểm S25 đã có](../../M3/docs/S25_CURRENT_REVIEW.md).

<a id="scope"></a>
## 1. Phạm vi đã chốt

Một ứng dụng công khai, không yêu cầu đăng nhập cho chức năng nghiệp vụ. Mọi khách xem và chỉnh **cùng một DB demo**; run, policy, kho và lịch sử cung cấp được khách khác nhìn thấy. Người dùng03/11/2026 yêu cầu bỏ banner/thông báo demo dùng chung khỏiUI; đây không còn là tiêu chí triển khai. Không thiết kế workspace riêng cho từng khách.

| Nhóm | Khách có thể làm | Điều kiện |
| --- | --- | --- |
| Nguồn | Tạo source_import từ bộ nguồn demo đăng ký sẵn | Không nhận file cá nhân hoặc đường dẫn/URL tùy ý; không mở raw local |
| Dự báo | Tạo forecast theo luồng UI hiện có, xem tiến độ và kết quả | Worker thực thi thật, giữ quan hệ nguồn và quy tắc chọn model; không trả kết quả mẫu giả cho run mới |
| Tồn kho | Tạo stock_projection, policy_replay, alert_replay | Fixed ROP/SS days/fixed quantity, L7/R1/H14, snapshot frozen và verifier giữ đúng |
| Cấu hình | Sửa kho, tạo phiên bản policy/scenario theo thao tác app hiện hỗ trợ | Giữ ngày hiệu lực/version/validation/409; không thêm nghiệp vụ doanh nghiệp ngoài app |
| Lifecycle | Ngừng/hủy/mở nhập nội bộ; preview/tạo/quản lý thông báo nhà mạng | Giữ quyền mua/bán, nhiều kho, cap/ETA; run complete không đổi theo cấu hình live |
| Kết quả | Lọc, biểu đồ, chi tiết, metric và CSV, dự báo tổng30 | DB/API/UI/CSV cùng run/scope; tổng30 có gói tương thích source demo |
| Vận hành | Người vận hành seed/reset/backup/migrate/deploy bằng công cụ riêng | Không có reset toàn DB công khai hoặc credential trong trình duyệt |

“Đầy đủ” là chức năng nghiệp vụ hiện có hoạt động xuyên suốt online. Không cần tài khoản, RBAC nhiều vai trò, tenant riêng, thanh toán, Redis/Celery, autoscaling hoặc object storage để bắt đầu. Giới hạn tài nguyên đặt ở chỗ nhận job, không biến app thành chỉ đọc.

Giữ C00 mặc định theo [kiểm S25](../../M3/docs/S25_CURRENT_REVIEW.md); không ép45% hoặc tự tích hợp S25. Online không tự nghiệm thu R05/R07/T14 hoặc biến dữ liệu demo thành bằng chứng mentor mới.

<a id="architecture"></a>
## 2. Kiến trúc tối giản được chọn

~~~mermaid
flowchart LR
    G[Mọi khách: xem và thao tác] --> V[Vercel: React/Vite]
    V -->|/api/v1 và CSV qua rewrite| A[Render: FastAPI]
    subgraph R[Một Render web service, một instance]
        A
        W[Worker hiện có, một process]
        D[(Persistent disk: nguồn demo và artifact)]
        A --> D
        W --> D
    end
    A --> P[(Postgres demo dùng chung)]
    W --> P
    O[Người vận hành] -->|seed, reset và backup có kiểm soát| P
    O -->|gói demo đã ẩn danh| D
~~~

Chọn **một Render web service trả phí có persistent disk**, chạy API và worker như hai process cùng release. [LauncherD1](../../web/backend/scripts/demo_stack.py) đã được thêm và đang kiểm: quản lý cả hai, truyền tín hiệu dừng, dọn processcon và báo lỗi khi một process chết. API một process Uvicorn; giữ queue PostgreSQL/advisory lock và một worker hiện có. Không fit model trong HTTP request hoặc tạo worker cho mỗi request.

Đây là lựa chọn kỹ thuật của project: disk Render chỉ gắn với một instance, không chia sẻ sang service khác; gắn disk có giới hạn scale và gián đoạn khi deploy. Chấp nhận các giới hạn đó cho demo thực tập. Không tách API/worker rồi giả định hai service mount chung disk. [Render disks](https://render.com/docs/disks).

Postgres demo tách khỏi appDB local và các DB bằng chứng. Disk chứa nguồn dẫn xuất, run mới và gói tổng30 demo; không mount thư mục gốc người dùng. API không public static nguồn/artifact/log, CSV qua route export. Cần giữ nguồn và artifact qua restart để chạy thêm run và đọc kết quả cũ. Nếu benchmark thiếu RAM/CPU thì tăng tài nguyên một service trước; chỉ xét tách worker/storage khi có nhu cầu đo được.

## 3. Dữ liệu phải hỗ trợ cả chạy mới

Không chỉ chuẩn bị DB kết quả tính sẵn. Gói demo phải đủ để import → forecast → inventory bằng pipeline hiện có, kèm run ban đầu để người xem vào là có nội dung.

1. Kiểm nguồn hiện tại theo hợp đồng20cột của src/data.py. Xuất bản dẫn xuất riêng: thay order/customer ID thật bằng giá trị demo, loại thông tin cá nhân/activation và trường tự do không cần thiết; giữ schema hợp lệ, quantity, ngày UTC, thứ tự giao dịch và quan hệ duplicate cần cho audit. Cột bắt buộc không dùng nghiệp vụ nhận giá trị demo hợp lệ. Nếu nguồn đã ẩn danh thì ghi nhận kiểm tra; không xin dữ liệu doanh nghiệp mới hoặc tải bảng ánh xạ ID lên cloud.
2. Không thay CSV20cột bằng aggregate rồi nhận source_import chạy nguyên trạng. Phải kiểm bằng auditor/importer thật. Nếu gộp dữ liệu để ẩn danh thì sinh nguồn demo hợp lệ, đối chiếu aggregate/cohort và ghi phần số liệu thay đổi.
3. Country/carrier/SKU dùng mã công khai đã kiểm hoặc alias đồng bộ. Nếu đổi danh tính tuyến thì cấu hình model/top10/selection demo phải tương thích; không đổi cấu hình M2/M05 gốc. Giữ train/validation/test và không dùng test để chọn lại model.
4. Tạo DB demo mới và seed kho/danh mục/policy/scenario/parents/run ban đầu bằng UUID/hash/provenance mới. Profile hiện tại fixed ROP/days/fixed quantity, trade_v2; tồn/nhập/ETA có nhãn giả định. Có source/forecast cha sẵn để thử nhanh, đồng thời tạo source/forecast mới vẫn hoạt động.
5. Chuẩn bị gói tổng30 tương thích source demo, kiểm route-day và provenance. Khi phải tạo gói dẫn xuất thì dùng ID/manifest/receipt mới qua luồng kiểm hợp lệ; không sửa sealed package hoặc bỏ hash check để gắn gói nguồn thật vào source demo. Chuẩn bị benchmark không trở thành nút tuning nghiên cứu công khai.
6. Kiểm cả nguồn seed và chuỗi source mới → forecast mới → inventory mới; kể cả import lại nguồn cùng nội dung và quan hệ nguồn của view tổng30. Chạy verifier, đối chiếu DB/API/CSV. Không gắn kết quả tính sẵn của nguồn khác vào run mới.
7. Kiểm DB/JSON/snapshot/CSV/error/log/bundle để không lộ ID gốc, secret, đường dẫn cá nhân hoặc raw download. Giữ snapshot/hash bằng chứng local nguyên; bản demo có nhãn dẫn xuất, không nhận số/hash bằng bản gốc nếu đầu vào đổi.

Gói dự kiến upload có danh sách tệp/trường, size/hash và kiểm ẩn danh cụ thể. Tạo gói/seed/chạy run là phần triển khai sau, chưa làm ở lượt chỉ Markdown.

<a id="demo-money-fields"></a>
### Giá và doanh thu trong bản nguồn demo

Bổ sung03/11/2026: người dùng cho phép bỏ hoặc làm giả giá vì demo chỉ cần quantity. Chọn cách giữ hợp đồng20cột, **thay toàn bộ giá trị tiền bằng0 trong bản CSV dẫn xuất dành cho demo**:

| Cột | Giá trị demo | Ý nghĩa |
| --- | --- | --- |
| unit_price_vnd | 0 | Placeholder, không phải giá bán thật |
| unit_cost_vnd | 0 | Placeholder, không phải giá vốn thật |
| gross_revenue_vnd | 0 | quantity × unit_price_vnd, không phải doanh thu thật |

Importer hiện yêu cầu đủ20cột và kiểm gross_revenue_vnd=quantity×unit_price_vnd; xóa cột sẽ cần đổi hợp đồng/importer. Không cần thêm việc đó cho demo. Không dùng hệ số nhân, làm tròn hoặc giá ngẫu nhiên từ giá thật; không giữ doanh thu gốc khi đã thay đơn giá. [Hợp đồng bản demo](../data-contract.md#demo-price-policy).

D2 thực hiện biến đổi trên bản sao mới, giữ CSV gốc và bằng chứng sealed nguyên. Auditor phải xác nhận nguồn hợp lệ trước biến đổi để không vô tình che xung đột duplicate bằng cách xóa khác biệt về tiền. Sau biến đổi kiểm đủ schema, tiền bằng0/toàn bộ hàng, không money-invalid/revenue-mismatch; đối chiếu quantity theo ngày UTC×item/tuyến, trạng thái, thứ tự và dedup như trước. Mô hình hiện dự báo quantity, các cột tiền được audit/tổng hợp nhưng không là feature/target dự báo hoặc tham số tồn; việc kiểm giữ nguyên dữ liệu quantity là bắt buộc.

Gói seed/artifact/export demo cũng phải được dựng từ nguồn đã xử lý, không mang theo bảng doanh thu/giá gốc từ kết quả cũ. Giá trị0 có nhãn placeholder demo, không diễn giải thành giá hoặc doanh thu thực bằng0. Nguồn dẫn xuất có SHA/provenance mới; không sửa hash hoặc giá trị trong run gốc. Đây là quy tắc chuẩn bịD2, **chưa tạo hoặc chỉnh CSV/DB ở lượt bổ sung kế hoạch này**.

## 4. Công việc code dự kiến

| Phần | Việc cần làm | Kiểm |
| --- | --- | --- |
| Settings | Origin HTTPS theo môi trường, PostgreSQL psycopg/TLS và cấu hình demo riêng | Từ chối cấu hình sai/trỏ appDB; không lộ secret |
| Launcher | Quản lý API + worker cùng release/disk và toàn bộ process con | Worker chết không báo khỏe; shutdown/restart không sót hoặc trùng process |
| Queue/quota | Queue/advisory lock cũ; một job chạy, giới hạn queue/tần suất/request/retention | Backend kiểm nguyên tử cả direct Render API, trả lỗi và thời gian thử lại rõ |
| Forecast compute | Kiểm ProcessPoolExecutor(max_workers=3) hiện có; demo dự kiến1process tính toán và giới hạn thread model | Đo RSS/thời gian nguồn/forecast/inventory; không đổi model/công thức/selection |
| FE | Giữ form/tạo run và giao diện hiện tại; hoàn thiện tiến độ/queue/error/retry ởD3 | Không thêm banner theo yêu cầu; hai cửa sổ/409/double-submit/Back/reload/mobile đúng |
| Routing | Giữ /api/v1; Vercel rewrite cho fetch và CSV, origin tường minh | GET/POST/PATCH, Idempotency-Key, query/status/lỗi/export headers qua proxy |
| Health | Health nhẹ, readiness kiểm DB/schema/disk/gói và worker heartbeat | Phát hiện worker/DB/disk lỗi thay vì chỉ API trả200 |
| Seed/reset | Lệnh vận hành riêng chỉ cho DB/path demo, maintenance/drain | Từ chối appDB và tệp bằng chứng; restore DB+artifact đồng bộ |

API/worker dùng role đọc/ghi dữ liệu demo, không có superuser/CREATE DATABASE/DDL; migration/reset dùng credential vận hành riêng. Khách không cần đăng nhập theo lựa chọn đã chốt. CORS không phải xác thực hoặc ngăn script gọi API trực tiếp; quota/request limits phải đặt ở backend, không chỉ disable nút.

Chốt giới hạn queue/tần suất/thời gian job/retention sau benchmarkD3. Không âm thầm giảm horizon/cohort, đổi model hoặc trả complete khi chưa chạy. Job giới hạn/gián đoạn có trạng thái/lý do và retry hợp lệ. Không thêm quota tài khoản khi không có tài khoản.

## 5. Cấu hình hosting dự kiến

| Thành phần | Cấu hình | Ghi chú |
| --- | --- | --- |
| Render web | Root repo, Python3.12, một instance/API/worker | Cần cả src/, M2/, data/configs và web/backend/configs |
| Build | python -m pip install -r web/backend/requirements.txt && python -m pip install --no-deps -e web/backend | Dependencies hiện có; package yêu cầu Python>=3.12,<3.13 |
| Start | `python web/backend/scripts/demo_stack.py` quản lý Uvicornfactory0.0.0.0/PORT và worker | Có ởD1; không migrate/seed/reset khi boot, không mở process cho mỗi request |
| Disk | Ví dụ /var/data/sigma-demo, nguồn source/data/, run outputs/m3/ | Monthly_benchmarks và run cùng dưới disk theo path resolver; nguồn immutable, artifact phát sinh |
| Postgres | DB demo riêng cùng region, internal URL, psycopg3/TLS theo endpoint | Schema head0008 hiện tại; migration/seed một nơi |
| Env | M3_MODE=demo, M3_DEMO_ROOT, M3_DATABASE_URL, M3_FRONTEND_ORIGIN, M3_SOURCE_ROOT, M3_OUTPUT_ROOT; quota/compute ởD3 | Chung cho API/worker, server-only; DBsigma_demo/test, rootdemo riêng, không copy .env local |
| Vercel | Root web/frontend; Node24 theo CI; npm ci; npm run build; output dist | Hash router hiện tại không cần SPA catch-all |
| Proxy/domain | /api/:path* tới Render /api/:path*; HTTPS mặc định .vercel.app/.onrender.com | Kiểm writes/CSV; không cache API mutable như asset; staging origin riêng, không wildcard mọi preview |

Không cần mua domain để trình diễn. Biến VITE_* có thể vào bundle công khai, không lưu secrets. External rewrite là khả năng của Vercel; lệnh/path/launcher ở đây là thiết kế project cần kiểm Linux/cloud. [Vercel rewrites](https://vercel.com/docs/routing/rewrites), [environment variables](https://vercel.com/docs/environment-variables), [Render Python](https://render.com/docs/python-version).

## 6. Chi phí phù hợp demo thực tập

Kiến trúc cơ sở: **Vercel FE + một Render web có disk + một Postgres demo**. Không trả thêm worker riêng/object storage/domain. Chưa chọn mua gói hoặc tổng ngân sách; đo RAM/CPU/disk trước. Một queue worker có thể sinh process model, không nhận512MB/2GB đủ khi chưa đo.

| Phương án | Khi dùng | Giới hạn |
| --- | --- | --- |
| Cơ sở có disk | Demo đầy đủ, giữ nguồn/run qua restart/deploy | Disk cần service trả phí; tổng gồm compute/disk/DB/usage, chưa là báo giá |
| Free thử ngắn | Chỉ thử hosting tạm khi chưa có ngân sách | Không persistent disk, file có thể mất sau restart/cold start; không nghiệm thu lưu dữ liệu bản đầy đủ |
| Tăng tài nguyên một service | Forecast vượt RAM/CPU | Giữ kiến trúc một instance trước, tách service/storage khi có nhu cầu thực |

Render Free ngủ sau15phút, có thể mất khoảng1phút khởi động; Postgres Free hết hạn30ngày và không có backup tự động. Tính vào lịch demo, không ping để lách ngủ. [Render Free](https://render.com/docs/free). Vercel Hobby cho mục đích cá nhân, phi thương mại theo [Hobby docs](https://vercel.com/docs/plans/hobby); kiểm điều kiện tài khoản và giá/usage khi triển khai.

Không giữ hai môi trường trả phí song song lâu dài chỉ để demo: dùng staging tạm, giữ bản local kiểm được rồi chuyển URL public theo release. Chốt ngân sách/tài khoản khi chuẩn bị triển khai thật; không chặn hoàn thiện kế hoạch Markdown.

<a id="steps"></a>
## 7. Lộ trình mới

| Bước | Công việc và đầu ra | Điều kiện hoàn tất |
| --- | --- | --- |
| D0 — chất lượng | Giữ kiểmS25/C00 đã có, C00 mặc định | Đã xongCHG086; không chạy lại/tích hợpS25 ở lượt này |
| D1 — nền demo đầy đủ | Settings/launcher API-worker cùng disk, health/readiness, cấu hình hosting mẫu; bỏ banner theo yêu cầu | Boot/shutdown/restart Windows-Linux với synthetic; không thay chức năng bằng chỉ đọc |
| D2 — dữ liệu và khôi phục | Nguồn20cột đã ẩn danh, seedDB/policy/scenario/parents/kết quả/tổng30, manifest/hash và reset | Chuỗi import/forecast/inventory từ đầu trên DBdemo; kiểm ẩn danh, reset DB+artifact đạt |
| D3 — kiểm chức năng/tài nguyên | Hai khách, versionconflict/queue/quota/retry, CSV/chart/tổng30/lifecycle, benchmark và mức giới hạn | Python/React/build/pipcheck; browser1440/390px; verifier độc lập; retention không phá run cha |
| D4 — triển khai thử | Vercel preview, Render service/disk/DBdemo, secrets server-only, seed đúng gói, mức chi phí/account cụ thể | Thực hiện sau khi được giao triển khai; gói/chi phí cụ thể; không nối DBlocal |
| D5 — online/công khai | Chuỗi run mới thật, chỉnh policy/lifecycle, frozen/CSV, hai browser, directAPI/proxy/restart/restore | Đủ chức năng, không lộ dữ liệu, quota/worker/backup đúng; URL/SHA/hashes/hướng dẫn cùng release |
| D6 — bàn giao vận hành | Reset/backup/restore/rollback, chẩn đoán queue/worker, hạn mức/chủ tài khoản | Người vận hành dựng lại được demo; không tự đóng R05/R07/T14 |

**Hiện tại:** D0 có bằng chứngCHG086. Người dùng đã giao D1, đang kiểm code settings/launcher/probes và template; D2–D6 chưa triển khai. Điểm dừng chỉMarkdownCHG087 là lịch sử, không cấmD1 mới được giao. Không migrate/seedDBapp, chạy nguồn thật, upload dữ liệu, trả phí hoặc deploy ởD1. Code nghiên cứuCHG086 vẫnlocal/ngoài stage; yêu cầu bỏ banner được áp dụng cho phạm vi hiện tại. [NềnD1 và phần còn chờD2/D3](../../web/backend/configs/DEMO_RUNTIME.md).

<a id="acceptance"></a>
## 8. Tiêu chí demo hoàn chỉnh

- Khách không đăng nhập chỉnh được kho/policy/scenario/lifecycle theo luồng hiện có. Khách khác thấy thay đổi sau refetch; cùng version bị409 đúng. Theo yêu cầu03/11/2026 không thêm banner/thông báo demo dùng chung.
- Tạo source từ bộ demo, forecast mới và cả3loại run tồn; queue/progress/error/retry và output thực, không chỉ xem run tính sẵn. Tổng30 tương thích source; H14 vận hành, threshold/depletion giữ riêng.
- Policy/stop/notice tác động run mới theo cutoff; run complete giữ snapshot/hash. Không mất quyền mua/bán/blocked/cap/Q/exclusions khi online; không gắn S25/45% làm cổng ngầm.
- API/CSV/chart/pagination/export khớp trên desktop/390px, Back/reload đúng. Writes qua proxy và directAPI cùng validation/quota/idempotency; không có đường bypass đưa source/file tùy ý.
- Một worker queue, job nặng không khóa API; benchmark có số đo. Restart/deploy không double worker/order; run gián đoạn và retry có trạng thái/quan hệ nguồn đúng, không nhận tự resume khi chưa hỗ trợ.
- Restart vẫn đọc source/artifact/run cũ và chạy thêm run mới; không DBcomplete trỏ artifact mất. Reset/restore đúng DB+disk version, retention bảo vệ run cha và file đang dùng.
- Không lộ secret/ID gốc/raw/log qua response/CSV/error/static/bundle; ghi chỉ ở DBdemo. Hiển thị giới hạn/giả định, không nhận chất lượng mô hình đã nghiệm thu.

## 9. Reset, backup và deploy lại

Reset là lệnh vận hành riêng, không có nút công khai. Kiểm tên DBdemo và absolute disk path trước thao tác; từ chối appDB/bằng chứng local. Vào maintenance ngừng nhận job/ghi, drain worker hoặc đánh dấu interrupted, dừng API/worker rồi restore DB+artifact cùng manifest, verify và mở lại. Không reset giữa request còn ghi, không tự reset mỗi lần worker khởi động hoặc thêm cron ngoài yêu cầu.

Trước release backup và restore thử cả DB/disk; backup Postgres không thay artifact backup. Gói seed nguồn bất biến có manifest lưu riêng; run do khách tạo có retention rõ, không hứa lưu vĩnh viễn. Nếu cần giữ run hiện tại, chụp DB/artifact đồng bộ trước reset. Không xóa artifact hoặc source/forecast cha đang được tham chiếu để giảm dung lượng.

Migration chạy một nơi có maintenance/rehearsal, không ở mọi API/worker startup. Render pre-deploy chạy compute riêng không truy cập disk; seed cần disk chạy bằng thao tác runtime có kiểm soát. Launcher quản lý signal/process group, readiness và process chết. Worker hiện đánh dấu runrunning thànhfailed/interrupted khi restart; kiểm/trình bày đúng, không hứa tự tiếp tục. [Render deploy/pre-deploy](https://render.com/docs/deploys).

Rollback đồng bộ FE/API/worker/schema/source/artifact. Chỉ rollback code nếu schema tương thích; nếu không roll forward hoặc restore DB+disk đã kiểm, ghi rõ thay đổi demo sau backup có thể mất. Không downgrade0008 khi dữ liệu không tương thích. Theo dõi health/readiness/queue/worker, lỗi/RAM/disk/DB và usage bằng dashboard sẵn có; không dựng hệ thống giám sát doanh nghiệp.

## 10. Tham chiếu và phạm vi suy luận

- Mã đã đọc: core/settings.py, main.py, worker.py, modules/runs, modules/forecasting, modules/reporting/monthly.py, src/data.py, FE RunDialog.tsx/HTTP. Phần thiếu ở mục4 là kế hoạch, chưa nhận đã triển khai.
- [Render disks](https://render.com/docs/disks), [Free](https://render.com/docs/free), [deploys](https://render.com/docs/deploys), [Python](https://render.com/docs/python-version), [Postgres](https://render.com/docs/postgresql-creating-connecting), [backup/PITR](https://render.com/docs/postgresql-backups), [pricing](https://render.com/pricing).
- [Vercel Vite](https://vercel.com/docs/frameworks/frontend/vite), [rewrites](https://vercel.com/docs/routing/rewrites), [environment](https://vercel.com/docs/environment-variables), [Hobby](https://vercel.com/docs/plans/hobby).

Co-locate API/worker, xuất nguồn và reset/quota là đề xuất từ mã project, không phải cam kết nền tảng rằng nguyên lệnh sẽ chạy. Benchmark/Linux/staging xác nhận ởD1–D5. Đối chiếu nguồn nền tảng ngày03/11/2026; kiểm lại cấu hình/giá lúc triển khai thật.
