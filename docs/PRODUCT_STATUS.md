# Trạng thái sản phẩm SIGMA — 15/11/2026

Đây là bảng đối chiếu hiện hành để nhóm đọc trước các checkpoint lịch sử. Mã nguồn dùng nhánh **main**. Bản mã được kiểm là **52a96e2c5bb446664b0505f28636317098896fb2**; các commit chỉ cập nhật tài liệu sau mốc này không phải một lần chạy lại mô hình.

## Yêu cầu và kết quả

| Yêu cầu của nhóm | Đã triển khai và kiểm | Giới hạn còn lại |
| --- | --- | --- |
| UI quản lý bằng React | Menu vận hành/kế hoạch, form chứng từ, phân trang, màn hình nhỏ và bàn phím; bảng có vùng cuộn riêng. | Chưa thay UAT với người dùng thực hoặc kiểm mọi thiết bị. |
| Đăng nhập admin và nhà cung cấp | Phiên cookie, CSRF, phân quyền theo supplier trước phân trang, quản lý tài khoản, đổi mật khẩu và khôi phục qua operator. | Supplier chỉ đọc; chưa có tự đăng ký hoặc khôi phục qua email. |
| Nhập SIM vật lý theo QR | QR theo phiếu giao/lô, tạo SVG tại máy chủ, đọc bằng máy quét bàn phím hoặc dán mã, đối chiếu rồi xác nhận nhận hàng. | Chưa quét camera hoặc quản lý ICCID từng SIM. QR không phải chữ ký của supplier. |
| Quản lý tồn thực | Kho/SKU, đơn nháp→xác nhận→nhận thiếu/đủ, xuất, kiểm kê, sổ chứng từ và audit; khóa dòng, version, idempotency và ghi nguyên tử. | Chưa có chuyển kho, trả hàng, tiền hàng hoặc đồng bộ đơn bán. Đây là phần mở rộng, không giả tồn mô phỏng thành tồn đã kiểm kê. |
| Thời gian hàng về theo supplier | Mặc định 7 ngày, admin chỉnh 1–365 ngày cho đơn mới; ETA đã chốt trong đơn được giữ nguyên. Tư vấn dùng lead time hiện hành. | Forecast thiếu số ngày cần thiết thì chặn tư vấn; không nối H14 thành 30/365 ngày bằng giả định. Run L7 cũ giữ hợp đồng cũ. |
| Loading/skeleton và dữ liệu trống | Trạng thái tải/lỗi/rỗng riêng, retry, giữ nháp, số 0 không bị coi là thiếu; bảng rỗng có thông báo. | Không xem số test là bảo đảm mọi lỗi mạng/thiết bị đều đã gặp. |
| Xem snapshot trên FE | Modal chỉ đọc chia mục, allowlist dữ liệu, phiên bản/nguồn và cấu hình frozen tách với cấu hình hiện tại. | Trang tư vấn sổ kho là phép đọc hiện tại, chưa lưu thành snapshot hoặc tự tạo đơn. |
| Bỏ hash ở backend | Image có release version dùng tham chiếu bất biến, bỏ quét source/gọi Git trong đường kiểm phiên bản. Local còn sửa mã vẫn có guard. | Giữ password hash, checksum nguồn/artifact, idempotency và khả năng đọc hash lịch sử. |
| Tối ưu DB/kịch bản | Query sổ kho theo trang, index/unique theo phạm vi, tư vấn đọc theo batch và transaction nhất quán; kịch bản dùng forecast cha đã hoàn tất. | Chưa có số đo tải lớn/p95 của toàn DB hoặc toàn pipeline; không công bố mức tăng tốc chưa đo. |
| Worker và Redis queue | Redis Streams, Run queued trong PostgreSQL là ý định công việc bền, publish lại/ACK/reclaim; chặn ghi đè trạng thái terminal. | Worker một owner; công việc bị gián đoạn phải retry thành run mới. Không tuyên bố đa-worker hoặc exactly-once. |
| Phân bổ một lần tại ngày chốt | Trọng số lịch sử 90 ngày theo từng origin; tổng forecast được index một lần, input tuyến được tái sử dụng; các kịch bản đọc item forecast đã lưu. | Đây là lịch sử 90 ngày cho phân bổ, không phải một mô hình dự báo tổng 90 ngày mới. Origin khác cần cơ sở riêng để tránh leakage. |
| Host và bàn giao | Image chỉ chứa source/runtime, Compose có PostgreSQL/Redis/artifact volume, app role không superuser; đã kiểm startup và restore trong CI. | **Chưa có host public/HTTPS chạy 24/7 của bản mới.** Chưa có cấu hình hạ tầng triển khai ở checkout này. |
| R05 tổng 30 ngày và nghiệm thu | Giữ target, top 10, split, metric và lịch sử đã chốt. | **Chưa có dữ liệu nguồn/run riêng của nhóm trong checkout này để chạy lại và chứng minh 10/10. C00/R05/R07/T14 không tự đổi thành đạt.** |

