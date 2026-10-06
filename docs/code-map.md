# Đọc và sửa mã SIGMA

**CHG-034/E62 — nhánh M2 ngày 07/10/2026:** root còn6 tệp điều hướng/môi trường;39 tệp đã chuyển vào data/configs, scripts, src/sigma, legacy và docs/planning/archive. Cấu hình giữ nguyên byte; resolver đọc được tên cũ của bundle đã khóa. `src/pipeline.py` là CLI ngày (`python -m sigma daily`), `sigma/ui/daily.py` là giao diện ngày. [Trang M2](../M2/report_app.py), [đóng gói báo cáo](../M2/presentation.py), [kịch bản trình bày](../M2/reports/presentation-guide.md). Kết quả9/10 giữ nguyên; LG U+ để tối ưu sau.

M2 ba họ mô hình có implementation tại [M2/models](../M2/models/README.md): `LightGBM/model.py`, `SARIMA/model.py`, `Prophet/model.py`, mỗi họ có `variants.json` và README riêng. `families.py` giữ runner; `common.py` giữ nhãn/schema; `registry.py` đăng ký module; `verify.py` đối soát độc lập. CLI chung trỏ vào package này; hai đường import cũ là alias. Kết quả, notebook và báo cáo nằm trong M2. Pool v2 có26 biến thể/50 cấu hình; `common.active_variants/effective_settings` giữ lựa chọn theo mục tiêu và override, `reuse.py` kiểm source/config/audit trước cache validation rồi dựng lại actual, không tái sử dụng test hoặc lựa chọn. Run hiện hành nghiên cứu là `m2_improved_models_20261006_fixed`; sản phẩm V13 có phạm vi riêng.

Implementation hiện hành được gom theo chức năng. 29 entry points cũ được chuyển vào `legacy/`, không có bản sao thuật toán. Root chỉ giữ README, AGENTS, pytest và khóa môi trường. Khi sửa, mở tệp trong `sigma/` hoặc core ngày trong `src/`.

```text
sigma/
├── __main__.py             # python -m sigma; danh sách lệnh và help
├── forecasting/            # mô hình tổng 7 ngày, features, head và cache validation
├── inventory/              # chính sách liên tục và khuyến nghị từ snapshot tương ứng
├── delivery/               # khách đặt D → lịch giao D+7
├── jobs/                   # refresh, chống chạy trùng, giữ last-good khi lỗi
├── ui/                     # menu và trang ngày/tuần/giao/tồn/so sánh
├── analysis/               # so sánh cùng cửa sổ ngày và tổng 7 ngày
├── verification/           # đối soát nhãn, metric, quantity, tồn, UI, parity
├── experiments/            # nghiên cứu ngày, tách khỏi cấu hình sản phẩm
├── demo.py                 # tạo bundle giả riêng và kiểm xuyên suốt
├── release.py              # kiểm toàn vẹn, khóa bộ demo M2–M3, HTML tình trạng
├── product_catalog.py      # đọc đúng run đã khóa; từ chối sai hash
└── provenance.py           # SHA-256 implementation và core được import
src/                       # core ngày và pipeline.py; sealed v11 nguyên
data/configs/
├── weekly.json             # cấu hình tuần dùng cho sản phẩm
└── experiments/            # cấu hình các đợt nghiên cứu có phiên bản
tests/                     # fixture giả, ca leakage, phép tính và guards
legacy/                    # lệnh/import tương thích trước CHG-027
docs/                      # yêu cầu, phương pháp, hướng dẫn và bằng chứng
docs/planning/             # TASK, PLAN, PROJECTMAP
scripts/                   # launcher PowerShell cho M2/sản phẩm và cài job
outputs/                   # run/hình/job state private, ignored Git
```

| Muốn sửa | Mở tệp |
|---|---|
| Feature, backtest, refit và chọn model tuần | [forecasting/weekly](../sigma/forecasting/weekly.py) |
| Chuẩn hóa ratio, median tuyến tính, mô hình từng tuyến | [linear](../sigma/forecasting/linear.py), [local](../sigma/forecasting/local.py) |
| Ngân sách số cây từng booster, giữ mặc định và chặn cấu hình sai | [boosting](../sigma/forecasting/boosting.py) |
| Hiệu chỉnh và kết hợp dự báo | [calibration](../sigma/forecasting/calibration.py), [mix](../sigma/forecasting/mix.py), [combine](../sigma/forecasting/combine.py) |
| Full H14 cho chính sách và kịch bản | [inventory/policy](../sigma/inventory/policy.py) |
| Khuyến nghị từ đúng sổ tồn cha | [inventory/snapshot](../sigma/inventory/snapshot.py) |
| Lịch khách D+7 và lượng đã biết/dự báo | [delivery/customer](../sigma/delivery/customer.py) |
| Refresh local và giữ run tốt | [jobs/refresh](../sigma/jobs/refresh.py) |
| Menu sản phẩm và trang so sánh | [ui/product](../sigma/ui/product.py), [ui/comparison](../sigma/ui/comparison.py) |
| Bản so sánh có CSV, Markdown, HTML và hình | [analysis/comparison](../sigma/analysis/comparison.py) |
| Giải thích sự kiện cạn, giữ mẫu số replay | [analysis/alert_diagnostics](../sigma/analysis/alert_diagnostics.py) |
| Nghiên cứu mùa vụ validation và đối soát | [experiments/seasonal_weekly](../sigma/experiments/seasonal_weekly.py), [verification/seasonal_weekly](../sigma/verification/seasonal_weekly.py) |
| Kiểm thay đổi cấu trúc không đổi kết quả | [verification/refactor](../sigma/verification/refactor.py) |
| Khóa bản báo cáo M2–M3, bảng đạt/chưa đạt và lỗi bộ demo | [release](../sigma/release.py), [product_catalog](../sigma/product_catalog.py), [ui/bundle](../sigma/ui/bundle.py) |
| Audit, target, metric và sổ giao dịch ngày | [src/data](../src/data.py), [evaluation](../src/evaluation.py), [inventory](../src/inventory.py), [transactions](../src/transactions.py) |

CLI mới: `python -m sigma --help`, sau đó `python -m sigma weekly --help` hoặc thay `weekly` bằng `compare`, `policy`, `stock`, `delivery`, `refresh`, `demo`, `check-product`, `verify-refactor`. CLI và notebook/import gọi cùng implementation.

Alias trong legacy giữ cùng module object, ví dụ `python legacy/weekly_forecast.py --help` hoặc `import legacy.weekly_forecast`. Lệnh khuyến nghị hiện hành là `python -m sigma`. Giao diện ngày ở `sigma/ui/daily.py`, pipeline ở `src/pipeline.py`; source snapshot đúng hash giữ provenance của v11 khi di chuyển. Cấu hình nghiên cứu và mô hình được chọn cho sản phẩm có vị trí riêng; cấu hình không chứa output riêng tư.

Sau thay đổi thuật toán hoặc cấu hình phải tạo run mới. Hash trong protocol trỏ tới implementation thật, core được import và các cấu hình; hash wrapper riêng không chứng minh đã giữ nguyên thuật toán. Refactor dùng cache validation xác thực rồi tính lại selection và fit test/future mới; không gọi validation cache là đã huấn luyện lại.
