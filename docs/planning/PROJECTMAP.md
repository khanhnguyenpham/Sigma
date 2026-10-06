# Bản đồ project SIGMA

**CHG-035/E63 — 06/10/2026:** theo yêu cầu người dùng, chuẩn bị xuất bản nhánh GitHub `codex/m2-report-20261007` với [báo cáo M2 tổng hợp](../../M2/reports/published_m2_20261007/README.md), HTML offline, biểu đồ, CSV metric/lựa chọn và hash đối soát. Giữ kết quả9/10 tổng7,15,89%, LG U+20,69% hoãn tối ưu; ngày0/10, test hồi cứu. Raw, train từng ngày và artifact forecast giữ local, không refit hoặc đổi nghiệm thu.

**CHG-034/E62 — 06/10/2026:** tạo nhánh local `codex/m2-report-20261007` để báo cáo M2 ngày07/10. Clean root33→6 tệp, chuyển39 tệp vào data/configs, src/sigma, scripts, legacy và docs/planning/archive. Đóng gói dữ liệu train/validation/test top10 và báo cáo HTML/Streamlit đọc run đã khóa9/10 tổng7,15,89%, LG U+20,69% để tối ưu sau. Không refit raw hoặc đổi lựa chọn; ngày0/10/R05/R07/T14 còn mở. [Kịch bản trình bày](../../M2/reports/presentation-guide.md).

**CHG-033/E61 — đã triển khai và đối soát 06/10/2026:** 12 biến thể đối chứng +14 mới,26 biến thể/50 cấu hình ngày–tổng7, tối đa3 worker. Run `m2_improved_models_20261006_fixed` complete, lựa chọn khóa theo validation: LightGBM9 tuyến/Prophet au(KDDI) cho tổng7, test hồi cứu 9/10, MAPE 15.89%, LG U+20,69%; ngày0/10,46.74%. 40 kiểm tra liên quan và verifier 401,600 dòng/9,160 nhóm metric đạt. Raw và583 tệp lịch sử nguyên; R05/R07/T14 còn mở, sản phẩm V13 giữ hiện hành. [Báo cáo cải tiến](../../M2/reports/m2_improved_models_20261006_handoff.md).

**CHG-032/E60 — 06/10/2026:** mã riêng từng họ nằm tại M2/models/LightGBM/model.py, SARIMA/model.py và Prophet/model.py; mỗi thư mục có variants.json và README. [Hướng dẫn mở rộng](../../M2/models/README.md), registry.py, common.py và families.py xác định giao diện và protocol chung. Báo cáo đối soát hiện tại ở M2/reports/m2_three_models_20261006_modular; bằng chứng parity24 trường hợp và bảo toàn583 tệp ở M2/artifacts/model_split_checked.json. 15 tests/221.280 dòng/2.040 nhóm metric đạt; không chạy lại huấn luyện dữ liệu thật.

**CHG-031/E59 — 06/10/2026:** [M2](../../M2/README.md) là nơi chính cho artifacts/models/notebooks/reports. Mã ba họ tại M2/models/families.py, verifier tại M2/models/verify.py, cấu hình tại M2/models/model_families.json, tests tại M2/models/tests, notebook tại M2/notebooks/model_comparison.ipynb. Mã ở sigma/forecasting/families.py và sigma/verification/model_families.py nay là alias; các đường outputs cũ là liên kết tương thích. 583 tệp kết quả nguyên byte; CLI/13 tests/notebook và verifier221.280 dòng/2.040 metric đạt. Báo cáo có đường mới tại M2/reports/m2_three_models_20261006_organized.

**CHG-030/E58 — 06/10/2026:** thêm `sigma/forecasting/families.py`, `sigma/verification/model_families.py`, `configs/model_families.json`, `tests/test_model_families.py` và [hướng dẫn/kết quả](../model-families.md). CLI `model-families` tạo ba thư mục LightGBM/SARIMA/Prophet với hai mục tiêu/họ; run `m2_three_models_20261006` complete,309 artifact. CLI `verify-model-families` đối soát221.280 dòng/2.040 nhóm metric và tạo `m2_three_models_20261006_review`. 9 kiểm tra mới,45 kiểm tra liên quan và pip check đạt. Raw/58 artifact ngày cũ/run tuần V13 local nguyên; CI chưa chạy, sản phẩm hiện hành chưa đổi.

