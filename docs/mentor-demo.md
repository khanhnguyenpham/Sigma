# Trình diễn dashboard M3 cho mentor — 5–7 phút

## Chuẩn bị

Mở **http://127.0.0.1:8507/** trong trình duyệt. Dashboard hiện đang chạy trên máy này; không cần khởi động thêm một bản. Khi cần mở lại sau khi tắt máy, chạy từ thư mục project:

```powershell
.\.venv\Scripts\python.exe -m streamlit run sigma/ui/product30.py --server.address 127.0.0.1 --server.port 8507 --server.headless true
```

Để trình chiếu dễ đọc, mở URL trong cửa sổ trình duyệt rộng. Đặt quốc gia/nhà mạng = **Tất cả**, tình huống = **Cơ sở · nhận đủ, đúng hạn**. Trong **Lọc SKU**, đặt loại/SKU = **Tất cả** hoặc bấm **Đặt lại bộ lọc**. Không cần mạng để gọi mô hình khi trình diễn; kết quả và thư viện đã nằm trên máy.

**Câu mở đầu:** “Nhóm em xây dựng luồng từ dự báo lượng bán SIM/gói data theo tuyến đến khuyến nghị bổ sung từng mặt hàng. Đây là bản M3 chạy local trên snapshot 2024–2025; tồn kho là mô phỏng. Nhóm trình bày cả kết quả đã có và tiêu chí còn thiếu.”

## 1. Tổng quan — khoảng 45 giây

Mở **Tổng quan**. Chỉ bốn số ở phạm vi mặc định:

- Dự kiến bán 30 ngày tiếp theo: **6.027,5 đơn vị**, từ 01–30/01/2026. Đây là kỳ vọng chưa làm tròn, chưa có số bán thực tế kỳ này.
- **9/10** tuyến top train đạt MAPE tổng 30 ≤20%; MAPE trung bình **11,79%**.
- Đề xuất bổ sung **240 đơn vị** cho **150 mặt hàng**, từ policy mô phỏng tại 31/12/2025.
- **145 mặt hàng** đã hết hoặc dự kiến cạn trong 1–6 ngày; đây là trạng thái tại mốc mới nhất, không phải mẫu số replay lịch sử.

Cuộn xuống biểu đồ để chỉ đường bán đã quan sát và đường phân bổ kỳ dự báo. Không gọi đường phân bổ là 30 dự báo ngày độc lập.

**Nói:** “Dashboard chuyển dự báo theo tuyến thành danh sách mặt hàng cần xem xét, thay vì chỉ hiển thị điểm số mô hình.”

## 2. Dự báo — khoảng 60 giây

Mở **Dự báo**, giữ **Tổng 30 ngày**, mốc **31/12/2025**. Lượng đã quan sát phải hiện **Chưa có**, không phải 0.

Đổi mốc sang **30/09/2025** để chỉ một cửa sổ đã có actual. Dashboard hiển thị tổng dự báo, tổng đã quan sát và chênh lệch tổng. Chênh lệch cửa sổ này không phải MAPE nghiệm thu theo tuyến.

Cuộn đến biểu đồ MAPE theo tuyến: đường ngưỡng 20%, **China Mobile 20,33%** còn chưa đạt. Mở phần so sánh tổng 7/tổng 30 khi cần: đối chứng mới tổng 7 đạt 9/10, trung bình 15,49%; tổng 30 đạt 9/10, 11,79%. Hai mục tiêu có mẫu số khác nhau; không kết luận mô hình ngày đã tốt hơn bằng chênh lệch này.

**Nói:** “Mentor yêu cầu tổng 30 ngày nên nhóm chạy và chấm riêng tổng D+1 đến D+30. Việc chọn mô hình dùng validation rồi khóa trước test; test hiện là hồi cứu.”

## 3. Kho hàng — khoảng 60 giây

Mở **Kho hàng**, tình huống cơ sở và tất cả bộ lọc. Bảng ưu tiên đưa mặt hàng đã hết/sắp cạn lên trước.

Tại **Mặt hàng minh họa**, chọn **StarHub · D10G-10D · eSIM · Singapore** (mặc định đang là mặt hàng đầu):

- Tồn hiện có **0**, điểm đặt lại **4**, đã đặt chưa nhận **1**.
- Mở giải thích công thức: SS **2**, S **5**, IP **1**.
- Tồn 0 < ROP 4 nên cần xem xét bổ sung; Q = max(0, 5−1) = **4**. Lô mới có ETA **03/01/2026**.
- Lead time nhập giả định của đối tác này là **3 ngày**; không bị đổi thành 7 ngày giao khách.

Mở **Toàn bộ mặt hàng và phiếu đề xuất nhập** → **Xuất phiếu đề xuất nhập CSV**. Bản mặc định có **150 dòng / tổng Q 240**. Đây là phiếu đề xuất mô phỏng, chưa gửi đơn nhập thực.

**Nói:** “Hàng đang về dùng để tránh đặt trùng, nhưng không tăng tồn trước ETA. Quy tắc kích hoạt dùng tồn hiện có < ROP.”

## 4. Kịch bản — khoảng 90 giây

