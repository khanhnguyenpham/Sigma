# M3 — ứng dụng đã triển khai và cách chạy

**CHG-068 bước14 — 26/10/2026, hoàn tất:** sau cổng13 mã73d6f39/remoteSHA/2CI success, người dùng giao14. React hiển thị ROP/SS/mode/N, ngày xuống ROP riêng ngày cạn, lý do/đường projection/bảng UTC; filter/export và metric threshold riêng depletion. Workspace thêm warning_items/projected_below_rop_items đếm item duy nhất; inventory API/CSV đọc5tham số từ policy frozen, công thức fixed hiển thị đúng.245Python (3ca mới),50React (7ca mới,1worker)/build/pipcheck và browser desktop/mobile390px trên2run synthetic đạt;1027protectedhash và3app run nguyên, schema0003_threshold giữ. Commit mã37c4525b90cb361d8eeabc23c46cfc82fb39f8dc đã push thường, remoteSHA khớp và2workflowCI completed/success; bước15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật mới chứng minh45%.

**CHG-068 bước12 — 26/10/2026, hoàn tất:** cảnh báo projected_below_rop/threshold_warning với predicted_threshold_date đã qua hàm thuần/simulation/worker, DTO/filter/CSV và verifier độc lập. Giữ ROP tại decision origin, chỉ receipts đã biết trước Q mới, strict < trong N ngày; metric threshold riêng depletion.242Python BE/M2 (28ca mới),34React chạy1worker/build/pipcheck/API-worker smoke đạt;9inventory golden/M2 parity và1024protectedhash nguyên. DB app đã backup/nâng0003_threshold, hash mọi cột cũ13bảng/3run nguyên, schema0diff. Commit mã14b18415014ee2867fac436e6bd7530d74b12188 đã push thường, remoteSHA khớp và2workflowCI completed/success; bước13–15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật chứng minh45%.

