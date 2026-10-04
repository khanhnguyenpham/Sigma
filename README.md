# SIGMA — Dự báo bán và mô phỏng tồn kho

Ứng dụng Streamlit chạy local trên Windows, tích hợp audit dữ liệu, EDA, dự báo 46 tuyến, phân bổ SKU, mô phỏng nhập hàng và cảnh báo. Mã, cấu hình, tests và notebook đã được triển khai; đã có Word tiến độ M2 và slide báo cáo ở local theo CHG-011.

**Kết quả ngày 05/10/2026:** run bàn giao `sigma_release_v4` dùng snapshot order 2024–2025. Test h1–7 có độ phủ 100%; **0/10 tuyến top 10 đạt MAPE ≤20%**, MAPE khoảng 40,93–61,96%. Đây là sản phẩm phần mềm có tiêu chí độ chính xác chưa đạt, chưa phải nghiệm thu toàn bộ bài. Không sửa actual hoặc chọn lại mô hình bằng test.

**Tinh chỉnh:** V2 thêm 8 robust và 4 LightGBM weighted-L1; V3 thêm 12 hồi quy lịch (37 ứng viên tổng cộng trên mỗi top 10). Chọn bằng validation, giữ 0/10 đạt. Test cũ được sử dụng lại, không phải kiểm định độc lập. Mean MAPE từng tuyến v1 50,53%; v2 48,35%; v3 49,03%. Không chọn V2 chỉ vì test tốt hơn; bản release dùng lựa chọn theo validation của V3. EDA lễ giữ nhóm unknown và mẫu số, không suy nhân quả.

## Chạy nhanh trên máy hiện tại

Mở PowerShell trong thư mục project, chạy:

```powershell
.\start_dashboard.ps1
```

Mở địa chỉ `http://127.0.0.1:8501`. Chọn bộ kết quả `sigma_release_v4` để xem bản bàn giao đã kiểm tra; `sigma_full_v1` giữ làm lịch sử. Chọn `demo_release` để xem dữ liệu giả. Dashboard có sáu tab: bán & dự báo, đánh giá, tồn & đặt hàng, cảnh báo, kịch bản, audit & giới hạn. Chạy pipeline trước khi mở dashboard trên máy mới.

## Cài trên máy Windows mới

Môi trường đã kiểm chứng: Python 3.14.7, Windows 64-bit. Cài Python, Git và mở PowerShell:

```powershell
git clone https://github.com/khanhnguyenpham/Sigma.git
cd Sigma
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
```

Nếu `python` trỏ tới phiên bản khác, dùng đường dẫn Python 3.14 đã cài. Không cần activate môi trường. `requirements.txt` khóa phiên bản; `requirements-demo.txt` tham chiếu cùng môi trường để demo không khác phép tính.

Demo độc lập, không cần CSV riêng tư:

```powershell
.\.venv\Scripts\python.exe run.py --demo --baseline-only --run-id demo_local
.\start_dashboard.ps1
```

Demo sinh toàn bộ dữ liệu giả, chỉ chạy ba baseline và mô phỏng; không chứng minh chất lượng mô hình trên sales thật. Chạy thêm `--demo` mà không có `--baseline-only` nếu muốn thử cả quy trình chọn mô hình với dữ liệu giả.

## Chạy dữ liệu thật local

Đặt bản CSV được phép sử dụng tại `data/sigma_sim_data_orders.csv`, giữ nguyên byte. Clone GitHub không tải dữ liệu này. Đọc [data/README](data/README.md) và [data-contract](docs/data-contract.md) trước khi đổi nguồn.

```powershell
.\.venv\Scripts\python.exe run.py --run-id sigma_local
```

Lệnh thực hiện audit → EDA → baseline → validation → test → forecast → inventory. SARIMA thử 6 cấu hình trên top 10; LightGBM thử 4 cấu hình nếu điều kiện validation kích hoạt. Chọn bằng validation rồi khóa trước test. Kết quả nằm ở `outputs/sigma_local/`, gồm manifest, predictions, metric, forecast, ledger, recommendations, alerts, bảng kịch bản và hình EDA. Dữ liệu/run thật chỉ giữ local.

Có thể chạy từng stage:

```powershell
.\.venv\Scripts\python.exe run.py --stage audit --run-id sigma_steps
.\.venv\Scripts\python.exe run.py --stage eda --run-id sigma_steps --resume
.\.venv\Scripts\python.exe run.py --run-id sigma_steps --resume
```

`--resume` chỉ chấp nhận cùng input/config/mã/mode, bỏ qua stage đã hoàn tất. Stage thất bại sẽ chạy lại; không ghi đè run khác. Nếu đổi cấu hình hoặc mã, tạo run-id mới. Dashboard từ chối run chưa hoàn tất hoặc artifact sai hash. Notebook [run_local](notebooks/run_local.ipynb) gọi cùng API với CLI và không chứa output riêng tư.

