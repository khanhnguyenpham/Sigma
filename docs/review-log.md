# Nhật ký rà soát, quyết định và thay đổi SIGMA

**Phiên bản:** 2.0 — 02/10/2026. **Trạng thái:** Khảo sát đã thực hiện, triển khai chưa bắt đầu. Lượt này cập nhật ba Markdown, không huấn luyện hoặc chạy thực nghiệm mới. Bằng chứng activation cũ được giữ như lịch sử, cần tính lại cho mục tiêu số bán.

[Kế hoạch hiện hành](../PLAN.md) · [Yêu cầu và tiêu chí nghiệm thu](requirements.md)

## 1. Quy tắc ghi nhận

- Phân biệt **đã xác minh trong tệp**, **nhận định của báo cáo**, **giả định**, **đề xuất** và **quyết định của bạn**.
- Xác nhận mentor M01/M02 được người dùng thuật lại; chưa có hai tệp ảnh để đọc trực tiếp. Nguồn U04 xác nhận chỉ order thực, phần còn lại giả định và bảo mật. Các giá trị A08–A17 là đề xuất, không gán cho mentor.
- Trạng thái rà soát dùng: có căn cứ, sai có bằng chứng, mâu thuẫn, chưa đủ bằng chứng. “Chưa đủ bằng chứng” không có nghĩa “đã sai”.
- Tách trạng thái nhận định khỏi trạng thái xử lý: kế hoạch có hướng sửa không có nghĩa PDF gốc đã được sửa hoặc mã đã được kiểm tra.
- Mỗi vấn đề/thay đổi có mã ổn định; không xóa lịch sử. Ghi phần bị thay thế và bằng chứng kiểm tra lại.
- Thời điểm ghi nhận là ngày 02/10/2026 theo Asia/Saigon; số liệu ngày trong CSV được xử lý theo UTC.

<a id="evidence"></a>
## 2. Sổ bằng chứng khảo sát

### E01 — Phạm vi đã đọc và hiện trạng

| Nguồn | Đã đọc/kiểm tra | Giới hạn |
|---|---|---|
| [Ảnh yêu cầu](PROJECT_REQUIREMENTS.png) | Đọc đầy đủ mục tiêu, M1/M2/M3, ngày/tháng, MAPE và cảnh báo | Ảnh không ghi năm |
| [Báo cáo nhóm](<Báo cáo chi tiết Sigma.pdf>) | Trích đọc toàn bộ 45 trang; xem trực tiếp sơ đồ trang 12 và 13, là hai trang có ảnh nhúng | Không có mã, bảng thực nghiệm hoặc nguồn nghiệp vụ đi kèm để tái lập mọi nhận định |
| [CSV đơn hàng](../data/sigma_sim_data_orders.csv) | Toàn bộ 100.000 dòng, 20 cột; khóa, missing, kiểu, thời gian, danh mục, phép tính, tổng hợp, độ thưa | Không có từ điển chính thức, lịch sử cập nhật trạng thái hoặc nguồn tồn kho |
| Thư mục/Git | Tại khảo sát ban đầu chỉ có ba đầu vào; sau đó thêm ba Markdown; 26 tệp cũ đang bị xóa | Nội dung tệp đã xóa không được khôi phục hay dùng như sản phẩm hiện hành |

Không có phần chữ hoặc sơ đồ nào của báo cáo bị bỏ qua vì không đọc được. Giới hạn còn lại là **chưa kiểm chứng đầy đủ các suy luận, nguồn nghiệp vụ và thực nghiệm**. Không nhận đã thực hiện một cuộc kiểm tra trình bày trực quan toàn bộ 45 trang.

### E02 — Hash nguồn bảo toàn

Hash SHA-256 được lấy trong khảo sát và kiểm tra lại trước khi tạo Markdown, cùng kết quả:

| Tệp | Kích thước byte đã khảo sát | SHA-256 |
|---|---:|---|
| `data/sigma_sim_data_orders.csv` | 17326622 | `22bf50f47978de131e3834811d4da9b4b3647e4eb4d073f574337e21143c5264` |
| `docs/PROJECT_REQUIREMENTS.png` | 425290 | `f6aa45d2f80b81798063e036b8c6510e74140182f19550c270e7e871df4b0a2c` |
| `docs/Báo cáo chi tiết Sigma.pdf` | 1039394 | `acb7d8de24e79a2bcc53c1aa5965fa8609661b65324edbadde71d7d699f6912b` |

### E03 — Cấu trúc, trạng thái và tổng quantity

Các phép kiểm tra dưới đây đã chạy trên **toàn bộ CSV**, không phải mẫu:

| Chỉ tiêu | Kết quả |
|---|---:|
| Dòng / cột | 100.000 / 20 |
| Order ID trùng / dòng trùng hoàn toàn | 0 / 0 |
| Missing activation_datetime | 5.691 |
| Missing ở các cột khác | 0 |
| Quantity nhỏ nhất / lớn nhất | 1 / 4 |
| Tổng quantity mọi trạng thái | 127.072 |
| Số dòng sai gross_revenue = quantity × unit_price | 0 |
| Product type | eSIM 73.092 dòng; physical_SIM 26.908 dòng |
| Plan type | fixed 72.052 dòng; unlimited 27.948 dòng |

| Order status | Số dòng | Tổng quantity | Có timestamp kích hoạt |
|---|---:|---:|---|
| success | 93.104 | 118.296 | Tất cả |
| refunded | 1.205 | 1.520 | Tất cả |
| failed | 2.330 | 2.958 | Không có |
| timeout | 2.214 | 2.814 | Không có |
| pending | 1.147 | 1.484 | Không có |

Tổng 5.691 timestamp thiếu khớp failed + timeout + pending. Đây là quan sát của tệp; chưa chứng minh quy tắc nghiệp vụ cho dữ liệu khác.

### E04 — Thời gian và ranh giới dữ liệu

