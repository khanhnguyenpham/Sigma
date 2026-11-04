# Demo đầy đủ chức năng — triển khai chỉ dùng free

**CHG-092/D5 — 04/11/2026, hoàn tất cho phương án máy đang mở:** Chuỗi nguồn/forecast/3loại tồn mới, interrupted→retry, cấu hình/lifecycle/frozen,12cặpAPI/CSV, hai phiênUI, desktop1440/mobile390, direct/HTTPSquota và full-size restore đã kiểm. [Bàn giao](../development.md#handoff-chg092-d5). Full snapshot15run giữ riêng; demo live phục hồi8run trước D5 để còn8slot. Link mới https://charlie-sas-men-scenarios.trycloudflare.com/ ; Vercel cũ chưa nốiAPI. Các checkpoint D4 bên dưới là lịch sử; D6 chưa làm. Không trả phí, không cam kết hoạt động khi máy tắt.

**04/11/2026 — đã triển khai thử backend khi máy mở:** Người dùng đã chấp nhận phương án phụ thuộc máy cá nhân và giao deploy thử BE. API+worker+Postgres/demo storage riêng chạy local, Cloudflare Quick Tunnel miễn phí phục vụ luônUI/API cùng origin; đã kiểmready/46kho/920sản phẩm, một job tồn mới complete/verified/API/CSV và dừng/mở lại. [Bàn giao/cách chạy](../development.md#handoff-chg091-d4-local). Vercel cũ chưa rewriteAPI. Yêu cầu online khi máy tắt/không local tunnel của03/11 bên dưới là checkpoint trước lựa chọn mới; không cần chờ Oracle cho bản thử này. D5–D6 chưa nghiệm thu.

**CHG-091/D4,03/11/2026:** Người dùng chốt **không phát sinh phí, không dùng dịch vụ trả phí** và **máy cá nhân tắt demo vẫn online**. Frontend đã build/deploy READY trên Vercel Hobby; backend chưa triển khai, chưa nối API, D4 còn dở. Phương án Render service/disk trả phí trước đây bị thay thế; không áp dụng template đó, không dùng credit trial của tài nguyên trả phí hoặc nâng gói. Không dùng tunnel chạy trên máy cá nhân. [Bàn giao D4](../development.md#handoff-chg091-d4). Các câu “chưa deploy/D4–D6 chưa làm” của checkpoint D3 dưới đây là lịch sử; D5–D6 hiện vẫn chưa làm.

**03/11/2026 — tiếp tục D3 và gỡ Tổng 30 khỏi demo theo yêu cầu mới.** Bỏ hẳn giao diện/API Tổng 30, không thêm cờ bật/tắt hoặc phụ thuộc bundle/receipt ngoài. Luồng dự báo vận hành H14/tồn/nhập/cảnh báo giữ nguyên. R05/M05 và bằng chứng nghiên cứu lịch sử không tự nghiệm thu hoặc xóa. Các checkpoint chờ Tổng30/tạm dừng phía dưới là lịch sử. D3 đã qua cổng code/publish tại3f5c430 (remoteSHA/haiCI success); full-size backup/reset và shutdown đạt; chưa deploy; D4–D6 chưa làm.

D0–D2 đã kiểm xong phần phục vụ demo hiện hành. D3 đã kiểm local: worker xử lý interrupted, retry mới có liên kết, forecast/3inventory/CSV/browser/quota và full-size backup/reset đạt; không sửa run lỗi cũ thành complete. [Bàn giao D3](../development.md#handoff-chg090-d3).

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
| Kết quả | Lọc, biểu đồ, chi tiết, metric và CSV vận hành H14 | DB/API/UI/CSV cùng run/scope |
| Vận hành | Người vận hành seed/reset/backup/migrate/deploy bằng công cụ riêng | Không có reset toàn DB công khai hoặc credential trong trình duyệt |

“Đầy đủ” là chức năng nghiệp vụ hiện có hoạt động xuyên suốt online. Không cần tài khoản, RBAC nhiều vai trò, tenant riêng, thanh toán, Redis/Celery, autoscaling hoặc object storage để bắt đầu. Giới hạn tài nguyên đặt ở chỗ nhận job, không biến app thành chỉ đọc.

Giữ C00 mặc định theo [kiểm S25](../../M3/docs/S25_CURRENT_REVIEW.md); không ép45% hoặc tự tích hợp S25. Online không tự nghiệm thu R05/R07/T14 hoặc biến dữ liệu demo thành bằng chứng mentor mới.

<a id="architecture"></a>
## 2. Kiến trúc và trạng thái chọn hosting

~~~mermaid
flowchart LR
    G[Mọi khách: xem và thao tác] --> V[Vercel: React/Vite]
    G --> T[Cloudflare Quick Tunnel: link thử hiện hành]
    T -->|UI và /api/v1 cùng origin| A[FastAPI: máy cá nhân8041]
    V -.->|Vercel cũ chưa nối API| A
    subgraph R[Runtime demo riêng: chạy khi máy mở]
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

Frontend đã deploy trên [Vercel](https://sigma-demo-eta.vercel.app/), project `sigma-demo`, từ commit4476a1c; URL đó chưa nốiAPI. Bản thử04/11 dùng giao diện build có sẵn do FastAPI phục vụ qua cùng linkQuickTunnel, không cần redeploy Vercel khi hostname tunnel đổi. API và worker như hai process cùng release, dùng DB/disk demo riêng trên máy cá nhân. [LauncherD1](../../web/backend/scripts/demo_stack.py) đã kiểm trên Windows/Linuxx64: quản lý cả hai, truyền tín hiệu dừng, chờ processgroup ngừng và báo lỗi khi một process chết. API một process Uvicorn; giữ queue PostgreSQL/advisory lock và một worker hiện có. Không fit model trong HTTP request hoặc tạo worker cho mỗi request.

Render có disk trả phí là thiết kế cũ, không còn được áp dụng. Render Free không có persistent disk; không triển khai rồi nhận dữ liệu/run sẽ bền qua restart. [Render disks](https://render.com/docs/disks), [Free](https://render.com/docs/free). Oracle Always Free chỉ là ứng viên chờ người dùng chấp nhận điều kiện đăng ký/tài khoản, xác minh capacity và kiểm LinuxARM; chưa là giải pháp đã chạy. Không đổi model hoặc dùng tài nguyên trả phí khi thiếu capacity.

Postgres demo tách khỏi appDB local và các DB bằng chứng. Disk chứa nguồn dẫn xuất và run mới; không mount thư mục gốc người dùng. API không public static nguồn/artifact/log, CSV qua route export. Cần giữ nguồn và artifact qua restart để chạy thêm run và đọc kết quả cũ. Nếu gói free thiếu RAM/CPU/storage thì dừng phần provision phụ thuộc đó, không tự tăng lên tài nguyên trả phí hoặc giảm chức năng.

## 3. Dữ liệu phải hỗ trợ cả chạy mới

Không chỉ chuẩn bị DB kết quả tính sẵn. Gói demo phải đủ để import → forecast → inventory bằng pipeline hiện có, kèm run ban đầu để người xem vào là có nội dung.

1. Kiểm nguồn hiện tại theo hợp đồng20cột của src/data.py. Xuất bản dẫn xuất riêng: thay order/customer ID thật bằng giá trị demo, loại thông tin cá nhân/activation và trường tự do không cần thiết; giữ schema hợp lệ, quantity, ngày UTC, thứ tự giao dịch và quan hệ duplicate cần cho audit. Cột bắt buộc không dùng nghiệp vụ nhận giá trị demo hợp lệ. Nếu nguồn đã ẩn danh thì ghi nhận kiểm tra; không xin dữ liệu doanh nghiệp mới hoặc tải bảng ánh xạ ID lên cloud.
2. Không thay CSV20cột bằng aggregate rồi nhận source_import chạy nguyên trạng. Phải kiểm bằng auditor/importer thật. Nếu gộp dữ liệu để ẩn danh thì sinh nguồn demo hợp lệ, đối chiếu aggregate/cohort và ghi phần số liệu thay đổi.
3. Country/carrier/SKU dùng mã công khai đã kiểm hoặc alias đồng bộ. Nếu đổi danh tính tuyến thì cấu hình model/top10/selection demo phải tương thích; không đổi cấu hình M2/M05 gốc. Giữ train/validation/test và không dùng test để chọn lại model.
4. Tạo DB demo mới và seed kho/danh mục/policy/scenario/parents/run ban đầu bằng UUID/hash/provenance mới. Profile hiện tại fixed ROP/days/fixed quantity, trade_v2; tồn/nhập/ETA có nhãn giả định. Có source/forecast cha sẵn để thử nhanh, đồng thời tạo source/forecast mới vẫn hoạt động.
5. Tổng 30 ngày đã loại khỏi demo theo yêu cầu03/11/2026; không cần package/bundle/receipt monthly để triển khai H14.
6. Kiểm cả nguồn seed và chuỗi source mới → forecast mới → inventory mới; kể cả import lại nguồn cùng nội dung và quan hệ nguồn H14. Chạy verifier, đối chiếu DB/API/CSV. Không gắn kết quả tính sẵn của nguồn khác vào run mới.
7. Kiểm DB/JSON/snapshot/CSV/error/log/bundle để không lộ ID gốc, secret, đường dẫn cá nhân hoặc raw download. Giữ snapshot/hash bằng chứng local nguyên; bản demo có nhãn dẫn xuất, không nhận số/hash bằng bản gốc nếu đầu vào đổi.

Gói dự kiến upload có danh sách tệp/trường, size/hash và kiểm ẩn danh cụ thể. CHG089/D2 thực hiện riêng nguồn/seed/run/reset trên local; chưa upload hoặc tạo tài nguyên cloud. Không đưa package Tổng30 vào gói demo; giữ bằng chứng nghiên cứu gốc riêng.

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

Gói seed/artifact/export demo cũng phải được dựng từ nguồn đã xử lý, không mang theo bảng doanh thu/giá gốc từ kết quả cũ. Giá trị0 có nhãn placeholder demo, không diễn giải thành giá hoặc doanh thu thực bằng0. Nguồn dẫn xuất có SHA/provenance mới; không sửa hash hoặc giá trị trong run gốc. Quy tắc này đã được triển khai bởi công cụ exportD2; nguồn gốc giữ nguyên.

## 4. Code D1–D3 và cổng kiểm hosting D4

| Phần | Việc cần làm | Kiểm |
| --- | --- | --- |
| Settings | Origin HTTPS theo môi trường, PostgreSQL psycopg/TLS và cấu hình demo riêng | Từ chối cấu hình sai/trỏ appDB; không lộ secret |
| Launcher | Quản lý API + worker cùng release/disk và toàn bộ process con | Worker chết không báo khỏe; shutdown/restart không sót hoặc trùng process |
| Queue/quota | Queue/advisory lock cũ; một job chạy, giới hạn queue/tần suất/request/retention | Backend kiểm nguyên tử cả direct Render API, trả lỗi và thời gian thử lại rõ |
| Forecast compute | Kiểm ProcessPoolExecutor(max_workers=3) hiện có; demo đã kiểm1process tính toán và giới hạn thread model | Đo RSS/thời gian nguồn/forecast/inventory; không đổi model/công thức/selection |
| FE | Giữ form/tạo run và giao diện hiện tại; tiến độ/queue/error/retry đã kiểm localD3 | Không thêm banner theo yêu cầu; hai cửa sổ/409/double-submit/Back/reload/mobile đúng |
| Routing | Giữ /api/v1; Vercel rewrite cho fetch và CSV, origin tường minh | GET/POST/PATCH, Idempotency-Key, query/status/lỗi/export headers qua proxy |
| Health | Health nhẹ, readiness kiểm DB/schema/disk/gói và worker heartbeat | Phát hiện worker/DB/disk lỗi thay vì chỉ API trả200 |
| Seed/reset | Lệnh vận hành riêng chỉ cho DB/path demo, maintenance/drain | Từ chối appDB và tệp bằng chứng; restore DB+artifact đồng bộ |

API/worker dùng role đọc/ghi dữ liệu demo, không có superuser/CREATE DATABASE/DDL; migration/reset dùng credential vận hành riêng. Khách không cần đăng nhập theo lựa chọn đã chốt. CORS không phải xác thực hoặc ngăn script gọi API trực tiếp; quota/request limits phải đặt ở backend, không chỉ disable nút.

Giới hạn local D3 đã khai báo trong template/runtime và kiểm bằng benchmark; kiểm lại tài nguyên hosting ở D4 trước deploy. Không âm thầm giảm horizon/cohort, đổi model hoặc trả complete khi chưa chạy. Job giới hạn/gián đoạn có trạng thái/lý do và retry hợp lệ. Không thêm quota tài khoản khi không có tài khoản.

## 5. Cấu hình runtime cần kiểm trên hosting free

| Thành phần | Cấu hình | Ghi chú |
| --- | --- | --- |
| Backend thử đã chạy local | Root repo, Python3.12, một API/worker, cổng8041 | Cần cả src/, M2/, data/configs và web/backend/configs; template Render trả phí không được áp dụng |
| Build | python -m pip install -r web/backend/requirements.txt && python -m pip install --no-deps -e web/backend | Dependencies hiện có; package yêu cầu Python>=3.12,<3.13 |
| Start | `python web/backend/scripts/demo_stack.py` quản lý Uvicornfactory0.0.0.0/PORT và worker | Có ởD1; không migrate/seed/reset khi boot, không mở process cho mỗi request |
| Disk | Ví dụ /var/data/sigma-demo, nguồn source/data/, run outputs/m3/ | Run dưới disk theo path resolver; nguồn immutable, artifact phát sinh |
| Postgres thử riêng | Cluster mới127.0.0.1:55433, DBsigma_demo, schema0008 | Restore D2 khớp18bảng/154artifact, không nối DBapp/D3; không public cổngDB |
| Env | M3_MODE=demo, M3_DEMO_ROOT, M3_DATABASE_URL, M3_FRONTEND_ORIGIN, M3_SOURCE_ROOT, M3_OUTPUT_ROOT; quota/compute ởD3 | Chung cho API/worker, server-only; DBsigma_demo/test, rootdemo riêng, không copy .env local |
| Vercel đã deploy | Root web/frontend; Node24 theo CI; npm ci; npm run build; output dist | Build READY; hash router không cần SPA catch-all; giữ bảo vệ Vercel trong staging |
| Proxy/domain chưa nối | /api/:path* tới backend /api/:path* khi có HTTPS cloud free đã kiểm | Kiểm writes/CSV; không cache API mutable như asset; origin riêng, không wildcard mọi preview |

Không cần mua domain để trình diễn. Biến VITE_* có thể vào bundle công khai, không lưu secrets. External rewrite là khả năng của Vercel; lệnh/path/launcher ở đây là thiết kế project cần kiểm Linux/cloud. [Vercel rewrites](https://vercel.com/docs/routing/rewrites), [environment variables](https://vercel.com/docs/environment-variables), [Render Python](https://render.com/docs/python-version).

## 6. Ngân sách bắt buộc0

Chỉ dùng gói free; không nâng cấp, mua domain hoặc dùng trial tài nguyên trả phí. Frontend tĩnh Vercel Hobby đã build/deploy; không dùng tính năng Pro. Mục đích project cá nhân/phi thương mại theo [Hobby docs](https://vercel.com/docs/plans/hobby). Theo yêu cầu mới04/11, bản thử được phép phụ thuộc máy cá nhân; dữ liệu riêng giữ trên disk qua restart, link tạm quaQuickTunnel. Nếu sau này cần online khi máy tắt thì chọn lại runtime, không tự mua tài nguyên.

| Phương án | Trạng thái | Giới hạn |
| --- | --- | --- |
| Render có persistent disk | Không được dùng | Cần trả phí, trái yêu cầu hiện tại |
| Render Free | Không chọn cho backend đầy đủ hiện tại | Không persistent disk, mất file sau restart/sleep; DB Free hết hạn30ngày |
| Backend máy cá nhân + Quick Tunnel | Đã được chọn và triển khai thử04/11 | Máy bật/có mạng/khôngsleep, link đổi khi mở lại; không có SLA |
| Oracle Always Free A1 | Ứng viên cũ, không cần cho bản thử local | Chưa có tài khoản/resource hoặc kiểmARM; không dùng credit trial/PAYG |

Render Free ngủ sau15phút, file thay đổi mất khi restart/sleep; không ping để lách ngủ. [Render Free](https://render.com/docs/free). Oracle hiện công bố tổng2OCPU/12GB A1 và200GB boot/block Always Free trong home region; có thể thiếu capacity hoặc thu hồi VM idle, không có SLA. [Tài nguyên Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). Không coi đây là cam kết uptime hoặc ARM đã tương thích.

Oracle yêu cầu người dùng tự xác minh danh tính bằng thẻ, có thể có khoản giữ tiền xác minh tạm thời; chưa được người dùng chấp nhận. [FAQ đăng ký](https://www.oracle.com/cloud/free/faq/). Không cần tiếp tục đăng ký Oracle để thử phương án local đã được cho phép. Bản thử đã có backend thật, không chỉ frontend; đây chưa là bằng chứng online độc lập máy cá nhân.

<a id="steps"></a>
## 7. Lộ trình mới

| Bước | Công việc và đầu ra | Điều kiện hoàn tất |
| --- | --- | --- |
| D0 — chất lượng | Giữ kiểmS25/C00 đã có, C00 mặc định | Đã xongCHG086; không chạy lại/tích hợpS25 ở lượt này |
| D1 — nền demo đầy đủ | Settings/launcher API-worker cùng disk, health/readiness, cấu hình hosting mẫu; bỏ banner theo yêu cầu | Boot/shutdown/restart Windows-Linux với synthetic; không thay chức năng bằng chỉ đọc |
| D2 — dữ liệu và khôi phục | Nguồn20cột đã ẩn danh, seedDB/policy/scenario/parents/kết quả, manifest/hash và reset | Chuỗi import/forecast/inventory từ đầu trên DBdemo; kiểm ẩn danh, reset DB+artifact đạt |
| D3 — kiểm chức năng/tài nguyên | Hai khách, versionconflict/queue/quota/retry, CSV/chart/lifecycle, benchmark và mức giới hạn | Python/React/build/pipcheck; browser1440/390px; verifier độc lập; retention không phá run cha |
| D4 — triển khai thử | Vercel frontend cũ READY; bản thử UI/API/worker quaQuickTunnel, Postgres/seed riêng trên máy | Theo phạm vi mới: máy mở mới dùng được, ngân sách0; seed/ready/jobtồn/API/CSV/restart đạt; chưa nghiệm thu đầy đủ D5 |
| D5 — online/công khai | Đã kiểm chuỗi run mới thật, cấu hình/lifecycle/frozen/CSV, hai phiênUI, directAPI/QuickTunnel/restart/restore | Đạt04/11 cho demo khi máy mở; snapshot15run giữ riêng, live8run/8slot; bằng chứng URL/codeSHA/hashes cùng release; chưa kiểm nhiều browser engine |
| D6 — bàn giao vận hành | Reset/backup/restore/rollback, chẩn đoán queue/worker, hạn mức/chủ tài khoản | Người vận hành dựng lại được demo; không tự đóng R05/R07/T14 |

**Hiện tại:** D0 vàD1 hoàn tất; D2 đã kiểm nguồn20cột/giá0, seed/parents/ba loại inventory, API/CSV vàreset. [Bàn giaoD2](../development.md#handoff-chg089-d2). Tổng30 đã bỏ khỏi phạm vi demo theo yêu cầu mới; D2 không còn phụ thuộc bàn giao ngoài này. Không migrate/seedDBapp, upload, trả phí hoặc deploy trongD2. Code nghiên cứuCHG086 vẫnlocal/ngoài stage; không thêm banner. [Công cụ và giới hạn](../../web/backend/configs/DEMO_RUNTIME.md).

<a id="acceptance"></a>
## 8. Tiêu chí demo hoàn chỉnh

- Khách không đăng nhập chỉnh được kho/policy/scenario/lifecycle theo luồng hiện có. Khách khác thấy thay đổi sau refetch; cùng version bị409 đúng. Theo yêu cầu03/11/2026 không thêm banner/thông báo demo dùng chung.
- Tạo source từ bộ demo, forecast mới và cả3loại run tồn; queue/progress/error/retry và output thực, không chỉ xem run tính sẵn. H14 vận hành, threshold/depletion giữ riêng; không có Tổng30 trong demo.
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
