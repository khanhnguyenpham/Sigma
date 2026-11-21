# Chức năng theo vai trò

SIGMA có hai vai trò đăng nhập được: **Admin** và **Đại lý**. Không có đăng ký công khai và không có tài khoản mặc định. Admin đầu tiên được tạo bằng lệnh trên máy (xem [đăng nhập và phân quyền](AUTHENTICATION.md)); các tài khoản còn lại do admin tạo trong ứng dụng.

| Vai trò | Ai dùng | Phạm vi dữ liệu |
| --- | --- | --- |
| Admin | Nhân viên vận hành kho, mua hàng và lập kế hoạch | Toàn bộ kho, sản phẩm, nhà cung cấp, đơn nhập, đại lý và công cụ dự báo |
| Đại lý | Đại lý bán lẻ lấy SIM/eSIM từ công ty | Chỉ dữ liệu của đại lý gắn với tài khoản |
| Nhà cung cấp | Đã ngừng từ migration `0012` | Không đăng nhập được; tài khoản cũ chỉ được giữ để truy vết |

Nghiệp vụ đại lý là **giả định của nhóm**, không phải yêu cầu đã được mentor xác nhận. Tồn, lô nhập, lead time và đối tác trong dữ liệu thử đều là mô phỏng.

## Admin

Menu bên trái chia thành các nhóm sau.

| Nhóm | Trang | Admin làm được gì |
| --- | --- | --- |
| — | Tổng quan | Xem các số liệu chính: tổng tồn sổ, đơn chờ nhận, đơn trễ hạn, đơn nháp, yêu cầu đại lý chờ xử lý, phiếu trong ngày. Bấm vào từng thẻ để mở trang tương ứng. |
| Kho | Tồn kho | Xem tồn theo từng kho (dạng thẻ kho) và từng sản phẩm; ghi phiếu xuất và kiểm kê. |
| | Chứng từ | Tra cứu phiếu nhận, xuất, kiểm kê theo loại, khoảng ngày và từ khóa. |
| | Kho hàng | Thêm, sửa, ngừng dùng kho. |
| Nhập hàng | Đơn nhập | Lập đơn nháp, xác nhận, đổi ETA (kèm lý do), hủy; nhận hàng đủ hoặc một phần, nhập tay hoặc quét mã QR của lô. |
| | Đề xuất nhập | Xem sản phẩm nào cần đặt thêm và đặt bao nhiêu, tính từ tồn toàn mạng, hàng đang về trong thời gian nhập và dự báo (hoặc ngưỡng tối thiểu khi chưa có dự báo). Đây là tư vấn, không tự tạo đơn. |
| Đại lý | Yêu cầu lấy hàng | Duyệt hoặc từ chối (kèm lý do) yêu cầu của đại lý, chọn kho rồi xuất hàng. |
| | Danh sách đại lý | Thêm, sửa, ngừng hoạt động đại lý; tạo tài khoản đăng nhập cho đại lý. |
| Danh mục | Sản phẩm | Thêm, sửa sản phẩm; cấu hình chính sách nhập (ngưỡng tối thiểu, số ngày tồn an toàn, lượng mỗi lô). |
| | Nhà cung cấp | Xem sản phẩm, tồn và chính sách theo nhà cung cấp; đặt lead time của nhà cung cấp. |
| Hệ thống | Lịch sử thao tác | Xem ai đã làm gì, lúc nào, lọc theo loại thao tác và ngày. |
| | Tài khoản | Tạo, khóa, mở khóa tài khoản. Không tự khóa được tài khoản đang đăng nhập. |
| Công cụ dự báo | Dự báo | Xem dự báo H14 theo tuyến và phân bổ xuống sản phẩm × ngày, so với số bán thực tế khi có. |
| | Kịch bản | Lưu phiên bản thiết lập và lịch ngừng cung cấp, chạy kế hoạch tồn, kế hoạch nhập hoặc kiểm tra cảnh báo, rồi xem kết quả. |
| | Tổng quan / Tồn / Nhập hàng mô phỏng, Cảnh báo | Xem kết quả của một lượt chạy mô phỏng: tồn chiếu 14 ngày, lô đặt và nhận, cảnh báo sớm hoặc khẩn; xuất CSV. |
| | Chính sách sản phẩm | Cấu hình sản phẩm dùng cho mô phỏng. |

Sổ kho (nhóm Kho, Nhập hàng, Đại lý, Danh mục) ghi vào dữ liệu vận hành thật của hệ thống. Công cụ dự báo đọc kết quả của các lượt chạy đã chốt; sửa thiết lập không viết lại kết quả cũ.

## Đại lý

Đại lý đăng nhập vào cổng riêng, không thấy menu của admin.

| Tab | Đại lý làm được gì |
| --- | --- |
| Tổng quan | Xem số yêu cầu theo trạng thái và các yêu cầu gần đây. |
| Đặt hàng | Xem sản phẩm đang kinh doanh và tổng tồn còn lại của công ty; lọc theo tình trạng, quốc gia, nhà mạng, loại SIM; thêm vào giỏ rồi gửi yêu cầu. Đặt vượt tồn vẫn gửi được nhưng có cảnh báo. |
| Yêu cầu của tôi | Theo dõi trạng thái từng yêu cầu, hủy khi còn chờ duyệt, xác nhận đã nhận hàng sau khi công ty xuất. |
| Tồn của tôi | Xem số hàng đã nhận về. |

Một yêu cầu đi qua các trạng thái:

```
Chờ duyệt ─┬─> Đã duyệt, chờ xuất ──> Đã xuất, chờ nhận ──> Đã nhận
           ├─> Từ chối      (admin, kèm lý do)
           └─> Đã hủy       (đại lý tự hủy)
```

Đại lý không xem được kho, nhà cung cấp, đơn nhập, công cụ dự báo hay dữ liệu của đại lý khác.

## Mọi tài khoản

- Đổi mật khẩu của chính mình từ menu tài khoản.
- Quên mật khẩu: liên hệ admin để được đặt lại.
- Chưa đăng nhập chỉ thấy màn hình đăng nhập, không đọc hay ghi được dữ liệu nghiệp vụ.
