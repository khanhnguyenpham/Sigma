# M3 — cấu trúc mã nguồn và tích hợp

**E91 đã triển khai:** services/alerts.py tính chẩn đoán hậu kiểm, api/results.py phục vụ GET alert-opportunities; FE AlertOpportunity dùng context theo run. M3/research/daily_validation.py riêng ngoài worker/adapter/selection phục vụ; outputs private, không thêm bảng DB. [Protocol nghiên cứu](../research/README.md).

**Hiện hành E90:** ứng dụng đã có code và fullrun local theo profile này. Xem [implementation, số kiểm thực và giới hạn](../IMPLEMENTATION.md). Nội dung E76/E89 có chữ “dự kiến/chưa triển khai” bên dưới là lịch sử thiết kế/checkpoint; không dùng làm trạng thái hiện hành hoặc bằng chứng chạy. R05/R07/T14 vẫn mở.

**Cập nhật implementation E89:** E89: backend/settings/models/migration/services nền/workerimport/CLI source+seed/scripts đã có; phần forecastadapter/fullreplay/frontend vẫn dự kiến. Hạn chế chỉMarkdown của CHG048 thuộc lượt tài liệu cũ, đã được yêu cầu implementation thay thế. [Phạm vi thực](../README.md#implementation-e89). Các nhãn “chưa có/dự kiến” bên dưới là trạng thái đặc tả ban đầu, chỉ được thay thế trong phần đã liệt kê.

**Trạng thái:** cây dự kiến để implement sau bộ tài liệu. Lượt CHG-048 chỉ tạo/sửa Markdown. Không tạo folder rỗng, scaffold, migration, package.json hay sửa requirements trong lượt này.

## 1. Stack và cấu trúc

Đích triển khai: Python3.12 cho đường M2 đã kiểm local; FastAPI/Pydantic2, SQLAlchemy2, psycopg3, Alembic; PostgreSQL18 local; React/TypeScript/Vite/Recharts. Khi bắt đầu code, khóa patch versions đã cài/kiểm trong dependency files, không sửa môi trường M2 đã khóa để viết tài liệu. BE có requirements riêng kế thừa root requirements với constraints chung; FE có package-lock.json.

```text
M3/
├── README.md
├── docs/                           # 01–06, có thật trong lượt tài liệu
├── backend/                        # Tất cả source bên dưới là DỰ KIẾN
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── src/sigma_m3/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI/CORS/lifecycle
│   │   ├── settings.py             # Env/source registry/L7/R1/H14
│   │   ├── db.py                   # Engine/session/transaction
│   │   ├── models.py               # 13 bảng SQLAlchemy
│   │   ├── schemas.py              # DTO/input validation
│   │   ├── api/
│   │   │   ├── catalog.py          # Kho/item/supplier/policy/scenario
│   │   │   ├── runs.py             # Queue/status/summary
│   │   │   └── results.py          # Forecast/tồn/alert/metric/export
│   │   ├── services/
│   │   │   ├── ingestion.py        # Audit/source version/daily sales
│   │   │   ├── m2_adapter.py       # Interface tới src/M2 hiện hữu
│   │   │   ├── forecast.py         # ML36 + final10
│   │   │   ├── allocation.py       # Weekday90/item30–90
│   │   │   ├── catalog.py          # Seed giả định/policy version
│   │   │   ├── inventory.py        # SS/ROP/IP/Q/ledger/ETA
│   │   │   ├── alerts.py           # Projection/replay14
│   │   │   ├── evaluation.py       # Metric/mẫu số
│   │   │   └── verification.py     # Manifest/coverage/bảo toàn
│   │   ├── worker.py               # Claim/phase/heartbeat
│   │   └── cli.py                  # Gọi cùng services với API
│   ├── migrations/                 # Alembic
│   └── tests/                      # Fixture giả/DB integration
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── api/                    # Typed client/DTO/context/error
│   │   ├── components/             # Filters/status/table/chart
│   │   ├── pages/                  # Sáu trang theo 04
│   │   ├── App.tsx
│   │   └── styles.css
│   └── tests/
├── configs/
│   ├── m3-profile.json             # Không raw/secret
│   └── .env.example
└── scripts/
    └── start_m3.ps1                # Launcher local sau implementation
```

Không thêm repository/service factory cho một implementation, message bus/microservices hoặc wrapper chỉ gọi một hàm. Services dùng session SQLAlchemy và transaction theo03. API/worker/CLI dùng cùng domain code. Không nhân bản M2 hoặc khôi phục toàn bộ code đã xóa từ backup.

## 2. Tái sử dụng code thực có

| Nguồn | Cách dùng dự kiến | Điều kiện |
|---|---|---|
| `src/data.py`: audit_orders/daily_sales/route_top | Audit, route stats; ingestion thêm item aggregates. | Hash nguyên, không xuất ID; quantity/status/activation giữ A08. |
| `src/evaluation.py` | Metric qua adapter. | Đúng tên cột/đơn vị; actual thiếu giữnull. |
| `src/common.py` | Hash/config/manifest helpers phù hợp. | ROOT đang trỏ repo; không gọi helper ghi outputs cũ cho M3. |
| `M2/models/weekly.py` | Prepare/fit/predict pooled46 cho ứng viên mới. | Nhãn≤cutoff, route index ổn định từ train population. |
| `M2/models/LightGBM/model.py` + variants | 5 spec gốc cho 36; orchestration selection mới ở M3. | Không sửa top10 cho pool46, không dùng final runner làm sweep. |
| `M2/models/Prophet/model.py`, families.py | Prophet riêng 36 tuyến. | Spec540/refit7/labels causal. |
| `M2/final_report.py`, focus.py, calibration.py | Import/replay10 final theo lock/protocol. | Giữ pooltop10/head LG U+; không gọi run() ghi đè run cha. |

Adapter nhận frame/bundle đã validate và cfg, trả route/model/origin/block/window/forecast/actual canonical. bundle_key từ server registry, không path tùy ý HTTP. Thiếu origin final thì orchestration gọi hàm replay với config khóa vào run M3 mới. Forecast10 import phải parity≤1e-8, lựa chọn/hash cha nguyên. ML36 không ghi M2/artifacts.

Nếu helper hardcode ROOT/output thì dùng hàm tính thuần qua adapter, không entrypoint side-effectful. Notebook sau này chỉ gọi service/CLI; không có thuật toán thứ hai trong notebook. Raw local không copy vào worktree tài liệu.

## 3. Cấu hình và artifact

Env: `M3_DATABASE_URL`, `M3_SOURCE_ROOT`, `M3_OUTPUT_ROOT`, `M3_FRONTEND_ORIGIN`; .env ignored. Source root là workspace dữ liệu local. Public profile chỉ chứa source_key/bundle_key và tham số không nhạy cảm; registry local resolve path cho key. Không trả absolute path/credential trong API hoặc manifest public.

Output mặc định `outputs/m3/<run_uuid>` ở workspace dữ liệu, thuộc outputs ignored; DB data ngoài Git. Không chọn output=M2/artifacts hoặc overwrite parent. Khi code mới thêm ignore M3/.env, outputs, frontend/dist; hiện chưa tạo các file đó.

Manifest: source/input/code hashes, revision, target/config/assumption versions, seed42, Python/library versions, parent/hash, cutoff/split/H14/L7/R1, full policy/catalog/map snapshot, selection/hash/lock time, phase/status, artifact hashes, counters/coverage/checks. Ghi staging rồi atomic rename, complete sau verify. Failed giữ log đã lọc; run cũ không tự refresh thành mới.

## 4. API, worker và CLI

main.py chỉ khởi tạo API; worker.py process riêng, một run cùng lúc với PostgreSQL advisory lock. ML tối đa3 worker nội bộ theo cấu hình M2, giới hạn thread LightGBM; không mỗi route mở thread vô hạn. FE poll status, không chờ HTTP fit. V1 một máy chưa cần Redis/Celery.

CLI đích, **chưa có implementation/chưa kiểm lệnh**:

```powershell
python -m sigma_m3.cli import-orders --source-key orders_snapshot
python -m sigma_m3.cli forecast --source-run <uuid> --mode replay
python -m sigma_m3.cli simulate --kind policy_replay --forecast-run <uuid> --scenario-id 1
python -m sigma_m3.cli verify --run-id <uuid>
python -m sigma_m3.worker
```

CLI tạo/đọc run cùng contract/idempotency API; tùy chọn --wait trả exit0 chỉ khi complete. Không có lệnh gửi đơn thực. Launcher đích mở API127.0.0.1:8000/FE127.0.0.1:5173/worker; Windows background process hidden. Dừng đúng PID do launcher tạo, không kill mọi python/node. Sau build FE có thể serve static local qua FastAPI; dev dùng Vite.

## 5. Database và local setup dự kiến

Alembic tạo13 bảng/constraints/index theo02; không migrate DB M2 vì M2 đang dùng artifacts. Thử migration trên database giả mới và upgrade revision trước. Source import idempotent source hash + target version, không cộng quantity lần hai. DB app role chỉ quyền cần cho schema M3.

Trình tự sau khi được giao code: môi trường Python3.12 riêng → dependency khóa → PostgreSQL/database → Alembic → seed giả → import CSV local → forecast → replay/verify → build FE → launcher. Khi đó README ghi lệnh thực đã chạy; cây/lệnh dự kiến ở đây chưa chứng minh môi trường hoạt động.

## 6. Kiểm và mở rộng

Pytest cho phép tính/adapter, PostgreSQL thật cho DB integration, Vitest/RTL và Playwright luồng chính FE. Smoke dùng injected predictor số biết trước; full ML/replay local là nghiệm thu riêng có manifest/metrics. Không chạy model để sửa MD.

Chỉ thêm multi-supplier selection/chuyển kho/auth nhiều người/queue phân tán khi có yêu cầu và tác động được duyệt. Theo dõi bằng Txx/PLAN hiện hữu, không tạo task system khác. Toàn bộ source ở cây trên là đích thiết kế, không nhận đã viết code.
