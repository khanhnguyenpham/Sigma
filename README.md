# SIGMA — Dự báo bán và mô phỏng tồn kho

Ứng dụng Streamlit chạy local trên Windows, tích hợp audit dữ liệu, EDA, dự báo 46 tuyến, phân bổ SKU, mô phỏng nhập hàng và cảnh báo. Mã, cấu hình, tests và notebook đã được triển khai; đã có bản nháp Word/slide lịch sử ở local; CHG-012 yêu cầu chỉ tập trung project, chưa làm tiếp tài liệu báo cáo.

**Kết quả ngày 05/10/2026:** bản thử nghiệm `sigma_monthly_v9` dùng snapshot order 2024–2025. Test h1–7 có độ phủ 100%; **0/10 tuyến top 10 đạt MAPE ≤20%**, MAPE khoảng 40,93–58,13%. Dự án còn đang hoàn thiện, chưa nghiệm thu toàn bộ bài. Không sửa actual hoặc chọn lại mô hình bằng test.

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
git clone --branch codex/sigma-local-pipeline https://github.com/khanhnguyenpham/Sigma.git
cd Sigma
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
```

Nếu `python` trỏ tới phiên bản khác, dùng đường dẫn Python 3.14 đã cài. Không cần activate môi trường. `requirements.txt` khóa phiên bản; `requirements-demo.txt` tham chiếu cùng môi trường để demo không khác phép tính.

Mã hiện hành ở nhánh `codex/sigma-local-pipeline`, PR số 1 còn draft; các lệnh trên clone đúng nhánh có sản phẩm. Chưa coi main đã nhận mã hoặc PR đã được review/merge.

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
- Trigger `closing_on_hand < ROP`; IP tính lượng đặt, không thay trigger. Nhận đầu ngày UTC, xử lý sale theo order_datetime/order_id và quyết định cuối ngày. `inventory_events.csv` ghi từng giao dịch, `inventory_ledger.csv` đối soát item/ngày; không mô phỏng receipt nội ngày, FIFO hoặc thay thế SKU.
- Có 7 kịch bản cơ sở/stress: cơ sở, một ngày bán về 0, giảm nhiều ngày, tăng bán, nhận thiếu, nhận trễ, không nhận; thêm 6 biến thể độ nhạy. Đây là giả định, không dự đoán được mọi cú sốc bất ngờ. Cảnh báo bất thường phát ra sau khi quan sát và không khẳng định nguyên nhân.
- Kịch bản làm tròn demand về đơn vị nguyên; receipt_fraction áp trên từng lượng đặt và làm tròn xuống. Đơn một sản phẩm với tỷ lệ 50% có thể nhận 0; phần chưa nhận giả định hủy, không tạo backorder thật.
- Đánh giá cảnh báo replay không đặt mới được tách khỏi chính sách có bổ sung hàng. Kết quả tồn mô phỏng không chứng minh hiệu quả vận hành thật.
- Snapshot trạng thái cuối không tái dựng thông tin doanh nghiệp có tại origin thật. Ảnh kickoff và PDF nguồn đang thiếu; triển khai dựa trên PLAN/requirements cùng thông tin người dùng thuật lại, không nhận đã đọc nguồn thiếu.

## Cấu trúc và hướng dẫn

`run.py` điều phối; `src/data.py` audit/chuỗi; `src/models.py` forecast; `src/calendar_models.py` hồi quy mùa vụ; `src/evaluation.py` metric/chọn; `src/inventory.py` tồn/cảnh báo; `src/reporting.py` EDA/demo; `src/common.py` manifest; `app.py` dashboard; `config.json` cấu hình tập trung; `tests/` ca dữ liệu giả và phép tính độc lập.

Đọc [TASK](TASK.md) để xem tiến độ, [PLAN](PLAN.md) để xem phương pháp, [requirements](docs/requirements.md) để xem nghiệm thu, [development](docs/development.md) để kiểm tra/bàn giao, [PROJECTMAP](PROJECTMAP.md) để phân biệt hiện trạng và lịch sử. Quy trình Git solo/nhóm ở [hướng dẫn TXT](HUONG_DAN_LAM_VIEC_NHOM.txt).

GitHub chỉ nhận mã, cấu hình, khóa môi trường, tests với fixture giả, notebook không output và tài liệu. Không đưa CSV thật, `outputs/`, môi trường, token hoặc file đăng nhập vào commit. GitHub Actions chạy tests, pipeline demo giả và AppTest trên Windows sạch; không có dữ liệu thật trên CI. Một lần chạy CI không thay diễn tập giao diện trên máy Windows thứ hai.

## Thử nghiệm context — CHG-013

`validate_context.py` và `src/context_models.py` thử bốn cấu hình có lịch sử tổng quốc gia/toàn hệ thống tại origin. Chỉ chấm validation, chưa được tích hợp selection/forecast/dashboard. Lệnh đã chạy local:

```powershell
& .venv/Scripts/python.exe validate_context.py --source-run sigma_release_v4 --experiment-id context_validation_v1
```

Mỗi experiment-id phải mới để giữ bằng chứng cũ. Script xác minh hash đầu vào từ manifest nguồn, lưu protocol, log cutoff, predictions/metrics/comparison trong outputs riêng. Kết quả: 2/10 tuyến cải thiện validation, 0/10 đạt ≤20%; đầy đủ 623 cặp h1–7 mỗi tuyến/mô hình. Không có dự báo test trong thử nghiệm. Không tự chuyển kết quả này thành run sản xuất.

`alert_opportunity_summary` chẩn đoán sau replay: phân biệt ca hết hàng trước ngày 7 từ origin và ca có cơ hội báo sớm. Đây là diagnostic, không dùng làm feature hoặc thay mẫu số `early_event_rate`. Bộ kiểm thử hiện hành có 53 ca đạt; run v4 vẫn giữ hash/mã lịch sử.

## Bản nháp báo cáo được giữ local

Tệp local trong `reports/M2/`: `SIGMA_Bao_cao_tien_do_M2.docx` (10 trang) và `SIGMA_Slide_bao_cao_M2_ban_giao.pptx` (16 slide, có speaker notes, bảng/biểu đồ chỉnh sửa được). Báo cáo gồm phương pháp, kết quả từng tuyến, tình huống mô phỏng, ma trận R01–R09, giới hạn và kịch bản demo. Word/slide giữ local ngoài Git vì dùng kết quả run riêng tư. Theo CHG-012, giữ bản nháp lịch sử và chưa chỉnh sửa tiếp; người dùng sẽ yêu cầu Word/slide sau. Bản nháp chưa chứng minh nghiệm thu project.

Release có 43 tệp khớp hash manifest, 37 tests đã chạy đạt và 1.100.320 dòng ledger cân bằng. Đánh giá chính vẫn 0/10 tuyến đạt R05; replay chỉ 31,67% sự kiện báo trước ít nhất 7 ngày. Xem review-log E14/E15 để truy vết.

## Run tích hợp v5 — đã kiểm tra kỹ thuật, chưa đạt R05

Config 1.3.0 tích hợp thêm context và phân phối lân cận mùa vụ vào validation, backtest khóa, forecast và tồn. Tối ưu truy cập ledger giữ nguyên công thức/giả định. Script `verify_release.py` kiểm lại metric, forecast, cân bằng ledger, strict trigger/Q, event và môi trường; lưu bằng chứng ngoài run sealed.

Lệnh run và xác minh đã chạy thực:

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_integrated_v5 --validation-cache-run sigma_release_v4
& .venv/Scripts/python.exe verify_release.py --run-id sigma_integrated_v5
```

