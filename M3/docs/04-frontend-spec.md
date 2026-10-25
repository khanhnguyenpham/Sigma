# M3 — đặc tả frontend

<a id="step8-actual"></a>
## Cấu trúc thực sau bước8 CHG-068 — 25/10/2026

Frontend vẫn ở **M3/frontend**, chưa chuyển sang web/frontend. Đã tách common.tsx và api/client.ts; không giữ shim hoặc barrel. Cây thực dưới src:

```text
components/
  ui/           State, Card, Table/Column, Pager, Panel, ExportButton,
                Badge (badge), DetailDrawer, PlanRequired, Icon, PageBoundary
  dialogs/      HelpDialog, RunDialog
  forecast/     MonthlyForecast
  alerts/       AlertOpportunity
hooks/          useResource.ts, useDialogFocus.ts
services/       http.ts: api, ApiError
config/         http.ts: API_PREFIX và read30s/write90s; navigation.ts: PAGES/kind
types/         api.ts: Row/Run/Page/WorkspaceData; context.ts: Context/PurchasingView
utils/          format.ts, labels.ts, url.ts (gồm readPurchasingView)
pages/          sáu trang cũ, giữ JSX và form/drawer lớn
App.tsx         giữ state/effect/layout/context; chỉ đổi import/đưa hằng ra config
main.tsx        giữ mount; chỉ đổi import PageBoundary
styles.css      giữ nguyên byte, import ở App; đổi index.css ở bước9
```

53khai báo/câu lệnh giữ AST ngoài import/export và tham chiếu3hằng HTTP có đúng giá trị cũ. App/layout và JSX/hook không đổi; client giữ Fetch API/abort/read30s/write90s/Idempotency-Key, không tự retry write. useResource giữ refresh/chặn response cũ, useDialogFocus giữ Tab/Escape/phục hồi focus. Types dùng chung được page/component import trực tiếp; không thêm router/state framework hoặc dependency.

