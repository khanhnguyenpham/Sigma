# SIGMA — Dự báo nhu cầu và lập kế hoạch tồn kho SIM/eSIM

SIGMA hỗ trợ theo dõi nhu cầu bán, lập kế hoạch tồn kho, đề xuất nhập hàng và cảnh báo nguy cơ cạn hàng. Hệ thống kết hợp **dự báo nhu cầu** với **tồn hiện có, lô đang về và cấu hình sản phẩm** để giải thích khi nào cần bổ sung, bổ sung bao nhiêu và hàng có về kịp hay không.

Dự án là bài thực tập, dùng dữ liệu bán giả định và lô nhập mô phỏng. **Dự án chỉ chạy trên máy cá nhân (local); không có bản demo hay bản host công khai.** Cách cài đặt và chạy xem ở mục [Chạy trên máy](#chạy-trên-máy).

## Bài toán hệ thống giải quyết

- Sản phẩm nào cần nhập thêm và lượng nhập mỗi lần là bao nhiêu?
- Lô đang về đã đủ lượng và có về trước lúc dự kiến cạn không?
- Trong 14 ngày tới, sản phẩm có nguy cơ xuống ngưỡng nhập hoặc cạn hàng không?
- Kế hoạch thay đổi thế nào khi chủ động ngừng nhập hoặc nhà mạng ngừng dịch vụ?

SIGMA theo dõi từng sản phẩm theo SKU, loại SIM/eSIM, nhà cung cấp và kho. Cạn hàng được xét cho từng sản phẩm tại kho tương ứng.

## Các chức năng chính

| Chức năng | Nội dung |
| --- | --- |
| Quản lý sản phẩm | Cấu hình ngưỡng nhập tối thiểu, số ngày tồn an toàn, lượng nhập mỗi lần và kho nhận mặc định. |
| Dự báo nhu cầu | Xem nhu cầu dự báo, phân bổ xuống sản phẩm/ngày và so sánh với số bán nguồn khi có dữ liệu đối chiếu. |
| Kịch bản | Lưu phiên bản thiết lập và lịch ngừng riêng, chạy/xem kết quả tại một trang; xóa phiên bản đã chạy vào thùng rác và khôi phục khi cần. |
| Tồn kho và nhập hàng | Theo dõi tồn, lượng đang về, lô nhập mô phỏng, ngày đặt và ETA. |
| Sổ kho theo chứng từ | Kho, sản phẩm, nhà cung cấp, đơn nhập, nhận hàng (kể cả quét QR), xuất, kiểm kê và lịch sử thao tác; đề xuất nhập kết hợp số dư, đơn đang về và dự báo. |
| Đại lý | Cổng riêng cho đại lý xem hàng, gửi và theo dõi yêu cầu lấy hàng; admin duyệt và xuất kho. Nghiệp vụ đại lý là giả định của nhóm. |
| Lịch cung cấp | Cấu hình ngừng nhập nội bộ hoặc nhà mạng ngừng dịch vụ riêng trong từng phiên bản kịch bản. |
| Cảnh báo và báo cáo | Xem nguy cơ xuống ngưỡng/cạn hàng, lý do quyết định và xuất CSV theo lượt chạy. |

## Ba loại công việc trong kịch bản

| Công việc | Cách hoạt động |
| --- | --- |
| **Kế hoạch tồn kho** | Tính ngưỡng, khuyến nghị nhập và chiếu tồn 14 ngày tại một mốc từ tồn cùng các lô đã biết; chưa coi khuyến nghị là lô đã đặt. |
| **Kế hoạch nhập hàng** | Mô phỏng bán, đặt lô và nhận hàng theo ETA; cập nhật quyết định và cảnh báo từng ngày. |
| **Kiểm tra cảnh báo** | Đối chiếu cảnh báo với sự kiện cạn trong hồi cứu để đo khả năng báo sớm; không tự tạo lô mới trong cửa sổ đánh giá. |

Lưu thiết lập không tự chạy công việc. Mỗi lượt chạy chốt đầu vào và cấu hình riêng, nên sửa thiết lập hiện tại không viết lại kết quả đã lưu.

Lượt mới tạo từ giao diện chỉ lấy lịch ngừng của phiên bản kịch bản được chọn. Để trống để chạy bình thường; xóa lịch rồi lưu phiên bản mới để reset. Lịch dùng chung trước đây vẫn được giữ trong kết quả lịch sử.

## Luồng xử lý tổng quát

1. Chuẩn bị nguồn bán và dự báo nhu cầu từ nền mô hình M2.
2. Phân bổ dự báo theo sản phẩm và ngày để có nhu cầu cho 14 ngày tiếp theo.
3. Kết hợp nhu cầu với tồn, lô đang về, chính sách nhập và lịch cung cấp đã chốt.
4. Worker tính kế hoạch, kiểm chứng kết quả rồi lưu tồn, lô nhập và cảnh báo.
5. Giao diện đọc kết quả qua API để hiển thị bảng, biểu đồ, chi tiết và CSV.

Mô hình dự báo **nhu cầu bán**. Ngày dự kiến cạn được suy ra từ nhu cầu đó cùng tồn và lịch nhận hàng.

Các khái niệm chính:

- **SS:** lượng dự phòng, tính từ số ngày tồn an toàn và mức nhu cầu dự báo.
- **ROP:** ngưỡng xét bổ sung, lấy giá trị lớn hơn giữa nhu cầu dự báo 7 ngày cộng SS (làm tròn lên) và ngưỡng nhập tối thiểu.
- **IP:** tồn hiện có cộng lượng đang về, dùng để tránh đặt thêm khi đã đủ hàng theo chính sách.
- **Q:** lượng một lô nhập cố định đã cấu hình, sau khi áp các ràng buộc cung cấp.
- **ETA:** ngày dự kiến nhận lô. Run mô phỏng L7 cũ dùng 7 ngày sau ngày đặt; đơn vận hành mới chốt theo mặc định supplier lúc lập đơn. Quyết định mô phỏng được xét hằng ngày.

Cảnh báo cạn nhìn trước 14 ngày. Nếu dự kiến cạn sau ít nhất 7 ngày thì xếp loại **sớm**; dưới 7 ngày thì xếp loại **khẩn**. Cảnh báo dưới ROP được phân biệt với cảnh báo tồn về 0.

## Xử lý ngừng cung cấp

| Trường hợp | Hành vi |
| --- | --- |
| **Ngừng nhập nội bộ** | Chặn đặt lô mới từ ngày hiệu lực tại kho; vẫn bán tồn được phép bán và nhận các lô đã đặt. |
| **Nhà mạng ngừng dịch vụ** | Thông báo mới áp dụng cho cùng SKU và loại sản phẩm của nhà mạng tại mọi thị trường/kho hiện có. Xét ETA và khả năng bán trước hạn; từ ngày hiệu lực chặn cả nhập và bán mới. |

Lô đã đặt không tự bị hủy hoặc từ chối nhận. Nếu về sau hạn ngừng dịch vụ, lượng hàng đó có thể trở thành tồn bị chặn bán. Ngày biết thông báo và ngày hiệu lực được lưu riêng để tránh sử dụng thông tin tương lai cho quyết định quá khứ.

## Kiến trúc hệ thống

```mermaid
flowchart LR
    FE[React / TypeScript] --> API[FastAPI]
    API <--> DB[(PostgreSQL)]
    API --> Queue[Redis Streams khi bật]
    Queue --> Worker[Python worker]
    Worker <--> DB
    Worker --> Files[Snapshot và tệp kết quả]
```

API kiểm tra yêu cầu và lưu công việc trong bảng `runs` của PostgreSQL. Có hai driver: PostgreSQL mặc định cho tương thích, hoặc [Redis Streams](docs/REDIS_QUEUE.md) làm transport khi bật (Compose dùng Redis). Run queued đã commit là ý định công việc bền; worker claim tại PostgreSQL, tính toán/kiểm chứng rồi mới hoàn tất. Chỉ chạy một driver/owner trong mỗi stack. FE theo dõi trạng thái và đọc kết quả qua API.

| Thành phần | Vị trí |
| --- | --- |
| Mô hình và đánh giá dự báo nền | `M2/` |
| Giao diện React | `web/frontend/` |
| API, worker và nghiệp vụ | `web/backend/` |
| Tài liệu đặc tả M3 | `M3/docs/` |

## Chạy trên máy

SIGMA chạy local gồm PostgreSQL, API FastAPI, worker Python và giao diện React. Mã nguồn không kèm dữ liệu bán, database, credential hay tài khoản mặc định.

1. Đặt bản CSV order được cấp phép tại `data/sigma_sim_data_orders.csv` (xem [quy định dữ liệu](data/README.md)).
2. Cài môi trường và nâng DB tới migration `0017` theo [hướng dẫn cập nhật local](docs/UPDATE_LOCAL.md), hoặc dùng [gói container local](docs/LOCAL_CONTAINER.md) để có môi trường tách biệt.
3. Tạo tài khoản admin đầu tiên theo [đăng nhập và phân quyền](docs/AUTHENTICATION.md). Có thể nạp [dữ liệu thử dùng chung](docs/UPDATE_LOCAL.md#dữ-liệu-thử-dùng-chung) cho DB thử còn trống.

Đẩy code lên GitHub không làm thay đổi web đang chạy trên máy của từng thành viên; mỗi người tự kéo code và cập nhật theo hướng dẫn trên.

## Tài liệu chi tiết

- [Bảng yêu cầu và trạng thái hiện hành](docs/PRODUCT_STATUS.md)
- [Nghiệp vụ và công thức](M3/docs/01-functional-spec.md)
- [Mô hình dữ liệu và ERD](M3/docs/02-data-model.md)
- [Backend, API và worker](M3/docs/03-backend-api.md)
- [Giao diện và luồng thao tác](M3/docs/04-frontend-spec.md)
- [Vòng đời cung cấp sản phẩm](M3/docs/07-product-supply-lifecycle.md)
- [Sổ kho](docs/WAREHOUSE_OPERATIONS.md), [đề xuất nhập](docs/OPERATIONS_PLANNING.md) và [nhận lô bằng QR](docs/RECEIPT_QR.md)
- [Mô hình dự báo M2 và kết quả](M2/reports/final_m2_20261011/README.md)
- [Kiểm tra và bàn giao từng thay đổi](docs/development.md)