**Bổ sung CHG-029/E56–E57 — 06/10/2026:** `sigma/experiments/seasonal_weekly.py` và verifier chạy validation-only, không cải thiện top 10 nên chưa tích hợp; run local `sigma_seasonal_validation_v14`, đối soát `sigma_seasonal_verification_v14`. `sigma/analysis/alert_diagnostics.py` bổ sung bảng giải thích sự kiện vào dashboard tồn, không sửa policy/forecast/mẫu số. 225 tests local và AppTest mới sáu trang/bốn kịch bản/SKU–loại đạt; CI bổ sung chưa xác minh. [Tài liệu chẩn đoán](../model-diagnostics.md) và hướng dẫn demo được cập nhật; run sản phẩm V13, raw/sealed ngày và Word/slide giữ nguyên.

**Hiện hành CHG-028/E53–E55 — 06/10/2026:** sản phẩm mặc định dùng V13 với 58 ứng viên chọn bằng validation, cùng policy V4, stock V7, customer V6 và comparison V3. Bộ báo cáo đã khóa tại sigma_m2m3_checkpoint_v3; mở start_m2m3.ps1 ở cổng 8504. **214 tests và CI Windows của commit 183ed10 đạt**; đã đối soát 447.810 cặp dự báo, 42.136 hệ số hiệu chỉnh, 1.100.320 dòng sổ, 267.908 giao dịch/nhập và 920 mặt hàng. AppTest sáu trang, bốn kịch bản và bộ lọc SKU/loại đạt. Job Windows 07:00 đã cài, chạy thử mã 0. Tuần đạt 9/10, MAPE trung bình 16,17%, LG U+ 21,19%; R05 ngày vẫn 0/10, tỷ lệ báo sớm 33,73% trên 2.867 sự kiện. **Chưa nghiệm thu toàn bài.** Dữ liệu gốc và 59 artifact v11 nguyên; src/ và run.py không đổi, app.py chỉ thêm khóa bộ run. Word/slide chưa làm lại; các cập nhật cũ bên dưới là lịch sử.

**Lịch sử CHG-027/E43–E49 — 05/10/2026:** sản phẩm mặc định dùng sigma_weekly_refactored_v12; đã hoàn tất bản so sánh ngày/tổng7 ngày và tổ chức mã sigma/ +29 entry points legacy/ +configs/experiments. 192 tests đạt; parity364.320 validation cache/7.590 fresh test/92 future/644 daily rows ở1e-8, cùng46 lựa chọn; raw/59 v11 files nguyên. Full policyV3 kiểm13 kịch bản/1.100.320 ledger/267.812 events; snapshotV6 kiểm920 items từ đúng policy; customerV5 kiểmD+7; AppTest6 trang và4 bộ lọc scenario đạt. Tuần9/10, mean16,19%, LG U+21,19%; R05 ngày0/10, early≥7 ngày33,80% cùng2867 events; chưa nghiệm thu toàn bài. CHG-027 thay thứ tự hoãn CHG-025; Word/slide không làm lại. Các cập nhật bên dưới E37–E41 là lịch sử.

**Cập nhật 05/10/2026 — CHG-024/025, E37–E39:** đã áp dụng **khách đặt D → giao D+7 ngày lịch UTC**, không trễ giao, gồm cuối tuần; không đổi lead time nhập kho. Người dùng mô tả snapshot order là giả định; đây là nguồn thuật lại, vẫn giữ dữ liệu/outputs private và raw nguyên. [Sản phẩm chung và lịch giao](../customer-delivery.md) mở bằng `start_product.ps1` tại cổng 8503. Run tuần hiện hành `sigma_weekly_calibrated_v5`: test hồi cứu **9/10**, mean **15,97%**, LG U+ **21,36%**; chọn validation rồi khóa trước test. 920 khuyến nghị tồn từ phân bổ tuần đã đối soát, replay cùng 5.520 cửa sổ báo sớm **33,73%**; chưa chạy lại toàn bộ chính sách liên tục bằng tuần. 150 tests đạt, AppTest năm trang/không exception; job refresh/skip chạy thật, script đăng ký lịch nền được chuẩn bị nhưng chưa cài. R05 ngày **0/10**, R07/T14 vẫn mở. **Sau khi đủ điều kiện nghiệm thu mới làm bản so sánh chính thức ngày/tổng 7 ngày và tổ chức lại code**, đúng thứ tự người dùng yêu cầu; chưa làm lại Word/slide. Những cập nhật E36/v1 bên dưới là lịch sử.

