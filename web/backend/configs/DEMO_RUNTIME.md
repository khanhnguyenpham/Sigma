# Runtime và dữ liệu demo

D1 thêm cấu hình/launcher/probes để API và worker chạy cùng một instance. D2 bổ sung xuất nguồn ẩn danh và công cụ seed/backup/reset bên dưới. Quota/benchmarkD3 và triển khaiD4 còn chờ. Theo yêu cầu03/11/2026, không thêm banner “demo dùng chung” vào giao diện.

## Cấu hình

Mẫu [demo.env.example](demo.env.example) chỉ chứa placeholder. `M3_MODE` mặc định `local`, giữ quy tắc origin/đường dẫn local cũ. Khi dùng `demo`:

- URL `postgres://` hoặc `postgresql://` được đổi driver thành `postgresql+psycopg://`, giữ credentials/query như TLS. DB chỉ được là `sigma_demo`, hoặc `sigma_m3_test` cho kiểm synthetic; từ chối appDB `sigma_m3`.
- Origin là một originHTTPS cụ thể, không path/query/fragment/credentials/wildcard hoặc trailing slash; hai originlocalhost5173 vẫn dùng được để kiểm local.
- Khai báo `M3_DEMO_ROOT` là thư mục riêng tên `sigma-demo`. Source/output là hai nhánh tách biệt bên trong; không trỏ source vào checkout root hoặc output vào artifact ứng dụng cũ. Ví dụ source `/var/data/sigma-demo/source`, output `/var/data/sigma-demo/outputs/m3`.
- `M3_WORKER_INSTANCE` do launcher tạo mới mỗi lần boot rồi truyền cho hai process, không đặt cố định trong cấu hình cloud.

Sau khi đã có schema và góiD2 trên môi trường demo riêng, chạy từ rootrepo với Python3.12 đã cài requirements và package backend:

```sh
python web/backend/scripts/demo_stack.py
```

Launcher đọc `PORT` (mặc định8000), bindAPI0.0.0.0, chạy một worker theo queue/advisory lock cũ. Không tự migrate/seed/reset/fit lúc startup. API hoặc worker thoát làm launcher dừng cả stack và trả mã lỗi; SIGTERM/SIGINT trênLinux dừng cả hai, kể cả model child trong processgroup. Windows dùngpsutil cho đúng cây process con đã tạo. Không dùng launcher này với env ứng dụng local; launcher local cũ vẫn giữ nguyên.

## Gói nguồn D2

Source là `M3_SOURCE_ROOT/data/sigma_sim_data_orders.csv`. Lệnh exportD2 tạo `M3_SOURCE_ROOT/demo-manifest.json`; probeD1 yêu cầu tối thiểu:

```json
{
  "version": 1,
  "anonymized": true,
  "money_policy": "zero",
  "source_file": "data/sigma_sim_data_orders.csv",
  "source_sha256": "REPLACE_WITH_64_HEX_SHA256_OF_DEMO_CSV"
}
```

Launcher từ chối thiếu/khác hash nguồn hoặc disk không ghi được. Hash được cache theo path/mtime/size để probe lặp không đọc lại toàn bộCSV; nguồn demo phải bất biến trong một release. Cờ`anonymized`/`money_policy` là khai báo của gói đã kiểmD2, **không thay kiểm ẩn danh, hợp đồng20cột hoặc việc quét các cột tiền bằng0**. ManifestD2 còn có SHA nguồn cha đăng ký và hai chữ ký quantity/ngày UTC×item/số đơn, thứ tự giao dịch; import/forecast demo đối chiếu các chữ ký này. M2/local vẫn yêu cầu nguồn gốc theo protocol, không đổi model hoặc tiêu chí chọn.

