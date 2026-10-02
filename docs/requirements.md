# Yêu cầu và tiêu chí nghiệm thu SIGMA

**Phiên bản:** 2.0 — 02/10/2026. **Trạng thái:** Khảo sát đã thực hiện, triển khai chưa bắt đầu; chưa có yêu cầu nào nghiệm thu toàn bộ. Lượt này chỉ cập nhật ba Markdown.

[Kế hoạch hiện hành](../PLAN.md) · [Nhật ký và thay đổi](review-log.md)

## 1. Nguồn và thứ tự áp dụng

Xác nhận mới của mentor do người dùng cung cấp thay phần cũ mâu thuẫn; yêu cầu bảo mật/phạm vi mới của người dùng được áp dụng. Báo cáo nhóm là bản nháp cần đối chiếu, không tự thành yêu cầu chính thức. Dữ liệu chứng minh điều quan sát trong tệp, không tự xác nhận quy tắc kinh doanh. Phân biệt xác nhận, lựa chọn người dùng và đề xuất kỹ thuật.

| Mã | Nguồn và phạm vi |
|---|---|
| S01 | [Ảnh đề bài](PROJECT_REQUIREMENTS.png): ban đầu nói kích hoạt; tuyến quốc gia–nhà mạng, M1–M3, MAPE≤20% top 10, cảnh báo trước≥7 ngày, dashboard. Phần target được M01 thay thế |
| S02 | [Báo cáo nhóm 45 trang](<Báo cáo chi tiết Sigma.pdf>): bản nháp/phương pháp/nhận định cần đối chiếu, mốc có năm |
| S03 | [CSV order](../data/sigma_sim_data_orders.csv): 100.000 dòng, 20 cột; dữ liệu quan sát |
| U01 | Yêu cầu khảo sát đầy đủ, bảo toàn gốc, quản lý thay đổi và bàn giao có bằng chứng ngày 02/10/2026 |
| U02 | Lựa chọn cũ: target mọi activation gồm refunded, MAPE ngày dương từng tuyến, mô phỏng, Colab/demo riêng, giữ mốc. Chỉ phần mâu thuẫn bị thay, xem DEC01–DEC13 |
| U03 | Yêu cầu chỉ tạo ba Markdown, chưa mã/cài đặt/thực nghiệm; giữ nguyên nguồn/tệp bị xóa |
| P01 | Thiết kế 1.0: UTC, split, horizon 14, hữu hạn ứng viên, chính sách tồn. Phần thay thế giữ ở review-log |
| M01 | Ảnh mentor về **số lượng bán không phụ thuộc active**, top 10 theo số bán, được người dùng thuật lại ngày 02/10/2026. Chưa nhận/đọc trực tiếp ảnh này |
| M02 | Ảnh mentor về **ngưỡng riêng từng đối tác**, Vina là ví dụ, chưa có giá trị số, được người dùng thuật lại ngày 02/10/2026. Chưa nhận/đọc trực tiếp ảnh này |
| U04 | Tệp yêu cầu cập nhật ngày 02/10/2026: chỉ order thực vì bảo mật, nhóm giả định phần còn lại; không chờ dữ liệu nội bộ; tồn < ngưỡng; bảo mật/độ nhạy/truy vết |
| P02 | Phương án 2.0 cụ thể hóa M01/M02/U04; A08–A17 vẫn **đề xuất**, chưa có bằng chứng nhóm/mentor xác nhận tham số |
| U05 | Yêu cầu “Cập nhật lại các file MD”: cho phép áp dụng bản cập nhật vào ba tệp hiện có, chưa triển khai phần mềm |

M01/M02 ghi đúng nguồn thuật lại, không giả nhận đã xem hai ảnh. Không cần xin lại quyết định mentor đã chốt hoặc dữ liệu doanh nghiệp sẽ không cung cấp. Ngày ghi nhận theo Asia/Saigon; ngày trong dữ liệu theo UTC.

## 2. Định nghĩa và phân loại hiện hành

