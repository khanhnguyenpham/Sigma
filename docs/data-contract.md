# Hợp đồng dữ liệu SIGMA

**Cập nhật 05/10/2026 — CHG-024/025, E37–E39:** đã áp dụng **khách đặt D → giao D+7 ngày lịch UTC**, không trễ giao, gồm cuối tuần; không đổi lead time nhập kho. Người dùng mô tả snapshot order là giả định; đây là nguồn thuật lại, vẫn giữ dữ liệu/outputs private và raw nguyên. [Sản phẩm chung và lịch giao](customer-delivery.md) mở bằng `start_product.ps1` tại cổng 8503. Run tuần hiện hành `sigma_weekly_calibrated_v5`: test hồi cứu **9/10**, mean **15,97%**, LG U+ **21,36%**; chọn validation rồi khóa trước test. 920 khuyến nghị tồn từ phân bổ tuần đã đối soát, replay cùng 5.520 cửa sổ báo sớm **33,73%**; chưa chạy lại toàn bộ chính sách liên tục bằng tuần. 150 tests đạt, AppTest năm trang/không exception; job refresh/skip chạy thật, script đăng ký lịch nền được chuẩn bị nhưng chưa cài. R05 ngày **0/10**, R07/T14 vẫn mở. **Sau khi đủ điều kiện nghiệm thu mới làm bản so sánh chính thức ngày/tổng 7 ngày và tổ chức lại code**, đúng thứ tự người dùng yêu cầu; chưa làm lại Word/slide. Những cập nhật E36/v1 bên dưới là lịch sử.

**Phương án tuần CHG-023/E36:** cùng target sales-success-utc-v1, tổng quantity của bảy ngày UTC liên tiếp. `weekly_forecast.csv`: route, model, as_of_date, window_start, window_end, week_block1/2, forecast_qty_7d, actual_qty_7d; actual tương lai để trống. `daily_allocation.csv`: route/origin/target_date/horizon_day/week_block/forecast_qty, is_daily_allocation=true; bảy forecast_qty cộng đúng forecast_qty_7d. Không phải dữ liệu tồn thực hoặc bảy dự báo ngày độc lập. Cửa sổ thiếu bảy actual không được chấm như tuần đầy đủ; metric tuần có coverage/zero-window count/MAE/WAPE/bias và cadence. [Protocol và lệnh thực chạy](weekly-forecast.md); schema run ngày không đổi.

**Triển khai 05/10/2026:** Audit/chuỗi/forecast/metric/phân bổ/tồn đã có trong src và CLI. Tên đầu ra thực cùng version/hash ghi trong manifest mỗi run; `forecast_qty` là giá trị dự báo, `target_date` là ngày được dự báo. CHG-016 thêm xử lý giao dịch UTC và event ledger, đã kiểm run v7; không chỉ dùng phép tương đương tổng ngày để nhận R06 đủ bằng chứng. Các mô tả “dự kiến/chưa có” ngày 02/10 bên dưới giữ làm lịch sử thiết kế. Không nâng giả định thành dữ liệu thật.

**Bản tài liệu:** 1.0 — 02/10/2026 (Asia/Saigon), diễn giải [PLAN 2.0](../PLAN.md), [requirements 2.0](requirements.md) và [review-log 2.0](review-log.md). Schema nguồn đã khảo sát chỉ đọc; schema processed/run bên dưới **dự kiến, chưa triển khai**. Không có từ điển dữ liệu doanh nghiệp để xác nhận toàn bộ ý nghĩa tên cột.

<a id="source-check"></a>
## 1. Nguồn và phạm vi kiểm chứng

Nguồn hiện có: [data/sigma_sim_data_orders.csv](../data/sigma_sim_data_orders.csv). Khảo sát chuẩn bị bộ tài liệu đã đọc toàn bộ CSV trong bộ nhớ, chỉ xuất thống kê/schema, không in định danh order/customer. Lượt tạo tài liệu đối chiếu lại hash, khớp bản đã khảo sát. Đây không phải audit pipeline T03.

