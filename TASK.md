# Điều phối công việc SIGMA

**Cập nhật:** 02/10/2026 (Asia/Saigon). **Căn cứ:** [PLAN 2.0](PLAN.md), [R01–R09](docs/requirements.md), [nhật ký 2.0](docs/review-log.md). T01 đang làm; T02–T14 chưa làm. Sáu tài liệu hỗ trợ đã được tạo, nhưng không thay bằng chứng triển khai hoặc nghiệm thu.

PLAN giữ toàn bộ mục tiêu, công việc, rủi ro, công sức và tiêu chí. Bảng dưới tóm tắt đúng mã/tên/phụ thuộc của PLAN; nhấp ID để đến nhiệm vụ chi tiết. “Chưa có” chỉ sản phẩm trong workspace hiện tại, không suy đoán nội dung các tệp cũ bị xóa. Giới hạn kiểm chứng tại [PROJECTMAP](PROJECTMAP.md#source-gaps).

## Bảng T01–T14

| ID / chi tiết | Tên | Trạng thái | Phụ thuộc | Rxx theo PLAN | Đầu ra chính | Tiêu chí hoàn thành tóm tắt | Bằng chứng hiện có / còn thiếu |
|---|---|---|---|---|---|---|---|
| [T01](PLAN.md#t01) | Chốt và cập nhật yêu cầu | Đang làm | Không | R01–R09 | PLAN, requirements, review-log; CHG-003 và tác động | Truy nguồn/tiêu chí/task; giữ lịch sử, giới hạn và nhãn đề xuất; tài liệu nhất quán | Có ba nguồn 2.0 và sáu tài liệu hỗ trợ; cần rà soát đóng T01. Ảnh/PDF thiếu; không nhận đã đọc lại |
| [T02](PLAN.md#t02) | Môi trường cục bộ và lệnh chạy | Chưa làm | T01 | R09 | Môi trường, phụ thuộc được khóa, CLI/notebook local, hướng dẫn | Môi trường sạch đọc nguồn local; phiên bản ghi lại; demo độc lập; dữ liệu thật không upload | Chưa có requirements, config, CLI, notebook hoặc bằng chứng môi trường sạch; Python khảo sát không thay nghiệm thu |
| [T03](PLAN.md#t03) | Audit và chuẩn hóa số bán | Chưa làm | T02 | R01, R09 | Audit, bảng lỗi/đối soát, dữ liệu processed | Hash nguyên; phân biệt dòng/đơn/quantity; success chưa active vẫn tính; duplicate có log, lỗi target chặn phần ảnh hưởng | Có khảo sát schema/hash trong data-contract; E03/E09 là lịch sử; thiếu pipeline audit và fixture |
| [T04](PLAN.md#t04) | Chuỗi số bán, lịch và EDA | Chưa làm | T03 | R02, R04 | daily_sales, calendar, bảng/hình EDA | Quantity bảo toàn theo A08; lưới 731 ngày/46 tuyến; hình có đơn vị/mẫu số/nguồn | Chưa có chuỗi ngày, lịch lễ hoặc EDA tái lập; không dùng bảng activation thay sản phẩm |
| [T05](PLAN.md#t05) | Top 10 và ba baseline | Chưa làm | T04 | R03–R05 | top_routes, predictions, metrics | Top 10 đúng sales train; baseline tính tay được; cùng cặp origin/horizon; đúng ngày 0/thiếu nhãn; không nhìn test xếp hạng | E09 có top 10 khảo sát lịch sử, cần sinh lại; E06 MA7 activation cần tính lại, không phải kết quả sales |
| [T06](PLAN.md#t06) | MVP xuyên suốt | Chưa làm | T05 | R03, R04, R06–R09 | Forecast → phân bổ → ledger → dashboard; run đầu tiên | Một lệnh tạo đầu ra nhất quán; màn hình khớp CSV; tồn có nhãn; thiếu config báo rõ | Chưa có run tích hợp, ledger hoặc dashboard |
| [T07](PLAN.md#t07) | SARIMA | Chưa làm | T05 | R04, R05 | Validation/predictions của 6 cấu hình top 10, log hội tụ | Cùng cặp origin/horizon; refit 7 ngày; ngoài mẫu; có lý do loại/chọn | Chưa có mô hình, log hội tụ hoặc metric SARIMA sales |
| [T08](PLAN.md#t08) | LightGBM có điều kiện | Chưa làm; có điều kiện | T07 | R04, R05 | Metric 4 cấu hình pooled/direct hoặc biên bản không kích hoạt | Chỉ kích hoạt nếu sau SARIMA còn top 10 chưa đạt validation ≤20%; feature tại origin, nhãn ≤ cutoff; chọn bằng validation | Chưa có validation T07 để xét điều kiện; không ghi “bỏ qua” hay hoàn thành trước khi có căn cứ |
| [T09](PLAN.md#t09) | Khóa và đánh giá M2 | Chưa làm | T06, T07, T08 hoặc biên bản không kích hoạt T08 | R04, R05, R09 | selected_models, test metrics, forecast, bảng đạt/chưa đạt | Đủ 46 tuyến; từng top 10 có MAPE/độ phủ/MAE/WAPE/bias truy về predictions; không chọn lại bằng test | Chưa có lựa chọn được khóa hoặc test sales; không suy ngưỡng 20% từ activation |
| [T10](PLAN.md#t10) | Đối tác, sổ tồn và cảnh báo | Chưa làm | T06 để phát triển; kết quả cuối nhận T09 | R06, R07 | Mapping/config, ledger, recommendations, alerts, simulation_metrics và độ nhạy | Phân bổ/cân bằng tồn; strict <; ngưỡng riêng; ETA/shortage đúng; event duy nhất; replay cảnh báo và chính sách riêng | A09–A16 là đề xuất trong PLAN; chưa có cấu hình/kịch bản hoặc kết quả mô phỏng; không chờ tồn thật |
| [T11](PLAN.md#t11) | Dashboard và cập nhật cục bộ | Chưa làm | T06, T09, T10 | R08, R09 | app.py, bộ lọc/bảng/hình, export và hướng dẫn | Manifest/phiên bản khớp; không trộn run/thật/mô phỏng; phân biệt 0/thiếu/chưa actual | Chưa có app hoặc gói demo; cutoff demo chỉ là thiết kế |
| [T12](PLAN.md#t12) | Kiểm thử, tái lập và bảo mật gói | Chưa làm | T09, T10, T11 | R01, R03–R09 | Tests, checks, run tái lập và kiểm tra gói | Hash nguyên; số nguyên khớp tuyệt đối, số thực theo dung sai ghi trước; input/config/seed tái lập; gói chia sẻ không riêng tư | Chưa có tests/pipeline hoặc môi trường demo kiểm chứng; kiểm tra Markdown không thay T12 |
| [T13](PLAN.md#t13) | Báo cáo, slide và bảo vệ | Chưa làm | T09–T12 | R01–R09 | report.md/PDF, slides, demo-script | Số/hình truy về run; rà RV01–RV16/CHG-003; đúng sales/giả định/giới hạn và bảo mật | Có sổ rà soát lịch sử; PDF nguồn chưa có trong workspace; chưa có báo cáo sửa/slide |
| [T14](PLAN.md#t14) | Nghiệm thu và đóng gói | Chưa làm | T12, T13 | R01–R09 | Ma trận nghiệm thu, biên bản, gói riêng tư hoặc giả, giới hạn | Người khác chạy theo README; demo tái hiện; mỗi yêu cầu có bằng chứng hoặc ghi chưa đạt; không tự công khai | Chưa có sản phẩm kỹ thuật, biên bản nghiệm thu hoặc gói bàn giao |

Các tham chiếu E03/E06/E09 và RVxx nằm trong [review-log](docs/review-log.md#evidence), thuộc bằng chứng lịch sử. Quan hệ Rxx ở bảng giữ nguyên PLAN; các chỗ chưa đối xứng với danh sách task trong requirements được ghi tại [sai khác nguồn](PROJECTMAP.md#source-gaps), không tự hợp nhất hoặc bỏ yêu cầu.

## Bước tiếp theo và thứ tự ưu tiên

1. **T01 — rà soát phần tài liệu:** xác nhận truy vết và giới hạn nguồn đã được phản ánh, kiểm tra bộ Markdown. Đây là nền cho phụ thuộc T02; tạo tài liệu chưa tự đóng T01 hoặc xác nhận A08–A17.
2. **T02 — khi được giao kỹ thuật và T01 đủ bằng chứng:** tạo môi trường/lệnh local trước để T03–T05 có đường tái lập. Không cần chờ dữ liệu doanh nghiệp ngoài order.
3. **T03 → T04 → T05:** audit và chuẩn hóa sales trước khi tạo chuỗi, top 10 và baseline. E06 activation không thay kết quả cần tính lại.
4. Sau T05, phát triển T06 và T07 theo phụ thuộc; xét T08 rồi khóa T09. T10 có thể phát triển sau T06, kết quả cuối nhận T09. T11 → T12 → T13 → T14 theo bảng, không bỏ điều kiện T08 tại T09.

Mốc nguồn giữ nguyên: M1 19/09/2026 đã qua, M2 17/10/2026, M3 07/11/2026. Chưa có bằng chứng nghiệm thu các mốc; quỹ giờ/phân công chưa rõ, không coi ngày kế hoạch là cam kết nguồn lực.

## Đồng bộ và đóng nhiệm vụ

- Giữ hệ trạng thái của PLAN: chưa làm → đang làm → bị chặn / cần kiểm tra lại → hoàn thành; “bị thay thế” giữ lịch sử. Giữ nguyên T01–T14, không thêm bảng task cạnh tranh.
- Khi có thay đổi tiến độ trong phạm vi được giao, cập nhật cả TASK và mục Txx trong PLAN; ghi bằng chứng/quyết định vào review-log. Nếu đổi nghiệm thu, cập nhật requirements; nếu đổi dữ liệu/giao diện, cập nhật data-contract và PROJECTMAP liên quan.
- Một trạng thái hoàn thành cần đầu ra thật và lệnh/ca kiểm tra, kết quả, run/hash/phiên bản phù hợp. Kết quả hết hiệu lực chuyển cần kiểm tra lại. Chưa từng làm không chuyển thành “đã xong, cần sửa”.
- Phân biệt task hoàn thành phần phương pháp với tiêu chí độ chính xác hoặc cảnh báo đạt; không sửa tiêu chí để đóng task. Dùng [checklist và mẫu bàn giao](docs/development.md#done).
- Lượt tạo sáu tài liệu này giữ nguyên ba nguồn 2.0, không nâng trạng thái task. Kiểm tra tài liệu và giới hạn được ghi riêng tại [PROJECTMAP](PROJECTMAP.md#doc-checks).
