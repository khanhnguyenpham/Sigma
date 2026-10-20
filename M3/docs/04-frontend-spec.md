# M3 — đặc tả frontend

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
