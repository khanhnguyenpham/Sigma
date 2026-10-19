# Nghiên cứu bổ sung, tách khỏi mô hình M3 đang phục vụ

daily_validation.py kiểm tra dự báo trực tiếp từng ngày trên top10 theo quantity **train**, đối chiếu danh sách final đã khóa. Không sửa M2, target/split/MAPE, bảng forecast hoặc selection ứng dụng.

Protocol daily-validation-v1 ghi manifest trước truy vấn/fit. SQL chỉ đọc aggregate đến30/09/2025; yêu cầu lịch quan sát đầy đủ01/01/2024–30/09/2025, từ chối thiếu ngày/null. Origin validation30/06–29/09; horizon1–14, chỉ chấm target trong validation. Giữ mọi ngày0 trong MAE/WAPE/bias/coverage; MAPE chỉ actual dương. Đây là validation đã sử dụng, không là holdout độc lập.

Tám phương pháp cố định: last, seasonal7, mean28, mean90, MAPE-weighted median90, weekday median90, LightGBM Poisson và LightGBM weighted L1. Baseline median MAPE dùng actual dương trong lịch sử để tối ưu loss MAPE, không loại ngày0 khỏi bảng đánh giá. Weighted L1 dùng trọng số1/max(y,1), vẫn giữ nhãn0. Hai model pooled top10 dùng150cây/leaves15/minchild100/lr0,03/lambda10/seed42; rolling365/refit7. Features từ prefix kết thúc origin: lag/mean/std, weekday lịch sử, tuyến, horizon và lịch target biết trước. Training target≤fit_cutoff.

Chọn model/tuyến bằng MAPE H1–7 → MAE → ID, coverage100%; H8–14 báo riêng cùng model. Manifest có status/protocol/code/input/requirements hashes, runtime/seed, fitlog cutoff và clipping, CSV predictions/metrics/selection; tất cả trong **outputs/research ignored local**.

Chạy từ root sau load_env.ps1: python -B -m M3.research.daily_validation --source-run SOURCE, dùng Python của .venv-m3. Thay SOURCE bằng UUID source_import complete thật. Mỗi lần tạo thư mục mới, giữ run trước. Đây không phải command thay model ứng dụng.

E91:28fits/95.760forecast/160nhóm metric. Lựa chọn validation H1–7 mean49,451918%,0/10≤20%; so phân bổ M3 cùng623cặp/tuyến mean51,905954%, tốt hơn ở7/10tuyến nhưng vẫn thiếu mục tiêu. Model mới có bias âm; chưa kiểm độc lập/test, chưa đưa vào chính sách tồn hoặc dashboard forecast. Không suy ra dữ liệu không thể dự báo dưới20% chỉ từ tám phương pháp này. [Phạm vi và bằng chứng](../IMPLEMENTATION.md).
