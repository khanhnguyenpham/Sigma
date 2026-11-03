# Nền chạy demo D1

D1 thêm cấu hình/launcher/probes để API và worker chạy cùng một instance. Chưa chuẩn bị dữ liệuD2, quota/benchmarkD3 hoặc triển khaiD4. Theo yêu cầu03/11/2026, không thêm banner “demo dùng chung” vào giao diện; các thao tác nghiệp vụ hiện có giữ nguyên.

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

Source là `M3_SOURCE_ROOT/data/sigma_sim_data_orders.csv`. D2 phải tạo `M3_SOURCE_ROOT/demo-manifest.json` theo hợp đồng tối thiểu:

```json
{
  "version": 1,
  "anonymized": true,
  "money_policy": "zero",
  "source_file": "data/sigma_sim_data_orders.csv",
  "source_sha256": "REPLACE_WITH_64_HEX_SHA256_OF_DEMO_CSV"
}
```

Launcher từ chối thiếu/khác hash nguồn hoặc disk không ghi được. Hash được cache theo path/mtime/size để probe lặp không đọc lại toàn bộCSV; nguồn demo phải bất biến trong một release. Cờ`anonymized`/`money_policy` là khai báo của gói đã kiểmD2, **không thay kiểm ẩn danh, hợp đồng20cột hoặc việc quét các cột tiền bằng0**. D1tests chỉ dùng tệp synthetic cho infrastructure probes; chưa tạo gói nguồn demo thật.

Khi dataset thay đổi, tạo source/run/provenance mới và release có kiểm soát; không sửa sealed inputs hoặc hash của run cũ. [Quy tắc giá placeholder và gói demo](../../../docs/planning/RENDER_VERCEL_DEPLOYMENT_PLAN.md#demo-money-fields).

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
