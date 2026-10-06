# Lịch sử README trước CHG-027 — không dùng làm hướng dẫn hiện hành

# SIGMA — Dự báo bán và mô phỏng tồn kho

**Tiến độ tiếp 05/10/2026 — CHG-026/E40–E41:** V6 validation 10/10 nhưng test tuần hồi cứu còn 9/10 (LG U+ 21,36%); V7 đang chạy, chưa nhận đạt. Chính sách tồn liên tục từ tuần V5 đã chạy đủ 13 kịch bản/93 origins H14 và đối soát độc lập 1.100.320 dòng ledger, base fill 85,04%; early replay 33,73% giữ nguyên mẫu số. 160 tests pass; năm trang AppTest không exception. Sản phẩm hiện vẫn chọn V5 trong config.delivery.json tới khi run mới hoàn tất/kiểm lại. R05 ngày/R07/T14 còn mở; không làm Word/slide hoặc nhận bản so sánh chính thức/đợt tổ chức lại code đã xong. Đoạn E37–E39 bên dưới là lịch sử trước E41.

**Cập nhật 05/10/2026 — CHG-024/025, E37–E39:** đã áp dụng **khách đặt D → giao D+7 ngày lịch UTC**, không trễ giao, gồm cuối tuần; không đổi lead time nhập kho. Người dùng mô tả snapshot order là giả định; đây là nguồn thuật lại, vẫn giữ dữ liệu/outputs private và raw nguyên. [Sản phẩm chung và lịch giao](../customer-delivery.md) mở bằng `start_product.ps1` tại cổng 8503. Run tuần hiện hành `sigma_weekly_calibrated_v5`: test hồi cứu **9/10**, mean **15,97%**, LG U+ **21,36%**; chọn validation rồi khóa trước test. 920 khuyến nghị tồn từ phân bổ tuần đã đối soát, replay cùng 5.520 cửa sổ báo sớm **33,73%**; chưa chạy lại toàn bộ chính sách liên tục bằng tuần. 150 tests đạt, AppTest năm trang/không exception; job refresh/skip chạy thật, script đăng ký lịch nền được chuẩn bị nhưng chưa cài. R05 ngày **0/10**, R07/T14 vẫn mở. **Sau khi đủ điều kiện nghiệm thu mới làm bản so sánh chính thức ngày/tổng 7 ngày và tổ chức lại code**, đúng thứ tự người dùng yêu cầu; chưa làm lại Word/slide. Những cập nhật E36/v1 bên dưới là lịch sử.

**Phương án tổng 7 ngày đã chạy (CHG-023/E36):** [hướng dẫn và kết quả tuần](../weekly-forecast.md). Test hồi cứu tuần h1–7: 9/10 top 10 đạt 20%, mean 17,19%; AIS còn 22,14%. Chạy `.\start_weekly_dashboard.ps1 -RunId sigma_weekly_v1` để xem tại cổng 8502. MAPE tuần chưa thay tiêu chí ngày; run ngày v11 và R05/R07 giữ trạng thái bên dưới. [Ảnh kickoff nhận lại](../kickoff-checklist.md) đã đọc trực tiếp tại E35.

Ứng dụng Streamlit chạy local trên Windows, tích hợp audit dữ liệu, EDA, dự báo 46 tuyến, phân bổ SKU, mô phỏng nhập hàng và cảnh báo. Mã, cấu hình, tests và notebook đã được triển khai; đã có bản nháp Word/slide lịch sử ở local; CHG-012 yêu cầu chỉ tập trung project, chưa làm tiếp tài liệu báo cáo.

**Kết quả ngày 05/10/2026:** bản thử nghiệm `sigma_scaled_v11` dùng snapshot order 2024–2025. Test h1–7 có độ phủ 100%; **0/10 tuyến top 10 đạt MAPE ≤20%**, MAPE khoảng 41,89–58,13%. Dự án còn đang hoàn thiện, chưa nghiệm thu toàn bộ bài. Không sửa actual hoặc chọn lại mô hình bằng test.

**Tinh chỉnh:** V2 thêm 8 robust và 4 LightGBM weighted-L1; V3 thêm 12 hồi quy lịch (37 ứng viên tổng cộng trên mỗi top 10). Chọn bằng validation, giữ 0/10 đạt. Test cũ được sử dụng lại, không phải kiểm định độc lập. Mean MAPE từng tuyến v1 50,53%; v2 48,35%; v3 49,03%. Không chọn V2 chỉ vì test tốt hơn; bản release dùng lựa chọn theo validation của V3. EDA lễ giữ nhóm unknown và mẫu số, không suy nhân quả.

