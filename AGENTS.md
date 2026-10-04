# Hướng dẫn làm việc với SIGMA

Áp dụng trong project này. Bộ hướng dẫn ngày 02/10/2026 dựa trên PLAN và yêu cầu phiên bản 2.0; phạm vi hành động theo yêu cầu người dùng ở mỗi lượt.

## Mục tiêu và ràng buộc

- Dự báo tổng `quantity` bán theo ngày UTC và tuyến `(destination_country, carrier)`. `success` theo `order_datetime` là **A08 đề xuất**, không phải quy tắc kế toán hoặc bộ lọc mentor xác nhận. Không dùng activation làm target hay điều kiện loại sale hợp lệ.
- Top 10 theo quantity bán **train**; train 01/01/2024–30/06/2025, validation 01/07/2025–30/09/2025, test 01/10/2025–31/12/2025. Horizon 14 ngày, đánh giá chính h1–7; h8–14 riêng. Không dùng tương lai để tạo feature, phân bổ, xếp hạng hoặc chọn mô hình.
- Giữ MAPE ngày dương ≤20% cho **từng tuyến top 10**, kèm độ phủ, MAE, WAPE và bias. Không đổi tiêu chí/bộ lọc để làm đẹp kết quả; kết quả activation cũ không chứng minh chất lượng sales forecast.
- Tồn mô phỏng theo tuyến × `sku` × `product_type`; ngưỡng riêng đối tác. Trigger `closing_on_hand < ROP`; IP chỉ tính lượng đặt. Chỉ order là dữ liệu thực được cung cấp; tồn, nhập, lead time và mapping đối tác có nhãn giả định/mô phỏng. Không xin thêm dữ liệu doanh nghiệp đã xác định không cung cấp.
- M01/M02 là xác nhận mentor **do người dùng thuật lại**; A08–A17 vẫn đề xuất. Không tự nâng trạng thái xác nhận hoặc nhận đã đọc nguồn thiếu.

## Đọc đúng tài liệu cho công việc

| Khi làm | Đọc |
|---|---|
| Bắt đầu phiên hoặc xác định tiến độ | [TASK](TASK.md), [PROJECTMAP](PROJECTMAP.md); xem phần task liên quan trong [PLAN](PLAN.md) |
| Nghiệp vụ, nghiệm thu, thay đổi yêu cầu | [requirements](docs/requirements.md), [quyết định](docs/review-log.md#decisions), [quy trình thay đổi](docs/review-log.md#change-process) |
| Dữ liệu, target, schema | [data-contract](docs/data-contract.md), PLAN mục 3–5, R01 |
| Mô hình, backtest, metric | PLAN mục 5, [development](docs/development.md#checks), R03–R05 |
| Phân bổ, tồn, cảnh báo | PLAN mục 6, data-contract, R06–R07 |
| Chạy, kiểm thử, bàn giao | [README](README.md), [development](docs/development.md), R08–R09 |

Không phải đọc mọi tài liệu cho chỉnh sửa nhỏ. PLAN giữ thiết kế chi tiết; requirements giữ tiêu chí; review-log giữ bằng chứng/lịch sử. TASK chỉ tóm tắt tiến độ, không tạo hệ thống task mới.

## Bảo toàn và triển khai

- Giữ nguyên CSV gốc; làm sạch/dedup chỉ trong đầu ra dẫn xuất có log. Không in order/customer ID, sao chép bản ghi riêng tư vào tài liệu hoặc đưa dữ liệu vào truy vấn ngoài. Run thật ở local; không tự upload, push hoặc publish.
- Không khôi phục tệp đã xóa, sửa lịch sử hay cấu hình Git toàn cục. Nếu Git root ngoài project hoặc lỗi ownership, ghi giới hạn và tiếp tục kiểm tra tệp/hash trong project; không quét kho cha.
- Phân biệt bằng chứng kiểm tra trực tiếp với nhật ký cũ. Kiểm tra tệp thực tế trước khi nhận đã có code, test, run hoặc lệnh chạy.
- Tại 02/10/2026 chỉ có CSV và tài liệu; trạng thái này là lịch sử. Ngày 05/10 đã triển khai mã, tests, config, CLI/notebook và dashboard, xem TASK/README. `src/`, `tests/`, `config.json`, CLI/notebook và dashboard trong PLAN là thiết kế gốc, nay cần đối chiếu tệp/run thực tế. Khi được giao kỹ thuật, theo cấu trúc PLAN; CLI/notebook dùng cùng mã, cấu hình tập trung, phiên bản/seed/manifest theo development. requirements.txt đã khóa phiên bản thư viện, xác minh môi trường ở E13/E14.
- Thiếu nguồn khác ngày không có giao dịch; chưa actual không phải 0. Giữ giới hạn snapshot trạng thái, không nhận đã tái dựng dữ liệu có sẵn tại origin vận hành thật.

## Kiểm tra và kết thúc lượt

- Sửa Markdown: kiểm tra link/anchor, bảng/khối mã, trạng thái và phân biệt thực tế/dự kiến. Sửa phép tính: chọn ca dữ liệu, leakage, metric, bảo toàn tương ứng trong [development](docs/development.md#checks); không chạy toàn bộ mô hình cho sửa nhãn thuần túy.
- Khi tiến độ thay đổi, đồng bộ TASK với task trong PLAN; cập nhật requirements nếu đổi nghiệm thu và review-log khi có bằng chứng/quyết định mới. Giữ mã Rxx/Axx/Txx và lịch sử; chỉ cập nhật trong phạm vi được giao. Lượt tạo bộ tài liệu này giữ nguyên ba nguồn.
- Chỉ hoàn thành khi có sản phẩm và kiểm tra thực chạy, kèm kết quả/run/hash phù hợp. Không bịa lệnh, số liệu hoặc nâng T02–T14 vì đã viết hướng dẫn. Phần mất hiệu lực phải ghi cần kiểm tra lại.
- Cuối lượt ghi việc đã làm, tệp liên quan, kiểm tra/kết quả, giới hạn và bước tiếp theo theo [mẫu bàn giao](docs/development.md#handoff).