| Chỉ tiêu | Kết quả |
|---|---|
| Order timestamp đầu | 2024-01-01 00:21:01 UTC |
| Order timestamp cuối | 2025-12-31 23:36:13 UTC |
| Số ngày đặt hàng UTC có dữ liệu | 731 |
| Activation timestamp đầu | 2024-01-01 18:52:11 UTC |
| Activation timestamp cuối | 2026-01-14 02:12:19 UTC |
| Timestamp không parse được trong giá trị không rỗng | 0 |
| Kích hoạt trước ngày đặt | 0 |
| Độ trễ trung bình / P90 / lớn nhất | Khoảng 6,1474 / 10,5417 / 14,9583 ngày |
| Quantity mọi dòng có activation | 119.816 |
| Quantity kích hoạt đến hết 31/12/2025 | 118.109 |
| Quantity kích hoạt sau 31/12/2025 | 1.707 |

Các tổng activation trên là bằng chứng lịch sử, không phải số bán. Mốc 16/01/2024 chỉ thuộc xử lý biên target 1.0 đã bị thay thế; 2.0 dùng ngày đặt từ 01/01/2024. Activation tháng 01/2026 không là nhãn lượng bán tháng 01; CSV không có order tháng đó.

### E05 — Danh mục, quan hệ và độ thưa

- 18 giá trị điểm đến, 46 nhà mạng/46 cặp điểm đến–nhà mạng, 8 region, 10 SKU, 2 product_type.
- Trong tệp: mỗi carrier thuộc một destination_country, mỗi destination_country thuộc một region. Đây là ánh xạ nhiều carrier đến một country, không phải quan hệ 1–1 hai chiều.
- `Europe (EU)` là một nhóm điểm đến. Các thuộc tính `plan_type`, `data_gb`, `validity_days` cố định theo SKU trong tệp.
- Có 13.794 customer_id; 13.093 ID xuất hiện với cả `new` và `returning`, nên customer_type không thể tự coi là thuộc tính bất biến của khách.
- Trong đơn success có đủ 80 tổ hợp region × SKU, 160 tổ hợp region × SKU × product_type và 920 tổ hợp carrier × SKU × product_type.
- Cả 10 SKU vẫn có đơn success ngày 31/12/2025; chưa có ca ngừng cung cấp được gắn nhãn.

Thống kê phục vụ đối chiếu **target lượng bán success theo ngày đặt**, trên đủ 731 ngày 2024–2025:

| Cấp | Kết quả |
|---|---|
| Region × SKU, 80 chuỗi | Trung bình 53,0301% ngày 0; nhỏ nhất 0%; lớn nhất 95,2120% |
| Carrier × SKU, 460 chuỗi | Trung bình 78,1830% ngày 0; độ dài chuỗi 0 liên tiếp lớn nhất trung bình 36,7174 ngày, cực đại 243 ngày |
| SKU toàn hệ thống, 10 chuỗi | Chuỗi 0 liên tiếp dài nhất 1 ngày; 6 SKU không có ngày 0 |
| Top 10 region × SKU theo lượng bán toàn kỳ | Chuỗi 0 liên tiếp dài nhất không quá 1 ngày |

Trong 1.0, đây là thống kê bổ sung khác target activation. Trong 2.0, chúng cùng bộ lọc sales cơ sở đề xuất nhưng vẫn khác cấp tuyến và kỳ xếp hạng: không dùng top 10 region × SKU toàn kỳ làm top 10 nghiệm thu tuyến theo train. T04 phải sinh lại các bảng bằng pipeline.

### E06 — Kiểm tra khả thi baseline trong bộ nhớ

**Đã thực hiện trong lượt khảo sát trước, chưa có script/CSV kết quả lưu trong dự án. Không phải kết quả nghiệm thu M2. Trạng thái 2.0: cần tính lại, target đã bị thay thế.** T03/T05 phải triển khai theo sales với mã, kiểm tra và đầu ra lưu được. Không đổi nhãn bảng activation này thành sales.

- Target: quantity của mọi activation, gồm refunded, UTC.
- Lưới mô hình bắt đầu 16/01/2024. Top 10 chọn bằng quantity đến hết 30/06/2025.
- Origin hằng ngày từ 30/06 đến 23/09/2025, horizon 1–7; ngày mục tiêu thuộc 07–09/2025. Mỗi tuyến/mô hình có 602 cặp origin–horizon.
- MA7 giữ trung bình 7 ngày cuối tại origin cho cả horizon. Ngày actual=0 bỏ khỏi MAPE và vẫn có trong MAE. Cùng một ngày mục tiêu có thể được chấm ở nhiều horizon; đây không phải 602 ngày độc lập.
- Đây là protocol khảo sát 7 ngày; không giả nhận đã chạy đầy đủ horizon 14 ngày của thiết kế cuối.

| Tuyến | MAPE ngày dương MA7 (%) | MAE | Số cặp actual >0 / tổng |
|---|---:|---:|---:|
| Thailand — dtac | 48,945 | 4,669 | 602 / 602 |
| Thailand — AIS | 45,963 | 4,716 | 602 / 602 |
| Thailand — TrueMove H | 45,825 | 4,144 | 595 / 602 |
| Japan — SoftBank | 52,967 | 3,201 | 602 / 602 |
| Japan — au (KDDI) | 50,335 | 3,576 | 602 / 602 |
| Japan — NTT Docomo | 72,510 | 4,103 | 600 / 602 |
| South Korea — KT | 55,000 | 2,885 | 596 / 602 |
| South Korea — SKT | 55,872 | 3,177 | 602 / 602 |
| South Korea — LG U+ | 49,619 | 2,871 | 602 / 602 |
| China — China Mobile | 70,547 | 2,662 | 595 / 602 |

Kết luận lịch sử: MA7 activation chưa đạt 20% trong khảo sát validation. Không dùng các giá trị đó để kết luận baseline sales đạt hay không đạt, hoặc dự đoán trước mô hình tốt nhất. Chưa chấm metric dự báo trên test cuối; lượt khảo sát chỉ xem cấu trúc/số ngày 0 trong khoảng test.

### E07 — Kiểm tra nhận định bổ sung của báo cáo