Tham số `--validation-cache-run` nhập tường minh bằng chứng validation lịch sử cùng source, config lõi, daily/top và hash; không nhập test, không nhận đã chạy lại 37 ứng viên cũ. 10 ứng viên mới chạy fresh, chọn lại chỉ bằng validation. Bỏ tham số này để chạy toàn bộ ứng viên từ đầu. Cache local không đi kèm clone GitHub. `validation_import.json` ghi nguồn/mã/hash cũ. Config v4 giữ ở `config.release-v4.json`. Test cũ đã xem; v5 vẫn 0/10 đạt 20%.

## Run tích hợp v6 — 51 ứng viên, R05 vẫn chưa đạt

Config 1.4.0 thêm bốn mô hình dự báo số đơn và phân phối quantity/đơn chỉ từ lịch sử tại origin. Tác vụ MAPE dùng phân phối compound Poisson; không thay sales target. Ba tuyến chọn count model bằng validation. Config v5 giữ ở `config.integrated-v5.json`.

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_integrated_v6 --validation-cache-run sigma_integrated_v5
& .venv/Scripts/python.exe verify_release.py --run-id sigma_integrated_v6
```

Run v6 nhập 47 bằng chứng validation v5 với lineage, chạy bốn ứng viên mới fresh; test/forecast/tồn chạy lại. 59 tests đạt, 50 tệp sealed, 84 pins đúng và AppTest 0 exception/10 bảng. Test đã xem: 0/10 đạt 20%, MAPE 40,93–58,13%, mean route MAPE 48,22%, độ phủ 100%. Bản kiểm tra tồn theo ngày chưa thay chứng cứ xử lý từng giao dịch; phần bổ sung R06 được ghi riêng và không sửa sealed run v6. Word/slide vẫn chờ yêu cầu lại.

## Run giao dịch v7 — mã hiện hành

Config 1.5.0 và `src/transactions.py` thực hiện receipt đầu ngày rồi từng sale theo UTC timestamp/order_id. Sổ private `inventory_events.csv` chứa ID và không được Git hoặc dashboard export. Sale có lượng yêu cầu mô phỏng, đáp ứng/thiếu và stock trước/sau; lịch sử không sửa. Kịch bản tăng/giảm giữ tổng item/ngày bằng phân bổ số nguyên đã khai báo. Cấu hình L/R/MOQ và receipt quantity có phần thập phân bị từ chối thay vì tự cắt.

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_transaction_v7 --validation-cache-run sigma_integrated_v6
& .venv/Scripts/python.exe verify_release.py --run-id sigma_transaction_v7
```

