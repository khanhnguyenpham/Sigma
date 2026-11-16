# Kế hoạch chuyển SIGMA sang hệ thống quản lý — 16/11/2026

Nguồn: góp ý mentor **do người dùng thuật lại** ngày 16/11/2026. Các quyết định A–D do người dùng duyệt cùng ngày. Nghiệp vụ đại lý là **giả định của nhóm** vì mentor không nêu chi tiết, không ghi thành xác nhận của mentor.

Kế hoạch này không đổi target, model, metric hay trạng thái C00/R05/R07/T14. Dự báo vẫn là H14 cho 46 tuyến như [AGENTS.md](../../AGENTS.md).

## 1. Góp ý và hiện trạng

| # | Góp ý mentor | Hiện trạng trong code (16/11) | Việc cần làm |
|---|---|---|---|
| G1 | Dự báo và kịch bản chỉ là công cụ nhỏ. Phần chính là hệ thống quản lý cho admin và đại lý. | Vai trò chỉ có `admin` và `supplier` chỉ đọc. Không có khái niệm đại lý. | Thêm vai trò đại lý và nghiệp vụ đại lý (mục 3). |
| G2 | FE đang lấy kịch bản làm trung tâm, cần chỉnh lại theo hướng quản lý. | `useAppContext` xoay quanh run đang chọn; 7/8 mục menu là dữ liệu mô phỏng; header luôn có "Tạo phương án". Quản lý thật dồn vào trang `Operations` với 8 tab. | Làm lại cấu trúc FE (mục 2). |
| G3 | Thêm skeleton hoặc loading khi tải dữ liệu. | Component `State` có skeleton, 9 trang và 31 component đã dùng. | Rà lại trên giao diện mới: nút đang gửi, bảng khi phân trang, chuyển trang, trang Tổng quan mới. |
| G4 | Cho phép đổi thời gian hàng về khi có sự cố. | ETA tự tính từ ngày đặt + lead time, chỉ sửa được khi đơn còn nháp (`operations/service.py: update_order`). | Thêm điều chỉnh ETA cho đơn đã xác nhận (mục 4). |
| G5 | Bỏ hash trong BE vì không cần thiết. | Còn 166 dòng ở 27 file: 5 cột sha trên `runs`, `runs/verification.py` (951 dòng), `specs_fingerprint`, chữ ký nguồn demo. 21 file test dùng verification, 50 file test có sha256. | Bỏ hash kiểm chứng (mục 6). |
| G6 | Tối ưu DB: tách bảng cho ít thông tin, ví dụ cấu hình item riêng, cấu hình nhà cung cấp riêng. | 28 bảng. `supplier_item_policies` gộp cấu hình item và supplier (13 cột); `runs` 28 cột; `inventory_daily` 25 cột; hai bảng kho song song `warehouses` (46 kho giả định) và `ops_warehouses` (kho thật). | Tách bảng (mục 5). |

## 2. Cấu trúc FE mới (G2, G3)

Tách 8 tab của `Operations` thành trang riêng trên menu. Dự báo và kịch bản gom thành một mục ở cuối menu.

**Admin**

| Nhóm menu | Trang |
|---|---|
| — | Tổng quan: tồn thấp, đơn nhập sắp về/trễ, yêu cầu đại lý chờ duyệt, thao tác gần đây |
| Kho | Tồn kho · Chứng từ (nhập/xuất/kiểm kê) · Kho hàng |
| Nhập hàng | Đơn nhập (có điều chỉnh ETA) · Đề xuất nhập · Nhà cung cấp |
| Đại lý | Danh sách đại lý · Yêu cầu lấy hàng |
| Danh mục | Sản phẩm (gộp cấu hình sản phẩm thật và cấu hình chính sách) |
| Hệ thống | Tài khoản · Lịch sử thao tác |
| Công cụ | Dự báo & kịch bản: tab Dự báo, Kịch bản, Kết quả mô phỏng (tồn/nhập/cảnh báo của run) |

**Đại lý:** Tổng quan · Đặt yêu cầu lấy hàng · Yêu cầu của tôi · Tồn của tôi · Tài khoản.

Quy tắc:

- Logic chọn run, bộ lọc "Phương án", nút "Tạo phương án" và nhãn "Dữ liệu mô phỏng" chỉ có trong mục Công cụ. Trang quản lý không gọi `/runs`.
- Giữ cơ chế điều hướng hiện có (`utils/url`), không thêm thư viện router. Link cũ dạng `#forecast`, `#scenarios`… chuyển về đúng tab trong Công cụ.
- Tái dùng `Table`, `State`, `Dialog`, form và component hiện có.
- Trang Tổng quan cần một API tổng hợp mới ở backend, chỉ đọc sổ kho thật.

## 3. Nghiệp vụ đại lý — giả định (G1, quyết định A, B)