- Trên đơn success, D5G-7D chiếm khoảng 9,8642% doanh thu; UL-30D khoảng 12,9604%, phù hợp các số làm tròn 9,9% và 13,0% trong báo cáo.
- Tổng tỷ trọng doanh thu của D20G-30D, UL-15D, UL-30D khoảng 36,8870%; tỷ trọng quantity khoảng 16,9938%, hỗ trợ phần “37% doanh thu, 17% sản lượng” theo bộ lọc success.
- Số quantity đã đặt nhưng chưa đến activation tại cuối ngày, tính trên các dòng có activation, từ 16/01/2024 đến 31/12/2025: nhỏ nhất 602, lớn nhất 1.739, trung bình khoảng 1.034,36. Đây là thống kê hồi cứu trên snapshot, không phải feature đã chứng minh có sẵn thời gian thực. Không dùng để xác nhận một mức tồn chờ kích hoạt cố định tại mọi thời điểm.
- Chưa tái lập các chỉ số mùa vụ 1,37/1,30/1,33, khả năng thay thế, chi phí hủy eSIM hoặc cam kết đối tác 7 ngày vì thiếu phương pháp/nguồn cần thiết.

### E08 — Xác nhận mới và phạm vi nguồn

Ngày 02/10/2026, tệp yêu cầu người dùng đính kèm tại `C:/Users/Admin/.codex/attachments/ddf44419-bee3-4d11-8024-981f3010bb31/Pasted text.txt` thuật lại hai ảnh mentor: M01 về số lượng bán không phụ thuộc active/top 10 theo số bán; M02 về ngưỡng riêng đối tác, Vina là ví dụ và chưa có số ngưỡng. Thư mục đính kèm chỉ có văn bản, **không có hai ảnh để kiểm tra trực tiếp**. Không coi ảnh PROJECT_REQUIREMENTS.png cũ là hai ảnh mới.

U04 xác nhận chỉ order thực được cung cấp vì bảo mật; nhóm giả định phần còn lại, không chờ thêm dữ liệu nội bộ. U04 cũng yêu cầu trigger tồn < ngưỡng, phân loại thật/dẫn xuất/giả định/mô phỏng, đánh giá độ nhạy và không tự upload dữ liệu thật. U05 “Cập nhật lại các file MD” cho phép áp dụng thay đổi vào ba tài liệu; không mở rộng thành triển khai pipeline.

### E09 — Khảo sát số bán phục vụ bản cập nhật

Các số sau được khảo sát từ toàn bộ CSV trong lượt lập phương án 2.0; không phải run pipeline hoặc thực nghiệm mô hình, chưa là nghiệm thu M2. Bộ lọc **success theo ngày đặt UTC là A08 đề xuất**, không gán bộ lọc cho mentor.

| Kiểm tra | Kết quả và giới hạn |
|---|---|
| Phân bố quantity | 1: 81.880 dòng; 2: 11.152; 3: 4.984; 4: 1.984; tổng quantity 127.072 |
| Sales cơ sở toàn kỳ | 93.104 success, quantity 118.296; 1.205 refunded, quantity 1.520, tách riêng như E03 |
| Activation của success | Tất cả success hiện có activation; không có ca thật success chưa active để chứng minh trực tiếp, cần fixture giả |
| Activation ngày sau ngày đặt | 90.855 success, quantity 115.423; đếm theo ngày UTC khác nhau, không phải tổng mọi độ trễ dương |
| Trạng thái/hoàn tiền | Không có canceled, ngày hoàn tiền, quantity hoàn một phần hoặc lịch sử đổi trạng thái; không đủ định nghĩa số bán thuần/gộp kế toán |
| Đối tác | Có carrier Vinaphone tại Vietnam/region Domestic; không có trường partner và không có literal Vina. Vina→Vinaphone vẫn là giả định A09 |
| Tổng train cơ sở | 01/01/2024–30/06/2025: 66.619 đơn success, quantity 84.518; top 10 theo quantity, hòa theo tên tuyến |

| Hạng | Điểm đến | Carrier | Quantity bán train | Số đơn success train |
|---|---|---|---:|---:|
| 1 | Thailand | dtac | 5.235 | 4.110 |
| 2 | Thailand | AIS | 5.173 | 4.075 |
| 3 | Thailand | TrueMove H | 5.051 | 4.036 |
| 4 | Japan | SoftBank | 4.077 | 3.197 |
| 5 | Japan | au (KDDI) | 4.037 | 3.199 |
| 6 | Japan | NTT Docomo | 4.011 | 3.156 |
| 7 | South Korea | KT | 3.550 | 2.801 |
| 8 | South Korea | SKT | 3.544 | 2.825 |
| 9 | South Korea | LG U+ | 3.424 | 2.753 |
| 10 | China | China Mobile | 2.447 | 1.901 |

T05 phải tái sinh top 10 và đối soát bảng này; tên top 10 trùng khảo sát activation không có nghĩa đại lượng/kỳ tính giống nhau. Đổi định nghĩa trạng thái phải phiên bản hóa, không chọn bằng metric test thuận lợi.

### E10 — Bảo mật và đầu vào ngoài order

Git hiện theo dõi CSV nguồn và hai tài liệu gốc. `.gitignore` không loại CSV khỏi lịch sử đã theo dõi. Không push/công khai kho, tự viết lại lịch sử hoặc sửa/xóa gốc. T02/T12/T14 sẽ kiểm tra gói chia sẻ theo allowlist mã/cấu hình mẫu/hướng dẫn/dữ liệu giả, không lẫn raw/ID/notebook output hoặc run thật.

Không có nguồn tồn kho/nhập hàng/lead time thật. Đây là ràng buộc đã được U04 xác nhận, **không phải vấn đề chặn cần doanh nghiệp giải quyết**. Giá trị cơ sở A09–A17 dùng cho mô phỏng, gắn nhãn và đánh giá độ nhạy. Xử lý thật chuyển về local; Colab nếu có chỉ minh họa giả. Lượt cập nhật tài liệu không thực hiện upload hoặc tạo môi trường.