| Khái niệm | Quy ước 2.0 |
|---|---|
| Target | Tổng quantity của dòng success theo UTC_date(order_datetime) và tuyến; **A08 đề xuất**, không phụ thuộc activation |
| Trạng thái khác | refunded loại cơ sở, success+refunded là kịch bản riêng; failed/timeout/pending loại. Không có canceled/ngày hoàn/hoàn một phần để bịa điều chỉnh |
| Sản phẩm / đơn / dòng | Quantity là lượng sản phẩm; order_count là ID hợp lệ khác nhau; số dòng là thống kê cấu trúc |
| Tuyến | destination_country–carrier, 46 cặp; Europe (EU) là nhóm điểm đến |
| Khoảng quan sát | 01/01/2024–31/12/2025, 731 ngày; không cắt đầu kỳ theo độ trễ activation |
| Train | 01/01/2024–30/06/2025 |
| Validation | Target_date 01/07/2025–30/09/2025 |
| Test | Target_date 01/10/2025–31/12/2025, không dùng chọn mô hình/định nghĩa số bán |
| Top 10 | Tổng quantity bán train giảm dần, hòa theo tên tuyến; cố định, không dùng doanh thu/số active/số đơn |
| Origin / horizon | Chạy sau chốt as_of_date, dự báo ngày kế tiếp; H=14, M2 chính h1–7, h8–14 riêng |
| Partner | Carrier là proxy đề xuất A09; Vina→Vinaphone là giả định, không là mapping đã xác minh |
| Khóa tồn | Tuyến × SKU × product_type; region không phải kho thật; đầu vào tồn/nhập/lead time đều giả định |
| Cần nhập | closing_on_hand < ROP theo cấu hình đối tác; bằng ngưỡng không kích hoạt; IP chỉ dùng tính lượng đặt |
| Thiếu thông tin | Không thay bằng 0; thiếu partner config báo missing_partner_config, không lấy cấu hình đối tác khác |

Dữ liệu quan sát trong order, dữ liệu dẫn xuất có công thức/cutoff, giả định có mã/trạng thái và kết quả mô phỏng có is_simulated/scenario_id phải được phân biệt trên bảng, manifest, dashboard và báo cáo. Lượng bán là snapshot hồi cứu; không chứng minh trạng thái đã biết tại origin hoặc phản ánh đủ nhu cầu/lost sales. Không lấy fulfilled của mô phỏng thay target bán lịch sử.

## 3. Yêu cầu bắt buộc và sản phẩm chứng minh

<a id="r01"></a>
### R01 — Chuẩn hóa và kiểm tra số bán