**Nguồn và phương án mới 05/10/2026 — E35/E36:** ảnh kickoff JPG mới đã xem trực tiếp, lưu bản sao ignored local; [đối chiếu nguồn](../kickoff-checklist.md) thay tình trạng thiếu ảnh kickoff ở các ghi nhận cũ bên dưới. PDF và ảnh M01/M02 vẫn chưa có; không phục hồi tệp bị xóa. [weekly_forecast.py](../../sigma/forecasting/weekly.py), [config.weekly.json](../../data/configs/config.weekly.json), [verify_weekly.py](../../sigma/verification/weekly.py), [weekly_app.py](../../sigma/ui/weekly.py), [launcher](../../scripts/start_weekly_dashboard.ps1), [tests](../../tests/test_weekly_forecast.py), [hướng dẫn tuần](../weekly-forecast.md) đã có thật. Run `outputs/sigma_weekly_v1/` và verification_v2 giữ private; test tuần 9/10, AIS 22,14%, chưa thay R05 ngày. 125 tests/AppTest đạt; mã core ngày/v11 không sửa. Các tình trạng thiếu nguồn ở E34 và ngày02/10 là lịch sử.

**Hiện trạng 05/10/2026:** Workspace hiện tại `C:/Users/nguye/OneDrive/Desktop/TTDN_Sigma`. Đã có `src/`, `tests/`, `config.json`, `run.py`, `app.py`, khóa phụ thuộc, notebook, script dashboard và CI. Run local thật hiện hành `outputs/sigma_scaled_v11/`; demo giả `outputs/demo_scaled_v11_verify/`; Word/slide local `reports/M2/`. Dữ liệu và outputs không thuộc gói Git. Các cây/tình trạng ngày 02/10 bên dưới là lịch sử trước triển khai; trạng thái hiện hành tại TASK và README. Git root đã kiểm tra nằm đúng project, không còn dùng giới hạn kho cha cũ để mô tả workspace này.

**Nghiên cứu E32:** Có [validation_campaign.py](../../sigma/experiments/validation.py) và [bốn ca kiểm](../../tests/test_validation_campaign.py); 111 tests hiện hành đạt. Campaign 12 cấu hình chọn trên tháng 5–6 nằm trong train, sau đó chấm toàn validation tháng 7–9: 0/10 đạt 20%, chưa tích hợp. Output riêng `outputs/sigma_ablation_campaign_v1/`, đối soát/so sánh `outputs/sigma_ablation_analysis_v3/`, đều private local. Mã production, 59 tệp sealed v11 và raw hash giữ nguyên; không chạy test mới, không sửa Word/slide.

**Lịch sử phạm vi CHG-012/013:** tập trung hoàn thiện project, chưa làm tiếp Word/slide. Có `validate_context.py`, `src/context_models.py`, tests và kết quả validation local `outputs/context_validation_v1/`; chưa tích hợp mô hình context vào production. E16 ghi kiểm tra trực tiếp; R05/R07 vẫn mở.

**Báo cáo tiến độ M2 E33 / CHG-022:** Người dùng yêu cầu ưu tiên Word báo cáo chi tiết và slide để nộp mentor trước. Bản hiện hành local tại `reports/M2_2026-10-05/`: `SIGMA_Bao_cao_tien_do_M2_Nop_mentor_2026-10-05_v3.docx` (18 trang), `SIGMA_Slide_bao_cao_M2_Nop_mentor_2026-10-05_v2.pptx` (24 slide có ghi chú). Đã kiểm bố cục và không có định danh nguồn; dùng số liệu sealed v11 và nghiên cứu E32. Run/mã production không sửa, R05/R07/T14 vẫn mở; không tự upload báo cáo.