| Thuộc tính | Kiểm tra trực tiếp trong đợt khảo sát này |
|---|---|
| Kích thước / dòng / cột | 17.226.621 byte; 100.000 dòng dữ liệu, không tính header; 20 cột |
| Biểu diễn | Đọc được bằng UTF-8; không BOM; phân cách dấu phẩy; 100.001 dấu LF, không CRLF |
| Độ rộng bản ghi | Không có dòng thiếu/thừa trường theo header |
| Thời gian | Mọi timestamp không rỗng parse được theo ISO-8601, có `Z` UTC |
| Missing | `activation_datetime`: 5.691 dòng; các cột khác: 0 theo kiểm tra rỗng/whitespace |
| Ngày đặt UTC | Từ 01/01/2024 đến 31/12/2025 |
| Ngày activation UTC | Từ 01/01/2024 đến 14/01/2026; không phải khoảng nhãn sales |
| Tuyến | 46 cặp `(destination_country, carrier)` |
| Trạng thái / số dòng | success 93.104; refunded 1.205; failed 2.330; timeout 2.214; pending 1.147 |

**SHA-256 hiện tại, tính trên byte gốc:**

```text
6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b
```

[E02 trong nhật ký](review-log.md#evidence) ghi kích thước 17.326.622 byte và hash lịch sử:

```text
22bf50f47978de131e3834811d4da9b4b3647e4eb4d073f574337e21143c5264
```

Chuyển LF thành CRLF **chỉ trong bộ nhớ** từ tệp hiện tại tạo đúng kích thước/hash lịch sử trên. Khác biệt byte phù hợp hoàn toàn với biểu diễn xuống dòng; không xác định ai hoặc công cụ nào đã chuyển. Không ghi đè CSV, không tuyên bố hash byte hiện tại giống E02. Dùng hash hiện tại làm mốc bảo toàn cho lượt này.

Số tổng quantity, duplicate, thứ hạng top 10, quan hệ SKU và các kết quả E03–E09 khác vẫn là **ghi nhận lịch sử nếu không nằm trong bảng kiểm tra trực tiếp trên**. T03–T05 phải tái sinh bằng mã và lưu bằng chứng. Ảnh/PDF thiếu và giới hạn Git tại [PROJECTMAP](../PROJECTMAP.md#source-gaps).

## 2. Schema CSV: 20 cột theo đúng thứ tự

CSV lưu văn bản. “Quan sát” dưới đây là kiểu biểu diễn của giá trị không rỗng, không có nghĩa file có kiểu vật lý như bảng SQL. “Dự kiến” là kiểu xử lý về sau. Ý nghĩa nghiệp vụ là suy luận từ tên cột và nguồn 2.0, trừ định nghĩa target đã có nguồn riêng; không coi là từ điển chính thức.

| Cột | Biểu diễn quan sát / missing | Kiểu xử lý dự kiến | Ý nghĩa và giới hạn |
|---|---|---|---|
| `order_id` | Chuỗi định danh; 0 thiếu | string | ID đơn dùng dedup/order_count; không xuất giá trị vào tài liệu/log chia sẻ |
| `order_datetime` | ISO-8601 UTC `Z`; 0 thiếu | datetime có timezone UTC | Thời điểm đặt; cơ sở gán ngày sales theo A08 |
| `activation_datetime` | ISO-8601 UTC `Z`; 5.691 thiếu | datetime UTC nullable | Thời điểm activation; audit riêng, không phải target/điều kiện sales |
| `product_type` | Chuỗi; 0 thiếu | string/categorical | Loại sản phẩm; thành phần khóa mặt hàng tồn, không gộp tùy tiện |
| `destination_country` | Chuỗi; 0 thiếu | string/categorical | Điểm đến của tuyến; nguồn cũ ghi Europe (EU) là nhóm điểm đến, không bắt buộc là mã quốc gia chuẩn |
| `region` | Chuỗi; 0 thiếu | string/categorical | Nhóm địa lý; không có bằng chứng là kho thật |
| `carrier` | Chuỗi; 0 thiếu | string/categorical | Nhà mạng của tuyến; proxy đối tác chỉ là A09 đề xuất |
| `sku` | Chuỗi; 0 thiếu | string | Mã gói/mặt hàng; giữ tên cột chữ thường, không đổi thành `SKU` trong nguồn |
| `plan_type` | Chuỗi; 0 thiếu | string/categorical | Loại gói; semantics chi tiết theo nhãn cần kiểm chứng khi audit |
| `data_gb` | Văn bản số nguyên; 0 thiếu | integer | Dung lượng ghi trên gói, đơn vị GB suy từ tên; không suy cách mã hóa gói unlimited hoặc coi là dung lượng đã tiêu thụ |
| `validity_days` | Văn bản số nguyên; 0 thiếu | integer | Số ngày hiệu lực suy từ tên; không phải lead time nhập hàng |
| `quantity` | Văn bản số nguyên; 0 thiếu | integer | Số đơn vị sản phẩm trên dòng; cần kiểm tra nguyên dương; đại lượng cộng để tạo target |
| `unit_price_vnd` | Văn bản số nguyên; 0 thiếu | integer tiền VND | Đơn giá suy từ tên; không làm trọng số xếp top 10 |
| `unit_cost_vnd` | Văn bản số nguyên; 0 thiếu | integer tiền VND | Chi phí đơn vị ghi trong order; không suy thành chi phí tồn/hủy hoặc hợp đồng được xác nhận |
| `gross_revenue_vnd` | Văn bản số nguyên; 0 thiếu | integer tiền VND | Doanh thu gộp ghi trên dòng; quan hệ quantity × unit_price là kiểm tra đối soát, không tự thành số bán thuần kế toán |
| `sales_channel` | Chuỗi; 0 thiếu | string/categorical | Kênh bán của bản ghi; không mặc định có sẵn cho ngày dự báo |
| `payment_method` | Chuỗi; 0 thiếu | string/categorical | Phương thức thanh toán ghi trên order |
| `customer_id` | Chuỗi định danh; 0 thiếu | string | ID khách; riêng tư, không dùng để minh họa hoặc đưa ra truy vấn ngoài |
| `customer_type` | Chuỗi; 0 thiếu | string/categorical | Nhãn khách tại bản ghi; E05 lịch sử cho thấy không thể mặc định bất biến theo customer_id |
| `order_status` | Chuỗi; 0 thiếu | string/categorical | Snapshot trạng thái; không có lịch sử chuyển trạng thái hoặc thời điểm hoàn tiền |

Không áp các giá trị min/max hoặc danh mục quan sát như giới hạn nghiệp vụ vĩnh viễn. Ví dụ quantity 1–4 là phạm vi ghi trong E03, không phải mức trần nhận dữ liệu tương lai.

<a id="definitions"></a>
## 3. Đơn vị, khóa và target

- **Dòng:** một bản ghi CSV; chưa mặc định bằng một đơn hợp lệ, nhất là khi có duplicate.
- **order_count:** số `order_id` hợp lệ khác nhau trong cùng nhóm ngày/tuyến sau xử lý duplicate và áp bộ lọc được khai báo. Với bảng sales cơ sở, dùng cùng bộ lọc A08. Không dùng số dòng hay order_count thay tổng quantity.
- **sales_qty:** tổng `quantity` của các dòng hợp lệ thuộc ngày đặt UTC và tuyến. Phương án cơ sở dưới là **A08 đề xuất**, không phải bộ lọc mentor xác nhận hoặc quy tắc kế toán:

```text
sales_qty[UTC_date(order_datetime), destination_country, carrier]
  = sum(quantity của dòng hợp lệ có order_status == "success")
```

- **Tuyến:** `(destination_country, carrier)`; hiện quan sát 46 cặp. Không đổi thành region × sku hoặc carrier × sku khi chọn top 10/nghiệm thu forecast.
- **Mặt hàng tồn:** `(destination_country, carrier, sku, product_type)`; `SKU` trong diễn giải PLAN chỉ cùng khái niệm với cột `sku`. Partner phải truy về mapping A09 có phiên bản, không có trường partner thật trong CSV.
- **Ngày:** parse timestamp thành UTC rồi lấy ngày; không chuyển sang timezone máy. Ngày ghi nhật ký tài liệu theo Asia/Saigon, khác ngày nghiệp vụ UTC.
- **Origin:** sau chốt `as_of_date`; h1 là ngày kế tiếp, `horizon_day` là số ngày từ origin tới ngày mục tiêu. PLAN ghi `forecast_date`, R04 ghi `target_date`: đều mô tả ngày mục tiêu, nhưng tên cột đầu ra chưa thống nhất bằng triển khai. Ghi rõ mapping khi tạo giao diện, không giả nhận hai cột đã tồn tại.

Theo [requirements](requirements.md), lưới thiết kế 01/01/2024–31/12/2025 gồm 731 ngày; train 01/01/2024–30/06/2025, validation 01/07/2025–30/09/2025, test 01/10/2025–31/12/2025. Top 10 cố định theo quantity bán train giảm dần, hòa theo tên tuyến; không dùng doanh thu, activation, số đơn hoặc test. H=14; h1–7 chính, h8–14 riêng.

## 4. Quy tắc làm sạch và missing — thiết kế chưa triển khai

**Bổ sung ngày 04/10/2026 (CHG-007):** Chuẩn hóa là parse/kiểm tra ở bản dẫn xuất có dấu vết, không sửa nguồn hoặc ép dữ liệu hợp lệ cho hợp mô hình. Timestamp có offset được chuyển UTC; timestamp naive không tự gán timezone. Chuỗi khóa chuẩn hóa phải khai báo quy tắc và phát hiện va chạm, không tự hợp nhất tuyến/SKU khác nhau. Quantity không nguyên dương và trạng thái lạ được báo lỗi, không đoán. Giá/doanh thu được audit riêng; lỗi tiền không tự chứng minh quantity sai. Ngày giảm/tăng bán thật không được tự xóa, cap hoặc impute; mất nguồn không phải ngày bán 0. Kịch bản biến động nguồn cung và lượng bán phải tách khỏi dữ liệu quan sát.

| Trường hợp | Xử lý theo PLAN / ranh giới suy luận |
|---|---|
| Thiếu cột bắt buộc tạo target, thiếu/sai order timestamp, khóa tuyến, order_id hoặc quantity | Ghi lỗi và cách ly/chặn phần target bị ảnh hưởng; không tự đoán ngày/khóa/số lượng. Rà chi tiết ca lỗi ở T03 trước khi chạy phụ thuộc |
| Trùng order_id, cùng nội dung | Giữ một bản trong processed, log số dòng/quantity bị loại và đối soát; nguồn không thay đổi |
| Trùng order_id, nội dung mâu thuẫn | Cách ly/chặn phần ảnh hưởng đến khi giải quyết; không tự chọn dòng thuận lợi theo metric |
| Nội dung giống nhưng ID khác | Không tự coi là cùng giao dịch để loại |
| Quantity không nguyên dương | Báo lỗi/chặn target bị ảnh hưởng; không làm tròn, ép 1, cap 4 hay tạo quantity âm |
| success | Tính quantity tại ngày đặt UTC, kể cả chưa activation hoặc activation muộn |
| refunded | Loại khỏi cơ sở; success+refunded chỉ là kịch bản định nghĩa riêng có phiên bản, không chọn bằng metric test |
| failed / timeout / pending | Không tính sales cơ sở; vẫn giữ trong audit/nguồn |
| Trạng thái lạ hoặc thiếu | Không suy là success/refunded; ghi lỗi và phần chưa có quy tắc để xử lý, không âm thầm hợp thức hóa target |
| activation thiếu/sai/trước order | Audit riêng; không loại sales hợp lệ hoặc thay thời điểm bán vì activation |
| Thiếu trường phụ trợ | Ghi missing và tác động cho thành phần dùng trường đó; không tự suy thông tin khách, đối tác hoặc giá trị tiền |
| Hủy/hoàn một phần/hoàn nhập | Không có canceled, ngày hoàn, quantity hoàn hoặc lịch sử trạng thái để xác định; không bịa điều chỉnh tồn/kế toán |

Order status chỉ là snapshot hồi cứu. Kiểm tra lag/cutoff không chứng minh trạng thái success cuối cùng đã được biết tại origin vận hành thật. Activation tháng 01/2026 không tạo actual sales tháng đó. Không xóa ngày 0, bỏ đỉnh hoặc winsorize để hạ MAPE.

### Ba tình huống phải tách

| Tình huống | Giá trị / nhãn cần giữ |
|---|---|
| Không có giao dịch hợp lệ trong ngày/tuyến thuộc phạm vi giả định quan sát đầy đủ A02/A05 | Điền `sales_qty=0`, order_count=0 trên lưới; đây là không có số bán quan sát, không chứng minh nhu cầu thị trường bằng 0 |
| Nguồn mất/thiếu/chưa xác định đầy đủ hoặc bản ghi lỗi chưa giải quyết | Giữ thiếu và lý do; không điền 0, không chấm như actual hợp lệ |
| Ngày forecast chưa có actual, ví dụ 01–14/01/2026 | `actual_qty` để trống/nullable, không 0; không chấm metric; activation hiện có không được dùng lấp nhãn |

Tương tự ở tồn kho: thiếu snapshot khác tồn 0; thiếu tệp receipts khác danh sách rỗng được khai báo theo A14. Thiếu cấu hình đối tác phải báo `missing_partner_config`, không lấy 0 hoặc ngưỡng chung thay thế.

## 5. Phân loại và truy vết dữ liệu

| Loại | Ví dụ | Truy vết tối thiểu theo thiết kế |
|---|---|---|
| Quan sát | Các trường order trong CSV | Path/hash nguồn, phạm vi đọc; chỉ có order thực theo người dùng, không khẳng định nguồn gốc doanh nghiệp bằng schema |
| Dẫn xuất | UTC date, sales_qty, order_count, top 10, lag/rolling, tỷ trọng | Công thức/bộ lọc, cutoff/cửa sổ, nguồn hash, target_definition_version và run khi đã triển khai |
| Tham chiếu công khai | Lịch lễ/Tết | Nguồn, quốc gia, ngày truy cập; không gửi dữ liệu riêng tư để tìm kiếm |
| Giả định | Partner map, tồn đầu, L/R/b/MOQ, receipts đầu kỳ | Mã Axx, giá trị/đơn vị/phạm vi, trạng thái, nguồn/lý do và assumption_version; tồn sinh từ trung bình sales vẫn là giả định |
| Mô phỏng | Ledger, fulfilled, shortage, khuyến nghị và cảnh báo | `is_simulated=true`, scenario_id, assumption_version, run/origin; không gọi là vận hành hoặc tồn thật |
| Dự báo | forecast_qty theo tuyến/ngày | run_id, model, as_of_date, horizon/ngày mục tiêu, target version; actual thiếu giữ trống |

M01/M02 là mentor do người dùng thuật lại. A08–A17 vẫn **đề xuất**, gồm proxy carrier/Vina→Vinaphone, tồn đầu, lead time, ngưỡng và seed; xem PLAN mục 3.2 để lấy giá trị/độ nhạy, không sao chép thành bảng tham số đã được duyệt tại đây.

<a id="outputs"></a>
## 6. Bảng đầu ra dự kiến và đơn vị

Tất cả sản phẩm dưới **chưa tồn tại**. Căn cứ PLAN mục 4.2, 5–6 và R01–R09. Khóa ở bảng là cấp dữ liệu dự kiến để đối soát, không phải schema API đã được khóa; tên trường nào chưa được PLAN nêu là mô tả, phải ghi rõ khi triển khai. Các bảng thuộc run phải truy về cùng manifest; phiên bản chung có thể ở manifest, không suy rằng đã có cột vật lý trong CSV.

| Sản phẩm / vị trí dự kiến | Khóa hoặc cấp dữ liệu | Đơn vị / nội dung | Truy vết và kiểm tra |
|---|---|---|---|
| `data/processed/daily_sales.csv` | Ngày UTC × destination_country × carrier, trong một target version | sales_qty: đơn vị sản phẩm; order_count: đơn khác nhau | target_definition_version, bộ lọc A08, tổng quantity khớp nguồn hợp lệ; thiếu khác 0 |
| `data/reference/holidays.csv` | Quốc gia/điểm đến × ngày × sự kiện lễ | Ngày và thông tin lịch | Nguồn/ngày truy cập; không coi là dữ liệu nội bộ hoặc cờ biết từ tương lai |
| `outputs/<run_id>/top_routes.csv` | Tuyến trong run, hạng không trùng | Tổng quantity bán train, thứ hạng | Train cutoff, target version, quy tắc hòa; khóa danh sách trước chấm test |
| `outputs/<run_id>/predictions.csv` | Run × as_of_date × tuyến × horizon_day × model | forecast_date/ngày mục tiêu; forecast_qty, actual_qty nếu có: sản phẩm; split | h1 là hôm sau; không forecast âm sau chặn có log; không làm tròn trước chấm; actual/split theo nhãn thật |
| `outputs/<run_id>/metrics.csv` | Run × model × tuyến × split × horizon hoặc nhóm horizon | MAPE/WAPE: %; MAE/bias: sản phẩm; số cặp và độ phủ | Truy đúng predictions; phân biệt số cặp với số ngày duy nhất; mẫu số 0 ghi không xác định |
| `outputs/<run_id>/selected_models.csv` | Tuyến trong run đã khóa | Model/cấu hình chọn và căn cứ validation | Metric/cấu hình/phiên bản; không dùng test chọn lại; ghi chưa đạt nếu không ứng viên đạt |
| `data/scenarios/partner_map.csv` | Carrier → partner_id theo assumption_version; alias có nguồn | carrier, partner_id, alias, nguồn/giả định | A09; không tự xác minh Vina→Vinaphone; thiếu mapping/config báo rõ |
| `data/scenarios/inventory.csv` | Scenario × cutoff snapshot × khóa mặt hàng tồn | Tồn đầu: sản phẩm | A10, cutoff chỉ dùng quá khứ; không nhầm thiếu snapshot với 0 |
| `data/scenarios/receipts.csv` | Scenario × lô hàng × khóa mặt hàng, có ETA UTC | Lượng đã đặt/chưa nhận: sản phẩm; ETA: ngày/thời điểm | A14; danh sách rỗng phải khai báo; chỉ cộng tồn khi tới ETA, không coi hàng muộn là sẵn có |
| `outputs/<run_id>/inventory_ledger.csv` | Run × scenario × khóa mặt hàng × thời gian/sự kiện; bản tổng hợp theo ngày tách rõ | opening, receipts, historical_sales, fulfilled, shortage, closing: sản phẩm | Thứ tự order_datetime/order_id; closing=opening+receipts−fulfilled; historical_sales=fulfilled+shortage; is_simulated |
| `outputs/<run_id>/inventory_recommendations.csv` | Run × scenario × origin × partner/mặt hàng | on_hand, SS, ROP, S, IP, Q: sản phẩm; ETA; trạng thái config | Ngưỡng riêng; trigger closing_on_hand < ROP; IP tính Q; MOQ chỉ khi Q>0; is_simulated |
| `outputs/<run_id>/alerts.csv` | Run × scenario × origin × mặt hàng × loại cảnh báo; event_id nối sự kiện được chấm | Ngày cạn dự kiến/thực mô phỏng; lead time cảnh báo: ngày | Tách dưới ROP/ngày cạn; event duy nhất; mẫu số/replay rõ; is_simulated |
| `outputs/<run_id>/simulation_metrics.csv` | Run × scenario × loại đánh giá × phạm vi kỳ/mặt hàng | Precision/recall/tỷ lệ đáp ứng/tỷ lệ báo ≥7 ngày: tỷ lệ có đơn vị ghi rõ; shortage/tồn: sản phẩm; sai số ngày cạn: ngày | Không trộn replay không đặt mới với policy có đặt; ghi mẫu số/ca loại/độ nhạy và assumption_version |

`data_audit.json` dự kiến chứa tổng hợp kiểm tra/lỗi/đối soát, không phát tán ID. `manifest.json` dự kiến ghi hash/kích thước nguồn hiện có, config/mã, Python/thư viện, seed, cutoff, target_definition_version/config_version/assumption_version, trạng thái từng bước. PLAN nói hash ba nguồn gốc; hiện hai nguồn vắng mặt phải ghi thiếu, không lấy hash lịch sử giả làm kết quả đọc tệp. Chi tiết đồng bộ tại [development](development.md#runs).

### Bất biến cần giữ khi triển khai

- Chọn top 10 và mô hình không nhìn test; feature, tỷ trọng 30/90 ngày và tồn đầu chỉ dùng lịch sử tới origin/cutoff. Không dùng actual trung gian tương lai trong horizon.
- Tổng forecast phân bổ chi tiết bằng forecast tuyến; không tự chuyển nước/carrier. Hai cửa sổ 30/90 cùng không có số bán thì ghi thiếu cơ sở, không khuyến nghị tuyến đó.
- Mô phỏng chỉ trừ fulfilled, không tồn âm; không thay sales lịch sử bằng fulfilled để khớp tồn giả định. Trigger strict <, IP tính Q; H phải đủ L+R.
- MAPE chỉ actual>0 nhưng MAE/WAPE/bias trên mọi cặp có nhãn. MAPE toàn 0, WAPE có mẫu số 0 không xác định; thiếu nhãn không chấm. Cùng target_date qua nhiều origin không phải nhiều ngày độc lập.
- Dashboard/báo cáo từ chối trộn run/phiên bản hoặc dùng kết quả hết hiệu lực. Nhãn dự kiến trong tài liệu chỉ được thay bằng đã triển khai sau có sản phẩm/kiểm tra thật.

## Event ledger hiện hành — CHG-016

`inventory_events.csv` là đầu ra private local, chứa order_id phục vụ đối soát; không đưa vào Git, log, tài liệu hoặc export dashboard. Khóa `(scenario_id, date, event_sequence)` liên tục trong ngày. Receipt có order_id trống, timestamp 00:00 UTC và xảy ra trước mọi sale trong ngày. Sale theo order_datetime UTC rồi order_id, cùng dữ liệu audited, không dùng activation. ITEM vẫn là destination_country/carrier/sku/product_type.

Mỗi event có event_type, event_datetime, historical_quantity, scenario_quantity, received_quantity, stock_before, fulfilled, shortage, stock_after, is_simulated và assumption_version. Receipt chỉ cộng lượng nhận; sale đáp ứng min(stock_before, scenario_quantity). Historical quantity không đổi; stress item-day được chia số nguyên bằng largest remainders theo quantity gốc, hòa phần dư theo thứ tự giao dịch. Đây là phân bổ nhu cầu mô phỏng, không suy ra từng đơn thực đã đổi quantity.

Đối soát stock_after=stock_before+received_quantity−fulfilled, scenario_quantity=fulfilled+shortage; stock trước event tiếp theo khớp stock sau event trước cho cùng item/ngày. Tổng event khớp ledger ngày; ngày không event vẫn có opening/closing trong inventory_ledger.csv. Thiếu hoặc trùng giao dịch chặn đối soát thay vì điền 0. Chỉ base có historical_sales=fulfilled+shortage; stress dùng scenario_demand cho đẳng thức này và giữ historical_sales để so sánh.

**Features cohort CHG-017:** First-seen chỉ trong snapshot; source label new/returning giữ ý nghĩa chưa xác nhận. Model không nhận customer_id/order_id. Giá không hợp lệ/invalid money thành missing price feature; validity không nguyên/không hợp lệ thành missing proxy. Không dùng activation và không loại quantity bán hợp lệ vì covariate thiếu. Proxy order_date+validity_days chỉ tính từ đơn đã quan sát tại origin, không nhận là expiry hoặc lịch mua lại thật.

**Hierarchical arrivals CHG-020:** Aggregate order_count là intermediate, không đổi target sales_qty. Phân bổ dựa monthly/recent shares từ ngày đã quan sát, giữ tổng expected arrivals trước positive-day quantity action. Không sử dụng aggregate actual sau origin hoặc claim quantity forecast cộng bằng số đơn. Invalid/missing aggregate counts/actual bị chặn; all-zero không giả tạo demand.

**Chuẩn hóa độc lập CHG-021:** check_data.py dùng nguồn đúng hash của manifest, đối chiếu quantity/order_count từng route-day và top10 train, không sửa nguồn. Train feature export có quantity int64, numeric data_gb/validity/giá/chi phí/revenue, *_valid và revenue_consistent; thiếu/không hợp lệ thành NaN+cờ, không tự đổi target sale. Giữ route/item labels và ý nghĩa plan_type=unlimited chưa có từ điển doanh nghiệp; không suy data_gb là quota tổng của unlimited. CSV feature không có order/customer ID, chỉ train và private local. StandardScaler model fit x tại cutoff; forecast và metric dùng quantity đơn vị gốc.


## Schema giao khách và tồn từ tuần — E37/E39

`delivery_commitments.csv`: ITEM, order_date UTC, delivery_date=order_date+7, commitment_qty nguyên, customer_delay_days=0, is_assumed_delivery=true. `delivery_projection.csv`: ROUTE, as_of_date, order_date=delivery_date−7, delivery_date, delivery_horizon_day 1–21, known_commitment_qty, forecast_from_future_orders_qty, planned_delivery_qty bằng tổng hai phần, basis, actual_delivered_qty thiếu. Đơn ≤origin mới thuộc known; hai phần không gộp thành actual.

`weekly_item_recommendations.csv`: ITEM, origin, partner, on_hand/SS/ROP/S/IP/Q, pending_quantity, eta_if_ordered, depletion_state/date, is_simulated=true, decision_applied=false. Stock/pending là snapshot mô phỏng base v11; vector tuần phân bổ weekday lịch sử rồi item share causal. Strict on_hand<ROP, IP chỉ lượng đặt. Chưa chạy lại lịch sử policy liên tục bằng tuần, không gửi đơn thật. Replay tuần dùng cùng 5.520 cửa sổ, initial stock/actual path/mẫu số của v11; không chọn bỏ ca dưới 7 ngày.

Các protocol/summary có kind, hash nguồn/cha/mã, không được lẫn family. Job giữ last_good_run local, skip khi fingerprint không đổi sau khi kiểm hash run; lỗi không thay run tốt hoặc log nội dung chứa định danh.
