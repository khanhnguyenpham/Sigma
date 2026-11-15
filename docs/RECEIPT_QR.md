# Nhận SIM vật lý bằng QR phiếu giao

Quyết định triển khai mặc định khi người dùng giao tự chọn: **một QR cho một phiếu giao/lô**, không phải mã kích hoạt hoặc serial từng SIM. Định dạng `sigma-delivery-v1` chỉ gồm order_id, mã phiếu giao và danh sách dòng/số lượng.

Admin mở đơn đã xác nhận → Nhận hàng → nhập mã phiếu, số lượng thực nhận → **Nhận lô SIM vật lý bằng QR**. Có thể tạo QR từ phiếu đang nhập hoặc dùng máy quét QR dạng bàn phím/dán nội dung QR vào ô rồi chọn Đọc phiếu QR. Tạo/đọc QR chỉ điền và đối chiếu thông tin, chưa tăng tồn.

Người nhận kiểm tra lại số lượng/ngày nhận, sau đó bấm **Ghi nhận nhập kho**. API ghi sổ vẫn kiểm phiên bản, lượng còn thiếu, số dư, transaction và mã phiếu duy nhất. Gửi lại cùng phiếu không tạo hai lần. Khi đọc/tạo QR đang chạy, form không cho ghi sổ đồng thời.

QR khác đơn, dòng eSIM, payload kích hoạt, URL, trường thừa, JSON trùng khóa hoặc quá lớn đều bị từ chối; không mở URL hoặc tự tải nội dung ngoài. Mã phiếu đã nhận bị chặn; phiên bản form cũ không tự nâng theo QR mới. Không có mật khẩu hoặc token đăng nhập trong QR. QR không thay quyền admin/CSRF và không phải chữ ký xác thực của nhà cung cấp.

Ảnh QR SVG được tạo trong backend bằng [Segno1.6.6](https://pypi.org/project/segno/), dùng [API SVG chính thức](https://segno.readthedocs.io/en/stable/api.html). Không gửi nội dung phiếu sang dịch vụ tạo QR bên ngoài. Phiếu quá nhiều dòng cần tách QR nhỏ hơn.

Giới hạn: chưa có camera tích hợp, theo dõi ICCID/serial từng SIM, chữ ký đối tác hoặc parser QR riêng của nhà mạng. Không tự coi mã do nhà mạng phát hành là định dạng SIGMA. Nhập tay vẫn dùng được và không bị bắt buộc đổi dữ liệu lịch sử sang QR.
