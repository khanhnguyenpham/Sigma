# Kế hoạch dự án SIGMA

**Phiên bản:** 2.0 — 02/10/2026 (Asia/Saigon).

**Trạng thái:** Khảo sát đã thực hiện, triển khai chưa bắt đầu. Lượt này chỉ cập nhật ba Markdown; chưa tạo mã, cài thư viện, huấn luyện, mô phỏng hoặc nghiệm thu M1/M2/M3. Chưa có run dự án.

## 1. Cách sử dụng và thay đổi chính

Tài liệu này giữ phương án hiện hành và T01–T14. [Yêu cầu](docs/requirements.md) giữ R01–R09, nguồn và tiêu chí. [Nhật ký](docs/review-log.md) giữ bằng chứng, quyết định cũ và CHG-003. Đường dẫn trong dấu mã là sản phẩm dự kiến, không có nghĩa đã tồn tại.

Phiên bản 2.0 áp dụng xác nhận mentor **do người dùng thuật lại**: M01 về số lượng bán không phụ thuộc active/top 10 theo số bán; M02 về ngưỡng nhập riêng theo đối tác; U04 về chỉ order thực, phần còn lại giả định và bảo mật. Hai ảnh mentor được nhắc đến chưa có tệp để đọc trực tiếp. Thông tin thuật lại đủ để cập nhật; không yêu cầu cung cấp thêm dữ liệu doanh nghiệp. Bộ lọc trạng thái và các con số tồn kho bên dưới vẫn là **đề xuất**, không phải số mentor xác nhận.

Thay target kích hoạt và cách cắt đầu kỳ cũ; thay trigger tồn kho bằng **tồn hiện có < ngưỡng đối tác**; chuyển xử lý dữ liệu thật về môi trường dự án cục bộ theo yêu cầu bảo mật. Giữ cấp tuyến, mã nhiệm vụ, protocol đánh giá, dashboard Windows, mô phỏng có nhãn và mốc đã chốt. Kết quả activation cần tính lại cho mục tiêu mới.

## 2. Mục tiêu, phạm vi và mốc

Dự báo **tổng quantity SIM/gói data bán theo ngày UTC và tuyến `(destination_country, carrier)`**, so sánh baseline, chọn mô hình theo tuyến, rồi mô phỏng tồn kho/cảnh báo theo đối tác. Lượng bán quan sát không đồng nhất với nhu cầu thị trường hoặc nhu cầu mất do hết hàng.

Phạm vi: audit, EDA tuần/tháng/lễ; dự báo 46 tuyến; MAPE ngày dương ≤20% cho **từng tuyến top 10**, kèm độ phủ và MAE/WAPE/bias; mô phỏng nhập hàng và cảnh báo trước ≥7 ngày; dashboard riêng trên Windows; báo cáo, slide và bàn giao tái lập. Không hứa trước đạt độ chính xác.

EOL, chuyển nhu cầu sang SKU/nhà mạng khác, FIFO theo lô, tối ưu chi phí, đặt hàng tự động, API, cơ sở dữ liệu và hosting là mở rộng. Không dùng mô phỏng để tuyên bố hiệu quả vận hành thật.

| Mốc | Ngày | Cách xử lý |
|---|---|---|
| M1 | 19/09/2026 | Đã qua; bù nền tảng, không coi báo cáo cũ là bằng chứng hoàn thành |
| M2 | 17/10/2026 | Giữ mốc; nghiệm thu riêng phương pháp và độ chính xác |
| M3 | 07/11/2026 | Giữ mốc; mô phỏng, dashboard, báo cáo và bàn giao |

Ảnh không ghi năm; năm 2026 theo báo cáo và lựa chọn người dùng. Chưa rõ quỹ giờ/phân công; ước lượng người-giờ không cam kết đủ nhân lực cho thời hạn.

## 3. Đầu vào, phân loại và bảo mật