## Chạy nhanh trên máy hiện tại

Mở PowerShell trong thư mục project, chạy:

```powershell
.\start_product.ps1
```

Mở địa chỉ `http://127.0.0.1:8503` để dùng menu sản phẩm chung. Xem [lịch giao và job local](../customer-delivery.md). Launcher cũ `start_dashboard.ps1` vẫn mở riêng phần ngày/tồn tại cổng 8501. Launcher chọn run thật hoàn tất mới nhất; chọn `sigma_scaled_v11` để xem run hiện hành và `demo_scaled_v11_verify` để xem demo giả. Các run v1–v10 giữ làm lịch sử. Dashboard có sáu tab: bán & dự báo, đánh giá, tồn & đặt hàng, cảnh báo, kịch bản, audit & giới hạn. Chạy pipeline trước khi mở dashboard trên máy mới.

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

## Chạy snapshot order local

Đặt bản CSV được phép sử dụng tại `data/sigma_sim_data_orders.csv`, giữ nguyên byte. Clone GitHub không tải dữ liệu này. Đọc [data/README](../../data/README.md) và [data-contract](../data-contract.md) trước khi đổi nguồn.

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

`--resume` chỉ chấp nhận cùng input/config/mã/mode, bỏ qua stage đã hoàn tất. Stage thất bại sẽ chạy lại; không ghi đè run khác. Nếu đổi cấu hình hoặc mã, tạo run-id mới. Dashboard từ chối run chưa hoàn tất hoặc artifact sai hash. Notebook [run_local](../../notebooks/run_local.ipynb) gọi cùng API với CLI và không chứa output riêng tư.

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

Đọc [TASK](../planning/TASK.md) để xem tiến độ, [PLAN](../planning/PLAN.md) để xem phương pháp, [requirements](../requirements.md) để xem nghiệm thu, [development](../development.md) để kiểm tra/bàn giao, [PROJECTMAP](../planning/PROJECTMAP.md) để phân biệt hiện trạng và lịch sử. Quy trình Git solo/nhóm ở [hướng dẫn TXT](../archive/HUONG_DAN_LAM_VIEC_NHOM.txt).

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

## Run v9 — lịch sử đã kiểm tra, tháng, origin và demo độc lập

Config 1.7.0 có 57 ứng viên; hai countmonth_365/all dùng lịch weekday/month biết trước tại origin. 55 validation evidence v8 nhập có lineage, hai monthly chạy fresh; 25.760 cặp khớp prototype 1e-8. Config cũ giữ ở config.cohort-v8.json. Run-id mới, không sửa hoặc resume sealed run bằng mã khác.

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_monthly_v9 --validation-cache-run sigma_cohort_v8
& .venv/Scripts/python.exe verify_release.py --run-id sigma_monthly_v9
```

Các lệnh v8 phía trên là lịch sử của mã v8. Với clone mới không có validation cache, bỏ --validation-cache-run để tính validation từ đầu. Chặn origin tương lai/không là ngày UTC đã chốt/thiếu actual tuyến; tháng 01/2026 chưa có actual. Demo mới giữ synthetic_orders.csv riêng trong outputs/<run_id>, manifest ghi nguồn thật dùng; resume không sinh lại hoặc ghi đè nguồn đã mất/đổi. AllocationPlan dùng lại đúng vector causal cho các scenario; stale matrix/forecast/window bị chặn, công thức tồn giữ nguyên.

92 tests đạt, 55 sealed files, 266.091 events/13 scenario và 1.100.320 ledger đối soát. Verify tái tính daily quantity, train top10, selection validation-only, actual test/forecast từ nguồn audited, rồi metric/stock/trigger/Q/hash/84 pins. Demo môi trường thứ hai tái lập 14 bảng, nguồn riêng được seal/verify; AppTest real Thailand/AIS và demo Vietnam/Vinaphone 0 exception/10 bảng, origin 31/10/2025, h8–14. Hai môi trường trên cùng máy chưa thay kiểm thử máy khác.

R05 vẫn 0/10: mean route MAPE 46,496812%, range 38,662919–58,134251%, coverage 100%; test đã xem và đánh giá lại, chưa là kiểm định độc lập mới. Replay early-event-rate 32,263690%, base fill 83,373% là mô phỏng, không bảo đảm mọi ca. Không gọi toàn bài hoàn thành; Word/slide chưa làm tiếp.

## Run v10 — lịch sử đã kiểm tra, aggregate arrivals và tỷ trọng tuyến

Config 1.8.0, catalog 59; giữ config v9 tại config.monthly-v9.json. Hai hiercount dùng aggregate order arrivals dự báo từ lịch biết trước, phân bổ bằng historical-month/recent route shares tại origin; basket quantity chuyển sang forecast sales quantity. Không dùng tổng actual tương lai; coherence chỉ áp dụng expected order counts trước sales action, không nhận tổng quantity forecast bằng tổng order count. 57 evidence validation v9 nhập có lineage; hai ứng viên mới chạy fresh, 25.760 cặp khớp prototype 1e-8.

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_hierarchical_v10 --validation-cache-run sigma_monthly_v9
& .venv/Scripts/python.exe verify_release.py --run-id sigma_hierarchical_v10
```