Khi dataset thay đổi, tạo source/run/provenance mới và release có kiểm soát; không sửa sealed inputs hoặc hash của run cũ. [Quy tắc giá placeholder và gói demo](../../../docs/planning/RENDER_VERCEL_DEPLOYMENT_PLAN.md#demo-money-fields).

## Công cụ dữ liệu D2

Chạy từ rootrepo với package backend đã cài. Env ứng dụng dùng role chỉ đọc/ghi dữ liệu; `M3_OPERATOR_DATABASE_URL` là credential riêng cùng server/DBdemo cho init/backup/reset, không truyền vào API/worker hoặc trình duyệt. DB và hai role phải được người vận hành tạo trước; công cụ không tạo database/role. `M3_PG_BIN` trỏ thư mục pg_dump/pg_restore khớp phiên bản server, hoặc dùng PATH. Không đưa env/private logs/CSV/dump lên Git.

```sh
python -m web.backend.scripts.demo_data export --orders /PRIVATE/registered-original.csv
python -m web.backend.scripts.demo_data init
python -m web.backend.scripts.demo_data run --request /PRIVATE/source-request.json
python -m web.backend.scripts.demo_data seed --source-run SOURCE_UUID --origin 2025-09-30
python -m web.backend.scripts.demo_data run --request /PRIVATE/forecast-request.json
```

Export chỉ nhận nguồn SHA đã đăng ký, yêu cầu thư mục source mới, audit duplicate trước khi xóa tiền. Giữ20cột, quantity/status/tuyến/SKU/ngày UTC/thứ tự, thay ID/giờ trong ngày/trường thừa và tiền0; không sinh bảng ánh xạ kèm theo. Init từ chối DB đã có bảng nghiệp vụ; không dùng reset để nâng schema. Công cụ chỉ nhận `sigma_demo` (hoặc DBtest), root tên`sigma-demo`, source`root/source`, output`root/outputs/m3` và operatorrole khác app. Không dùng envlocalứng dụng.

RequestJSON nguồn: `{"kind":"source_import","as_of_date":"2025-12-31","source_key":"orders_snapshot"}`. Sau seed, requestforecast: `{"kind":"forecast","as_of_date":"2025-12-31","source_import_run_id":"SOURCE_UUID","mode":"replay"}`. Đây là worker thật qua queue hiện có; replay fit/verify toàn protocol, có thể mất thời gian. Tiếp đó dùng UUIDforecast/scenario để tạo ba loại run tồn qua UI/API hoặc requestJSON theo RunCreate hiện hành; không thay mô hình bằng kết quả mẫu.

Sau khi worker bị dừng đột ngột, khởi động lại launcher để worker lấy advisorylock và chuyển run còn `running` thành `failed/interrupted`. Giữ run và artifact cũ; gửi request mới với `retry_of_run_id` trỏ run lỗi và Idempotency-Key mới. Không sửa status hoặc codehash của run cũ. Nếu chuẩn hóa line ending hay đổi code, hoàn tất việc đó trước khi khởi động worker và enqueue retry; parent đã complete vẫn giữ provenance/hash của lần chạy trước.

### Snapshot và reset ngoại tuyến

1. Dừng launcher/API/worker và chờ mọi request/job kết thúc. Không chạy công cụ giữa request đang ghi. Markermaintenance chặn request nghiệp vụ mới và readiness; advisorylock từ chối khi worker còn chạy, không tự kill worker.
2. Chụp snapshot mới: `python -m web.backend.scripts.demo_data backup --name baseline`. Có dumpPostgres dạngcustom, bản sao toàn bộ`outputs/` và manifest SHA/count từng bảng, từng tệp, schema/source/code. Heartbeat/private diagnosticlog không vào snapshot.
3. Reset về snapshot: `python -m web.backend.scripts.demo_data reset --name baseline --confirm sigma_demo`. Lệnh xác minh hash/source/schema trước, restoreDB bằng một transaction, cấp lại quyềnapp, đối chiếu toàn bảng, đổi thư mụcoutput rồi kiểm artifact. Không dùng`--create`, không chọn DB bằng nội dungdump. Thay đổi sau snapshot sẽ mất.
4. Nếu restore bị gián đoạn, marker được giữ để API tiếp tục503. Đọc private operatorlog, giữ snapshot đã kiểm rồi chạy lại đúng lệnh với`--recover`; công cụ chỉ phục hồi cùng snapshot và dọn thư mục tạm của lần restore đó sau khi đã đối chiếu. Không xóa marker thủ công để mở dữ liệu chưa đồng bộ. Khởi động lại launcher sau khi reset thành công và kiểmready/API/verifier.

Snapshot nằm`M3_DEMO_ROOT/backups/NAME`; nguồn bất biến ở`source/` phải được sao lưu cùng manifest riêng. Snapshot chỉ dùng với schema tương thích; khác releasecode cần rehearsal lại, không nhận rollbackcode là đủ. Không có HTTPreset hoặc reset khiboot.

### Phần tổng 30 ngày chờ bàn giao

Bundle`sigma_aggregate_focus_20261018` và receipt gốc do người khác phụ trách, hiện không có trên máy này. Tổng30 không là cha của H14/inventory nên không cản demo các chức năng đó; endpoint tổng30 vẫn báo thiếu gói409, không giả kết quả hoặc bỏ hashcheck. Cần nhận bundle/receipt hợp lệ, đối chiếu route-day và tạo package gắn nguồn demo qua bước riêng trước khi trình diễn tổng30/R05. D2 chưa nghiệm thu phần này; R05/R07/T14 giữ mở.

## Probes

| Route | Ý nghĩa |
| --- | --- |
| `/api/v1/live` | Process API phản hồi; không truy vấnDB |
| `/api/v1/ready` | Schema Alembic khớp head; ởmode demo thêm disk/gói nguồn và worker |
| `/api/v1/health` | Giữ hợp đồng health cũ, gồmDBping |

Ready trả200 khi các check đều đạt, ngược lại503 với các cờboolean, không trả URL/password/path/SQL. Worker phát heartbeat cả lúc idle hoặc đang chạy job; kiểm freshness10giây, PID/create-time, releasecode và instance của lần boot. Worker chết hoặc marker cũ không làm API báo ready. Các probe mới không thêm vào schemaOpenAPI nghiệp vụ cũ. Readiness không chứng minh quota/D2quality/tổng30 đã hoàn tất.

## Hosting mẫu

- [Render template](render.demo.yaml.example) viết theo cú phápJSON hợp lệ trong YAML, kiểm được bằng schemaRender mà không thêm thư việnYAML. Đây là tệp`.example`, không phải Blueprint đang hoạt động; một webservice/disk, auto-deployoff, healthcheck`/api/v1/ready`. Rootrepo `.python-version` chọn3.12. Plan/RAM/disk là cấu hình minh họa, benchmarkD3 và ngân sách quyết định trướcD4.
- URLDB cần role ứng dụng đọc/ghi demo, không dùng owner/migration role. D4tạoDB/role riêng và thao tác migration/seed runtime có kiểm soát; mẫu không tự cấp quyền hoặc chạyDDL.
- [Vercel template](../../frontend/vercel.demo.json.example) được copy thành`web/frontend/vercel.json` ởD4 sau khi thay URLRender thực; projectroot`web/frontend`, Node24theoCI. Rewrite`/api/:path*` áp dụng cảwrites vàCSV; hashrouter giữ nguyên.
- Chưa có quota/retention/compute limit: hoàn thiện và kiểmD3 trước khi mở API công khai. D1 không phải bản đã đủ điều kiện deploy.

Tham chiếu: [Render Blueprint schema](https://render.com/schema/render.yaml.json), [healthchecks](https://render.com/docs/health-checks), [Vercel schema](https://openapi.vercel.sh/vercel.json). Schema validation chỉ kiểm cấu trúc, không phải đã provision/kiểmonline.