## Bằng chứng của bản mã hiện hành

- [M3 synthetic integration](https://github.com/khanhnguyenpham/Sigma/actions/runs/43712696757): **success**, đủ backend, frontend, M2 regression và container. Backend **581 passed**, gồm Redis thật; React **163 passed**, TypeScript/build qua.
- [Synthetic tests](https://github.com/khanhnguyenpham/Sigma/actions/runs/43712696746): **success**. Đây là kiểm thử tổng hợp, không thay bằng chứng chất lượng dự báo trên nguồn của nhóm.
- Container thực sự build/start/migrate/login, kiểm role DB và Redis, tạo chứng từ synthetic rồi backup/restore sang DB riêng; đối soát balance/ledger/account và khôi phục một tệp artifact. Chưa diễn tập toàn bộ dữ liệu vận hành riêng của nhóm.
- Browser ở checkpoint trước: API/PostgreSQL thử riêng, QR xem trước không tăng tồn rồi nhận hàng có tăng tồn; tư vấn nhập, đổi mật khẩu, màn hình 390px và không có page error. Browser không được chạy lại chỉ vì sửa tài liệu.
- Benchmark synthetic lookup forecast: 46 tuyến × 185 origin, 17.020 dòng; lookup cũ **16,102 giây**, index kèm đối chiếu 8.510 nhóm **1,683 giây**, tổng bằng nhau. Chỉ đo lookup, không phải thời gian fit/chạy toàn hệ thống.

## Nhóm kéo về và chạy

1. Dùng [hướng dẫn cập nhật local](UPDATE_LOCAL.md) nếu máy đã có DB; backup trước, pull main, cài dependency, build FE, migrate tới `0011_operational_inventory` và khởi động đúng stack.
2. Dùng [gói container local](LOCAL_CONTAINER.md) nếu muốn môi trường mới tách biệt. Tự tạo mật khẩu riêng, bootstrap admin; không có tài khoản mặc định hoặc dữ liệu đơn hàng đi kèm repo.
3. Đăng nhập → đăng ký kho/SKU → kiểm kê tồn đầu → lập/xác nhận đơn → xem/nhận từng phần → kiểm số dư và chứng từ. Chỉ dùng môi trường thử khi tập thao tác.
4. Tư vấn nhập cần nguồn và forecast hoàn tất đúng ngày, đủ horizon và policy. Khi thiếu, giao diện phải giải thích lý do; không tự lấy kết quả synthetic làm dữ liệu thực.

Tài liệu nghiệp vụ: [sổ kho](WAREHOUSE_OPERATIONS.md), [tư vấn nhập](OPERATIONS_PLANNING.md), [QR](RECEIPT_QR.md), [auth](AUTHENTICATION.md), [Redis](REDIS_QUEUE.md), [release identity](RELEASE_IDENTITY.md). [PLAN nâng cấp](planning/PRODUCT_UPGRADE_PLAN_20261114.md) giữ khảo sát ban đầu để truy vết; bảng trên là trạng thái hiện tại. Các lựa chọn triển khai theo ủy quyền người dùng không được ghi thành xác nhận nghiệp vụ của mentor.