**CHG-073 — 25/10/2026, chỉ sửa MD:** [mục tiêu làm việc R07≥45%](../docs/requirements.md#r07-target-chg073) được ghi theo lời mentor người dùng thuật lại, với báo trước≥7ngày; tính bắt buộc/phạm vi còn cần làm rõ. Early rate cơ sở34,391350% chưa đạt mục tiêu làm việc này. Các số replay/độ nhạy bên dưới là kết quả lịch sử, chưa được chạy lại trong lượt MD. Bước11 CHG-068 đã hoàn tất theo [bàn giao](../docs/development.md#handoff-chg068-step11); bước12–15 chưa bắt đầu. Chưa đổi code/cấu hình/metric/snapshot, không nhận cảnh báo xuống ROP hoặc tăng safety tự chứng minh45%. [Kế hoạch bổ sung](../docs/planning/PLAN.md#chg073), [bảng nghiệm thu](ACCEPTANCE.md).

**Hiện hành CHG-072 — 25/10/2026:** frontend ở web/frontend, configs/research code/env ở web/backend; M3 chỉ giữ Markdown và protocol nghiên cứu. Backend serve/build/launcher/CI đã đổi đường; tên env/DB, FE/nghiệp vụ/API/13bảng/snapshot giữ nguyên. [Cây thực](docs/05-source-architecture.md#web-layout-chg072), [bàn giao](../docs/development.md#handoff-chg072). Bước11–15 chưa bắt đầu; các mốc đường M3/frontend/configs/research/env dưới đây là lịch sử trước chuyển vị trí, các lệnh chạy đã cập nhật.

**CHG-071 — lệnh hiện hành:** từ root repo, API dùng `python -m uvicorn main:create_app --factory`, worker `python -m worker`, CLI `python -m cli`; launcher ở web/backend/scripts. Cài editable từ web/backend; src backend không có thư mục sigma_m3. FE/configs/env vẫn M3, root src vẫn M2. Cấu trúc/namespace trong các mốc E89–E104 là lịch sử, không là lệnh chạy mới.

**CHG-070 — cách chạy hiện hành:** cài package từ `web/backend`, dùng Alembic `web/backend/alembic.ini`; FE build tại `M3/frontend/dist`, configs/env/scripts giữ ở M3. API/worker/CLI dùng cùng package  [Lệnh chạy hiện hành](../README.md) và [cây thư mục](docs/05-source-architecture.md#web-layout-chg070). Các mô tả Streamlit và số kiểm E89–E103 bên dưới giữ như lịch sử;7file hướng dẫn/bản sao cũ đã bỏ, tra bằng [Git/E104](../docs/review-log.md#removed-docs-chg070).

**CHG-068 bước5 — 24/10/2026:** người dùng yêu cầu làm riêng bước5 sau checkpoint `992b8f5`. Đã tách core/catalog/configuration và rút main391→45dòng; giữ26route/OpenAPI đầy đủ, DDL13bảng và giao dịch/version/snapshot. Local107Python/26React/build/pipcheck/CLI/import/Alembic/smoke đạt,845protectedhash nguyên. Commit mã `db6c1d5` đã push, SHAremote khớp và cả2workflowCI completed/success. Bước5 hoàn tất; bước6–15 chưa bắt đầu. [Bàn giao và kiểm tra](../docs/development.md#handoff-chg068-step5). Không có migration hoặc thay model/policy/mẫu số metric ở bước này; chưa chạy fullreplay mới.

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo feature và thành phần dùng chung, sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Bản nguồn hiện có dùng API/worker/React và lớp Streamlit riêng. CHG-068 chỉ cập nhật đặc tả ở bước1; bảng kiểm/chạy bên dưới thuộc lần trước. Từng bước sau sẽ ghi kiểm thực cùng giới hạn; không nhận đã refactor, chạy lại replay hoặc cải thiện metric ở bước tài liệu.

[Kế hoạch CHG-068 và cổng từng bước](../docs/planning/PLAN.md#chg-068).

<a id="submission-e99"></a>
## Hoàn thiện bản nộp — E99, 21/10/2026

[Hướng dẫn nộp và luồng kiểm sản phẩm](SUBMISSION.md). Bổ sung trạng thái khởi động/kết nối lỗi, timeout và clear timer/listener, loại late reply, không auto retry write; lỗi đọc có Thử tải lại. Làm mới phát event chỉ đọc, không reload/reset session. PageBoundary giữ lỗi trang không làm mất sidebar; reload toàn trang có cảnh báo phiên. Hướng dẫn giải thích thao tác/ROP/IP/MOQ/pending và giới hạn, có focus/Escape. Menu mobile Escape trả focus về nút mở; skip link, reduced motion và browser Back giữa các trang giữ context. Khi phương án mới đang tải không hiện nhầm chưa có kế hoạch.

PublicBundle suy danh sách origin có đủ920item closing và vectorH14 từ release đã pin, không tạo target/feature hoặc fit mới; dropdown online chỉ cho chọn các ngày này. Nguồn thực có93ngày30/09–31/12/2025, đã kiểm seed920từngngày. Backend vẫn kiểm nguồn/origin/idempotency/config như E98. Không nới cổng dữ liệu, metric hoặc sửa frozen run.120Python+31React đạt; source và asset được rà trước cập nhật deploy. Browser và CI mới được ghi riêng trong review-log E99.


<a id="streamlit-react-e98"></a>
## React trên Streamlit — E98

Bản công khai dùng cùng source React quản lý E97; `MODE=streamlit` chuyển API sang RPC qua `streamlit-component-lib`2.0.0, assets tương đối trong `react_ui`. Adapter Python chỉ đọc gói aggregate đã pin và thay đổi trạng thái riêng từng phiên. Không mở FastAPI/PostgreSQL local ra Internet. [Hướng dẫn build, phạm vi và manifest](../docs/review-log.md#removed-docs-chg070).

Phương án mới lấy số tồn đóng tại origin đã công bố, danh sách lô đầu kỳ khai báo trong kịch bản (trống nghĩa không có), chính sách có hiệu lực và forecast H14 khóa. Dùng cùng hàm recommend/project L7/R1/H14; không tái dựng 28ngày giao dịch, không fit ML mới. Lưu cấu hình không sửa run đã công bố. Tối đa8phương án/40kịch bản/2048phiên bản policy mỗi phiên, mỗi kịch bản tối đa100điều chỉnh/lô, input số hữu hạn, ETA đúngD+7, guard parent/origin/idempotency/version. Trạng thái mất khi phiên bị reset, không phải kho dữ liệu nhiều người dùng bền vững.

117Python chạy toàn bộ đạt trước lượt hardening;6test adapter chạy lại sau guard dữ liệu lỗi đạt.23React đạt sau sửa CSV; build cả local và Streamlit. Dữ liệu nguồn trực tiếp:920mặt hàng/46tuyến, tồn1314/Q793mặt hàng/5866đơn vị, lô20đơn vị ETA04/11. Phương án online cơ sở không khai báo lô giữ tồn1314 nhưng Q794mặt hàng/5871đơn vị, đúng khác biệt khởi tạo.7360đường dự phóng được bổ sung, mỗi đường14ngày chỉ gồm date/closing_forecast/receipts_qty; không sao chép explanation/rawID. R05 tổng30 giữ10/10 hồi cứu, mean11,621356%; không đổi metric/holdout/nghiệm thu. Browser công khai và bằng chứng triển khai xem E98 trong review-log.


<a id="purchasing-e97"></a>
## Bàn làm việc nhập hàng — E97, 20/10/2026

Người dùng đã làm rõ muốn cách trình bày và thao tác như phần mềm doanh nghiệp. Bỏ dãy bước đánh số E96; Tổng quan ưu tiên việc cần xử lý. Phạm vi vẫn là M3 mô phỏng, không thêm đơn đặt supplier thật, phiếu duyệt, nhận hàng thủ công, tài khoản hoặc quyền truy cập nhiều người.

**Cách dùng:** Nhập hàng → Cần bổ sung để rà các mặt hàng Q>0, lượng đang về, ROP và ETA nếu đặt tại ngày kế hoạch. Tìm theo SKU/nhà mạng/quốc gia/loại; nhiều từ phải cùng khớp, không phân biệt hoa thường. Sắp xếp lượng hoặc ngày nhận. Nhấn dòng xem lý do, IP/mức tồn mục tiêu/MOQ và mở đúng hồ sơ tồn kho. Đề xuất chưa phát sinh lô nhập. Tab Đang về và Lịch sử lô nhập xem các lô đã đặt tại mốc dữ liệu, mở chi tiết lịch đặt/ETA/số đã nhận/chính sách. Từ Tồn kho có thể mở đề xuất hoặc hàng đang về; từ Cảnh báo mở tồn/kế hoạch nhập. Kho/item/run/ngày giữ đúng; tab nhập được lưu bằng tham số view trong URL và khôi phục sau reload. Tìm kiếm hoặc đổi context đóng chi tiết cũ, xóa dữ liệu cũ ngay trong lúc chờ và reset trang.

**Read model mới:** `GET /api/v1/runs/{id}/purchasing` và `/purchasing/export`. Query as_of_date bắt buộc, view=recommendations/incoming/history; search≤80ký tự; sort=quantity_desc/quantity_asc/eta_asc/ordered_desc (ngày đặt chỉ dành cho lô); page/page_size≤100 và bộ lọc kho/item/loại/supplier. Summary theo toàn bộ bộ lọc/tìm kiếm, không chỉ trang hiện tại; các tab chia cùng scope. CSV xuất toàn bộ tập khớp cùng thứ tự/context, bỏ giới hạn trang; có run_status, view_date, known_orders_through, is_simulated và chống công thức CSV. Không thêm bảng hoặc ghi DB.

Mốc lô được biết là min(ngày xem, origin snapshot hoặc period_end replay). Chỉ lô ordered_on≤mốc mới được hiện; Đang về có ETA>mốc. received_qty=0 trước ETA dù trạng thái cuối replay là received. Không suy đã nhận sau origin snapshot; banner ghi mốc đã biết. Dữ liệu gốc của lô và sealed run giữ nguyên; cách xem toàn kỳ cũ trong API/export gốc tiếp tục dùng cho đối soát, UI quản lý mới dùng purchasing.

**Kiểm thực:**111Python=79M3+32M2,0fail/error;19React, TypeScript/Vite build và Ruff đạt. Hai test API mới kiểm ngày đặt tương lai, status nhận theo ETA, snapshot clamp, tìm trước phân trang, CSV toàn bộ cùng scope/sort, invalid/incomplete guard và không ghi lại receipt. Hai test FE mới kiểm search không lộ bảng/CSV cũ, resetpage và lô→đúngitem. Browser thực kiểm lô16125→item341→Đang về, reload giữ view=incoming; tìm Optus D10G có2mặt hàng và drawer giải thích. API/CSV thật run0c3460ff:793đề xuất/5866đơn vị, xuất793dòng dù requestpage_size1/page2;1lô20đơn vị ETA04/11, đã nhận0 tại31/10. Replay cơ sở chỉ1308lô đã đặt tới31/10 được xem trong history, không lộ các lô đặt sau đó. Viewport390/1440 và receipt/ảnh giữ local. Không refit hay đổi kết quả M05/R07/T14. CI của commit mới phải kiểm riêng.


<a id="react-management-e95"></a>
## React quản lý M3 — E95, 20/10/2026

**Bổ sung E96:** giao diện ghi rõ Kho SIM & gói data; Tổng quan có bốn lối đi Xem dự báo, Kiểm tra tồn, Kế hoạch nhập, Theo dõi cảnh báo. Đây là nút chuyển màn hình giữ context, không phải trạng thái công việc đã hoàn thành. Trang dự báo phân biệt tổng30 với forecast14ngày phục vụ tồn. Các nhãn nhà cung cấp, ngưỡng nhập tối thiểu, lượng đặt tối thiểu và số ngày tồn an toàn diễn giải bằng tiếng Việt.17React/build đạt; browser kiểm điều hướng và viewport390/1440 không tràn. Không đổi API/ML hoặc chạy lại backend;109Python/CI E95 bên dưới là lượt trước. Không thêm trang báo cáo hoặc chức năng ngoài M3.

Theo yêu cầu mới của người dùng, giao diện dùng React/TypeScript/Vite, sidebar và bảng quản lý thông thường. Không thêm xử lý bán hàng, gửi đơn nhà cung cấp, đăng nhập hoặc quản trị người dùng ngoài thiết kế M3. Dữ liệu tồn/nhập/kho vẫn là mô phỏng có nhãn; ngày làm việc là UTC của snapshot 2024–2025.

| Màn hình | Việc người dùng thực hiện |
|---|---|
| Tổng quan | Xem tồn hiện có, mặt hàng cần bổ sung, lô đang về và nguy cơ cạn; mở một mặt hàng hoặc tạo phương án. KPI và danh sách theo cùng run, ngày, kho, SKU, loại và nhà cung cấp. |
| Tồn kho | Lọc trạng thái, mở ngăn chi tiết SKU để xem tồn/ROP/pending/IP/Q/MOQ; xuất CSV cùng bộ lọc. |
| Dự báo nhu cầu | Chọn tổng30, tổng7 hoặc ngày phân bổ; xem lượng bán/actual. Tổng30/7 ở cấp tuyến; SKU/loại áp dụng cho phân bổ ngày, nhãn ghi rõ. Chất lượng, nguồn và giới hạn hồi cứu nằm trong phần mở rộng. |
| Nhập hàng | E97: Cần bổ sung/Đang về/Lịch sử theo mốc dữ liệu; tìm kiếm, sắp xếp, chi tiết và CSV cùng scope. Không dùng trạng thái cuối kỳ để suy ngược; xem mục purchasing-e97. |
| Cảnh báo | Lọc tín hiệu, mở chi tiết diễn biến tồn14ngày; dữ liệu TP/FP/FN/TN và chẩn đoán cơ hội chỉ trong phần đánh giá replay mở rộng. |
| Cấu hình | Danh mục kho, chính sách supplier-item có phiên bản, tạo kịch bản và lô đầu kỳ; lưu không sửa kết quả đã khóa. |

**Tạo phương án:** nút trên header → chọn loại công việc, dự báo hoàn tất, kịch bản, ngày → gửi một lần → xem tiến độ ở Tổng quan. Mặc định ưu tiên forecast replay có nhiều origin thay bản chỉ có origin tương lai; backend vẫn kiểm parent/source/cutoff. Chọn forecast/source ở các trang tồn thì phải bấm chọn kế hoạch tương thích; không lặng lẽ lấy tồn của run khác. URL giữ bộ lọc. Đổi run/bộ lọc hủy dữ liệu cũ, ngăn chi tiết cũ đóng ngay; Escape đóng ngăn hiện tại. Không dùng màn hình này để gửi đơn thật.

**API bổ sung:** `GET /api/v1/runs/{id}/workspace?as_of_date=YYYY-MM-DD`, tùy chọn warehouse_id/item_id/product_type/supplier_id. Chỉ run tồn complete/compatible; trả context, summary, attention6, incoming5, route_stock8. Tổng tính trên toàn bộ bộ lọc, không phải chỉ50dòng trang. Incoming xét `ordered_on <= known_orders_through < eta`; snapshot chỉ biết tới origin, replay chỉ tới kỳ ghi nhận. Có nhãn riêng nếu ngày xem sau mốc đã biết; thiếu sổ tồn giữ on_hand=null. Metric API thêm split trước phân trang/export để test không bị khuất sau validation.

**Đã kiểm trực tiếp:**109Python (77M3+32M2),17React, TypeScript/Vite build và Ruff. Browser thực mở đủ sáu màn hình, chọn kế hoạch tương thích, lọc Japan/NTT Docomo/item341, mở/đóng chi tiết bằng Escape, chuyển ba chế độ dự báo, lưu kịch bản mới `management_ui_20261020`v1 và tạo stock_projection mới. Run `0c3460ff-6219-408d-b4a6-8a744f06e21d`complete/verified:920threshold/920events/1lot/1714alerts; cùng forecast replay/scenario7/origin31/10. API/CSV đối soát1dòng: closing7/ROP20/pending20/IP27/Q0, ETA04/11; không coi pending là tồn hiện có. Tổng quan46tuyến/920item:1314tồn,793mặt hàng Q>0/5866đơn vị,1lô20đơn vị,200mặt hàng urgent/already_depleted. Đây là số liệu của phương án mô phỏng cụ thể, không KPI doanh nghiệp thật. Responsive390/768/1440 đã kiểm: trang không tràn ngang; bảng có vùng cuộn riêng. Console error ở lượt kiểm cuối trống. Receipt và ảnh trong outputs local, không phải artifact cần push.

**Nhóm lấy mã:** dùng các lệnh clone/cài trong mục “Cài trên máy thành viên” bên dưới. Nếu đã có checkout nhánh này, lưu thay đổi cá nhân rồi `git pull --ff-only origin m3-implementation`; trong `web/frontend` chạy `npm ci`, `npm test`, `npm run build`. Tại root nạp env và chạy launcher như hướng dẫn. Thành viên cần PostgreSQL và nguồn bài local; Git không kèm DB/raw/run/env. Không copy nguyên UUID local để kỳ vọng máy mới đã có kết quả; tạo nguồn/forecast/mô phỏng theo quy trình bên dưới.

**Giới hạn:** React mới phục vụ cùng backend local, chưa deploy lên Internet hoặc thay app Streamlit public. M05 tổng30 vẫn10/10 hồi cứu; không refit hoặc nâng R07/T14/mentor nghiệm thu từ việc đổi giao diện. Không thêm auth/hosting nhiều người trong lượt này.


**E94 — đã triển khai Streamlit công khai theo yêu cầu mới:** [Mở SIGMA](https://sigma-demand-inventory.streamlit.app/) · [phạm vi online và source](../docs/review-log.md#removed-docs-chg070). Cùng kết quả M3 mới L7/R1/H14 và tổng30; 11 bảng tổng hợp+1mảng forecast, khoảng6,6MB, không raw/ID đơn/khách/DB/env. What-if dùng cùng hàm policy/project và chỉ giữ trong phiên; các tác vụ worker/huấn luyện/DB vẫn local. Các mô tả “chưa deploy” bên dưới là mốc lịch sử trước E94.

**E93/M05 — 20/10/2026, áp dụng hiện tại:** R05 chấm tổng 30 ngày thay từng ngày theo mentor được người dùng thuật lại. [Kết quả và tích hợp tổng 30](MONTHLY.md): 10/10≤20%, mean11,621356%, coverage100%, 63 cửa sổ/tuyến, test hồi cứu. API/React có tab riêng và CSV; luồng tồn H14 giữ nguyên. Các mô tả R05 ngày/E92 bên dưới là lịch sử trước M05.

Kiểm E93: 97 Python (65 M3 +32 M2), 11 frontend, TypeScript/build, Ruff và pip check đạt; API và trình duyệt đã kiểm tab tổng30/46 tuyến/null/CSV. Run/source thật và gói benchmark giữ local. Không fit lại H14 hoặc đổi các replay tồn chỉ để tích hợp benchmark.

**E92,20/10/2026:** nghiên cứu ngày panel đạt45,971604% validation/0trên10,168fits; serving giữ nguyên.89Python đạt,9FE thuộc E91 không đổi. [Đối chiếu tiêu chí và cổng còn mở](ACCEPTANCE.md). CI E91 cd57235 đã xác nhận cả haiworkflow success; CI của commit mới phải xem riêng.

Ngày kiểm: 19/10/2026. Nhánh: `codex/m3-implementation`, nền `M3-design-plan` tại `20a3c45`. Phạm vi là **ứng dụng local FastAPI + React/TypeScript + PostgreSQL18**, 46 kho giả định, 920 mặt hàng, L7/R1/H14. Đây là implementation mới, riêng với Streamlit/tổng30 của nhánh khác. Không cần thay M2 final để chạy M3.

## Phần mềm và kết quả nghiên cứu

| Thành phần | Bằng chứng trực tiếp |
|---|---|
| Nguồn | Import100.000 dòng, quantity118.296, 46 tuyến, 920 item, 672.520 item-day. Raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. |
| Database | PostgreSQL18.6, app role không superuser, migration0001 tạo đúng13 bảng nghiệp vụ; Alembic check không drift. |
| Forecast | Chạy validation/khóa/test/future thật:185 origin,17.020 tổng tuần,2.382.800 item-day forecast. Mỗi origin đủ46 tuyến ×2 khối. |
| M2 final10 | Pooled LightGBM chỉ top10; Prophet riêng au(KDDI); LG U+ giữ override.40 nhóm metric test khớp báo cáo đã khóa trong1e-8. Không có bundle per-origin lịch sử ở checkout này nên **không tuyên bố đã so từng dòng với bundle cũ**. |
| Mở rộng36 | 5 LightGBM gốc học pooled46, Prophet riêng từng tuyến; chọn bằng validation đủ coverage, MAPE→MAE→ID.36 lựa chọn và1.799 dòng fit log kiểm lại; không dùng test chọn lại. |
| Phân bổ | Tính độc lập17.020 nhóm bảo toàn tổng,2.382.800 dòng weekday90/share30→90 và eligibility first_seen≤origin; đạt. |
| Policy replay cơ sở | 01/10–31/12/2025;85.560 ledger,16.423 sự kiện,3.245 lô; fill90,4121%, thiếu1.531/15.968 quantity. Receipt trước bán, ETA D+7, không âm, bán=đáp ứng+thiếu. |
| Alert replay cơ sở | 6 cửa sổ14 ngày không chồng, không đặt mới;82.800 ledger. TP2098/FP852/FN769/TN702; loại1099 ca đã cạn tại origin; early986/2867=34,3913%;8 ngày cuối ngoài cửa sổ đủ nhãn. |
| Snapshot | 31/10 và31/12 có920 dòng khởi tạo; không thêm actual tương lai vào ledger. Projection14 ngày dùng forecast và lô đã biết. |
| API/React | Sáu màn hình, bộ lọc/URL, bảng/biểu đồ, giải thích ROP/IP/MOQ, config có version, tạo job nền, tải CSV cùng context. API/CLI dùng cùng services. |
| Kiểm phần mềm |E91:86 ca Python:54 M3 +32 M2;9 ca Vitest/RTL và production build đạt. Nền E90 đã kiểm npm ci/pip check/Alembic check. Kết quả chi tiết private trong outputs, không đưa source orders vào CI. |

| Metric test, daily origins | Số tuyến MAPE≤20% | MAPE trung bình tuyến | Coverage |
|---|---:|---:|---:|
| Tổng7 H1–7, fixed10 |10/10|15,745366%|100%|
| Tổng7 H8–14, fixed10 |8/10|16,600553%|100%|
| Tổng7 H1–7, new36 |2/36|35,400179%|100%|
| Tổng7 H8–14, new36 |2/36|35,521325%|100%|
| Tổng7 H1–7, all46 |12/46|31,127393%|100%|
| Ngày **phân bổ từ tổng tuần**, fixed10 H1–7 |0/10|51,919555%|100%|

Không nhầm ngày phân bổ M3 với mô hình trực tiếp từng ngày trong thử nghiệm M2 cũ. MAPE chỉ actual dương; có MAE/WAPE/bias/counts/coverage ở API. Kết quả tuần không thay R05 ngày. M2 test hồi cứu, LG U+ đã chọn sau test-sweep; đây không là holdout độc lập. **R05/R07/T14 còn mở**, không nhận bảo đảm điểm hoặc mọi sự kiện đều báo sớm. Tồn, receipt, supplier/city/policy đều giả định; A08 là đề xuất success/orderUTC, không là kế toán đã xác nhận.

## Độ nhạy đã chạy

Cùng nguồn/forecast/L7, đổi một trục, không dùng để chọn lại model hoặc che lỗi:

| Kịch bản | Fill policy replay | Thiếu quantity | Tồn cuối trung bình/item-day | Số lô | Early alert replay |
|---|---:|---:|---:|---:|---:|
| Cover7, safety1 (cơ sở) |90,4121%|1.531|5,3836|3.245|34,3913%|
| Cover3, safety1 |89,4790%|1.680|5,3141|3.278|25,9549%|
| Cover14, safety1 |90,5686%|1.506|5,2487|3.114|17,6083%|
| Cover7, safety0,5 |89,1971%|1.725|5,2710|3.168|34,3913%|
| Cover7, safety1,5 |91,5018%|1.357|5,5357|3.317|34,3913%|

Đủ10 run cho5 kịch bản ×2 loại replay, tất cả complete/đối soát. Alert replay không đặt mới nên đổi safety không đổi đường tồn/projection cạn; thay đổi chỉ ảnh hưởng tín hiệu dướiROP. Đổi cover thay mẫu sự kiện tương lai, không được so early như cùng mẫu số. Tăng safety giảm shortage trong policy replay nhưng tăng tồn/lô, không là bảo đảm hết hàng bằng0.

Fresh future run `d57975c8-3d14-40a2-bee6-b3b8e20575ad` qua mã worker cuối:46tuyến/92tuần/12.880itemforecast,43fitlog,actual sau31/12 null; giữ nguyên selectionSHA từ replay. Source reuse run `6db3901f-b6f5-4ee9-a2e3-129d3407ba55` giữ tổng daily672.520 dòng, không nhân đôi nguồn. Manifest của hai run mới có full config/runtime/seed. Warning Prophet thiếu plotly chỉ liên quan plot tùy chọn; chart ứng dụng dùng React, fit/verification không phụ thuộc plotly.

## Cây mã để thành viên đọc

| Đường dẫn | Trách nhiệm |
|---|---|
| `web/backend/src/models.py`, `web/backend/migrations/` |Registry13 model thuộc8module trên cùng Base; FK/unique/check/index và migration giữ nguyên. |
| `core/`, `modules/*/schemas.py` dưới backend src |Env local, Base/DTO/hash/context/serialization, lỗi không echo dữ liệu nhạy cảm. |
| `modules/forecasting/ingestion.py`, `modules/inventory/seeding.py`, `modules/catalog/` |Audit nguồn, hash-dedup, danh mục và giả định có version. |
| `modules/forecasting/{m2_adapter,service,allocation,models}.py` |Tái dùng M2, validation/selection/forecast46 và phân bổ causal. |
| `modules/configuration/context.py`, `modules/inventory/`, `modules/purchasing/`, `modules/alerts/` |Snapshot policy, sổ giao dịch/ngày, lượng nhập, ETA, hai replay và router/read model nghiệp vụ. |
| `modules/runs/`, `worker.py`, `cli.py` |Parent DAG/config hash, idempotency, queue một worker, heartbeat30s, verify trước complete. |
| `modules/runs/verification.py` |Tính lại allocation/actual/threshold/event/receipt/mẫu số cảnh báo; receipt kiểm ngoài run đã khóa. |
| `main.py`, `modules/reporting/`, các module/router.py |Result/metric/CSV/monthly và serve React đã build; tổng quan/tồn/nhập/cảnh báo ở module tương ứng. |
| `web/frontend/src/services/`, `types/`, `utils/`, `config/`, `hooks/`, `components/`, `layouts/`, `pages/` |Client typed/abort, context/layout và sáu trang ghép component; form/drawer riêng, main import index.css giữ byte cũ. |
| `web/backend/tests/`, `web/frontend/tests/`, `.github/workflows/m3.yml` ở root |Fixture giả PostgreSQL, unit/integration, RTL và CI. |

## Cài trên máy thành viên

Clone đúng nhánh; không cần merge main để đọc/chạy:

```powershell
git clone --branch m3-implementation https://github.com/khanhnguyenpham/Sigma.git
cd Sigma
py -3.12 -m venv .venv-m3
.\.venv-m3\Scripts\python.exe -m pip install -r web/backend/requirements.txt
.\.venv-m3\Scripts\python.exe -m pip install --no-deps -e web/backend
Copy-Item web/backend/configs/.env.example web/backend/.env
```

Cần PostgreSQL18 và Node24/npm11. Tạo app role **không superuser**, hai database riêng `sigma_m3`/`sigma_m3_test` do role đó sở hữu. Dùng tài khoản quản trị PostgreSQL của máy để thực hiện; ví dụ trong psql:

```sql
CREATE ROLE sigma_m3_app LOGIN;
\password sigma_m3_app
CREATE DATABASE sigma_m3 OWNER sigma_m3_app;
CREATE DATABASE sigma_m3_test OWNER sigma_m3_app;
```

Điền mật khẩu/port/local paths trong `web/backend/.env`, không commit. `M3_SOURCE_ROOT` trỏ workspace đang giữ nguyên CSV tại `data/sigma_sim_data_orders.csv`; raw không nằm trong Git, thành viên dùng nguồn bài nhóm đã có. Không cần gửi lại dữ liệu doanh nghiệp. `M3_OUTPUT_ROOT` là thư mục private; không chọn M2/artifacts hoặc thư mục run cũ. DB trên máy kiểm là portable127.0.0.1:55432, không cài service toàn máy; đây không là yêu cầu port của mọi thành viên.

```powershell
. ./web/backend/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -m alembic -c web/backend/alembic.ini upgrade head
.\.venv-m3\Scripts\python.exe -m pip check
cd web/frontend
npm ci
npm test
npm run build
cd ../..
. ./web/backend/scripts/start_m3.ps1
```

Mở `http://127.0.0.1:8000/`, OpenAPI `/docs`, health `/api/v1/health`. Launcher chạy API+worker ẩn, log ở outputs; dừng bằng `web/backend/scripts/stop_m3.ps1`, chỉ dừng PID mà launcher tạo và đúng creation time. PostgreSQL quản lý riêng. Đây là app local, chưa có auth/hosting nhiều người; push GitHub không xuất bản database hoặc ứng dụng lên Internet.

Để phát triển FE: chạy `start_api.ps1`, `start_worker.ps1` trong hai terminal; tại web/frontend dùng `npm run dev` port5173 proxyAPI8000. Không đồng thời mở worker dev và launcher; worker thứ hai bị advisory lock chặn.

## Tạo dữ liệu và lượt chạy

```powershell
. ./web/backend/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -m cli import-orders --as-of-date 2025-12-31 --request-key import-v1 --wait
# Thay SOURCE bằng UUID trả về ở lệnh trên, không dùng chuỗi ví dụ nguyên trạng.
.\.venv-m3\Scripts\python.exe -m cli seed-simulation --source-run SOURCE --as-of-date 2025-09-30
.\.venv-m3\Scripts\python.exe -m cli forecast --source-run SOURCE --as-of-date 2025-12-31 --mode replay --request-key forecast-v1 --wait
# Thay FORECAST bằng UUID forecast complete và SCENARIO bằng ID kịch bản đã seed.
.\.venv-m3\Scripts\python.exe -m cli simulate --kind policy_replay --forecast-run FORECAST --scenario-id SCENARIO --as-of-date 2025-09-30 --period-start 2025-10-01 --period-end 2025-12-31 --wait
.\.venv-m3\Scripts\python.exe -m cli simulate --kind alert_replay --forecast-run FORECAST --scenario-id SCENARIO --as-of-date 2025-09-30 --period-start 2025-10-01 --period-end 2025-12-31 --wait
.\.venv-m3\Scripts\python.exe -m cli simulate --kind stock_projection --forecast-run FORECAST --scenario-id SCENARIO --as-of-date 2025-10-31 --wait
.\.venv-m3\Scripts\python.exe -m cli verify --run-id RUN
```

CLI `--wait` dùng worker thông thường; dừng worker nền trước khi dùng chế độ này. Cách dùng web: chọn nguồn/forecast/scenario, bấm Tạo phương án; worker nền nhận và cập nhật status. Không trộn hai cách để chạy hai worker. Forecast replay là việc nặng, không chạy lại chỉ để sửa thành phố hoặc xem dashboard. `forecast --mode future --forecast-run FORECAST` dùng selection khóa, origin không trước30/09/2025; không chọn lại bằng test. Missing vector/policy/history → failed, không tự điền0. Khi mã thay đổi, restart worker rồi tạo request mới; code mismatch không được ghi complete.

Seed chỉ tạo giả định rõ ràng: cover3/7/14 và safety×0,5/1/1,5, không ghi đè policy người dùng. Policy effective dates là [from,to); một supplier/item tại mỗi thời điểm. Policy mới không được đóng khoảng ảnh hưởng run đã khóa; muốn thử lịch sử dùng **scenario override** trong Cấu hình. Lô đầu kỳ có ETA đúng D+7, ordered_on≤origin. Snapshot không tự phát sinh đơn; khuyến nghị chưa là receipt.

## Cách trình diễn và kiểm

1. Chọn snapshot31/10 → kho Japan/NTT Docomo → SKU. Tồn kho: nhấn dòng xem SS/ROP floor/IP/MOQ/Q. Dòng snapshot là khởi tạo, không phải sales actual ngày31/10.
2. Dự báo → Tổng7 và Ngày phân bổ; xem H1–7/H8–14, sai số toàn cửa sổ test. Actual sau31/12 giữnull.
3. Nhập hàng → tách khuyến nghị và lô replay; Cảnh báo → nhấn dòng để thấy projection, chọn alert replay để xem confusion/early toàn lượt.
4. Cấu hình → tạo scenario với cover/safety, policy riêng và lô đang về; tạo run mới, run cũ giữ snapshot. URL giữ run/kho/item/origin, filter dùng chung bảng/CSV; KPI quản lý Tổng quan theo bộ lọc/ngày; tỷ lệ đánh giá replay trong phần mở rộng ghi rõ là **toàn lượt**.
5. Xuất CSV: đối chiếu run/source/config/selection hashes, cutoff, phiên bản và nhãn mô phỏng. Export không có raw orders/customer/source IDs; đọc dữ liệu từng batch.

```powershell
. ./web/backend/scripts/load_env.ps1
.\.venv-m3\Scripts\python.exe -B -m pytest web/backend/tests tests M2/models/tests --basetemp=outputs/pytest-team
.\.venv-m3\Scripts\python.exe -m alembic -c web/backend/alembic.ini check
```

Test DB phải đúng tên `sigma_m3_test`; fixture TRUNCATE chỉ database này, không dùng DB ứng dụng. Thiếu env thì tests PostgreSQL sẽ skip, không được báo là đã kiểm DB. CI chỉ dùng fixture giả; lần push phải xem kết quả GitHub riêng, không suy CI từ tests local. Workflow M3 tách Linux/PostgreSQL (54 tests M3), Windows/Python3.12 với toàn bộ dependency M3 (32 tests hồi quy M2, gồm golden300forecast ở ngưỡng1e-8), và frontend (9 tests/build). Golden được ghi trên Windows: lần CI đầu trên Linux có30giá trị Prophet lệch tối đa7,8783e-6; đây là giới hạn parity giữa hai nền tảng, chưa chứng minh Linux tái lập golden ở1e-8. Giữ nguyên fixture/ngưỡng/model M2; không bỏ test hoặc dùng CI xanh để nhận parity Linux.

Artifacts full/DB/env/raw giữ local. Complete chỉ sau verify; source-hash dedup giữ request identity nhưng tái dùng canonical daily dataset. Run đầu E89/E90 đã khóa không sửa manifest để thêm trường; phiên bản worker sau bổ sung runtime/seed/full config vào manifest của **run mới**. Receipt kiểm lại run cũ nằm ngoài thư mục đã khóa.


## Kiểm E2E kết thúc

Từ React tạo scenario `e2e_receipt_policy` v2 rồi run `950e6844-d611-48cf-b0ef-4e845ba0811a`, theo dõi queued→running→complete qua worker nền. Đã kiểm 920threshold/920events/1lô/1714alerts, CSV tải trực tiếp từ trình duyệt khớp1dòng đang lọc. Japan/NTT Docomo, D10G-10D eSIM: closing7, floor20/ROP20, pending20, IP27, S21, MOQ10, Q0; ETA04/11 từ ordered28/10. Cảnh báo dướiROP không tự đặt thêm khi pending đủ. Run và scenario v1 trước đó giữ nguyên.

Form ngày đã được kiểm lại bằng thao tác nhập và state updates riêng cho từng trường; ngày đặt và ETA được giữ sau đổi quantity. Nút thêm lô/override chờ catalog đã tải.7tests FE gồm chống render dữ liệu run cũ khi đổi context, abort response cũ, gửi lặp/retry cùng key và lưu ngày/quantity. Dữ liệu thực được kiểm riêng, không gọi7tests này là full browser E2E tự động. Launcher stop/start đã chạy, giữ PostgreSQL và các ứng dụng khác; web vẫn tại8000.

## E91 — Chẩn đoán và thử nghiệm bổ sung

Màn Cảnh báo có phân tích **toàn lượt alert replay** qua GET /runs/{id}/alert-opportunities. Run complete/đúng kind, snapshot/hash và summary phải khớp; query filter bị từ chối để mẫu số không đổi. Actual chỉ dùng giải thích sau replay, không làm feature. Không cập nhật manifest/summary của run đã khóa.

Cơ sở:1.550/2.867 sự kiện cạn ởD+1…D+6; chỉ1.317ca có khoảng cách từ origin≥7. Do đó trần báo sớm tại chính các origin/tồn đầu này là45,936519%, so thực986/2867=34,391350%; còn331ca đủ thời gian nhưng không có cảnh báo. Trần này không áp cho mọi hệ thống/kịch bản, không xóa ca cạn sớm hoặc thay R07 bằng tỷ lệ có điều kiện. Không có sự kiện thì các tỷ lệ null. UI hiển thị phân bố14ngày và giữ mẫu số khi lọc bảng; đã kiểm trực tiếp chọnJapan/NTTDocomo:40dòng tại origin, mẫu số toàn lượt vẫn2867. Ảnh local outputs/m3-alert-opportunities.png.

[Nghiên cứu ngày validation](docs/research.md) dùng8phương pháp/28fits,95.760forecast/160nhóm metric/6.390ngày-tuyến đầu vào≤30/09/2025; không đọc test. Best theo từng tuyến H1–7 mean49,451918%,0/10≤20%; phân bổ M3 cùng623cặp/tuyến mean51,905954%.7/10tuyến có MAPE thấp hơn, nhưng loss giảm kèm bias âm; chưa chọn để phục vụ hoặc dùng vào tồn. Không nhận là đã cải thiện test/sản phẩm. Cần bằng chứng tiếp trước thay profile.

Run nghiên cứu cuối: outputs/research/daily-validation-v1-560a112e-2452-4b7a-a0c7-1e16d0475351. SelectionSHA0608d7dcda479cfea1e051f610edbfa833130db0ed43635b28c2bade72057180. Lượt trước7811fb30 được giữ; bản cuối bổ sung runtime/input/requirements hashes và clipping log, predictions/metrics/selection giống byte. Đối soát độc lập160nhóm metric/28cutoff/hashes/10selection đạt; receipt outputs/e91-verification.json ngoài run đã khóa.

86tests Python (54M3+32M2),9FE và TypeScript/build đạt. Hai test research kiểm future mutation/nhãn fit/thiếu lịch/zero; ca API kiểm mẫu số/boundary6–7–14, null, sai summary/filter/kind/status; FE kiểm context cũ và snapshot không có metric giả. Launcher restart riêng API/worker, giữ PostgreSQL. Snapshot mới309cc381-70cf-4e6a-9c1e-5b1220c49950 complete/verify:920threshold/920events/1lot/1714alerts, backendSHA1acba62a5213d419b67e4fca56ddaa1f0052bd4c2cbc86bd899c6a3d293e4f0f. Dùng lại forecast cha đã khóa; không refit toàn forecast/replay. Run E90 giữ codeSHA lịch sử, không sửa thành SHA mới. R05/R07/T14 còn mở; CI của commit E91 phải kiểm riêng sau push.

## E92 — Dự báo ngày với số đơn và tín hiệu thị trường

Nghiên cứu daily-panel-validation-v2 nằm ngoài worker/adapter/profile đang phục vụ.3ứng viên: LightGBM pooled Poisson/weightedL1 và weightedL1 riêng tuyến,350cây/leaves15/minchild60/lr0,04/lambda10/seed42. Feature chỉ dùng đến origin: số đơn, units/order, số0, country/global demand, weekday56/182/365 và lag364/365/366 của target; lịch tương lai biết trước, annual chưa có giữ NaN feature. SQL đầu vào≤30/09/2025; không truy test.

Run outputs/research/daily-panel-validation-v2-5f80050a-6413-4113-9627-522c0395bc6d complete:168fits/35.910forecast/60nhóm metric; H1–7 validation mean45,971604%,0/10≤20%.9/10tuyến thấp hơn v1 mean49,451918%, nhưng còn bias âm. Chưa chấm test/thay model app hoặc tính lại tồn. SelectionSHA95e5a80b8b9ba5a2731c29f63d25c9a09d4fafde98f382119e2350bb3baf8b96; manifestSHA18be7e6a58d33f1bb987f1a20cc3400d52a9b66a06a5120c22a8a413a594c23a. Receipt độc lập outputs/e92-research-verification.json kiểm60nhóm,10winner,168cutoff/scope/paircount và toàn hash.

Tách evaluate_frame dùng chung; lượt v1-6aea9e7c sau refactor tái lập byte-exact95.760predictions/metrics/selection với v1 E91. Sau khi bắt đầu fit bổ sung guard từ chối target làm feature, nhãn test/âm/thiếu và horizon lệch. Lượt fit dùng bản trước guard; source đúng hash đã được lưu receipt riêng outputs/e92-source-archive, không sửa run/manifest cũ. Guard mới kiểm bằng tests; dữ liệu đã fit cũng được đối soát hợp lệ, không nhận model đã chạy lại bằng source sau guard.

89Python/0fail/error/skip đạt. FE/app/DB không sửa trong E92,9FE/build và CI2workflow success của cd57235 là bằng chứng E91. BackendSHA giữ1acba62a5213d419b67e4fca56ddaa1f0052bd4c2cbc86bd899c6a3d293e4f0f. Không rerun toàn forecast/replay để sửa nghiên cứu/docs.

Phân tích331ca đủ thời gian nhưng bỏ sót: tất cả tồn đầu≤2,311ca tồn1, tổngforecast14 thấp hơn tồn trong331ca, không cóforecast0 hoặc receipt đầu kỳ; median forecast14/tồn0,580714. Actual phát sinh một vài đơn có thể làm cạn trong khi point projection chưa chạm0. Đây là mô tả sau replay; chưa dùng để chọn ngưỡng theo test hoặc đổi R07. R07 không có chỉ tiêu100% tổng sự kiện trong nguồn; không tự nhận đạt hay tự thêm yêu cầu này. [Bảng cổng nghiệm thu](ACCEPTANCE.md) và T14 giữ mở.