Kiểm baseline26→30React/build,120Python baseline và9contract sau sửa;4ca mới cho bảng bàn phím, pager, CSV và focus. Smoke browser6màn hình trên DB test trống và help/Escape/focus đạt;970protectedhash và CSS nguyên. [Bàn giao](../../docs/development.md#handoff-chg068-step8). Bước9–15 chưa bắt đầu; cây đích CHG-069 và các trạng thái cũ bên dưới là thiết kế/checkpoint trước.

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo pages, layouts và component dùng chung (CHG-069), sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

<a id="frontend-target-chg069"></a>
## Cấu trúc FE dự kiến — CHG-069, 24/10/2026

**CHG-070:** đích thư mục FE sau này là `web/frontend/`; hiện code/tests/build FE vẫn tại `M3/frontend/` và chưa di chuyển. Lượt này chỉ chuyển BE vào `web/backend/`. Cách chia bên trong src giữ CHG-069.

Người dùng yêu cầu cập nhật Markdown và push trước, tham khảo cây thư mục trong ảnh và cho phép bỏ thư mục chưa cần. Đây là đặc tả cho bước8–9 CHG-068, thay đích `app/features/shared` trước đó; chưa di chuyển hoặc sửa code FE. Ảnh chỉ là tham chiếu cấu trúc, không bổ sung chức năng của project trong ảnh. Bước1–5 đã hoàn tất; bước6–15 chưa bắt đầu.

```text
web/frontend/src/
├── components/       # UI dùng chung và component nghiệp vụ tái sử dụng
├── config/           # Điều hướng và cấu hình HTTP phía trình duyệt
├── hooks/            # Tải dữ liệu, abort, focus, context run/bộ lọc
├── layouts/          # Khung ứng dụng, sidebar, header, bộ lọc chung
├── pages/            # Sáu màn hình hiện có
├── services/         # HTTP client typed gọi FastAPI
├── types/            # DTO API và kiểu context/URL
├── utils/            # Format, nhãn, ngày UTC, query string
├── App.tsx           # Ghép layout và màn hình theo URL hiện có
├── index.css         # CSS toàn cục; đổi từ styles.css ở bước9
├── main.tsx          # Mount React và import CSS toàn cục một lần
└── vite-env.d.ts
```

### Trách nhiệm và cách chuyển mã

| Đích dự kiến | Mã hiện có và trách nhiệm |
|---|---|
| `components/ui/` | Tách Table, Pager, State, Card, Panel, Badge, DetailDrawer từ `components/common.tsx`; gom Icon/PageBoundary hiện có. Component nhận props, không chứa phép tính tồn. |
| `components/dialogs/` | HelpDialog và RunDialog; dùng chung hook quản lý focus/Escape. |
| `components/forecast/`, `components/alerts/` | Đặt MonthlyForecast và AlertOpportunity hiện có vào nhóm nghiệp vụ tương ứng. Chỉ tạo nhóm khi chuyển component thực. |
| `components/configuration/` | Tách PolicyForm, ScenarioForm, PolicyOverrideEditor, ReceiptEditor khi xử lý form lớn; dùng chung PolicyFields cho policy/override. Không thêm form-builder. Các trường mode mới chỉ triển khai ở bước13. |
| `hooks/` | Tách useResource và useDialogFocus từ common.tsx; useAppContext gom run/bộ lọc/đồng bộ URL từ App. Giữ AbortController, chống response cũ, refresh và loading/error. |
| `layouts/` | Tách AppLayout, Sidebar, Header, ContextFilters từ App.tsx; layout điều phối bố cục và nhận context qua props/hook. |
| `pages/` | Giữ Overview, Inventory, Forecast, Replenishment, Alerts, Configuration. Page ghép component và dữ liệu; form, drawer, bảng lớn được tách khi có trách nhiệm riêng. |
| `services/http.ts` | Chuyển api và ApiError từ api/client.ts, dùng Fetch API hiện có; giữ abort, read30s/write90s, Idempotency-Key và không tự retry write. Giữ một client, chưa tạo wrapper cho từng endpoint. |
| `types/api.ts`, `types/context.ts` | Tách Row/Run/Page và Context/kiểu view nhập hàng khỏi client/App; bổ sung DTO cụ thể khi sử dụng, không tạo kiểu cho tính năng chưa có. |
| `utils/` | format.ts cho text/num/fmt/pct; labels.ts cho label/errorLabel; url.ts cho query/resultQuery/readContext/contextUrl/readPurchasingView. Tiện ích ngày dùng UTC, không tính lại SS/ROP/metric. |
| `config/` | navigation.ts giữ sáu ID/nhãn PAGES hiện có; http.ts giữ prefix `/api/v1` và timeout dùng chung client/export. Không đặt secret hoặc policy nghiệp vụ tại đây. |
| `App.tsx`, `main.tsx`, `index.css` | App chỉ ghép layout/page và context. Đổi styles.css thành index.css và chuyển import sang main.tsx ở bước9, giữ giao diện; chỉ tách CSS component khi thực sự cần. |

Luồng phụ thuộc: pages/layouts điều phối components/hooks; hooks gọi services; services dùng types/config; utils độc lập với UI. Không tạo import vòng hoặc đưa component riêng của một page vào thư mục chung khi chưa được tách rõ. React tiếp tục dùng state/hook và URL hiện có, không thêm router hoặc state framework.

### Các thư mục chưa cần

- `stores/`: state/run/bộ lọc hiện đủ với useState, hooks và URL; chưa cần Redux/Zustand hoặc store riêng.
- `lib/`: trách nhiệm hiện tại đã thuộc services/utils, chưa có SDK cần adapter riêng.
- `src/docs/`, `src/examples/`: tài liệu ở `M3/docs/`, fixture giả và tests ở `M3/frontend/tests/`.
- `assets/`: chỉ thêm khi có ảnh/font được import thực; favicon hiện giữ ở `public/`.
- Không tạo thư mục rỗng hoặc thêm tầng `app/`, `features/`, `shared/` bên ngoài cây trên.

### Phân bước và điều kiện giữ hành vi

Bước8 tách components/hooks/services/types/utils/config khỏi common.tsx/client tổng; cập nhật import và kiểm loading/error/abort/focus/bảng/phân trang/CSV. Bước9 tách layouts, context của App, form/drawer lớn và tổ chức sáu pages; đổi CSS theo cây trên. Mỗi bước vẫn kiểm local → commit → push → SHA remote khớp → CI đạt trước bước kế tiếp.

Giữ nguyên sáu màn hình và ID URL `overview`, `inventory`, `forecast`, `replenishment`, `alerts`, `configuration`; không đổi `replenishment` thành `purchasing`. Giữ run/ngày/bộ lọc và tab nhập hàng qua refresh/Back, chống dữ liệu cũ khi đổi context nhanh, retry đọc, hỗ trợ bàn phím/Escape/focus, mobile và export CSV. Tests tiếp tục ở frontend/tests; chỉ đổi import khi refactor thực, giữ kiểm null khác0 và lỗi mạng. Dev dùng Vite; React gọi FastAPI HTTP và build được FastAPI phục vụ local.

PolicyFields dùng chung cho policy/scenario override; chỉ hiển thị trường phù hợp mode ở bước13. Cảnh báo ở bước14 giải thích tồn/ROP/N/ngày xuống ngưỡng/ngày cạn riêng; tổng quan đếm item duy nhất. CHG-069 không đổi yêu cầu nghiệp vụ hoặc nghiệm thu R08–R09/T11–T12, R07/T14 vẫn mở.

[Kế hoạch CHG-068 và cổng từng bước](../../docs/planning/PLAN.md#chg-068).

**E97 hiện hành — cách dùng như phần mềm điều hành:** [Phạm vi và bằng chứng](../IMPLEMENTATION.md#purchasing-e97). Dãy bước E96 đã bỏ theo trả lời làm rõ của người dùng. Nhập hàng dùng purchasing read model theo ngày với3tab/search/sort/CSV/drawer. Liên kết tồn ↔ nhập ↔ cảnh báo giữ đúng SKU/context; view nhập khôi phục qua URL. Các rule/view toàn kỳ trước đó là lịch sử hoặc phục vụ API đối soát. Không thêm màn hình/phân quyền/PO thật ngoài M3.


**E96:** giao diện có ngữ cảnh SIM/gói data, bốn nút nghiệp vụ ở Tổng quan giữ run/ngày/bộ lọc và thuật ngữ nhập/cấu hình bằng tiếng Việt. Không thêm màn hình hoặc quy trình ngoài đặc tả. [Kiểm thực](../IMPLEMENTATION.md#react-management-e95).


**E95 — giao diện quản lý đã triển khai:** [Hướng dẫn và bằng chứng](../IMPLEMENTATION.md#react-management-e95). Sáu route giữ nguyên phạm vi M3; sidebar/header mới, bộ lọc chung, ngăn chi tiết SKU/cảnh báo, lịch xử lý thu gọn. Tổng quan dùng API workspace theo run/ngày/filter; màn hình forecast mặc định lượng bán tổng30, có tổng7/ngày phân bổ; bảng chất lượng/replay nằm trong details.109Python+17React/build và browser thực đã kiểm. Các đặc tả/checkpoint lịch sử bên dưới không tự thay bằng chứng hiện hành. React local độc lập với Streamlit public E94.


**Cập nhật M05/E93 — 20/10/2026:** [R05 tổng30 và implementation hiện hành](../MONTHLY.md) thay cổng độ chính xác ngày bằng tổng D+1…D+30 theo mentor do người dùng thuật lại. Đã đối soát 10/10≤20% hồi cứu. Benchmark chỉ đọc có manifest/source/target/hash riêng, API/UI/CSV; không thêm bảng DB hoặc thay forecast tồn H14. Các mục R05 ngày dưới đây mô tả thiết kế trước M05; A08 và nghiệm thu mentor vẫn tách riêng.

**E91 đã triển khai:** Cảnh báo có panel cơ hội7ngày, so tỷ lệ thực với trần thời gian của chính lượt replay; phân bố14ngày mở rộng. Số liệu toàn lượt không theo bộ lọc bảng, không thay tỷ lệ chính thức. Chỉ alert_replay complete; loading/error/null/context cũ được kiểm. Không hiển thị trên snapshot.

**Hiện hành E90:** ứng dụng đã có code và fullrun local theo profile này. Xem [implementation, số kiểm thực và giới hạn](../IMPLEMENTATION.md). Nội dung E76/E89 có chữ “dự kiến/chưa triển khai” bên dưới là lịch sử thiết kế/checkpoint; không dùng làm trạng thái hiện hành hoặc bằng chứng chạy. R05/R07/T14 vẫn mở.

**Cập nhật implementation E89:** E89: frontend vẫn chưa triển khai; API nền/database có ở nhánh implementation, chưa là UI6trang. [Phạm vi thực](../README.md#implementation-e89). Các nhãn “chưa có/dự kiến” bên dưới là trạng thái đặc tả ban đầu, chỉ được thay thế trong phần đã liệt kê.

**Trạng thái:** thiết kế React/TypeScript, chưa có UI chạy. Schema tại [02](02-data-model.md), API tại [03](03-backend-api.md). Mục tiêu là giải thích forecast → tồn → nhập/cảnh báo và cho chỉnh cấu hình, chạy kịch bản local.

## 1. Khung giao diện và context

React/TypeScript + Vite, CSS thông thường; Recharts cho đường/bars. Fetch API qua client typed; context + useState quản lý lựa chọn, chưa thêm design system/state framework. Tham chiếu [hướng dẫn TypeScript của React](https://react.dev/learn/typescript). FE không tính lại công thức tồn hoặc metric.

Sidebar sáu màn hình; header hiển thị run, kind/status, as_of_date UTC, observation_end, forecast parent, scenario/version và nhãn “Mô phỏng”. Filter chung: kho/tuyến, SKU, product_type, supplier, khoảng ngày. Supplier/city theo snapshot run; catalog hiện tại chỉ ở trang cấu hình. Đổi kho xóa SKU không còn hợp lệ; có nút xóa filter.

Run selector mặc định chỉ complete; danh sách queued/running/failed ở tổng quan mở trang trạng thái. Inventory run luôn dùng forecast_run_id của chính nó; không ghép forecast cha khác vào ledger cũ. Forecast run chưa có tồn thì trang tồn hướng dẫn tạo/chọn run mô phỏng tương thích.

Lưu context vào URL search params: run_id, warehouse_id, item_id, product_type, supplier_id, date_from/date_to. Reload khôi phục filter; ID sai báo lỗi, không tự chọn run mới nhất. Hủy request cũ bằng AbortController khi context đổi, tránh response đến trễ ghi đè.

## 2. Sáu màn hình

| Màn hình/route | Nội dung | API và thao tác |
|---|---|---|
| Tổng quan `/overview` | Run/status/phase, tuyến/item/coverage, nguy cơ cạn, shortage, tồn bình quân theo loại run. | GET runs/summary; chọn/tạo run, xem tiến độ/lỗi đã lọc. |
| Dự báo `/forecast` | Actual/forecast theo tuyến, Tổng7/Ngày phân bổ, block1/2; MAPE/MAE/WAPE/bias/coverage, model/selection_basis. | GET forecasts/routes/items + metrics. Chọn một origin, không cộng rolling windows trùng nhau thành sales độc lập. |
| Tồn kho `/inventory` | Opening/receipt/sales/fulfilled/shortage/closing, SS/ROP_forecast/floor/ROP/S/IP/Q; chart tồn và ngưỡng. | GET inventory; panel item diễn giải policy/công thức. Không coi tổng ROP nhiều SKU là ngưỡng kho dùng đặt hàng. |
| Nhập hàng `/replenishment` | Tab Khuyến nghị/Lô đang về, trigger/Q/pending/ETA/supplier/ordered/received. | GET inventory/replenishments; chạy mô phỏng mới. Không có nút gửi supplier thật hoặc sửa receipt trực tiếp. |
| Cảnh báo `/alerts` | BelowROP riêng depletion; urgent/early/already_depleted; ngày cạn/lead days; projection14 ngày. | GET alerts (explanation trong response). Replay thêm TP/FP/FN/TN, early rate và mẫu số; policy không có confusion class. |
| Cấu hình `/configuration` | Tab Kho, Supplier-policy, Kịch bản; city giả định, version/effective dates, floor/MOQ/safety, cover/receipts. | GET catalog/policies/scenarios; PATCH city; POST policy/scenario version mới. |

Chart Tổng7 vẽ theo khối7 ngày, không trình tổng khối như actual một ngày. Chart ngày ghi “phân bổ từ tổng tuần”. Bảng metric tách rolling/nonoverlap; mỗi tuyến có chất lượng riêng, không dùng mean46 che tuyến kém.

## 3. Tạo run và chỉnh cấu hình

Workflow đầu tiên: import snapshot local → forecast replay/khóa selection → policy replay hoặc alert replay. Stock projection minh họa một cutoff. Mặc định trình bày replay31/10/2025; latest cutoff31/12 dự báo01–14/01/2026 chưa actual, không gọi giám sát hiện thời2026.

Form run hiện parent/source/cutoff/scenario version,46 tuyến,L7/R1/H14; chỉ chọn parent complete tương thích. Nút chạy tạo Idempotency-Key bằng crypto.randomUUID; disable khi đang gửi; retry mạng dùng lại key/body. Đã được server nhận thì mở status, poll2s đến terminal. Retry run failed dùng key mới và retry_of, không đổi run cũ.

Policy form chọn item/supplier/ngày hiệu lực, floor nguyên≥0/MOQ nguyên≥1/safety≥0; hiện version và khoảng đang có. L7 chỉ đọc. BE kiểm overlap/cutoff/version;409 hiển thị xung đột và tải lại, không tự ghi đè. City luôn có nhãn “Giả định”, không nhận tối ưu. Receipts phải khai báo rỗng rõ hoặc nhập danh sách; thiếu khai báo khác0 lô.

Thử policy lịch sử đã được run tham chiếu bằng scenario override version mới cùng lý do, không sửa policy cũ. Run đang xem giữ snapshot; sau chạy có link sang run mới, không thay số biểu đồ cũ trong lúc job chưa complete.

## 4. Trạng thái và số liệu

| Trạng thái | Hiển thị/hành vi |
|---|---|
| Loading | Skeleton/spinner, không hiện0 tạm. |
| Empty do filter | “Không có bản ghi phù hợp”, giữ filter và cho xóa. |
| Chưa actual | “—”, tooltip chưa quan sát; actual chart ngắt; metricnull. |
| Failed/incomplete | Status/error_code, thiếu thành phần nào; không hiện dữ liệu một phần như complete. |
| Missing policy/allocation | Chỉ item cần xử lý, link cấu hình; không gán0 hoặc policy khác. |
| API/DB lỗi | Banner/thử lại; dữ liệu cũ nếu còn phải ghi lần tải/run/cutoff. |
| Invalidated/mismatch | Chặn kết quả, giải thích cần run tương thích. |
| Tồn0/low stock/shortage | Ba nhãn khác nhau; tồn0 origin không gắn báo sớm. |
| Pending đủ/Q0 | “Dưới ngưỡng, đã có hàng đang về”; vẫn hiện ETA/nguy cơ nếu ETA sau cạn. |

Tồn/nhập số nguyên; forecast1–2 số lẻ và metric2 số lẻ để đọc, tooltip giữ số gốc; không tính từ giá trị đã làm tròn. Bias có dấu; coverage có n/N; null khác0. Phân biệt sales snapshot/dẫn xuất, forecast ML, phân bổ ngày, giả định policy/kho và tồn mô phỏng. Note top10: metric tuần không đóng R05 ngày; LG U+ test-selected hồi cứu.

## 5. Xuất và khả năng sử dụng

Xuất đúng dataset/run/filter hiện tại; tên file có run/cutoff, cột metadata/version/is_simulated. Không raw order/customer IDs; chỉ complete được export. Lỗi download không đổi dataset.

Desktop1366×768, bảng cuộn ngang với cột kho/item cố định; layout dùng được ở768px. Form có label/lỗi tại trường, thao tác bàn phím; trạng thái không chỉ bằng màu. Chart có đơn vị/legend/tooltip/bảng số. Text React escape mặc định, không render HTML từ dữ liệu. Không thêm map nếu không phục vụ quyết định tồn.

## 6. Kiểm FE dự kiến

Sáu route mở; đổi run/filter đồng bộ, response cũ không ghi đè; origin/block/null đúng; Q/ETA/ROP khớp BE; double click không tạo run đôi;409 hiện rõ. Vitest + React Testing Library kiểm trạng thái; Playwright một luồng xuyên API thật với fixture giả. Kiểm label/keyboard và export cùng filter. Chưa chạy các kiểm ứng dụng này; xem [06](06-testing-delivery.md).
