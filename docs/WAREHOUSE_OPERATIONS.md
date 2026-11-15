# Vận hành kho theo chứng từ

**Bổ sung15/11:** Đã có [tư vấn nhập từ số dư thực](OPERATIONS_PLANNING.md), [QR phiếu giao SIM vật lý](RECEIPT_QR.md) và [đổi/khôi phục mật khẩu](AUTHENTICATION.md). Tư vấn là profile mới chỉ đọc, chưa tự tạo đơn hoặc lưu snapshot; không đổi run cũ. Các giới hạn phía dưới ghi nền trước cập nhật này; giới hạn chi tiết hiện hành ở từng tài liệu mới.

Phần mới ngày 15/11/2026: React, FastAPI và migration PostgreSQL đã có, kiểm trên dữ liệu synthetic riêng. Chưa triển khai vào demo cũ/public hoặc nghiệm thu toàn sản phẩm để vận hành rộng.

## Bắt đầu

Khởi tạo auth theo [AUTHENTICATION](AUTHENTICATION.md), nâng migration lên `0011_operational_inventory`. Không có tài khoản hoặc tồn kho mặc định. Admin mở trang gốc sẽ vào **Vận hành kho**; liên kết dự báo cũ vẫn mở đúng kết quả đã chọn.

1. Thêm kho vật lý ở **Kho hàng**, gồm mã duy nhất, tên và quốc gia.
2. Thêm SKU ở **Sản phẩm**: tên, loại SIM/eSIM, nhà cung cấp/nhà mạng, quốc gia sử dụng. Nhà cung cấp được tạo nếu chưa có. Không dựng lịch sử bán cho sản phẩm mới hoặc đổi định danh nguồn đã tồn tại.
3. Đổi **Thời gian nhập** tại **Nhà cung cấp**, từ1–365 ngày lịch, mặc định7. Đơn mới lưu lead time/ETA tại lúc lập; đổi mặc định không viết lại đơn đã có.
4. Nếu đã có hàng, dùng **Kiểm kê / tồn đầu**, nhập số lượng đếm thực tế, mã phiếu và lý do. Không lấy tồn mô phỏng làm số dư thực.

## Luồng chứng từ

| Thao tác | Kết quả |
| --- | --- |
| Tạo / sửa nháp | Chọn supplier, sản phẩm, lượng và kho từng dòng; chưa đổi tồn. |
| Xác nhận đơn | Chuyển sang chờ nhận, không sửa dòng đơn đã xác nhận; chưa tăng tồn. |
| Nhận hàng | Ghi mã phiếu giao, ngày và số thực nhận từng dòng. Nhận từng phần thì giữ phần còn thiếu; nhận đủ thì đóng đơn. |
| Hủy đơn / phần chưa nhận | Cần lý do; giữ toàn bộ hàng đã nhận và phiếu đã ghi. |
| Xuất kho | Lượng dương, không vượt tồn; kiểm lại số dư khi ghi sổ. |
| Kiểm kê | Nhập số đếm được, không nhập chênh lệch. Cho phép0; tự tính lượng điều chỉnh và tồn sau phiếu. |
| Chứng từ / lịch sử | Xem biến động, tồn sau phiếu và người thực hiện. Không sửa/xóa trực tiếp phiếu đã ghi sổ. |

Ngày sổ kho dùng **Asia/Ho_Chi_Minh (UTC+7)**; audit lưu thời điểm UTC. Không ghi ngày tương lai hoặc trước biến động gần nhất của cùng sản phẩm/kho. Quy tắc này không đổi ngày bán UTC của nguồn dự báo.

## Toàn vẹn và quyền