- Mỗi tài khoản đại lý gắn đúng một đại lý. Đại lý chỉ đọc và ghi dữ liệu của chính mình; lọc theo đại lý trước phân trang.
- Đại lý xem danh mục SIM/eSIM đang hoạt động và tồn khả dụng của kho công ty. Không thấy nhà cung cấp, đơn nhập hay chứng từ nội bộ.
- Luồng yêu cầu lấy hàng: đại lý gửi yêu cầu → admin duyệt hoặc từ chối có lý do → admin chọn kho và xuất kho bằng chứng từ xuất hiện có → đại lý xác nhận đã nhận. Đại lý hủy được khi yêu cầu chưa duyệt. *Khi triển khai (16/11) bỏ trạng thái nháp để gọn; giỏ hàng nằm ở trình duyệt đến khi gửi.*
- Tồn của đại lý = tổng số lượng đã xác nhận nhận. Chưa ghi nhận bán ra của đại lý.
- Admin quản lý đại lý (tạo, sửa, ngưng hoạt động) và tài khoản đại lý.
- **Bỏ đăng nhập của vai trò `supplier`.** Nhà cung cấp giữ nguyên là dữ liệu của đơn nhập. Tài khoản supplier cũ được vô hiệu hóa, không xóa.
- Ngoài phạm vi: công nợ, giá bán, đại lý cấp 2, báo bán ra, trả hàng.

## 4. Điều chỉnh ETA (G4)

- Admin điều chỉnh ETA của đơn đã xác nhận và chưa nhận đủ. Bắt buộc nhập lý do; ETA mới không trước ngày đặt.
- Dùng `version` hiện có để chống ghi đè; ghi `ops_audit_events` với ETA cũ, ETA mới, lý do.
- Đề xuất nhập và Tổng quan đọc ETA hiện hành. Đơn trễ (quá ETA chưa nhận đủ) hiện rõ trên Tổng quan.
- Lead time của nhà cung cấp vẫn chỉ áp cho đơn mới.

## 5. Tách bảng DB (G6)

Danh sách đề xuất; mỗi bảng được rà nghiệp vụ trước khi viết migration.

- `supplier_item_policies` → `item_settings` (ROP floor, số ngày an toàn, horizon cảnh báo, lượng nhập cố định) và `supplier_item_terms` hoặc cột tại `ops_supplier_settings` (MOQ, lead time). Giữ khả năng đọc phiên bản cũ cho run lịch sử.
- `runs` → `runs` (định danh, trạng thái, thời gian) + `run_configs` (snapshot cấu hình) + `run_results` (tóm tắt, manifest, lỗi).
- Xem gộp `warehouses` (kho giả định theo tuyến) với `ops_warehouses`. Nếu không gộp được thì ghi rõ lý do.
- `inventory_daily`: xem tách phần tính chính sách (SS, ROP, target, khuyến nghị) khỏi phần số dư.
- Migration nối tiếp `0011_operational_inventory`, có downgrade, chạy trên DB thử có dữ liệu synthetic. Không xóa dữ liệu cũ.

**Kết quả M4 (16/11):** khi rà nghiệp vụ thấy `supplier_item_policies` vốn đã là cấu hình theo sản phẩm (khóa theo item), còn cấu hình nhà cung cấp đã nằm riêng. M4a (0015) đổi tên thành `item_policies` và `supplier_settings`, bỏ cột `supplier_id` thừa. Theo quyết định người dùng, việc tách `runs` gộp vào M5 để chỉ viết lại test một lần. Không gộp hai bảng kho (rủi ro cao, người dùng không chọn); `inventory_daily` giữ nguyên.

## 6. Bỏ hash (G5, quyết định C)

- Bỏ: các cột `source_sha256`, `code_sha256`, `config_sha256`, `request_sha256`, `selection_sha256` của `runs`; `runs/verification.py`; `specs_fingerprint`; chữ ký nguồn demo; `parent_bundle_sha256`. Sửa hoặc xóa test tương ứng.
- Giữ: `password_hash`, `token_digest` của phiên đăng nhập (bảo mật); `request_key` chống bấm gửi hai lần; checksum file backup nếu còn dùng.
- Run cũ vẫn mở và đọc được kết quả.

## 6a. Thời gian nhập theo nhà cung cấp (G8, bổ sung 16/11, đã làm)

Mentor để mặc định 7 ngày cho mọi nhà cung cấp, cần chỉnh được từng nhà cung cấp và áp xuống toàn bộ sản phẩm của nhà cung cấp đó. Phần quản lý đã có từ trước (đơn mới, đề xuất nhập). Bổ sung cho kịch bản mô phỏng: run mới chốt `supplier_lead_times` vào snapshot; ROP = nhu cầu dự báo trong thời gian nhập + SS, mức mục tiêu thêm ngày kế tiếp, ngày về lô = ngày đặt + thời gian nhập. Giới hạn 1–13 ngày cho mô phỏng (H14). Run cũ không có khóa này giữ 7 ngày. Migration `0014_supplier_lead_simulation` nới ràng buộc `replenishment_orders`.

## 6b. Tối ưu worker (G7, bổ sung 16/11)

