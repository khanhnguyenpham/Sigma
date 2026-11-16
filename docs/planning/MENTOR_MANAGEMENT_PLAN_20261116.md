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
- Luồng yêu cầu lấy hàng: đại lý tạo yêu cầu (nháp → gửi) → admin duyệt hoặc từ chối có lý do → admin xuất kho bằng chứng từ xuất hiện có → đại lý xác nhận đã nhận. Đại lý hủy được khi yêu cầu chưa duyệt.
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

## 6. Bỏ hash (G5, quyết định C)

- Bỏ: các cột `source_sha256`, `code_sha256`, `config_sha256`, `request_sha256`, `selection_sha256` của `runs`; `runs/verification.py`; `specs_fingerprint`; chữ ký nguồn demo; `parent_bundle_sha256`. Sửa hoặc xóa test tương ứng.
- Giữ: `password_hash`, `token_digest` của phiên đăng nhập (bảo mật); `request_key` chống bấm gửi hai lần; checksum file backup nếu còn dùng.
- Run cũ vẫn mở và đọc được kết quả.

## 7. Thứ tự và cổng mỗi bước

| Bước | Nội dung | Kiểm tối thiểu |
|---|---|---|
| M1 | Cấu trúc FE mới, tách trang quản lý, mục Công cụ, Tổng quan mới | Vitest + build, xem web ở desktop và 390px |
| M2 | Vai trò đại lý: DB, API, quyền, giao diện đại lý | pytest phân quyền/luồng yêu cầu, Vitest, build |
| M3 | Điều chỉnh ETA | pytest version/audit/ETA hợp lệ, Vitest |
| M4 | Tách bảng DB | pytest + migrate up/down trên DB thử, run cũ đọc được |
| M5 | Bỏ hash | pytest toàn bộ, run cũ đọc được |
| M6 | Rà loading/skeleton trên giao diện mới | Xem web, Vitest |

Mỗi bước dừng để người dùng xem trước khi sang bước sau. Chỉ commit/push khi người dùng giao. Không ghi DB demo, refit hay deploy.

## 8. Tiêu chí nghiệm thu

- Đăng nhập admin thấy menu quản lý ở mục 2; mục Công cụ là mục duy nhất có run/kịch bản.
- Đăng nhập đại lý chỉ thấy 5 trang của đại lý và dữ liệu của mình; gọi API của đại lý khác bị từ chối.
- Luồng yêu cầu lấy hàng chạy đủ: tạo → gửi → duyệt → xuất kho → đại lý xác nhận, tồn kho công ty giảm đúng số lượng.
- Admin đổi ETA đơn đã xác nhận, có lý do và audit; xung đột version bị chặn.
- Không còn cột sha kiểm chứng trên `runs` và không còn `verification.py`; mật khẩu và phiên vẫn được hash.
- Cấu hình item và cấu hình nhà cung cấp nằm ở bảng riêng; migration up/down qua trên DB thử.
- Mọi trang có trạng thái tải, lỗi, rỗng.