- Phiên bản đơn/số dư chống ghi đè khi hai người cùng thao tác. Dữ liệu đã đổi trả409; giữ form để người dùng tải lại và đối chiếu.
- Tạo đơn/ghi phiếu có `Idempotency-Key`: cùng mã/nội dung trả kết quả cũ, cùng mã/nội dung khác bị từ chối. React chặn nhấn lặp và giữ mã khi retry sau lỗi mạng.
- Khóa dòng đơn/số dư; cập nhật lượng nhận, chứng từ, ledger, balance và audit trong cùng transaction. Lỗi ở bước cuối rollback toàn bộ.
- Không nhận vượt phần còn thiếu, dùng dòng đơn khác hoặc xuất âm tồn. Mã phiếu giao duy nhất trong từng đơn. Sản phẩm ngừng nhập vẫn nhận đơn đã xác nhận và xuất tồn còn lại.
- Trigger PostgreSQL chặn UPDATE/DELETE trên phiếu, dòng phiếu và audit. Quản trị DB có quyền cao vẫn cần quy trình riêng.
- Giới hạn số lượng mỗi đơn/phiếu/số dư `2^53−1` để FE giữ đúng số nguyên. Tổng tồn lớn hơn trả chuỗi số nguyên, không ép float.
- Admin được ghi; supplier chỉ đọc đơn/sản phẩm của supplier gắn với tài khoản. Scope áp trước count/paging và kiểm khi mở chi tiết. Chưa cấp supplier quyền nhận hàng/sửa ETA.

## Dữ liệu và API

| Bảng mới | Vai trò |
| --- | --- |
| `ops_warehouses` | Kho vật lý, độc lập với `warehouses` đang đại diện tuyến nguồn ở nền cũ. |
| `ops_products` | Tên/trạng thái vận hành của item; giữ SKU/loại/tuyến nguồn đã có. |
| `ops_supplier_settings` | Lead time mặc định, phiên bản và người chỉnh. |
| `ops_purchase_orders` | Trạng thái, ngày đặt, ETA/lead time đã lưu, phiên bản và actor. |
| `ops_purchase_order_lines` | Sản phẩm/kho, lượng đặt và đã nhận. |
| `ops_stock_documents` | Phiếu nhập/xuất/kiểm kê đã ghi sổ. |
| `ops_stock_document_lines` | Delta và tồn sau phiếu; khóa ngoại ghép với dòng đơn. |
| `ops_stock_balances` | Tồn hiện tại và phiên bản theo kho vật lý/item. |
| `ops_audit_events` | Người thực hiện, thời điểm, đối tượng và nội dung. |

API admin dưới `/api/v1/operations`: summary, warehouses, products, suppliers/settings, orders/confirm/cancel/receipts, stock, issues, counts, documents, audit. Supplier dùng `/api/v1/supplier/orders`, `/orders/{id}`, `/operational-products`. API lô mô phỏng cũ giữ tương thích nhưng không phải sổ kho vận hành.

Migration0011 chỉ thêm bảng/index/trigger, không sửa source/run/snapshot cũ. Downgrade từ chối nếu bất kỳ bảng vận hành nào còn dữ liệu. Cần backup/rehearsal trước khi áp vào môi trường có người dùng.

## Phần còn thiếu

**Sổ kho chưa tự cấp tồn/lead time cho kế hoạch.** Các trang Dự báo & kế hoạch vẫn dùng run mô phỏng L7/R1/H14. Lead time30 của đơn mới không chứng minh ROP/cảnh báo cũ đã tính theo30. Tích hợp phải có profile mới, đủ vector dự báo và kiểm riêng; giữ kết quả lịch sử.

Chưa có QR theo SIM/lô, serial, gửi đơn cho đối tác, return/transfer, giá trị tiền hàng hoặc đồng bộ đơn bán. Xuất kho hiện là phiếu nhập tay. Redis/outbox, reset/rotation mật khẩu, host bền dữ liệu và diễn tập backup/restore bản nâng cấp còn thiếu. Xem [PLAN](planning/PRODUCT_UPGRADE_PLAN_20261114.md).

[Bàn giao kiểm thử](development.md#handoff-operational-ledger) chỉ là bằng chứng kỹ thuật trên synthetic, không thay nghiệm thu production hoặc nâng C00/R05/R07/T14.