- **Nguồn:** S01/M1, S03, U01, M01, U04. **Trạng thái:** Chưa nghiệm thu; khảo sát không thay pipeline.
- **Nội dung:** Audit toàn bộ order; target A08; tách dòng/đơn/quantity; kiểm tra order timestamp, trạng thái, duplicate, giá trị và tổng hợp.
- **Tiêu chí:** Hash nguồn không đổi; quantity bảo toàn; success chưa active vẫn tính tại ngày đặt; activation thiếu/sai không loại sales hợp lệ. Trùng ID giống nội dung chỉ dedup processed có log; trùng ID mâu thuẫn cách ly/chặn phần ảnh hưởng, khác ID không tự xóa. Quantity nguyên dương; audit activation riêng. Không xóa ngày 0/đỉnh để hạ sai số.
- **Sản phẩm dự kiến:** data_audit.json, processed/daily_sales.csv, bảng lỗi/đối soát và manifest.
- **Nhiệm vụ:** [T01](../PLAN.md#t01), [T03](../PLAN.md#t03), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).

<a id="r02"></a>
### R02 — Phân tích số bán và mùa vụ

- **Nguồn:** S01/M1, M01, P02. **Trạng thái:** Chưa nghiệm thu.
- **Nội dung:** EDA số bán theo tuần/tháng/lễ/Tết, độ thưa và giả thuyết mùa du lịch trên 731 ngày.
- **Tiêu chí:** Nguồn lịch công khai, quốc gia/ngày truy cập; hình có đơn vị/mẫu số/bộ lọc/phạm vi; hệ số tái tính được. Không dùng cờ tương lai làm feature; không mặc định mùa hè chung mọi tuyến hoặc kết luận nhân quả. Các hình activation cũ cần tính lại/đổi phạm vi rõ.
- **Sản phẩm dự kiến:** holidays.csv, bảng/hình EDA của run, phần phân tích báo cáo.
- **Nhiệm vụ:** [T04](../PLAN.md#t04), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).

<a id="r03"></a>
### R03 — Baseline ngoài mẫu cho số bán

- **Nguồn:** S01/M1 yêu cầu naive/moving average; P01/P02 thêm seasonal naive 7/protocol; M01 đổi target. **Trạng thái:** Chưa nghiệm thu; MA7 activation không là kết quả sales/M2.
- **Nội dung:** Naive, MA7, seasonal naive 7 cho 46 tuyến; lưu từng origin/horizon và chấm cùng cặp hợp lệ.
- **Tiêu chí:** Split thời gian, không shuffle; tính tay được; không dùng actual tương lai/trung gian horizon; refit 7 ngày/cập nhật actual theo protocol. Ngày 0/thiếu nhãn/nhiều origin cùng target xử lý đúng; công khai giới hạn snapshot trạng thái.
- **Sản phẩm dự kiến:** predictions.csv, metrics.csv, protocol và ca chống rò rỉ.
- **Nhiệm vụ:** [T05](../PLAN.md#t05), [T06](../PLAN.md#t06), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).

<a id="r04"></a>
### R04 — Dự báo số bán và chọn mô hình theo tuyến

- **Nguồn:** S01/M2 và U02 giữ cấp quốc gia–nhà mạng; M01 đổi target/top 10; P02 phương pháp. **Trạng thái:** Chưa nghiệm thu.
- **Nội dung:** Forecast 46 tuyến; top 10 train; 6 SARIMA, 4 LightGBM khi còn top 10 chưa đạt validation sau SARIMA; chọn từng tuyến bằng validation.
- **Tiêu chí:** Đủ forecast/as_of_date/target_date/horizon/model và 14 ngày ở lượt forecast. Feature lag/rolling số bán tại origin/lịch biết trước; nhãn train nhiều horizon≤cutoff. Top 10 không nhìn test; không chọn lại bằng test; forecast âm chặn 0 có thống kê, không làm tròn trước chấm. Các tuyến ngoài top 10 chọn baseline MAE tốt nhất.
- **Sản phẩm dự kiến:** top_routes.csv, selected_models.csv, predictions/metrics ứng viên, log hội tụ, config/manifest.
- **Nhiệm vụ:** [T04](../PLAN.md#t04), [T05](../PLAN.md#t05), [T06](../PLAN.md#t06), [T07](../PLAN.md#t07), [T08](../PLAN.md#t08), [T09](../PLAN.md#t09), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).

<a id="r05"></a>
### R05 — Độ chính xác từng tuyến top 10

- **Nguồn:** S01 ghi MAPE≤20% top 10; U02 chọn ngày dương/từng tuyến, chưa phải mentor xác nhận riêng; M01 yêu cầu xếp theo số bán. **Trạng thái:** Chưa nghiệm thu.
- **Nội dung:** Cả 10 tuyến phải đạt MAPE ngày dương≤20% trên test chính h1–7; kèm số mẫu/độ phủ, MAE/WAPE/bias mọi ngày. h8–14 riêng.
- **Tiêu chí:** Metric truy về predictions; actual 0 vẫn trong MAE/WAPE/bias; MAPE toàn 0 và WAPE mẫu số 0 không xác định, không trả 0%. Không nhãn không chấm. Không đổi định nghĩa sales, top 10, bộ lọc ngày hoặc mô hình bằng metric test để đạt.
- **Sản phẩm dự kiến:** metrics test theo tuyến/horizon, bảng top 10 đạt/chưa đạt và giới hạn.
- **Nhiệm vụ:** [T05](../PLAN.md#t05), [T07](../PLAN.md#t07), [T08](../PLAN.md#t08), [T09](../PLAN.md#t09), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).
- **Giới hạn:** MAPE MA7 45,8%–72,5% cũ thuộc activation, cần tính lại; không dự báo trước khả năng đạt ngưỡng của sales. Không đạt vẫn công bố đúng.

<a id="r06"></a>
### R06 — Tồn kho và ngưỡng nhập theo đối tác

- **Nguồn:** S01/M3, U02 mô phỏng; M02 ngưỡng riêng, U04 strict < và chỉ order; A09–A16/P02 là đề xuất. **Trạng thái:** Chưa nghiệm thu.
- **Nội dung:** Phân bổ sales forecast theo 30/90 ngày; giả định tồn/ETA/L/R/b/MOQ; tính SS/ROP/S/IP/Q và ledger. Mỗi partner cấu hình riêng; proxy carrier/Vina→Vinaphone có nhãn giả định.
- **Tiêu chí:** Trigger closing_on_hand < ROP; bằng ngưỡng không kích hoạt; IP dùng lượng đặt, MOQ chỉ Q>0. Thiếu cấu hình không gán 0/ngưỡng chung. Phân bổ bảo toàn; ETA có hiệu lực đầu ngày; giao dịch order_datetime/order_id; closing=opening+receipts−fulfilled; sales=fulfilled+shortage; không sửa sales lịch sử. H đủ L+R. Hai đối tác có thể khác cảnh báo cùng tồn. Tồn 0 khác còn tồn thấp và khác shortage.
- **Sản phẩm dự kiến:** partner_map/config, inventory.csv/receipts.csv giả định, inventory_ledger.csv, inventory_recommendations.csv, simulation_metrics.csv.
- **Nhiệm vụ:** [T06](../PLAN.md#t06), [T10](../PLAN.md#t10), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).
- **Giới hạn:** Chỉ kiểm chứng quy tắc/kịch bản; độ nhạy tồn đầu {3,7,14} ngày, L {1,3,7}, hệ số safety {0,5;1;1,5}, ghi kết luận đảo chiều. Không đòi thêm dữ liệu nội bộ hoặc khẳng định tồn đúng doanh nghiệp.

<a id="r07"></a>
### R07 — Đo cảnh báo trước ít nhất 7 ngày

- **Nguồn:** S01/M3; P02 replay/horizon; U04 mô phỏng có nhãn. **Trạng thái:** Chưa nghiệm thu.
- **Nội dung:** Tách cảnh báo dưới ngưỡng với ngày cạn dự kiến; 1–6 ngày khẩn/muộn, 7–14 sớm, không bịa ngày ngoài horizon.
- **Tiêu chí:** Ca cạn ngày 10 có báo trước≥7; ngày 3 không tính đạt. Replay đợt 14 ngày không chồng lấn từ origin 30/09/2025, đủ nhãn, không đặt mới; event đầu tiên/mặt hàng/đợt duy nhất. Có precision/recall, tỷ lệ báo sớm, số muộn, sai số ngày cạn/mẫu số. Lượt đánh giá chính sách có nhập mới tách riêng, không gọi cảnh báo được ngăn cạn là sai.
- **Sản phẩm dự kiến:** alerts.csv, event ledger, simulation_metrics.csv, ca tính tay và độ nhạy.
- **Nhiệm vụ:** [T06](../PLAN.md#t06), [T10](../PLAN.md#t10), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).
- **Giới hạn:** Ca chuẩn chỉ chứng minh cơ chế, phải công khai replay. Không có ngưỡng precision/recall chính thức; không tự thêm để tuyên bố đạt. Không coi cạn trong 7 ngày là báo trước 7 ngày, không bảo đảm mọi tình huống.

<a id="r08"></a>
### R08 — Dashboard riêng trên Windows

- **Nguồn:** S01/M3, U02 demo riêng; U04 bảo mật; P02 local. **Trạng thái:** Chưa nghiệm thu.
- **Nội dung:** Streamlit đọc một run hoàn tất, xem sales actual/forecast/metric, tồn/khuyến nghị/cảnh báo mô phỏng và giả định theo đối tác.
- **Tiêu chí:** Màn hình khớp CSV; manifest và các phiên bản nhất quán, không trộn run/hết hiệu lực; luôn có as_of_date/thời điểm chạy. Phân biệt 0/thiếu/chưa actual, thật/dẫn xuất/giả định/mô phỏng; thiếu gói báo rõ. Demo không cần train lại, export theo quyền dữ liệu.
- **Sản phẩm dự kiến:** app.py, requirements-demo, gói riêng tư/gói giả, demo-script/hướng dẫn cập nhật local.
- **Nhiệm vụ:** [T06](../PLAN.md#t06), [T11](../PLAN.md#t11), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).
- **Mặc định:** Replay 31/10/2025; latest cutoff 31/12/2025 dự báo 01–14/01/2026, **không có actual order tháng 01**; activation tháng 01 không dùng chấm. Không gọi là giám sát hiện thời.

<a id="r09"></a>
### R09 — Tái lập, bảo mật và quản lý thay đổi

- **Nguồn:** U01/U03/U04/U05; P02. **Trạng thái:** Có bộ tài liệu, chưa nghiệm thu tái lập/bàn giao.
- **Nội dung:** Nguồn bảo toàn; input/config/assumption/target/mã/run có phiên bản; chỉ xử lý dữ liệu thật trong dự án local, không phụ thuộc doanh nghiệp cấp thêm dữ liệu.
- **Tiêu chí:** Môi trường local sạch và máy demo chạy theo README; cùng input/config/seed tái lập, số nguyên tuyệt đối và số thực theo dung sai đã ghi. Manifest hash/Python/thư viện/cutoff/seed; báo cáo truy về run. Thay A08 tính lại chuỗi/top 10/mô hình/tồn, thay A12 tính lại tồn/cảnh báo, giữ forecast nếu độc lập. Kết quả cũ mất hiệu lực phải đánh dấu. Không upload thật/tìm kiếm ngoài chứa dữ liệu riêng tư; allowlist gói chia sẻ không raw/ID/notebook output/lịch sử Git chứa CSV.
- **Sản phẩm dự kiến:** Ba Markdown; README mới, notebook local, mã/config/phụ thuộc, tests/checks, manifest, báo cáo/slide, biên bản nghiệm thu và gói phù hợp quyền.
- **Nhiệm vụ:** [T01](../PLAN.md#t01), [T02](../PLAN.md#t02), [T03](../PLAN.md#t03), [T06](../PLAN.md#t06), [T09](../PLAN.md#t09), [T10](../PLAN.md#t10), [T11](../PLAN.md#t11), [T12](../PLAN.md#t12), [T13](../PLAN.md#t13), [T14](../PLAN.md#t14).
- **Giới hạn:** CSV đã tracked, .gitignore không xóa lịch sử; không push/công khai hoặc tự viết lại Git. Colab dữ liệu thật bị thay bằng local; Colab nếu cần chỉ minh họa giả.

## 4. Quyết định, đề xuất và phần chưa kiểm chứng

| Nhóm | Nội dung hiện hành | Nguồn/trạng thái |
|---|---|---|
| Đã xác nhận | Số lượng bán không phụ thuộc active; top 10 theo số bán | M01, thuật lại mentor |
| Đã xác nhận | Ngưỡng riêng đối tác, Vina ví dụ; **không có số ngưỡng** | M02, thuật lại mentor |
| Ràng buộc | Chỉ order thực; phần còn lại nhóm giả định; không xin thêm nội bộ; bảo mật | U04 |
| Giữ lựa chọn cũ | Tuyến quốc gia–nhà mạng; MAPE ngày dương từng tuyến; mô phỏng, demo riêng, M2 17/10/2026, M3 07/11/2026, bù M1 | U02, phần không mâu thuẫn |
| Đề xuất có thể điều chỉnh | success làm sales, Vina→Vinaphone, tồn đầu 7 ngày, L=3, b=4/2, review=1, MOQ=1, receipts đầu rỗng, seed=42 | A08–A17/P02; chưa gắn nhãn nhóm/mentor thống nhất |
| Phạm vi hành động | Cập nhật ba Markdown hiện có; chưa code/cài đặt/thực nghiệm | U05 |

Không có câu hỏi cần trả lời để cập nhật tài liệu. Trạng thái lịch sử, số bán thuần/gộp, mapping partner và vận hành tồn thật là giới hạn/giả định, không trở thành phụ thuộc xin thêm dữ liệu. Quỹ giờ nhóm chưa rõ; tổng 97–149 người-giờ hoặc 105–163 nếu T08 kích hoạt không phải cam kết nhân lực.

## 5. Nghiệm thu và phiên bản

Chưa có run, tests pipeline, dashboard, báo cáo sửa hoặc slide. Không yêu cầu R01–R09 nào được đánh dấu hoàn thành toàn bộ. Chương trình chạy, phương pháp đúng, metric đạt và vận hành thật được chứng minh là các kết luận cần bằng chứng khác nhau.

Chỉ gọi toàn dự án hoàn thành khi đủ bằng chứng bắt buộc; nếu sản phẩm bàn giao còn tiêu chí chưa đạt, ghi **“đã bàn giao sản phẩm; còn tiêu chí chưa đạt”**. Phản hồi mới ghi [quy trình thay đổi](review-log.md#change-process), cập nhật PLAN/tiêu chí/config và đánh dấu đầu ra cần tính lại. Không sửa tiêu chí để vượt kiểm tra.

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 1.0 | 02/10/2026 | R01–R09 theo target activation/lựa chọn cũ; chưa có phản hồi mới lúc ghi nhận |
| 2.0 | 02/10/2026 | CHG-003 áp dụng M01/M02/U04/U05: sales, partner, giả định, local/bảo mật; mã yêu cầu giữ nguyên, chưa nghiệm thu |