Clone mới không có validation cache thì bỏ --validation-cache-run và dùng run-id mới. Lệnh v9/v8 phía trên là lịch sử mã tương ứng; không sửa/resume sealed run bằng mã mới. Verify tái tính cả nhãn quantity và metric của toàn bộ validation predictions, kể cả evidence nhập; kiểm train top/selection/actual test và forecast, hash, stock/event/day/Q. 101 tests đạt; 57 sealed files, 266,469 events, 1.100.320 ledger, 84 pins. Demo nguồn riêng tái lập 14 bảng, verify/AppTest real và demo 0 exception/10 bảng.

R05 vẫn 0/10, MAPE 38,58–58,13%, mean route MAPE 46.503945%, coverage 100%. Có tuyến test tốt hơn và kém hơn v9; không chọn lại bằng test. Test đã xem, chưa là kiểm định độc lập mới. Replay early-event-rate 33.135682%, base fill 83.755010% là mô phỏng. Chưa nghiệm thu toàn bài; Word/slide chưa làm tiếp.

**Kiểm bổ sung E29:** Verify yêu cầu đủ từng cặp origin–horizon cho mỗi model/tuyến validation, giữ tail ngoài split có actual trống và missing forecast chỉ được giữ nếu candidate đã có log failure/excluded. 101 tests đạt; real/demo verify lại, không thay model, forecast hoặc sealed run.

## Run v11 hiện hành — chuẩn hóa feature và kiểm tra dữ liệu độc lập

Config 1.9.0, 61 ứng viên production; config v10 lưu ở config.hierarchical-v10.json. Tám prototype monthly weighted-L1 đã đánh giá trên validation; hai cấu hình có lợi tích hợp, sáu cấu hình không cải thiện giữ riêng. StandardScaler fit chỉ trên lịch/feature đến cutoff mỗi lần refit. Loss dùng trọng số 1/quantity ngày dương, quantity gốc giữ đơn vị khi forecast/chấm; ngày zero giữ trong MAE/WAPE/bias. Chọn bằng validation, khóa trước test.

```powershell
& .venv/Scripts/python.exe run.py --run-id sigma_scaled_v11 --validation-cache-run sigma_hierarchical_v10
& .venv/Scripts/python.exe verify_release.py --run-id sigma_scaled_v11
& .venv/Scripts/python.exe check_data.py --run-id sigma_scaled_v11 --output-id sigma_scaled_v11_data_quality
```

Clone mới bỏ --validation-cache-run để fit validation từ đầu; dùng run-id/output-id mới. Các lệnh v10 trở về trước thuộc mã lịch sử, không resume sealed run bằng mã mới. check_data.py kiểm độc lập từ raw CSV tới quantity/order_count ngày UTC và top10 train, xuất normalized_train_covariates.csv chỉ train, không order/customer ID, numeric/validity/revenue flags. Source và route/item labels giữ nguyên; invalid covariate có cờ, sale hợp lệ vẫn giữ. Output riêng dưới outputs và không ghi đè thư mục cũ. Toàn bộ output vẫn private local. CI chỉ dùng nguồn giả.

107 tests đạt, 59 sealed files; 266,222 events/13 scenario/1.100.320 ledger/84 pins verified. 25.760 fresh validation pairs khớp hai prototype 1e-8; demo môi trường thứ hai tái lập 14 bảng, AppTest real/demo 0 exception/10 bảng. Chuẩn hóa độc lập xác nhận 93.104 sales/118.296 quantity/66.619 train rows, source hash nguyên.

