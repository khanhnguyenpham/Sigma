# SIGMA — Dự báo số bán và mô phỏng tồn kho

**Trạng thái ngày 02/10/2026 (Asia/Saigon):** Có dữ liệu order và bộ tài liệu phát triển; chưa có pipeline, cấu hình chạy, tests, notebook, mô hình, dashboard hoặc run dự án. T01 đang làm; T02–T14 chưa làm. Bộ tài liệu bổ sung này dựa trên ba nguồn phiên bản 2.0, không thay đổi nội dung các nguồn đó.

SIGMA hướng tới dự báo tổng `quantity` SIM/gói data bán theo ngày UTC và tuyến `(destination_country, carrier)`, so sánh mô hình rồi phân bổ forecast để mô phỏng tồn kho/cảnh báo theo đối tác. Target không phải activation. Bộ lọc `success` theo `order_datetime` là **A08 đề xuất**, chưa phải quy tắc kế toán hay xác nhận mentor về trạng thái đơn.

## Đầu vào và giới hạn

CSV order cục bộ `data/sigma_sim_data_orders.csv` là dữ liệu thực duy nhất được cung cấp theo xác nhận người dùng. Khảo sát chỉ đọc xác minh 100.000 dòng, 20 cột, 46 tuyến; ngày đặt UTC từ 01/01/2024 đến 31/12/2025. CSV không được đưa lên GitHub; xem [hướng dẫn dữ liệu cục bộ](data/README.md). Ý nghĩa chi tiết và giới hạn snapshot nằm trong [data-contract](docs/data-contract.md).

Tồn kho, nhập hàng, lead time và mapping đối tác sẽ dùng giả định/mô phỏng có nhãn; không phụ thuộc việc xin thêm dữ liệu nội bộ. Lượng bán quan sát không đồng nhất với toàn bộ nhu cầu thị trường. Xử lý dữ liệu riêng tư tại môi trường dự án cục bộ; không upload, push hoặc publish dữ liệu/run thật.

Ảnh đề bài và PDF được tài liệu tham chiếu nhưng chưa có trong workspace. Bằng chứng đã đọc chúng, kết quả activation cũ và ghi nhận Git trong nhật ký là lịch sử, không phải kiểm tra trực tiếp của lượt này. Xem [hiện trạng và sai khác](PROJECTMAP.md#source-gaps), gồm giới hạn Git và chênh lệch hash do xuống dòng.

## Đọc bộ tài liệu

| Tài liệu | Mục đích |
|---|---|
| [AGENTS](AGENTS.md) | Quy tắc ngắn cho Codex và cách chọn tài liệu cần đọc |
| [TASK](TASK.md) | Điều phối T01–T14, bằng chứng còn thiếu và bước kế tiếp |
| [PROJECTMAP](PROJECTMAP.md) | Tệp thực tế, cấu trúc dự kiến, luồng và tác động thay đổi |
| [PLAN](PLAN.md) | Thiết kế chi tiết, giả định Axx, phương pháp và nhiệm vụ |
| [requirements](docs/requirements.md) | Nguồn yêu cầu, R01–R09 và tiêu chí nghiệm thu |
| [review-log](docs/review-log.md) | Bằng chứng lịch sử, quyết định và quy trình quản lý thay đổi |
| [data-contract](docs/data-contract.md) | Schema nguồn, định nghĩa dữ liệu và giao diện đầu ra dự kiến |
| [development](docs/development.md) | Cách triển khai, kiểm tra, quản lý run và bàn giao phiên |

Người mới đọc README → TASK → PROJECTMAP, sau đó phần chuyên môn liên quan. Ba nguồn phiên bản 2.0 có câu “lượt này chỉ cập nhật ba Markdown”: đó là phạm vi lượt cũ; lượt hiện tại bổ sung đúng sáu tài liệu theo yêu cầu mới, vẫn chưa triển khai kỹ thuật.

## Phương pháp và stack dự kiến

Theo PLAN: Python local; pandas/numpy, statsmodels SARIMA, matplotlib, Streamlit; LightGBM có điều kiện sau đánh giá validation. Chưa cài/khóa phụ thuộc hay kiểm chứng tương thích cho dự án. Runtime dùng khảo sát không phải môi trường huấn luyện đã bàn giao.

Top 10 chọn theo quantity bán trong train 01/01/2024–30/06/2025; validation 01/07/2025–30/09/2025; test 01/10/2025–31/12/2025. Horizon 14 ngày, chính h1–7 và h8–14 riêng. [R05](docs/requirements.md#r05) giữ MAPE ngày dương ≤20% cho từng tuyến top 10, kèm độ phủ/MAE/WAPE/bias; chưa có kết quả forecast sales để kết luận đạt.

Ngưỡng tồn riêng theo đối tác; trigger `closing_on_hand < ROP`, IP dùng tính lượng đặt. Các tham số A08–A17 còn là đề xuất. Dashboard, báo cáo và kiểm tra cảnh báo ≥7 ngày đều là sản phẩm dự kiến, chưa nghiệm thu.

## Cách chạy

**Chưa có lệnh chạy dự án được kiểm chứng**, vì `run.py`, `config.json`, `requirements.txt` và `app.py` chưa tồn tại. Không cài thư viện hoặc chạy pipeline chỉ từ hướng dẫn này.

Ví dụ CLI trích từ thiết kế PLAN mục 4.2 — **dự kiến, chưa kiểm chứng**:

```text
python run.py --config config.json --stage audit
```

Các stage dự kiến khác: `backtest`, `forecast`, `inventory`, `report`, `all`; chọn một stage. Hướng dẫn môi trường/lệnh thật chỉ được bổ sung sau T02 có bằng chứng chạy. Notebook local dự kiến dùng cùng mã CLI; Colab nếu cần chỉ là minh họa với dữ liệu giả.

## Bước tiếp theo

Rà soát/khép phần tài liệu của [T01](PLAN.md#t01), giữ nguồn, giả định và giới hạn rõ ràng. Khi được giao triển khai kỹ thuật và điều kiện T01 có bằng chứng, bắt đầu [T02](PLAN.md#t02), sau đó T03 → T04 → T05. Việc tạo tài liệu không hoàn thành task kỹ thuật hoặc nghiệm thu M1/M2/M3.

## Repository Git

Repository theo yêu cầu người dùng: [khanhnguyenpham/Sigma](https://github.com/khanhnguyenpham/Sigma). Bản hiện tại lưu bộ tài liệu phát triển, chưa có mã triển khai. Dữ liệu nguồn, kết quả chạy, môi trường cục bộ và thông tin đăng nhập được loại bằng `.gitignore`.

Để lấy tài liệu và làm việc trên ổ F:

```powershell
git clone https://github.com/khanhnguyenpham/Sigma.git F:\code\Sigma
```

Chỉ chạy lệnh trên khi thư mục đích chưa tồn tại. CSV cần được cung cấp cục bộ theo [hướng dẫn dữ liệu](data/README.md); clone repository không tự tải dữ liệu riêng tư.