Run đã kiểm 51 sealed files, 1.100.320 ledger rows, event chronology/stock chain/đối soát audited sales và 84 pins. 75 tests đạt; AppTest 0 exception/10 bảng khi đổi South Korea/KT, origin và h8–14. Forecast, selection, metric và mô phỏng ngày khớp v6; R05 vẫn 0/10. Demo môi trường thứ hai tái lập 14 bảng và kiểm events riêng. Máy thật thứ hai/mentor review vẫn thiếu; không coi hai virtualenv cùng máy thay việc đó.

Các lệnh v5/v6 bên trên ghi lệnh lịch sử tại E17/E19 với mã tương ứng. Mã mới không xác minh được code hash của run cũ; dùng mục v7 và tên run mới khi chạy lại. Không sửa hoặc seal lại run lịch sử. Validation cache chỉ có local; clone sạch có thể bỏ tham số cache để chạy fresh. Prototype cohort CHG-017 hiện chỉ thử validation, chưa tích hợp CLI hoặc nghiệm thu.

## Run composition/cohort v8 — đã kiểm tra

Config 1.6.0 tích hợp bốn cohort candidate, catalog 55. Source identifiers chỉ dùng tính first-seen trong bộ nhớ, không làm input model. Features tổng hợp cutoff origin; order-date-plus-validity chỉ là proxy thử nghiệm, không là activation/expiry/gia hạn đã xác nhận. Giá/validity không hợp lệ là covariate thiếu, không loại sale hợp lệ.

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_cohort_v8 --validation-cache-run sigma_transaction_v7
& .venv/Scripts/python.exe verify_release.py --run-id sigma_cohort_v8
```

51 evidence validation cũ nhập với lineage, bốn cohort chạy fresh. 51.520 dự báo cohort khớp prototype 1e-8; lựa chọn mới ở TrueMove H/SKT chỉ dựa validation. 83 tests đạt; 53 sealed files; 265.985 events và 1.100.320 ngày/item/scenario đối soát; AppTest 0 exception/10 bảng. Demo .venv-verify tái lập 14 bảng và kiểm events. Test đã xem: 0/10 đạt, mean route MAPE 48,05%, range 40,93–58,13%; coverage 100%. Replay early-event-rate 31,29%, base fill rate 82,63%. Không đánh dấu toàn bài đạt. Config v7 giữ ở config.transaction-v7.json. Các lệnh v7 cũng thuộc mã/run lịch sử khi chuyển sang v8; dùng run-id mới, không sửa sealed evidence.

## Run v9 hiện hành — tháng, origin và demo độc lập

Config 1.7.0 có 57 ứng viên; hai countmonth_365/all dùng lịch weekday/month biết trước tại origin. 55 validation evidence v8 nhập có lineage, hai monthly chạy fresh; 25.760 cặp khớp prototype 1e-8. Config cũ giữ ở config.cohort-v8.json. Run-id mới, không sửa hoặc resume sealed run bằng mã khác.

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_monthly_v9 --validation-cache-run sigma_cohort_v8
& .venv/Scripts/python.exe verify_release.py --run-id sigma_monthly_v9
```

Các lệnh v8 phía trên là lịch sử của mã v8. Với clone mới không có validation cache, bỏ --validation-cache-run để tính validation từ đầu. Chặn origin tương lai/không là ngày UTC đã chốt/thiếu actual tuyến; tháng 01/2026 chưa có actual. Demo mới giữ synthetic_orders.csv riêng trong outputs/<run_id>, manifest ghi nguồn thật dùng; resume không sinh lại hoặc ghi đè nguồn đã mất/đổi. AllocationPlan dùng lại đúng vector causal cho các scenario; stale matrix/forecast/window bị chặn, công thức tồn giữ nguyên.

92 tests đạt, 55 sealed files, 266.091 events/13 scenario và 1.100.320 ledger đối soát. Verify tái tính daily quantity, train top10, selection validation-only, actual test/forecast từ nguồn audited, rồi metric/stock/trigger/Q/hash/84 pins. Demo môi trường thứ hai tái lập 14 bảng, nguồn riêng được seal/verify; AppTest real Thailand/AIS và demo Vietnam/Vinaphone 0 exception/10 bảng, origin 31/10/2025, h8–14. Hai môi trường trên cùng máy chưa thay kiểm thử máy khác.

R05 vẫn 0/10: mean route MAPE 46,496812%, range 38,662919–58,134251%, coverage 100%; test đã xem và đánh giá lại, chưa là kiểm định độc lập mới. Replay early-event-rate 32,263690%, base fill 83,373% là mô phỏng, không bảo đảm mọi ca. Không gọi toàn bài hoàn thành; Word/slide chưa làm tiếp.