<a id="report-review"></a>
## 3. Sổ rà soát báo cáo gốc

Số trang tính theo PDF từ 1. Tất cả mục mới có **hướng xử lý trong kế hoạch**; PDF gốc giữ nguyên và báo cáo sửa chưa tồn tại. RV03 giữ nhận định 1.0 có mốc thời gian và cập nhật cách xử lý theo M01; không coi đổi yêu cầu là bằng chứng khảo sát cũ sai.

| Mã / vị trí | Nhận định hoặc phương pháp | Trạng thái | Bằng chứng và nguồn đối chiếu | Ảnh hưởng | Sửa hoặc xác minh tiếp theo |
|---|---|---|---|---|---|
| RV01 — Tr. 3–4 | Số dòng, trạng thái, missing và danh mục/SKU | Có căn cứ | E03–E05, kiểm tra toàn bộ CSV khớp các số chính | Dùng được làm nền tảng nhưng chưa có pipeline lưu | T03 sinh bảng kiểm tra và đối soát lại |
| RV02 — Tr. 4–7, 27–29 | Forecast region × SKU; chỗ khác route=carrier+SKU | Mâu thuẫn | Ảnh yêu cầu tuyến quốc gia–nhà mạng; báo cáo tự dùng nhiều định nghĩa; bạn chọn giữ ảnh | Đổi target, top 10, mô hình và giao diện | T01/T04 chốt tuyến; SKU chỉ là chi tiết mô phỏng |
| RV03 — Tr. 7 | Chọn ngày đặt vì activation thiếu 5,69% | Mâu thuẫn với target 1.0; mục tiêu đã đổi ở 2.0 | E03: missing không chứng minh phải đổi target; **M01 mới** mới là căn cứ chuyển sang số bán | Ngày đặt nay phù hợp mục tiêu mới, nhưng lý do cũ vẫn không đủ | T03/T04 dùng order_datetime theo M01/A08; không biến activation thành điều kiện sales |
| RV04 — Tr. 6, 18–19 | 730 ngày và lưới 58.480 dòng | Sai có bằng chứng / mâu thuẫn | E04: 731 ngày; 731×80=58.480 | Sai mẫu số/diễn giải | T03/T13 sinh kích thước từ lịch, sửa thành 731 |
| RV05 — Tr. 6–7, 34 | Khoảng 53% và 78,2% ngày 0; chuỗi 0 tối đa 243 ngày | Có căn cứ | E05 tái tính theo quantity success/ngày đặt | Hỗ trợ nhận định chia nhỏ làm chuỗi thưa | Giữ đúng cấp/target sales; vẫn phải sinh phân tích chính theo tuyến |
| RV06 — Tr. 8, 20–23, 39–41 | Khóa tồn lúc region×SKU, lúc có carrier/product_type | Mâu thuẫn | Schema cũ không có các chiều công thức mới sử dụng | Có nguy cơ dùng cùng tồn cho nhiều mặt hàng | T06/T10 thống nhất tuyến×SKU×product_type |
| RV07 — Tr. 17 | customer_type là thuộc tính duy nhất CUSTOMER | Chưa đủ định nghĩa | E05: 13.093 khách xuất hiện với cả new/returning | Tách bảng có thể làm sai nghĩa theo thời điểm | Giữ ở đơn hàng; không cần CUSTOMER trong phạm vi hiện hành |
| RV08 — Tr. 19, 25, 42 | Có CSV lịch kèm theo, đồng thời nói thiếu lịch Âm lịch | Mâu thuẫn về đầu vào hiện có | E01: CSV lịch không còn trong thư mục; nguồn lịch chưa kiểm chứng | Không tái lập phân tích lễ/Tết | T04 tạo lịch dẫn nguồn; không dùng cờ biết từ tương lai |
| RV09 — Tr. 26 | Cột “số đơn thành công” dùng số mọi trạng thái | Mâu thuẫn | CSV khớp số mọi trạng thái; chú thích báo cáo cũng thừa nhận chưa lọc success | Sai cách hiểu mẫu | T13 đổi nhãn hoặc sinh lại theo bộ lọc nêu rõ |
| RV10 — Tr. 8–9, 42 | Forecast 7 ngày bảo đảm báo trước ≥7 ngày | Mâu thuẫn | Tr. 42 thừa nhận chưa bảo đảm; ví dụ cạn 0,8–3,3 ngày không đủ lead time cảnh báo | Không đủ bằng chứng nghiệm thu M3 | T10 forecast 14 ngày/replay, đo lead time, phân biệt cảnh báo muộn |
| RV11 — Tr. 25–26, 29–30, 40–41 | Nhiều công thức SS, lượng nhập và trigger | Mâu thuẫn / chưa đủ bằng chứng | Khoảng bảo vệ, hàng đang về và trigger khác nhau; M02/U04 mới yêu cầu riêng đối tác và strict < | Thay công thức trigger cũ, giữ IP cho lượng đặt | Theo PLAN 2.0: on_hand < ROP riêng đối tác, kiểm tra bằng ngưỡng/ETA/MOQ |
| RV12 — Tr. 34–35 | Không bán, tăng lỗi và thiếu mã mới đủ kết luận ngừng cung cấp | Chưa đủ bằng chứng | Không có nhãn EOL, thông báo hay lịch sử kho; E05 không có ca ngừng được gắn nhãn | Báo giả khi giảm nhu cầu hoặc thiếu dữ liệu | Chỉ là tín hiệu, EOL ngoài phạm vi hiện hành; không chờ thêm dữ liệu |
| RV13 — Tr. 35–37 | Doanh thu, mùa vụ, mức thay thế SKU | Có căn cứ một phần | E07 hỗ trợ tỷ trọng doanh thu; thiếu phương pháp tái lập hệ số mùa vụ/thay thế | Trộn thống kê với suy luận nghiệp vụ | Giữ số đã kiểm; gắn nhãn giả định và không dùng hệ số chưa xác minh |
| RV14 — Tr. 36 | eSIM hủy gần như không tốn; cam kết 7 ngày; luôn khoảng 980 SIM chờ | Chưa đủ bằng chứng | Thiếu chính sách/hợp đồng; E07 cho thấy backlog biến động | Có thể tạo quy tắc nghiệp vụ sai | Không dùng như sự thật; phạm vi hiện hành dùng giả định có nhãn, không chờ hợp đồng/dữ liệu nội bộ |
| RV15 — Tr. 38 | Lead time cảnh báo = ngày phát hiện − ngày dừng | Sai có bằng chứng | Phát hiện trước làm phép trừ âm | Đảo dấu chỉ tiêu | T13 sửa thành ngày sự kiện − ngày phát hiện; EOL vẫn ngoài phạm vi, áp dấu đúng cho ngày cạn mô phỏng |
| RV16 — Tr. 42–45 | Kế hoạch mô hình và kết luận tổng kết | Chưa đủ bằng chứng thực nghiệm | Không có mã, forecast ngoài mẫu hoặc bảng metric đi kèm | Không được coi M1/M2 đã hoàn thành | T05–T09 sinh bằng chứng, T13 viết lại theo kết quả |