Góp ý bổ sung của mentor do người dùng thuật lại: không tính lại cơ sở phân bổ 90 ngày ở mỗi ngày mới; tính ở ngày đầu rồi dùng lại cho các ngày sau, **chấp nhận sai số**.

Hiện trạng đã kiểm trong code (16/11):

- Commit `52a96e2` mới **index tổng dự báo** (`index_prediction_totals`) và dùng lại ma trận lịch sử theo tuyến. Bản chất chưa đổi: `forecast_run` vẫn gọi `allocate()` cho **mỗi origin × mỗi tuyến** (replay 185 × 46 = 8.510 lần). Mỗi lần cắt lại 90 ngày, tính trọng số thứ và tỷ trọng SKU 30/90 ngày, rồi dựng từng dòng bằng vòng lặp Python và ghi COPY từng dòng (khoảng 2,38 triệu dòng `item_forecasts`).
- Worker tồn kho (`inventory/simulation.py`) lặp theo **ngày × item**, và mỗi lượt lại: quét toàn bộ danh sách policy (`policy_at`), cắt lại lịch sử (`history_at`), cộng lại lượng đang về. Run kịch bản luôn đọc và pivot toàn bộ `daily_sales` của nguồn, kể cả khi chỉ cần một ngày.
- `runs/verification.py` tính lại kết quả sau khi chạy, khoảng gấp đôi thời gian; phần này bỏ ở M5.

Việc cần làm (mỗi việc đo thời gian trước–sau trên cùng dữ liệu synthetic, ghi số đo vào development):

| Mã | Việc | Ảnh hưởng kết quả |
|---|---|---|
| W1 | Tách `allocate()` thành `build_basis` (trọng số thứ 90 ngày, tỷ trọng SKU 30/90 ngày) và `apply_totals`. Tính basis **một lần ở origin đầu** của run cho mỗi tuyến, các origin sau dùng lại; SKU mới xuất hiện sau origin đầu thì basis tuyến đó được tính lại. Lưu ngày tính basis vào `item_forecasts` để truy vết. | **Có sai số chủ đích** so với tính lại hằng ngày; ghi mức chênh (MAE theo item-ngày) cho replay. Tổng tuần vẫn bảo toàn. Run cũ giữ nguyên. |
| W2 | Dựng dòng phân bổ bằng numpy (ma trận ngày × SKU) thay vì vòng lặp dict, ghi COPY theo khối. | Không đổi số. |
| W3 | Worker tồn: index policy theo item một lần; tính sẵn lịch sử theo item; giữ tổng lượng đang về thay vì cộng lại mỗi ngày. | Không đổi số. |
| W4 | Run kịch bản chỉ đọc `daily_sales` của khoảng ngày cần dùng. | Không đổi số. |

W2–W4 phải cho kết quả giống hệt bản cũ. W1 đổi kết quả có chủ đích nên cần người dùng xem mức chênh trước khi nhận.

## 7. Thứ tự và cổng mỗi bước

| Bước | Nội dung | Kiểm tối thiểu |
|---|---|---|
| M1 | Cấu trúc FE mới, tách trang quản lý, mục Công cụ, Tổng quan mới | Vitest + build, xem web ở desktop và 390px |
| M2 | Vai trò đại lý: DB, API, quyền, giao diện đại lý | pytest phân quyền/luồng yêu cầu, Vitest, build |
| M3 | Điều chỉnh ETA | pytest version/audit/ETA hợp lệ, Vitest |
| M4 | Tách bảng DB | pytest + migrate up/down trên DB thử, run cũ đọc được |
| M5 | Bỏ hash, gỡ `verification.py`, tách `runs` (snapshot/kết quả sang bảng riêng) | pytest toàn bộ, run cũ đọc được |
| M6 | Rà loading/skeleton trên giao diện mới | Xem web, Vitest |
| M7 | Tối ưu worker W1–W4 (mục 6b) | pytest, số đo trước–sau, mức chênh của W1 |

Mỗi bước dừng để người dùng xem trước khi sang bước sau. Chỉ commit/push khi người dùng giao. Không ghi DB demo, refit hay deploy.

## 8. Tiêu chí nghiệm thu

- Đăng nhập admin thấy menu quản lý ở mục 2; mục Công cụ là mục duy nhất có run/kịch bản.
- Đăng nhập đại lý chỉ thấy 5 trang của đại lý và dữ liệu của mình; gọi API của đại lý khác bị từ chối.
- Luồng yêu cầu lấy hàng chạy đủ: tạo → gửi → duyệt → xuất kho → đại lý xác nhận, tồn kho công ty giảm đúng số lượng.
- Admin đổi ETA đơn đã xác nhận, có lý do và audit; xung đột version bị chặn.
- Không còn cột sha kiểm chứng trên `runs` và không còn `verification.py`; mật khẩu và phiên vẫn được hash.
- Cấu hình item và cấu hình nhà cung cấp nằm ở bảng riêng; migration up/down qua trên DB thử.
- Mọi trang có trạng thái tải, lỗi, rỗng.