**Nghiên cứu E34:** [calibrate_campaign.py](../../sigma/experiments/calibration.py), [verify_calibration.py](../../sigma/verification/daily_calibration.py) và [bốn ca kiểm](../../tests/test_calibrate_campaign.py) đã chạy; toàn suite 115 tests đạt. Head phối hợp/hiệu chỉnh học tháng 5, chọn tháng 6 trong train rồi khóa trước validation; refit 7 ngày chỉ dùng nhãn đã qua. Run riêng `outputs/sigma_calibration_campaign_v2/`, đối soát `outputs/sigma_calibration_verification_v1/`: vẫn 0/10 đạt 20%, 38,64–52,10%; mean kém v11 validation. Không tích hợp, không chấm test mới hoặc sửa sealed v11. Chẩn đoán train theo tháng/weekday là in-sample, không phải cận dưới cho mọi mô hình. Ảnh/PDF kickoff gốc vẫn thiếu; đã đề nghị đối chiếu nguyên văn, chưa tự thay tiêu chí.

**Thời điểm đối chiếu:** 02/10/2026 (Asia/Saigon). **Thư mục project:** `C:/Users/asus/OneDrive/Máy tính/sigma/Sim-Demand-Forecasting-main`.

Bản đồ này ghi tệp thực tế và sai khác nguồn; [PLAN 2.0](PLAN.md) vẫn giữ thiết kế chi tiết, [requirements](../requirements.md) giữ nghiệm thu, [review-log](../review-log.md) giữ lịch sử. Mô tả khảo sát chỉ đọc ngày 02/10 bên dưới giữ làm lịch sử. Pipeline hiện đã chạy, xem E11–E15; ảnh/PDF nguồn vẫn thiếu và không nhận đã đọc lại.

<a id="actual-tree"></a>
## Cây trước triển khai — lịch sử 02/10/2026

```text
Sim-Demand-Forecasting-main/
├── AGENTS.md                       # Mới: quy tắc và điều hướng cho Codex
├── TASK.md                         # Mới: điều phối T01–T14
├── PROJECTMAP.md                   # Mới: hiện trạng, cấu trúc, sai khác
├── README.md                       # Mới: giới thiệu và điểm bắt đầu
├── PLAN.md                         # Có trước: kế hoạch chi tiết 2.0, giữ nguyên
├── data/
│   └── sigma_sim_data_orders.csv   # Có trước: nguồn riêng tư, giữ nguyên byte
└── docs/
    ├── requirements.md             # Có trước: R01–R09, giữ nguyên
    ├── review-log.md               # Có trước: bằng chứng/lịch sử, giữ nguyên
    ├── data-contract.md            # Mới: schema và hợp đồng dữ liệu dự kiến
    └── development.md              # Mới: triển khai, kiểm tra và bàn giao
```

Bốn tệp có trước và sáu tài liệu mới là toàn bộ tệp hiện có trong project tại lần đối chiếu này. Chưa có mã nguồn, cấu hình, môi trường dự án, tests, notebook, outputs hoặc báo cáo chạy. Không tìm thấy AGENTS áp dụng trong project/các thư mục cha ở bước khảo sát trước khi tạo AGENTS mới. Vai trò và lộ trình đọc từng tài liệu tại [README](../../README.md).

<a id="planned-tree"></a>
## Cấu trúc thiết kế trước triển khai — lịch sử 02/10/2026

Trích nhóm sản phẩm từ PLAN mục 4; cây dưới chỉ liệt kê phần kỹ thuật còn thiếu. Tên/path không chứng minh sản phẩm tồn tại; không tạo thư mục rỗng hoặc khôi phục tệp cũ để làm đủ cây.

