# Nhật ký rà soát, quyết định và thay đổi SIGMA

**CHG-048/E76 — 19/10/2026:** đã nhận yêu cầu chỉ tạo/sửa Markdown thiết kế M3 và commit/push nhánh riêng. [Bộ đặc tả](../M3/README.md) giữ nguồn thuật lại, phân biệt thực tế/dự kiến, không nhận đã chạy BE/FE/DB/ML mới. Chi tiết và bằng chứng ở [E76](#e76).

**CHG-038/E66 — 11/10/2026:** thử nghiệm lịch local hoàn tất,10 ứng viên không thắng đối chứng LG U+ trên validation; không chấm test mới. [Protocol/CSV/bảng kết quả](calendar-experiment.md); chi tiết bằng chứng ở mục CHG-038/E66 cuối nhật ký. R05/R07/T14 giữ mở.

**CHG-029/E56 — 06/10/2026:** người dùng yêu cầu cải thiện chất lượng để nộp/bảo vệ. Đăng ký thử nghiệm validation-only về bộ nhớ mùa vụ tuần: bốn cấu hình Gaussian khoảng cách lịch tròn 28/56 ngày × quantity thô hoặc chuẩn hóa theo 90 ngày tại origin, thêm hai biến thể ratio giảm trọng số lịch sử với half-life 90 ngày (sáu tổng). Áp dụng cùng cấu hình cho mọi tuyến; refit 7 ngày, nhãn kết thúc không sau cutoff. Mục tiêu là kiểm giả thuyết thiếu khả năng học mùa vụ, không tăng số cây thêm. So sánh validation với lựa chọn V13 đã khóa; không chấm test hoặc chuyển production trong thử nghiệm này. Đăng ký trước fit, chưa có kết quả. Chẩn đoán CV/tự tương quan và fit hồi cứu tháng×weekday chỉ mô tả dữ liệu, không là chứng minh MAPE 20% bất khả thi. Giữ target/top10/split/ngưỡng/R05 và bộ trình diễn V13 nguyên; không làm Word/slide mới, không hứa điểm mentor.

**Phiên bản lịch sử:** 2.0 — 02/10/2026. **Trạng thái tại 02/10:** Khảo sát đã thực hiện, triển khai chưa bắt đầu. Lượt này cập nhật ba Markdown, không huấn luyện hoặc chạy thực nghiệm mới. Bằng chứng activation cũ được giữ như lịch sử, cần tính lại cho mục tiêu số bán.

**Cập nhật triển khai 05/10/2026:** E01–E10/RV/QA-DOC cũ là lịch sử, không phải kiểm tra lại ảnh/PDF đang thiếu. E11 trở đi là bằng chứng kiểm tra trực tiếp lượt triển khai; CHG-008 cho phép local và push allowlist, CHG-009/010 cho phép tinh chỉnh bằng validation và công khai test đã xem. Không nghiệm thu toàn bài khi R05 chưa đạt.

[Kế hoạch hiện hành](planning/PLAN.md) · [Yêu cầu và tiêu chí nghiệm thu](requirements.md)

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
| [Báo cáo nhóm](Báo cáo chi tiết Sigma.pdf) | Trích đọc toàn bộ 45 trang; xem trực tiếp sơ đồ trang 12 và 13, là hai trang có ảnh nhúng | Không có mã, bảng thực nghiệm hoặc nguồn nghiệp vụ đi kèm để tái lập mọi nhận định |
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

### E11 — Audit và pipeline sales thực chạy, 05/10/2026

Run `sigma_full_v1` đã complete: audit → EDA → baseline → validation → test → forecast → inventory. CSV local 100.000 dòng/20 cột; success 93.104 dòng, 118.296 quantity; 46 tuyến × 731 ngày = 33.626 route-days. Hash trước/sau `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b` giữ nguyên. Không có lỗi target/duplicate/đối soát tiền trong nguồn này; 5.691 activation thiếu không dùng loại sale. Audit và fixtures vẫn chặn lỗi target, giữ money diagnostics riêng. Forecast latest 46 × 14 = 644 cặp, actual tháng 01/2026 trống.

### E12 — Tinh chỉnh hữu hạn, không đổi tiêu chí

V1: 3 baseline, 6 SARIMA/top10 và 4 LightGBM Poisson khi điều kiện validation kích hoạt. 59/60 SARIMA có độ phủ validation đầy đủ; 1 ứng viên loại do fit/hội tụ. V2 thêm 8 weighted-median robust và 4 LightGBM inverse-label weighted L1; V3 thêm 12 hồi quy lịch biết trước, tổng 37 cấu hình trên từng top10. Calendar dùng thứ trong tuần và harmonic năm, không dùng actual tương lai; exploratory validation và CLI khớp 143.640 cặp ở dung sai 1e-8. Model selection vẫn validation, mọi nhãn fit <= cutoff.

Test v1: 0/10 đạt, MAPE 41,10–73,65%, mean MAPE tuyến 50,53%. V2: 0/10, mean 48,35%. V3: 0/10, 40,93–61,96%, mean 49,03%, 6 tuyến cải thiện so với v1. **Không chọn V2 vì test tốt hơn:** V3 có lựa chọn theo validation; test đã xem và đánh giá lại không độc lập. MAE/WAPE/bias/độ phủ vẫn công bố, không lấy mean hoặc WAPE thay tiêu chí từng tuyến. Dữ liệu/target/top10/split/ngưỡng giữ nguyên. Các thử nghiệm chưa chứng minh 20% là bất khả thi, cũng chưa có bằng chứng đạt ngưỡng.

### E13 — Kiểm tra local, tái lập, CI và Git

`python -m pytest` trong môi trường khóa đã chạy 37 tests đạt; ca tính tay, missing/0, giữ hash, duplicate/quantity/UTC, lựa chọn validation, chống leakage, phân bổ/balance/trigger/ETA, cảnh báo, run hỏng và calendar unknown. `pip check` đạt trong .venv và .venv-verify. Demo v1 và demo_release cùng input hash/config/seed: 14 bảng khớp, số nguyên tuyệt đối, số thực 1e-8, loại run-id để đối chiếu. Baseline/SARIMA/LightGBM Poisson validation v1 và v2 trong môi trường sạch có hash CSV giống tuyệt đối.

AppTest demo và run thật v1: 0 exception, 10 bảng; đổi origin và nhóm horizon đạt. Kiểm tra trình duyệt local hiển thị sáu tab, actual/forecast và nhãn tồn mô phỏng, cảnh báo R05. Run v1 có 1.100.320 ledger rows/13 chính sách: cân bằng tồn và demand=fulfilled+shortage đúng tuyệt đối, không âm, historical sales không đổi giữa scenario; 5.520 alert item-windows event-id duy nhất. Replay cảnh báo không đặt mới tách khỏi policy. V3 early-event-rate khoảng 31,67%, chưa chứng minh mọi ca báo trước >=7 ngày; không tự thêm ngưỡng precision/recall nghiệm thu.

Git root đã xác minh đúng project; CSV/outputs/.venv/.tools ignored. Stage allowlist đầu 24 file không có ID nguồn, token, CSV/run thật; notebook không output. Push nhánh codex/sigma-local-pipeline thành công theo CHG-008, Draft PR #1. Windows CI [37225721518](https://github.com/khanhnguyenpham/Sigma/actions/runs/37225721518) thành công với tests + pipeline demo giả + AppTest trên runner sạch; không có raw orders trên CI. Chưa diễn tập UI trên máy Windows cá nhân thứ hai. Tại thời điểm E13, báo cáo/slide chưa tạo; trạng thái mới ở E15/CHG-011.

### E14 — Kiểm tra bản release bàn giao

Run `sigma_release_v4` complete, cấu hình 1.2.1, 43 tệp sealed khớp hash. CSV gốc giữ SHA256 `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. Mã thực chạy có hash `289064ed0368262fb1027b304732f793700a3a34d0b367f1e7198be0334370c1`, khớp working code khi kiểm tra. Git revision trong manifest ở đầu run không đại diện mọi thay đổi chưa commit, dùng code hash để nhận diện. Manifest SHA256 `dbfa747134e2769cbf81214c7cb7dadfc2e6aa0806b9ce413e923beb1496c152`.

Sáu bảng lựa chọn/validation/test/forecast tái lập v3 theo dung sai 1e-8. Top 10 có 623 cặp h1–7/tuyến, độ phủ 100%, 0/10 đạt MAPE ≤20%, khoảng 40,93–61,96%. Forecast mới 644 cặp, actual tháng 01/2026 trống. Kiểm tra 1.100.320 dòng ledger cân bằng số nguyên/không âm, nhu cầu bằng đáp ứng cộng thiếu; Q và trigger strict < đúng, event-id replay duy nhất. Khóa 84 package được kiểm chứng trong environment_verification trước seal. AppTest release: 0 exception/10 bảng khi đổi quốc gia/carrier, origin và h8–14. Launcher đã chạy local trên 127.0.0.1:8501 và chọn release thật hoàn chỉnh mới nhất.

### E15 — Báo cáo tiến độ M2 và slide local

Theo CHG-011, đã tạo `reports/M2/SIGMA_Bao_cao_tien_do_M2.docx` 10 trang, SHA256 `7a1f3f170939f5dfbeaaad221509084c245a93cf7624fa96a3e0c75848a5c295`, và `SIGMA_Slide_bao_cao_M2_ban_giao.pptx` 16 slide, SHA256 `1063e90cc4d9f2fccb919e2411b36be128a0b42136179a8694621e9e6354a768`. Nội dung truy về release_v4 và giữ rõ 0/10 đạt R05, early-event-rate 31,67%, test reuse và giả định. Không bịa tên trường/mentor hoặc đóng góp cá nhân.

DOCX: render_docx.py đã thử nhưng thiếu LibreOffice, dùng Word cài sẵn chạy ẩn export PDF QA và Poppler tạo ảnh. Đã kiểm tra mọi trang, sửa đường kẻ tiêu đề rồi render lại. Ghi chú thuyết trình đã rà bằng tiếng Việt, giải thích chỉ số/mẫu số và giới hạn từng slide. PPTX: Artifact Tool export/import, finalizer kiểm tra gói/layout/font, hai chart native có workbook snapshot khớp cache và bảng native. Đã render mọi slide và kiểm tra bố cục; không tuyên bố đã mở/chỉnh sửa trong PowerPoint. File QA và report có kết quả riêng tư đều ignored/local, không push. T13 mới hoàn thành phần tiến độ M2, báo cáo cuối kỳ/bảo vệ còn mở.

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

**M05 — 20/10/2026 (CHG-061):** người dùng trả lời “Đã chốt chấm tổng 30 ngày” cho câu hỏi mentor có chốt MAPE≤20% trên tổng30 thay từng ngày hay không. Ghi nhận là **mentor do người dùng thuật lại**, không phải biên bản mentor được đọc trực tiếp. R05 áp dụng tổng quantity D+1…D+30 cho từng top10 train, actual dương trong MAPE; coverage/MAE/WAPE/bias và split giữ nguyên. Ngày/7ngày còn chẩn đoán và tồn H14. Không đổi A08 hoặc biến kết quả hồi cứu thành holdout độc lập. [Phạm vi hiện hành](../M3/MONTHLY.md).

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
| DEC22 | Phần mềm local/Git allowlist và A08–A17 thực nghiệm — CHG-008, người dùng đồng ý | Thay giới hạn hành động chỉ tài liệu ở DEC21; không xác nhận mentor/nguồn thiếu. Báo cáo/slide để sau. |
| DEC24 | Word tiến độ M2 và slide sau phần mềm — CHG-011, người dùng yêu cầu | Thay việc để sau ở CHG-008. Tạo từ run đã kiểm tra, giữ chưa đạt R05/cảnh báo, lưu local; không tự nâng nghiệm thu. |
| DEC23 | Tinh chỉnh thêm bằng validation — CHG-009/010, yêu cầu người dùng | Giữ tiêu chí 20%/target/split; test đã xem được công khai, không gọi độc lập hoặc chọn bản bằng test. |

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

## 5. Kiểm tra ngày 02/10/2026 — lịch sử

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
| CHG-004 | 04/10/2026 | Người dùng yêu cầu chia task triển khai và cung cấp 6 tên: Nguyên, Khang, Du, Tuấn Anh, Hiếu, Cường | Đề xuất người phụ trách/review cho T01–T14 trong TASK/PLAN và cập nhật hướng dẫn TXT. Chưa có năng lực, quỹ giờ, GitHub username hoặc xác nhận nhận việc; không đổi nghiệp vụ, A08–A17, phụ thuộc, công sức hay trạng thái. Chưa tạo Issue, push hoặc triển khai code |
| CHG-005 | 04/10/2026 | Người dùng làm rõ muốn cả nhóm cùng làm từng task một | Thay cách làm các module song song của CHG-004 bằng cùng một Txx, chia checklist nhỏ cho 6 người, PR riêng từng phần và kiểm tra chung trước chuyển task. TASK/PLAN/TXT được đồng bộ; người phụ trách cũ là đầu mối đề xuất. Ước lượng tải cá nhân cũ cần phân bổ lại; công sức tổng, nghiệp vụ, phụ thuộc, trạng thái giữ nguyên. Chưa tạo Issue/push hoặc triển khai code |
| CHG-006 | 04/10/2026 | Người dùng yêu cầu được hướng dẫn làm solo và push Git từng phần | Thay cách phối hợp CHG-004/005 bằng người dùng làm toàn bộ T01–T14 với hỗ trợ từng phần; giữ phân công nhóm làm lịch sử hết áp dụng. TASK/PLAN/TXT mô tả phần nhỏ, kiểm tra, commit/push code và tài liệu được phép. Không đổi nghiệp vụ, giả định, phụ thuộc, nghiệm thu hoặc công sức tổng; chưa biết quỹ giờ solo. Lượt này chuẩn bị phần tài liệu/Git, chưa triển khai pipeline; kết quả push cần kiểm chứng riêng |
| CHG-007 | 04/10/2026 | Người dùng yêu cầu trợ lý làm phần mềm xuyên suốt/Git, báo cáo và slide sau; bổ sung chuẩn hóa theo kickoff, giảm bán/doanh thu và đối tác nhập ít | TASK/PLAN/requirements/data-contract bổ sung hành vi và ca stress vào T03–T12; không đổi target/split/metric, không xác nhận A08–A17 hay nguồn kickoff thiếu. Local/online, cấu hình cơ sở, quyền push cụ thể và nghĩa “nhập ít” đang chờ làm rõ. Preflight chỉ đọc 100.000 dòng bằng Python standard library: không phát hiện lỗi độ rộng, quantity, order timestamp, duplicate hoặc đối soát doanh thu; 5.691 activation trống; 46 tuyến. SHA-256 trước/sau giữ 6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b. Chưa có audit pipeline, fixture, stress run hoặc nghiệm thu T02–T14; commit 25fb7f5 vẫn local, push trước bị auto-review từ chối |
| CHG-008 | 05/10/2026 | Người dùng trả lời “đồng ý” sau lựa chọn triển khai và yêu cầu làm A–Z | Chọn Streamlit local Windows, PLAN/requirements làm căn cứ khi nguồn kickoff thiếu; A08–A17 cho thực nghiệm, không mentor xác nhận; cả giảm bán và nhận thiếu/trễ. Cho phép push mã/config/tests fixture giả/notebook không output/tài liệu, gồm commit 25fb7f5, tới khanhnguyenpham/Sigma qua nhánh và PR. CSV/run thật/token không push. T13 báo cáo/slide vẫn để sau. CHG-007 chờ lựa chọn đã được thay thế; không đổi tiêu chí độ chính xác. |
| CHG-009 | 05/10/2026 | Người dùng yêu cầu phải tinh chỉnh để đáp ứng yêu cầu | Sau khi công bố test v1 0/10 đạt, mở thí nghiệm v2: giữ dữ liệu/target/top10/split/metric/ngưỡng; thêm 8 robust weighted-median (4 cửa sổ × có/không shrink thứ trong tuần) và 4 LightGBM inverse-label weighted-L1, chọn bằng validation như cũ. Test đã được xem; v2 đánh giá lại trên test cũ, không gọi kiểm định độc lập. Không nâng trạng thái R05 nếu vẫn chưa đạt; lưu v1, config.original.json và v2 tách run/config version. |
| CHG-010 | 05/10/2026 | Tiếp tục yêu cầu tinh chỉnh CHG-009 | V3 thêm 12 hồi quy lịch biết trước: cửa sổ 365/toàn lịch sử × 1/2 harmonic năm × weighted LAD alpha 0,001/0,01 hoặc Poisson alpha 0,1; feature thứ trong tuần và sin/cos day-of-year. Thử nghiệm chỉ dùng nhãn tới cutoff trên validation, không dùng nhãn test để chọn; validation cải thiện thêm 2 tuyến nên tích hợp CLI/dashboard và chạy lại toàn bộ. Test vẫn là test đã xem, không độc lập. Không đổi R05 hoặc target/ngưỡng. |

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

| CHG-011 | 05/10/2026 | Người dùng yêu cầu hoàn thiện sản phẩm rồi tạo Word báo cáo tiến độ M2 và slide báo cáo | Thay deferral T13 của CHG-008. Tạo báo cáo tiến độ từ release đã kiểm tra, đọc yêu cầu và giữ giới hạn thực tế. Word/slide có số liệu local không push. R05/cảnh báo sớm và nghiệm thu toàn bài không tự đổi sang đạt. |

### Điều chỉnh ưu tiên sau CHG-011

- **CHG-012, 05/10/2026:** Người dùng yêu cầu chỉ tập trung hoàn thiện project; Word/slide chỉ làm tiếp khi người dùng yêu cầu lại. T13 tạm dừng phần soạn tài liệu, giữ bản nháp cũ làm lịch sử. T09/R05 và T10/R07 tiếp tục xử lý; chưa nghiệm thu toàn bài. Việc tạo báo cáo trước khi đạt tiêu chí trong CHG-011 không phù hợp thứ tự người dùng mong muốn.
- **CHG-013, đăng ký trước chạy ngày 05/10/2026:** thử nghiệm riêng bốn LightGBM context: cửa sổ nhãn 180/365 ngày × Poisson/L1 trọng số 1/y ngày dương. 25 feature gồm lịch biết trước, lịch sử tuyến, tổng quốc gia/toàn hệ thống đã quan sát tại origin. Seed 42, 300 cây, 31 lá, min-child 50, refit 7 ngày; cùng top 10 train/split/horizon/metric. Chỉ chấm validation, chưa tích hợp selection sản xuất; không dùng test để lựa chọn. Test cũ đã được xem ở vòng trước và không trở thành holdout độc lập. Kết quả lưu local riêng, không sửa run v4.
- **Chẩn đoán trực tiếp replay v4:** trong 2.867 sự kiện hết hàng có 1.550 xảy ra trước ngày 7 từ origin; 1.317 có cơ hội báo trước ít nhất 7 ngày, trong đó 409 bị bỏ sót. Trần cơ hội tại origin theo thiết kế reset tồn đầu hiện tại là 45,94%; đây là giới hạn thiết kế replay, không phải bằng chứng ngưỡng dự báo R05 bất khả thi. Giữ mẫu số/metric cũ, không loại ca khó để nâng tỷ lệ. Bước tiếp theo là tách cơ hội theo dõi khỏi lỗi phát hiện và kiểm tra thuật toán cảnh báo.

### E16 — Thử nghiệm context và chẩn đoán cảnh báo trực tiếp

Ngày 05/10/2026, chạy `.venv/Scripts/python.exe validate_context.py` local: bốn cấu hình, 56 lần fit weekly, 40 nhóm model/tuyến h1–7, mỗi nhóm 623 cặp có độ phủ 100%; không có predictions test. TrueMove H validation MAPE từ 38,397185% xuống 36,841717%; LG U+ từ 39,952113% xuống 39,465932%. Các tuyến còn lại không cải thiện; 0/10 đạt 20%. Chưa tích hợp selection sản xuất hoặc chạy test mới. Không khẳng định yêu cầu R05 đã đạt hoặc không thể đạt.

Đầu ra riêng `outputs/context_validation_v1/`: protocol SHA-256 `c6fcb0af461ad15301dd2913db92986e4cb95ae72ca687b9972bbd87bf3b2345`; comparison SHA-256 `ceb954706b244c39a791045b1ce81f387df43630e5a459b075bff2e7bb9d37d9`. Protocol giữ code hash tại thời điểm khởi chạy; sửa diagnostic tồn sau đó không sửa các mô hình/đầu vào experiment.

Chẩn đoán cảnh báo dùng `alert_opportunity_summary` trên alerts v4: 2.867 actual events, 1.550 trước ngày 7, 1.317 có cơ hội, 409 FN trong nhóm có cơ hội; opportunity rate 45,9365%, recall nhóm có cơ hội 68,9446%. Giữ nguyên early-event-rate v4 31,67% và mẫu số tất cả events. File diagnostic SHA-256 `ce763ad032ff7d6f777787cd63891df3291fc15a1ed1541641cf3b87f346e64d`.

Chạy `.venv/Scripts/python.exe -m pytest -q`: **45 passed** sau khi bổ sung fallback cho cửa sổ training toàn 0 (Poisson và weighted L1), gồm ca sửa toàn bộ tương lai các tuyến không đổi feature/nhãn, đối chiếu weekday/tổng quốc gia bằng tay, alignment training/inference h1/7/14 và mẫu số cảnh báo. Raw CSV kiểm hash trực tiếp vẫn `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. Run v4 và Word/slide giữ nguyên; chưa chứng minh production phiên bản mới, chưa nghiệm thu toàn bài. Bước tiếp: xử lý 409 ca bỏ sót và đánh giá cách theo dõi tồn từ sớm; cải thiện mô hình chọn bằng validation, giữ tiêu chí.

### CHG-014 — Tiếp tục hoàn thiện, đăng ký trước run mới

05/10/2026: người dùng yêu cầu tiếp tục tới khi đạt tất cả tiêu chí, không dừng sau mỗi thử nghiệm. T13 vẫn chưa làm tiếp. Tích hợp bốn context vào validation/locked-test/forecast của CLI; thêm sáu phân phối lân cận mùa vụ, bandwidth 14/28/56 ngày × có/không hiệu chỉnh mức bán 28 ngày, action tối thiểu hóa MAPE ngày dương theo kernel Gaussian lịch biết trước. Cả sáu chỉ dùng history tới origin, mức hiệu chỉnh clip 0,5–2 đăng ký trước. Seed/split/top 10/target/metric giữ nguyên; test cũ đã xem, không dùng chọn lại.

Config 1.3.0 có 47 ứng viên top 10. Run mới có thể nhập tường minh **bằng chứng validation lịch sử** của v4: xác minh source/hash, daily/top/config, không nhập metrics test; giữ historical code hash/provenance và chạy 10 ứng viên mới thực sự. Không nhận đã chạy lại SARIMA cũ. Test/forecast/tồn chạy lại theo lựa chọn validation mới. Tối ưu truy cập tồn không thay công thức/stock giả định/mẫu số cảnh báo. Các ca fixture và kiểm cân bằng/run mới phải đạt trước bàn giao.

R07 hiện hành yêu cầu ca chuẩn ngày 10 có ≥7 ngày, ngày 3 không tính đạt, replay không chồng, precision/recall/rate và giới hạn; **không có ngưỡng precision/recall chính thức hoặc cam kết mọi cú sốc**. Phân biệt hoàn thành cơ chế/đo lường với tỷ lệ sớm quan sát thấp. Không sửa yêu cầu để gọi 31,67% thành cảnh báo mọi ca.

### Chẩn đoán giả định nhiễu — đăng ký trước tính toán

Dùng riêng train để mô tả lượng đơn/ngày và phân phối quantity/đơn. Tính rủi ro MAPE của mô hình tham chiếu đơn đến độc lập Poisson, lượng mỗi đơn theo tần suất train, cường độ theo tháng train. Đây là tính toán phụ thuộc giả định, không phải chặn dưới cho mọi thuật toán trên dữ liệu thật, không làm forecast/chọn model và không chấm test. Mục đích kiểm tra mức biến động do số đơn nhỏ trước khi tăng tìm kiếm cấu hình thiếu căn cứ.

### CHG-015 — Đăng ký thử nghiệm số đơn trước chạy

05/10/2026: thử bốn cấu hình validation-only: Poisson lịch gồm weekday, 2 harmonic năm và trend elapsed-year, cửa sổ 365/toàn history; LightGBM context Poisson trên order_count, cửa sổ 180/365 ngày. Số đơn và tỷ lệ quantity/đơn chỉ từ lịch sử success tới fit cutoff. Chuyển cường độ đơn sang forecast quantity bằng phân phối compound Poisson với frequency quantity/đơn lịch sử, action tối thiểu hóa MAPE ngày dương; không dùng phân phối future hoặc ID. Seed 42, refit 7 ngày, cùng split/top10/horizon/metric; bốn cấu hình cố định, chưa tích hợp production và không xem test để chọn. Lý do: quantity 1–4 và số đơn thấp là nguồn phương sai lớn; train 2025 có mức bán cao hơn cùng kỳ 2024, mô hình lịch cũ chưa có trend. Kết quả chưa biết tại lúc đăng ký.

### E17 — Run tích hợp v5 và kiểm tra trực tiếp

Run `sigma_integrated_v5` hoàn tất bảy stage: 47 ứng viên trên top 10, trong đó 37 ứng viên nhập evidence validation v4 được ghi `validation_import.json`, 10 ứng viên mới chạy fresh. Lựa chọn validation mới ở TrueMove H, LG U+, SoftBank và dtac. Test đã dùng lại: 0/10 đạt, MAPE 40,933418–61,957794%, mean route MAPE 49,504049%; độ phủ 100%. Không chọn lại bằng test hoặc nhận cải thiện mọi tuyến.

Manifest có 48 tệp sealed, SHA-256 `24bf4038d5ea51cd8ed15d3fab1250dca2a84c1221f23916248bdbbe81def174`; code SHA-256 `fe8c2f8761cdb407f5dea708b96d326414db0ba72f54e6dd085ac8d4ae9eb582`. `verify_release.py --run-id sigma_integrated_v5` kiểm trực tiếp metric từ predictions, 644 forecast, 1.100.320 dòng ledger số nguyên/không âm/cân bằng, lịch sử bán không đổi trong 13 scenario, strict trigger/Q/MOQ, event duy nhất và 84 package đúng pin. Verification lưu ngoài sealed run, SHA-256 `ea7e84d22e173567dc7143de0fb07266376cba95122c1f0f80e9197000fbab65`.

Replay v5: 5.520 windows, 1.099 đã trống không tính event mới; TP 1.945, FP 861, FN 922; precision 69,315752%, recall 67,840949%, early-event-rate 31,496338%, muộn 1.042. 414 ca FN có cơ hội ≥7 ngày; 1.550 actual events trước ngày 7 vẫn nằm trong mẫu số 2.867. Fill rate base 82,608968%. Không thêm ngưỡng precision/recall chính thức hoặc dùng opportunity recall thay metric chính.

`pytest -q`: 53 passed. AppTest v5 0 exceptions, 10 bảng; kiểm Japan/SoftBank, origin 31/10 và h8–14. `.venv-verify` chạy `demo_integrated_v5_verify`: 14 bảng khớp demo_release, số nguyên tuyệt đối và số thực 1e-8; manifest SHA-256 `1580d41e59aaccf7e3fb1476233aff55b5e7200b44d821e64eddd24d0743bcb4`. Hai môi trường cùng máy không thay diễn tập máy thứ hai. Raw hash giữ nguyên. Word/slide không sửa.

### E18 — Thử nghiệm count CHG-015

`count_validation_v1` chỉ validation, bốn cấu hình có trend/quantity-distribution lịch sử: cải thiện LG U+ (39,465932% xuống khoảng 36,647%), China Mobile (49,202676% xuống khoảng 42,310%) và KT (49,228794% xuống khoảng 45,897%). Vẫn 0/10 đạt 20%, không chấm test hoặc tích hợp production tại thời điểm bằng chứng này. Protocol SHA-256 `b1a0df9b5c19a002b60c8f44c929467afd72c2406d962b49d5e4a5bf82f6be6d`. Action compound Poisson kiểm độc lập bằng SciPy Poisson PMF/brute-force MAPE ở rate 1/3/10 và rate 0 trả 0.

Diagnostic train `train_noise_diagnostic_v1` theo giả định arrival độc lập/quantity thực nghiệm có risk tham chiếu trung bình theo tuyến khoảng 39,8–50,8%; không phải chặn dưới cho mọi thuật toán hoặc bằng chứng test bất khả thi. Không sửa R05, target, top 10 hoặc ngày chấm. Bước tiếp: tích hợp các count candidate có cải thiện validation, kiểm leakage/selection/forecast và run tiếp; mục tiêu hoàn thiện vẫn đang hoạt động, chưa nghiệm thu toàn bài.

**Tiếp tục CHG-015:** Sau kết quả validation ba tuyến cải thiện, tích hợp bốn count candidate vào CLI/test khóa/forecast bằng sales audited để giữ causal basket-size distribution. Config 1.4.0 có 51 ứng viên. Run mới nhập evidence validation v5 tường minh, giữ lineage và không nhận chạy lại 47 ứng viên cũ; count candidate mới chạy fresh. Không thay metric, top 10 hoặc target, không dùng test để chọn. Kiểm tra lại numerical match với experiment, anti-leakage, PMF/action độc lập và run xuyên suốt.

### E19 — Run tích hợp v6 đã kiểm tra trực tiếp

`sigma_integrated_v6` complete bảy stage, 51 ứng viên/top 10: nhập 47 evidence validation v5, bốn count candidate chạy fresh. 51.520 dự báo validation count khớp experiment CHG-015 tại dung sai 1e-8. Lựa chọn mới chỉ dựa validation ở China Mobile, KT, LG U+. Test đã xem: 0/10 đạt, MAPE 40,933418–58,134251%, mean route MAPE 48,216811%; mỗi tuyến đủ 623 cặp h1–7, coverage 100%. Giữ target/top/split/ngưỡng; không nhận kết quả test độc lập.

50 tệp sealed; manifest SHA-256 `8f16bec3f81aa39a7763e371db23989eebee4d190c8c698683ed5fdb2a91ad54`; code SHA-256 `4ca833a16973b7687538ac6447993f1bc6e60bceea37458a51e6463e4f005d29`. `verify_release.py` kiểm metric từ predictions, forecast 644 cặp, 1.100.320 ledger số nguyên/cân bằng, historical_sales 15.968/scenario, strict trigger/Q và 84 package. Verification ngoài run SHA-256 `6ed72f9e83c6ca88fa0245db2c41dbea3174fe8a4949245587b33fe6ea191ead` có cả package versions/lock hash. Code v6 khác v5; không dùng mã mới nhận đã xác minh lại run v5.

Replay: TP 1.931, FP 854, FN 936; precision 69,335727%, recall 67,352633%, early-event-rate 31,391699%, late 1.031, mean day error 4,657690; 5.520 windows/1.099 đã trống. 417 FN có cơ hội ≥7 ngày; 1.550 trước ngày 7 giữ trong mẫu số 2.867. Base fill rate 82,571393%. 59 tests đạt; AppTest v6 0 exception/10 bảng với China/China Mobile, origin 31/10, h8–14. Raw hash nguyên. Word/slide không sửa.

Rà R06 phát hiện ledger tổng item/ngày dù cân bằng không cung cấp thứ tự order_datetime/order_id. Tiếp tục bổ sung event ledger và đối soát giao dịch; không nhận R06 đầy đủ từ bằng chứng tổng ngày hoặc sửa sealed v6.

### CHG-016 — Sổ giao dịch UTC và bảo toàn kịch bản

Theo R06/PLAN 6.2, CLI tồn xử lý receipt đầu ngày rồi sale theo order_datetime UTC/order_id trong toàn ngày. Mỗi sale ghi stock_before/fulfilled/shortage/stock_after vào inventory_events.csv private local, không hiển thị hoặc export ID trên dashboard. Ngày không event vẫn có opening/closing trong ledger ngày. Kịch bản nhu cầu theo item-day giữ tổng số nguyên đã khai báo và phân bổ largest remainders theo quantity lịch sử; hòa phần dư theo thứ tự giao dịch. Historical quantity không sửa; base bằng sale gốc. Cấm tự cắt phần thập phân L/R/MOQ hoặc receipt quantity. Không thay forecast/ngưỡng/metric/target.

Config 1.5.0; giữ config v6 tại config.integrated-v6.json. V7 sẽ nhập evidence validation v6 có lineage, khóa selection chỉ từ validation, chấm test/forecast/tồn lại; không sửa sealed run v6. Verification độc lập kiểm chronological sequence, receipt timing, identity/quantity/timestamp với source audited (không log record), partial fulfillment từng sale, stock chain và các tổng/day. Kiểm thử fixture/tamper trước run thật; chưa nhận v7 hoàn thành hoặc R05 đạt.

### E20 — Chẩn đoán validation của pool và khách hàng

Chỉ đọc validation của sealed v6, tối ưu phép kết hợp không âm các forecast ứng viên đủ coverage/không lỗi, có constant không âm, theo cùng positive-day MAPE h1–7. Fit và score trên cùng validation nên đây là tham chiếu lạc quan hồi cứu, không phải backtest causal, không dùng làm candidate hoặc chấm nghiệm thu. 0/10 đạt 20%; fitted MAPE 35,308842–50,056933%. Protocol SHA-256 `dac8f1e1eb8e38cd67e5a270be2764cd8689ade2482e0c40c93d1d1385776a15`. Phạm vi kết luận: kết hợp tuyến tính pool hiện có vẫn thiếu trên mẫu validation này; không chứng minh mọi mô hình đều không thể đạt. Không đọc test để tối ưu weights.

Train-only: 66.619 sales rows/13.316 customer IDs, 53.303 giao dịch sau lần xuất hiện đầu trong snapshot (80,011708%); median gap 46,119606 ngày. Không xuất IDs. Nhãn customer_type của nguồn là new/returning, không phải B2B/B2C; first-seen trong snapshot không đồng nghĩa khách mới thật. Khoảng cách lặp gần 7/14/28/30 ngày không chứng minh có lịch gia hạn đúng validity_days.

### CHG-017 — Thử nghiệm composition/cohort chỉ trên validation

Bốn ứng viên cố định: cửa sổ 180/365 × weighted L1 positive-day MAPE/Poisson, 31 leaves/min-child 100/300 trees/seed 42. Thêm 11 feature tổng hợp lịch sử: số đơn, first-seen trong snapshot, source-labeled-new share, mean price, eSIM share, basket size và order-date-plus-validity proxy; tất cả cutoff origin. Proxy validity không là activation, expiry thật, cam kết gia hạn hoặc target. Customer/order IDs không đưa vào mô hình/đầu ra public. Protocol được ghi trước fit trong outputs/cohort_validation_v1; kiểm sửa future quantity/validity/price/customer không đổi feature tại cutoff. Chỉ tích hợp nếu validation có lợi, không dùng test chọn hoặc sửa target/top/split/metric. Chưa nhận nghiệm thu mô hình này.

### E21 — Giao dịch v7 đã kiểm trực tiếp

`sigma_transaction_v7` complete bảy stage, config 1.5.0. 51 validation candidate evidence v6 nhập với provenance, không nhận đã fit lại các candidate cũ; test/forecast/tồn chạy lại. Bảy bảng selection/validation/test/acceptance/forecast/demo_forecast/simulation_metrics khớp v6 ở 1e-8 (run_id khác). R05 vẫn 0/10, không đổi target/top/split/metric hoặc chọn bằng test.

51 tệp sealed, manifest SHA-256 `c42bc862631398ab504c237a8ff82f649d1000313690fbb16e4358585fafcd7e`; code SHA-256 `1500b536f16317ceba9bc527f948e578b92fc0c8f92bc1d119f12aaa7959a696`. `verify_release.py` kiểm 1.100.320 ledger rows, 84 pins, 265,994 private events gồm 163,098 sale và 102,896 receipt qua 13 scenario. Kiểm UTC/tiebreak, receipt đầu ngày, sequence, lịch sử IDs/quantity/timestamp/item khớp source audited trong bộ nhớ, partial fulfillment, stock chain và event/day conservation. Verification ngoài sealed run SHA-256 `a0519b80dd364af33e4c0bb34cbfa33a0b2b8f642a5e44cc674acd1f12ca050c`. Không in hoặc đưa source IDs vào tài liệu/Git. Raw SHA-256 nguyên.

75 tests đạt; AppTest 0 exception/10 bảng với South Korea/KT, origin 31/10, h8–14. Demo `demo_transaction_v7_verify` trong .venv-verify tái lập 14 bảng với demo v5, integer exact/float 1e-8; 49.015 event đối soát (43.719 sale/5.296 receipt), AppTest 0 exception/10 bảng. Demo manifest SHA-256 `c11a6d126154a7ab935d5d0665bf7ff7efa7a75444b49b5de81b591021db7a9c`. Hai môi trường cùng máy không thay diễn tập máy khác. Word/slide không sửa; PR draft/mentor review và R05 vẫn mở.

### E22 — Composition/cohort validation CHG-017

Bốn ứng viên hoàn tất 51.520 cặp dự báo, 40 nhóm metric chính đều đủ coverage, 0/10 đạt 20%. Best cohort_365_mape cải thiện hai tuyến trên validation: TrueMove H 35,169584% so với lựa chọn v6 36,841717%; SKT 45,496615% so với 45,868388%. Không cải thiện tám tuyến khác. Protocol SHA-256 `b511832145a16cb5bee22d48e7f605c1b6e63def6613e76853f597454a7f28f7`; experiment chỉ đọc val/train, test chưa chấm cho các ứng viên này.

**Tiếp tục CHG-017:** Tích hợp `src/cohort_models.py` và bốn ứng viên vào CLI/selection/test khóa/forecast, giữ feature horizon causal và không dùng IDs làm input model. Invalid price/validity trở thành missing covariate, không mất sale hợp lệ; validity không nguyên không tự cắt để tạo proxy. 83 tests đạt trước run thật. Config 1.6.0, 55 ứng viên; giữ config v7 ở config.transaction-v7.json. V8 nhập 51 evidence validation v7 tường minh, chạy bốn cohort fresh, khóa selection bằng validation rồi chấm test/forecast/tồn; kiểm numerical match prototype. Không nhận 20% hoặc v8 complete trước kiểm thực.

### E23 — Run cohort v8 đã kiểm trực tiếp

`sigma_cohort_v8` complete bảy stage, catalog 55: nhập 51 evidence validation v7, bốn cohort fresh; selection mới TrueMove H/SKT chỉ bằng validation. 51.520 dự báo cohort production khớp prototype CHG-017 tại 1e-8. Test đã xem: 0/10 đạt, mean route MAPE 48,045274%, range 40,933418–58,134251%; 623 cặp h1–7/tuyến, coverage 100%. Không đổi tiêu chí hoặc chọn bằng test.

53 files sealed, manifest SHA-256 `3ec3c31bb2d95c5486721511a3a5088baf85f4c31725f75779dd4cf9bfb7edae`; code SHA-256 `b7e6d6e6beecc6bdb2c23c6626620f4890075b38c73be911dc2e961993b4ce5d`. Verify metric/644 forecast/1.100.320 ledger/84 pins/265.985 events (163.098 sale/102.887 receipt)/13 scenarios; history identities/quantity/item/timestamp/stock chain/event-day match audited source without public record output. Verification ngoài sealed run SHA-256 `09a2f4c728b9e01d4891ddd6ff34d05968dc8c25095b7ad0a47608e373453e85`, thêm từng code_file hash. Raw hash nguyên.

83 tests đạt. AppTest 0 exception/10 bảng ở Thailand/TrueMove H, origin 31/10 và h8–14. Replay TP 1.936/FP 858/FN 931, precision 69,291339%, recall 67,527032%, early 31,287060%, late 1.039, day error 4,655475; 420 FN có cơ hội ≥7 ngày, không bỏ 1.550 event trước ngày 7 khỏi mẫu số. Base fill rate 82,634018%. Demo `demo_cohort_v8_verify` môi trường thứ hai tái lập 14 bảng v7, 49.015 events đối soát; manifest SHA-256 `5b3bb34e5f647486f7d51c3c1bae468ff5a8e9149cd97be071b5b2ecb535cccf`. Hai môi trường cùng máy không thay diễn tập thật máy khác. Word/slide giữ nguyên.

### CHG-018 / E24 — Count calendar tháng, chỉ validation

Protocol viết trước fit ở outputs/count_monthly_validation_v1; hai ứng viên cố định 365/all, Poisson alpha 0.1, weekday/month indicators và elapsed-year trend biết trước tại origin. Basket distribution/count action giữ causal và positive-day MAPE; không đọc test. 25.760 cặp, đủ coverage ở 20 nhóm h1–7, 0/10 dưới 20%. Best monthly cải thiện sáu tuyến validation so với v8: LG U+ 35,229595%; dtac 38,349461%; au 38,631444%; KT 45,707953%; AIS 46,045369%; NTT Docomo 49,296264%. Bốn tuyến khác không cải thiện. Protocol SHA-256 `93a19b6187db18f472f84495609fec5e8b11b1dbd8ce6e9c55532690a0e9b89e`. Chưa nhận đã tích hợp production hoặc chấm test. Mẫu lịch tháng tránh giả định đã biết các ngày nghỉ bổ sung được công bố sau origin; holiday EDA library hiện vẫn là reference hồi cứu.

**Tiếp tục CHG-018:** Tích hợp countmonth_365/all thành family riêng, giữ count model cũ và chronology/split/metric; config 1.7.0 có 57 ứng viên, config v8 giữ ở config.cohort-v8.json. 92 tests đạt trước run thật, gồm future mask/weekday-month indicators/selected dispatch và operation guards. V9 nhập 55 validation evidence v8, hai monthly candidate fresh rồi khóa selection trước test. Chưa nhận v9 hoàn tất hoặc đạt R05.

### CHG-019 — Origin hợp lệ, demo isolate và allocation reuse

R04/R08: Chặn origin không là ngày UTC đã chốt, thiếu coverage tuyến, thiếu actual hoặc actual_available=false; không dời last observed vào origin tương lai hoặc coi thiếu là 0. R09: Mỗi demo có synthetic_orders.csv riêng trong run, manifest ghi source_relative_path; failed resume không regenerate/overwrite source, không khôi phục source đã mất; không ghi đè run-dir có nội dung khi thiếu provenance. Nguồn doanh nghiệp không sửa. CI/verify đọc đúng nguồn thực được manifest chỉ rõ.

R06/R09: AllocationPlan chia sẻ đúng cùng vectors causal theo origin qua 13 scenario; fingerprint matrix/forecast/config windows ngăn dùng plan cũ. Initial cover/L/safety có thể khác nhưng không thay allocation. Chặn duplicate/missing horizon và negative vector. Kết quả phải đối soát bằng fixture và replay base thật từ forecast v8, không lấy tăng tốc làm bằng chứng forecast đạt. V9 chạy thật theo selection validation mới và verify độc lập. Không sửa sealed v8; không làm Word/slide.

### E25 — Run monthly v9 và operational guards đã kiểm trực tiếp

sigma_monthly_v9 complete bảy stage. Catalog 57; nhập 55 evidence validation v8 có provenance, chỉ hai monthly chạy fresh. 25.760 cặp khớp prototype ở 1e-8. Selection khóa trước test bằng validation, không đổi target/top10/split/metric. Test đã xem: 0/10 đạt, mean route MAPE 46,496812%, range 38,662919–58,134251%; coverage 100%, 623 cặp h1–7/tuyến và 92 target days (không nhận 623 mẫu độc lập). R05 chưa đạt.

55 sealed files; manifest SHA-256 `353f61d689d28ecb473714436754de21cd971e7bd16e4de3283162626030078d`; code SHA-256 `adb70645f08c4cd52f09d566b524c9f48abe5e4bc243a85a66ece4ee8b954bca`. Verification SHA-256 `bd422489fb3347ab949ee936af2dde77fb7b8cba640b551320aa0d4936218bbe` ngoài sealed run: tái tính nguồn audited→daily quantity/train top10/selection validation-only/actual test-forecast, metric/644 forecast/1.100.320 ledger/84 pins; 266.091 events gồm 163.098 sale/102.993 receipt qua 13 scenario khớp lịch sử/chronology/stock chain/tổng ngày. Raw hash nguyên. Khởi tạo từ snapshot trạng thái hiện có, không nhận đã tái dựng availability vận hành thật.

Replay TP 2.005/FP 883/FN 862, precision 69,425208%, recall 69,933729%, early 32,263690%, late 1.080, day error 4,518204; 5.520 windows/1.099 existing empty excluded. Base fill 83,372996% là mô phỏng. R07 không bảo đảm mọi ca, không đặt thêm ngưỡng nghiệm thu.

92 tests đạt. Demo demo_monthly_v9_verify trong .venv-verify tái lập 14 bảng demo v8 ở 1e-8, verify 7.176 ledger/49.015 events/84 pins và nguồn riêng sealed; demo manifest SHA-256 `f8a0540a7733cdf1c2818bf4ddb32aed2f04e328a963093e487b2f54e7191e98`. Real AppTest Thailand/AIS và demo AppTest Vietnam/Vinaphone: 0 exception/10 bảng, origin 31/10/2025, h8–14. QA SHA-256 `804e2cd6ab23472a050d00387546d92247d6f11d859ec1350b2ce438fc488eb8`. Hai môi trường cùng máy chưa thay diễn tập máy khác; chưa nghiệm thu toàn bài, Word/slide không sửa.

CHG-019 AllocationPlan: real base replay theo forecast v8 tái lập hai bảng 84.640 rows/bảng, 21.586 events/12.546 sale/9.040 receipt được đối soát. Summary SHA-256 `e0bf101a3e4af68fe9fee20c6141b1f6d938dbb61d9111926c9e4b1e145f19cf`. Timing 25,248s chuẩn bị/13,589s replay chỉ một lần local, không là benchmark before/after. Origin thiếu actual/non-midnight/stale, duplicate horizon/negative forecast, source missing/changed và stale allocation bị chặn qua fixtures. Không sửa sealed v8 hay xóa lịch sử.

### CHG-020 / E26 — Aggregate arrivals và route shares, chỉ validation

Hai ứng viên đăng ký trước fit: hiercount_365_share90 và hiercount_all_share180. Aggregate Poisson weekday/month/trend trên số đơn tất cả tuyến; route shares = 0,5 historical month + 0,5 recent 90/180 days, month prior strength 100 orders cố định. Chỉ dữ liệu đến origin, quantity basket đến cutoff; không đổi quantity target hoặc ngầm dùng total actual tương lai. Weekly refit, H14, positive-day MAPE action giữ nguyên. Protocol SHA-256 `300b14bf3b561f649ec27188dbfdc7caedb62c3ed6301851ae119ba98165d6cc`; 25.760 pairs, 20 primary groups đủ coverage, future mutation tại train_end không đổi forecast 10 tuyến. Chỉ đọc validation để đánh giá, không dùng test chọn.

Best validation cải thiện bảy tuyến so v9: au 37,162299%; dtac 37,628274%; SKT 44,218517%; KT 45,130124%; AIS 45,456764%; NTT Docomo 49,034660%; SoftBank 50,540080%. LG U+/TrueMove H/China Mobile không cải thiện; 0/10 đạt 20%. Tích hợp hai candidate thành family hiercount riêng trong src/hierarchical_models.py và config 1.8.0; giữ config v9 tại config.monthly-v9.json. 97 tests đạt trước run, gồm causal mutation/all-route share sum/missing actual/all-zero/selected dispatch. V10 nhập 57 evidence validation v9, chạy hai mới rồi khóa trước chấm test; chưa nhận run complete hoặc R05 đạt.

### E27 — Run hierarchical v10 đã kiểm trực tiếp

sigma_hierarchical_v10 complete bảy stage; catalog 59, nhập 57 evidence validation v9 với provenance, chạy hai hiercount fresh. 25.760 cặp khớp prototype 1e-8. Selection đổi bảy tuyến chỉ theo validation, khóa trước test. Test đã xem: 0/10 đạt, mean route MAPE 46.503945%, range 38.582119–58.134251%; coverage 100%, 623 cặp h1–7 và 92 target days/tuyến. KT và au kém hơn v9 trên test, một số tuyến tốt hơn; không chọn lại mô hình dựa trên test. R05 vẫn chưa đạt.

57 sealed files; manifest SHA-256 `2e129eefb493b97b3a3aed4c9cc72f143d952bc278f9d8a24dfab734887683b0`; code SHA-256 `c59fd16eee52bded5bfbee7b4111b4f4cb3ff9811b4cc63191b35eacda7b02c1`; verification SHA-256 `f8114807390d1e113752dfd470f09a6b4f24065cd62175b5a8b6617ee1287c18` ngoài sealed run. Verify nguồn→daily quantity/train top/selection validation-only/actual test/forecast và thêm nhãn quantity/metric toàn bộ validation predictions kể cả cache. 644 forecast/59.248 backtest/1.100.320 ledger/84 pins; 266469 events gồm 163098 sale/103371 receipt qua 13 scenario, đối soát audited source/UTC/partial fulfill/stock chain/day. Raw hash nguyên, không công khai IDs/records.

Replay TP 2030/FP 886/FN 837, precision 69.615912%, recall 70.805720%, early 33.135682%, late 1080, mean day error 4.489163; 5.520 windows/1.099 existing empty excluded. Base fill 83.755010% là mô phỏng, không bảo đảm mọi ca hoặc đặt ngưỡng nghiệm thu mới.

100 tests đạt. Demo demo_hierarchical_v10_verify .venv-verify tái lập 14 bảng v9 ở 1e-8, verify 7.176 ledger/49.015 events/84 pins; source riêng trong sealed run. Demo manifest SHA-256 `069cf056dfea15bd5fc21617a6d18bf99607c6e04347c2f16fa38ce855d51add`; QA SHA-256 `b48abea7497088cc07d5c53f07d5a72c4adc700a1ab2b5139bf1eccf3b775e0d`. AppTest real Thailand/AIS, demo Vietnam/Vinaphone, origin 31/10/2025 và h8–14: 0 exception/10 bảng. Hai môi trường cùng máy chưa thay diễn tập máy khác. V9 đã push b5adbc0; Windows CI [push](https://github.com/khanhnguyenpham/Sigma/actions/runs/37245341018) và [PR](https://github.com/khanhnguyenpham/Sigma/actions/runs/37245343593) success. Không sửa sealed v9, Word/slide không sửa, chưa nghiệm thu toàn bài.

### E28 — Độ nhạy tồn v10, kết luận có đảo chiều

Phân tích mô tả sau replay, không dùng chọn model hoặc feature. Từ ledger sealed v10, tổng demand/fulfilled/shortage theo scenario/tuyến; mean route closing = tổng closing/92 ngày. Summary ngoài sealed run SHA-256 `0e6602c3217fd468e6937020a04652e5b1f99ee2b4c90a4dee0e6cb48673065c`, liên kết parent manifest v10 và hashes hai bảng tổng hợp local. Tồn/nhập vẫn giả định; không công khai bảng riêng tư.

Toàn bộ tuyến gộp: cover 3/7/14 ngày có fill 83,498246/83,755010/84,487725%; L 1/3/7 ngày có fill 90,449649/83,755010/78,920341%; safety multiplier 0,5/1/1,5 có fill 81,788577/83,755010/85,971944%. Khi xét từng tuyến, kết luận chiều fill đảo ở 2/46 tuyến theo cover, 1/46 theo L, 1/46 theo safety. Không nói tăng buffer luôn cải thiện mọi tuyến; đây là kết quả chính sách reorder/ETA/MOQ đang mô phỏng, chưa suy nguyên nhân hoặc tối ưu tham số theo test. Mean stock không luôn tăng theo cover ở 5 tuyến, theo L ở 30 tuyến; theo safety không đảo ở 46 tuyến.

Base fill 83,755010%; partial receipt 50% giảm còn 41,345190%, trễ 3 ngày còn 70,465932%, không nhận còn 7,690381%; surge tăng nhu cầu 3 ngày đạt fill 82,261977%. Drop 1 ngày và drop 7 ngày giữ lượng lịch sử trong events, chỉ scenario_demand đổi; không thay target sales hoặc gọi fulfilled là demand thật. Kịch bản không dự báo trước cú sốc chưa biết và không bao quát mọi trường hợp thực tế.

### E29 — Đủ cặp validation và CI v10

Verify bổ sung kiểm không trùng pair, origins đúng toàn validation, H đủ từng origin/model/tuyến và mỗi model/tuyến đủ số origins, rồi mới tái tính label/metric/selection. Fixture thiếu pair bị chặn dù được seal; missing forecast không có log failure/excluded bị chặn, SARIMA failed có NaN vẫn giữ làm evidence coverage thấp và không chọn. Tổng 101 tests đạt; real sigma_hierarchical_v10 và demo_hierarchical_v10_verify verify lại đạt. Không đổi target/selection/model/forecast/manifest/sealed files; core code hash vẫn khớp v10, raw hash nguyên.

Verification trước E27 lưu nguyên ở outputs/sigma_hierarchical_v10_verification_v1.json, SHA-256 `f8114807390d1e113752dfd470f09a6b4f24065cd62175b5a8b6617ee1287c18`. Kết quả kiểm bổ sung ở outputs/sigma_hierarchical_v10_verification.json, SHA-256 `07ca0273f6e4e5e37e66d704ec89c3f5346e2a4937083e303e216605fe1abf67`; demo verification SHA-256 `3fd42dd3d8444ee8f4615ac041a7b862f73c8baa59f76d8b9ded203afd4fe06d`. Các tệp này local ngoài sealed run, không push. CI commit 173ae9e [push](https://github.com/khanhnguyenpham/Sigma/actions/runs/37246508041) và [PR](https://github.com/khanhnguyenpham/Sigma/actions/runs/37246512646) success với 100 tests lúc đó; kiểm bổ sung 101 tests được push riêng. R05 vẫn 0/10; chưa nghiệm thu toàn bài, chưa làm tiếp Word/slide.

### CHG-021 / E30 — Rà lại chuẩn hóa và loss model theo yêu cầu người dùng

Người dùng yêu cầu tiếp tục hoàn thiện và rà chuẩn hóa dữ liệu/mô hình vì R05 chưa đạt. Đối soát độc lập trực tiếp từ CSV (không gọi src.data.audit_orders/daily_sales): 100.000 rows, 93.104 sales, 118.296 quantity, 66.619 train rows; quantity/day UTC và order_count từng route-day khớp v10 tuyệt đối, top10 train khớp. Covariates validity/data_gb/giá/chi phí/revenue chuyển numeric, flags explicit; invalid=0 trên nguồn này. Không đổi route/item keys, không sửa raw, không làm mượt/xóa outlier target. Feature CSV chỉ train, không IDs, private local. Summary SHA-256 `566902068a408ab15d7b3c67647c61e58ff9c8274513b6ae6ec836a53d6777cc`; đây là bằng chứng kiểm tra trực tiếp, không tự nhận đã tái dựng availability doanh nghiệp.

Pool diagnosis v10: LP nonnegative combination 59 complete/nonfailed candidates + constant, fit và score cùng validation (tham chiếu hồi cứu lạc quan, không candidate causal/không test). Vẫn 0/10 dưới 20%, min 34,388599%, max 48,134049%. Protocol SHA-256 `bd38f44f159726b5e9d50f90946cd17ee4babb9c916239a72089f7db8184f857`. Không chứng minh mọi mô hình đều không thể đạt, chỉ combining pool này chưa đủ trên validation này.

Thử tám direct calendar weighted-L1 cấu hình đăng ký trước fit (365/all × alpha .001/.01 × raw feature/StandardScaler). Scaler chỉ fit dữ liệu đến cutoff mỗi lần, không scale target quantity hoặc fit trên tương lai. 51.520 pairs mỗi nhóm raw/scaled, đủ coverage, kiểm future mutation. Best raw cải thiện AIS 44,054370% và SKT 44,211401%; best scaled cải thiện AIS 43,372739% so 45,456764% v10, chín tuyến khác không tốt hơn. 0/10 đạt 20%; không xem test cho thử nghiệm này. Protocol raw SHA-256 `6291cc7c3ba37c013225f679c9a15f10f4f60f7607f467a6f8e19558c114ab5f`, scaled SHA-256 `8da10d8801655ad3a532285ee9b3f6cf59ca3b0bd4de0c1291ea0da124b3a80e`.

Chỉ tích hợp hai cấu hình có lợi theo validation: monthlad_0_0p001/scaledmonthlad_0_0p001; sáu cấu hình không cải thiện giữ prototype, không tăng production catalog vì số lượng. Config 1.9.0, production catalog 61 (67 đã thử khi tính cả sáu prototype), giữ config v10 ở config.hierarchical-v10.json. src/monthly_lad.py dùng positive-label inverse weights, giữ zero trong evaluation, không đổi quantity/split/top10/metric. V11 nhập 59 evidence validation v10 có lineage, chạy hai mới/khóa trước test; không sửa sealed v10 và không làm Word/slide. Chưa nhận V11 đạt R05 trước run thực.

### E31 — Run scaled/loss v11 và chuẩn hóa độc lập đã kiểm trực tiếp

sigma_scaled_v11 complete bảy stage. Production catalog 61 (59 validation evidence nhập từ v10, hai monthly-L1 fresh). 25.760 cặp production khớp hai prototype 1e-8. AIS chọn scaledmonthlad_0_0p001, SKT chọn monthlad_0_0p001 chỉ bằng validation, khóa trước test. Test đã xem: 0/10 đạt, mean route MAPE 47.589594%, range 41.890877–58.134251%, 623 cặp h1–7/92 target days/tuyến, coverage 100%. AIS/SKT test kém hơn v10; không lấy test để rollback/chọn lại. R05 chưa đạt; không nhận chuẩn hóa chắc chắn tạo độ chính xác 20%.

59 files sealed; manifest SHA-256 `bc32eea8351919d71ce92cda32381845a72ebfba3c8b1873f096feeeee3eb9c2`; core code SHA-256 `e05bc3df1a81bb023d2a5ba01d98efed174183a1a6728a50bec7269b3c5a760f`; verification SHA-256 `113e79831f6ec67c2e1204e6fa72bb33e260fcf109a0ced2ff72489a830622db`. Verify nguyên raw/daily/train-top/quantity labels và metrics tất cả validation, đủ origin–horizon, selection/actual test và forecast/644 forecast/59.248 backtest/1.100.320 ledger/84 pins. 266222 events = 163098 sale + 103124 receipt/13 scenario, source chronology/stock chain/day đối soát. Dữ liệu raw nguyên, run cũ không sửa.

Replay TP 2029/FP 886/FN 838, precision 69.605489%, recall 70.770841%, early 33.100802%, late 1080, mean day error 4.518482; 5.520 windows/1.099 existing-empty excluded. Base fill 83.523297% mô phỏng, không là guarantee hay ngưỡng mentor.

107 tests đạt. Demo demo_scaled_v11_verify .venv-verify tái lập 14 bảng v10 ở 1e-8, 7.176 ledger/49.015 events/84 pins verified. AppTest real Thailand/AIS, demo Vietnam/Vinaphone, 31/10/2025/h8–14: 0 exception/10 bảng. Demo manifest SHA-256 `8231726c40a3f3974c524ef2632df1bdd90bd83e5de8e63996fba86f01217568`; QA SHA-256 `9e63965f78b93fcdbceec63b8cf5bd61279ba51dfd918659f6831913c2868ca3`. Hai môi trường cùng máy chưa thay diễn tập máy khác.

check_data.py production CLI đã chạy nguồn thật v11 và fake demo: normalized numeric feature CSV có validity/revenue flags, không IDs, chỉ train. Real check summary SHA-256 `bb388437aad8f709762d67659552d0ff1477527223f011927c912bbd828f3a6c`; fake summary `c32ac3db89a5f6bfeef5b29503ebe030262f811d63ff6496a23df368aa7c34f7`; v2 recheck v10 `90e5c0b50c1e654d2957268d79a83fc99f63763a60a2e2e27e38008d234566f5`. Độc lập không gọi audit_orders/daily_sales của pipeline, raw→daily count/quantity/top10 khớp tuyệt đối. Root helper không thuộc core model hash, tool hash ghi trong summary. Các output này private ngoài sealed run. Chưa nghiệm thu toàn bài; Word/slide không sửa.

### E32 — Campaign có chọn trong train, chưa có cải thiện đủ để tích hợp

Theo yêu cầu tiếp tục hoàn thiện của người dùng, giữ production v11 và thực hiện một đợt ablation có hệ thống trong validation_campaign.py. Không đổi requirement, không đọc/chấm test cho nghiên cứu; snapshot gốc được audit rồi filter trước daily/features/fit. Mười tuyến xếp hạng theo quantity đến 30/04/2025 cho inner phase, kiểm khớp top10 train cuối kỳ; không lấy thứ hạng cuối kỳ để thay lại nhóm inner. Protocol lưu trước fit, SHA-256 `73ec3e2c04e7f56e089d8875202efcbeb06103220cfe065aa5135661e594dbaf`; tool SHA-256 `f5125b192e05970317ae311d3cc778e6a38d3d73e5edca946ca38e955b05a635`.

12 specs cố định: calendar/history/annual × raw/ratio × leaves7/31; window365, 200 estimators, learning_rate .03, min_child150, lambda10, seed42, threads4. Calendar/history gồm route/country/global past, order-count/basket past, lịch đã biết; annual thêm target-date một năm trước và cửa sổ ±7/±28 đã kết thúc trước origin, căn calendar-year/năm nhuận. Ratio dùng mean90 đến origin (floor1), inverse normalized-label weights tương ứng relative quantity error, forecast trả lại quantity gốc. Zero labels giữ trong đánh giá; target không làm mượt/lọc outlier. LightGBM L1 dùng loss phù hợp MAPE dương, không coi scale là bảo đảm chất lượng.

Inner phase 01/05–30/06/2025 nằm trong train: 102.480 pairs, 120 primary model/route groups full coverage; cả ứng viên tốt nhất mỗi tuyến cũng 0/10 đạt20. Lựa chọn theo MAPE/MAE/lexical khóa trước outer phase; inner-selected SHA-256 `2819a28c637649db0344c642198b3b67eb01aed49594a14b6e61928b2a1b96a7`. Official validation 01/07–30/09: 154.560 pairs, 120 primary groups full coverage, mỗi model/route 623 eligible h1–7 pairs/92 target days. Locked selection mean MAPE 44.968965%, range 36.287133–52.093932%, 0/10 đạt20. Kể cả chọn ứng viên tốt nhất hồi cứu trên outer validation vẫn 0/10 đạt20, không sử dụng cách chọn này cho production. Campaign summary SHA-256 `bf21b46f0a343764b5ab73288415dc5cbd4f7a10ca05674be2b63ff9822fd437`.

Đối soát independent CSV→quantity/day UTC/train-top, đủ origin–horizon mọi model/tuyến, labels, metric và inner lock đạt. So sánh cùng cặp với v11 validation-selected: v11 mean41.978903%, campaign tăng2.990062 điểm phần trăm; một tuyến point estimate tốt hơn, không tuyến nào có toàn CI95% delta dưới0. Bootstrap paired circular full-calendar target-day blocks7, 2.000 draws, seed42; không nhận 623 pairs là 623 ngày độc lập. Baseline v11 được chọn trên chính validation nên so sánh không độc lập; CI là mô tả sau nhiều đợt thử, không bảo đảm tương lai hay chứng minh mọi mô hình không thể đạt20. Quantity1–3 chiếm11.048478% cặp dương và26.906837% tổng relative-error v11 validation; đây là phân rã lỗi, không xác định nguyên nhân hoặc cho phép loại ngày nhỏ.

Kết quả phân tích cuối `outputs/sigma_ablation_analysis_v3/`, summary SHA-256 `e30284a0987c4a7c57603fede53750791878221e5c0439f452b322d105a32088`. V1 protocol có lỗi tên cột raw, v2 sửa trước phân tích, v3 căn full calendar để giữ ngày zero; giữ các protocol cũ local, không thay block/draws/seed theo kết quả. Không chạy phân tích v1/v2 để lựa mô hình, không sửa sealed outputs production. Campaign/analysis đều private local.

111 tests pass (107 có trước + bốn kiểm feature/fit future mutation, calendar-year leap alignment, ratio phục hồi units, inner-selector từ chối validation/test). Source hash và core code hash vẫn khớp E31; toàn bộ 59 sealed files v11 nguyên. Không tích hợp 12 ứng viên vì chưa giúp đạt yêu cầu; catalog production vẫn61, không chạy test lại. TASK/PLAN đồng bộ T09/T12, README/PROJECTMAP/development ghi workflow và giới hạn. R05/R07/T14 vẫn mở; không sửa Word/slide. Bước tiếp là dùng ablation và phân rã lỗi để xác định giả thuyết có tín hiệu ngoài mẫu, không nhận tăng số mô hình/tests là gần nghiệm thu.

### CHG-022 / E33 — Báo cáo tiến độ chi tiết và slide M2 gửi mentor

Ngày 05/10/2026, người dùng yêu cầu gấp Word báo cáo tiến độ chi tiết và slide M2 để nộp mentor trước. Yêu cầu mới kết thúc việc hoãn soạn theo CHG-012 trong phạm vi báo cáo tiến độ, không tự thay đổi nghiệm thu R05/R07/T14. Không bịa tên trường/mentor, đóng góp cá nhân hoặc dữ liệu tồn doanh nghiệp. Phân công sáu thành viên và lịch đến 17/10 là đề xuất, chưa xác nhận thực hiện.

Đầu ra private local `reports/M2_2026-10-05/`:
- `SIGMA_Bao_cao_tien_do_M2_Nop_mentor_2026-10-05_v3.docx`: 18 trang, 19 bảng chỉnh sửa được, một hình EDA từ sealed v11; SHA256 `666284c3b1c0e0ece60786d365518035280047bab0eb700bc7ec9e9a3aa6014c`.
- `SIGMA_Slide_bao_cao_M2_Nop_mentor_2026-10-05_v2.pptx`: 24 slide, 24 phần ghi chú thuyết trình tiếng Việt, 19 bảng native và hai biểu đồ kèm workbook sửa được; SHA256 `b69c4ca74548c4df3e5bbfe0bc5454d59608d69891c2959f632d822efb6c777b`.

Đọc trực tiếp hash các bảng/hình dùng từ v11, raw và các summary/verification/QA/campaign E32 trước soạn. Báo cáo giữ 0/10 R05, MAPE test 41,89–58,13%, coverage 100%, replay sớm 33,10%; tách phương pháp, số liệu validation/test/horizon, 13 scenario và giả định A08–A17. Mã production, CSV gốc và sealed run không sửa; lượt báo cáo không chạy lại mô hình hoặc tests sản phẩm. 111 tests và CI là bằng chứng phiên E32/commit fe69ac1, không nhận chạy lại trong lượt này.

QA thực chạy: canonical render_docx không có LibreOffice nên dùng Microsoft Word hidden export PDF local, Poppler rasterize; đã xem riêng cả 18 trang cuối. PPTX dùng artifact-tool/finalizer: package/layout/font/native table/chart/workbook kiểm đạt, import lại chính file cuối và xem riêng 24 slide. Không nhận đã chạy native PowerPoint. Kiểm XML đếm trang/bảng/ghi chú/chart/workbooks, các số chính và đối chiếu tokens với order/customer IDs nguồn: 0 trùng. Dấu trang/hình giữ nguyên trong bản cuối v3; bản DOCX v2 có lỗi mất ngắt trang trong bước làm sạch chữ, không bàn giao. Logs, PDF/PNGs QA và receipts nằm `.tools/m2_20261005/`, ignored; chỉ hai file cuối giao người dùng, không tự upload/push.

T13/TASK/PLAN/PROJECTMAP đã đồng bộ. Báo cáo tiến độ đã có; nghiệm thu toàn bài còn mở. Bước tiếp: người dùng/nhóm rà báo cáo, diễn tập demo và tiếp tục phân tích R05/R07 theo protocol; không đổi target/split/top10/metric để đạt bằng hình thức.

### E34 — Hiệu chỉnh/kết hợp có chọn trong train, chưa đạt R05

Người dùng yêu cầu tiếp tục hoàn thiện sản phẩm đáp ứng kickoff sau khi nhận báo cáo tiến độ. Tiêu chí R01–R09 giữ nguyên; chưa có quyền sửa ngưỡng/target/split để nhận đạt. Workspace vẫn thiếu ảnh/PDF kickoff gốc, đã đề nghị đối chiếu nguyên văn tiêu chí, không nhận đã đọc nguồn thiếu. R05/R07/T14 chưa đóng; yêu cầu hoàn thiện không tạo bằng chứng để hứa trước độ chính xác.

Đã triển khai `calibrate_campaign.py`: phối hợp convex, affine positive-day weighted-LAD và affine regularized; dùng dự báo causal E32 đã kiểm/hash giữ nguyên. Head học tháng 5, chỉ chấm chọn tháng 6 với origin ≥31/05/2025 để không dùng head fit sau origin; tất cả chọn nằm trong train. Khóa theo tuyến trước chấm validation tháng 7–9. Refit head 7 ngày, nhãn tối đa ≤cutoff, không dùng test chọn/tuning. Không đổi catalog/config/production hoặc báo cáo E33.

Run local `sigma_calibration_campaign_v2` complete, validation 0/10 đạt20%, mean45,106266%, range38,636338–52,101122%; v11 validation mean41,978903%. SKT giảm1,017510 điểm nhưng vẫn43,193891%; chín tuyến khác kém hơn nên chưa có căn cứ để đưa cả phương pháp vào production. Không chấm test mới. Run v1 giữ lịch sử; v2 bổ sung guard phase/horizon/nhãn âm, kết quả giống v1. Summary v2 SHA256 `0eb9d4d87066bbfe6040c05748fa5af452e439b3bdf317cbc40b2327025fde45`, selection SHA256 `6e58875ab3aa6d9e9ff915a3348f4efe77183074f1e0b3437525c0f2b5ad6517`.

`verify_calibration.py` đã chạy độc lập: đọc raw→success quantity UTC/train-top, đủ 11.970 cặp validation (623h1–7 và574h8–14 mỗi tuyến), actual/metric khớp, nhãn head≤cutoff và mọi forecast tái tạo từ weights/base forecasts trong1e−8. Raw và toàn bộ59 sealed files v11 nguyên. Summary đối soát tại `outputs/sigma_calibration_verification_v1/summary.json`, output/IDs giữ private local. Bốn tests mới kiểm future-mutation, nghiệm convex tính tay độc lập, missing coverage bị chặn và nhãn âm không bị bỏ để chấm dễ; full suite115tests đạt. Chưa nhận CI mới trước khi có kết quả remote.

Chẩn đoán train547ngày: meanquantity4,47–9,57/ngày vàstd3,11–5,05; tương quan lag1 sau loại trung bình tháng/weekday −0,0094–0,1037. Calendar fit lạc quan in-sample weighted-median vẫn33,36–42,72% MAPE. Đây là dấu hiệu phần biến động còn lớn và nhóm lịch hiện tại chưa đủ; không phải cận dưới tối ưu cho mọi mô hình, không chứng minh mục tiêu20% bất khả thi. Không dùng diagnostic này làm forecast, bỏ ngày thấp hoặc thay mẫu số.

TASK/PLAN/T09/T12, PROJECTMAP/README/requirements đã đồng bộ. Bước tiếp: đối chiếu kickoff gốc khi có nguồn; kiểm giả thuyết feature/tín hiệu quá khứ dựa trên phân rã sai số, giữ lựa chọn trước chấm và không claim toàn bài đạt. Cần hướng có tín hiệu mới ngoài mẫu, không chạy thêm thuật toán chỉ để tăng số lượng.

Mã/tests/tài liệu E34 cùng cập nhật báo cáo E33 đã push commit `2f15f94` lên `codex/sigma-local-pipeline`; actual CSV/run/Word/slide không trong commit. GitHub Actions kiểm đúng head SHA: [push](https://github.com/khanhnguyenpham/Sigma/actions/runs/37295773007) và [PR](https://github.com/khanhnguyenpham/Sigma/actions/runs/37295779249) đều success. Draft PR1 đã cập nhật mô tả, giữ draft; chưa merge hoặc nghiệm thu. Ghi nhận này chỉ cập nhật bằng chứng remote, không đổi code hoặc kết quả nghiên cứu.

### E35 — Đã đọc ảnh kickoff người dùng gửi lại

Ngày 05/10/2026 người dùng gửi JPG `f43397dd-bd00-4bd4-b239-f1daa267ced2.jpg` và yêu cầu “nhìn và làm đi”. Đã xem trực tiếp ảnh: dự báo kích hoạt theo ngày/tuyến, M1 chuẩn hóa/mùa vụ/baseline, M2 mô hình/MAPE≤20%/top10/so sánh, M3 safety stock/ROP/cảnh báo trước≥7ngày/dashboard; dòng kỹ năng có job định kỳ. [Đối chiếu và nguyên văn](kickoff-checklist.md). Không tự diễn giải dấu `/` thành bắt buộc cả SARIMA/Prophet/LightGBM; ảnh không ghi năm hoặc protocol metric.

Bản sao byte giữ ignored local `reports/requirements/kickoff_received_2026-10-05.jpg`, SHA256 `ee6b9837b60d5321683b1e452204f22b188a5a43f11f8072a4fca9fb82f1b7b2`; không phục hồi ảnh cũ đã xóa/không push ảnh. S01 cập nhật nguồn đã đọc trực tiếp, các ghi nhận thiếu ảnh trước E35 giữ lịch sử. PDF và ảnh mentor M01/M02 vẫn thiếu; M01 số bán/M02 ngưỡng riêng đối tác vẫn là thuật lại, không nâng thành đã xem. Giữ target sales theo M01 và các ràng buộc nguồn hiện hành.

### CHG-023 / E36 — Làm mô hình dự báo tổng quantity trong 7 ngày

Người dùng yêu cầu: “thay vì mô hình dự đoán từng ngày thì dùng mô hình dự đoán tổng lượt bán trong 7 ngày được không, làm đi”. Cho phép triển khai phương án tuần; chưa có bằng chứng mentor chấp thuận thay nghiệm thu theo ngày của S01/R05. Đơn vị giữ quantity/A08, không đổi sang order_count/doanh thu hoặc activation. Giữ split/top10 train/seed, threshold20%; không dùng weekly metric để nhận đạt daily R05.

Đã có `weekly_forecast.py`, `config.weekly.json`, `verify_weekly.py`, `weekly_app.py`, `start_weekly_dashboard.ps1`, mười tests mới và [hướng dẫn](weekly-forecast.md). Đăng ký chín mô hình trước fit: last7, MA28/90, weighted median weekly90/365, bốn LightGBM trực tiếp L1/raw/ratio và Poisson; pooled nhận diện tuyến, lựa chọn riêng từng tuyến. Target là tổng ngày1–7/ngày8–14; lịch/feature chỉ tới origin, weekly label có end≤cutoff, refit7ngày. Ratio được khôi phục quantity. Lựa chọn validation h1–7 weekly positive-MAPE/full coverage rồi MAE/tên, lưu/hash trước tổng hợp/chấm test. Future-mutation/thiếu ngày/nhãn âm/zero-week/conservation/hash/path traversal đều được kiểm bằng fixture giả.

Run `outputs/sigma_weekly_v1/` complete, 46 tuyến/92 tổng tương lai/644 phần ngày theo weekday90 quá khứ. Actual tương lai trống, không gọi phân bổ là mô hình ngày độc lập. Validation khóa8/10≤20%, range12,93–20,41%; test hồi cứu9/10≤20%, mean17,192945%, range13,415419–22,141090%, AIS22,141090% còn chưa đạt. Test này đã được xem trong nghiên cứu ngày, không nhận kiểm định độc lập. Chạy mỗi7ngày cũng9/10, AIS24,589706%; không chọn lịch thuận lợi. Khối8–14 riêng. Các cửa sổ đầy đủ coverage100%, h1–7 có86 cặp/tuyến hoặc13 tuần không chồng lấn. Không chấm tuần thiếu nhãn cuối split như tuần đủ hoặc đổi mẫu số để cải thiện.

`verify_weekly.py` bản kiểm bổ sung chạy `sigma_weekly_verification_v2`: 75.900 cặp raw→UTC quantity→tổng tuần khớp; đủ mọi route/model/block/origin, nhãn fit≤cutoff, lựa chọn đúng validation, manual MAPE/MAE/WAPE/bias khớp trong1e−8, tương lai thiếu actual và tổng phân bổ tuần khớp. Raw hash và59 sealed files v11 nguyên; mã core ngày/config1.9.0/Word/slide không sửa. Verification_v1 giữ lịch sử trước guard toàn nhóm; v2 thêm kiểm đủ route/model/block và hash hai bảng phân tích.

So cùng cửa sổ test, mean weekly MAPE top10: trực tiếp17,192945%; cộng ngày v11 29,898718%; naive40,366682%; MA7 19,177956%; MA28 18,089670%. Phân bổ về ngày có diagnostic mean positive-day MAPE51,108744% trên các cửa sổ đủ tuần, không phải lưới nghiệm thu R05 đầy đủ; không nhận tuần tốt nghĩa là ngày tốt. Chính sách tồn ngày/replay/cảnh báo v11 chưa đổi; cần tích hợp/kiểm riêng forecast phân bổ trước thay đường chạy T10.

Run summary SHA256 `099adf7c5fed3ec66c1dc59865524c4a0d71e0886a2183c83af0ef013f8d1ee3`; selection SHA256 `f8d78e776a8926a95b13b7c9a7a7574079d83f2158de2d775df23d9574eb08ff`. Verification v2 khóa comparison `9b849d8b14ffec8413ac537f193d18b8e0cbd9c4a329323f5e3a3b41d959f2fc`, daily diagnostic `08e3b675ea16d45d297c009d8f04cbff7bdc2570e819a3b7888966bf7085d688`. Các CSV/run giữ local.

`pytest -q` toàn suite125tests đạt; AppTest thật4tab/6bảng/0exception, kiểm Thailand/AIS/lịch7ngày/khối8–14; launcher PowerShell parse đạt. T09/T11/T12 và TASK/PLAN/PROJECTMAP/requirements/data-contract/development/README đã đồng bộ. R05 ngày, AIS tuần, R07/T10 và T14 vẫn mở. Git chỉ mã/config/tests/tài liệu. Bước tiếp: dùng validation và giả thuyết khóa trước chấm để cải thiện, kiểm tích hợp chính sách tồn từ tổng tuần, giữ lịch vận hành còn cần làm; không lấy test AIS để chọn lại hoặc làm lại báo cáo chưa được yêu cầu.

Commit mã `a8421234bcde61df4a4b2303993d54924bf16e9e` đã push lên `codex/sigma-local-pipeline`. GitHub Actions kiểm đúng SHA: [push](https://github.com/khanhnguyenpham/Sigma/actions/runs/37299653238) và [PR](https://github.com/khanhnguyenpham/Sigma/actions/runs/37299659054) đều completed/success trên Windows sạch. Draft PR1 đã cập nhật mô tả đúng daily/weekly/giới hạn, chưa merge. Dashboard tuần server local cổng8502 trả HTTP200/health ok, đã yêu cầu mở panel browser. Chỉ cập nhật tài liệu ghi CI sau commit mã; không đổi forecast/test/selection/run.


### CHG-024/025 — Giao khách, nguồn giả định và thứ tự hoàn thiện

| ID | Ngày | Nguồn | Quyết định và tác động |
|---|---|---|---|
| CHG-024 | 05/10/2026 | Mentor 7 ngày do người dùng thuật lại, người dùng xác nhận **khách đặt→khách nhận** và mô tả order là giả định | M03/U07: D+7 ngày lịch UTC, customer delay 0, không đổi supplier lead time. Code/run/verification lịch giao, menu sản phẩm, job local; giữ nguồn và lịch sử U04/DEC17. Không đổi target hoặc nhận MAPE đạt từ backlog biết trước. |
| CHG-025 | 05/10/2026 | Sau khi đủ yêu cầu/điều kiện, người dùng yêu cầu so sánh dự báo ngày/tổng 7 ngày và tổ chức lại code | U08: giữ T09/T10/T14 đang mở; bản so sánh chính thức và đợt dọn cấu trúc chưa thực hiện. Bảng đối soát metric nghiên cứu không đóng hai việc này; chưa làm tiếp Word/slide. |

### E37 — Customer D+7, menu sản phẩm và job local, 05/10/2026

**Nguồn M03/U07:** người dùng thuật lại mentor, làm rõ customer order→delivery; không có ảnh M03 được đọc. Order hiện được mô tả giả định, chưa độc lập xác minh bộ sinh. Thông tin U04/DEC17 “order thực” là lịch sử; bảo mật/bảo toàn/split/target vẫn giữ. `delivery.py`, config.delivery, independent verify, tests, menu/launcher/job/installer đã có. D+7 UTC gồm weekend; không thay supplierL3 hoặc các stress nhập.

`sigma_delivery_v3` từ V5/v11: 100.000 dòng audit, 80.105 nhóm cam kết, 118.296 quantity, 1.885 quantity đã đặt giao 7 ngày tới; 966 projection rows/46 tuyến×21 ngày,phần đơn mới dự báo 14 ngày 2948,02524067 quantity. Source raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`, summary SHA `e4efa00d63ce135ead1ec2d35a2308aa9dd083165aca319acf0515a4fc5cf741`. Independent `sigma_delivery_verification_v3`: known only orders≤origin; raw aggregation đúng 7 calendar, forecastshift+quantity bảo toàn, actual giao NaN, không export IDs,59 hashes sealed v11 và raw nguyên. V1/V2 và verifier lịch sử giữ local; không sửa sealed run.

CLI refresh tạo `sigma_delivery_job_20261005T123438490909`, lần tiếp `skipped_unchanged`; run job independent verify đạt, summary SHA `29342f177417369f0e74bba0a1b6c99d0d1b14bbd625efd4877da96d297d0c52`. Fixtures kiểm lock chạy chồng, lỗi giữ state tốt bytewise, input change bị chặn và lỗi chỉ log category. Script Windows Task Scheduler parse đạt, **chưa đăng ký lịch nền**, không gọi daily 07:00 active. Server menu chung 8503 health HTTP 200/ok, đã yêu cầu mở panel browser; AppTest 5 trang/filter Thailand-AIS không exception, QA `outputs/sigma_product_qa_v2.json`. Giao lịch không chứng minh actual giao/tồn đủ/MAPE ngày đạt.

CHG-025 giữ thứ tự: đủ điều kiện rồi bản so sánh chính thức ngày/tổng tuần và đợt tổ chức lại code. Chưa đóng hai việc từ các bảng verifier. README/TASK/PLAN/PROJECTMAP/requirements/data-contract/development đồng bộ; Word/slide giữ bản cũ, không tự tạo/upload.

### E38 — Tín hiệu cùng kỳ, macro và head causal cho tổng tuần, 05/10/2026

Các config riêng đăng ký trước fit: V2 annual 12 ứng viên, V3 fixed blend 15, V4 macro 18, V5 calibration 30. Mỗi run chọn validation từng tuyến, full coverage, lock SHA trước test. Mean top 10 test lần lượt 16,090186%;16,180811%;15,997608%;15,966928%. Không chọn phiên bản theo test: V5 validation mean 15,406536% tốt hơn V4 15,440931%; validation V5 9/10, China Mobile 20,411711%; test 9/10, LG U+ 21,356535%,12,672661–21,356535%,coverage 1. Lịch 7 ngày không chồng lấn 9/10, LG U+ 21,027461%. Không đổi LG về model cũ đạt trên test.

V5 summary SHA `a1efacce7ffa492bec53e4fe012676373491848918b8f0a1ebf9258d52893f3e`; selection SHA `63bf14769c237bd1c8431c3d2b71babf65159c538f56ceab534b353af1a5dec8`. Independent verifier `sigma_weekly_calibrated_verification_v1` kiểm 235.290 prediction pairs, raw quantity/top 10/nhãn/coverage/metric/selection/cutoff/future actual NaN/conservation; raw và 59 sealed v11 nguyên. Head verifier `sigma_weekly_calibration_head_verification_v1` refit teacher≤pastorigin, label ends≤headcutoff, reconstruct weighted median/prior/clamp độc lập 27.876 factors, base×factor đúng, 136.620 validation pairs cũ V4 không đổi 1e−8. V2/V3/V4 generic verifiers cũng đã chạy 98.670/121.440/144.210 pairs. Một bản headverifier bị ngắt để sửa reset index khi thêm prior sau lọc zero; bản cuối đã chạy đầy đủ, không thay factor/mô hình/run V5. Test đã xem vẫn đánh giá hồi cứu, không holdout độc lập. R05 ngày v11 0/10 giữ nguyên.

### E39 — Phân bổ tuần vào khuyến nghị tồn và replay cùng mẫu số, 05/10/2026

`weekly_inventory.py` tạo 920 khuyến nghị snapshot 31/12/2025 từ V5/v11: giữ partner thresholds, strict on_hand<ROP,SS/ROP/S/IP/Q/ETA; pending chỉ đơn đã đặt chưa về ở origin. Snapshot tồn v11 đã trừ lúc đặt/reservation, customer D+7 không trừ lần 2. Không áp dụng Q, không gửi đơn; **chưa chạy lại toàn bộ continuous policy bằng tuần**. V1 partial lỗi tênconfig target được giữ local; V2 đã complete, V3 đọc prior only-column tránh DtypeWarning và complete. `sigma_weekly_inventory_v3` summary SHA `5ec46f0fa4101a530f863133950ee30603e8fd0b7a73c5def010d37c1d135c58`.

Replay cùng 5.520 item windows và 2.867 actual events, actual date/path khớp v11: TP 2071/FP 836/FN 796,precision 71,241830%,recall 72,235787%,early 33,728636%; không bỏ early<7 ngày, không tăng tồn vô hạn hoặc đổi mẫu số. Independent `sigma_weekly_inventory_verification_v1`: raw SKU shares/stock/pending integer/threshold/Q/depletion 920 items và raw actual paths 5.520 windows khớp,59 sealed v11 và raw nguyên. Bốn tests mới kiểm conservation H14,strict formula/pending ETA, future mutation, missing block/stale forecast; toàn suite **150 tests pass**. Menu weekly inventory AppTest 2 bảng; R05/R07/T14 vẫn mở; chỉ push mã/config/tests/tài liệu, outputs/job state/reports không push.

**Bàn giao mã E37–E39:** commit `eb1962a3f8de0576600278f4136040ed55784eb9` đã push lên `codex/sigma-local-pipeline`. Xác minh chính xác head SHA: [CI push](https://github.com/khanhnguyenpham/Sigma/actions/runs/37312001266) và [CI PR](https://github.com/khanhnguyenpham/Sigma/actions/runs/37312007859) đều completed/success trên Windows sạch. Draft [PR1](https://github.com/khanhnguyenpham/Sigma/pull/1) đã cập nhật mô tả sản phẩm và giới hạn, chưa merge. Publish scan 37 tệp không có định danh nguồn hoặc credential; kiểm 15 liên kết/anchor mới, fence 12 Markdown và trạng thái TASK/PLAN đạt. Server sản phẩm cổng 8503 vẫn health ok; raw và 59 sealed v11 kiểm lại nguyên, entrypoint tuần khớp protocol đã đăng ký. Commit ghi bằng chứng CI sau đây chỉ sửa tài liệu, không sửa mã hoặc run. Bước tiếp T09/T10: cải thiện ngoài mẫu bằng validation, hoàn tất kiểm policy liên tục từ tuần; giữ R05/R07/T14 mở. Bản so sánh chính thức và tổ chức lại code theo CHG-025 còn chờ đủ điều kiện nghiệm thu.


### CHG-026 — Tiếp tục hoàn thiện theo yêu cầu người dùng, 05/10/2026

Người dùng yêu cầu tiếp tục tới khi đạt. Giữ R01–R09, A08–A17 và CHG-024/025: không thay dữ liệu, top10, split, target hoặc tiêu chí để đạt; không suy customer D+7 thành supplier L=7. T09 tiếp tục thử mô hình chọn validation; T10 hoàn thiện chính sách tồn liên tục theo tuần, T11 bổ sung màn hình 13 kịch bản. R05 ngày/R07/T14 còn mở; bản so sánh chính thức và đợt tổ chức lại code vẫn theo thứ tự CHG-025. Không làm tiếp Word/slide.

### E40 — Mô hình tuần tuyến tính V6 và phối hợp V7, 05/10/2026

V6 đăng ký 34 ứng viên: V5 cộng bốn hồi quy median theo từng tuyến, lịch sin/cos năm 1/2 harmonic, lag đã biết, chuẩn hóa chỉ từ train và L1 alpha 0,001/0,01/0,1. Weight inverse target dương; zero vẫn giữ trong metric. `sigma_weekly_linear_v6`: validation 10/10, mean 15,033558%; test hồi cứu vẫn 9/10, mean 16,109422%, LG U+ 21,356535%. Lựa chọn khóa bằng validation; không đổi LG U+ vì xem test. Summary SHA `673a798f90d5e55f979dff7c8358491ea10ef82d182449c9112b2196a520d800`, selection SHA `b21182537fdc5166d0f8838c25f80e8db5ee8254d36ddd797df0f0229c699266`. `sigma_weekly_linear_verification_v1` kiểm 265.650 cặp; raw và 59 tệp sealed v11 nguyên.

V7 đăng ký 38 ứng viên: thêm bốn phối hợp annual LightGBM/linear, head 56/84 ngày và prior 0/4 tuần. Teacher tại mỗi origin quá khứ chỉ fit nhãn đã có; trọng số phối hợp tối ưu relative absolute loss của các tuần không chồng lấn đã kết thúc tại head cutoff, prior trọng số 0,5. Không học bằng test hoặc actual trong tương lai. V7 đang chạy tại thời điểm ghi đăng ký này; chưa nhận đạt. Tests inverse-relative-loss/convex bounds, future mutation, fit cutoff và dispatch đã pass.

### E41 — Chính sách liên tục theo tuần đã chạy/đối soát, 05/10/2026

`weekly_policy.py` chạy `sigma_weekly_policy_v1` từ V5/v11, giữ nguyên tham số tồn/nhập và 13 kịch bản. Mỗi quyết định có đủ H14 ở 93 origins 30/09–31/12/2025: 59.892 dòng forecast, 1.100.320 dòng ledger và cùng số recommendations, 267.827 events gồm 163.098 sales và 104.729 receipts. Cửa sổ cuối chưa đủ actual vẫn dự báo causal từ model đã khóa, refit neo theo split; actual ngoài nguồn để thiếu. Nhập 00:00 UTC trước bán theo order_datetime/order_id; trừ tồn đúng một lần khi đặt, không trừ lại tại D+7. Summary SHA `79951fb7767b93ae32ee31e8a09b5d005704a22fd37e01e85d22d866c48f0cc3`.

Base fill 85,038828%, nhận 50% fill 42,272044%, trễ nhập 3 ngày 72,463677%, không nhập 7,690381%. Độ nhạy L1 fill 90,837926%, L7 80,241733%, cover14 85,658818%, safety×1,5 87,049098%; đây là mô phỏng, không tối ưu tham số để che thiếu hàng. Replay giữ 5.520 cửa sổ/2.867 actual events/1.099 đã cạn loại trước: early 33,728636%, precision 71,241830%, recall 72,235787%; không bỏ ca cạn dưới 7 ngày.

`sigma_weekly_policy_verification_v1` đã đối soát độc lập mọi dòng số nguyên ledger/Q/IP, ma trận đơn đang về và lượng nhận thiếu/trễ, raw SKU shares/SS/ROP/S, bảo toàn tổng tuần và các forecast đã khóa, thứ tự events và mẫu số replay. 59 tệp v11/raw nguyên. Toàn suite 160 ca pass. AppTest năm trang không exception; tồn tuần có 4 bảng, lọc Thailand/AIS đã kiểm. V1 policy là bản lịch sử code tại lúc chạy; hỗ trợ head mixture bổ sung sau V1 cần run mới. Phần E39 “chưa chạy policy liên tục” đã được thay bằng bằng chứng E41, không sửa run E39.

### Đăng ký mở rộng E42 — mô hình riêng từng tuyến, chưa chạy

Giả thuyết chung: cây pooled có thể chia sẻ sai quan hệ giữa các tuyến; thêm ba boosted median riêng từng tuyến (raw7/ratio7/ratio15) và một median tuyến tính có lịch sử cùng kỳ được impute từ train. Mỗi tuyến dùng lịch sử/scale có sẵn tại origin, weight inverse target dương, route-specific weight normalization, training window và refit giữ nguyên. Annual missing được impute bằng median train và có indicator; không điền bằng dữ liệu tương lai. Bốn ứng viên đăng ký trước fit, chọn vẫn MAPE validation h1–7 rồi MAE/tên với full coverage. Không xem riêng LG U+ trên test để chọn hoặc sửa selection. Chạy sau V7 hoàn tất; kết quả và runtime phải kiểm trước đưa vào sản phẩm.


E42 bổ sung trước fit: V8 dùng 42 ứng viên, tái sử dụng nguyên 288.420 cặp validation của 38 ứng viên V7 sau kiểm hash/nguồn/base protocol/spec và tham số. Chỉ fit bốn ứng viên mới trên validation; selection tính lại trên đủ 42, lưu/hash rồi chạy test mới cho các model được chọn. Không tái sử dụng test để chọn; CLI không có tùy chọn bỏ tuyến khó. Protocol mới ghi SHA summary/prediction của cha và module cache; run cha không bị sửa. Không nhận đã fit lại 38 ứng viên cache trong V8; bỏ tùy chọn cache sẽ fit lại đầy đủ theo cùng cấu hình.


### Đăng ký E43 — phối hợp sau hiệu chỉnh quá khứ, chưa chạy

Giả thuyết: phối hợp dự báo annual đã hiệu chỉnh causal với median lịch trơn hoặc cây macro để giảm phương sai do bất đồng mô hình. Đăng ký sáu ứng viên chung cho đủ 46 tuyến: trọng số annual cố định 25/50/75%, annual parent ratio7/head56/prior4 không đổi; component thứ hai linear h2 alpha0,01 hoặc macro ratio15. Không tìm trọng số theo test hoặc cấu hình riêng LG U+. V9 có 48 ứng viên, tái sử dụng nguyên validation V8 sau xác thực cache, chỉ fit sáu ứng viên mới; selection vẫn cùng MAPE/MAE/tên, test chạy sau khóa. Cần kiểm lượng trước/sau head, fit_cutoff, metric, chính sách tail và UI; chưa nhận đạt.


### Đăng ký E44 — phối hợp annual/macro thích ứng, chưa chạy

Tiếp tục kiểm drift bằng head đã kiểm E40: bốn ứng viên annual ratio7 + macro ratio15, lịch sử teacher 56/84 ngày và prior trọng số0,5 với 0/4 tuần. Teacher labels≤teacher origin, head chỉ học các tuần đã kết thúc tại cutoff, trọng số convex giữ quantity. V10 có 52 ứng viên, giữ 48 validation cũ sau xác thực cache; lựa chọn vẫn cùng tiêu chí, khóa rồi test. Không chọn trọng số theo test hoặc đổi bộ lọc. Không sửa code mô hình giữa V9 đang chạy; cấu hình mới đăng ký riêng trước fit.


E40/V7 bổ sung sau thực chạy: `sigma_weekly_mix_v7` complete, validation 10/10, mean 14.996939%; test tuần hồi cứu 9/10, mean 16.209849%, LG U+ vẫn 21,356535%. Coverage100%, summary SHA `da751df0a169e2282b3fbd1e6ae70fe8ca5346783344fa22806c2eb44fcf5d06`, selection SHA `202d86d3a565126948b52030d3520dc9be8b6167ef954f7fc51f2eb3454aa579`. `sigma_weekly_mix_verification_v1` kiểm 296,010 cặp; raw/59 sealed v11 nguyên. `sigma_weekly_mix_head_verification_v1` kiểm 9,292 trọng số và 31,195 quantity rows, replay teacher/convex objective khớp, 258,060 cặp V6 không đổi.

E42/V8 bổ sung sau thực chạy: `sigma_weekly_local_v8` complete, validation 10/10, mean 14.996939%; test tuần hồi cứu 9/10, mean 16.209849%, LG U+ vẫn 21,356535%. Coverage100%, summary SHA `21e4024b48b95757f70c3ee3c9aab15c91007213ec13f4d7935d538f3716b229`, selection SHA `3795d7bb0c9eb7d49daf3d5fa1afd2d986ce30ce51dc64561417b3cee3e1e26a`. `sigma_weekly_local_verification_v1` kiểm 326,370 cặp; raw/59 sealed v11 nguyên. `sigma_weekly_local_fit_verification_v1` đối soát toàn bộ 288,420 cặp cache V7, tái fit 17 checkpoints đầu/cuối mỗi model/phase và 3,034 cặp, kiểm độc lập 230 bộ median/mean train. Không nhận kiểm mọi checkpoint từ kiểm mẫu; generic đã kiểm đủ mọi nhãn/metric/coverage.

### E45 — Demo đầy đủ từ nguồn tự sinh và cách chọn bundle, 05/10/2026

`demo_product.py --prefix sigma_synthetic_product_v1` đã chạy từ `config.original.json`/seed42, sinh ba tuyến riêng có nhãn generated_synthetic, không đọc/sửa snapshot được cung cấp. Tạo đủ daily/weekly/customer D+7/stock/policy và bốn verifier. Weekly chỉ là demo năm phương pháp/ba tuyến; không thay chiến dịch 48/52 ứng viên hoặc nghiệm thu top10 của nguồn được cung cấp. Synthetic source SHA `b5561e4e0ff084336c98f9fdd2d9f480b309ff0e4d64054932048c2e30c554b0`. Policy demo có 13 kịch bản/7.176 dòng ledger/49.741 events, 36 replay windows; integer balances/Q/IP/chronology và lượng trước/sau D+7 đối soát.

`check_product.py` kiểm cả năm trang và CSV của bundle, cadence7/khối8–14, 21 delivery days/actual thiếu/giao đúngD+7, lượng dự báo bảo toàn; kiểm bốn bộ lọc policy base/nhận50%/trễ3/ngừng nhập và balances của các dòng được hiển thị, không exception. QA `sigma_synthetic_product_qa_v1` giữ local. Chọn `-DeliveryConfig` cho launcher và biến process `SIGMA_DELIVERY_CONFIG`; overview/weekly default lấy lại bundle ở mỗi rerun, không giữ mặc định stale V5. Demo hiển thị3/3 và provenance do phần mềm sinh; không gọi3/10 hoặc dùng dữ liệu demo để nhận đạt nguồn bài. Namespace job theo đường dẫn bundle riêng, không ghi đè state actual; explicit default của CLI/TaskScheduler giữ namespace cũ. Tests env/path escape/state isolation pass. CI bổ sung build/check chính bundle demo này trên Windows sạch; CI mới chưa chạy tại lúc ghi.



### Đăng ký E46 — đủ vòng boosting và hiệu chỉnh causal, chưa chạy

Thử giả thuyết underfit với 300 cây thay vì150 ở learning rate0,03 không đổi; hai parent annual ratio7/macro ratio15 và head56/prior0 hoặc4 cho mỗi parent, tổng sáu ứng viên mới chung đủ46 tuyến. V11 có58 ứng viên; nguồn/split/metric/selection giữ nguyên, cache52 validation cũ chỉ sau xác thực. Cần bổ sung override số cây ở spec và kiểm count/mutation trước chạy; tham số default150 của các model cũ không đổi. Không sửa code khi V10 hoặc policyV2 còn chạy; không chọn cấu hình dựa trên test. Đây là nghiên cứu thêm, chưa nhận đạt R05 hoặc tích hợp.


### CHG-027 — làm so sánh và tổ chức code ngay, 05/10/2026

Người dùng: “bạn làm hoàn thiện và cải tiến hơn cho tôi chưa, làm so sánh sắp xếp lại code các thứ đi”. Thứ tự CHG-025 được thay: làm bản so sánh chính thức và refactor ngay trong lượt này, vẫn tiếp tục mục tiêu hoàn thiện. R05 không đổi; không làm Word/slide. E46 chỉ đăng ký, chưa triển khai override số cây/chưa chạy; cấu hình đề xuất giữ ignored local, không gọi là model đã thực hiện.

### E47 — so sánh cùng cửa sổ và sổ tồn, đã chạy

Run sigma_day_week_comparison_v1 dùng weekly V9/v11/policyV2: 7.590 cửa sổ 46 tuyến, 86 cửa sổ h1–7 và79 h8–14/tuyến; cadence13/12 riêng. MAPE tuần trực tiếp thấp hơn tổng daily model ở cả10 tuyến, mean16,193421%, 9/10 đạt; LG U+21,192259%. Grid ngày R05 vẫn623 cặp/tuyến, 0/10; diagnostic602 cặp h1–7/tuyến chấm cả daily model và phân bổ tuần, không nhận phân bổ là model ngày đạt. So sánh13 kịch bản tồn giữ cùng demand; base fill83,523297% →84,969940%, shortage2631→2400; cảnh báo≥7 ngày33,100802%→33,798396%, cùng2867 sự kiện/5520 cửa sổ/1099 đã cạn loại trước. CSV/Markdown/HTML/hình giữ local, không có source IDs. Nguồn raw và59 v11 files được xác thực nguyên. Summary chứa hash từng bảng/hình và cha; test hồi cứu, không độc lập.

### E48 — đăng ký refactor trước chạy parity

Gom31 implementation vào sigma/forecasting, inventory, delivery, jobs, ui, verification, experiments, analysis; root giữ alias CLI/import để không làm hỏng lệnh cũ. Config nghiên cứu vào configs/experiments; configs/weekly.json giữ48 ứng viên V9, không đổi lựa chọn mô hình. CLI python -m sigma có help và các lệnh theo chức năng. Hash phải trỏ implementation thực và core đã import, không chỉ wrapper. Cho phép dùng lại validation cùng ứng viên sau xác thực; selection tính lại/lưu hash rồi fit test/future mới, parity ở1e-8 và hash raw/59 daily files. Run mới sigma_weekly_refactored_v12 chưa nhận xong tại lúc đăng ký. src/run.py/app.py ngày không đổi.


E43 bổ sung sau chạy: sigma_weekly_combined_v9 đã complete/coverage100%; validation10/10, test9/10, mean16,193421%, LG U+21,192259%. SummarySHA6b8c6e6e774f33c87693f8a8887347c07e236ba63b8ef50f58797a8766415a9b; generic371.910 pairs, kiểm46041 quantity blends/32844 factors và318780 validation cache không đổi. sigma_weekly_policy_v2 complete/13 kịch bản/1100320 ledger/267812 events, basefill84,969940%/early33,798396%; verifier toàn sổ/events/denominator pass. sigma_weekly_inventory_v5 lấy đúng stock parent policyV2 (920 items), verifier pass/5520 replay/2867 events; summaryfb0d399baf32ff9a763852e3fc8d549d128b3843fe935bb9ae36c293f4b1780d. sigma_delivery_v4 nguồnV9 đã verifyD+7/118296 quantity. Không sửa các run cũ.

E44 bổ sung sau chạy: sigma_weekly_macro_mix_v10 complete/52 ứng viên, validation10/10/test9/10; top10 giống V9 nhưng một số tuyến ngoài top10 đổi lựa chọn validation, nên không trộn V10 với policyV9. SummarySHA4f36d45e71340177f527ac75c9aded5a762dd6b0ad3477ba0c605acad48ecb1a; generic402270 pairs, independentmix17204 weights/61722 quantity rows,364320 cache V9 nguyên. Đợt mới CHG-027 dùng cấu hình sản phẩm V9 đã kiểm cùng bộ policy/stock/customer; không chọn lại model top10 bằng test. V10 giữ nghiên cứu riêng.

E48 parity đã chạy: sigma_weekly_refactored_v12 summaryee0f61d065e009381bcaacb06fdf76967f3af895f68c67457ee80793c450f7d1; sigma_weekly_refactor_parity_v1 kiểm364320 cached validation/7590 fresh test/184 selected metrics/92 future/644 allocations, tất cả số thực1e-8 và cùng46 lựa chọn. SHA selection không byte-identical do read/write float CSV: không sửa selection/run cũ để ép hash; mỗi run tự khóa hash trước test, semantic/numerical parity được kiểm trực tiếp. 29 alias chuyển vào legacy; root giữ sản phẩm/job và core ngày. 192 tests pass; demoV2/13 kịch bản đã kiểm, trang so sánh bổ sung và6 trang AppTest demo không exception; bundle nguồn bài sau refactor còn đang kiểm trước promotion.


### E49 — bộ sản phẩm sau refactor đã kiểm và chọn mặc định

V12 generic kiểm371910 prediction pairs; parityE48 giữ model/numeric1e-8. PolicyV3 từV12 có13 scenarios/93 origins/59892 forecasts/1100320 ledger vàrecommendations/267812 events; verifier độc lập quantity integer, raw shares, thresholds, pending event matrix, chronology, tail labels và5520 replay cùng2867 actualevents đạt. SummarySHA43f1ec2986babba4dcc3a4ef30b1392bbd1d289eac7ad3bb9817bdd10a3a3095. Basefill84,969940%/early33,798396% khớpV9 policy.

StockV6 lấy đúng policyV3 closing/pending; 920 SS/ROP/IP/Q/ETA đối soát, summary4eaeb5c1bfb7061222faa8146d8fe8ff538c4765b0100a03b869340557d52cd5. CustomerV5 kiểm80105 groups/118296 historicalqty/1885 knownnext7/966 projectedroute-days, fixed7calendar/no delay/actualmissing; summary6afe75ad6367dac6b8179b6c6d478f29c3707ba27e5d38fa448a9beda2ef8aaa. Bundle staging6 trang AppTest không exception,4 scenarios base/partial/late/none mỗi1840 ThailandAIS ledger rows khớp balance. config.delivery.json được chọnV12 sau tất cả evidence đã verified, SHA552cf2398eac298c6fec69667ee5f79afd130fc6dca29c112baf09eb3da2a823.

So sánhV2 giữ đúng7590 windows/13 scenarios; bốn CSV aggregate vàfigure byte-identical vớiV1 trướcrefactor; prose sửa nhãn chưa đạt chung. Tất cả output giữ local. DemoV3 từ nguồn sinh riêng đã chạy đầy đủ CLI mới gồm compare, verify vàpolicy/stock/customer; không đọc suppliedCSV. SourceSHA b5561e4e0ff084336c98f9fdd2d9f480b309ff0e4d64054932048c2e30c554b0, chỉ3 tuyến khôngcertify top10. 192tests/full đã đạt,14ca affected delivery/bundle/alias pass sau guardhash. R05/R07/T14 còn mở; test hồi cứu, không tự nhận100%.


E49 bổ sung refresh: CLI defaultV12 tạo sigma_delivery_job_20261005T160156072664 rồi lần kế tiếp skipped_unchanged; verifier rawD+7/80105groups/118296qty/966days pass, summary80136b5979c0e754f4d41c4b5a757e65948adae745e0fe294f2d1db905300f2e. Jobstate local, lịchWindows vẫn chưa cài. DemoV3 QA6 trang/current canonical paths/4 scenariofilters pass ởsigma_synthetic_product_qa_v4; không thay bằng runprivate trên CI. Quétpublish143 text files không IDs/token, khôngCSV/outputs/reports/.tools;203 local links/anchors và15 Markdown fences pass, hai link nguồn lịch sử thiếu được giữ khai báo, không phục hồi.


### E50 — commit và Windows CI của bản mã đã tổ chức

Commit mã043cf8595803f6331ebec4ca1eac14aa63af849e đã push codex/sigma-local-pipeline. Kiểm đúnghead, hai workflow hoàn tấtsuccess: [push CI](https://github.com/khanhnguyenpham/Sigma/actions/runs/37338362331), [PR CI](https://github.com/khanhnguyenpham/Sigma/actions/runs/37338369564). Windows sạch cài dependencies/pipcheck,192tests, dailyfake/audit, fullsyntheticproduct/compare/verifiers và6-pageAppTest/scenariofilters pass; không có suppliedCSV trên CI. Artifact PR1 vẫnattached/draft, khôngmerge. Health local8503 trả200/ok. Các chỉnh docs/TXT ghi E50 về sau không đổi implementation đã kiểm ởcommit này.

Cập nhật mô tả PR bằng nội dung đã chuẩn bị bị automated approval review từ chối: reviewer xem đây là external messaging vàcông bố riêng aggregate private-derived metadata, không coi quyềnpushcode là quyềnupdatePRbody. Đã hỏi người dùng quyền riêng; chưa nhận trả lời/chưa sửa PRbody, khôngworkaround. Việc đọc CI/commitcode/kiểm vàbàn giao vẫn hoàn tất trong phạm vi đã cho phép.


### CHG-028 — Hoàn thiện tối đa sản phẩm phục vụ M2–M3, 06/10/2026

Nguồn: người dùng yêu cầu tinh chỉnh sản phẩm cuối để đem báo cáo M2–M3. Tiếp tục T09–T12/T14, giữ R05 ngày và metric tuần riêng; chưa tạo lại Word/slide. Không nâng giả định/đạt kỹ thuật thành nghiệm thu. Bản V12 vẫn là mặc định cho tới khi có kiểm tra đủ bộ phụ thuộc. Không đăng lại nội dung PR đang chờ người dùng cho phép.

### E51 — Đăng ký ngân sách booster trước chạy V13, 06/10/2026

E46 đã đăng ký giả thuyết 300 cây nhưng hoãn khi tổ chức mã. Nay `sigma/forecasting/boosting.py` kiểm số nguyên1–2000 và override chỉ cho booster; pooled/local dùng đúng override, mặc định cũ giữ nguyên. 28 ca kiểm booster/local/weekly đạt, gồm số cây thực23 và future mutation. Cấu hình `configs/experiments/weekly-boost.json`: giữ52 ứng viên V10, thêm2 parent300cây +4 head causalhistory56/prior0 hoặc4 (58 tổng), learning rate/split/source/top10/metric giữ nguyên. Dự kiến run mới `sigma_weekly_boost_v13`, authenticate cache validationV10, khóa selection mới trước fresh test; test đã xem, không là kiểm định độc lập. Đây là đăng ký trước fit, chưa có kết quả V13.


### E52 — Quy tắc chọn bản tích hợp trước kết quả testV13, 06/10/2026

Đã đọc selection validation khóaV13: top10 mean14,978399%,10/10; TrueMoveH chọn annual300, LG U+ giữ calblendmacro75. Chưa đọc summary/metric testV13. Quy tắc tích hợp: nếu generic verifier/source/conservation/cutoff/cache và tests đạt, dùng selectionV13 từ validation cho bộ sản phẩm mới, bất kể test có cải thiện hay không; không chọn V12/V13 bằng test. Không ghi đè bộ báo cáoV12 đã khóa. Tạo policy/snapshot/customer/comparison/QA mới tương ứng trước khi đổi mặc định; giữ R05 mở.


### E53 — V13 đã chạy và đối soát độc lập, 06/10/2026

Run sigma_weekly_boost_v13 complete,58 ứng viên; cache394680 validationpairs từV10,6 ứng viên mới fitvalidation, fresh test/future. SelectionSHA1b24d9ed4d33ea5a407d634c83b0cdac2df62d41aebdf8250dfb3797c5f93848 khóa trước test; summarySHAd2e0a1fedede62c7fa02f154100223423aad71d404e6bd52378005c4ac057d2f. Validation10/10mean14,978399%; test9/10mean16,173459%,LG U+21,192259%,coverage100%. Generic sigma_weekly_boost_verification_v13 kiểm447810pairs, nhãnquantityUTC/toptrain/metric/cutoff/grid/fullcoverage/phân bổH14/actualNaN/source và59 tệp sealedv11 đạt. Calibration replay chi tiết đang chạy, chưa nhận hoàn tất. CustomerV6/verificationV6 kiểm80105groups/118296quantity/1885knownnext7/966route-days; futureH14qty2926,629101; summarySHA1a5e42cd1887d22a730415e58e2ca6ce8831e894991ac92e36d040a8fbd1c5bd. PolicyV4 còn đang chuẩn bịH14; chưa đổi mặc định. Lệnh verify-delivery gọi sớm khi run chưa complete đã được chạy lại đúng sau khicomplete, đạt; lỗi CLI flag ban đầu không là lỗi artifact.214tests toàn bộ đạt. app.py thêm3 dòng khóa menu run bằng SIGMA_LOCKED_RUN_ID; src/run.py/CSV và59 artifactv11 nguyên, không đổi dự báo ngày.


### E54 — Bộ trình diễn M2–M3 và bản tích hợpV13, 06/10/2026

Đã hoàn tất calibration replay42136factors/136620oldvalidationpairs; policyV4 kiểm13kịch bản/1100320ledger/267908events(163098sale+104810receipts),93originsH14/59892forecasts,chronology/cutoff/integerquantity/parentprediction/raw59sealed đạt. Basefill85,020040%,shortage2392; partial42,265782%,late72,457415%,none7,690381%; early33,728636%,TP2061/FP845/FN806,precision70,922230%,recall71,886990%,2867events/5520windows/1099alreadyemptyexcluded. StockV7 kiểm920items/5520replay, đúngpolicyV4,stricttrigger/quantity/nodoubledebit. CustomerV6/compareV3 đối soát; checkpointV3 kiểmsource/parents/protocolhash/top10/comparison vàexportHTML/CSV/configđãkhóa. AppTest sigma_m2m3_v13_ui_qa:6trang/4kịch bản/SKU+product_type, lựa chọn run ngày chỉV11,khôngexception; bộ demo phầnmềm sinhV4 vàQAđãkiểm riêng.214tests toàn bộ đạt,21tests liênquanjob/bundle/release đạt sau bổsung last_attempttimestamp. app.py chỉ3dòngkhóa run,src/run.pynguyên;59artifactV11+rawnguyên. Bundlemặc định được chuyểnV13 theoquy tắcE52 saukiểm,khôngđổi nghiệmthu.

Windows task SIGMA-Customer-Delivery-Refresh đã cài07:00+07,pythonwẩn,IgnoreNew/StartWhenAvailable/30minmax; Start-ScheduledTask chạy thật LastTaskResult0/Ready,NextRunTime06/10/202607:00. Sandbox đọcSchedulerbịAccessDenied đã đọc lại bằng escalationthànhcông; không làauto-review rejection. CLIrefreshskipped_unchanged giữlastgoodV12 trước chuyểnmặcđịnh; jobcode nayghi last_attempt ngay cảskip. Source/run thật giữlocal,scheduledjobkhôngupload. Server8504bộV12 kiểm200/ok trước chuyểnlauncher; bảnV13 cần khởiđộng lại riêng. Không làm lạiWord/slide,khôngcậpnhậtPRbody đangchờcho phép.

Hashsummary: sigma_weekly_boost_v13: d2e0a1fedede62c7fa02f154100223423aad71d404e6bd52378005c4ac057d2f; sigma_weekly_policy_v4: 084c782c4972cdb45c4e55825be36547e4e98a537c3258341e99c9fad68e8d96; sigma_weekly_inventory_v7: 14c383ffb2f52925a58210ed359076fa89bbebd968134e4e183b2e79ed04c0f6; sigma_delivery_v6: 1a5e42cd1887d22a730415e58e2ca6ce8831e894991ac92e36d040a8fbd1c5bd; sigma_day_week_comparison_v3: 5d0192bd452d67b26bb0ab8f9dd033590a974f328510905c1a94eceaeff97925; sigma_m2m3_checkpoint_v3: 259eca998d44956a011f40b6272cc5390f51fbf641c6813184305cac48a180db.


### E55 — Kiểm cuối, job V13 và GitHub CI, 06/10/2026

- Code commit `183ed104f61351c3bc0aed3be285300ad555fb87` đã push lên `codex/sigma-local-pipeline`, 39 tệp mã/config/tests/tài liệu; chỉ `data/README.md` được tracked trong data/outputs/reports/.tools/.venv, không có CSV hay run thật. Privacy scan 39 tệp không có order/customer ID hoặc mẫu credential; 195 link/anchor Markdown và fences đạt, hai nguồn lịch sử thiếu giữ nguyên.
- CI Windows của đúng commit: [push](https://github.com/khanhnguyenpham/Sigma/actions/runs/37354219823) và [pull_request](https://github.com/khanhnguyenpham/Sigma/actions/runs/37354225347) đều completed/success. Pip check/tests/demo ngày/audit dữ liệu giả/full bundle tự khóa/đối soát/sáu trang và scenario filters/standalone dashboard đều đạt. Full local pytest cuối sau chuyển config V13 và sửa job đạt 214 tests.
- Default refresh V13 tạo `sigma_delivery_job_20261005T180738816751`, sau đó `skipped_unchanged`; verification V5 kiểm D+7,80105 nhóm/118296 quantity/1885 known-next7/966 route-days/raw/59 sealed đạt, summarySHA618d0e4d9654f88069f6b348e81f70162cc5a9599183492ffe73e10748277332. Scheduler chạy lại 06/10/2026 01:10:55+07, LastTaskResult0, NextRunTime07:00; last_attempt ghi timestamp mới khi skip, last-good giữ nguyên.
- Server SIGMA đã khởi động lại với checkpoint V3 tại 127.0.0.1:8504, health200/ok. Owned exec session trước được dừng bằng Ctrl+C sau khi native Stop-Process lỗi; không nhận native stop đã thành công. Browser/file mở trong Codex trả queued, không nhận đã hiện tab. Start_m2m3.ps1 trỏ đúng V3; launcher đã chạy thật và parsecheck đạt.
- Mô tả PR vẫn cũ: chưa gửi lại hành động bị automatic approval review từ chối ở E50 do chưa có quyền gửi số liệu tổng hợp trong nội dung PR. PR vẫn draft, chưa merge. Không thay raw/target/top10/split/metric, không tạo Word/slide mới. Sản phẩm dùng được để demo tiến độ; R05/R07 và mentor nghiệm thu còn mở.

### E57 — Chẩn đoán, thử nghiệm bị loại và màn hình giải thích cảnh báo, 06/10/2026

- CHG-029/E56 đã đăng ký sáu ứng viên trước fit trong protocol local. `sigma_seasonal_validation_v14` complete: 45.540 cặp validation, 46 tuyến, đủ độ phủ; best research từng top 10 chỉ 4/10 đạt20%, 0/10 cải thiện so với V13. Ba tuyến ngoài top 10 cải thiện, chưa tích hợp hoặc chấm test. Giữ sản phẩm V13, không có dự báo/test/selection production mới.
- `sigma_seasonal_verification_v14` kiểm độc lập tổng quantity của từng nhãn, 1.104 nhóm metric, toàn bộ origin/horizon, khóa so sánh theo validation và 12 future-mutation (sáu ứng viên tại hai cutoff). RawSHA6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b và 59 artifact ngày v11 nguyên. Research summarySHA27a1a462699a8325adee1764e2f71d1fc65c11af572f36fb181072c010f7e82f; verifierSHA4f9793a3cef07fa52c45e681c7ae71a8991958c177e247ba3085c719a56698a0.
- `dispersion.csv` chỉ dùng train/validation: CV ngày validation top10 0,454–0,598, CV tổng7 ngày0,201–0,348. Fit hồi cứu tháng×weekday MAPE24,54–36,86% chỉ là mô tả, không forecast/cận dưới/chứng minh mục tiêu bất khả thi. Tài liệu `docs/model-diagnostics.md` ghi phạm vi và cách giải thích, không sửa tiêu chí hoặc cam kết điểm.
- `sigma/analysis/alert_diagnostics.py` + trang tồn hiển thị từng ca không dùng event/order/customer ID, lọc nhóm/tuyến/SKU/loại. Kiểm lại policyV4: 2867events,1550cạntrướcngày7,1317cócơhội,967phát hiện,350bỏ sót; tỷ lệ chính967/2867=33,73%, chẩn đoán967/1317=73,42% không thay mẫu số. 1099alreadyempty loại riêng đúng protocol. Không dùng actual hồi cứu làm feature cảnh báo.
- Toàn pytest local đạt225, collect xác nhận225. AppTest `sigma_m2m3_diagnostics_filter_ui_v14` và `sigma_synthetic_diagnostics_ui_v14` kiểm sáu trang, bốn kịch bản, nhóm cảnh báo/SKU/loại và sổ 92ngày/mặt hàng; không exception. Lần đầu gọi QA synthetic với tuyến Thailand/AIS bị guard từ chối vì fixture không có tuyến đó; đã dùng đúng tuyến giả mặc định và chạy lại đạt. Mã verifier nay hash cả analysis được UI import.
- Bộ khóaV3 summarySHA259eca998d44956a011f40b6272cc5390f51fbf641c6813184305cac48a180db nguyên; UI QA mới thay bằng chứng giao diện cũ, không cần fit lại forecast/tồn khi chỉ thêm diễn giải. TASK/PLAN/PROJECTMAP/README/code-map/demo cập nhật, không tạo Word/slide hoặc sửa nội dung PR. R05/R07/T14 giữ mở. CI của thay đổi mới chưa kiểm; CI183ed10/214tests giữ lịch sử. Bước mô hình kế tiếp cần kiểm độ ổn định theo các khối thời gian trong train/validation, không tiếp tục dò cùng test hoặc tăng cây không có giả thuyết.


### CHG-030 / E58 — Ba họ mô hình và ba thư mục kết quả, 06/10/2026

- Nguồn: người dùng yêu cầu ưu tiên LightGBM/SARIMA/Prophet và các biến thể cho ngày và trực tiếp tổng7, sau đó yêu cầu triển khai và tạo ba thư mục riêng. Đây là quyền chạy thử nghiệm local; không phải mentor xác nhận thay R05 ngày. T07–T09/T12/requirements/PLAN/TASK được đồng bộ; sản phẩm46 tuyến V13/tồn/cảnh báo không chuyển sang pool mới.
- Thêm CLI model-families, verify-model-families, configs/model_families.json, pipeline, verifier,9 ca kiểm tra và docs/model-families.md. Cài Prophet1.5.0/cmdstanpy1.3.0/stanio0.5.1/tqdm4.70.1 vào .venv, khóa requirements và pip check đạt. Có24 cấu hình họ×mục tiêu,240 candidate/tuyến validation; top10 train, split/horizon14/refit7 và metric nguyên, cửa sổ nhãn365 ngày. LightGBM pooled top10; SARIMA/Prophet riêng tuyến.
- Lượt đầu dừng ở worker Windows do runpy làm hàm worker nằm trong __main__, chưa chấm test; lưu ở outputs/m2_three_models_20261006_attempt1 với status failed. Đã gọi worker qua module canonical, chạy lại đầy đủ. Dự báo validation LightGBM ngày chạy lại khớp SHA với lượt đầu. Không xóa kết quả lỗi hoặc gọi nó là run complete.
- Run m2_three_models_20261006 complete:309 artifact, ba thư mục LightGBM/SARIMA/Prophet, mỗi thư mục có daily/direct_7d và validation/test/future predictions, metrics, lựa chọn, fit logs. Fit thật toàn bộ candidate;0 lỗi hội tụ/forecast. Khóa cả sáu nhánh trước test, family_selected SHA0a61abc563017368f51af4292ceef9c3be3081fb65c94ad2a305c237bf70e9e5; overall_selected SHA8b8ef954c6f483432a6e2283c4b73217efed9f1013fb7d78ca389d899d0a197f. Run manifest SHA2449341dd0c66574045965297a067ec7d10032688b21cd72626e3c40a48a3c5b.
- Test ngày LightGBM/SARIMA/Prophet lần lượt47,770132/54,634202/57,281331%, đều0/10 đạt20%. Trực tiếp tổng7 lần lượt16,830027/16,920597/26,431040%, đạt8/8/3 tuyến. Cộng dự báo ngày thành tổng7 lần lượt36,529121/20,665894/23,699286%. Độ phủ100%; ngày và tổng có mẫu số khác nhau. Hai phương án tổng dùng cùng cửa sổ/actual; mô hình ngày vẫn chọn theo metric ngày. Baseline MA28 tổng18,089670%,7/10.
- LightGBM thắng validation cả20 lựa chọn tuyến×mục tiêu trong grid đăng ký; không chọn lại bằng test dù một số tuyến SARIMA/Prophet có test tốt hơn. LightGBM tổng7 còn au(KDDI)20,114787%, LG U+22,015303%. Pool mới hẹp hơn pool V13 và huấn luyện pooled top10; không kế thừa thành tích9/10 của pool cũ. Prophet năm Fourier3 trên365 ngày có giới hạn nhận dạng trend/mùa vụ; log1p SARIMA dùng expm1 điểm, chưa hiệu chỉnh bias.
- Verifier độc lập m2_three_models_20261006_review đọc raw, đối chiếu quantity/top10/221.280 dòng/2.040 nhóm metric, cadence, nhãn đủ bảy ngày, cutoff, lựa chọn, khóa, baseline và tương lai actual trống; status verified. Raw SHA6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b nguyên. Validate58 artifact sealed ngày sigma_full_m2_20261005 và toàn bộ file run tuần sigma_weekly_v13_m2_analysis_20261006 local nguyên; không nhận đã kiểm59 artifact trên máy khác.
- 45 kiểm tra liên quan đạt, gồm9 mới về tính tay nhãn/tổng, actual tương lai, future-mutation sáu nhánh estimator thật, candidate thiếu dự báo, selection cấm test và verifier phát hiện WAPE sai. Chạy kiểm tra SARIMA/Prophet cập nhật/refit chín origin trên fixture cho16 trường hợp biến thể×mục tiêu cũng không lỗi. Pip check/compile/diff check đạt; CI/full suite toàn repo chưa chạy lại. Biểu đồ đã xem trực tiếp, báo cáo Markdown/bảng tuyến trong review local.
- Test đã xem trước, chỉ đánh giá hồi cứu; R05/R07/T14 giữ mở. Không push/upload, không đổi raw, không viết lại Word/slide, không đổi lịch Windows hoặc cấu hình sản phẩm.


### CHG-031 / E59 — Gom M2 vào bốn thư mục, 06/10/2026

- Nguồn: người dùng yêu cầu tách một folder riêng M2 và đem những thứ thuộc về nó vào, kèm hình artifacts/models/notebooks/reports. Đã tạo M2 cùng bốn phần, README có đường dẫn/lệnh chạy. Phạm vi là tổ chức tệp và bảo toàn bằng chứng, không đổi model/target/split/selection/nghiệm thu.
- Chuyển25 bộ/tệp đầu ra có tên M2 từ outputs vào M2/artifacts hoặc M2/reports, giữ nguyên cả các bộ đã seal (kể cả đầu ra mô phỏng đi kèm). Nguồn dữ liệu và core dùng chung giữ làm phụ thuộc của project. Các đường outputs cũ dùng junction cho thư mục và hardlink cho tệp để những caller/historical link tiếp tục đọc được; nội dung chính nằm trong M2.
- Chuyển6 tệp mã/cấu hình/tài liệu/tests vào M2: families.py, verify.py, model_families.json, build_report.py, tests/test_model_families.py và reports/model-families.md. Thêm notebook đọc kết quả; pytest testpaths và CLI trỏ vào M2. Hai import sigma cũ là alias, docs/model-families.md là chỉ dẫn tới vị trí mới. Future run ghi M2/artifacts, verifier ghi M2/reports.
- Trước move đã ghi hash583 tệp kết quả. M2/artifacts/relocation_before.json và relocation_checked.json chứng minh tất cả583 tệp nguyên byte. Với hardlink, kiểm samefile tới đích trước đối chiếu hash; đường resolve của hardlink vẫn là tên ban đầu, khác junction. Không sửa manifest, metric, forecast hoặc các báo cáo đã seal khi chuyển.
- Mã families.py lịch sử có SHA5b696015cde310d3cb8d53b555ddac1589046c44515c6c9e6dad3fc83c446791, được giữ nguyên trong M2/artifacts/source_snapshots/<sha>/families.py. Verifier chấp nhận nguồn hiện hành đúng hash hoặc snapshot đúng hash, không viết hash mới vào manifest cũ. Thêm ca kiểm snapshot sai/thiếu phải bị từ chối. Các lần chạy mới hash cả implementation M2/models/families.py.
- 13 kiểm tra đạt (11 M2 gồm9 cũ+2 layout,2 core organization). CLI help hai lệnh đạt; notebook v4 validate và ba code cell chạy được, đọc9 hàng summary/20 lựa chọn, lưu notebook không có output. Kiểm13 link mới và Git ignore dữ liệu/report private đạt.
- Chạy verify-model-families từ CLI mới cho m2_three_models_20261006, tạo m2_three_models_20261006_organized: verified221.280 dòng/2.040 nhóm metric,0 candidate lỗi, nguồn/selection/future actual nguyên. Run manifest vẫn SHA2449341dd0c66574045965297a067ec7d10032688b21cd72626e3c40a48a3c5b. Báo cáo mới trỏ về M2; PNG và bảng tuyến có hash giống bản trước. Validate run từ đường M2 và outputs đều kiểm309 artifact đạt.
- TASK/PLAN/PROJECTMAP/README/code-map cập nhật đường hiện hành, lịch sử E58 giữ nguyên. Không refit dữ liệu thật, không upload/push, không đổi tồn/lịch Windows/Word/slide. R05/R07/T14 giữ trạng thái; CI/full suite không chạy lại cho việc đổi cấu trúc.

### CHG-032 / E60 — Tách mã theo từng họ mô hình, 06/10/2026

- Nguồn: người dùng yêu cầu trong models tách folder riêng cho từng mô hình để dễ đọc và thêm mô hình. LightGBM, SARIMA, Prophet mỗi họ có model.py, variants.json, README.md và package __init__.py. Cấu hình chung tham chiếu biến thể theo đường dẫn, registry nạp thành giá trị cụ thể trong manifest. Mọi biến thể khớp cấu hình run đã khóa.
- families.py giữ protocol/backtest/selection, common.py giữ nhãn và schema; registry.py đăng ký rõ từng module. Mô hình riêng tuyến dùng fit/update/predict; pooled dùng phase. Runner và verifier duyệt họ/biến thể trong cấu hình, bỏ giới hạn cứng ba tên/bốn biến thể. Không thêm cơ chế tự khám phá hoặc phụ thuộc mới. New-run provenance hash cả các module M2. Hướng dẫn thêm họ/biến thể ở M2/models/README.md.
- Kiểm độc lập với source snapshot chính xác SHA5b696015cde310d3cb8d53b555ddac1589046c44515c6c9e6dad3fc83c446791:24 trường hợp (12 biến thể×2 mục tiêu), mỗi trường hợp9 origin và2 refit; predictions/actual/cutoff/fit logs khớp ở tolerance1e-8, chênh lệch dự báo lớn nhất0. SARIMA có extend/warm start, Prophet giữ coefficients giữa refit, LightGBM có fit lại pooled. Fixture tổng hợp, không huấn luyện lại raw. Windows ProcessPool spawn qua module canonical cũng khớp ts_job trực tiếp.
- 15 kiểm tra liên quan đạt (13 M2,2 core organization), thêm ca họ mới đăng ký đọc variants riêng và ca cấu hình không hợp lệ bị từ chối trước fit. Hai CLI help/compileall/git diff check đạt. Bằng chứng local ở M2/artifacts/model_split_checked.json;583 tệp trước move vẫn cùng hash/samefile, raw nguyên. Không sửa manifest lịch sử.
- Verifier CLI mới tạo m2_three_models_20261006_modular, status verified:221.280 dòng/2.040 nhóm metric,0 candidate lỗi; raw/selection/future actual nguyên. Manifest SHA2449341dd0c66574045965297a067ec7d10032688b21cd72626e3c40a48a3c5b; bảng tuyến SHA b759d7a960bd7c14ffcf265bb087a47fb02cad50c08b69089cae5428d8093c16 giống bản trước. Báo cáo/biểu đồ mới lấy danh sách họ từ manifest; report cũ nguyên. README/notebook trỏ tới báo cáo mới.
- TASK/PLAN/PROJECTMAP/code-map cập nhật vị trí và bằng chứng. CI/full suite không chạy lại; kết quả hồi cứu, R05/R07/T14 và sản phẩm hiện hành không thay đổi. Không upload/push hoặc refit dữ liệu thật.
- Kiểm cuối: link trong6 hướng dẫn hiện hành đạt; notebook v4 validate/3 code cell chạy đạt,9 hàng summary và20 lựa chọn, không lưu output. Biểu đồ báo cáo mới đã xem trực tiếp, nhãn/số liệu không bị cắt. Hash bằng chứng parity vẫn khớp41 module hiện hành; Git ignore artifact/report riêng tư và diff check đạt.

### CHG-033 / E61 — Cải tiến ba họ trước deadline M2, 06/10/2026

- Nguồn: người dùng chốt ưu tiên tổng7, sau đó yêu cầu triển khai toàn bộ kế hoạch. Đăng ký trước fit12 biến thể cũ+14 mới,50 cấu hình mục tiêu; giữ split/quantity/top10/H14/refit7/selection và tối đa3 worker. Các biến thể năm/cửa sổ/budget/units/targets nằm trong config từng họ; hai hiệu chỉnh chỉ direct_7d,history56/prior4/bounds0.5..1.5.
- Mã hỗ trợ override theo biến thể, normalize/inverse và metric từng tháng; verifier đối chiếu teacher/head/application và nguồn quantity độc lập. Snapshot đúng hash của implementation trước sửa được lưu local; run cũ nguyên. 40 kiểm tra liên quan đạt; chạy mới còn đang thực hiện, chưa nhận kết quả đạt hoặc đổi sản phẩm/nghiệm thu.

- Lượt m2_improved_models_20261006 đã fit đủ500 ứng viên tuyến/mục tiêu,475 artifact seal,2 candidate SARIMA lỗi được loại. Verifier phát hiện bug actual metadata của hai calibration: biến end dùng khi audit ghi đè split end. Không nhận run này verified; giữ nguyên manifest SHA dbd730a321a2b280a36b69aa6239434aacc29f29495d9fffdc4404ef0f903ca0 và ghi marker invalid_actual_metadata bên ngoài run. Dự báo số học và12 biến thể đối chứng không đổi (176.640 dòng validation,max delta0).
- Đã đổi biến audit thành label_end, thêm regression nhãn toàn bộ9 origin qua2 refit và cả hai horizon. 40 tests đạt. Run mới m2_improved_models_20261006_fixed dùng validation forecast cache đã seal: source/config/daily audit cùng giá trị, estimator sources phải giống hash hoặc đúng ba thay đổi tên biến sửa metadata; AST các hàm forecast/metric/selection không đổi. Actual được dựng lại từ audit raw mới cho mọi candidate; tính lại metric/lựa chọn/khóa trước test fresh, không tái sử dụng test hoặc lựa chọn của lượt lỗi. Source snapshots và lineage giữ nguyên.

- Kết quả cuối E61: `m2_improved_models_20261006_fixed` complete với155 artifact seal; manifest SHA `6407c68e9f520da51924fb021a275a947ada9cca15fbde06f35287218f3561dc`, overall selection SHA `98eb1ea7fa468f082424e429702dd8f6e85126b665540d17759ae5b19d32b48f`. 356.960 dòng validation cache khớp dự báo lượt đầu, actual kiểm lại từ raw/split đúng; lineage12 input forecast/log và source equivalence trong manifest. Test/future fit mới sau khóa.
- Verifier `m2_improved_models_20261006_fixed_review` verified: 401,600 dòng/9,160 nhóm metric; 2 SARIMA candidate lỗi (TrueMove H/arima_101 ngày và TrueMove H/sarimax năm540 tổng7) bị loại. Raw/labels/cutoff/teacher/head/factor/application/top10/selection/baseline/monthly/metric đối soát đạt; forecast test/future của mọi lựa chọn đầy đủ và future actual trống.
- Test từng họ LightGBM/SARIMA/Prophet: ngày46,743066/54,634202/55,471704%, đều0/10; direct7 16,111771/17,124072/16,508667%, đạt8/7/8 tuyến. Tổng cộng dự báo ngày 32,284798/20,665894/16,880778%, đạt1/5/9. SARIMA validation cải thiện nhưng test kém hơn, không chọn lại theo test.
- Overall khóa bằng validation: tổng7 LightGBM9 tuyến và Prophet au(KDDI), 15.887577%,9/10; LG U+20,688009% còn thiếu. Ngày LightGBM10 tuyến,46.743066%,0/10. Validation tháng7/8/9 của mix tổng7 14,959282/14,163125/18,698053%,9/9/7 tuyến; ngày39,113593/37,426834/53,804349%,0 tuyến. Chẩn đoán tháng không thay luật lựa chọn.
- Báo cáo bàn giao riêng có bảng trước/sau, tuyến, tháng và ưu/nhược ngày–tổng7; báo cáo verifier và CSV nằm ở M2/reports, notebook đọc fixed run. Phần phần mềm/đánh giá/báo cáo hoàn tất sớm ngày06/10; deadline17/10 giữ nguyên. 40 kiểm tra liên quan đạt; CI/full suite và demo máy thứ hai chưa chạy lại. Test hồi cứu, R05/R07/T14 chưa đóng; không thay sản phẩm V13 hoặc Word/slide, không push/upload.
- Kiểm cuối trực tiếp: notebook v4 validate và3 code cell chạy từ M2/notebooks đạt (9 hàng summary/20 lựa chọn/720 metric tháng, không lưu output); biểu đồ mới đã xem, số và nhãn đầy đủ. 7 hướng dẫn/43 link local kiểm đạt. Run reference309/cache475/fixed155 artifact và5 report files nguyên seal;583 tệp lịch sử cùng hash/samefile, raw nguyên. Implementation/config hiện hành khớp manifest fixed; compileall/diff check đạt, outputs private vẫn Git ignored. Receipt M2/artifacts/improved_handoff_checked.json.


### CHG-034 / E62 — Clean root và nhánh báo cáo M2 ngày07/10, 06/10/2026

- Nguồn: người dùng yêu cầu clean file root, chuyển đầu vào train vào data, tạo nhánh M2 về dữ liệu/mô hình tuyến/phương pháp/kết quả để báo cáo ngày mai. Chốt9/10 tổng7, giữ một tuyến chưa đạt để tối ưu sau. Nhánh local codex/m2-report-20261007 được tạo từ checkout hiện hành, giữ các thay đổi M2 đã làm; chưa push/upload.
- Chuyển39 tệp:24 JSON config (12 root+12 configs),5 launcher,6 Python entry point,3 Markdown planning và1 TXT archive. Root33→6 tệp điều hướng/môi trường. Data/configs JSON giữ nguyên byte; config_path hỗ trợ các tên cũ trong sealed bundle. Daily CLI src/pipeline.py và dashboard sigma/ui/daily.py; checker vào sigma/verification, wrappers trong legacy. Source snapshots86 module đúng SHA trước sửa; nguồn/3 run seal giữ nguyên.
- M2/presentation.py đóng gói index.html, CSV mô hình ngày/tổng7, metric tháng và checkpoint từ m2_improved_models_20261006_fixed, không train. Data/training/m2_report_20261007 có daily/top10/audit và3 bảng split top10; raw vẫn data/sigma_sim_data_orders.csv nguyên. M2/report_app.py có3 tab và scripts/start_m2.ps1 cổng8505; guide7–10 phút có bảng10 tuyến. Cả hai giữ LG U+20,688009% chưa đạt, hoãn tối ưu; mix15,887577%,9/10, ngày0/10.
- Verifier sau relocation m2_improved_models_20261006_m2_branch_review verified401.600 dòng/9.160 nhóm metric,2 lỗi candidate SARIMA đã loại; raw/selection/future actual nguyên. Manifest SHA6407c68e9f520da51924fb021a275a947ada9cca15fbde06f35287218f3561dc. Không chạy lại validation/test fit của nguồn thật hoặc đổi pipeline sản phẩm.
- Full suite262 tests đạt sau sửa resolver nhận root rõ ràng để giữ custom bundle/job namespace trong fixture. Thêm2 tests synthetic cho path compatibility và checkpoint9/10 không được đổi tuyến chưa đạt/giảm coverage. AppTest M2:3 tab,10 tuyến,9/10 tổng và0/10 ngày, metric9/10–15,89%–100%, không exception. Trang trình duyệt được xem trực tiếp; tiêu đề/chỉ số/trạng thái/bảng hiển thị đúng.
- Cấu hình sản phẩm V13 mặc định có parent sigma_weekly_boost_v13 chưa có artifact trên máy này, nên smokecheck real product bị chặn trước UI; không sửa bundle để che lỗi hoặc nhận đã kiểm6 trang V13 thật. Kiểm tương thích bằng bộ synthetic riêng; M2 đúng raw và run thật vẫn kiểm độc lập như trên. CI remote chưa chạy; mốc báo cáo07/10 không tự đổi deadline17/10/nghiệm thu R05/R07/T14.
- Kiểm cuối E62: sửa st.Page sang path tuyệt đối vì main script đã chuyển vào sigma/ui; check-product synthetic kiểm đủ6 trang/4 kịch bản và bộ lọc SKU–type đạt. 14 tests liên quan được chạy lại sau sửa, đạt. Demo synthetic full đã audit/forecast/policy/stock/delivery/comparison/freeze/verify, không đọc raw bài; check-data canonical kiểm train-only quantity/feature đạt. Receipt cleanup_checked.json:39 move,24 config byte nguyên,86 snapshot đúng SHA,3 run seal và583 file lịch sử nguyên,3 split quantity bằng nguồn,11 guide/99 link local đạt,2 notebook validate/3 cell M2 chạy đạt. PowerShell launcher M2 đã chạy thật, trang8505 và HTML8506 được xem trực tiếp; không push/upload.


### CHG-035 / E63 — Xuất bản nhánh và báo cáo M2 theo yêu cầu, 06/10/2026

- Người dùng yêu cầu tạo nhánh trên GitHub và đẩy M2 report. Đây là quyền xuất bản báo cáo tổng hợp; tiếp tục giữ raw, dữ liệu train và artifact dự báo local. Không dùng quyền này để thay production, merge PR hoặc đổi kết quả.
- Bộ published_m2_20261007 gồm báo cáo Markdown/HTML, biểu đồ, CSV metric/lựa chọn/tháng và evidence.json. Sao chép từ checkpoint đã khóa, kiểm seal trước khi xuất; không sửa bản local đã khóa, không fit lại. Git ignore chỉ mở allowlist các tệp tổng hợp được chọn.
- Kết quả9/10,15,887577%; LG U+20,688009% giữ chưa đạt/hoãn tối ưu; ngày0/10, test hồi cứu. Cập nhật README/guide và TASK/PLAN/PROJECTMAP để đọc báo cáo từ clone mà không cần raw. Kiểm tệp/hash/link và remote head riêng cho lần xuất bản; không nhận CI remote đạt trước khi xác minh.
- Kiểm trước push đạt:13 tệp báo cáo,41 liên kết, hash từng tệp/biểu đồ nhúng khớp,10 tuyến đủ độ phủ và đúng một tuyến LG U+ chưa đạt. Các CSV chỉ metric/lựa chọn tổng hợp, không có bản ghi order/customer hoặc forecast từng origin; raw/train/artifact và script xuất bản được Git ignore. Không chạy lại mô hình cho lần xuất bản tài liệu.
- Đã push nhánh mới lên origin GitHub thành công; `git ls-remote --heads` xác nhận commit báo cáo `88ddbbae66e61fdee409a7b11f91b459bf212db1` khớp HEAD local. [Nhánh M2](https://github.com/khanhnguyenpham/Sigma/tree/codex/m2-report-20261007) và [báo cáo đọc trực tiếp](https://github.com/khanhnguyenpham/Sigma/blob/codex/m2-report-20261007/M2/reports/published_m2_20261007/README.md). Cập nhật nhật ký xuất bản sau commit báo cáo; CI của nhánh mới chưa được xác minh.


### CHG-036 / E64 — Tên nhánh và email người dùng, 06/10/2026

- Người dùng yêu cầu bỏ tiền tố codex, dùng tên m2-forecast và email chaoskid1415@gmail.com. Chọn m2-forecast-report; đặt user.email/user.name trong Git config local của repo, không đổi global.
- Tạo nhánh mới từ bộ M2, sửa author/committer của riêng ba commit M2 trên nhánh mới; git diff với nhánh cũ xác nhận nội dung toàn cây giữ nguyên trước khi cập nhật tên trong hướng dẫn. Ba commit lịch sử nguồn bài trước M2 giữ nguyên danh tính. Nhánh cũ local vẫn giữ làm đối chiếu.
- Cập nhật README gốc/M2, presentation-guide, README báo cáo và evidence.json; chỉ đổi tên nhánh và hash README, các CSV/biểu đồ/HTML và run seal không đổi. Không fit lại hoặc thêm dữ liệu riêng tư.
- [Nhánh báo cáo](https://github.com/khanhnguyenpham/Sigma/tree/m2-forecast-report), [báo cáo M2](https://github.com/khanhnguyenpham/Sigma/blob/m2-forecast-report/M2/reports/published_m2_20261007/README.md). Push nhánh mới và xác nhận remote head trước khi bỏ tên nhánh GitHub cũ. CI mới chưa xác minh.

### CHG-037 / E65 — Tái hiện M2 từ CSV được đưa lại, 09/10/2026

- Người dùng yêu cầu tái hiện toàn bộ M2 và cho phép lấy mã nhánh trong ảnh. Đã fetch hai nhánh; `origin/codex/sigma-local-pipeline` tại `219088df0d741b6f76e969aceb28c1bb7a0c3e17` là tổ tiên của HEAD `36b300c8eaff7f590655bff2f97587df7d4b015a`. Không cần merge; không push/upload hoặc đổi lịch sử Git.
- CSV local 17.226.621 byte có SHA-256 `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`, khớp nguồn E61. Đã kiểm12 hash trong evidence báo cáo published; lưu hash toàn bộ báo cáo published và ba Word hiện có trước chạy để kiểm bảo toàn sau.
- Đăng ký run mới `m2_reproduce_20261009`, fit mới toàn bộ26 biến thể/50 cấu hình, không cache validation. `data/configs/m2-reproduce.json` giữ mọi tham số estimator/selection, chỉ bỏ tham chiếu run v1 chưa có tại máy và thêm ghi chú nguồn. So sánh riêng với báo cáo published, không giả phục hồi run lịch sử. T07–T09/T12 đang kiểm lại; chưa có kết quả mới, R05/R07/T14 giữ mở.
- Kiểm đầu trong sandbox:66/76 đạt,10 ca Prophet lỗi WinError623 khi Windows chặn binary Stan. Đã xác minh fixture Prophet ngoài sandbox thành công, dừng đúng các tiến trình thử do lượt này tạo, đánh dấu run đầu `interrupted` và không dùng làm cache. Chạy native mới `m2_reproduce_20261009_full`, mọi tham số estimator/selection giữ nguyên. Bộ76 kiểm tra dữ liệu/mô hình/leakage/metric đạt; sau bổ sung mở run mới có3 kiểm tra presentation đạt (hai ca đã thuộc bộ76, một ca mới).
- Run full hoàn tất475 artifact, raw SHA nguyên; manifest SHA `744241997537e441a7b55fb59bb75d75320c47f9c78652348f23615c93a5d411`. Verifier độc lập `m2_reproduce_20261009_full_review` đạt401.600 dòng/9.160 nhóm metric,2 candidate SARIMA không hội tụ, khóa lựa chọn nguyên và future actual trống.20 lựa chọn chung,90 kết quả họ×tuyến×mục tiêu và9 trung bình họ/mục tiêu khớp published; chênh MAPE test lớn nhất0. Validation có chênh làm tròn tối đa1,42e-14; không dùng kết quả để chỉnh selection.
- Kết quả mới: trực tiếp tổng7 đạt9/10, MAPE trung bình15,887576512782127%; LG U+20,6880086148% chưa đạt. Ngày0/10,46,74306601784154%; coverage100% cho lựa chọn. Test hồi cứu; R05/R07/T14 giữ mở. Không đổi requirements hoặc mô phỏng M3/sản phẩm V13. Python3.12.14 local khác3.14.7 ghi ở lock lịch sử; toàn bộ thư viện đúng requirements.txt, pip check đạt.
- Dẫn xuất mới:731×46=33.626 dòng ngày; top10 train5.470/validation920/test920, quantity40.549/8.637/7.765. Xuất đầu vào lần fit đầu30/06/2025 cho50 cấu hình,561.200 dòng bảng học và300 cặp hiệu chỉnh; kiểm hash, quantity nguồn, nhãn SARIMA/Prophet, trọng số LightGBM, cutoff teacher/head và không có order/customer ID đạt. JSON chỉ ghi tham số áp dụng cho từng họ, tách mô hình cha và đầu hiệu chỉnh. Các lần refit tiếp theo được truy bằng mã và fit logs, không gọi bảng đầu kỳ là mọi lần học.
- Bổ sung `RunId` cho launcher/dashboard, đọc run mới đã seal và verified; kiểm checkpoint lịch sử mặc định vẫn giữ chặt. Notebook trỏ run mới hoặc SIGMA_M2_RUN_ID, giữ không output. [Báo cáo local và đối chiếu](../M2/reports/m2_reproduce_20261009_full_review/README.md). Bảo toàn13 tệp published và ba Word theo hash trước/sau; không push/upload. Chỉ tái chạy protocol M2 hiện tại có đủ12 biến thể cũ trong pool26, không giả phục hồi nguyên byte các run lịch sử v1/V13/M3.
- AppTest native đạt3 tab/3 metric, cả hai chế độ ngày/tổng7 có10 tuyến và khớp CSV,0 exception; notebook thực chạy3 cell, giữ file không output. AppTest trong sandbox bị kẹt, đã dừng đúng tiến trình do lượt này tạo trước khi chạy native. Dashboard chạy nền ẩn tại127.0.0.1:8505; health/trang chính được kiểm riêng. Không cài job định kỳ hoặc đổi sản phẩm V13.

### CHG-038 / E66 — Thử nghiệm lịch lễ trên nhánh mới, 11/10/2026

- Nguồn: người dùng duyệt kế hoạch triển khai đầy đủ; tạo `codex/m2-calendar-forecast` từ `m2-forecast-report`, giữ các thay đổi chưa commit/tệp local. Quyền chỉ local, không push/upload. T04/T08–T09/T12 mở nghiên cứu tổng7 LG U+; target A08 success theo ngày đặt UTC, train/top10/split/H14/R05 ngày giữ nguyên.
- Mã mới `M2/models/calendar_reference.py`, `calendar_experiment.py`, tests và `data/configs/m2-calendar.json`; hai hook tùy chọn trong LightGBM/weekly, không đổi đường chạy mặc định. Đăng ký trước fit năm nhóm lịch × trực tiếp/hiệu chỉnh,10 ứng viên; tham số/seed/refit/ratio/calibration gốc giữ nguyên. Catalog lọc sự kiện có ngày công bố≤origin của từng mẫu/teacher rồi tính lại cờ/khoảng cách; ngày bổ sung thiếu nguồn công bố bị loại khỏi model, không có feature chỉ ra ngày chưa biết.
- Audit100.000 dòng/93.104 success/118.296 quantity/46 tuyến, không duplicate/dedup;33.626 dòng ngày bảo toàn. Raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. Lịch local2.980 dòng,01/01/2024–14/01/2026,4 điểm đến, đệm14 ngày trong catalog; SHA `58f947e922ab257433ccc6a782deb4596b66f8a2412e93ff3913a31f7628f611`. Nguồn chính thức/ngày truy cập/công bố trong config/catalog; luật lặp lại và cửa sổ mùa có nhãn giả định, không nhận đã xác minh mọi ngày lịch sử.
- Train EDA1.768 đỉnh ngày/cửa sổ7, LG U+118/40; cùng ngưỡng z4/tăng50%, tổng7 so tám tuần trước không chồng. Có đối chiếu cùng thứ, ngày lễ không tăng và đỉnh ngoài lịch. Trùng thời điểm không chứng minh nhân quả; bảng quantity/đỉnh không dùng làm feature. Run phân tích `m2_calendar_analysis_20261011` và run chính có đầu ra riêng, không sửa run cũ.
- Run `m2_calendar_20261011` complete,20 artifact seal; manifest SHA `42450c2efdbaf08851ad1fe228b95efa0a725520352d4b5b79fce3acd4a3ebf2`. LG U+ validation MAPE h1–7 đối chứng raw/hiệu chỉnh11,636178/11,632703%; VN11,754667/11,754667%; điểm đến12,122517/12,109701%; cả hai11,911011/11,911011%; cả hai+mùa12,123005/12,123005%. Coverage100% cả hai block. MAE lễ VN tốt hơn nhưng MAPE kém hơn, không đổi tiêu chí để chọn. Không nhóm lịch thắng validation nên giữ lựa chọn cũ, không chấm test mới. Mốc test hồi cứu20,688009%,9/10 còn nguyên; mục tiêu<20% chưa đạt, không nhận lịch có lợi ích.
- Kiểm trong run:18.400 nhãn/dự báo,400 nhóm metric,1.400 cặp hiệu chỉnh;3.680 cặp đối chứng lệch tối đa1,4210854715202004e-14<1e-8. Raw và498 tệp protected nguyên hash, gồm475 artifact run đối chứng và báo cáo/dashboard/notebook/launcher/Word hiện có. Receipt `M2/artifacts/m2_calendar_20261011_review.json` kiểm độc lập seal/implementation/config/catalog/raw, lưới lịch/top10 train/quantity,400 nhóm metric bằng phép tính trực tiếp, lựa chọn nguyên và không có lượt test mới.
- 35 tests liên quan đạt (8 mới,27 sẵn có); hai ca dashboard lỗi quyền thư mục temp ban đầu chạy lại với basetemp trong workspace và đạt. `pip check` đạt. Full suite/fixture SARIMA–Prophet/CI remote không chạy lại. Audit sandbox/native đều hoàn tất; không có lỗi audit bị che. Các kiểm lịch năm nhuận/âm lịch/nghỉ bù/chồng lễ/giao năm/biên và thông tin công bố muộn/future mutation có ca thực chạy.
- [Hướng dẫn và bàn giao](calendar-experiment.md) có CSV, nguồn, lệnh, bảng so sánh và giới hạn. TASK/PLAN/PROJECTMAP đồng bộ; requirements không đổi. Dashboard/bộ báo cáo khóa giữ nguyên, R05/R07/T14 vẫn mở. Nếu nghiên cứu tiếp cần giả thuyết mới đăng ký từ train/validation, không chỉnh chọn bằng test đã xem.

### CHG-039 / E67 — Nghiên cứu tiếp riêng LG U+, 11/10/2026

- Người dùng yêu cầu bắt đầu thử nghiệm để LG U+ đạt<20%, giữ nguyên các tuyến đã đạt. Làm local trên codex/m2-calendar-forecast, bảo toàn thay đổi/tệp có sẵn; không commit/push/upload. Target A08 success theo ngày đặt UTC/top10 train/split/H14/R05 ngày và dashboard/báo cáo khóa giữ nguyên.
- Đăng ký từng lượt trước fit:35 cấu hình bám nhu cầu/scale28–56/feature order/pooled Hàn Quốc/riêng LG/residual/blend;44 cấu hình tổng quốc gia×tỷ trọng quá khứ và blend với lựa chọn lượt1;24 cấu hình tinh chỉnh quanh scale56 vì thắng validation lượt1. Các con số gồm đối chứng lặp lại, không là số mô hình độc nhất. Hai cửa sổ lịch sử10/2024 và04/2025 chỉ chẩn đoán, population xếp theo lượng bán trước origin đầu kỳ. Validation chính chọn MAPE block1,MAE,ID và khóa trước test; không chọn theo test. Đây là nghiên cứu tuần tự trên test đã xem nhiều lần, không là holdout độc lập.
- Mã mới focus_experiment.py/hierarchy_experiment.py/refinement_experiment.py và config tương ứng. Tái dùng estimator/feature/metric/calibration hiện có, không sửa core mặc định ở lượt này hoặc thêm dependency. Feature/scale/share dùng lịch sử tại origin, teacher/head chỉ nhận nhãn hoàn tất; country teacher target là tổng quốc gia còn actual/metric sau phân bổ là LG U+. Residual dùng weighted ridge co về0 và clip±25% scale; blend có trọng số cố định. Run đầu audit lại100.000 order,118.296 quantity/46 tuyến; hai run sau tái dùng daily đã seal, kiểm lại hash raw và ghi lineage, không nhận đã audit mới.
- m2_focus_20261011 complete25 artifact; chọn focus_scale56_mul56p4, validation11,632703→10,775820%. Test h1–7 hồi cứu20,688009→20,520981%, giảm0,167028 điểm phần trăm nhưng chưa<20%, vẫn9/10. MAE11,436603→11,493482, WAPE20,926550→21,030626; h8–14 MAPE18,992036→20,156147 và cadence7 ngày h1–7 còn20,667111%. Không nhận cải thiện đồng đều hoặc nghiệm thu. Manifest SHA7723ed69133f0d2a695acdacfdef065fab7d331b2a58e6196c241dce3f5e8204.
- m2_hierarchy_20261011 complete16 artifact và m2_refinement_20261011 complete15 artifact: không ứng viên nào thắng validation10,775820%, không chấm thêm test. Giữ toàn bộ kết quả/khóa riêng; không lấy một ứng viên khác trong pool bằng kết quả test. Manifest SHA lần lượtbcffdd029836589129764296d3d4cec6b6d4c8f4f1df725a0b516b47e4d23415 và3859c9023cb4bd87e857ede47b93e076c38e44f90c3d91364b26b7787a98661c. Đã dừng sau lượt tinh chỉnh hữu hạn theo protocol.
- 42 tests liên quan đạt (7 mới và35 hồi quy;20 fixture SARIMA/Prophet deselect), pip check đạt. Kiểm mới bao gồm causal mutation quantity/order, parity real estimator, residual/clipping/actual tamper, country pool, phân bổ nhãn/future, blend align và freeze CSV. Full suite/CI remote không chạy lại. Hai đối chứng focus và scale56 tái hiện chênh forecast0.
- Run đối soát18.952 nhãn/dự báo validation,412 nhóm metric validation và40 nhóm metric test; teacher/head/application/actual/cutoff đều đạt. Ba receipt độc lập _review.json kiểm seal/implementation/config/raw, tính trực tiếp412 metric validation,42 nhóm country/share/blend và điều kiện tối ưu residual/cutoff. Chín tuyến cũ có1.656 forecast test và metric khớp chính xác; lựa chọn mô hình nguyên. Metadata số validation trong selection dẫn xuất lượt1 có sai khác round-trip≤3,55e-15, không đổi forecast/model hoặc file nguồn. Lượt2/3 selection chín tuyến khớp chính xác cả metadata.
- Raw SHA6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b nguyên; lượt cuối kiểm562 tệp protected nguyên hash, gồm run cũ/lịch/những lượt nghiên cứu trước, published/dashboard/notebook/launcher/Word. [Báo cáo và CSV](focus-experiment.md) ghi đủ kết quả chưa đạt và giới hạn. TASK/PLAN/PROJECTMAP/M2 README đồng bộ; requirements không đổi. Mục tiêu<20% chưa đạt, R05 ngày/R07/T14 giữ mở; không đổi sản phẩm hoặc tự công bố kết quả.

### CHG-040 / E68 — Năm giả thuyết tiếp theo cho LG U+, 11/10/2026

- Người dùng cho phép bắt đầu các hướng tiếp theo đã đề xuất: residual trên cấu hình56 thắng validation, age weights, refit nhanh, count×basket và feature cơ cấu đơn lớn/độ phân tán. Làm local trên `codex/m2-calendar-forecast`, giữ toàn bộ thay đổi có sẵn. Target A08 success/ngày đặt UTC, top10 train, ba split/H14 và nghiệm thu R05 ngày giữ nguyên. Chín tuyến/dashboard/báo cáo khóa không đổi; không commit/push/upload hoặc thêm dependency.
- Đăng ký21 cấu hình trước fit bằng `data/configs/m2-adaptive.json`, module riêng `adaptive_experiment.py`:7 bản raw/nhân/cộng/affine trên scale56;6 bản half-life28/56/112;4 refit1/3 ngày;4 kết hợp half-life56/refit1/3. Trọng số inverse-normalized-target nhân giảm mũ theo tuổi ngày cuối nhãn, tổng weight giữ bằng đối chứng. Teacher/head chỉ học nhãn hoàn tất. Hai fold lịch sử chỉ chẩn đoán; chọn validation MAPE h1–7,MAE,ID và đủ coverage, thắng10,77582022385683% mới khóa/chấm một test hồi cứu.
- `m2_adaptive_20261011` complete15 artifact; tốt nhất vẫn đối chứng56/nhân56p4 validation10,77582022385683%, không chấm test mới. Residual mới tốt nhất11,527652%; age weights11,708249%; refit3 raw10,816207%; age56/refit3 raw13,321580%. Đối chứng lệch0; receipt kiểm252 metric của hai fold/validation,733 weighted fits,1.192 head, actual/cutoff/cadence và chín selection chính xác.591 tệp protected/raw hash/quantity/top10 nguyên. Manifest SHA `a2f1e3528149743f43839aa7ed0b3719e2a6b0903beb0184d4e6353751388686`;25 tests liên quan và pip check đạt.
- Đăng ký26 cấu hình cơ cấu đơn trước fit bằng `data/configs/m2-composition.json`, module riêng `composition_experiment.py`:8 bản quantity feature/control × raw/nhân56p4;18 bản count scale28/56/90 × raw/nhân56p4 × basket trailing28/56/90. Đơn lớn quantity≥3 khóa trước; feature chỉ rolling quá khứ về tỷ trọng lớn và CV quantity/đơn. Audit raw lại, block nếu không một dòng/order; daily moment không xuất order/customer ID. Count teacher/head dùng nhãn count, đầu ra/metric cuối dùng quantity thật.
- Run đầu `m2_composition_20261011` bị guard chặn actual điền vượt cuối validation sau phân bổ count×basket, trước selection/test. Giữ19 artifact seal `failed`/`invalidated`, không dùng làm kết quả/cache. Sửa metadata để giữ actual trống khi count window chưa hoàn tất split; thêm regression test với snapshot chứa order sau validation. Không đổi26 candidate/feature/params/selection; config chỉ thêm provenance sửa lỗi. Run `m2_composition_20261011_fixed` complete38 artifact; toàn bộ7.696 forecast hai fold và validation trước/sau sửa khớp chính xác0, hash run lỗi nguyên. Bốn tests cơ cấu đơn đã đạt, tổng29 tests liên quan lượt này.
- Lựa chọn khóa từ validation `composition_both56_mul56p4` đạt10,616717142432643% so với10,77582022385683% trước; giữ LightGBM150 cây/7 lá/train365/refit7/seed42/scale56/đầu56p4, thêm bảy feature đơn lớn và CV. Một test hồi cứu20,446740131508527% so với20,52098066284474% trước và20,688008614795773% ban đầu; vẫn chưa<20%,9/10. MAE11,482204/WAPE21,009990% kém đối chứng ban đầu, bias-5,921379; h8–14 MAPE20,292426% kém cả hai mốc. Cadence7 ngày h1–7/h8–14 còn20,526069%/22,056650%, coverage100%. Không thay ứng viên bằng kết quả test hoặc nhận cải thiện đồng đều.
- Manifest SHA lượt26 `03aebcc02c444f25762958a616915e0e73b2f50f776b08eaff725b72371b8079`. Receipt độc lập đối soát33.626 dòng daily moment từ raw,21 giá trị feature tính trực tiếp từ order,352 metric hai fold/validation/test,54 nhóm count×basket,336 head về actual/cutoff/tối ưu factor/application. Khóa selection trước giờ test được đối chiếu; chín selection/1.656 forecast/mọi metric nguyên chính xác, future hai dòng actual trống. Tổng hai lượt604 nhóm metric/733 weighted fits/1.528 head kiểm độc lập. Raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b` và630 tệp protected nguyên.29 tests (8 mới,21 hồi quy) và pip check đạt, không chạy full suite/CI remote/SARIMA/Prophet mới.
- [Protocol/kết quả lượt21](adaptive-experiment.md), [báo cáo/CSV/receipt lượt26](composition-experiment.md). Test đã xem nhiều lần vẫn hồi cứu, không là holdout độc lập. Hai lượt hữu hạn gồm47 cấu hình đã hoàn tất, mục tiêu<20% chưa đạt; R05 ngày/R07/T14 còn mở. T04/T08–T09/T12 đồng bộ TASK/PLAN/PROJECTMAP/M2 README, requirements không đổi; dashboard/bộ báo cáo khóa và mọi thay đổi có sẵn giữ nguyên. Chưa commit/push/upload; nghiên cứu tiếp cần giả thuyết mới dựa trên train/validation, không quét ứng viên bằng test đã xem.

### CHG-041 / E69 — Chấm toàn bộ cấu hình trên test theo yêu cầu mới, 11/10/2026

- Người dùng yêu cầu “test toàn bộ chứ không cần validate dưới val thấp nhất”. Phạm vi mới cho phép chấm toàn bộ ứng viên đã đăng ký, không đòi thắng validation; chỉ áp dụng bảng nghiên cứu hồi cứu riêng. Các điều kiện không chấm thêm test trong E66–E68 giữ đúng theo lịch sử lượt đó, được thay trong phạm vi so sánh mới này. Không sửa tiêu chí R05 ngày, A08 success UTC thực nghiệm, top10 train, ba split/H14 hoặc lựa chọn validation/sản phẩm đã khóa.
- Module mới `M2/models/retrospective_sweep.py`, config `data/configs/m2-test-sweep.json`, hai tests mới. Catalog160 lượt từ sáu bảng validation đã seal (10/35/44/24/21/26), đối chiếu config/hash trước fit, không lọc bằng validation. Tái dùng nguyên phase/params/seed/refit cũ, ba worker local. Daily/moment từ run audited đã seal, kiểm lại raw SHA/quantity/count/train top10, không nhận audit raw mới. Lịch vẫn biết theo origin, teacher/label hoàn tất trước cutoff. Không thêm dependency hoặc gọi SARIMA/Prophet mới.
- Run `m2_test_sweep_20261011` tính xong đủ160 lượt và xuất metric từng nhóm, nhưng dừng ở bước đọc baseline vì sai tên `test_predictions.csv` thay `focus_test_predictions.csv`. Giữ35 artifact và seal failed. Sửa đường dẫn, thêm preflight tệp baseline và `--reuse-phases`; tạo `m2_test_sweep_20261011_fixed`, complete43 artifact. Config/catalog/params không đổi; toàn bộ29.440 dòng forecast/actual/metadata khớp chính xác từ run đầu, không refit hoặc thử tham số mới. Protocol/execution run đầu khóa catalog trước fit; timestamp run sửa là phần đối soát/tổng hợp dự báo có sẵn.
- Có17/160 lượt MAPE test h1–7<20%, coverage100%;160 lượt gồm đối chứng/đầu lặp,100 bộ dự báo hai block khác nhau ở1e-8,10 bộ có h1–7<20%, không gọi17 kết quả độc lập. Tốt nhất theo MAPE/MAE/pool/ID là `refinement/tune56_w540_mul56p4`, test19,26589984972207%, validation11,336558417751442%. Scale56/train540/annual pooled top10, LightGBM150 cây/7 lá/min-child100/lr0,03/lambda10/seed42/refit7/đầu56p4, không thêm lễ/cơ cấu đơn. Bản raw đồng hạng h1–7, h8–14 khác nhẹ. Mốc validation này không thắng10,775820% của E67 nên trước đây bị gate; nay tìm được qua xếp hạng test, không là đánh giá độc lập.
- Bản tốt nhất h1–7 MAE10,529504/WAPE19,266752%/bias-3,749518,86 cặp; nonoverlap18,429381%,13 cặp. H8–14 MAPE20,255792%,79 cặp; nonoverlap20,990611%,12 cặp, coverage100% tất cả. H8–14 vẫn kém mốc ban đầu18,992036%. Phân tầng hồi cứu h1–7:16 cửa sổ có lễ10,180162%,70 cửa sổ thường21,342640%, không là feature/tiêu chí chọn hoặc suy nhân quả. Các nhóm lịch/count×basket/age/hierarchy không có bản<20%; bảng160 giữ toàn bộ kết quả.
- Receipt độc lập đọc lại29.440 cặp/640 nhóm metric/mẫu số, điểm validation toàn bộ160 lượt khớp nguồn,2.116 head/349 weighted fits/60 nhóm country/share/blend/count×basket. Ba đối chứng184 cặp mỗi bản lệch0. Chín selection/1.656 forecast test/mọi metric, raw và757 tệp protected nguyên hash; không tạo selection mới, không sửa dashboard/published/notebook/launcher/Word.25 tests liên quan (2 mới,23 hồi quy) và pip check đạt; một test cũ lỗi thư mục temp sandbox đã chạy riêng với basetemp trong project và đạt. Không chạy full suite/CI remote.
- Manifest SHA `8b6167a5ace0b163fa0c0249e2d091e344be51e5d4a09a5f35cd121545fba0a0`; receipt SHA `fae92b2b5b6090ea3ff82d6eddc5bfdf8d797c80988404e2381d0c6a4fe2740f`; raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. [Bảng CSV/protocol/kết quả/giới hạn](test-sweep-experiment.md), run/receipt local. T08–T09/T12 và TASK/PLAN/PROJECTMAP/M2 README đồng bộ; requirements không đổi. Đã tìm được ứng viên đạt mục tiêu số học tổng7 test<20%, nhưng đã chọn bằng test hồi cứu; lựa chọn validation E68 vẫn20,446740%, R05 ngày/R07/T14 mở. Giữ toàn bộ thay đổi có sẵn, không commit/push/upload hoặc tích hợp sản phẩm.


### CHG-042 / E70 — Bộ final M2, chạy lại và chuẩn bị GitHub, 11/10/2026

- Người dùng yêu cầu nhánh mới `M2-final-report`, tổng hợp10 mô hình theo tuyến, dọn bộ báo cáo, thêm file cấu hình, chạy lại để kiểm <20% và push GitHub. Tạo nhánh từ `codex/m2-calendar-forecast`, giữ mọi thay đổi có sẵn. Quyền push là chỉ dẫn trực tiếp mới, thay giới hạn không push của E66–E69 trong phạm vi mã/config/báo cáo tổng hợp này; không gửi raw hoặc artifact chi tiết. Chín tuyến giữ lựa chọn validation gốc; LG U+ dùng ứng viên thắng test E69 theo mục tiêu người dùng. Không chọn lại chín tuyến hoặc đổi target/top10/split/H14/R05.
- `data/configs/m2-final.json` khóa10 lựa chọn trước fit. Runner `M2/final_report.py` tái dùng phase LightGBM/Prophet/hiệu chỉnh hiện có, fit mới validation/test/future, không tìm thêm ứng viên.9 cấu hình LightGBM,1 Prophet; nhiều tuyến dùng chung biến thể. LG U+ scale56/học540/annual pooled/150cây/7lá/min-child100/lr0,03/lambda10/seed42/refit7/đầu56p4. Chín tuyến còn lại giữ params cũ. Không dùng feature lễ/cơ cấu đơn trong final; Prophet au(KDDI) riêng tuyến, học540, additive/Fourier3/weekly/cp-prior0,01.
- Run `m2_final_20261011` bị kẹt tại thư viện NamedTemporaryFile do quyền TEMP trong sandbox, dừng và seal failed trước khi có bảng dự báo hoàn chỉnh. Run `m2_final_20261011_tempfix` dùng TEMP trong workspace nhưng CmdStan bị WinError623 khi tạo tiến trình; có log Prophet failed/NaN và bị guard chặn, seal failed. Kiểm Prophet trên dữ liệu giả ngoài sandbox đạt; chạy `m2_final_20261011_local` với cùng config/params/seed và TEMP workspace ngoài sandbox, không sửa mô hình để vượt lỗi. Hai run lỗi giữ nguyên để truy vết.
- Run final complete26 artifact, audit mới100.000 dòng/118.296 quantity/46 tuyến; raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b` nguyên. Verifier audit raw lần hai, đối soát top10 train, selection trước execution, nhãn và biên split, cutoff,3.700 dự báo,80 nhóm metric,58 đầu hiệu chỉnh;771 tệp raw/run lịch sử/published nguyên hash. Chín tuyến có1.656 cặp validation và1.656 cặp test khớp forecast/actual cũ chính xác, maxdiff0; LG U+184 cặp mỗi split khớp nguồn E67/E69 maxdiff0.
- Tổng D+1…D+7 test **10/10<20%, mean15,745365636274759%, coverage100%**,86 cặp đủ nhãn mỗi tuyến. LG U+19,26589984972207%, MAE10,529504 quantity, WAPE19,266752%, bias-3,749518 quantity; so mốc20,688009% giảm1,422109 điểm phần trăm. H8–14 còn20,255792%, nonoverlap h1–7/h8–14 là18,429381%/20,990611%. H8–14 không đạt toàn bộ. Test đã tham gia chọn LG U+, nên rerun là kiểm tái lập hồi cứu, chưa có holdout độc lập; MAPE tổng7 không thay R05 theo ngày/R07/T14.
- Full suite thu292 ca; lần chạy đầy đủ đạt291, một AppTest final skip vì báo cáo chưa xuất lúc thu/chạy. Sau xuất, chạy riêng4 ca final đều đạt, gồm chính ca AppTest đã skip và đổi cadence/horizon; mọi292 ca đã có lần chạy đạt. Pip check đạt, notebook final2 code cells chạy đạt/không lưu output, chart xem trực tiếp, Markdown links hiện hành/code fence/AST/privacy/schema và12 hash public-report đạt. CI remote chưa xác minh ở thời điểm ghi đoạn này. Không dùng số tests thay accuracy.
- Báo cáo `M2/reports/final_m2_20261011` gồm12 tệp aggregate: README/HTML/chart, lựa chọn, metric test/validation/tháng, trước/sau, cấu hình JSON/Markdown, receipt/manifest. `M2/final_app.py` đọc aggregates đã kiểm hash; launcher mặc định mở final, `-RunId` mở lịch sử. `M2/HISTORY.md` giữ nguyên nội dung M2 README cũ; root README đưa hướng dẫn cũ vào phần lịch sử. `.gitignore` chỉ allowlist12 tệp final, bỏ scratch/cache/draft Word/PDF khỏi gói; `.gitattributes` giữ byte report để hash không đổi giữa checkout Windows/Linux. Raw/daily/per-origin/private drafts ở local, không xóa bằng chứng lịch sử; inventory/M3 không đổi.
- Run manifest SHA `7be713a8389d487bb4d9f7aa70df45896c98d933549d722bd0136052a18e0976`; receipt SHA `f36dd0e7908e6c72c9923c32c737a7e340f38b1de7f5e9b3bd4395d51fad58a7`; public manifest SHA `85f09bff60e7351d74d9555d4117be6ea5152ae53167318c744e75922d8d925d`. [Kết quả](../M2/reports/final_m2_20261011/README.md), [cấu hình10 tuyến](../M2/reports/final_m2_20261011/model_configurations.md), [receipt](../M2/reports/final_m2_20261011/verification_summary.json). TASK/PLAN/PROJECTMAP/T08–T09/T11–T13 đồng bộ; requirements không đổi vì không đổi nghiệm thu. Bước tiếp: push bộ được phép theo ủy quyền người dùng, kiểm remote SHA/CI, rồi dùng final để chuẩn bị báo cáo/bảo vệ; chưa nhận nghiệm thu toàn bài hoặc bảo đảm dự báo dữ liệu mới.

- Dọn14 thư mục cache/fixture tạm sau khi kiểm đường dẫn tuyệt đối trong workspace; không xóa raw/run/published/draft. Lần kiểm quyền đầu timeout, retry được chấp thuận và hoàn tất.

- Xác nhận xuất bản E70: commit mã `0cbeaf05e7bd44d740c3ab784047a557706d78f4` đã push nhánh `M2-final-report`, remote SHA khớp, working tree sạch; không tạo PR hoặc gửi raw/artifact riêng tư. [CI Windows của đúng commit mã](https://github.com/khanhnguyenpham/Sigma/actions/runs/38136737500) completed/success, mọi step đạt: khóa phụ thuộc/pip check, full pytest, synthetic audit/pipeline/demo và các trang dashboard. Commit tiếp theo chỉ ghi bằng chứng này vào tài liệu, không đổi source/config/run/report. Bước tiếp: dùng bộ final và file cấu hình để chuẩn bị trình bày, giữ giới hạn hồi cứu/h8–14/R05/R07/T14.


### CHG-043 / E71 — Chuẩn bị học và bảo vệ M2 trong 4 giờ, 14/10/2026

**Yêu cầu trực tiếp:** người dùng cần hiểu chi tiết M2 để báo cáo thứ Sáu16/10/2026, gồm model từng tuyến, dữ liệu/giai đoạn học và cách kể các thử nghiệm không đạt. Phạm vi T13: tài liệu học và luyện trình bày; không thay deadline17/10 trong PLAN hoặc nghiệm thu.

**Sản phẩm:** hoàn thiện [tài liệu học](../M2/reports/mentor_prep_20261014/README.md) có lịch240 phút, từ điển, bảng model/metric10 tuyến, ví dụ cutoff/refit và một ca dtac thực, giải thích LightGBM/Prophet/SARIMA, lịch sử thử nghiệm, kịch bản8–10 phút và20 câu phản biện; thêm [ôn tập10 phút](../M2/reports/mentor_prep_20261014/ON_TAP_10_PHUT.md), [25 dòng cửa sổ học](../M2/reports/mentor_prep_20261014/training_windows.csv), [receipt](../M2/reports/mentor_prep_20261014/evidence.json). Bản nháp có sẵn thiếu bảng final và các tệp bằng chứng đã được hoàn thiện. Sửa diễn giải weighted L1 của ratio: với mẫu dương, scale triệt tiêu trong lỗi tương đối; điều này không bảo đảm metric ngoài mẫu.

**Kiểm trực tiếp:** Python qua stdin bằng `.venv/Scripts/python.exe -B -`, không fit model. Hash raw khớp nguồn final;26 artifact trong manifest run và11 tệp trong report manifest hợp lệ. Tự tổng hợp nguồn100.000 dòng/93.104 success/118.296 quantity, không ID trùng; đối chiếu33.626 dòng daily và top10 train. Tự tính40 nhóm metric từ1.840 forecast test, đối chiếu nhãn tổng7 với daily; sai khác metric tối đa0 với CSV đọc round-trip. Dùng hàm prepare/target_history thật nhưng không fit để kiểm25 dòng cửa sổ tại5 cutoff, đối chiếu35 dòng fitlog. Kiểm59 liên kết nội bộ,16 bảng và các fence của hai tài liệu học. Raw/run/báo cáo final giữ nguyên; không xuất giá trị định danh.

**Kết quả giữ nguyên:** h1–7 có10/10 dưới20%, mean15,745366%, coverage100%; h8–14 có8/10, China Mobile21,634373% và LG U+20,255792%. LG U+ chọn bằng test-sweep; cả test vẫn hồi cứu. Kiểm head LG U+ trên test block1 đều hệ số1, không gán toàn bộ cải thiện cho head. Run manifest SHA `7be713a8389d487bb4d9f7aa70df45896c98d933549d722bd0136052a18e0976`; receipt phiên học SHA `8cb41924bdb823c2f01ed3311e2944282b308dc1654e1151c255accfad3c3cfe`.

**Giới hạn/bước tiếp:** không chạy full suite, dashboard, refit hoặc CI trong phiên này; không suy kiểm hash thành tái huấn luyện. R05 ngày/R07/T14 mở; snapshot không tái dựng trạng thái tại origin thật. T13 bổ sung tài liệu chuẩn bị, chưa xác nhận người học đã hiểu hoặc đã bảo vệ; TASK/PLAN được đồng bộ, requirements không đổi. Tiếp theo học theo240 phút và tự nói kịch bản/trả lời phản biện. Các tài liệu học giữ local, không push/upload; bộ final và báo cáo cũ không sửa.


### CHG-044 / E72 — Chuyển tài liệu học M2 sang Word ngày 14/10/2026

Theo yêu cầu người dùng, tạo [một file Word](../M2/reports/mentor_prep_20261014/SIGMA_M2_Tai_lieu_hoc_va_bao_cao.docx) 20 trang từ README học4giờ và ON_TAP_10_PHUT, giữ số liệu final và giới hạn hồi cứu. Có mục lục cập nhật,14 bảng, số trang và phụ lục ôn tập; bảng narrative chuyển thành đoạn văn, sơ đồ giữ bằng luồng chữ. Dùng python-docx của bundled runtime; render_docx.py lỗi thiếu soffice, thay bằng Word COM chạy ẩn export PDF và bundled pdf2image/Poppler tạo PNG. Đã xem20 trang, sửa ngắt bảng/khối mã và số thứ tự danh sách; lần cuối chỉ trang15 đổi, kiểm lại trang15. Xác minh20 trang không rỗng, các số liệu chính hiện diện. SHA256 DOCX `c698bdd0464f5b9d801a15f928eba33284d93de29bee96165bb88de6169be156`; receipt QA local `tmp/mentor_word_qa/verification.json`. Không refit model hoặc thay raw/run/report final; TASK/PLAN T13 đồng bộ, R05/R07/T14 còn mở. Tệp dẫn nguồn trong Word liên kết tới workspace local; bước tiếp là học và ôn tập theo lộ trình.


### CHG-045 / E73 — Dọn toàn bộ codebase cho bộ M2 final, 14/10/2026

**Yêu cầu trực tiếp:** tạo nhánh backup/checkpoint và nhánh cleanup; chỉ giữ code cần cho bộ final để báo cáo16/10, có thể lấy lại code cũ, commit local, không merge/push/deploy. Phạm vi T09/T11–T13, không đổi tiêu chí hoặc nghiệm thu.

**Bảo toàn:** nhánh gốc `M2-final-report` tại `b1415289614a9793c6ff4a6ee1e350fc0a49014c`; bốn tài liệu đang sửa đã kiểm diff và commit checkpoint `5271d0b9d0411506f1a22ada9c2fe337be00ec84` trên `backup/m2-before-cleanup`. `cleanup/m2-final` bắt đầu từ checkpoint. Bản sao riêng bền vững tại `C:/Users/Admin/OneDrive/Desktop/WorksSpace/SIGMA-m2-backup-20261014`:466 tệp local/ignored trong ZIP đã test CRC, ZIP byte tracked, patch tài liệu, inventory/hash trước dọn. Môi trường ảo/cache/secrets không đưa vào commit. Không reset/clean/sửa lịch sử hoặc nhánh gốc; không khôi phục nguồn đã thiếu trước lượt này.

**Truy vết và sản phẩm:** đối chiếu config final, report/manifest/selected và code thật:10 lựa chọn,7 cấu hình, LightGBM9 tuyến pooled top10, Prophet au(KDDI), LG U+ `tune56_w540_mul56p4` test-selected. Tách feature/fit pooled và đầu nhân cần thiết ra `M2/models/weekly.py`, `focus.py`, `calibration.py`; giữ audit/daily/top/metric ở src, CLI final, dashboard, notebook final và tests liên quan. Bỏ code M1/M3/V13, SARIMA implementation, biến thể không chọn, sweep/calendar/recent/composition/residual/blend, aliases, notebook/entrypoint/tests cũ và39 công cụ tmp đã sao lưu.193→28 tệp code tracked `.py/.ps1/.ipynb`;205 tệp tracked bị xóa, tổng244 nếu tính tmp. Không chuyển code bị loại vào archive trong codebase. Bỏ5 dependency không còn nằm trong closure sử dụng (statsmodels/patsy/formulaic/interface_meta/wrapt), giữ83 phiên bản cũ theo metadata local; không uninstall môi trường.

[Bản đồ code tiếng Việt](../M2_CODE_MAP.md) có bảng10 tuyến→config→hàm, feature/nhãn/cửa sổ/refit/metric, tham số/bằng chứng và lệnh khôi phục. README/M2/model guides, launcher8505, CI và tài liệu bị ảnh hưởng đã cập nhật; nội dung nghiên cứu cũ được giữ, link implementation bị xóa được dẫn đến cách lấy backup trong tài liệu có thể sửa. Báo cáo khóa/Word/PDF giữ byte; link/lệnh code trong các báo cáo khóa là lịch sử, cần backup. `--stage verify-artifacts` kiểm evidence lịch sử mà không nhận source hiện tại giống source cũ hoặc sửa receipt; `verify` cho run mới vẫn bắt buộc khớp source/config. Export cho phép report-id mới và từ chối ghi đè.

**Kiểm trực tiếp:** Python3.12.14 local, `python -B -m pytest -s --basetemp=.cache/m2-final-suite`:**32 passed in26.16s**. Có300 forecast giả,10 tuyến,7 cấu hình, ba refit; parity trước/sau tối đa0. Fixture chạy cả Prophet/CmdStan native và pooled LightGBM150 cây; không lấy dữ liệu riêng tư làm fixture. Tests thêm kiểm future mutation,7.300 nhãn pooled tại cutoff, tổng7/annual calendar, Prophet540, zero/missing, head/prior/clip, manifest/path, export và AppTest3tab/cadence/block. Notebook hai code cell dùng load_report được kiểm riêng, không lưu output. Bảng tham số hiệu lực và tất cả key/spec còn giữ đối chiếu backup không đổi; import15module nội bộ, parse26Python files, PowerShell launcher và `pip check` đạt. `git diff --check` đạt.

`python -B -m M2.final_report --run-id m2_final_20261011_local --stage verify-artifacts` đạt:3.700 forecast (1.840validation+1.840test+20future),80metric,58heads; mỗi split chín tuyến1.656forecast và LG U+184forecast khớp parent với chênh0. Raw100.000 dòng/118.296quantity/top10 được audit lại, không in ID. Hash960tệp raw/data/artifact/report/Word/PDF nguyên; run manifest vẫn `7be713a8389d487bb4d9f7aa70df45896c98d933549d722bd0136052a18e0976`. Kiểm link/anchor/bảng/fence tài liệu sửa không có lỗi mới; các link đã thiếu trước lượt này (ảnh/PDF nguồn, handoff cải tiến cũ và đường configs cũ) vẫn phân biệt là lịch sử, không tạo tệp thay thế.

**Giới hạn:** chưa chạy full training raw, sweep, CI hoặc cài môi trường mới; CI vẫn cấu hình Python3.14, chưa kiểm lại trong lượt này. Prophet báo thiếu Plotly tùy chọn, AppTest cảnh báo bare context nhưng tests không lỗi. Một lượt fixture trong sandbox bị dừng do CmdStan; baseline và suite thành công dùng native local. So sánh JSON tham số lần đầu vấp suy kiểu None→NaN khi đọc; đã so lại bằng kiểu JSON gốc/spec và đạt. Test export phát hiện thiếu thư mục cha và đã sửa rồi kiểm lại. Không coi kiểm artifact là tái fit hoặc nghiệm thu; source hash cũ khác mã đã dọn được nêu rõ, không sửa manifest cũ. Bộ final vốn lưu forecast/log/config, không có model serialize trong manifest; không bổ sung cơ chế save/load mới.

**Bàn giao/bước tiếp:** TASK/PLAN và tài liệu code được đồng bộ, giữ nguyên số liệu h1–7 10/10 hồi cứu, h8–14 8/10 và R05 ngày/R07/T14 mở. Commit cleanup sau kiểm; dùng M2_CODE_MAP để diễn tập tìm code. Cần full replay thì chủ động dùng run-id/report-id mới với raw/parent local; cần M1/M3/sweep cũ thì lấy nhánh backup đầy đủ. Không push/upload/deploy hoặc xóa backup.


### CHG-046 / E74 — Đặt tên và cho phép push nhánh M2 final, 14/10/2026

Người dùng yêu cầu trực tiếp “đặt tên rồi đẩy lên github”, thay giới hạn không push của CHG-045. Đặt tên `M2-final-cleanup` cho nhánh `cleanup/m2-final`; giữ nguyên commit dọn `7cea15823f18cb7c4ebbcd77f7450d428c9634a7`, nhánh gốc `M2-final-report` tại `b141528` và backup tại `5271d0b`. Remote `origin` là `https://github.com/khanhnguyenpham/Sigma.git`; đã kiểm nhánh đích chưa tồn tại và nhánh gốc remote khớp b141528 trước đổi tên.

Chỉ đồng bộ tên nhánh/lệnh Git trong README, M2/README, M2_CODE_MAP, TASK/PLAN và nhật ký; không đổi implementation, tham số, forecast, metric hoặc nghiệm thu. Kiểm diff/checks tài liệu và phạm vi các commit mới trước push: không có raw, artifact riêng tư, Word/PDF, môi trường hoặc bản sao riêng trong thay đổi gửi lên. Các tệp aggregate final đã có trên nhánh gốc không đổi. Bằng chứng32 tests/parity300forecast/hash960tệp thuộc commit dọn E73, không nhận đã chạy lại trong lượt đổi tên. Không merge, force-push, deploy hoặc xóa backup. Kết quả push và SHA remote được kiểm trực tiếp khi thực hiện, báo ở bàn giao lượt này.

<a id="e76"></a>
### CHG-048 / E76 — Đặc tả M3 theo góp ý mentor và yêu cầu chỉ Markdown, 19/10/2026

**Nguồn:** M04 là mentor do người dùng thuật lại trong phiên: ngưỡng theo supplier×product_type×sku linh hoạt, nhập kho7 ngày, một kho giả định/tuyến. S03 là phần ảnh M3 đính kèm đã xem: chính sách tồn, cảnh báo≥7, dashboard, đến 07/11. U09 là lựa chọn BE/FE riêng, MySQL hoặcPG (thiết kế chọnPG), 46 tuyến, mở rộngML36, cảROP/MOQ, ROPmax với floor, một supplier/item; cho tạo bộMD/commit/push nhánh không codex. Người dùng nhắc lại rõ chỉ MD, không code. Không nhận đã xem ảnh mentor M01–M03 thiếu hoặc hợp đồng/kho thật.

**Quyết định/phạm vi:** áp dụng profile `m3-design-v1`, FastAPI/React/PG, 13 bảng, sáu màn hình, worker riêng. Giữ final10, mở thiết kế6ML cho 36 chọn bằng validation; seed ngưỡng/city/supplier giả định có version. L7 mới thay A11L3 trong M3 mới; M03customerD+7 vẫn là lịch sử riêng. A08–A17 không được nâng xác nhận đồng loạt; R05/R07/T14 chưa đạt từ bộ tài liệu. Các kết quả tồn/UI cũ cần kiểm lại với profile mới.

**Git và bảo toàn:** tạo worktree riêng từ `261c631b9677fce72f1a716047d02c15f8232280`, nhánh `M3-design-plan`. Worktree gốc có 3 file tracked sửa và 1 file untracked, được giữ nguyên; không đưa CHG-047/E75 local chưa commit vào commit này, do đó dùng048/76 tránh trùng mã. Remote nhánh đích chưa tồn tại lúc kiểm bằng git ls-remote. Không sửa Git global/lịch sử/khôi phục code, không copy raw vào worktree mới.

**Đầu ra:** [M3/README](../M3/README.md)+6 đặc tả, đồng bộ requirements, data-contract, PLAN, TASK, PROJECTMAP, review-log và link root README. Toàn bộ thay đổi là `.md`; source/schema/API/CLI/tests đều là thiết kế tương lai. Không cài dependency/chạy migration/model/app/DB trong lượt này.

**Kiểm trực tiếp đầu lượt:**83 file được bảo vệ gồm CSV nguồn, 26 artifact final local và các code/config/report file tracked phù hợp; aggregateSHA256=`fe97ffa4e8cb1dd1337c0af9dbd6d7c2c95b911abb09a5157bae2463f036bbb4`. CSV SHA256=`6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. Đây là phạm vi83 file đã kiểm, không nhận đã kiểm lại960 file của E73.

**Kiểm cuối lượt đã chạy:** 14 Markdown trong phạm vi (7 mới + 7 nền); 51 link/anchor mới hợp lệ (26 trong M3 và 25 link liên quan ở tài liệu nền), 66 bảng đúng số cột, 19 khối mã đóng đủ trên 14 file; ERD đúng 13 bảng, API có 20 cặp method/path không trùng. Kiểm độc lập bằng Python standard library qua stdin: 16/16 ca công thức, ETA, balance, phân bổ, metric và replay windows khớp kỳ vọng; đây là kiểm đặc tả, không phải tests implementation. Kiểm đếm lại nguồn: 46 tuyến, 920 khóa item. Không tìm thấy giá trị order/customer ID nguồn trong corpus 14 tài liệu. 83 file được bảo vệ giữ nguyên aggregate SHA-256 ở trên; `git diff --check` đạt sau khi sửa khoảng trắng EOF. Bước stage/commit có cổng kiểm chỉ `.md`; kết quả commit và SHA remote được báo trong bàn giao lượt này.

**Giới hạn:** chưa chạy tests ứng dụng, full model, DB hoặc FE; chưa có run M3 để nghiệm thu. Kiểm link chỉ bao phủ link/anchor mới và liên quan M3, không nhận toàn bộ link lịch sử đến nguồn thiếu đã hợp lệ. **Bước tiếp:** sau bộ tài liệu, nhận việc code riêng rồi thực hiện T08–T12 theo M3/06; T13/T14 cần bằng chứng thực. Push chỉ xác nhận khi SHA remote khớp commit; không merge hoặc deploy.


### CHG-057 / E89 — Triển khai mốc nền M3 theo PLAN

**Quyền/phạm vi:** người dùng yêu cầu “bắt đầu triển khai theo PLAN” sau đọc bộ M3. Đây là quyền code/cài/kiểm local, thay phạm vi chỉMD của CHG048; không tự push/deploy/rawupload. Giữ mãT08–T12/R01/R04/R06/R08/R09; R05/R07/T14 mở. Thời điểm19/10/2026 Asia/Saigon. Nhánh `codex/m3-implementation` lấy nền20a3c45, worktree trong outputs/workspaces/m3-implementation để không đổi nhánh tổng30/ứng dụng đang chạy.

- **Thực có:** package sigma_m3/Python3.12.14; requirements kế thừa83pin root M2,15dependency bổ sung khóa (FastAPI0.146.0,SQLAlchemy2.0.55,Alembic1.20.0,psycopg3.3.6). PostgreSQL18.6 portable từ trang EDB chính thức, chỉ127.0.0.1:55432, roleapp không superuser, hai DBapp/test riêng, không cài service. Alembic0001_m3 sinhDDL13bảng thật, migration/checkdrift đạt. Env/DB/binaries private ignored.
- **Mã:** settings/db/models/schemas/errors/main, services runs/catalog/ingestion/seeding/inventory/alerts/allocation/receipts,worker/CLI và scripts. HTTP không fit/uploadraw; lỗi không echo input/raw/DBURL. Policy khóa item để xử lý đổi supplier/concurrentedit, runcomplete gate/idempotency perkey,worker advisorylock/restartinterrupted. Receipt primitive khóa lô, đúngETA và nhận một lần. Worker hiện chỉ source_import; không gọi kind chưa có thành complete. Không claimfullAPI/FE/job30s.
- **Kiểm:**35tests M3 đạt/0fail/error/skip, gồm caROPbằng/dưới/trên,MOQ,pending,cân bằng,ETA7,cạn0/6/7/14/H,confusion/null denominator,allocationmissing/futuremutation,DTO,PostgreSQL13bảng/NaNInf/actualnull,API202/200/409/422/404,parentgate/concurrency/receipt/singleworker. 32tests M2 hiện hành đạt/0skip trên môi trường3.12 mới; pipcheck và Alembiccheck không códrift. Warning TestClient dùnghttpx deprecated; không đổi các pin M2 để che warning.
- **Nguồn thật:** CLIimport-orders --wait tạo run96e77f53-fa7c-46be-987f-50e308920dba complete.100.000dòng/118.296quantity/46tuyến/920item/672.520dailyrows; sourceSHA6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b nguyên. Run/manifest ở outputs/m3/UUID private. Seed920policy tại30/09 bằng28ngày quá khứ,5scenario cơ sở/cover3/14/safety0,5/1,5. Verifier độc lập CSVstdlib +SQL tính lại920firstseen/floor/MOQ/safety vàquantity,hashmanifest đạt. Lặp source cùngrequestkey vẫn1run/daily; seedlần2 reused920. Không chép raw vào worktree.
- **Lỗi và sửa:** bootstrap PostgreSQL lần đầu bị giữ pipe sau pg_ctlstart; đã dừng đúng tiến trình riêng, giữ cluster cũ failed, tạo pgdata_v2 mới với outputpgctl vào logfile và runtime giữ sống. Không ảnh hưởng dịch vụ khác. Kiểm bổ sung đã chặn bigintoverflow,Decimalpolicy vàduplicate allocation history. Không sửa sealedrun đầu khi mã bổ sung sauđó; current_codehash có thể khác runhistorical và không được ghi lại thành giống.
- **HTTP thực:** uvicorn127.0.0.1:8000 healthok/database reachable; GETcatalog trả46kho/920item/46supplier/920policy; sourceGETcomplete. Không phải FE hoặc proof6screens. RuntimePG/API do lượt này tạo giữ riêng; credentials không ghi trong tài liệu, API hay Git. Tệp mã/config/report M2 nền và rootenvironment không sửa, khôngrefit hoặc dùng kết quả Streamlit cũ đểđóng profileL7.

**Bàn giao:** [README thực thi](../M3/README.md#implementation-e89) phân biệt phần đã có và đích chưa xây. Artifacts private: outputs/m3-foundation-verification.json,m3-foundation-tests.xml,m2-regression-tests.xml và runmanifest. TASK/PLAN/PROJECTMAP/requirements cùng6spec đã cập nhật trạng thái. Chưa adapterfinal10/ML36/allocation nguồn thật,fullpolicy/alertreplay,APIkết quả/export/snapshot,React/E2E hoặc periodic heartbeat. Idempotency giữa requestkey khác cùngsourcehash còn phải làm. Bước tiếp theo T08–T09 theo PLAN, giữ khóa10final và selection36 bằng validation; không bảo đảm MAPE/cảnhbáo khi chưa chạy.


<a id="e90"></a>
### CHG-058 / E90 — Forecast46, tồn L7 và ứng dụng M3 thực thi

**Quyền và phạm vi,19/10/2026:** người dùng yêu cầu “hãy hoàn thành tất cả rồi push lên github đi”. Quyền này thay phạm vi chỉlocal/chỉMD ở E76/E89 cho code/config/tests/docs M3 mới. Không đưa raw, run artifacts, DB, env/credentials hoặc source IDs lên GitHub; không tự merge/deploy/public dữ liệu. Checkout `outputs/workspaces/m3-implementation`, nhánh `codex/m3-implementation`, nền20a3c45. Source/requirements/model/report M2 giữ nguyên; không khôi phục M2/artifacts đã thiếu. Word/slide ngoài yêu cầu lượt này.

**Mã thực:** adapter M2 read-only tách pooledtop10 với pool46 cho new36; orchestration6ứng viên/validation/selection lock/test/future, phân bổ causal. Snapshot catalog/policy/version, giao dịch receipt đầu ngày rồi order_datetime/order_id (DB chỉ source_sequence), ledger ngày, ROP/MOQ/IP/ETA7, policy/alert replay riêng và stock projection. API result/metrics/export phân trang, context/hash/parent complete gates, hash-dedup source giữ identity request; full config/runtime/seed trong manifest run mới; worker một tiến trình/heartbeat30s/verify-before-complete/code mismatch gate. React6màn hình, URL/filter, abort response cũ, loading/empty/error/null, config version/scenariooverride/initialreceipts, chống submitlặp, CSV cùng context, focus trap/Escape và table keyboard. Cây source và lệnh tại [M3/IMPLEMENTATION](../M3/IMPLEMENTATION.md).

**Chạy thật đã kiểm:** nguồn96e77f53-fa7c-46be-987f-50e308920dba giữ100.000raw/118.296quantity/46routes/920items/672.520dailyrows. Forecastrun7f7c53cb-4603-4e0a-b945-f43a9b57a715:185origin/17.020route/2.382.800itemforecast. Verifier độc lập kiểm đầy đủ actual, conservation/weekday90/share30→90/firstseen,36 lựa chọn từ rankingvalidation,1.799dòng fitlog cutoff; selectionSHA `c4e8b3756126689f001fd6b15dcd3f63cf507600615b3e411e25734c0d88782c`.40nhóm metric final10 khớp report trong1e-8; không có bundle per-origin lịch sử nên không nhận parity từng dòng với run cũ.

**Kết quả trung thực:** weekly H1–7 fixed10 đạt10/10≤20%, mean15,745366%; H8–14 8/10,16,600553%. New36 H1–7 chỉ2/36,35,400179%; all46 12/46,31,127393%, coverage100%. Ngày phân bổ từ forecasttuần M3 top10 H1–7 là0/10,51,919555%; không nhầm với directdaily M2 cũ. Test hồi cứu/fixedLGU+ test-selected giữ nhãn. R05 ngày không được thay bằng tổngtuần.

Policy cơ sởrun d8d8cf3b-58cc-44eb-94f4-c79661131b3f:85.560ledger/16.423events/3.245orders;15.968sales/14.437fulfilled/1.531shortage,fill90,412074%. Verifier tính lại85.560threshold, từng eventbalance, orderQ/ETA/receipt; đạt. Alert cơ sởc20da6c2-2fa8-486f-a53f-3ab401682041:6window14ngày/82.800ledger/16.395events/0neworders/10.231alerts;TP2098/FP852/FN769/TN702,excluded1099,early986/2867=34,391350%,precision71,118644%,recall73,177537%,dateMAE4,287893ngày. Tám ngày cuối ngoài cửa sổ đủ14. Snapshot31/10 dbdbdd93-d325-4874-81f4-7382316daace và31/12 4b63935f-bc0c-4b3d-8dec-426a9751aaa3 kiểm920dòng/run; khôngfutureactualledger.

**Kiểm phần mềm:**78tests Python=46M3+32M2,0failed/error/skip;5Vitest/RTL đạt, npmci từlock141packages, TypeScript và productionbuild đạt; code split không còn chunk>500kB. Pipcheck/Alembiccheck đạt; RuffFcheck/format chỉM3, không đổi pinM2. Warning Starlette/httpx TestClient giữ công khai, không giả là lỗi nghiệp vụ hoặc nâng pinM2 để che. LiveAPI/CSV đối soát tạiwarehouse18/origin31/10:2route,14allocateddaily,20inventory,39alerts, đúngcontext/hash/count;92futureweeklyrows actualnull. Forbidden/rawexport404,unknownfilter422,kindmismatch409. Tests tạm ban đầu vướng quyền thư mục temp Windows, đã dùng basetemp trong outputs; một test bắt lỗi blockLiteral querystring, đã sửa coerceint1..2 và rerun đạt.

**UI trực tiếp:** mở ứng dụng production tại127.0.0.1:8000; kiểm sáu màn hình, chọnJapan/NTTDocomo, daily/weekly, giải thíchROP/IP/MOQ, projection và tạo scenarioe2e_receipt_policy từ form với override/lôD+7. Reload giữrun/kho/origin; desktop1366×768/tablet768×1024 không tràn body, bảng có scroll riêng. Ảnh private outputs/m3-overview-desktop.png. Không coi 5RTLtests là số ca E2E trình duyệt; hai mức bằng chứng phân biệt.

**Bảo toàn và giới hạn:** rawSHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b` kiểm lại nguyên; gitdiff đối với src/M2/data-configs/requirements nền không thay. Run đầu đãsealed không sửa manifest sau khi code cải tiến; verifier receipt nằm ngoài run. Phần mềm local chưa auth/cloud/multiuser, không là đặt hàng thật. A08–A17/M04 giữ thẩm quyền cũ; R05/R07/T14 vẫn mở. Không hứa điểm hoặc ngưỡng sai số/báo sớm cho mọi tuyến. CI GitHub chỉ xác nhận sau push/đọc status, không suy từ local.

**Bàn giao:** README/6spec/TASK/PLAN/PROJECTMAP/requirements đồng bộ với implementation; E76/E89 giữ lịch sử. Các lệnh CLI có placeholder SOURCE/FORECAST/SCENARIO/RUN phải thay bằng ID thật, không chạy nguyên ví dụ. Kiểm source/selection/ledger/alerts/HTTP/FE có artifacts trong outputs private. Theo dõi thêm độ nhạy và freshfuture/queue/UI run ở phần bổ sung bên dưới trước push; không tự sửa các run cũ thành code revision mới.

**Bổ sung E90 sau kiểm cuối:**10run cơ sở/cover3/cover14/safety0,5/safety1,5 ×policy/alert đềucomplete. Policy fill lần lượt90,412074/89,478958/90,568637/89,197144/91,501754%; thiếu1531/1680/1506/1725/1357. Alert early34,391350/25,954915/17,608286/34,391350/34,391350%; mẫu số cover3=3194,cover14=2124,base=2867, không coi là cùng denominator. Bảng và diễn giải tại IMPLEMENTATION. Các run đầu có receipt ngoài manifest;8run độ nhạy có verify-before-complete trong summary; hai run safety1,5 dùng verifier cuối thêm đối chiếu timestamp/source_sequence thật và event→daily.

Freshfuture d57975c8-3d14-40a2-bee6-b3b8e20575ad complete qua worker cuối:46routes/92weekly/12.880item/43fitlogs, giữselectionSHA, actual tương lai null. Sourcehash reuse6db3901f-b6f5-4ee9-a2e3-129d3407ba55 complete với request identity riêng; tổngdaily vẫn672.520, không duplicate. Manifest mới chứa fullconfig/runtime/seed; manifestrun cũ không sửa. Hai helper kiểm từng tranh workerlock ở khoảng trống giữa job; advisorylock chặn tiến trình thứhai, không chạy trùng; đã tiếp tục đúng các queuedUUID bằng một worker, không nângqueued thànhcomplete hoặc sửa lịch sử.

Kiểm Markdown14tệp/69linkM3/64bảng/fence khônglỗi. Audit82tệp thay đổi/đầu ra public dự kiến:0rawID/0token-privatekey pattern/0privatefile; rootworkingtree gốc sạch, src/M2/data-configs/requirements nền nguyên. Launcher start_m3.ps1 đã chạy API+worker ẩn và API reachable; đang kiểm lượt tạo từ React trước khi push. Không nhận một lần thử terminal bịlỗi/queued là chạy hoàn tất.

**E90 — E2E hoàn tất:** React scenarioe2e_receipt_policy v2 → run950e6844-d611-48cf-b0ef-4e845ba0811a queued/running/complete;920threshold/920events/1order/1714alerts verified. Receipt đặt28/10→ETA04/11 qty20; item341 closing7/ROP20/pending20/IP27/S21/MOQ10/Q0. CSV browserdownload đúng1row/filter/run/hash và giá trị này, receipt ở outputs/browser-e2e-receipt.json; ảnh outputs/m3-e2e-inventory.png. Bảnv1/run9973f09f-6f91-4125-9210-1857d38414df giữ lịch sử (receipt đã quaorigin, pending0), không sửa để làm đẹp. Trong kiểm UI phát hiện dateinput controlled chưa giữ ngày qua chuỗi thao tác; đã bổ sung input/change handling + functionalrowupdates, chờcatalog, test ngày/quantity, và xác minh date/ETA sau nhập/save/run/CSV. Thêm gate không render dữ liệu context cũ ngay trước effect và loại duplicate selectedrun trong poll. Kiểm cuốiFE7tests/TypeScript/build đạt; số5tests ban đầu là mốc trước sửaUI, không phải số cuối. Launcherstop/start đúngPID/creationtime/ownedchildren đã chạy, API/worker giữ hoạt động.

Kiểm bổ sung trực tiếp: Escape đóng dialog; UUID không tồn tại giữ thông báo lỗi, không tự chuyển sang run khác; quay lại URL950e6844 giữ bộ lọc. Các fullrun trước commit mang revision nền879365e và codeSHA riêng của source đang sửa; không dùng revision nền để nhận workingtree sạch hoặc sửa manifest thành commit sau này. Mã cuối giữ codeSHA được worker kiểm, Gitcommit/publication được đối soát riêng. Kiểmlink cuối14tệp/69linkM3/65bảng/fence đạt. FE cuối7tests, Python78tests; không tự nâng R05/R07/T14 theo số tests.

**Tiếp tục E90 lúc19:23 ngày19/10:** hạn mức5giờ đãused0/ordinaryUsageAllowed=true, tắt lịch một lần và tiếp tục theo quyền push đã có. Apphealth/database reachable; codeSHA hiện tại `5a20aa6bd2a64d415035fad403636c09ec58a66eee8c54a57ab6482ab176e3bc` khớp run E2E950e6844 đãcomplete. XML78tests=0failed/error/skip và log7FEtests được kiểm trực tiếp. Rà lại84tệp từ nhánh thiết kế:0privatefile/0sourceID/0token-keypattern;14Markdown/69linkM3/65bảng/fence đạt. Diffkhôngstage rỗng, src/M2/data-configs/requirements nền không thay; stage72tệp implementation/docs đã rà, không córaw/run/DB/env. Commit/push và trạng tháiCI sẽ được đối soát bằng SHAremote và workflow tương ứng, không suy từlocal.

**E90 — Push và kiểm CI lần đầu:** commit implementation `b144548fc39d9875d226860bd99061ee849a7c14` đã push và ls-remote xác nhận đúng SHA. Workflow Synthetic tests run39251965876 đạt (Windows/Python3.14); frontend job118057702844 đạt7tests/build. Workflow M3 run39251965975:46tests backend/PostgreSQL đạt; bước32tests M2 trên Linux có1lỗi parity,30/300giá trị Prophet sai khác tối đa7,87829352e-6 so với fixture Windows, lớn hơnatol1e-8. Không xem CI lần này là đạt toàn bộ; chưa kết luận nguyên nhân thư viện nhị phân từ log đơn lẻ. Điều chỉnh workflow giữ strict golden trên Windows/Python3.12 với đầy đủ lock M3, giữ46tests PostgreSQL trên Linux và frontend; không đổi fixture/tolerance/model/test M2, không nhận parity Linux ở1e-8. Healthcheck PostgreSQL thêm đúng user/database để tránh log role root không tồn tại. Kết quả CI của commit kế tiếp phải đọc trực tiếp sau push, độc lập với kết quả local.

<a id="e91"></a>
### CHG-059 / E91 — Tiếp tục hoàn thiện và kiểm giới hạn dự báo/cảnh báo

Ngày19/10/2026 Asia/Saigon, người dùng yêu cầu tiếp tục và hỏi đã hoàn thiện chưa; tiếp tục phạm vi hoàn thiện/push code/docs từ CHG058. Nhánh codex/m3-implementation nền03786ab, root tổng30 giữ nguyên; không merge/deploy/Word/slide/rawupload. Commit03786ab trước lượt này đã có hai workflow CI success; đây là bằng chứng cũ, không thay CI cho thay đổi mới.

**R07/T10–T12:** bổ sung opportunity_breakdown đọc event timing sau replay và GET alert-opportunities, panel React trong Cảnh báo. Không đổi forecast/actual/stock formula/metric, không sửa run cha. Cơ sở5520cases, tương lai2867, excluded1099;1550ca cạnD+1…6 không thể có7ngày từ origin.1317ca đủ thời gian,986đã phát hiện/331bỏ sót; trần tại các origin này45,936519%, thực34,391350%. Không coi đó là trần mọi hệ thống hoặc thay mẫu số R07. API từ chối filter/kind/status/summary lệch; unknown/empty giữ lỗi/null. Đối soát độc lập case dates với API đạt. Trình duyệt đã đọc đúng số, chọnJapan/NTTDocomo vẫn mẫu số toàn lượt2867/bảng40dòng; ảnh private outputs/m3-alert-opportunities.png.

**R05/T08–T09 nghiên cứu riêng:** protocol daily-validation-v1 ghi trước fit,8phương pháp gồm6baseline/2LightGBM; ranktop10train, query≤30/09/2025, fullcalendar, targetUTC/A08, horizon14, rolling365/refit7, maxlabel≤cutoff. Không đổi final10/ML36/weekday allocation hoặc dùng test chọn. Bản đầu7811fb30 hoàn tất28fits/95.760forecast; bản560a112e bổ sung runtime/input/requirements hashes/clippinglog, predictions/metrics/selection giống byte. Cả hai giữ local, không ghi lại manifest cũ.160nhóm metric và10winner được tính độc lập từ CSV,28cutoff/hashes đạt; manifestSHA37ea061307c31c0befd9becaaca1d53609a24ddcd9b2d984a35e6dcd6c88da83. SelectionSHA0608d7dcda479cfea1e051f610edbfa833130db0ed43635b28c2bade72057180. Validation H1–7 mean49,451918%,0/10; allocated cùng623cặp/tuyến51,905954%, thấp hơn7/10 nhưng vẫn thiếu20%. Chưa chấm test/thay model phục vụ hoặc dùng vào tồn; không nhận dữ liệu không thể dự báo từ8phương pháp.

**Kiểm thực:**86Python=54M3+32M2/0fail/skip;9FE/4files/TypeScript/build đạt. Rerun2test research sau bổ sung metadata đạt; không thay phép tính fit, output giống byte. XML outputs/e91-tests.xml; helper .tools/e91_verify.py lúc đầu thiếu project import path, sửa helper và chạy lại đạt, không sửa sourceM2. Snapshot mới quaAPI+worker309cc381-70cf-4e6a-9c1e-5b1220c49950 complete verified920threshold/920events/1lot/1714alerts, codeSHA1acba62a5213d419b67e4fca56ddaa1f0052bd4c2cbc86bd899c6a3d293e4f0f; dùng forecast cha nguyên. Launcher stop/start đúngownPID, PG giữ. Run cũ không cập nhật codeSHA hoặc summary.

**Trạng thái:** TASK/PLAN/PROJECTMAP/requirements và API/FE/source/test docs/hướng dẫn đồng bộ. R05/R07/T14 không nâng nghiệm thu; không có xác nhận mentor thay tiêu chí. Raw/DB/env/run/CSVforecast/ảnh private local. Chỉ source/tests/docs nghiên cứu mới và chẩn đoán được chuẩn bị push. Rà privacy/link/diff và CI sau commit được ghi trong receipt/bàn giao; không suy CI từ local. Bước tiếp theo nghiên cứu chưa kiểm test và331ca còn cơ hội, cần protocol/evidence trước đổi profile phục vụ.

<a id="e92"></a>
### CHG-060 / E92 — Tiếp tục tối ưu ngày và phân biệt đúng cổng nghiệm thu

Ngày20/10/2026 Asia/Saigon, người dùng yêu cầu chạy để đạt mọi tiêu chí. Tiếp tục T08–T12 trong quyền hoàn thiện/push source/docs; không đổi target/split/top10/metric, không merge/deploy/Word/slide. Nhánh codex/m3-implementation nềncd57235; đầu lượt đọc TASK/PROJECTMAP/requirements và phần PLAN liên quan. CI của cd57235 đã kiểm trực tiếp: Synthetic tests39285952472 success và M3 synthetic integration39285952382 success, không còn dùng trạng thái queued E91.

**Nghiên cứu R05:** daily_panel.py và evaluate_frame chung, protocol v2 trước fit; feature counts/units-per-order/annual/weekday/market/country causal. Top10 train khớp final; chỉ query≤30/09/2025.3candidates/168fits/35.910forecast/60metricgroups; lựa chọn validation H1–7 mean45,971604%,0/10≤20%,9/10tuyến thấp hơn v1 mean49,451918%. Không mở test/chọn bằng test/thay app/đưa vào ledger. Run5f80050a giữ local, selectionSHA95e5a80b8b9ba5a2731c29f63d25c9a09d4fafde98f382119e2350bb3baf8b96 và manifestSHA18be7e6a58d33f1bb987f1a20cc3400d52a9b66a06a5120c22a8a413a594c23a. Verifier độc lập kiểm60metricgroups/10winner/168cutoff/fit scope/paircounts/hashes đạt. V1-6aea9e7c sau refactor tái lập95.760predictions/metric/selection giống byte E91.

**Bảo toàn phiên bản:** trong lúc research fit đã thêm input guard vào evaluator (chặn target feature/test labels/âm/thiếu/horizon lệch). Không nhận source mới là source đã fit; source bản trước guard tái dựng receipt ngoài run, SHA khớp chính xác hash đã ghi trước fit. Không sửa manifest hoặc kết quả run cũ. Guard mới được test và dữ liệu đã fit qua kiểm ranh tương ứng; thuật toán fit không đổi. Receipt outputs/e92-source-archive và e92-research-verification.json private.

**R07:** phân tích331FN đủ7ngày:331tồn≤2,311tồn1;331forecast14<tồn,0forecast0,0receiptsinitial; median expected14/stock0,580714. Đây là diễn giải sau replay, không feature hoặc rule tune bằng test. R07 có yêu cầu đo/ca chuẩn/mẫu số nhưng chưa có ngưỡng precision/recall/earlyrate tổng chính thức; không tự thêm100%. Giữ trạng thái chưa nghiệm thu, không coi34,3913% tự đạt hoặc tự fail ngưỡng không tồn tại. M3/ACCEPTANCE phân biệt phần mềm/correctness, kết quảR05 và mentor nghiệm thu; M1/M2 lịch sử chưa tự nâng.

**Kiểm và bàn giao:**89Python=57M3+32M2,0fail/error/skip; tests mới gồm cross-route futuremutation/annualmissing/calendar/count guards và chống target/test leakage. FE/app/DB không đổi;9FE/build là E91, không nhận đã rerun không cần thiết. Raw hash/source/M2/config/requirements giữ, run thật local. TASK/PLAN/PROJECTMAP/requirements/README/IMPLEMENTATION/ACCEPTANCE đồng bộ; R05/R07/T14 mở. Không kết luận mọi mô hình đều bất khả đạt20% chỉ từ nghiên cứu này; không hứa ép metric. Cần nghiên cứu nhu cầu thưa/uncertainty, protocol và evidence trước đổi profile. Commit/push/CI mới phải kiểm riêng trước báo đạt.


## CHG-061 / E93 — R05 tổng 30 và tích hợp M3, 20/10/2026

M05 thay tiêu chí ngày theo xác nhận mentor được người dùng thuật lại. Không chỉnh raw, target/top10/split, prediction hoặc sealed run. T08–T12 nối kết quả tổng30 thật sang read model riêng của M3; không thay DB13bảng, M2 final, forecast H14 hay policy/alert đã khóa.

Verifier gốc chạy lại thành công lúc 2026-10-19T18:43:57.970403+00:00, receipt private `sigma_aggregate_focus_20261018_e93_20261020_verification.json`. SummarySHA `a8e90ec29ea154c34ac9d54fcf0a224767fe37a2435ab1ba0d57453359878c38`; sourceSHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`; selectionSHA `f7cac3993d32e2d8c40e8fb28a8479ada7a059f9b126c6e0222865e02902e465`. Kiểm 1.048 fit cutoff, 92 lựa chọn khóa trước test, train top10, 8.556 nhóm allocation.

CLI prepare-monthly đối soát 33.626 route-day PostgreSQL với run nguồn, kiểm 8.510 tổng30/cutoff/actual, tính lại metric khớp1e-9, baseline cùng mẫu. Gói private `42dd7812e3b92ebddf781e9eaa0b0e2458e8f4dc764abce3db1c3888573940c0`: 184 dòng metric, 10/10 đạt≤20%, mean11,621356%, 63 cửa sổ/tuyến, coverage100%. Naive0/10/37,871734%; MA7 5/10/18,287797%; MA28 7/10/17,403218%.

Các flag lịch sử `daily_R05_acceptance_replaced=false` trong sealed summary/receipt giữ nguyên; acceptance overlay M05 riêng. Đây là tái dùng kết quả fit thật đã kiểm lại, không nhận vừa fit mới. Tất cả test hồi cứu vì hướng focus đã chọn sau khi xem test cũ. T14 cần mentor rà target A08, mô phỏng/R07 và giới hạn holdout. Xem [kết quả/API/cách chạy](../M3/MONTHLY.md).

Kiểm E93 local: 97 Python (65 M3 +32 M2), 0 fail/error/skip; 11 FE, TypeScript/build, Ruff và pip check đạt. Kiểm API thật 10 metric/63 cửa sổ, 46-route filter, nonoverlapping3, actual tương lai null, CSV context và snapshot cùng source. Trình duyệt đã hiển thị 10/10/11,62%/100%; đổi top10/46 và origin31/12, actual01–30/01 null. 17 Markdown/112 link M3/69 bảng không lỗi. Lần chạy tests đầu lỗi quyền thư mục temp cũ; chuyển basetemp riêng trong project. Một test fixture sửa số giá trị unpack trước lượt toàn bộ đạt; không sửa metric vì lỗi này. CI commit mới phải xem riêng, không suy từ CI E92.


## CHG-062 / E94 — đưa M3 lên Streamlit công khai, 20/10/2026

Người dùng yêu cầu “hãy đưa lên streamlit công khai đi”. Kế thừa quyền dùng repo riêng tư và công khai aggregate đã cho trước đó; không thêm OAuth hoặc đổi repo public. T11/T12 thêm source `M3/streamlit`, builder local, runtime allowlist và UI7màn hình. Không triển khai PostgreSQL/FastAPI/worker/raw lên Community Cloud; bản Streamlit đọc dữ liệu đã kiểm và mô phỏng riêng phiên.

Gói24tệp/6.620.188byte, 11bảng nén+NPZfloat64: sourceSHA giữ nguyên, manifestSHA `004df66221186936ae46cd3dec3a9a14097f51d1dcfd8c3c7fd68924e20341fb`. DB đối soát 17.020 nhóm allocation trong1e-8, ledger balance/IP/sales, ETA7 và alert metrics tính lại khớp. 87.400ledger/3.246lô/8.941alertrows/10scenario summaries; source order/customer IDs trong payload=0, không credential patterns. Bốn module chia sẻ với backend giữ byte nguyên. Clone repo deploy mới, giữ checkout cloud cũ có thay đổi .gitattributes.

106 tests Python đạt, không fail/error/skip; gồm9tests public mới. AppTest7màn hình,3chế độ forecast và submit what-if đạt. Lượt AppTest đầu bị kẹt trong sandbox; chỉ dừng đúng tiến trình test do agent tạo và chạy lại có chẩn đoán/timeout với quyền local phù hợp, đạt trong vài giây. Không sửa dữ liệu/metric vì lỗi môi trường.

Đã push `Sigma-M3-App/main` commit `779b6c44f56aefbbba1c907a57a3acc4144563ef`, remoteSHA khớp. App ngủ do không hoạt động; đã wake, cloud hiện đúng `m3-public-20261020-v1`,10/10/11,62%/100%, fill90,41%/early34,39% theo profile mới. Share→Make this app public checkbox=1. Không gửi lời mời/email. Link [ứng dụng](https://sigma-demand-inventory.streamlit.app/); [source/phạm vi](../M3/streamlit/README.md). Raw/run/DB/env và ảnh/receipt kiểm giữ local. R05 test hồi cứu; R07/T14 tiếp tục cần mentor review.


<a id="e95"></a>
## CHG-063 / E95 — React thành web quản lý M3, 20/10/2026

Người dùng yêu cầu làm lại FE bằng React, tập trung chức năng M3 đã bàn, bỏ trình bày dạng báo cáo và push cho nhóm. Nhánh codex/m3-implementation nềncdfad3a; đọc AGENTS/TASK/PROJECTMAP/PLAN và đặc tả FE/nghiệp vụ/API liên quan. Không đổi model, raw, split/top10/M05, database schema hoặc công thức policy.

Đã triển khai sidebar/header/bộ lọc, tổng quan công việc theo ngày/filter, bảng tồn và ngăn chi tiết, đề xuất/lô nhập, cảnh báo nghiệp vụ, cấu hình versioned. Ba chế độ forecast giữ API thật; tổng30 mặc định46tuyến, metric/replay trong details. Thêm workspace read model theo frozen run, tính pending theo ordered_on/ETA tại mốc đã biết; metric split lọc trước phân trang/export. Fix ngăn chi tiết stale, pager nhập khi đổi filter và mặc định forecast parent replay nhiều origin. Không thêm gửi đơn supplier thật/auth/hosting nhiều người.

109Python=77M3+32M2 đạt0fail/error;17React đạt, build/TypeScript/Ruff đạt. Test mới kiểm không lấy lô đặt trong tương lai/không dùng status cuối replay, SKU/type/null/incomplete guard và split trước phân trang. Test FE kiểm tác vụ chính/stalecontext/drawer/pager/parent/snapshotcaption. Lượt test đầu timeout do PostgreSQL local chưa chạy đúng cổng; khởi động đúng cluster pgdata_v2 với port55432, không reinit/mất dữ liệu. Một lần test UI sau bổ sung caption lỗi fixture thiếu context; sửa fixture theo API thật rồi chạy lại17 đạt. Bố cục mobile phát hiện chart-panel tràn; thêm min-width0 và kiểm390/768/1440 hết tràn trang.

Browser tạo kịch bản management_ui_20261020v1 và phương án0c3460ff-6219-408d-b4a6-8a744f06e21d từ forecast7f7c53cb/scenario7. Worker complete/verified920threshold/920events/1lot/1714alerts. Đối soát API/CSV case item341:closing7/ROP20/pending20/IP27/Q0, ETA04/11. Tổng quan theo bộ lọc46tuyến/920item:1314tồn,793Q>0/5866đơn vị,1lô20,200urgentitems. Tất cả là mô phỏng cụ thể, không gọi KPI doanh nghiệp. Console error ở lượt cuối trống; ảnh/receipts ởoutputs private.

TASK/PLAN/PROJECTMAP/README/IMPLEMENTATION và đặc tả FE/API đồng bộ. M05 vẫn10/10 hồi cứu, R07/T14 chưa nâng nghiệm thu. React mới chưa thay ứng dụng Streamlit E94; source/docs được phép push nhưng raw/run/DB/env không vào Git. SHAremote và CI kiểm sau commit, không suy đạt từ test local. Hướng dẫn cho nhóm tại [IMPLEMENTATION](../M3/IMPLEMENTATION.md#react-management-e95).


## CHG-064 / E96 — Làm rõ ngữ cảnh bài M3 trên web quản lý

Ngày20/10/2026, người dùng hỏi đã giống web quản lý chưa và yêu cầu “giống bài tập hơn”. Đã hỏi làm rõ; trong khi chưa có trả lời, chọn hướng bám đề M3/dễ trình diễn, giữ giao diện quản lý. Chỉ sửa nhãn/ngữ cảnh SIM/gói data, lối đi bốn bước ở Tổng quan và diễn giải tiếng Việt thuật ngữ nhập/cấu hình. Không thêm login/PO/khách hàng/quy trình doanh nghiệp hoặc trang báo cáo; không đổi target/model/policy/API/DB/run/metric/nghiệm thu.

17React và TypeScript/Vite build đã chạy đạt. Browser thực bấm Xem dự báo và Kế hoạch nhập giữ run0c3460ff/origin31/10; bốn bước là điều hướng, không giả làm trạng thái hoàn tất. Viewport390/1440 không tràn trang, số liệu mô phỏng giữ nguyên; ảnh lưuoutputs local. Không chạy lại109Python hoặc refit vì chỉ thay nhãn/điều hướng;109Python và hai CI success f563d7d thuộc E95. TASK/PLAN/PROJECTMAP/IMPLEMENTATION/FE spec đồng bộ; CI commit mới kiểm riêng khi push. Bản Streamlit không đổi.
