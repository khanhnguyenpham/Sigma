# Thử nghiệm lịch lễ M2

Ngày11/10/2026, CHG-038/E66; nhánh local `codex/m2-calendar-forecast`. Nghiên cứu T04/T08–T09/T12, ưu tiên tổng quantity7 ngày của South Korea/LG U+. Target A08 success/ngày đặt UTC, top10 train, split và R05 ngày giữ nguyên. Các thay đổi chưa commit trước lượt này được giữ.

## Dữ liệu và CSV

- [Lịch đủ ngày](../data/reference/calendar_features.csv): 2.980 dòng =745 ngày×4 điểm đến,01/01/2024–14/01/2026. Có thứ/tuần ISO/tháng/quý/ngày trong năm/cuối tuần; lễ Việt Nam và điểm đến, kỳ lễ, nghỉ bù, khoảng cách clip15 ngày, trước/sau7 ngày, nguồn và ngày công bố/truy cập. Khoảng cách15 nghĩa là ngoài14 ngày, không phải khoảng cách chính xác. Trước lễ này và sau lễ khác có thể cùng đúng.
- [Catalog sự kiện](../data/reference/calendar_features.events.json): có lịch đệm14 ngày hai đầu và ngày công bố riêng từng sự kiện. CSV là tham chiếu hồi cứu; mô hình phải lọc catalog tại origin trước khi tính lại cờ/khoảng cách. Provider đọc CSV để kiểm lưới và lấy cờ mùa, đọc catalog để dựng lịch có sẵn tại origin.
- [Đỉnh train](../M2/artifacts/m2_calendar_analysis_20261011/sales_peaks.csv): 1.768 dòng gồm đỉnh ngày và cửa sổ7 ngày, có thể chồng nhau. LG U+ có118 đỉnh ngày/40 cửa sổ tuần. Quantity/order_count/nền/mức tăng/lễ liên quan chỉ dùng EDA, không làm feature tương lai.
- [Tổng hợp lễ/mùa](../M2/artifacts/m2_calendar_analysis_20261011/train_calendar_summary.csv), [đối chiếu cùng thứ](../M2/artifacts/m2_calendar_analysis_20261011/train_matched_holidays.csv). Đối chiếu cùng thứ dùng ngày thường±56 ngày chỉ bên trong train; đây là mô tả hồi cứu, không là feature causal.

