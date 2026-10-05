# Bản đồ project SIGMA

**Hiện trạng 05/10/2026:** Workspace hiện tại `C:/Users/nguye/OneDrive/Desktop/TTDN_Sigma`. Đã có `src/`, `tests/`, `config.json`, `run.py`, `app.py`, khóa phụ thuộc, notebook, script dashboard và CI. Run local thật hiện hành `outputs/sigma_hierarchical_v10/`; demo giả `outputs/demo_hierarchical_v10_verify/`; Word/slide local `reports/M2/`. Dữ liệu và outputs không thuộc gói Git. Các cây/tình trạng ngày 02/10 bên dưới là lịch sử trước triển khai; trạng thái hiện hành tại TASK và README. Git root đã kiểm tra nằm đúng project, không còn dùng giới hạn kho cha cũ để mô tả workspace này.

**Lịch sử phạm vi CHG-012/013:** tập trung hoàn thiện project, chưa làm tiếp Word/slide. Có `validate_context.py`, `src/context_models.py`, tests và kết quả validation local `outputs/context_validation_v1/`; chưa tích hợp mô hình context vào production. E16 ghi kiểm tra trực tiếp; R05/R07 vẫn mở.

**Thời điểm đối chiếu:** 02/10/2026 (Asia/Saigon). **Thư mục project:** `C:/Users/asus/OneDrive/Máy tính/sigma/Sim-Demand-Forecasting-main`.

Bản đồ này ghi tệp thực tế và sai khác nguồn; [PLAN 2.0](PLAN.md) vẫn giữ thiết kế chi tiết, [requirements](docs/requirements.md) giữ nghiệm thu, [review-log](docs/review-log.md) giữ lịch sử. Mô tả khảo sát chỉ đọc ngày 02/10 bên dưới giữ làm lịch sử. Pipeline hiện đã chạy, xem E11–E15; ảnh/PDF nguồn vẫn thiếu và không nhận đã đọc lại.

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

Bốn tệp có trước và sáu tài liệu mới là toàn bộ tệp hiện có trong project tại lần đối chiếu này. Chưa có mã nguồn, cấu hình, môi trường dự án, tests, notebook, outputs hoặc báo cáo chạy. Không tìm thấy AGENTS áp dụng trong project/các thư mục cha ở bước khảo sát trước khi tạo AGENTS mới. Vai trò và lộ trình đọc từng tài liệu tại [README](README.md).

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

Ảnh/PDF nguồn được PLAN đưa trong cây thiết kế được liệt kê ở phần nguồn thiếu bên dưới, không phải tệp kỹ thuật sẽ tự sinh. Mô hình dữ liệu đầu ra mới ở mức [giao diện dự kiến](docs/data-contract.md#outputs), chưa có API/schema thực thi. T12 tập hợp kiểm thử nghiệm thu; các kiểm tra cần thiết vẫn được viết/chạy cùng từng task kỹ thuật trước đó.

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
| review-log E02 | Hash/kích thước CSV hiện tại khác bản lịch sử; chuyển LF→CRLF trong bộ nhớ khớp đúng hash/kích thước E02 | Ghi cả hai dấu vết tại [data-contract](docs/data-contract.md#source-check). Không coi byte hiện tại giống byte lịch sử, không sửa xuống dòng để ép khớp |
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
