# M3 — cấu trúc mã nguồn và tích hợp

**Tính policy bước11 CHG-068 — 25/10/2026:** inventory/service có2mode SS và2mode ROP, simulation chọn lịch sử causal theo decision origin, independent verifier tự đối soát từng dòng. Mode đã lưu từ bước10 nay chạy được, không guard tạm; API/schema13bảng/FE/default legacy giữ, cấu trúc web của CHG-072 giữ. [Công thức và ví dụ](01-functional-spec.md#configurable-calculation-step11), [kiểm và bàn giao](../../docs/development.md#handoff-chg068-step11). Bước12–15 chưa bắt đầu; các trạng thái trước bước11 bên dưới là checkpoint lịch sử.

<a id="web-layout-chg072"></a>
## Cấu trúc thực CHG-072 — 25/10/2026

Theo yêu cầu trước bước11, code ứng dụng nằm trong web; M3 chỉ giữ Markdown đặc tả, protocol và hướng dẫn. Đây là chuyển vị trí sau bước10, không triển khai bước11–15.

```text
web/
  frontend/           index.html, package/lock, public, src, tests, tsconfig, vite.config
  backend/
    src/              main/worker/cli/models, core và8module hiện có
    configs/          m3-profile.json, acceptance-30d.json, .env.example
    research/         daily_validation.py, daily_panel.py
    scripts/          launcher API/worker/stack, load_env.ps1
    migrations/       0001_m3, 0002_policy
    tests/            kiểm BE/DB/research hiện có
    .env              local ignored, chuyển nguyên byte từ M3/.env
M3/
  docs/               đặc tả và research.md (protocol nghiên cứu)
  *.md                README/IMPLEMENTATION/ACCEPTANCE/MONTHLY/SUBMISSION
```

FastAPI và launcher đọc web/frontend/dist. CI npm working-directory/cache theo web/frontend; profile/monthly acceptance đọc web/backend/configs, không giữ fallback đường M3 cũ. load_env.ps1 mặc định web/backend/.env; tên biến/DB/distribution vẫn sigma_m3/M3 như trước. Hai nghiên cứu chạy từ root bằng python -m web.backend.research.daily_validation hoặc daily_panel; PROJECT_ROOT dùng chung giữ output/requirements tại root. Không thêm dependency/package wrapper/symlink.

FE source/tests/package-lock và10file build giữ byte; config JSON/env giữ byte.144Python và34React/build trước/sau đạt,1005protectedhash nguyên; AST9file Python chỉ đổi đường/import/root. [Bàn giao và giới hạn](../../docs/development.md#handoff-chg072). Các cây cũ bên dưới là checkpoint lịch sử trước CHG-072.


**Backend bước10 — 25/10/2026:** configuration models/schemas/service/context thêm persistence policy parameters; core/run_context thêm default vào bản diễn giải legacy, không ghi snapshot; policy_at chặn mode chưa có công thức. Alembic0002_policy thêm5cột/5check trên supplier_item_policies, vẫn13bảng. [Schema](02-data-model.md#policy-persistence-step10), [bàn giao](../../docs/development.md#handoff-chg068-step10). Không thêm module/dependency, FE/nghiệp vụ tính toán giữ bước9; bước11–15 chưa bắt đầu.

**Frontend sau bước9 CHG-068 — 25/10/2026:** FE vẫn M3/frontend; App ghép6pages với AppLayout/Sidebar/Header/ContextFilters, state/effect ở useAppContext. useConfiguration giữ ghi cấu hình; form policy/scenario và3drawer tách component. index.css giữ byte của styles.css, import tại main. Không dependency/nghiệp vụ mới. [Cây thực](04-frontend-spec.md#step9-actual), [kiểm và bàn giao](../../docs/development.md#handoff-chg068-step9). Backend/dữ liệu không đổi; bước10–15 chưa bắt đầu.

<a id="step7-actual"></a>
## Cấu trúc thực sau bước7 CHG-068 — 25/10/2026

`web/backend/src` hiện có4entry/registry main.py, worker.py, cli.py, models.py; `core/` và8module catalog/configuration/forecasting/inventory/purchasing/alerts/runs/reporting. Không còn source trong api/services cũ, không giữ shim. Phần vừa chuyển:

```text
modules/inventory/
  models.py           InventoryDaily, InventoryEvent
  service.py          quantity/vector14/PolicyValues/recommend/eta/fulfill_day
  simulation.py       pure_window và persist replay/projection
  seeding.py          giả định tồn/chính sách/kịch bản được khai báo
  schemas.py          WorkspaceFilters
  router.py           workspace và inventory HTTP
modules/purchasing/
  models.py           Replenishment
  schemas.py          PurchasingFilters
  service.py          purchasing_data, lịch sử nhận hàng theo as-of
  receipts.py         receive_due, transaction lock/idempotent receipt
  router.py           workbench, CSV, replenishments HTTP
modules/alerts/
  models.py           Alert
  schemas.py          WholeRun
  service.py          project/replay_metrics/opportunity_breakdown
  router.py           alerts và alert-opportunities HTTP
models.py             chỉ đăng ký13model chung core.db.Base cho Alembic
```

Reporting giữ Filters/dataset/context/metric/CSV dùng chung và result_response HTTP adapter; router các module dùng lại adapter này. Runs giữ verifier độc lập. Không thêm tầng service/repository/queue hoặc công thức thứ hai. Main chỉ thêm wiring router alerts; worker/CLI đổi import module,6launcher giữ nguyên. Packaging chỉ tìm core/modules và4py-modules, không gói api/services cũ.

Đã kiểm9snapshot synthetic lấy từ203e506 trước tách, ledger/event/order/alert/summary khớp canonical hash; toàn bộ kiểm tại [bàn giao bước7](../../docs/development.md#handoff-chg068-step7). API/13bảng/DDL và snapshot cũ giữ nguyên. Bước8–15 chưa bắt đầu. Các cây dưới đây là checkpoint lịch sử hoặc thiết kế tương lai.

<a id="step6-actual"></a>
## Checkpoint sau bước6 CHG-068 — 25/10/2026

Đã tách forecasting/runs/reporting từ checkpoint4abdc8a. Cây thực dưới `web/backend/src/`:

```text
main.py / worker.py / cli.py          entry point giữ nguyên giao diện
models.py                            registry13bảng +4model tồn chờ bước7
core/serialization.py                clean_json dùng chung
modules/
  catalog/ / configuration/          phần đã tách ở bước5
  forecasting/
    models.py                        DailySales, RouteForecast, ItemForecast
    ingestion.py                     audit/import/dedup nguồn
    service.py                       validation/selection/forecast46
    allocation.py / m2_adapter.py     phân bổ causal/tái dùng M2
  runs/
    models.py / schemas.py            Run/RunCreate
    service.py                       enqueue/idempotency/progress
    router.py / verification.py       HTTP run/đối soát độc lập
  reporting/
    schemas.py / service.py           filter/context/dataset/metric
    router.py                        bảng kết quả/chẩn đoán/CSV
    monthly.py / monthly_router.py    benchmark30 read model/API/CSV
api/                                 workspace/purchasing, chờ bước7
services/                            inventory/simulation/alerts/receipts/seeding
```

`models.py` đăng ký đúng một `core.db.Base`; alias model tại registry phục vụ Alembic. Caller nghiệp vụ dùng model của module trực tiếp. `RunCreate` chuyển vào runs/schemas.py, bỏ schemas.py ở root và cập nhật packaging thành4py-modules. Không giữ shim import cũ; entry point worker/CLI và6launcher không đổi giao diện. `progress` chuyển runs/service để simulation dùng chung; JSON serialization thuộc core.

Reporting giữ các view đọc kết quả và CSV hiện có, kể cả tồn/cảnh báo dùng chung; worker vẫn dispatch cùng service với CLI/API. Không thay phép tính, ledger, API, schema, dependency hoặc snapshot. Bước7–15 chưa bắt đầu. [Kiểm và bàn giao](../../docs/development.md#handoff-chg068-step6). Các cây phía dưới ghi checkpoint lịch sử hoặc đích tương lai.

<a id="flat-backend-chg071"></a>
## Checkpoint backend trực tiếp trong src — CHG-071, 24/10/2026

Theo yêu cầu mới, bỏ tầng sigma_m3; worker ở cùng backend, launcher gom về web/backend/scripts. Cấu trúc sau thay đổi:

```text
web/backend/
├── src/
│   ├── main.py
│   ├── worker.py
│   ├── cli.py
│   ├── models.py
│   ├── schemas.py
│   ├── api/
│   ├── core/          # Settings/PROFILE, DB/Base, errors/hash/context
│   ├── modules/       # catalog/configuration đã tách ở bước5
│   └── services/      # Phần nghiệp vụ còn chờ bước6–7
├── scripts/           # load_env/local_stack/start_api/start_worker/start_m3/stop_m3
├── migrations/
├── tests/
├── pyproject.toml
├── requirements.txt
└── alembic.ini
```

Setuptools khai báo5py-modules main/worker/cli/models/schemas và4nhóm package api/core/modules/services từ src. Không tạo backend package tên src vì root repo đã có package src của M2. PROFILE chuyển từ __init__ cũ vào core/settings.py; không đổi giá trị. Import Python và entry point dùng tên trực tiếp, không giữ shim sigma_m3. Giữ tên distribution sigma-m3, bảng/DB sigma_m3 và biến M3_* để không đổi dữ liệu hoặc cấu hình kết nối.

PROJECT_ROOT được cập nhật theo độ sâu mới; ingestion/adapter tiếp tục đọc data/configs tại root. Launcher lấy root từ web/backend/scripts, đọc M3/.env, dùng .venv-m3 của Desktop; background process tiếp tục hidden và dừng theo PID đã ghi. Không thêm queue/service/state layer. FE build vẫn M3/frontend/dist, configs/research/env ở M3. Các cây của CHG-070/bước5 bên dưới là checkpoint trước yêu cầu bỏ namespace; bước6–15 chưa bắt đầu.

<a id="web-layout-chg070"></a>
## Checkpoint CHG-070 trước khi bỏ namespace — 24/10/2026

Lượt này chuyển backend sau bước5 vào web, dọn tài liệu cũ; chưa triển khai module bước6–7 hoặc refactor FE bước8–9. Cây thực:

```text
Sigma/
├── web/
│   └── backend/
│       ├── src/sigma_m3/  # API, core/modules/services, worker.py, cli.py
│       ├── migrations/
│       ├── tests/
│       ├── alembic.ini
│       ├── pyproject.toml
│       └── requirements.txt
└── M3/
    ├── frontend/         # FE hiện tại, chưa di chuyển/refactor
    ├── configs/          # Profile/acceptance và env example
    ├── scripts/          # Launcher API/worker và load_env
    ├── research/
    └── docs/
```

Đích sau này là web/backend và web/frontend; entry point worker tiếp tục trong package backend để dùng cùng nghiệp vụ, không tạo queue/package/service thứ hai. Không tạo folder frontend/worker rỗng ở web. Giữ namespace sigma_m3,13bảng và /api/v1. Backend dùng PROJECT_ROOT của checkout để đọc M3/configs và M3/frontend/dist; source/output env không đổi. code_digest ghi đường mới cho run mới, không sửa hash/manifest/run cũ. Cây chi tiết module sau bước5 bên dưới vẫn mô tả package đang dùng; mục1 bên dưới là đích sau các bước refactor còn lại, không phải trạng thái hiện tại.

<a id="step5-actual"></a>
## Cấu trúc thực sau bước5 CHG-068

**CHG-068 bước5 — 24/10/2026:** người dùng yêu cầu làm riêng bước5 sau checkpoint `992b8f5`. Đã tách core/catalog/configuration và rút main391→45dòng; giữ26route/OpenAPI đầy đủ, DDL13bảng và giao dịch/version/snapshot. Local107Python/26React/build/pipcheck/CLI/import/Alembic/smoke đạt,845protectedhash nguyên. Commit mã `db6c1d5` đã push, SHAremote khớp và cả2workflowCI completed/success. Bước5 hoàn tất; bước6–15 chưa bắt đầu.

```text
sigma_m3/
  main.py                         factory/lifecycle/CORS/router/static,45dòng
  core/
    db.py                         engine/session, một Base và column helpers
    settings.py                   cấu hình/PROJECT_ROOT giữ đúng checkout
    errors.py                     DomainError
    schemas.py                    DTO base dùng chung
    hashes.py                     JSON/code digest và Git revision
    run_context.py                parent/checksum/source identity/snapshot maps
    http.py                       lỗi HTTP, health, record và pagination chung
  modules/
    catalog/
      models.py                   Warehouse,Item,Supplier
      schemas.py                  WarehouseUpdate
      service.py                  đọc live/frozen catalog, sửa kho có version
      router.py                   HTTP kho/item/supplier
    configuration/
      models.py                   Policy,Scenario
      schemas.py                  PolicyCreate và scenario/receipt/override DTO
      service.py                  policy/version/scenario với transaction lock
      context.py                  freeze_inventory nguyên quy tắc
      router.py                   HTTP policy/scenario
  models.py                       registry13bảng +8domain model chờ bước6–7
  schemas.py                      RunCreate chờ bước6
  api/runs.py                     route/view runs đã tách khỏi main; chưa module6
  api/,services/,worker.py,cli.py  phần còn lại, dùng import core/module mới
```

`models.py` đăng ký cả model feature và model còn lại vào đúng `core.db.Base.metadata`; Alembic nạp registry này trước kiểm. Không còn db.py/errors.py/settings.py ở root package hoặc services/catalog.py/context.py; callers/tests/scripts/research đã đổi import. Không tạo shim hoặc module tương lai rỗng.

SHA256 canonical của toàn bộ OpenAPI và DDL table/index được ghi golden từ code992b8f5 trước refactor;6test contract đạt, trong fullsuite107Python.22định nghĩa hàm/model/DTO/helper di chuyển khớp AST cũ; kiểm3thứ tự import từ process mới không vòng lặp. Default source/output root không lệch sau chuyển settings; router không dùng session global chung giữa hai app. Các cây có chữ dự kiến ở bên dưới thuộc thiết kế/checkpoint cũ; chỉ cấu trúc trên đã thực hiện trong bước5.

Phần forecast/runs/reporting, inventory/purchasing/alerts và FE chưa tổ chức lại theo bước6–9. Core có helper đọc/kiểm run dùng chung; điều đó không tự hoàn tất module runs hoặc thay forecast/ledger.


**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo pages, layouts và component dùng chung (CHG-069), sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Đích BE: `core/` cho settings, DB/Base, lỗi/hash/run context; `modules/{catalog,configuration,forecasting,inventory,purchasing,alerts,runs,reporting}`. Main chỉ bootstrap/router; worker/CLI dùng cùng service; model đăng ký một metadata cho Alembic. Giữ module nhỏ, không thêm repo/service factory/queue mới. FE đích theo pages/layouts/components và các tầng hỗ trợ của [CHG-069](04-frontend-spec.md#frontend-target-chg069), chưa refactor code FE. Gỡ host/adapter/cloud transport/build/dependency Streamlit, giữ artifact/HTML/notebook/CLI M2.

[Kế hoạch CHG-068 và cổng từng bước](../../docs/planning/PLAN.md#chg-068).

**Cập nhật M05/E93 — 20/10/2026:** [R05 tổng30 và implementation hiện hành](../MONTHLY.md) thay cổng độ chính xác ngày bằng tổng D+1…D+30 theo mentor do người dùng thuật lại. Đã đối soát 10/10≤20% hồi cứu. Benchmark chỉ đọc có manifest/source/target/hash riêng, API/UI/CSV; không thêm bảng DB hoặc thay forecast tồn H14. Các mục R05 ngày dưới đây mô tả thiết kế trước M05; A08 và nghiệm thu mentor vẫn tách riêng.

**E91 đã triển khai:** services/alerts.py tính chẩn đoán hậu kiểm, api/results.py phục vụ GET alert-opportunities; FE AlertOpportunity dùng context theo run. M3/research/daily_validation.py riêng ngoài worker/adapter/selection phục vụ; outputs private, không thêm bảng DB. [Protocol nghiên cứu](research.md).

**Hiện hành E90:** ứng dụng đã có code và fullrun local theo profile này. Xem [implementation, số kiểm thực và giới hạn](../IMPLEMENTATION.md). Nội dung E76/E89 có chữ “dự kiến/chưa triển khai” bên dưới là lịch sử thiết kế/checkpoint; không dùng làm trạng thái hiện hành hoặc bằng chứng chạy. R05/R07/T14 vẫn mở.

**Cập nhật implementation E89:** E89: backend/settings/models/migration/services nền/workerimport/CLI source+seed/scripts đã có; phần forecastadapter/fullreplay/frontend vẫn dự kiến. Hạn chế chỉMarkdown của CHG048 thuộc lượt tài liệu cũ, đã được yêu cầu implementation thay thế. [Phạm vi thực](../README.md#implementation-e89). Các nhãn “chưa có/dự kiến” bên dưới là trạng thái đặc tả ban đầu, chỉ được thay thế trong phần đã liệt kê.

**Trạng thái:** cây dự kiến để implement sau bộ tài liệu. Lượt CHG-048 chỉ tạo/sửa Markdown. Không tạo folder rỗng, scaffold, migration, package.json hay sửa requirements trong lượt này.

## 1. Stack và cấu trúc

Đích triển khai: Python3.12 cho đường M2 đã kiểm local; FastAPI/Pydantic2, SQLAlchemy2, psycopg3, Alembic; PostgreSQL18 local; React/TypeScript/Vite/Recharts. Khi bắt đầu code, khóa patch versions đã cài/kiểm trong dependency files, không sửa môi trường M2 đã khóa để viết tài liệu. BE có requirements riêng kế thừa root requirements với constraints chung; FE có package-lock.json.

```text
web/                                # ĐÍCH sau các bước refactor còn lại
├── backend/
│   ├── src/
│   │   ├── main.py
│   │   ├── core/
│   │   ├── modules/
│   │   │   ├── catalog/
│   │   │   ├── configuration/
│   │   │   ├── forecasting/
│   │   │   ├── inventory/
│   │   │   ├── purchasing/
│   │   │   ├── alerts/
│   │   │   ├── runs/
│   │   │   └── reporting/
│   │   ├── worker.py
│   │   └── cli.py
│   ├── scripts/                    # Launcher API/worker đã chuyển ở CHG-071
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── alembic.ini
└── frontend/                       # Chưa di chuyển, còn M3/frontend
    ├── src/
    │   ├── components/
    │   ├── config/
    │   ├── hooks/
    │   ├── layouts/
    │   ├── pages/
    │   ├── services/
    │   ├── types/
    │   ├── utils/
    │   ├── App.tsx
    │   ├── main.tsx
    │   ├── index.css
    │   └── vite-env.d.ts
    ├── tests/
    ├── package.json
    ├── package-lock.json
    └── vite.config.ts
```

Cấu trúc thực hiện tại xem đầu tài liệu: backend đã ở web, mới tách core/catalog/configuration; các module còn lại là bước6–7, FE theo bước8–9 và CHG-069. Docs/configs/research/scripts/env còn ở M3, không nằm trong package hoặc tự tạo bản sao ở web.

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
python -m cli import-orders --source-key orders_snapshot
python -m cli forecast --source-run <uuid> --mode replay
python -m cli simulate --kind policy_replay --forecast-run <uuid> --scenario-id 1
python -m cli verify --run-id <uuid>
python -m worker
```

CLI tạo/đọc run cùng contract/idempotency API; tùy chọn --wait trả exit0 chỉ khi complete. Không có lệnh gửi đơn thực. Launcher đích mở API127.0.0.1:8000/FE127.0.0.1:5173/worker; Windows background process hidden. Dừng đúng PID do launcher tạo, không kill mọi python/node. Sau build FE có thể serve static local qua FastAPI; dev dùng Vite.

## 5. Database và local setup dự kiến

Alembic tạo13 bảng/constraints/index theo02; không migrate DB M2 vì M2 đang dùng artifacts. Thử migration trên database giả mới và upgrade revision trước. Source import idempotent source hash + target version, không cộng quantity lần hai. DB app role chỉ quyền cần cho schema M3.

Trình tự sau khi được giao code: môi trường Python3.12 riêng → dependency khóa → PostgreSQL/database → Alembic → seed giả → import CSV local → forecast → replay/verify → build FE → launcher. Khi đó README ghi lệnh thực đã chạy; cây/lệnh dự kiến ở đây chưa chứng minh môi trường hoạt động.

## 6. Kiểm và mở rộng

Pytest cho phép tính/adapter, PostgreSQL thật cho DB integration, Vitest/RTL và Playwright luồng chính FE. Smoke dùng injected predictor số biết trước; full ML/replay local là nghiệm thu riêng có manifest/metrics. Không chạy model để sửa MD.

Chỉ thêm multi-supplier selection/chuyển kho/auth nhiều người/queue phân tán khi có yêu cầu và tác động được duyệt. Theo dõi bằng Txx/PLAN hiện hữu, không tạo task system khác. Toàn bộ source ở cây trên là đích thiết kế, không nhận đã viết code.