Mở **Kịch bản**. Ở bộ chọn đầu trang, đổi từ cơ sở sang **Đối tác chỉ giao 50%**. Giữ quốc gia/nhà mạng = tất cả để đối chiếu các số sau:

| Kịch bản | Tỷ lệ đáp ứng | Lượng chưa đáp ứng |
|---|---|---|
| Cơ sở | 85,97% | 2.240 |
| Đối tác chỉ giao 50% | 46,49% | 8.545 |
| Đối tác giao trễ 3 ngày | 74,18% | 4.123 |
| Không nhận được hàng | 7,69% | 14.740 |

Cuộn xuống hai biểu đồ: lượng đáp ứng/thiếu theo ngày và đường tồn kịch bản so với cơ sở. Các số là mô phỏng lịch sử quý IV/2025, không phải số kho doanh nghiệp và không phải hiệu quả đã đo trong thực tế.

Đổi sang **Một ngày không bán được** hoặc **Lượng bán còn 30% trong 7 ngày**. Cú sốc được giả định bắt đầu 15/11/2025, mô hình không được nhận thông tin tương lai này. Bảng 13 kịch bản cho thấy độ nhạy của chính sách. Có thể chọn Thailand/AIS để minh họa bộ lọc theo tuyến; lúc đó số liệu thay đổi đúng phạm vi, không đối chiếu trực tiếp với bảng toàn bộ ở trên.

**Nói:** “Đây là stress test khả năng chịu biến động, không phải lời hứa mô hình biết trước cú sốc. Nhóm chưa gọi là tối ưu chi phí vì chưa có chi phí lưu kho/thiếu hàng được xác nhận.”

## 5. Cảnh báo — khoảng 45 giây

Trả về **Cơ sở**, tất cả bộ lọc, rồi mở **Cảnh báo**. Phần đầu là danh sách cần xử lý hiện tại; phần dưới là đánh giá lịch sử riêng:

- **1.053/2.867 = 36,73%** sự kiện được báo trước ít nhất 7 ngày.
- **1.550** ca cạn trước ngày thứ 7 của đợt, không thể có đủ 7 ngày từ origin đầu đợt.
- Trong **1.317** ca có cơ hội đủ thời gian, vẫn bỏ sót **264** ca.

**Nói:** “Nhóm giữ nguyên mẫu số, không loại ca cạn sớm để tăng điểm. Cảnh báo đã có cơ chế và replay kiểm chứng, nhưng tiêu chí báo sớm chưa đạt mọi trường hợp.”

## 6. Giao khách và kết luận — khoảng 45 giây

Mở **Giao khách**: **1.885 đơn vị** từ đơn đã đặt được lên lịch giao trong 7 ngày đầu; phần ngày 8–37 dựa trên đơn tương lai được dự báo. Actual giao **chưa được cung cấp**. Giao D+7 là ngày lịch, gồm cuối tuần; không trừ kho lần hai lúc giao.

Kết ở **Kiểm chứng** để mentor thấy phần đã làm và phần còn thiếu. Thông tin train/validation/test, mô hình, nguồn và job 07:00 nằm trong các phần mở rộng.

**Câu kết:** “Nhóm đã có sản phẩm M3 chạy được từ dự báo đến đề xuất nhập, kiểm tra được tác động kịch bản và xuất kết quả. Nhóm chưa nhận đạt toàn bộ: China Mobile tổng 30 còn trên 20%, tiêu chí ngày còn mở và cảnh báo sớm còn thiếu. Đây là các phần cần tiếp tục cải thiện.”

## Nếu mentor hỏi

- **Tại sao dùng dữ liệu 2025?** Đây là snapshot được cung cấp; chưa có actual cho kỳ dự báo tháng 01/2026, không giả vờ đây là kho đang chạy tại tháng 10/2026.
- **Dữ liệu nào là thật trong bài?** Chỉ nguồn order được cung cấp; tồn, nhập hàng, mapping đối tác và lead time nhập là giả định. Định nghĩa success theo ngày đặt UTC vẫn là A08 đề xuất.
- **Vì sao chưa 10/10?** Công khai China Mobile 20,33%; hai thử nghiệm bổ sung không cải thiện ổn định nên giữ riêng. Không sửa nhãn hoặc chọn từng tuyến theo điểm test.
- **Các bài kiểm thử có chứng minh dự báo chính xác?** Không. Chúng kiểm code, bảo toàn, leakage và giao diện. MAPE và khả năng báo sớm được đánh giá riêng.
- **Nhóm đã push bản này chưa?** Chưa. Code ở nhánh local `codex/30day-m3`; dữ liệu và run riêng tư giữ local.

[Protocol/kết quả nguồn bài](30day-m3.md) · [Hai thử nghiệm bổ sung](aggregate-refinement.md)

Ảnh kiểm tra chỉ có tại máy tạo run: [Tổng quan](../reports/M3_2026-10-16/mentor_tong_quan.png) · [Kịch bản giao 50%](../reports/M3_2026-10-16/mentor_kich_ban.png) · [Biểu đồ tồn và lượng thiếu](../reports/M3_2026-10-16/mentor_bieu_do.png).