Các mục “có căn cứ” chỉ xác nhận phần đã kiểm, không duyệt toàn bộ chương. Chưa xếp các suy luận thiếu nguồn vào nhóm “sai có bằng chứng”.

<a id="decisions"></a>
## 4. Sổ quyết định

Mọi quyết định dưới đây được ghi ngày **02/10/2026**. “Bạn xác nhận” là quyết định của người dùng, không tự đổi thành “mentor xác nhận”. **DEC01–DEC13 giữ nội dung lịch sử 1.0; không phải toàn bộ quy tắc hiện hành.** Bảng trạng thái và quyết định 2.0 sau đó áp dụng khi có mâu thuẫn.

| Mã | Quyết định, nguồn | Lý do và phần ảnh hưởng |
|---|---|---|
| DEC01 | Giữ target kích hoạt ngày/tuyến quốc gia–nhà mạng; bạn xác nhận | Bám ảnh yêu cầu; thay đề xuất region×SKU làm mục tiêu chính. R01/R04; T03–T14 |
| DEC02 | Tổng quantity mọi activation kể cả refunded; bạn xác nhận | Hoàn tiền cuối kỳ không xóa sự kiện kích hoạt đã ghi. R01/R04/R05; không suy ra trạng thái lịch sử |
| DEC03 | MAPE ngày dương ≤20% cho từng tuyến top 10, kèm độ phủ và MAE/WAPE/bias; bạn xác nhận | Xử lý actual 0 minh bạch; R05, T05–T09. Giữ ngưỡng dù khảo sát chưa đạt |
| DEC04 | M3 mô phỏng có nhãn; bạn xác nhận | Chưa có tồn/ETA/lead time thật; R06/R07; không suy rộng nghiệp vụ |
| DEC05 | Colab huấn luyện, demo riêng; bạn xác nhận. Windows/Streamlit theo kế hoạch được chấp nhận | Gói CSV/JSON tách khỏi huấn luyện; R08/R09; chưa bật hosting hoặc lịch chạy |
| DEC06 | Giữ M2 17/10/2026, M3 07/11/2026, bù M1; bạn xác nhận | Quỹ giờ chưa rõ, chỉ ước lượng công sức; không mặc định thành viên cũ là phân công hiện hành |
| DEC07 | UTC; model từ 16/01/2024 đến 31/12/2025, giữ activation sau cutoff riêng; đề xuất đã được chấp nhận | Giảm vấn đề biên, không chấm nhãn tháng 01 không đầy đủ; R01/R04/R05 |
| DEC08 | Split train/validation/test cố định; top 10 chỉ từ train; daily origin, refit 7 ngày; đề xuất đã được chấp nhận | Tránh chọn mô hình/top 10 bằng tương lai; T05–T09 |
| DEC09 | Ba baseline, 6 SARIMA; 4 LightGBM khi SARIMA còn top 10 chưa đạt validation; đề xuất đã được chấp nhận | Thử nghiệm hữu hạn, dễ giải thích; không hứa trước mô hình tốt nhất |
| DEC10 | Horizon 14 ngày, M2 xem riêng 1–7; đề xuất đã được chấp nhận | Có đường kiểm chứng cảnh báo ≥7 ngày; không coi horizon dài là bảo đảm cảnh báo |
| DEC11 | Tồn theo tuyến×SKU×product_type, phân bổ 30/90 ngày, ETA và một chính sách; đề xuất đã được chấp nhận | Bảo toàn số lượng và không gộp hàng khác loại; region chưa phải kho thật |
| DEC12 | EOL/FIFO/đổi SKU/tối ưu chi phí/đặt hàng tự động ngoài v1; đề xuất đã được chấp nhận | Thiếu dữ liệu xác minh và không bắt buộc trong ảnh |
| DEC13 | Chỉ tạo ba Markdown lúc này; yêu cầu hiện tại của bạn | Thu hẹp bước thực hiện, không thay đổi mục tiêu dự án; chưa tạo code/cài phụ thuộc/thực nghiệm |

### Trạng thái quyết định cũ tại 2.0