```text
Sim-Demand-Forecasting-main/
├── config.json                    # Target, split, mô hình, đối tác, giả định
├── requirements.txt               # Phụ thuộc huấn luyện local, chưa khóa
├── requirements-demo.txt          # Phụ thuộc dashboard, chưa khóa
├── run.py                         # CLI dự kiến
├── app.py                         # Streamlit dự kiến
├── notebooks/run_local.ipynb      # Dùng cùng mã với CLI
├── src/
│   ├── data.py                    # Audit và dữ liệu dẫn xuất
│   ├── models.py                  # Baseline/SARIMA/LightGBM có điều kiện
│   ├── evaluation.py              # Backtest và metric
│   ├── inventory.py               # Phân bổ, ledger, chính sách/cảnh báo
│   └── reporting.py               # Bảng, hình và gói kết quả
├── tests/
│   ├── test_data.py
│   ├── test_forecasting.py
│   └── test_inventory.py
├── data/
│   ├── reference/holidays.csv      # Lịch công khai có nguồn
│   ├── scenarios/
│   │   ├── partner_map.csv         # Mapping giả định
│   │   ├── inventory.csv           # Snapshot mô phỏng
│   │   └── receipts.csv            # Hàng về giả định/mô phỏng
│   └── processed/daily_sales.csv
├── outputs/<run_id>/               # Riêng tư; manifest/audit/forecast/metric
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

Ảnh/PDF nguồn được PLAN đưa trong cây thiết kế được liệt kê ở phần nguồn thiếu bên dưới, không phải tệp kỹ thuật sẽ tự sinh. Mô hình dữ liệu đầu ra mới ở mức [giao diện dự kiến](../data-contract.md#outputs), chưa có API/schema thực thi. T12 tập hợp kiểm thử nghiệm thu; các kiểm tra cần thiết vẫn được viết/chạy cùng từng task kỹ thuật trước đó.

## Luồng dự kiến và điểm kiểm soát

```text
order gốc → audit → daily sales → EDA/lịch → baseline/backtest
→ chọn mô hình bằng validation → khóa lựa chọn → test
→ forecast → phân bổ SKU × product_type
→ mô phỏng tồn kho/cảnh báo → dashboard/báo cáo
```

CSV không bị ghi đè. Mỗi sản phẩm dẫn xuất truy về target/cutoff/run; tồn và cảnh báo thêm scenario/assumption version. Forecast sales chấm trên order holdout; kết quả tồn đánh giá theo kịch bản. Giao diện không được trộn actual, dự báo, giả định và mô phỏng.

| Thay đổi | Thành phần phải rà soát/tính lại | Kiểm tra bắt buộc liên quan |
|---|---|---|
| Target, bộ lọc A08, timezone | Data contract/config; T03–T14: chuỗi, EDA, top 10, mô hình, metric, phân bổ, tồn, hình/báo cáo | Quantity, UTC, activation độc lập; hash gốc; truy phiên bản target |
| Split, cutoff, origin/horizon | Config/backtest/top 10/selection/forecast; T04–T14 và nhãn dashboard | Top 10 chỉ train; feature/nhãn đúng cutoff; cùng cặp chấm; H đủ L+R; công khai test đã dùng |
| Mô hình, feature, refit hoặc lựa chọn | models/evaluation dự kiến; predictions/metrics/selected_models; các đầu ra tồn/báo cáo phụ thuộc forecast | Không nhìn tương lai; chọn bằng validation; metric tính tay; không dùng test chọn lại |
| Mapping, tồn đầu, lead time, safety, MOQ, receipts | A09–A16/config/scenario; T06/T10–T14, manifest/ledger/alerts/độ nhạy | Ngưỡng riêng, strict <, IP/Q, ETA, cân bằng tồn, event duy nhất; A12 không đòi fit lại forecast nếu độc lập |
| Chỉ nhãn hoặc trình bày | Tài liệu/hình/dashboard liên quan | Link/đơn vị/nguồn, khớp số và nhãn thực/dự kiến; không thực nghiệm lại nếu phép tính không đổi |

<a id="source-gaps"></a>
## Nguồn thiếu và sai khác cần giữ rõ

| Vị trí / nguồn | Đối chiếu trực tiếp và trạng thái | Tác động / cách sử dụng |
|---|---|---|
| PLAN mục 3, review-log E01/E02, requirements S01/S02 | `docs/PROJECT_REQUIREMENTS.png` và `docs/Báo cáo chi tiết Sigma.pdf`: **được tài liệu tham chiếu nhưng chưa có trong workspace**. Bốn liên kết cũ tới hai tệp này chưa phân giải được | Không nhận đã đọc/kiểm chứng lại ảnh hoặc 45 trang PDF. Giữ nhận xét E/RV như lịch sử, không tạo tệp giả hoặc khôi phục |
| M01/M02, review-log E08 | Hai ảnh mentor chỉ được người dùng thuật lại trong nguồn 2.0; chưa có tệp để đọc trực tiếp | Giữ nguồn thuật lại, không gán bộ lọc success, mapping hoặc số ngưỡng cho mentor |
| review-log E02 | Hash/kích thước CSV hiện tại khác bản lịch sử; chuyển LF→CRLF trong bộ nhớ khớp đúng hash/kích thước E02 | Ghi cả hai dấu vết tại [data-contract](../data-contract.md#source-check). Không coi byte hiện tại giống byte lịch sử, không sửa xuống dòng để ép khớp |
| PLAN mục 3, review-log E01/E10, QA-DOC-001/002 | Khảo sát chuẩn bị chạy `git rev-parse --show-toplevel` gặp dubious ownership tại kho cha `C:/Users/asus`; project không có `.git` riêng | Chưa xác minh tracked CSV, danh sách 26 tệp bị xóa hay diff hiện tại. Đây là ghi nhận lịch sử, không phát hiện mới. Không sửa safe.directory/global Git; dùng danh sách tệp/hash trong project |
| Đầu ba nguồn 2.0, U03/U05, DEC13/DEC21 | Phạm vi “ba Markdown” thuộc lượt cũ; yêu cầu hiện tại cho phép bổ sung sáu tài liệu | Giữ nguyên nguồn, không diễn giải giới hạn cũ thành cấm tạo sáu tài liệu hiện tại; chưa có quyền triển khai kỹ thuật trong lượt này |
| PLAN mục 6.1 / CSV; PLAN mục 4.2 / requirements R04 | CSV dùng `sku`, mô tả khóa dùng `SKU`; forecast interface ghi `forecast_date`, tiêu chí ghi `target_date` | Giữ `sku` ở nguồn; ghi khác biệt tên ngày mục tiêu trong data-contract. Giao diện đầu ra chưa triển khai, cần chốt khi làm kỹ thuật, không đổi nguồn âm thầm |
| PLAN T01/T10 so với requirements R01–R09 | PLAN gắn T01 với R01–R09, trong requirements T01 được liệt kê trực tiếp ở R01/R09; R09 liệt kê T10 nhưng PLAN T10 ghi R06/R07 | Mức liệt kê truy vết chưa đối xứng. TASK giữ Rxx theo PLAN; ghi rõ đối chiếu này, không bỏ nghĩa vụ R09 hoặc tự sửa ba nguồn |
| review-log E06 và QA-DOC-001/002 | E06 là MA7 activation, không có script/CSV kết quả hiện hành; các QA cũ thuộc bộ ba nguồn ở thời điểm cũ | Không dùng như baseline sales hoặc kiểm tra bộ sáu tệp mới; T02–T14 vẫn chưa làm |

Các sai khác trên không tự xác nhận hoặc bác bỏ nghiệp vụ đã được thuật lại. Thiếu ảnh/PDF hoặc dữ liệu tồn thật không tạo yêu cầu xin thêm dữ liệu doanh nghiệp; triển khai sau này dựa trên yêu cầu/giả định có nhãn và công khai giới hạn.

<a id="doc-checks"></a>
## Kiểm tra lượt bổ sung tài liệu

**Kết quả ngày 02/10/2026: đạt kiểm tra tài liệu trong phạm vi dưới đây.** Đã chạy kiểm tra chỉ đọc bằng Python standard library qua `python -B -` trong PowerShell; mã kiểm tra truyền qua stdin, không tạo script hoặc kết quả kỹ thuật giả trong project.

- Đúng 10 tệp hiện có: bốn tệp nền và sáu Markdown mới; không tạo thêm tệp ngoài danh sách.
- Sáu Markdown đọc UTF-8 hợp lệ; 72 liên kết tương đối/anchor hợp lệ; 15 bảng đúng số cột; 9 khối mã đóng đủ.
- Bảng điều phối đủ đúng một dòng cho mỗi T01–T14; tên, tập phụ thuộc và Rxx khớp PLAN. T01 vẫn đang làm, T02–T14 chưa làm; giữ điều kiện T08 và vai trò T06/T09 với T10. Ba nguồn giữ đủ chín định nghĩa R01–R09.
- Từ điển đủ 20 cột theo đúng thứ tự header CSV; phân biệt kiểu quan sát/kiểu dự kiến và ý nghĩa suy luận. Đã rà nội dung target sales/A08 đề xuất, split, top 10 train, H14/h1–7/h8–14, metric và trigger strict < theo nguồn 2.0.
- SHA-256 của CSV, PLAN, requirements và review-log khớp mốc đầu lượt tạo tài liệu (4/4); không khôi phục nguồn thiếu hoặc đổi Git config. Kiểm chứng phạm vi bằng inventory/hash, không tuyên bố có Git diff hợp lệ.
- Bốn liên kết trong hai tài liệu nguồn tới ảnh/PDF thiếu vẫn là giới hạn đã ghi ở bảng trên; không tính chúng là liên kết mới đạt kiểm tra. Bằng chứng lịch sử và kiểm tra trực tiếp đã được tách rõ.

Đây là kiểm tra Markdown/schema/truy vết và bảo toàn nguồn, **không phải kiểm thử pipeline hoặc nghiệm thu T02–T14/M1/M2/M3**. Chưa cài thư viện, huấn luyện hoặc mô phỏng. Bước tiếp theo: rà soát đóng phần tài liệu T01 theo tiêu chí trong PLAN; T02 chỉ bắt đầu khi được giao kỹ thuật và điều kiện T01 có bằng chứng, sau đó T03 → T04 → T05.

**Cập nhật CHG-014:** Có `src/seasonal_models.py`, `src/validation_cache.py`, `verify_release.py`, config 1.3.0 và run tích hợp v5 đang kiểm tra. Context đã tích hợp CLI; mô tả chưa tích hợp CHG-013 bên trên chỉ kết quả lịch sử. Demo `demo_integrated_v5_verify` trong môi trường thứ hai tái lập 14 bảng. R05 vẫn 0/10, không gọi toàn bài đã đạt.

**Cập nhật CHG-015/E19:** `src/count_models.py`, config 1.4.0 và v6 đã kiểm tra kỹ thuật (59 tests/50 sealed files/AppTest), 51 ứng viên chọn bằng validation; R05 vẫn 0/10. R06 còn bổ sung thứ tự giao dịch; không nâng ledger tổng ngày thành bằng chứng giao dịch.

**Cập nhật CHG-016/E21:** Có `src/transactions.py`, config 1.5.0, `config.integrated-v6.json` và run v7 đã đối soát event/day/nguồn audited. 75 tests đạt; mã hiện hành xử lý thứ tự giao dịch thật trong mô phỏng, không chỉ chứng minh tương đương tổng ngày. Prototype cohort CHG-017 chỉ validation, chưa tích hợp production.

**Cập nhật CHG-017/E23:** Có `src/cohort_models.py`, config 1.6.0, config v7 lưu và run v8 đã kiểm 83 tests/53 hashes/AppTest. Cohort đã tích hợp CLI sau validation, không còn chỉ prototype. R05 vẫn 0/10; dữ liệu/proxy/giả định giữ nhãn.

**Cập nhật CHG-018/019/E25:** Config 1.7.0, catalog 57 và run sigma_monthly_v9 đã kiểm 92 tests/55 hashes/nguồn/top/selection/actual/AppTest. Có tests/test_operational_guards.py, AllocationPlan causal và nguồn giả riêng trong mỗi run. R05 vẫn 0/10; Word/slide chưa làm tiếp.

**Cập nhật CHG-020/E27:** Có src/hierarchical_models.py, tests/test_hierarchical_models.py và tests/test_release_verification.py. Config 1.8.0/catalog 59; v10 đã kiểm 100 tests/nguồn và metric validation/top/selection/actual/ledger/events/AppTest. R05 vẫn 0/10, không chọn bằng test; Word/slide chưa làm tiếp.

**Cập nhật CHG-021/E31:** Có check_data.py, src/monthly_lad.py và tests chuẩn hóa/scaler. Config 1.9.0, v11 kiểm 107 tests/59 sealed hashes/nguồn/validation/ledger/events/AppTest. Chuẩn hóa độc lập và scaler causal được kiểm; test vẫn 0/10, không chọn lại bằng test; Word/slide chưa làm tiếp.