Raw được audit lại đủ100.000 dòng,93.104 dòng success,118.296 quantity và46 tuyến; không dedup loại dòng nào. Hash nguồn `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. Tạo33.626 dòng ngày, tổng quantity bảo toàn. Phạm vi giả định quan sát đầy đủ giữ như config cũ; không suy thiếu nguồn thành0.

Đỉnh ngày dùng quy tắc hiện có: lịch sử28 ngày không gồm ngày hiện tại, tối thiểu14 ngày, robust-z≥4 hoặc tăng≥50% và chỉ lấy phía tăng. Bổ sung trung vị cùng thứ tám tuần trước. Tổng7 so trung vị tám cửa sổ tuần trước không chồng; chỉ gắn cờ khi đủ tám tuần, cùng ngưỡng. Nền0 giữ tỷ lệ tăng trống, không sinh vô cực. Không loại đỉnh/ngày0 khỏi metric.

## Nguồn và giả thuyết

Nguồn công khai được tra cứu riêng, không gửi bản ghi order/customer ra ngoài. Nguồn/ngày có sẵn được khóa trong [config](../data/configs/m2-calendar.json); dùng `holidays==0.105` đã cài.

- Lịch nghỉ Việt Nam2024/2025 và kỳ nghỉ đầu2026: Báo Chính phủ; nghỉ hoán đổi29/04/2024 chỉ có sẵn từ nguồn12/04/2024. Lịch công chức gồm cuối tuần, không chứng minh mọi khách nghỉ cùng lịch.
- Hàn Quốc01/10/2024,27/01/2025,03/06/2025: Korea.net có nguồn ghi ngày công bố. Dùng ngày bài đăng bảo thủ, không tự suy ngày thông tin có sẵn sớm hơn. Ví dụ27/01 chỉ vào feature từ15/01/2025.
- China2024/2025: thông báo lịch năm của State Council; lịch2025 chỉ dùng từ12/11/2024. Chỉ kỳ nghỉ Việt Nam được bổ sung dải cuối tuần công chức; các quốc gia khác giữ định nghĩa ngày lễ của thư viện, không nhận đây là toàn bộ ngày nghỉ du lịch.
- Japan: đối chiếu quy tắc với Cabinet Office. Các ngày lặp lại của thư viện được **giả định** có sẵn trước kỳ quan sát, không nhận đã xác minh từng ngày hoặc có snapshot lịch lịch sử.
- Thailand: nguồn PRD xác minh kỳ Songkran2024; ngày bridge thiếu bằng chứng ngày công bố giữ `unverified_announcement_excluded` và loại khỏi model. Không đưa cờ chính ngày chưa biết vào feature.
- Hè6–8 là giả thuyết thị trường xuất phát Việt Nam, nhưng order không có quốc gia xuất phát. Xuân3–5/thu9–11 cho Japan/South Korea dựa cửa sổ mùa rộng của JNTO/VISITKOREA, không phải số khách thực tế hoặc ngày hoa nở dự báo. Country-specific peak season khác chưa được tự bổ sung.

Ngày bán là UTC; lễ được ghép theo nhãn ngày dân sự quốc gia, không suy thời điểm/ngày khởi hành thực tế. Các trùng hợp trong EDA không chứng minh quan hệ nhân quả. Ví dụ LG U+ có30 ngày lễ điểm đến trong train, chỉ5 ngày bị gắn cờ tăng và25 ngày không tăng theo quy tắc trên.

## Protocol chạy

```powershell
.venv\Scripts\python.exe -B -m M2.models.calendar_experiment --run-id ten_run_moi --stage analyze
.venv\Scripts\python.exe -B -m M2.models.calendar_experiment --run-id ten_run_khac
.venv\Scripts\python.exe -B -m pytest M2/models/tests/test_calendar_experiment.py -q
```

Tên run phải mới. File lịch đã có chỉ được tái dùng nếu nội dung và catalog khớp; run giữ bản sao lịch riêng cùng hash. CLI không đổi checkpoint/dashboard hoặc push.

Năm nhóm `none/vn/destination/both/both_season`, mỗi nhóm mô hình cha ratio7 và đầu hiệu chỉnh56 ngày/prior4 tuần:10 cấu hình. LightGBM pooled top10, giữ tham số/seed/refit/units gốc. Cờ lễ/mùa đếm toàn bộ7 ngày mục tiêu; khoảng cách lấy min. Cờ lịch không chia theo scale quantity. Nhãn fit/teacher/head phải kết thúc≤cutoff; ngày công bố lọc tại origin của từng mẫu, không dùng lịch biết tại cutoff muộn để sửa lại mẫu quá khứ.

Đối chứng `lgbm_annual_ratio7` và `lgbm_cal_ratio7_56_p4` phải khớp dự báo validation của run `m2_reproduce_20261009_full` ở dung sai tuyệt đối1e-8. Chọn LG U+ bằng MAPE validation block1,MAE rồi model ID; full coverage cả hai block. Chín tuyến khác giữ lựa chọn/dự báo từ run đã seal, kiểm lại hash/actual/metric.

Không cải thiện validation so với đầu hiệu chỉnh hiện tại thì dừng, không chấm test mới. Có cải thiện thì ghi `selected_models.csv` và `selection_lock.json` trước test, chỉ chấm lựa chọn đã khóa. Báo MAPE/MAE/WAPE/bias/coverage theo block/cadence, thêm nhóm dịp lễ/ngày thường và ổn định tháng validation. Test đã xem là hồi cứu. Ngưỡng mục tiêu mới LG U+<20%; R05 ngày không thay thế.

## Kết quả đã kiểm ngày 11/10/2026

Run [m2_calendar_20261011](../M2/artifacts/m2_calendar_20261011/README.md) hoàn tất,20 artifact đã seal. Không nhóm lịch nào cải thiện MAPE validation h1–7 của LG U+ so với đối chứng hiệu chỉnh. Vì vậy không chấm test mới, không tích hợp vào dashboard và không đạt mục tiêu giảm test xuống<20%. Mốc test hồi cứu hiện có vẫn20,688009%,9/10 tuyến; R05 ngày/R07/T14 giữ mở.

| Nhóm feature | MAPE trực tiếp % | MAPE hiệu chỉnh % |
|---|---:|---:|
| Đối chứng hiện tại | 11,636178 | **11,632703** |
| Lễ Việt Nam | 11,754667 | 11,754667 |
| Lễ điểm đến | 12,122517 | 12,109701 |
| Cả hai | 11,911011 | 11,911011 |
| Cả hai và mùa | 12,123005 | 12,123005 |

Tất cả ứng viên đủ coverage100% cả hai block. Đây là validation, không phải MAPE test mới. Lễ Việt Nam có MAE6,683866 thấp hơn đối chứng6,709092, nhưng MAPE kém hơn nên không được chọn. [Bảng đủ MAPE/MAE/WAPE/bias/coverage](../M2/artifacts/m2_calendar_20261011/validation_metrics.csv) gồm cả h8–14 và cadence không chồng; [nhóm lễ/ngày thường](../M2/artifacts/m2_calendar_20261011/validation_calendar_strata.csv) chỉ dùng chẩn đoán. Chín tuyến khác giữ lựa chọn cũ.

[Kiểm chứng trong run](../M2/artifacts/m2_calendar_20261011/verification.json):18.400 nhãn/dự báo,400 nhóm metric và1.400 cặp hiệu chỉnh được đối soát;3.680 cặp đối chứng lệch tối đa1,4211e-14, nhỏ hơn dung sai1e-8. Raw và498 tệp được bảo vệ (run cũ, báo cáo published, dashboard/notebook/launcher, Word hiện có) nguyên hash. [Receipt kiểm lại độc lập](../M2/artifacts/m2_calendar_20261011_review.json) xác minh seal, mã/config, lưới lịch, top10 train, quantity,400 nhóm metric bằng phép tính trực tiếp, lựa chọn nguyên và không có lượt test mới.

35 tests liên quan đạt:8 mới và27 sẵn có, chọn dữ liệu/LightGBM/weekly/calibration, không chạy lại các fixture SARIMA/Prophet. Hai ca dashboard ban đầu lỗi quyền tạo thư mục temp đã chạy lại đạt với `--basetemp tmp/calendar-pytest-20261011`. `pip check` đạt; không nhận full suite hoặc CI remote đã chạy. Audit sandbox/native đều hoàn tất.

Manifest SHA-256 `42450c2efdbaf08851ad1fe228b95efa0a725520352d4b5b79fce3acd4a3ebf2`; lịch `58f947e922ab257433ccc6a782deb4596b66f8a2412e93ff3913a31f7628f611`; đỉnh `595245a9c6b151cb5bd6a2c063a2ad9044a5bc84edb25ce88e2cc95a90aec872`. CSV lịch và catalog phải đi cùng nhau. Phần “unresolved” trong config nói trạng thái nguồn trong catalog, không phải feature cho mô hình.

T04/T08–T09/T12 đã đồng bộ ở TASK/PLAN/PROJECTMAP và E66; yêu cầu nghiệm thu không đổi. Bước tiếp theo nếu tiếp tục nghiên cứu là đăng ký một giả thuyết mới dựa trên train/validation; không chỉnh lịch hoặc chọn lại ứng viên bằng test đã xem.
