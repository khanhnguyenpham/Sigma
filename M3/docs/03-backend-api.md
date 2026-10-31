# M3 — backend, API và worker

## CHG-079 — Supplier là carrier

`GET /api/v1/suppliers` trả các trường `id`, `carrier`, `created_at`; bỏ code/display_name/is_assumed/assumption_source của supplier. API policy giữ supplier_id để bảo toàn FK và snapshot cũ; `supplier_code` trong read model là tên carrier, thêm `carrier` để form xác định nhà cung cấp. POST policy/scenario trả 422 `supplier_carrier_mismatch` nếu chọn sai carrier; run mới cũng kiểm scenario cũ khi freeze. Import/seed dùng carrier làm khóa, không còn SUP theo ordinal tuyến. [Schema](02-data-model.md#supplier-carrier-chg079).


## Lượng cố định mỗi lần nhập sau CHG 076

POST /api/v1/supplier-item-policies nhận fixed_order_qty nguyên dương thay moq. API và cột DB cũ moq chỉ dùng đọc lịch sử; API mới từ chối MOQ hoặc thiếu lượng fixed. POST /scenarios từ chối override moq/fixed_order_qty. Run mới dùng policy thiếu lượng fixed hoặc scenario cũ có override lượng trả missing_contract_quantity, không đoán lượng hợp đồng.

Inventory/replenishments API và CSV trả fixed_order_qty từ snapshot của run; lịch sử không có giá trị này trả null và giữ moq cũ. Worker và verifier dùng fixed nếu snapshot đã khai báo; snapshot cũ giữ luật MOQ. Không sửa config_sha256/result_summary/manifest cũ.

**CHG-068 bước14 — 26/10/2026, hoàn tất:** sau cổng13 mã73d6f39/remoteSHA/2CI success, người dùng giao14. React hiển thị ROP/SS/mode/N, ngày xuống ROP riêng ngày cạn, lý do/đường projection/bảng UTC; filter/export và metric threshold riêng depletion. Workspace thêm warning_items/projected_below_rop_items đếm item duy nhất; inventory API/CSV đọc5tham số từ policy frozen, công thức fixed hiển thị đúng.245Python (3ca mới),50React (7ca mới,1worker)/build/pipcheck và browser desktop/mobile390px trên2run synthetic đạt;1027protectedhash và3app run nguyên, schema0003_threshold giữ. Commit mã37c4525b90cb361d8eeabc23c46cfc82fb39f8dc đã push thường, remoteSHA khớp và2workflowCI completed/success; bước15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật mới chứng minh45%.

<a id="warning-read-model-step14"></a>
## Read model trình bày sau bước14 — 26/10/2026

Workspace summary thêm warning_items và projected_below_rop_items bằng set item_id từ các alert đã lưu trong context/ngày; warning bỏ not_within_horizon, projected chỉ type projected_below_rop. urgent_items và các trường cũ giữ nghĩa trước đây. Hai tín hiệu cho một item vẫn warning_items=1; số dòng bảng/CSV không là số item. Không tính lại projection khi đọc run cũ.

Inventory API/CSV thêm safety_mode/safety_lookback_days/safety_factor/rop_mode/warning_horizon_days từ policy snapshot; policy legacy diễn giải defaults trong bộ nhớ. Thay live policy không đổi dữ liệu đọc từ run. Không mở rộng schema/route/filter mới ở bước14, không thêm các trường này vào dataset replenishments. [UI và kiểm](04-frontend-spec.md#warning-presentation-step14).

**CHG-068 bước12 — 26/10/2026, hoàn tất:** cảnh báo projected_below_rop/threshold_warning với predicted_threshold_date đã qua hàm thuần/simulation/worker, DTO/filter/CSV và verifier độc lập. Giữ ROP tại decision origin, chỉ receipts đã biết trước Q mới, strict < trong N ngày; metric threshold riêng depletion.242Python BE/M2 (28ca mới),34React chạy1worker/build/pipcheck/API-worker smoke đạt;9inventory golden/M2 parity và1024protectedhash nguyên. DB app đã backup/nâng0003_threshold, hash mọi cột cũ13bảng/3run nguyên, schema0diff. Commit mã14b18415014ee2867fac436e6bd7530d74b12188 đã push thường, remoteSHA khớp và2workflowCI completed/success; bước13–15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật chứng minh45%.

<a id="threshold-api-step12"></a>
## Alerts API/CSV thực sau bước12 — 26/10/2026

GET /runs/{id}/alerts dùng DTO AlertPage/AlertRow, thêm predicted_threshold_date nullable và enum projected_below_rop/threshold_warning. alert_type được whitelist below_rop/depletion/projected_below_rop; kết hợp state/as_of_date/warehouse/item/supplier/product_type/date/pagination như cũ. Filter type sai bị422; dùng filter này ở dataset khác bị422. total là số dòng tín hiệu, không phải số item duy nhất.

GET /runs/{id}/exports/alerts nhận cùng filter, xuất mọi trang cùng predicted_threshold_date, context/hash và explanation frozen. Run cũ có ngày mới null, không được sinh ngược tín hiệu mới. GET /metrics?granularity=threshold đọc metric toàn alert replay đã khóa; lọc bảng alerts không sửa mẫu số. GET /alert-opportunities tiếp tục chỉ đối soát depletion. [Định nghĩa và giới hạn](01-functional-spec.md#threshold-alerts-step12).

<a id="policy-api-step10"></a>
## Policy API thực sau bước10 — 25/10/2026

POST/GET `/api/v1/supplier-item-policies` bổ sung5trường của [schema](02-data-model.md#policy-persistence-step10). Bỏ trường ở policy POST dùng default days/forecast/28/1/7; null hoặc enum/range/nonfinite sai trả422 invalid_input theo lỗi an toàn cũ. Version/effective date/conflict409 và HTTP path không đổi.

POST `/api/v1/scenarios` nhận cùng5trường tùy chọn trong từng settings.policy_overrides: thiếu/null kế thừa policy, giá trị0 của factor là override hợp lệ. GET trả các trường đã khai báo; scenario version trước không bị cập nhật. POST `/runs` đóng băng policy hiệu lực+override vào config mới, idempotency giữ nguyên. GET run tiếp tục ẩn detailed snapshot như cũ; inventory/alerts/CSV chưa thêm field/tín hiệu mới ở bước10.

Tại checkpoint bước10, mode mới chỉ lưu và worker báo stage_not_implemented. Sau bước11, cả4tổ hợp đã chạy qua worker/independent verify; HTTP path/body và schema response giữ nguyên, inventory/CSV trả SS/ROP/S/Q được tính theo policy frozen. [Công thức thực](01-functional-spec.md#configurable-calculation-step11). Client FE hiện chưa có control mới (bước13); body policy cũ vẫn dùng defaults. Run cũ/hash nguyên; [bàn giao và kiểm](../../docs/development.md#handoff-chg068-step10).


**CHG-068 bước5 — 24/10/2026:** người dùng yêu cầu làm riêng bước5 sau checkpoint `992b8f5`. Đã tách core/catalog/configuration và rút main391→45dòng; giữ26route/OpenAPI đầy đủ, DDL13bảng và giao dịch/version/snapshot. Local107Python/26React/build/pipcheck/CLI/import/Alembic/smoke đạt,845protectedhash nguyên. Commit mã `db6c1d5` đã push, SHAremote khớp và cả2workflowCI completed/success. Bước5 hoàn tất; bước6–15 chưa bắt đầu. HTTP giữ URL, operation ID, tham số/body/schema, pagination, lỗi an toàn và idempotency. Router catalog/configuration dùng session của từng app qua Request; API runs chỉ chuyển khỏi main sang api/runs.py, chưa triển khai module runs của bước6.

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo pages, layouts và component dùng chung (CHG-069), sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Giữ `/api/v1` và API hiện hữu; policy/scenario DTO đã thêm mode/parameter tại bước10 ở trên. Alerts/filter/export đã thêm tín hiệu/ngày xuống ngưỡng tại bước12; phần trình bày workspace/UI đã triển khai tại bước14. HTTP là transport duy nhất sau bước3; không fit trong request. Các mốc refactor dưới đây là lịch sử.

[Kế hoạch CHG-068 và cổng từng bước](../../docs/planning/PLAN.md#chg-068).

**E97 — purchasing read model:** `GET /api/v1/runs/{id}/purchasing` và `/purchasing/export` chỉ đọc frozen inventory run complete. Query as_of_date, view, search, sort, page/page_size và bộ lọc kho/item/type/supplier; [contract, ngày được biết và kiểm thực](../IMPLEMENTATION.md#purchasing-e97). Tìm kiếm/tổng hợp/sort trước phân trang; export toàn bộ scope và chống công thức CSV. Không ghi receipt hoặc thêm bảng. Các API kết quả/export toàn kỳ cũ giữ nguyên cho đối soát.


**E95 bổ sung read model quản lý:** `GET /api/v1/runs/{id}/workspace` nhận as_of_date bắt buộc và bộ lọc warehouse_id/item_id/product_type/supplier_id; chỉ inventory-kind complete, kiểm frozen parent. Trả context/summary/attention/incoming/route_stock, không ghi DB hoặc tính lại policy. Lô đang về xét ngày đặt/ETA theo mốc đã biết, bỏ qua trạng thái received cuối replay khi xem lịch sử. Missing inventory giữ on_hand=null. `/metrics` và CSV metric hỗ trợ split trước phân trang. [Kiểm thực và giới hạn](../IMPLEMENTATION.md#react-management-e95).


**Cập nhật M05/E93 — 20/10/2026:** [R05 tổng30 và implementation hiện hành](../MONTHLY.md) thay cổng độ chính xác ngày bằng tổng D+1…D+30 theo mentor do người dùng thuật lại. Đã đối soát 10/10≤20% hồi cứu. Benchmark chỉ đọc có manifest/source/target/hash riêng, API/UI/CSV; không thêm bảng DB hoặc thay forecast tồn H14. Các mục R05 ngày dưới đây mô tả thiết kế trước M05; A08 và nghiệm thu mentor vẫn tách riêng.

**Hiện hành E90:** ứng dụng đã có code và fullrun local theo profile này. Xem [implementation, số kiểm thực và giới hạn](../IMPLEMENTATION.md). Nội dung E76/E89 có chữ “dự kiến/chưa triển khai” bên dưới là lịch sử thiết kế/checkpoint; không dùng làm trạng thái hiện hành hoặc bằng chứng chạy. R05/R07/T14 vẫn mở.

**Cập nhật implementation E89:** E89: đã có API nền và worker source_import; endpoint kết quả/export/catalogsnapshot, job forecast/replay và heartbeat30s chưa triển khai. Xem bảng phạm vi thực ở README. [Phạm vi thực](../README.md#implementation-e89). Các nhãn “chưa có/dự kiến” bên dưới là trạng thái đặc tả ban đầu, chỉ được thay thế trong phần đã liệt kê.

**Trạng thái:** hợp đồng dự kiến, chưa có endpoint chạy. FastAPI + SQLAlchemy + Alembic + PostgreSQL; Python tái sử dụng M2. Nghiệp vụ tại [01](01-functional-spec.md), schema tại [02](02-data-model.md), FE tại [04](04-frontend-spec.md).

## 1. Ranh giới API và dữ liệu

Base `/api/v1`; JSON UTF-8, ngày YYYY-MM-DD UTC, timestamp ISO8601 có offset. Response không có raw order/customer ID, path máy hoặc credentials. Dùng ID nội bộ M3. Quantity forecast là number hữu hạn, actual thiếu=null kèm actual_available=false. DTO không nhận trường thừa; số âm/NaN/Infinity bị từ chối.

GET danh sách nhận page≥1/page_size1…100 (mặc định50), trả `{items,total,page,page_size}`. Filter được whitelist: warehouse_id, item_id, supplier_id, product_type, date_from/date_to và state khi phù hợp; supplier filter theo policy snapshot của run. Sort cố định ngày rồi warehouse/item, có ID làm tie-break. Không dùng timezone browser đổi ngày nghiệp vụ.

Mỗi response kết quả có `context`: run_id, source_import_run_id, forecast_run_id nếu có, as_of_date, observation_end, scenario_id, target/config/assumption version, is_simulated và evaluation_limit. GET run/status không cần complete; GET kết quả bắt buộc complete. Kết quả không khớp parent/version →409, không lấy run gần nhất thay thế.

## 2. Catalog và cấu hình

| Method/URL | Input và output | Quy tắc |
|---|---|---|
| GET `/health` | status API và database reachable | Không trả thông tin kết nối nhạy cảm. |
| GET `/warehouses` | Danh sách route/city/code; filter country | Catalog hiện tại hoặc `run_id` để xem snapshot. |
| PATCH `/warehouses/{id}` | city, expected_version → warehouse version mới | Chỉ chỉnh city/nhãn giả định; route key bất biến; run snapshot cũ giữ nguyên. |
| GET `/items` | warehouse/product_type/search sku | Có first_seen_date; nhận run_id để đọc catalog snapshot. |
| GET `/suppliers` | supplier code/name/is_assumed | Seed giả định, không có contact thực. |
| GET `/supplier-item-policies` | item/supplier/effective_on | Trả lịch sử hoặc policy hiệu lực. |
| POST `/supplier-item-policies` | item_id,supplier_id,effective_from,floor,moq,safety_days,expected_version | Tạo version mới, đóng khoảng trước trong transaction; trả201; chặn chồng/hồi tố phá run. |
| GET `/scenarios` | code/version/settings/assumptions | Mỗi version bất biến. |
| POST `/scenarios` | name,code,base_scenario_id?,settings | Tạo version; cover3/7/14, multiplier≥0, receipts khai báo; L7/R1 cố định. |

Các policy field gốc canonical là `configured_rop_floor`, `moq`, `safety_days`; bước10 bổ sung5tham số theo bảng schema ở trên cho DB/DTO, control FE mới chờ bước13. effective_to được BE xác lập từ phiên bản tiếp theo, không cho FE đóng khoảng gây khoảng trống bất ngờ. Khoảng trống đã có phải báo thiếu policy; không tự lấp bằng supplier khác. Policy override hồi tố chỉ qua scenario snapshot mới, với lý do và is_assumed=true.

POST policy giả minh họa:

```json
{
  "item_id": 101,
  "supplier_id": 7,
  "effective_from": "2025-10-31",
  "configured_rop_floor": 100,
  "moq": 50,
  "safety_days": 2,
  "expected_version": 1
}
```

ID trên là ID giả trong ví dụ, không phải bản ghi nguồn. Thiếu policy/receipts/mapping phải có lỗi nêu loại cấu hình thiếu và ID M3, không in dòng order.

## 3. Run API và workflow

| Method/URL | Chức năng |
|---|---|
| POST `/runs` | Validate input/parents, tạo queued, trả202 + run_id/status_url. |
| GET `/runs` | Liệt kê status/kind/cutoff/versions/progress; không cần đọc kết quả. |
| GET `/runs/{id}` | Trạng thái, phase, counters, lỗi đã lọc, manifest summary. |
| GET `/runs/{id}/summary` | Tổng hợp run complete và metric đúng granularity. |
| GET `/runs/{id}/forecasts/routes` | Hai khối tuần, model/selection/actual/coverage. |
| GET `/runs/{id}/forecasts/items` | Forecast ngày item, share và nguồn phân bổ; aggregate=route_day nếu cần. |
| GET `/runs/{id}/inventory` | Tồn ngày, SS/ROP/S/IP/Q, config_status. |
| GET `/runs/{id}/replenishments` | Lô mô phỏng, ordered/received, quantity/ETA/supplier. |
| GET `/runs/{id}/alerts` | BelowROP/depletion/projected_below_rop, ngày xuống ROP riêng ngày cạn, giải thích/đánh giá alert replay. |
| GET `/runs/{id}/alert-opportunities` | E91: chẩn đoán toàn alert_replay complete; phân bố ngày cạn, caD+1…6, trần thời gian và ca đủ7ngày nhưng bỏ sót. Không nhận query filter; actual chỉ dùng giải thích sau replay; đối soát mẫu số với summary đã khóa. |
| GET `/runs/{id}/metrics` | Chọn granularity=weekly/allocated_daily/alert/policy, block/cadence. |
| GET `/runs/{id}/exports/{dataset}` | CSV theo dataset allowlist và filter hiện tại; download response. |

POST `/runs` cần header `Idempotency-Key` (chuỗi≤128), DTO theo kind:

| kind | Trường bắt buộc | Xử lý |
|---|---|---|
| source_import | source_key, as_of_date | source_key='orders_snapshot' trỏ path cấu hình server; audit/hash/catalog/daily_sales. Không upload raw qua HTTP. |
| forecast | source_import_run_id, as_of_date, mode | mode='replay' chạy validation→lock→test và future; mode='future' dùng selection lock đã có qua forecast_run_id. |
| policy_replay | source_import_run_id,forecast_run_id,scenario_id,period_start,period_end,as_of_date | Chuỗi liên tục; as_of=ngày trước period_start; cần forecast từng ngày quyết định. |
| alert_replay | source_import_run_id,forecast_run_id,scenario_id,period_start,period_end,as_of_date | Đợt14 không chồng lấp; origin đầu 30/09/2025 trong profile này. |
| stock_projection | source_import_run_id,forecast_run_id,scenario_id,as_of_date | Snapshot cuối origin + projection14; luôn khởi tạo seed tồn cuối cutoff từ μ28/cover_days, có nhãn giả định; không tự lấy tồn từ run khác. |

Ví dụ giả:

```json
{
  "kind": "policy_replay",
  "source_import_run_id": "10000000-0000-4000-8000-000000000001",
  "forecast_run_id": "10000000-0000-4000-8000-000000000002",
  "scenario_id": 1,
  "as_of_date": "2025-09-30",
  "period_start": "2025-10-01",
  "period_end": "2025-12-31"
}
```

Response202: `{run_id,status:"queued",status_url}`. Cùng key/body trả200 cùng run; key trùng nhưng body khác trả409. Retry lỗi phải key mới và retry_of_run_id, tạo run mới. Không có endpoint thực gửi đơn nhập/nhận hàng thủ công ởv1: worker tự tạo/nhận lô đúng kịch bản. FE có thể xem preview input trước bấm chạy, nhưng không sửa trực tiếp kết quả.

Mode future yêu cầu selection lock của run forecast complete cùng source/target/spec; dữ liệu mới phải khai báo source import mới và kiểm compatibility, không âm thầm dùng model từ nguồn khác. Profile snapshot hiện tại cutoff31/12/2025 dự báo01–14/01/2026 chưa có actual. Replay mặc định FE chọn31/10/2025 để trình bày, không gọi giám sát hiện thời2026.

## 4. Response kết quả và lỗi

Inventory row tối thiểu: item_id,warehouse_id,date,opening_qty,receipts_qty,sales_qty,fulfilled_qty,shortage_qty,closing_qty,policy_id,ss,rop_forecast,configured_rop_floor,rop,target_stock,pending_qty,inventory_position,needs_replenishment,recommended_qty,eta_if_ordered,config_status. `configured_rop_floor`/supplier lấy policy snapshot, eta_if_ordered=date+7 chỉ có khi Q>0.

Alert row: item/warehouse/as_of/type/state/predicted_threshold_date/predicted_depletion_date/lead_days/actual_depletion_date/evaluation_class/is_evaluable/exclusion_reason/explanation. explanation gồm tồn origin, vector forecast14, receipts biết trước, tham số đã áp dụng và projection ngày; số liệu đều cùng run. Không có event source IDs.

Metric row: warehouse_id hoặc item_id theo granularity, block,cadence,mape_positive_pct,mae,wape_pct,bias,expected_pairs,labeled_pairs,positive_pairs,coverage. Alert metric thêm TP/FP/FN/TN, early_numerator/event_denominator/late_count/date_mae; policy metric thêm fulfilled/sales/shortage/mean_closing. Null có null_reason.

Lỗi thống nhất:

```json
{"error":{"code":"missing_partner_config","message":"Thiếu chính sách hiệu lực cho mặt hàng.","details":{"item_id":101}},"request_id":"demo-request"}
```

| HTTP | Mã tiêu biểu | FE xử lý |
|---|---|---|
| 404 | not_found | Hiện tài nguyên không tồn tại; không đổi run tự động. |
| 409 | run_not_complete, version_conflict, policy_overlap, parent_mismatch, idempotency_conflict | Hiện lý do; phiên bản cũ yêu cầu tải lại cấu hình. |
| 422 | invalid_input, invalid_lead_time, missing_partner_config, missing_allocation_basis, insufficient_history | Chặn thao tác, chỉ trường/ID cần xử lý. |
| 503 | database_unavailable | Cho thử lại, giữ bộ lọc và không gán số0. |

Lỗi phát hiện sau khi chạy ghi run failed/error_code; HTTP GET status vẫn200 để FE đọc trạng thái. Không trả stacktrace/path/raw. Cảnh báo kiểm chất lượng đầu vào khác cảnh báo tồn hàng.

## 5. Worker, transaction và tính lặp lại

API chỉ validate nhanh và insert queued. Worker Python riêng xử lý lần lượt một run; không huấn luyện trong HTTP/BackgroundTasks. Theo [lưu ý FastAPI](https://fastapi.tiangolo.com/tutorial/background-tasks/#caveat), tính toán nặng cần tách cách thực thi; v1 một máy dùng worker + PostgreSQL sẵn có, chưa thêm Redis/Celery.

Worker giữ PostgreSQL advisory lock cố định cho một worker M3; worker thứ hai thoát có thông báo. Khi lấy lock sau restart, các run running còn sót được đánh failed/interrupted, không tự coi complete hoặc chạy lại cùng run. Claim queued cũ nhất trong transaction ngắn `FOR UPDATE SKIP LOCKED`; chuyển running, đóng băng config/parents/hash; release row lock trước tính toán. Heartbeat mỗi 30s, tiến độ theo phase/counters thực, không bịa ETA.

Phase: validate → audit/import hoặc forecast/allocate → simulate nếu cần → verify → complete. Forecast replay: validation6 ứng viên36 tuyến → persist selection lock/hash → test/future của lựa chọn đã khóa + import/replay10 tuyến final → allocation → verify. Artifacts staging cùng run; chưa complete thì FE không đọc. Một lỗi bắt buộc làm toàn run failed, không bỏ tuyến để giảm mẫu số.

Transaction lô nhập: khóa inventory_daily decision → tính Q từ pending hiện tại → insert order_key duy nhất → ghi decision. Receipt: khóa order → nếu ordered và đến ETA, tạo event receipt duy nhất, chuyển received trong cùng transaction. Chạy lại bước không cộng tồn/lô hai lần. Sales events xử lý thứ tự audit, đóng balance/day bằng kiểm tổng độc lập. Không giữ transaction DB mở trong lúc model.fit.

## 6. Local, export và giám sát

API bind127.0.0.1:8000; FE dev127.0.0.1:5173; CORS chỉ origin FE local cấu hình. Chưa có auth vì demo một máy, không mở0.0.0.0 hoặc deploy cloud theo hướng dẫn này. SQL dùng ORM/bound parameters; secret qua env local ignored. Source path chỉ do config server/CLI local chọn, không để HTTP đọc path tùy ý.

Exports allowlist: route_forecasts,item_forecasts,inventory_daily,replenishments,alerts,metrics; cùng run/filter, có nhãn mô phỏng/cutoff/version. Không export raw/daily source theo order/event trace. Escape ô CSV bắt đầu ký tự công thức khi có văn bản nhập tự do. GET export chặn failed/incomplete. Files private không thành static directory công khai.

Quan sát qua runs.status/phase/heartbeat/error_code/result_summary; mỗi run có manifest, không tích hợp hệ thống monitoring ngoài. Dashboard polling2s khi queued/running, dừng khi terminal. Các kiểm endpoint/worker/DB vẫn chưa được chạy; xem [06](06-testing-delivery.md).