| Mã cũ | Trạng thái | Phần giữ / thay thế |
|---|---|---|
| DEC01 | Bị thay thế một phần | Giữ tuyến quốc gia–nhà mạng; activation thay bằng sales theo DEC14 |
| DEC02 | Bị thay thế | Không còn mọi activation gồm refunded; A08 đề xuất success theo ngày đặt, refunded là kịch bản riêng |
| DEC03 | Giữ | MAPE ngày dương/từng tuyến do người dùng chọn; áp vào sales, không hạ 20% |
| DEC04 | Giữ, làm rõ | Mô phỏng có nhãn là đường nghiệm thu tồn; U04 xác nhận không chờ dữ liệu thật ngoài order |
| DEC05 | Bị thay thế một phần | Huấn luyện thật local; Windows/Streamlit demo riêng giữ; Colab chỉ tùy chọn giả |
| DEC06 | Giữ | M2 17/10/2026, M3 07/11/2026, bù M1, chưa có quỹ giờ/phân công |
| DEC07 | Bị thay thế một phần | Giữ UTC/cuối 31/12/2025; bỏ cắt 16/01, sales từ 01/01/2024; activation tháng 01 không là nhãn sales |
| DEC08 | Giữ cấu trúc, tính lại đầu vào | Train từ 01/01/2024 đến 30/06/2025; validation/test không đổi; top 10 sales train; daily origin/refit 7 ngày |
| DEC09 | Giữ phương pháp | Ba baseline, 6 SARIMA, LightGBM 4 cấu hình có điều kiện; chạy lại theo sales |
| DEC10 | Giữ | H14, M2 h1–7/h8–14 riêng; horizon dài không tự bảo đảm cảnh báo |
| DEC11 | Bị thay thế một phần | Giữ khóa tuyến×SKU×product_type/ETA; tỷ trọng sales 30/90; ngưỡng riêng/strict on_hand < ROP, không trigger IP≤ROP |
| DEC12 | Giữ phạm vi | Các mở rộng vẫn ngoài phạm vi bắt buộc 2.0; không xin thêm dữ liệu để thực hiện chúng |
| DEC13 | Giữ giới hạn hành động | U05 cho phép cập nhật ba Markdown, chưa code/cài đặt/thực nghiệm |

### Quyết định và phương án 2.0

| Mã | Nội dung / nguồn | Tác động / trạng thái |
|---|---|---|
| DEC14 | Số bán không phụ thuộc active, top 10 theo số bán — M01 thuật lại mentor | Thay target; R01–R05, T03–T14; không dùng activation lọc sale hợp lệ |
| DEC15 | success theo order_datetime UTC cơ sở, refunded tách — A08/P02 | **Đề xuất**, chưa là quy tắc kế toán/mentor; thiếu ngày hoàn/lịch sử trạng thái; test không dùng chọn bộ lọc |
| DEC16 | Ngưỡng riêng — M02; proxy carrier/Vina→Vinaphone và b=4/2 — A09/A12 | Chỉ ngưỡng riêng được xác nhận; mapping/con số đề xuất; thiếu cấu hình báo rõ |
| DEC17 | Chỉ order thực, phần khác nhóm giả định — U04 | Không chờ tồn/nhập/lead time; A08–A17 có trạng thái/độ nhạy/phiên bản |
| DEC18 | Xử lý thật local, không tự upload/công khai/truy vấn ngoài chứa bí mật — U04/P02 | Thay Colab thật; notebook chung mã/CLI, Windows demo riêng; kiểm gói allowlist/Git tracked |
| DEC19 | Sales 01/01/2024–31/12/2025 và top 10 train — P02/E09 | Dẫn xuất target mới, bỏ biên activation; khảo sát không thay pipeline |
| DEC20 | on_hand < ROP, IP tính Q; ledger/ETA/thiếu giữ sales gốc — U04/P02 | Thay trigger; R06/R07, T06/T10–T14; công thức/tham số là chính sách mô phỏng |
| DEC21 | Cập nhật ba tệp hiện có — U05 | Ghi 2.0, giữ mã/lịch sử, chưa bắt đầu kỹ thuật |

<a id="impact-v2"></a>
### CHG-003 — Ma trận thay đổi và tác động

| Xác nhận mới | Nội dung cũ bị ảnh hưởng | Điều chỉnh | Tệp / sản phẩm / nhiệm vụ | Tiêu chí kiểm chứng |
|---|---|---|---|---|
| M01: bán không phụ thuộc active | R01/R04, A01/A04, DEC01/02/07, activation/cắt 16/01 | Quantity success/ngày đặt đề xuất, 731 ngày; không activation filter | Ba MD/config/processed/EDA/forecast/metric/tồn/báo cáo; T03–T14 | Fixture chưa active vẫn tính, quantity>1 đúng, đổi activation không đổi sales, đối soát tổng |
| M01: top 10 theo số bán | Top 10 activation/MA7 E06 | Sales train 01/01/2024–30/06/2025, tính lại baseline/selection | top_routes/predictions/metrics/selected_models/báo cáo; R03–R05, T05–T09/T12–T14 | Khớp E09/A08, thay test không đổi top 10; cùng cặp chấm; không gọi E06 là sales/M2 |
| M02: ngưỡng riêng, Vina ví dụ | A07/DEC11, tham số chung L=3/b=3 cũ | Cấu hình từng partner; mapping A09 và b=4/2 chỉ đề xuất | config/partner_map/scenario/khuyến nghị/cảnh báo/dashboard; R06–R08, T06/T10–T14 | Cùng tồn khác cảnh báo; thiếu config không fallback; con số không gán mentor |
| U04: dưới ngưỡng strict < | Trigger IP≤ROP 1.0 | on_hand < ROP; IP tính Q, hàng muộn không coi sẵn có | PLAN/công thức/ledger/alerts/tests; R06/R07, T10/T12 | ROP−1, =ROP, +1; Q=0 không MOQ, ETA đúng/không đặt trùng |
| U04: chỉ order thực | Thiếu snapshot/hợp đồng dễ thành phụ thuộc xin thêm | A08–A17 có giá trị/phạm vi/lý do/độ nhạy/trạng thái; không chờ doanh nghiệp | Ba MD/config/scenario/ledger/metrics; R06/R07/R09, T01/T06/T10–T14 | Khởi tạo từ config, ledger cân bằng/shortage rõ, sales gốc giữ, báo kết luận đảo chiều |
| U04: bảo mật | DEC05 Colab thật/kiểm tra Colab sạch | Local notebook/train; Colab giả tùy chọn; gói chia sẻ không dữ liệu riêng tư | Ba MD/README dự kiến/requirements.txt/run_local.ipynb/manifest/gói; R08/R09, T02/T11–T14 | Không upload thật; allowlist kiểm cả notebook/Git; local sạch tái lập |
| U04: đánh giá riêng dự báo/tồn | Dễ coi tồn giả là thật hoặc ngăn cạn là báo sai | Forecast chấm order holdout; tồn chấm kịch bản, no-new-order khác policy | tests/metrics/alerts/figures/report/slides; R05–R09, T09–T14 | Sales metric truy actual; cạn đếm một lần; thật/giả định/giới hạn rõ |
| U05: cập nhật MD | Bản mới đang ở mức kế hoạch trong chat | Ghi đúng ba tệp, không bản trùng/triển khai | PLAN.md, requirements.md, review-log.md; T01 | Liên kết/mã/trạng thái/công sức nhất quán; 3 hash và 26 tệp bị xóa giữ nguyên |

