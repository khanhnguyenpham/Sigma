# Hướng dẫn làm việc với SIGMA

## Phạm vi và bảo toàn

- Dùng `main` làm nhánh chính. Chỉ commit, push, publish hoặc deploy trong phạm vi người dùng giao. Khi publish, rà diff và credential, xác minh SHA trên remote và CI của đúng commit. Giữ tên commit theo nội dung thay đổi.
- Giữ nguyên dữ liệu nguồn. Chỉ làm sạch hoặc loại trùng trong đầu ra dẫn xuất có audit. Không in hoặc chuyển bản ghi đơn hàng, định danh khách hàng, credential, DB, backup, runtime hay artifact riêng tư ra ngoài. Giữ `outputs/`, `dist/`, dữ liệu và cấu hình runtime ngoài stage.
- Bảo toàn các thay đổi sẵn có. Giữ `docs/planning/COMMIT_BLOCK_PLAN.md`, `web/backend/research/current_s25_review.py`, `web/backend/research/current_s25_verification.py` và `web/backend/tests/test_current_s25_review.py` ngoài phạm vi chỉnh sửa và stage trừ khi người dùng giao riêng. Không sửa lịch sử Git hoặc cấu hình Git toàn cục.
- Chỉ mở hoặc restart demo, ghi DB demo, enqueue run thật, refit hay triển khai khi công việc được giao bao gồm thao tác đó. Dùng môi trường thử riêng khi cần kiểm tích hợp. URL demo hiện hành lấy từ `connection.json` của runtime.

## Hợp đồng nghiệp vụ

- Dự báo tổng `quantity` bán theo ngày UTC và tuyến `(destination_country, carrier)`. Dùng `order_datetime` và trạng thái `success` theo target A08 đề xuất. Giữ activation ngoài target và điều kiện loại sale hợp lệ. Phân biệt ngày quan sát có số bán bằng 0 với ngày thiếu actual.
- Ứng dụng web dự báo **H14 cho toàn bộ 46 tuyến** tại mỗi mốc chốt: model xuất hai tổng tuần D+1…D+7 và D+8…D+14 (`route_forecasts`), sau đó phân bổ xuống SKU × ngày D+1…D+14 (`item_forecasts`) theo trọng số thứ 90 ngày và tỷ trọng SKU 30/90 ngày. Mã tại `web/backend/src/modules/forecasting/`, đặc tả tại [M3 §3](M3/docs/01-functional-spec.md#3-target-mô-hình-và-thời-gian).
- 10 tuyến top theo lượng bán train giữ model đã chốt của M2 (`data/configs/m2-final.json`). 36 tuyến còn lại chọn model trên validation và khóa lựa chọn trước khi chạy test. Giữ các tập train, validation và test theo cấu hình M2. Chỉ dùng thông tin có tại mốc chốt khi tạo feature, phân bổ, xếp hạng hoặc chọn model.
- R05 (tổng D+1…D+30, MAPE trên actual dương ≤20% cho từng tuyến top 10, kèm coverage, MAE, WAPE và bias) là tiêu chí nghiên cứu M2, **không phải phạm vi dự báo của ứng dụng**; Tổng30 đã gỡ khỏi web từ 03/11/2026. Không nối H14 thành 30 ngày bằng giả định. Giữ nguyên tiêu chí, mẫu số và trạng thái xác nhận của C00/R05/R07/T14 trừ khi người dùng giao thay đổi. Phân biệt xác nhận mentor do người dùng thuật lại với các giả định A08–A17.
- Gắn nhãn giả định hoặc mô phỏng cho tồn, lô nhập, lead time và mapping đối tác. Lead time lấy theo nhà cung cấp (mặc định 7, mô phỏng 1–13 ngày, chốt vào snapshot khi tạo run; run cũ giữ 7). Giữ R1/H14 và hợp đồng hiện hành của policy, forecast và kết quả đã chốt. Run kịch bản dùng dự báo cha đã hoàn tất. Bảo toàn khả năng đọc snapshot lịch sử khi sửa nghiệp vụ mới.

## Tài liệu và kiểm tra

- Đọc [README](README.md) để định vị mã và lệnh. Dùng [đặc tả M3](M3/docs/01-functional-spec.md), [hợp đồng dữ liệu](docs/data-contract.md) và [yêu cầu](docs/requirements.md) cho nghiệp vụ. Dùng [PLAN](docs/planning/PLAN.md) cho thiết kế và [TASK](docs/planning/TASK.md) cho tiến độ.
- Giữ `AGENTS.md` dành cho chỉ dẫn còn hiệu lực. Ghi lịch sử và bàn giao trong [development](docs/development.md), quyết định và bằng chứng trong [review-log](docs/review-log.md). Đồng bộ TASK/PLAN và tiêu chí nghiệm thu khi phạm vi thay đổi.
- Chọn kiểm tra theo phạm vi. Với FE, chạy test React và build liên quan. Với backend hoặc phép tính, chọn ca phù hợp với hợp đồng, dữ liệu, leakage và bảo toàn kết quả. Với Markdown, kiểm tra liên kết và cấu trúc. Tuân thủ giới hạn chạy kiểm thử người dùng đã đặt.
- Báo tệp đã sửa, kiểm tra thực chạy và giới hạn còn lại. Phân biệt kết quả kiểm tra của lượt hiện tại với bằng chứng lịch sử.