## Quy ước và giới hạn

- Target là tổng `quantity` của trạng thái `success` theo ngày UTC, tuyến `(destination_country, carrier)`; activation không làm target hoặc điều kiện loại sale. A08–A17 được người dùng chọn cho thực nghiệm, chưa phải mentor xác nhận.
- Train 01/01/2024–30/06/2025; validation 01/07–30/09/2025; test 01/10–31/12/2025. Top 10 lấy từ train. Horizon 14 ngày; h1–7 chính, h8–14 riêng; MAPE ngày dương, kèm MAE/WAPE/bias/độ phủ. Forecast sau 31/12/2025 chưa có actual, không gán 0.
- Chỉ order là dữ liệu được cung cấp. Tồn đầu, mapping đối tác, lead time và receipts đều có nhãn giả định/mô phỏng. Khi cấu hình mapping/partners rỗng, bootstrap train-only tạo từng đối tác và ghi trong `effective_config.json`; cấu hình thiếu một phần không được tự lấp.
- Trigger `closing_on_hand < ROP`; IP tính lượng đặt, không thay trigger. Ledger theo item/ngày UTC, nhận đầu ngày và quyết định cuối ngày; tương đương cộng giao dịch trong các điều kiện này, chưa mô phỏng receipt nội ngày, FIFO hoặc thay thế SKU.
- Có 7 kịch bản cơ sở/stress: cơ sở, một ngày bán về 0, giảm nhiều ngày, tăng bán, nhận thiếu, nhận trễ, không nhận; thêm 6 biến thể độ nhạy. Đây là giả định, không dự đoán được mọi cú sốc bất ngờ. Cảnh báo bất thường phát ra sau khi quan sát và không khẳng định nguyên nhân.
- Kịch bản làm tròn demand về đơn vị nguyên; receipt_fraction áp trên từng lượng đặt và làm tròn xuống. Đơn một sản phẩm với tỷ lệ 50% có thể nhận 0; phần chưa nhận giả định hủy, không tạo backorder thật.
- Đánh giá cảnh báo replay không đặt mới được tách khỏi chính sách có bổ sung hàng. Kết quả tồn mô phỏng không chứng minh hiệu quả vận hành thật.
- Snapshot trạng thái cuối không tái dựng thông tin doanh nghiệp có tại origin thật. Ảnh kickoff và PDF nguồn đang thiếu; triển khai dựa trên PLAN/requirements cùng thông tin người dùng thuật lại, không nhận đã đọc nguồn thiếu.

## Cấu trúc và hướng dẫn

`run.py` điều phối; `src/data.py` audit/chuỗi; `src/models.py` forecast; `src/calendar_models.py` hồi quy mùa vụ; `src/evaluation.py` metric/chọn; `src/inventory.py` tồn/cảnh báo; `src/reporting.py` EDA/demo; `src/common.py` manifest; `app.py` dashboard; `config.json` cấu hình tập trung; `tests/` ca dữ liệu giả và phép tính độc lập.

Đọc [TASK](TASK.md) để xem tiến độ, [PLAN](PLAN.md) để xem phương pháp, [requirements](docs/requirements.md) để xem nghiệm thu, [development](docs/development.md) để kiểm tra/bàn giao, [PROJECTMAP](PROJECTMAP.md) để phân biệt hiện trạng và lịch sử. Quy trình Git solo/nhóm ở [hướng dẫn TXT](HUONG_DAN_LAM_VIEC_NHOM.txt).

GitHub chỉ nhận mã, cấu hình, khóa môi trường, tests với fixture giả, notebook không output và tài liệu. Không đưa CSV thật, `outputs/`, môi trường, token hoặc file đăng nhập vào commit. GitHub Actions chạy tests, pipeline demo giả và AppTest trên Windows sạch; không có dữ liệu thật trên CI. Một lần chạy CI không thay diễn tập giao diện trên máy Windows thứ hai.

## Báo cáo tiến độ M2

Tệp local trong `reports/M2/`: `SIGMA_Bao_cao_tien_do_M2.docx` (10 trang) và `SIGMA_Slide_bao_cao_M2_final.pptx` (16 slide, có speaker notes, bảng/biểu đồ chỉnh sửa được). Báo cáo gồm phương pháp, kết quả từng tuyến, tình huống mô phỏng, ma trận R01–R09, giới hạn và kịch bản demo. Word/slide giữ local ngoài Git vì dùng kết quả run riêng tư. Báo cáo tiến độ chưa thay nghiệm thu độ chính xác, báo cáo cuối kỳ hoặc bảo vệ.

Release có 43 tệp khớp hash manifest, 37 tests đã chạy đạt và 1.100.320 dòng ledger cân bằng. Đánh giá chính vẫn 0/10 tuyến đạt R05; replay chỉ 31,67% sự kiện báo trước ít nhất 7 ngày. Xem review-log E14/E15 để truy vết.
