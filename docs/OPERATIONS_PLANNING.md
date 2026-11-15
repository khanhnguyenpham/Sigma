# Đề xuất nhập từ sổ kho

Profile mới `ops_network_fixed_lot_h14_v1`, tách khỏi các run mô phỏng L7/R1/H14. Màn hình **Vận hành kho → Đề xuất nhập** là bản xem tại thời điểm yêu cầu, chưa lưu snapshot kế hoạch và chưa đặt đơn tự động. Không dùng làm bằng chứng nâng R05/R07/T14.

## Đầu vào và kỳ tính

- Tồn sổ cộng theo item trên tất cả kho vật lý, chỉ dùng một lần cho một dự báo. Đây là tư vấn toàn mạng, chưa giải bài toán vận chuyển giữa các kho.
- Chỉ dùng lượng chưa nhận của đơn đã xác nhận/nhận một phần; đơn nháp/hủy/nhận đủ không vào pending. ETA lấy từ chính đơn đã lưu, không tính lại bằng mặc định supplier mới.
- Lead time cho đơn định đặt lấy mặc định hiện tại của supplier. Chính sách lượng nhập cố định, ngưỡng tối thiểu và số ngày an toàn phải đang hiệu lực; chưa cấu hình thì không đề xuất số giả.
- Dự báo phải là run đã hoàn tất, nguồn cha đã hoàn tất và không có ngày quan sát tương lai. Chọn origin hôm nay hoặc hôm qua UTC, chỉ dùng ngày từ sau hôm nay UTC. Dự báo hôm qua còn13ngày thì giữ13, không chép thêm một ngày để đủ14.
- Giả định số dư hiện tại giữ tới đầu ngày UTC kế tiếp; chưa xử lý nhu cầu còn lại trong ngày. Đây không phải đồng bộ thời gian thực với đơn bán. Ngày nghiệp vụ nhận/xuất của sổ kho vẫn Việt Nam UTC+7; ETA được dùng theo ngày lịch trong tư vấn, không coi là giờ giao chính xác.

## Công thức và kết luận

SS = làm tròn lên nhu cầu bình quân các ngày dự báo còn đủ × số ngày an toàn. ROP = max(ngưỡng tối thiểu, làm tròn lên nhu cầu trong lead time + SS). IP xét đặt = tồn sổ + lượng dự kiến nhận trong lead time; pending đến muộn không dùng để che thiếu hàng sớm. Pending tổng vẫn được hiển thị để đối chiếu.

Nếu IP ≤ ROP, đề xuất đúng một lô cố định đã cấu hình; không tự đổi lượng lô hoặc nhân dự báo. Yêu cầu đủ vector liên tục ít nhất lead time +1ngày xét lại; lead30/365 khi forecast chỉ13–14ngày phải chặn. Không dùng tổng30 để giả tạo dự báo từng ngày dài hơn.

Chiếu tồn nhận đầu ngày, đáp ứng nhu cầu tối đa bằng hàng có, giữ tồn không âm và ghi nhu cầu chưa đáp ứng. Thiếu trước ETA mới có cảnh báo riêng vì đặt thông thường chưa cứu được. Lô đã quá ETA nhưng còn thiếu được tách **chưa rõ lịch về**, không giả đã nhận và không tự đề xuất mua trùng.

Có lịch ngừng nhập/ngừng dịch vụ đã biết trong kỳ thì chuyển sang kiểm tra thủ công; chưa tự áp cap tối ưu trong profile này. Lịch sử vẫn theo resolver nghiệp vụ đã có, không xóa hoặc viết lại.

## Tính nhất quán và giới hạn

API admin `/api/v1/operations/recommendations` dùng transaction **repeatable read, read only** và đọc batch theo trang. Không cập nhật balance/đơn/run/forecast. Supplier không được đọc tư vấn toàn mạng. Số thiếu trả null kèm lý do, không trả0 để giả đủ an toàn. Các tổng lớn được kiểm giới hạn số nguyên chính xác trên FE.

Chưa có snapshot tư vấn bền vững, nút chuyển tư vấn thành đơn, chuyển kho, phân bổ hạn mức và forecast mới dài hơn14ngày. Không coi phần tư vấn này là đã hoàn tất toàn bộ tích hợp/tối ưu tồn.