Đã khảo sát toàn bộ CSV 100.000 dòng/20 cột, đọc ảnh và phần chữ 45 trang PDF, xem sơ đồ trang 12–13. [Sổ bằng chứng](docs/review-log.md#evidence) ghi số liệu, giới hạn, hash. Ba đầu vào gốc giữ nguyên; 26 tệp Git đang bị xóa không tự khôi phục.

| Loại | Nội dung | Cách ghi nhận |
|---|---|---|
| Quan sát | quantity, order_datetime, order_status, tuyến, SKU và các trường order | Nguồn CSV; order thực tế theo người dùng; không suy ra đầy đủ thị trường |
| Dẫn xuất | Ngày UTC, sales_qty, order_count, top 10, lag/rolling, tỷ trọng | Công thức, bộ lọc, cửa sổ/cutoff và target_definition_version |
| Tham chiếu công khai | Lịch lễ/Tết | Nguồn, quốc gia, ngày truy cập; không gửi dữ liệu riêng tư khi tra cứu |
| Giả định | Ánh xạ đối tác, tồn đầu, ngưỡng, lead time, lịch nhập, xử lý thiếu | Mã Axx, phiên bản và trạng thái; tồn đầu sinh từ thống kê order vẫn là giả định |
| Mô phỏng | Sổ tồn, fulfilled, shortage, khuyến nghị, cảnh báo | is_simulated=true, scenario_id, assumption_version; không gọi là tồn thật |
| Dự báo | Lượng bán tương lai do mô hình tạo | Model/run/origin/horizon; actual thiếu để trống, không đổi thành 0 |

Dữ liệu thực duy nhất được cung cấp là order. Tồn/nhập/lead time không phải phụ thuộc chờ doanh nghiệp. Xử lý dữ liệu thật và run riêng tư **cục bộ trong môi trường dự án**. Colab chỉ còn là lựa chọn minh họa với **dữ liệu giả**, không thuộc đường chạy bắt buộc; không tự upload dữ liệu thật hoặc kết quả riêng tư lên dịch vụ ngoài.

CSV gốc đã được Git theo dõi: `.gitignore` không loại dữ liệu khỏi lịch sử Git. Không push/công khai kho hiện tại, không tự viết lại lịch sử hoặc xóa nguồn. Gói chia sẻ về sau theo danh sách cho phép: mã, cấu hình mẫu, hướng dẫn, dữ liệu giả; kiểm tra cả notebook output, run và định danh. Báo cáo chỉ dùng tổng hợp cần thiết; ví dụ dùng dữ liệu giả/ẩn danh phù hợp. Không đưa order/customer ID hoặc dữ liệu bảo mật vào truy vấn ngoài.

### 3.1. Giả định cũ và tình trạng hiện hành

| Mã | Nội dung và trạng thái 2.0 | Hệ quả |
|---|---|---|
| A01 | Activation là target: **bị thay thế** bởi số bán | Kết quả kích hoạt không dùng đánh giá sales |
| A02 | CSV đầy đủ trong phạm vi cung cấp vẫn là giả định; nguồn order thực theo người dùng, trạng thái chỉ là snapshot | Không khẳng định trạng thái cuối đã biết tại origin thật; đổi phạm vi phải tính lại |
| A03 | UTC giữ nguyên vì timestamp có Z | Đổi timezone ảnh hưởng ngày/lịch/split và mọi kết quả phụ thuộc |
| A04 | Kích hoạt tiêu thụ tồn: **bị thay thế** bởi A15 | Tính lại mô phỏng theo giao dịch bán |
| A05 | Không có giao dịch trong ngày quan sát tính 0; không suy ra nhu cầu tiềm ẩn bằng 0 | Nếu phát hiện mất nguồn phải ghi thiếu, không điền 0 |
| A06 | MAPE ngày dương/từng tuyến do người dùng chọn, chưa được mentor xác nhận riêng | Nêu rõ quy ước khi trình bày nghiệm thu |
| A07 | Chỉ có order thực, phần còn lại nhóm giả định: **ràng buộc người dùng xác nhận** | Không yêu cầu thêm dữ liệu nội bộ để triển khai |

### 3.2. Giả định cơ sở đề xuất

A08–A17 đều là **Đề xuất**. Cập nhật tài liệu không biến con số thành “nhóm đã thống nhất” hoặc “mentor xác nhận”. Phương án cơ sở đủ cụ thể để triển khai khi được giao bước kỹ thuật; không chặn kế hoạch vì thiếu dữ liệu ngoài order.

| Mã / thông số | Định nghĩa, đơn vị, phạm vi | Cơ sở đề xuất | Lý do | Độ nhạy / thay thế | Thành phần bị ảnh hưởng | Trạng thái |
|---|---|---|---|---|---|---|
| A08 — Số bán | Đơn vị sản phẩm/ngày đặt/tuyến | Chỉ success; không lọc activation | Quy ước ban đầu dựa trên trạng thái có sẵn | Kịch bản riêng success+refunded, không chọn vì metric dễ đạt | Target/top 10/EDA/mô hình/tồn/báo cáo; T03–T14 | Đề xuất |
| A09 — Đối tác | Proxy theo carrier, ánh xạ có nguồn | Một carrier là một đối tác mô phỏng; Vina → Vinaphone | Không có trường partner, có Vinaphone nhưng không có literal Vina | Thay ánh xạ có phiên bản, không sửa CSV | T06/T10–T14 | Đề xuất |
| A10 — Tồn đầu | Đơn vị/mặt hàng tại cutoff khởi tạo | ceil(7 × bình quân bán/ngày của 28 ngày kết thúc cutoff), đủ ngày 0 | Tái lập theo quy mô bán, không suy ra tồn thật | Cover 3, 7, 14 ngày | Ledger/thiếu/cảnh báo; T06/T10–T14 | Đề xuất |
| A11 — Lead time | Ngày lịch/đối tác | 3 ngày, ghi riêng từng đối tác | Đơn giản; không lấy độ trễ activation làm lead time | 1, 3, 7 ngày | ETA/ROP/S/tồn/cảnh báo; T10–T14 | Đề xuất |
| A12 — Safety-stock days | Ngày/đối tác, tính ngưỡng từng mặt hàng | Vinaphone 4; các đối tác khác 2, phải có bản ghi riêng từng đối tác | Minh họa quy ước riêng; **số do kế hoạch đề xuất** | Nhân cơ sở 0,5; 1; 1,5 | SS/ROP/S/khuyến nghị/mô phỏng; T10–T14 | Đề xuất |
| A13 — Rà soát/MOQ | Ngày, đơn vị/đối tác | R=1, cuối ngày; MOQ=1, ghi từng đối tác | Dễ giải thích, chỉ áp MOQ khi Q>0 | Cho phép sửa từng đối tác rồi kiểm tra lại | Lượng nhập và quyết định đặt; T10–T14 | Đề xuất |
| A14 — Hàng đang về | Số lượng/lô và ETA UTC | Danh sách đầu kỳ rỗng được khai báo rõ; lô mới do chính sách sinh | Không có nhập hàng thật; thiếu tệp không tự bằng danh sách rỗng | Ca hàng về sớm/đúng/muộn | IP/ledger/ngày cạn; T06/T10–T14 | Đề xuất |
| A15 — Thiếu hàng | Đơn vị/giao dịch, không backorder | fulfilled=min(số bán,tồn); shortage=số bán−fulfilled; không tự hoàn nhập refunded | Sổ tồn không âm, giữ yêu cầu bán lịch sử | Đổi quy tắc phải có kịch bản mới | Ledger/thiếu/đánh giá chính sách; T10–T14 | Đề xuất |
| A16 — Phân bổ | Tỷ trọng SKU × product_type trong tuyến | Sales 30 ngày kết thúc origin, tổng 0 dùng 90; cả hai 0 ghi thiếu cơ sở | Không nhìn sang tương lai | Đổi cửa sổ có phiên bản, kiểm tra bảo toàn | Forecast chi tiết/tồn/cảnh báo; T06/T10–T14 | Đề xuất |
| A17 — Seed | Số nguyên, thành phần ngẫu nhiên | 42; mô phỏng cơ sở xác định | Tái lập mô hình/dữ liệu giả | Đổi seed ghi manifest | Thành phần ngẫu nhiên; T02/T08/T12 | Đề xuất |

Cấu hình tập trung dự kiến `config.json`: target/status, UTC, split, horizon, mô hình, seed, bảng ánh xạ, **đầy đủ từng đối tác**, cách sinh tồn đầu và phiên bản. Thiếu đối tác báo `missing_partner_config`, không lấy ngưỡng chung hoặc 0 thay thế.

## 4. Thiết kế pipeline và bộ tệp

**Order bảo toàn → audit → chuỗi số bán → EDA/lịch → baseline/backtest → chọn bằng validation → test → forecast → phân bổ → mô phỏng từng kịch bản → dashboard/báo cáo.** Ảnh/PDF là nguồn yêu cầu và đối chiếu, không là nguồn tồn kho.

Python local; pandas/numpy xử lý, statsmodels SARIMA, matplotlib hình, Streamlit dashboard; LightGBM có điều kiện. Notebook/CLI dùng cùng mã nguồn. Khóa phụ thuộc sau kiểm tra tương thích thực, không nhận đã kiểm chứng ngay trong kế hoạch.

### 4.1. Cấu trúc dự kiến

```text
Sim-Demand-Forecasting/
├── PLAN.md
├── README.md                         # Soạn mới khi triển khai
├── config.json
├── requirements.txt                 # Huấn luyện cục bộ
├── requirements-demo.txt
├── run.py
├── app.py
├── data/
│   ├── sigma_sim_data_orders.csv     # Gốc, riêng tư, giữ nguyên
│   ├── reference/holidays.csv
│   ├── scenarios/
│   │   ├── partner_map.csv           # Ánh xạ giả định
│   │   ├── inventory.csv             # Snapshot mô phỏng
│   │   └── receipts.csv              # Lượng và ETA giả định
│   └── processed/daily_sales.csv
├── docs/
│   ├── PROJECT_REQUIREMENTS.png      # Gốc, giữ nguyên
│   ├── Báo cáo chi tiết Sigma.pdf    # Gốc, giữ nguyên
│   ├── requirements.md
│   └── review-log.md
├── notebooks/run_local.ipynb
├── src/
│   ├── data.py
│   ├── models.py
│   ├── evaluation.py
│   ├── inventory.py
│   └── reporting.py
├── tests/
│   ├── test_data.py
│   ├── test_forecasting.py
│   └── test_inventory.py
├── outputs/<run_id>/                 # Riêng tư
│   ├── manifest.json
│   ├── data_audit.json
│   ├── top_routes.csv
│   ├── predictions.csv
│   ├── metrics.csv
│   ├── selected_models.csv
│   ├── inventory_ledger.csv
│   ├── inventory_recommendations.csv
│   ├── alerts.csv
│   ├── simulation_metrics.csv
│   ├── figures/
│   └── checks.txt
└── reports/
    ├── report.md
    ├── report.pdf
    ├── slides.pptx
    └── demo-script.md
```

Chỉ ba Markdown điều phối được cập nhật lúc này; tệp mới khác chưa tạo. `requirements.txt`/`run_local.ipynb` thay phương án `requirements-colab.txt`/`colab_run.ipynb` của 1.0. Không khôi phục README hoặc tệp cũ.

### 4.2. Giao diện và truy vết

| Thành phần | Giao diện dự kiến |
|---|---|
| CLI | `python run.py --config config.json --stage audit\|backtest\|forecast\|inventory\|report\|all`; chọn một stage |
| Chuỗi ngày | Ngày UTC, tuyến, sales_qty, order_count, target_definition_version; phân biệt dòng/đơn/quantity |
| Forecast | run_id, as_of_date, tuyến, forecast_date, horizon_day, model, forecast_qty; actual_qty/split khi có nhãn |
| Partner map | carrier, partner_id, alias, nguồn/giả định, assumption_version; không gọi Vina→Vinaphone là đã xác minh |
| Ledger | scenario_id, thời gian/ngày, khóa mặt hàng, opening, receipts, historical_sales, fulfilled, shortage, closing, is_simulated |
| Khuyến nghị | Đối tác/mặt hàng, on_hand, SS, ROP, S, IP, Q, ETA, trạng thái thiếu cấu hình, is_simulated |
| Cảnh báo | Loại, origin, ngày cạn dự kiến/thực trong mô phỏng, lead time cảnh báo, event_id/scenario_id, is_simulated |
| Manifest | Hash/kích thước ba nguồn, config/mã, Python/thư viện, seed, cutoff, target_definition_version/config_version/assumption_version, trạng thái từng bước |
| Gói demo | Một run hoàn tất, manifest khớp mọi bảng/phiên bản; không cần mô hình nhị phân/huấn luyện lại |

Đầu ra dẫn xuất truy về phiên bản target; tồn thêm phiên bản giả định. Dashboard từ chối run thiếu/hết hiệu lực hoặc trộn phiên bản. Gói riêng tư và gói dữ liệu giả được kiểm tra theo mục đích chia sẻ.

## 5. Số bán và phương pháp dự báo

### 5.1. Định nghĩa cơ sở và làm sạch

```text
sales_qty[UTC_date(order_datetime), destination_country, carrier]
  = sum(quantity của dòng order_status == "success")
```

Đây là **A08 đề xuất**, không phải bộ lọc mentor xác nhận. Quantity là sản phẩm; order_count là số order_id hợp lệ khác nhau; số dòng chỉ là thống kê cấu trúc. Tuyến vẫn quốc gia/điểm đến–nhà mạng, 46 cặp; Europe (EU) là nhóm điểm đến.

| Trường hợp | Xử lý cơ sở |
|---|---|
| success | Tính quantity tại order_datetime, kể cả chưa có/activation muộn |
| refunded | Loại cơ sở; kịch bản định nghĩa riêng success+refunded |
| failed / timeout / pending | Không tính vào sales cơ sở |
| Hủy/hoàn một phần/hoàn nhập | Không đủ trường xác định; không bịa canceled, ngày hoàn, quantity âm hoặc nhập lại kho |
| Trùng order_id, nội dung giống | Giữ một bản trong processed, ghi log/đối soát; giữ gốc |
| Trùng order_id, nội dung mâu thuẫn | Cách ly/chặn target bị ảnh hưởng đến khi giải quyết |
| Nội dung giống, ID khác | Không tự loại là trùng giao dịch |
| Quantity không nguyên dương | Ghi lỗi/chặn target bị ảnh hưởng; 1–4 chỉ là phạm vi quan sát, không là cap tương lai |
| Activation thiếu/sai | Audit riêng; không loại giao dịch bán hợp lệ vì activation |

Không có ngày hoàn tiền, lượng hoàn một phần hay lịch sử trạng thái. Không gọi cơ sở success là định nghĩa kế toán số bán thuần đã xác nhận. Đây là nhãn **snapshot hồi cứu**, không chứng minh success cuối cùng đã biết tại origin vận hành thật.

Khoảng mô hình **01/01/2024–31/12/2025, 731 ngày UTC**; bỏ cắt 16/01 của target activation cũ. Tạo lưới ngày–tuyến, điền 0 trong phạm vi giả định quan sát, đối soát quantity. Không xóa ngày 0, loại đỉnh hoặc winsorize để giảm MAPE. Activation tháng 01/2026 không là nhãn sales; nguồn không có order tháng đó.

### 5.2. Thời gian và chống rò rỉ

| Phần | Ngày mục tiêu | Mục đích |
|---|---|---|
| Train ban đầu | 01/01/2024–30/06/2025 | Top 10, fit ban đầu |
| Validation | 01/07/2025–30/09/2025 | Chọn mô hình/cấu hình |
| Test cuối | 01/10/2025–31/12/2025 | Đánh giá sau khóa lựa chọn |

Top 10 theo **tổng quantity bán train**, hòa điểm theo tên tuyến, cố định. Bảng khảo sát sales trong nhật ký chỉ để đối soát; T05 phải sinh lại bằng pipeline. Không dùng tổng toàn kỳ, doanh thu, activation hoặc số đơn để xếp hạng.

Origin hằng ngày sau chốt ngày; dự báo từ hôm sau, H=14. Chỉ chấm target thuộc split và có nhãn; mọi mô hình cùng cặp origin–horizon hợp lệ. M2 chính h1–7, h8–14 riêng. Refit mỗi 7 ngày, cập nhật actual đã qua giữa các lần fit; cùng quy tắc trên validation/test/dự báo. Không dùng metric test chọn lại mô hình; cập nhật actual theo lịch không cho phép đổi lựa chọn đã khóa.

Feature dùng sales lag/rolling tại origin, tuyến/horizon và lịch biết trước. Không dùng activation, trạng thái cuối đơn tương lai, doanh thu ngày dự báo, actual trung gian trong horizon, tỷ trọng toàn kỳ hoặc cờ bất thường biết từ tương lai. Mẫu huấn luyện nhiều horizon chỉ có nhãn với target_date≤cutoff fit. Chống nhìn trước theo ngày không xóa giới hạn snapshot trạng thái; không tuyên bố tái dựng chắc chắn thông tin thời gian thực.

Lịch lễ có nguồn công khai/quốc gia/ngày truy cập. “Mùa hè” là giả thuyết; hình/bảng có đơn vị/mẫu số, không kết luận nhân quả hay mùa du lịch chung cho mọi tuyến.

### 5.3. Ứng viên và chọn mô hình

1. Naive lặp giá trị cuối; MA7 giữ trung bình 7 ngày cuối cho cả horizon; seasonal naive 7 lặp tuần quan sát cuối. Chạy 46 tuyến.
2. SARIMA top 10: 6 cấu hình tích order={(1,0,0),(1,1,1)} và seasonal_order={(0,0,0,7),(1,0,0,7),(0,1,1,7)}. Có hằng số khi không sai phân. Ghi cảnh báo/lỗi; không hội tụ loại khỏi lựa chọn, không bỏ riêng dự báo xấu để chấm thuận lợi.
3. Nếu sau SARIMA còn bất kỳ top 10 không đạt MAPE validation≤20%, thử LightGBM pooled/direct nhiều horizon: 4 cấu hình num_leaves 15/31 × min_data_in_leaf 20/50, Poisson, 300 vòng, learning rate 0,05, seed 42. Không kích hoạt thì T08 có biên bản lý do.
4. Top 10: trong mô hình đạt ≤20% validation chọn MAE mọi ngày thấp nhất; không có thì chọn MAPE ngày dương thấp nhất rồi MAE, ghi **chưa đạt mục tiêu**. Các tuyến khác chọn baseline MAE thấp nhất. Tương đương số học ưu tiên đơn giản, ghi dung sai trước đánh giá.

Forecast âm chặn 0, đếm lần chặn; không làm tròn trước chấm. Không đổi success/refunded, top 10 hoặc tập ngày nhằm đạt 20%.

### 5.4. Metric và giới hạn

MAPE ngày dương = 100×mean(abs(actual−forecast)/actual), chỉ actual>0; kèm số cặp dương/tổng có nhãn và độ phủ. MAE=mean(abs(error)); WAPE=100×sum(abs(error))/sum(actual); bias=mean(forecast−actual), trên mọi cặp có nhãn. Báo theo tuyến/horizon và nhóm horizon; nhiều origin cùng target_date không là các ngày độc lập.

Toàn bộ actual=0: MAPE/WAPE không xác định, báo MAE/số ngày 0; không trả 0% giả. Thiếu actual không chấm, công khai số mẫu thiếu. Chỉ đạt độ chính xác khi **cả 10 tuyến** đạt ≤20% test chính h1–7, có độ phủ và metric mọi ngày.

MA7 45,8%–72,5% khảo sát cũ dùng activation: **cần tính lại cho sales**, không phải nghiệm thu M2 hoặc bằng chứng chất lượng dự báo số bán. Sau khi xem test, sửa mô hình phải ghi test đã được sử dụng; không gọi cùng tập đó là kiểm định độc lập.

## 6. Mô phỏng tồn kho và cảnh báo

### 6.1. Khóa, phân bổ và ngưỡng riêng

Khóa mặt hàng `(destination_country, carrier, SKU, product_type)`; region chỉ là địa lý. Carrier làm proxy đối tác A09; Vina→Vinaphone là ánh xạ giả định, không phải quan hệ mentor đã xác nhận.

Phân bổ forecast tuyến bằng sales 30 ngày kết thúc origin; tổng 0 dùng 90 ngày; cả hai 0 ghi thiếu cơ sở và không khuyến nghị tuyến đó. Tổng chi tiết bằng forecast tuyến; không tự chuyển sang nước/nhà mạng khác. Thiếu snapshot khác tồn 0; thiếu danh sách hàng về khác danh sách rỗng đã khai báo.

Mỗi đối tác có L (lead time), R (review period), b (safety days), MOQ riêng. Cùng công thức nhưng tham số từng đối tác/mặt hàng:

```text
SS  = ceil(b × mean(forecast[1..H]))
ROP = ceil(sum(forecast[1..L]) + SS)
S   = ceil(sum(forecast[1..L+R]) + SS)
IP  = closing_on_hand + toàn bộ số lượng đã đặt chưa nhận
needs_replenishment = closing_on_hand < ROP
Q = ceil(max(0, S - IP)) nếu needs_replenishment, ngược lại Q = 0
Nếu Q > 0: Q = max(Q, MOQ)
```

Nếu H<L+R, yêu cầu tăng horizon; không kéo dài ngầm. **Trigger dùng tồn hiện có, không dùng IP hoặc ≤.** Hàng đang về dùng tính Q nhưng chỉ tăng tồn khi tới ETA. Cảnh báo tồn thấp có thể còn khi Q=0 do đặt đủ; hiển thị “đã có hàng đang về”, tránh đặt trùng.

Ví dụ giả định: forecast 10 đơn vị/ngày, L=3; Vinaphone b=4 cho SS=40, ROP=70; đối tác b=2 cho SS=20, ROP=50. Cùng tồn 60, một bên cảnh báo, bên kia không. **Các số không do mentor cung cấp.** Phải ghi bản cấu hình từng đối tác, không mặc định khi thiếu.

### 6.2. Trình tự sổ tồn và thiếu hụt

1. Lấy tồn đầu ngày; cộng lô đến hạn vào đầu ngày UTC theo ETA.
2. Xử lý bán hợp lệ theo order_datetime; hòa timestamp theo order_id.
3. Mỗi giao dịch: fulfilled=min(quantity,tồn), shortage=quantity−fulfilled; chỉ trừ fulfilled. Không backorder/tự hoàn nhập refunded.
4. Chốt tồn cuối; tạo forecast/ngưỡng/quyết định đặt sau chốt ngày, dùng thông tin đến ngày đó.
5. Đơn nhập mới cuối ngày có ETA sau L ngày lịch; không cộng lùi vào đầu ngày vừa chốt. Hàng muộn không xóa cảnh báo trước ETA.

Đối soát `closing = opening + receipts − fulfilled` và `historical_sales = fulfilled + shortage`. Không sửa sales gốc/target hoặc thay bằng fulfilled để khớp tồn giả định.

Phân biệt `0 < on_hand < ROP` (còn hàng, cần nhập), `on_hand=0` (hết hàng), `shortage>0` (có yêu cầu không đáp ứng). Tồn 0 không tự chứng minh mất nhu cầu khi chưa có giao dịch. Mô phỏng dùng số bán lịch sử như yêu cầu cần đáp ứng trong kịch bản, không tái dựng tồn thật hay đo nhu cầu thị trường đã mất.

### 6.3. Cảnh báo và đánh giá

Dưới ROP và ngày cạn dự kiến là hai loại cảnh báo khác nhau. Chiếu tồn bằng forecast/ETA: lần đầu về 0 trong 1–6 ngày là khẩn/muộn, 7–14 ngày là sớm; không cạn trong H ghi “chưa thấy cạn trong 14 ngày”. Đã tồn 0 tại origin là sự kiện hiện hữu, không tính là cảnh báo sớm cho sự kiện tương lai.

Đánh giá cảnh báo bằng **đợt 14 ngày không chồng lấn**, origin đầu 30/09/2025, tăng 14 ngày, chỉ lấy đợt có đủ nhãn đến 31/12/2025. Khởi tạo mỗi đợt từ lịch sử đến origin; không đặt hàng mới sau cảnh báo, vẫn nhận lô đã khai báo trước origin theo ETA. Mỗi mặt hàng/đợt chỉ chấm sự kiện cạn đầu tiên với event_id duy nhất; ngày cạn là ngày tồn lần đầu về 0, tách lượng thiếu chưa đáp ứng.

Tại origin đợt, dự đoán có/không cạn và ngày cạn; so với đường tồn dùng sales thực cùng đợt để tính TP/FP/FN, precision, recall, tỷ lệ sự kiện báo trước ≥7 ngày, số cảnh báo muộn, sai số ngày cạn trên ca ghép được. Công khai mẫu số/ca bị loại; không có sự kiện/cảnh báo thì tỷ lệ tương ứng không xác định. Đợt độc lập không đại diện chính sách vận hành liên tục.

Đánh giá chính sách bổ sung hàng bằng lượt riêng liên tục 01/10–31/12/2025, có đặt mới/ETA, khởi tạo từ lịch sử trước kỳ. Báo thiếu hụt, tỷ lệ đáp ứng, tồn bình quân cuối ngày. Không coi cảnh báo được đặt hàng ngăn cạn là báo sai.

Độ nhạy thay từng trục, giữ trục khác cơ sở: tồn đầu cover {3,7,14}, lead time {1,3,7}, safety-days multiplier {0,5;1;1,5}. Báo kết luận có đảo chiều không. Không tự đặt ngưỡng precision/recall chính thức hoặc bảo đảm mọi ca đều báo trước 7 ngày.

## 7. Nhiệm vụ, phụ thuộc và công sức

Trạng thái: chưa làm → đang làm → bị chặn / cần kiểm tra lại → hoàn thành; “bị thay thế” giữ lịch sử. T01 đang làm ở mức tài liệu; T02–T14 chưa làm. Kết quả khảo sát cũ cần tính lại không có nghĩa task kỹ thuật đã hoàn thành.

### Giai đoạn 1 — Bù M1

<a id="t01"></a>
### T01 — Chốt và cập nhật yêu cầu

- **Trạng thái:** Đang làm — cập nhật tài liệu 2.0, chưa nghiệm thu kỹ thuật.
- **Mục tiêu/yêu cầu:** R01–R09; số bán, nguồn mentor thuật lại và giả định.
- **Đầu vào/công việc/đầu ra:** Ba nguồn/xác nhận mới → CHG-003 và tác động → PLAN, requirements, review-log.
- **Phụ thuộc:** Không.
- **Kiểm tra/hoàn thành:** Nguồn/tiêu chí/task/sản phẩm truy được; tham số không gán cho mentor; ba tài liệu nhất quán và giữ lịch sử/giới hạn.
- **Rủi ro/xử lý:** Đổi định nghĩa/giả định → tăng phiên bản, vô hiệu hóa phụ thuộc.
- **Công sức:** 4–6 người-giờ.

<a id="t02"></a>
### T02 — Môi trường cục bộ và lệnh chạy

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R09; xử lý riêng tư, notebook/CLI cùng mã.
- **Đầu vào/công việc/đầu ra:** T01 → local environment, kiểm tra/khóa phụ thuộc, CLI/notebook → requirements, run.py, run_local.ipynb, hướng dẫn.
- **Phụ thuộc:** T01.
- **Kiểm tra/hoàn thành:** Môi trường sạch đọc nguồn local; ghi phiên bản; demo độc lập; không upload dữ liệu thật. Colab nếu có chỉ dùng giả.
- **Rủi ro/xử lý:** Chưa rõ tài nguyên máy → đo khi triển khai, không hứa hiệu năng; kiểm soát gói vì CSV đã tracked.
- **Công sức:** 4–6 người-giờ.

<a id="t03"></a>
### T03 — Audit và chuẩn hóa số bán

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R01, R09.
- **Đầu vào/công việc/đầu ra:** CSV/config → audit schema/thời gian/quantity/trạng thái/trùng/activation riêng → audit, bảng lỗi, processed.
- **Phụ thuộc:** T02.
- **Kiểm tra/hoàn thành:** Hash giữ nguyên; đối soát dòng/đơn/quantity; bán chưa active vẫn tính; duplicate có log; lỗi target chặn phụ thuộc.
- **Rủi ro/xử lý:** Snapshot không tái dựng live → ghi giới hạn, không bịa lịch sử hoặc xin thêm dữ liệu nội bộ.
- **Công sức:** 6–10 người-giờ.

<a id="t04"></a>
### T04 — Chuỗi số bán, lịch và EDA

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R02, R04.
- **Đầu vào/công việc/đầu ra:** T03/lịch công khai → 731 ngày/46 tuyến và EDA → daily_sales, calendar, bảng/hình.
- **Phụ thuộc:** T03.
- **Kiểm tra/hoàn thành:** Quantity bảo toàn theo A08, kích thước từ lịch, hình có đơn vị/mẫu số/nguồn; không activation target.
- **Rủi ro/xử lý:** Ít quan sát lễ → giới hạn diễn giải, không kết luận nhân quả; lịch không cần dữ liệu nội bộ.
- **Công sức:** 8–12 người-giờ.

<a id="t05"></a>
### T05 — Top 10 và ba baseline

- **Trạng thái:** Chưa làm; MA7 activation cần tính lại, không thay task.
- **Mục tiêu/yêu cầu:** R03–R05.
- **Đầu vào/công việc/đầu ra:** Sales/protocol → top 10 train, rolling origin/metric → top_routes, predictions, metrics.
- **Phụ thuộc:** T04.
- **Kiểm tra/hoàn thành:** Top 10 khớp tổng train; ví dụ tính tay/origin; cùng cặp chấm; ngày 0/thiếu nhãn đúng; không nhìn test xếp hạng.
- **Rủi ro/xử lý:** MAPE cao → ghi thực nghiệm, giữ tiêu chí/định nghĩa.
- **Công sức:** 8–12 người-giờ.

### Giai đoạn 2 — Xuyên suốt và M2, hạn 17/10/2026

<a id="t06"></a>
### T06 — MVP xuyên suốt

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R03, R04, R06–R09.
- **Đầu vào/công việc/đầu ra:** Baseline/cấu hình nhỏ → forecast/phân bổ/ledger/dashboard → run đầu tiên.
- **Phụ thuộc:** T05.
- **Kiểm tra/hoàn thành:** Một lệnh tạo đầu ra nhất quán, màn hình khớp CSV, tồn có nhãn, thiếu cấu hình không bị lấp ngầm.
- **Rủi ro/xử lý:** Sai khóa/đơn vị → sửa giao diện trước mở rộng mô hình.
- **Công sức:** 6–10 người-giờ.

<a id="t07"></a>
### T07 — SARIMA

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R04, R05.
- **Đầu vào/công việc/đầu ra:** Sales/evaluator → 6 cấu hình top 10 → validation/predictions/log hội tụ.
- **Phụ thuộc:** T05.
- **Kiểm tra/hoàn thành:** Cùng cặp origin/horizon, refit 7 ngày, ngoài mẫu; lý do loại/chọn.
- **Rủi ro/xử lý:** Chậm/không hội tụ → ghi thất bại, giữ baseline; không lọc ngày khó.
- **Công sức:** 10–16 người-giờ.

<a id="t08"></a>
### T08 — LightGBM có điều kiện

- **Trạng thái:** Chưa làm; chỉ kích hoạt theo mục 5.3.
- **Mục tiêu/yêu cầu:** R04, R05.
- **Đầu vào/công việc/đầu ra:** Validation T07 → 4 cấu hình pooled/direct → metric hoặc biên bản không kích hoạt.
- **Phụ thuộc:** T07.
- **Kiểm tra/hoàn thành:** Feature tại origin, nhãn≤cutoff, không activation/future actual; chọn bằng validation.
- **Rủi ro/xử lý:** Overfit/không cải thiện → giữ đơn giản, không tìm kiếm vô hạn.
- **Công sức:** 8–14 người-giờ nếu kích hoạt.

<a id="t09"></a>
### T09 — Khóa và đánh giá M2

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R04, R05, R09.
- **Đầu vào/công việc/đầu ra:** T07/T08/MVP → khóa, test cuối, forecast → selected_models, test metrics, đạt/chưa đạt.
- **Phụ thuộc:** T06, T07, T08 hoặc biên bản không kích hoạt T08.
- **Kiểm tra/hoàn thành:** Đủ 46 tuyến; từng top 10 có MAPE/độ phủ/MAE/WAPE/bias truy về predictions; không chọn lại bằng test.
- **Rủi ro/xử lý:** Test không đạt → “M2 còn tiêu chí chưa đạt”; sửa sau test phải phiên bản mới và công khai đã xem test.
- **Công sức:** 4–6 người-giờ.

### Giai đoạn 3 — Tồn kho và dashboard M3

<a id="t10"></a>
### T10 — Đối tác, sổ tồn và cảnh báo

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R06, R07.
- **Đầu vào/công việc/đầu ra:** Sales/forecast/A09–A16 → mapping/tham số riêng/ledger/ETA/strict threshold/replay/độ nhạy → recommendations, alerts, simulation_metrics.
- **Phụ thuộc:** T06 để phát triển; kết quả cuối nhận T09.
- **Kiểm tra/hoàn thành:** Bảo toàn phân bổ/cân bằng tồn/thiếu; dưới/bằng/trên ngưỡng; cùng tồn khác cảnh báo theo đối tác; không trùng event; tách no-new-order và policy replay.
- **Rủi ro/xử lý:** Kết luận nhạy giả định → trình bày trường hợp đảo chiều, không gán tham số cho mentor hoặc chờ tồn thật.
- **Công sức:** 16–24 người-giờ.

<a id="t11"></a>
### T11 — Dashboard và cập nhật cục bộ

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R08, R09.
- **Đầu vào/công việc/đầu ra:** T09/T10 → bộ lọc, actual/forecast, metric, bảng giả định, tồn/cảnh báo, export kiểm soát → app.py/hướng dẫn.
- **Phụ thuộc:** T06, T09, T10.
- **Kiểm tra/hoàn thành:** Manifest/phiên bản đúng; CSV khớp màn hình; không trộn run/thật/mô phỏng; phân biệt 0/thiếu/chưa có actual.
- **Rủi ro/xử lý:** Nhầm hiện thời → luôn hiện cutoff/thời điểm chạy; demo 31/10/2025, latest cutoff 31/12/2025 dự báo 01–14/01/2026 chưa có actual order.
- **Công sức:** 8–12 người-giờ.

### Giai đoạn 4 — Kiểm tra và bàn giao trước 07/11/2026

<a id="t12"></a>
### T12 — Kiểm thử, tái lập và bảo mật gói

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R01, R03–R09.
- **Đầu vào/công việc/đầu ra:** Pipeline → ca mục 8/môi trường local sạch/kiểm tra gói → tests, checks, run tái lập.
- **Phụ thuộc:** T09, T10, T11.
- **Kiểm tra/hoàn thành:** Hash nguồn nguyên; số nguyên khớp tuyệt đối, số thực theo dung sai ghi trước; cùng config/seed tái lập; gói chia sẻ không raw/ID/notebook output riêng tư.
- **Rủi ro/xử lý:** Lệch môi trường → tìm nguyên nhân/khóa phụ thuộc, không coi runtime khảo sát là môi trường bàn giao.
- **Công sức:** 10–14 người-giờ.

<a id="t13"></a>
### T13 — Báo cáo, slide và bảo vệ

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R01–R09.
- **Đầu vào/công việc/đầu ra:** Run kiểm tra/review-log → viết sales/phương pháp/kết quả/giả định/độ nhạy/giới hạn → report.md/pdf, slides, demo-script.
- **Phụ thuộc:** T09–T12.
- **Kiểm tra/hoàn thành:** Số/hình truy về run/định nghĩa; rà RV01–RV16/CHG-003; không gọi activation MA7 là sales; minh họa đúng bảo mật.
- **Rủi ro/xử lý:** Sót kết luận cũ → thay hoặc gắn nhãn lịch sử, giữ PDF nguồn.
- **Công sức:** 10–16 người-giờ.

<a id="t14"></a>
### T14 — Nghiệm thu và đóng gói

- **Trạng thái:** Chưa làm.
- **Mục tiêu/yêu cầu:** R01–R09.
- **Đầu vào/công việc/đầu ra:** Sản phẩm/kiểm tra/báo cáo → ma trận/diễn tập máy khác/gói phù hợp quyền → biên bản, gói riêng tư hoặc giả, giới hạn.
- **Phụ thuộc:** T12, T13.
- **Kiểm tra/hoàn thành:** Người khác chạy theo README trong môi trường được phép; demo tái hiện; mọi yêu cầu có bằng chứng hoặc chưa đạt; không tự đăng công khai.
- **Rủi ro/xử lý:** Đổi sát hạn → đánh giá tác động/kiểm tra lại, không đánh dấu hoàn thành với bằng chứng hết hiệu lực.
- **Công sức:** 3–5 người-giờ.

**Tổng:** 97–149 người-giờ chưa gồm T08; 105–163 nếu kích hoạt T08. T10 tăng 4–6 và T12 tăng 2 người-giờ ở cả hai cận so với 1.0, cho chính sách đối tác, sổ giao dịch, độ nhạy và bảo mật; chưa gồm chờ phản hồi/thời gian máy chạy.

## 8. Kiểm thử và bàn giao

Các ca bắt buộc khi triển khai:

- **Sales:** UTC, 29/02/2024, order timestamp thiếu/sai, quantity>1, trạng thái/refunded, duplicate giống/mâu thuẫn. Fixture success chưa active (CSV chưa có ca này); activation muộn vẫn tính ngày đặt. Sửa activation không đổi sales/feature/top 10/tiêu thụ mô phỏng.
- **Thời gian:** Sửa sau origin không đổi forecast tại origin; thay test không đổi top 10 train/tỷ trọng; nhiều bước không lấy actual tương lai; nhãn LightGBM≤cutoff. Ghi riêng giới hạn snapshot.
- **Metric:** Actual 0/toàn 0/forecast 0/không nhãn; nhiều origin cùng ngày; ví dụ tính tay và đủ mẫu số.
- **Đối tác:** Cùng forecast/tồn khác cảnh báo do cấu hình; ROP−1, ROP, ROP+1; thiếu cấu hình báo rõ; không nhầm hết hàng/còn tồn thấp/thiếu hụt giao dịch.
- **Tồn:** Phân bổ bảo toàn; thiếu snapshot khác 0; ETA sớm/đúng/muộn; không MOQ khi Q=0; forecast 0 không chia 0; cân bằng ledger và historical_sales=fulfilled+shortage; giữ sales lịch sử.
- **Cảnh báo:** Cạn ngày 10 báo đủ ≥7, ngày 3 là muộn; không bịa ngoài horizon; event duy nhất; replay cảnh báo và policy riêng; không có sự kiện ghi mẫu số đúng.
- **Tích hợp:** Không trộn run/phiên bản; thiếu gói rõ; input/config/seed tái lập; đổi A12 tính lại tồn/cảnh báo, không cần fit forecast; đổi A08 tính lại target và mọi phụ thuộc.
- **Bảo mật:** Gói chia sẻ theo allowlist, không raw CSV/ID/notebook output thật/lịch sử Git chứa nguồn; run thật ở local.

Bàn giao gồm ba nguồn có hash; ba tài liệu điều phối; mã/config/phụ thuộc/notebook local; dữ liệu dẫn xuất/lịch; predictions/metrics/top 10/selection; kịch bản/ledger/khuyến nghị/cảnh báo/độ nhạy; dashboard; báo cáo nguồn/PDF/slide; hướng dẫn chạy/cập nhật/test; biên bản và tiêu chí chưa đạt. Dữ liệu thật chỉ trong phạm vi riêng tư được phép, không dùng “bàn giao” làm quyền upload.

Hoàn thành đòi hỏi từng yêu cầu bắt buộc có bằng chứng, tái lập được, báo cáo khớp mã/run, đánh giá đúng quy ước, nhóm giải thích được target/snapshot/ngày 0/split/mô hình/giả định/thay đổi. Chương trình chạy không tự chứng minh MAPE/cảnh báo đạt. Nếu còn thiếu tiêu chí, ghi **“đã bàn giao sản phẩm; còn tiêu chí chưa đạt”**.

## 9. Quản lý thay đổi và bước tiếp theo

Ghi nguồn/ngày/mã → xác định R/A/T/đầu ra ảnh hưởng → sửa kế hoạch/config/tăng phiên bản → đánh dấu kết quả cũ cần tính lại → kiểm tra liên quan trước hoàn thành. [Nhật ký](docs/review-log.md#change-process) giữ ma trận/quy trình; không xóa mã T01–T14 hoặc lịch sử.

**Hiện tại:** chỉ cập nhật/kiểm tra ba Markdown. Không có câu hỏi nghiệp vụ bắt buộc để hoàn tất bước này; phần ngoài order đã có giả định cơ sở. A08–A17 chờ nhóm xem xét, không yêu cầu xin dữ liệu doanh nghiệp. R05/R07 chưa có bằng chứng nghiệm thu; quỹ giờ chưa biết.

**Bước kỹ thuật tiếp theo khi được giao:** T02 local, rồi T03/T04/T05 theo sales 2.0; chưa thực hiện trong lượt này. Khi tiếp tục chat khác, đọc ba tài liệu, Git, config/manifest thực tế nếu có; không suy ra tiến độ từ cây tệp dự kiến.

## 10. Lịch sử phiên bản

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 1.0 | 02/10/2026 | Activation, Colab, chính sách tồn chung; chỉ lập tài liệu. Quyết định/bằng chứng lịch sử giữ ở review-log |
| 2.0 | 02/10/2026 | CHG-003: sales, top 10 theo train, ngưỡng đối tác/strict <, A08–A17, chỉ order thực và xử lý cục bộ/bảo mật; giữ mã task/mốc, chưa triển khai |