**Vô hiệu hóa:** E06 và lựa chọn/dự báo/metric/hình theo activation chỉ là lịch sử, **cần tính lại** cho sales. Ngưỡng chung/trigger IP≤ROP cũ **bị thay thế**. Chưa có run/mô hình/dashboard đã triển khai để xóa hoặc đổi nhãn thành run mới. E03–E05 vẫn là khảo sát đúng phạm vi; T03/T04 phải sinh lại bằng mã. Không ghi T02–T14 “đã xong rồi cần sửa” vì chúng chưa bắt đầu.

## 5. Lỗi kỹ thuật và kiểm tra hiện tại

- Chưa có mã nguồn dự án nên chưa có lỗi runtime/model hoặc bộ kiểm thử dự án được thực thi.
- Lượt khảo sát gặp lỗi encoding khi in tiếng Việt từ Python, sau đó cấu hình stdout UTF-8 và đọc được báo cáo; không phải lỗi PDF hoặc dữ liệu.
- Truy vấn bộ nhớ máy bằng Get-CimInstance bị từ chối truy cập; không thu được thông số RAM và không dùng giả định phần cứng đó để cam kết hiệu năng.
- Các thư viện huấn luyện/demo chưa được cài cho dự án. Không coi runtime dùng để đọc dữ liệu của công cụ là môi trường huấn luyện cục bộ/máy demo đã bàn giao.
- Kiểm tra bộ Markdown gồm tính nhất quán mã task/yêu cầu, liên kết tương đối, trạng thái, hash gốc và phạm vi thay đổi Git. Đây là kiểm tra tài liệu, không phải kiểm thử pipeline hay nghiệm thu M2/M3.

**QA-DOC-001 — 02/10/2026 (lịch sử phiên bản 1.0):** Đã kiểm tra ba Markdown bằng kiểm tra chỉ đọc: mỗi T01–T14 và R01–R09 có đúng một định nghĩa; nhiệm vụ có đủ trạng thái, mục tiêu, đầu vào/đầu ra, phụ thuộc, tiêu chí, rủi ro và công sức; liên kết nội bộ/anchor tồn tại; bảng đủ cột và khối mã đóng đủ. SHA-256 của 3/3 đầu vào không đổi. Git chỉ có thêm đúng ba Markdown, giữ nguyên 26 tệp bị xóa trước đó. Kết quả: đạt kiểm tra tài liệu và phạm vi thay đổi. Không có kiểm thử pipeline, huấn luyện hoặc thực nghiệm mới trong lượt tạo 1.0.

**QA-DOC-002 — 02/10/2026 (phiên bản 2.0):** Đã kiểm tra chỉ đọc ba Markdown: 69 liên kết tương đối/anchor hợp lệ; T01–T14 và R01–R09 có đúng một định nghĩa; task đủ bảy trường, T01 đang làm và T02–T14 chưa làm; A08–A17 đều đề xuất; bảng/khối mã/UTF-8 hợp lệ. Tổng công sức tính lại đúng 97–149 hoặc 105–163 người-giờ. Đã đối chiếu target sales, split, ngưỡng strict <, local/bảo mật và các nội dung activation/Colab cũ có nhãn lịch sử hoặc bị thay thế. SHA-256 3/3 đầu vào không đổi; giữ nguyên đúng 26 tệp bị xóa; phạm vi thay đổi chỉ ba Markdown hiện có. Kết quả: đạt kiểm tra tài liệu, **không phải kiểm thử pipeline hoặc nghiệm thu M2/M3**.

<a id="change-process"></a>
## 6. Quy trình xử lý phản hồi mentor và phát hiện lỗi

1. **Ghi nhận:** mã CHG hoặc BUG, nội dung, nguồn, ngày, lý do; phân biệt mentor trực tiếp/bạn thuật lại/báo cáo nháp/phát hiện kỹ thuật.
2. **Xác định thay thế:** yêu cầu/giả định nào được bổ sung, sửa hoặc thay thế; không tự đổi mục tiêu nếu nguồn chưa đủ rõ.
3. **Phân tích tác động:** Rxx, Axx, Txx, mã/config, dữ liệu xử lý, run, metric, hình và đoạn báo cáo nào bị ảnh hưởng.
4. **Chọn cách sửa:** ghi phương án và kiểm tra cần chạy lại. Lỗi thường trong phạm vi được giao được tự sửa; chỉ hỏi khi còn lựa chọn quan trọng về mục tiêu/phạm vi/nghĩa dữ liệu/chi phí.
5. **Cập nhật:** sửa requirements và PLAN, tăng phiên bản cấu hình/giả định/target tương ứng khi có triển khai, giữ mã task. Chỉ chuyển trạng thái giả định từ đề xuất sang nhóm thống nhất/mentor xác nhận khi có nguồn; không xóa dấu vết cũ.
6. **Vô hiệu hóa:** chuyển phần hoàn thành mất hiệu lực sang “cần kiểm tra lại”; không để dashboard/báo cáo sử dụng run cũ như vẫn hợp lệ.
7. **Xác minh:** chỉ hoàn thành lại khi có bằng chứng mới, run/check cụ thể. Không đổi tiêu chí hoặc dung sai chỉ để vượt kiểm tra.