R05 vẫn 0/10: test MAPE 41,89–58,13%, mean route MAPE 47.589594%, coverage 100%. AIS/SKT được chọn tốt hơn trên validation nhưng test kém hơn v10; không rollback dựa vào test. Test đã xem, chưa kiểm định độc lập mới. Replay early 33.100802%, simulated base fill 83.523297%. Phần mềm chạy đúng và dữ liệu chuẩn hóa không đồng nghĩa đạt độ chính xác 20%; chưa nghiệm thu toàn bài, Word/slide chưa làm tiếp.

## Campaign nghiên cứu E32 — chọn trong train trước khi chấm validation

[validation_campaign.py](../../sigma/experiments/validation.py) chạy riêng khỏi production. Mười tuyến xếp hạng bằng quantity đến 30/04/2025 cho giai đoạn chọn cấu hình; script xác minh chúng khớp top10 train cuối kỳ, không đổi lại danh sách hồi cứu. Tháng 5–6 chỉ là phần tuning nằm trong train; split chính tháng 7–9 và tháng 10–12 giữ nguyên. Lịch sử global/country/route kết thúc origin; đặc trưng cùng kỳ năm trước căn ngày lịch, kể cả năm nhuận. Mọi nhãn fit ≤ cutoff, refit 7 ngày, H14.

```powershell
& .venv/Scripts/python.exe validation_campaign.py --output-id sigma_ablation_campaign_v1
```

Lệnh trên đã chạy thực; dùng output-id mới khi chạy lại. Protocol lưu trước fit, output giữ local; không ghi đè, không sửa config/selected_models/forecast v11. Snapshot gốc được audit, rồi bỏ sales test trước aggregation/features/ranking/fit/scoring. Mười hai cấu hình = lịch/lịch sử/cùng kỳ × quantity gốc/tỷ lệ theo mean90 đến origin × 7/31 leaves. Tỷ lệ chỉ dùng khi học, forecast phục hồi quantity gốc; inverse-label weighted L1 giữ mục tiêu relative error. Ngày 0 vẫn có trong đánh giá. Tham số loss/trees tham chiếu [tài liệu LightGBM](https://lightgbm.readthedocs.io/en/latest/Parameters.html); tách thời gian theo [hướng dẫn scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split).

Kết quả đã đối soát: 102.480 pairs trong train và 154.560 pairs validation, 120 nhóm h1–7 mỗi giai đoạn đủ coverage. Lựa chọn khóa trong train đạt validation mean MAPE 44,968965%, range 36,287133–52,093932%; 0/10 đạt 20%, kể cả chọn lạc quan ứng viên tốt nhất trên validation cũng 0/10. So sánh theo target-day blocks 7 ngày/2.000 draws không thấy cải thiện rõ ràng so v11 trên validation; v11 đã chọn bằng chính validation nên so sánh này không độc lập. Không tích hợp 12 cấu hình và không chạy lại test. Tổng 111 tests pass, production v11/source/sealed files nguyên. Đây là bằng chứng một đợt thử chưa đạt, không là chứng minh mọi mô hình đều không thể đạt R05.

## Hiệu chỉnh/kết hợp E34 — nghiên cứu chưa tích hợp

[calibrate_campaign.py](../../sigma/experiments/calibration.py) kiểm tra phối hợp không âm, affine weighted-LAD và affine có regularization trên dự báo causal đã lưu của E32. Học head trên nhãn tháng 5, chọn trên origins/target tháng 6 nằm trong train, khóa theo tuyến trước khi chấm validation. Sau đó head refit mỗi 7 ngày bằng các nhãn OOF đã qua cutoff; không đổi target, top10, split chính hoặc metric. Không cần train lại 12 base models nhưng cần output E32 local có hash khớp; clone mới chưa có cache phải chạy workflow E32 trước.

```powershell
& .venv/Scripts/python.exe calibrate_campaign.py --output-id sigma_calibration_campaign_v2
& .venv/Scripts/python.exe verify_calibration.py --run-id sigma_calibration_campaign_v2 --output-id sigma_calibration_verification_v1
```

Các lệnh đã chạy, chạy lại phải chọn id mới. Đối soát độc lập từ raw orders tới daily quantity/11.970 cặp/metric/trọng số đã khớp; 623 cặp h1–7/tuyến, 574 h8–14/tuyến. Toàn suite 115 tests đạt. Validation vẫn 0/10 đạt 20%, range 38,636338–52,101122%, mean 45,106266% so v11 41,978903%; không tích hợp và không chấm test mới. Raw và 59 sealed files v11 giữ nguyên. Train diagnostic chỉ đánh giá biến động và calendar fit in-sample, không phải dự báo hợp lệ hoặc chứng minh mọi mô hình đều không thể đạt. R05/R07 và nghiệm thu toàn bài còn mở.
