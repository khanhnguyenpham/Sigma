# Đăng nhập và phân quyền SIGMA

Bản nâng cấp ngày 14/11/2026. Đọc cùng [PLAN](planning/PRODUCT_UPGRADE_PLAN_20261114.md). Đây là phần triển khai trên nhánh phát triển; chưa tự cập nhật bản public hoặc DB demo cũ.

## Quyền hiện có

| Tài khoản | Được làm | Giới hạn |
| --- | --- | --- |
| Admin | Sản phẩm, tồn, kịch bản, dự báo, cảnh báo, cấu hình, snapshot, CSV; tạo/khóa/mở khóa tài khoản | Không tự khóa tài khoản đang sử dụng. Không có đăng ký công khai. |
| Nhà cung cấp | Cổng riêng xem sản phẩm của mình và các lô mô phỏng gắn với chính sách của mình | Chỉ đọc. Không xem API quản trị, chạy kịch bản, snapshot toàn hệ thống hoặc CSV của run. Chưa có quyền sửa ETA/nhập QR. |
| Chưa đăng nhập | Màn hình đăng nhập, static FE, health/live/ready | Không đọc hoặc ghi dữ liệu nghiệp vụ. Health không trả credential hoặc đường dẫn private. |

Quyền supplier chỉ đọc là phạm vi tối thiểu của bước triển khai hiện tại, chưa chốt quyền supplier sửa ETA/tạo chứng từ ở D04–D06. Mapping sản phẩm theo nhà mạng của kho nguồn; lô theo supplier của chính sách đã dùng cho lô. Không suy quyền từ kho nhận hàng hoặc tham số do trình duyệt gửi. Bộ lọc SQL áp dụng trước đếm tổng và phân trang.

Lô đang hiển thị vẫn là **mô phỏng theo từng phương án**. Không cộng các lô từ nhiều run thành đơn mua thực tế; portal chưa tiếp nhận đơn mua hay gửi hàng thật.

## Khởi tạo môi trường mới

Dùng Python3.12 và PostgreSQL18. Các bước này dành cho môi trường được người vận hành chọn; không tự migrate DB cũ trước khi sao lưu/rehearsal.

```powershell
python -m pip install -r web/backend/requirements.txt
python -m pip install --no-deps -e web/backend
# Cấp M3_DATABASE_URL bằng secret manager hoặc env riêng, không commit vào Git.
python -m alembic -c web/backend/alembic.ini upgrade head
python -m modules.auth.bootstrap
```

Lệnh bootstrap hỏi tên và mật khẩu qua terminal, không đặt mật khẩu trong dòng lệnh. Chỉ tạo admin đầu tiên; nếu đã có admin thì từ chối. Không seed tài khoản/mật khẩu mặc định. Admin đăng nhập rồi chọn **Tài khoản** để tạo người dùng khác; mật khẩu mới tối thiểu12, tối đa128 ký tự.

`Settings.from_env()` luôn bật authentication, bao gồm startup local và demo. `Settings(..., auth_required=False)` chỉ là cách dựng profile tương thích cho unit/integration test cũ; không có biến môi trường tắt auth khi chạy ứng dụng. Cổng supplier vẫn từ chối nếu không có identity, kể cả profile test tắt auth.

## Phiên và API

- Phiên8giờ, token ngẫu nhiên chỉ lưu digest trong DB. Cookie `sigma_session`, HttpOnly, SameSite=Lax, path `/api/v1`; bật Secure khi FE cấu hình HTTPS hoặc request HTTPS. Host FE/API cùng origin để cookie và CSV hoạt động; proxy phải truyền thông tin HTTPS đúng.
- `GET /api/v1/auth/session` trả người dùng hiện tại và CSRF token của phiên; không trả mật khẩu/digest. API ghi yêu cầu `X-CSRF-Token`; React tự gắn token trong bộ nhớ, không lưu mật khẩu/token vào localStorage.
- `POST /api/v1/auth/login` tạo phiên mới và thu hồi cookie phiên cũ của trình duyệt. Sai5lần trên cùng tài khoản khóa đăng nhập15phút. Thông báo sai tài khoản/mật khẩu thống nhất. Không có tài khoản thì không tạo phiên.
- `POST /api/v1/auth/logout` thu hồi phiên tại DB rồi xóa cookie. Khóa tài khoản thu hồi toàn bộ phiên. Mở khóa không khôi phục token cũ. Phiên hết hạn hoặc bị khóa bị từ chối ở request tiếp theo.
- `GET/POST /api/v1/auth/users`, `PATCH /api/v1/auth/users/{key}` chỉ admin. API chỉ xuất trường business an toàn. Không có public signup hoặc chức năng reset mật khẩu trong phiên bản này; cần bổ sung luồng reset trước khi vận hành rộng.
- `GET /api/v1/supplier/products`, `GET /api/v1/supplier/shipments` chỉ supplier; không tin `supplier_id` từ URL để đổi quyền.
- Portal mới mặc định xem đơn vận hành qua `/api/v1/supplier/orders`, `/orders/{id}` và `/operational-products`. Chỉ đọc đúng supplier, không lộ ghi chú nội bộ hoặc cho ghi sổ. Các API mô phỏng trước giữ tương thích. Xem [vận hành kho](WAREHOUSE_OPERATIONS.md).

Password hash (Argon2) và digest token đăng nhập là cơ chế bảo vệ credential; không thuộc yêu cầu bỏ fingerprint code/artifact ở D03.

## Migration và dữ liệu cũ

Revision `0010_auth_sessions` thêm `auth_users` và `auth_sessions`, index theo user/hạn phiên; không thêm chủ sở hữu giả cho run cũ hoặc sửa kết quả mô phỏng. Run cũ mặc định chỉ admin đọc. Downgrade từ chối nếu còn tài khoản hoặc phiên để tránh mất dữ liệu đăng nhập. Các migration nghiệp vụ trước vẫn giữ guard dữ liệu của chúng.

## Cần hoàn thiện trước khi host

Chọn hạ tầng/URL/budget theo D07, HTTPS và reverse proxy cùng origin; quản lý secret, backup/restore cả bảng auth, rotation/reset password, dọn phiên hết hạn và rate limit đăng nhập theo client đáng tin cậy. Chưa có bằng chứng triển khai public bản nâng cấp này. Không coi test synthetic là kiểm tải hoặc kiểm an ninh độc lập cho production.