Khi một phần bị chặn, tiếp tục phần độc lập. Sau mỗi giai đoạn ghi: việc đã xong, kiểm tra thực sự đã chạy, kết quả, vấn đề mở và bước tiếp. Khi tiếp tục ở chat khác, đọc ba tài liệu và kiểm tra Git/config/manifest/tệp thực tế; không suy ra thành công từ danh sách tệp dự kiến.

### Mẫu ghi nhận cho giai đoạn thực hiện

| Trường | Nội dung cần ghi |
|---|---|
| Mã, ngày, trạng thái | CHG-xxx hoặc BUG-xxx; thời điểm và trạng thái hiện hành |
| Nội dung, nguồn, lý do | Trích ý đủ hiểu, ai xác nhận, nguồn có thể tìm lại |
| Phạm vi tác động | Rxx/Axx/Txx, tệp/config, dữ liệu, run và phần báo cáo |
| Cách xử lý | Phương án đã chọn, phần bị thay thế, lý do |
| Kiểm tra lại | Lệnh/ca kiểm tra, đầu vào, kỳ vọng, kết quả thực tế |
| Bằng chứng đóng | Run/hash/tệp hoặc lý do còn mở; ngày hoàn thành lại |

Ví dụ tác động: CHG-003 đổi target sang sales nên T03 cần định nghĩa mới, T04 trở đi phải dùng/tính lại sản phẩm phụ thuộc. Đổi A08 ảnh hưởng chuỗi, top 10, mô hình, metric, tồn và báo cáo; đổi A12 chỉ ảnh hưởng tồn/cảnh báo/độ nhạy/dashboard/báo cáo, không fit lại forecast nếu mô hình không phụ thuộc A12. Sửa nhãn biểu đồ chỉ ảnh hưởng hiển thị nếu phép tính không đổi. Sau khi xem metric test, vòng sửa mô hình phải công khai test đã sử dụng, không gọi cùng tập là kiểm định độc lập.

## 7. Lịch sử thay đổi và vấn đề còn mở

| Mã | Ngày | Nội dung / nguồn | Tác động / trạng thái |
|---|---|---|---|
| CHG-001 | 02/10/2026 | Bạn chấp nhận kế hoạch sau khảo sát và các lựa chọn U02 | Thiết lập R01–R09, T01–T14, A01–A07; chưa tạo sản phẩm kỹ thuật |
| CHG-002 | 02/10/2026 | Bạn yêu cầu tạm thời chỉ tạo ba Markdown rồi xác nhận thực hiện | Giới hạn hành động ở tài liệu; giữ nguyên phương án dự án; không khôi phục 26 tệp đã xóa |
| CHG-003 | 02/10/2026 | M01/M02 thuật lại mentor, U04 chỉ order/bảo mật/giả định, U05 yêu cầu cập nhật MD | Đã áp dụng phiên bản 2.0 vào ba tài liệu; tác động tại ma trận trên. A08–A17 đề xuất; kỹ thuật chưa bắt đầu, kết quả activation cần tính lại |

Giới hạn và trạng thái còn mở, không phải yêu cầu xin thêm dữ liệu doanh nghiệp:

- A01/A04 bị thay thế; A02 còn giới hạn tính đầy đủ/snapshot trạng thái. Order thực theo người dùng; không coi số bán là toàn bộ nhu cầu thị trường.
- A07/U04 xác nhận không có dữ liệu nội bộ ngoài order; triển khai bằng A08–A17, không bị chặn chờ tồn/ETA/lead time thật.
- A08–A17 là đề xuất cần giữ nhãn, cấu hình tập trung và độ nhạy; không có giá trị ngưỡng mentor cung cấp hoặc mapping Vina được xác minh.
- A06: quy ước MAPE do bạn chọn phải được trình bày rõ khi gửi mentor.
- R05: MA7 activation E06 cần tính lại; chưa có baseline sales/SARIMA/LightGBM/test cuối để kết luận đạt hay không đạt 20%.
- R07: chưa có cảnh báo/replay đo được; chưa biết tỷ lệ báo trước 7 ngày.
- T02/T12: chưa kiểm tra môi trường local sạch hoặc máy demo; chưa có bằng chứng tái lập dự án; Colab thật đã bị thay thế.
- Tổng công sức mới 97–149 người-giờ, hoặc 105–163 nếu T08 kích hoạt; quỹ giờ/phân công chưa rõ, không suy ra cam kết đủ nguồn lực.

**Bước tiếp theo:** kiểm tra ba Markdown trong phạm vi hiện tại. Khi được giao triển khai mới bắt đầu T02 môi trường cục bộ, rồi T03–T05 theo sales. Không có câu hỏi bắt buộc để cập nhật tài liệu; không yêu cầu xác nhận lại M01/M02/U04.

## 8. Tài liệu phương pháp đã tham khảo trong lượt lập kế hoạch

Các nguồn này hỗ trợ lựa chọn phương pháp/công cụ, không xác nhận quy tắc nghiệp vụ trong CSV:

- [Forecasting: Principles and Practice — Time series cross-validation](https://otexts.com/fpp3/tscv.html): chỉ dùng quan sát có trước target khi dự báo.
- [Forecasting: Principles and Practice — Evaluating point forecast accuracy](https://otexts.com/fpp3/accuracy.html): metric ngoài mẫu và vấn đề MAPE khi actual bằng 0.
- [statsmodels — SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html): cấu hình mô hình dự kiến.
- [LightGBM — Parameters](https://lightgbm.readthedocs.io/en/stable/Parameters.html): tham số ứng viên dự kiến.
- [Streamlit — Run your app](https://docs.streamlit.io/develop/concepts/architecture/run-your-app): chạy dashboard cục bộ.
- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html): nguồn tham khảo phương án 1.0; ở 2.0 Colab chỉ tùy chọn minh họa dữ liệu giả, không tải dữ liệu thật.

Ngày tham khảo trong lượt khảo sát: 02/10/2026. Phiên bản phụ thuộc cụ thể chưa được lựa chọn hoặc kiểm chứng bằng cài đặt dự án.
