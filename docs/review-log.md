# Nhật ký rà soát, quyết định và thay đổi SIGMA

**Phiên bản lịch sử:** 2.0 — 02/10/2026. **Trạng thái tại 02/10:** Khảo sát đã thực hiện, triển khai chưa bắt đầu. Lượt này cập nhật ba Markdown, không huấn luyện hoặc chạy thực nghiệm mới. Bằng chứng activation cũ được giữ như lịch sử, cần tính lại cho mục tiêu số bán.

**Cập nhật triển khai 05/10/2026:** E01–E10/RV/QA-DOC cũ là lịch sử, không phải kiểm tra lại ảnh/PDF đang thiếu. E11 trở đi là bằng chứng kiểm tra trực tiếp lượt triển khai; CHG-008 cho phép local và push allowlist, CHG-009/010 cho phép tinh chỉnh bằng validation và công khai test đã xem. Không nghiệm thu toàn bài khi R05 chưa đạt.

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
