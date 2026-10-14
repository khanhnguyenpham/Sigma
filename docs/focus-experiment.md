# Thử nghiệm riêng LG U+

**CHG-045/E73 — 14/10/2026:** nhánh `cleanup/m2-final` chỉ giữ code M2 final. Xem [bản đồ code hiện hành](../M2_CODE_MAP.md) và [khôi phục code cũ](../M2_CODE_MAP.md#khôi-phục-code-cũ). Các lệnh/đường code M1, M3, V13 và thử nghiệm bên dưới là lịch sử, cần nhánh backup để chạy; dữ liệu, kết quả, bằng chứng và tiêu chí nghiệm thu không đổi.

**Cập nhật tiếp CHG-040/E68:** người dùng cho phép thêm năm giả thuyết ở hai lượt21+26 cấu hình. [Kết quả mới](composition-experiment.md): validation10,616717%, test hồi cứu20,446740%, vẫn chưa<20%; chín tuyến/dashboard/báo cáo khóa nguyên. Phần bên dưới giữ bằng chứng ba lượt E67, không là trạng thái nghiên cứu mới nhất.

CHG-039/E67,11/10/2026; local trên `codex/m2-calendar-forecast`, sau thử nghiệm lịch không cải thiện. Người dùng cho phép tiếp tục tìm MAPE tổng quantity7 ngày South Korea/LG U+<20%, giữ nguyên chín tuyến đã đạt. A08 success/ngày đặt UTC, top10 train, split/H14 và R05 ngày giữ nguyên; test đã xem là hồi cứu.

**Kết quả cuối ba lượt E67:** ứng viên chọn bằng validation đạt MAPE test h1–7 **20,520981%**, so với20,688009% cũ; giảm0,167028 điểm phần trăm, **chưa đạt<20%**. Ba lượt hoàn tất, không thay dashboard hoặc bộ dự báo đã khóa. Chín tuyến cũ giữ nguyên1.656 dòng dự báo và toàn bộ metric tương ứng.

## Đăng ký trước fit

[Config](../M2_CODE_MAP.md#khôi-phục-code-cũ) khóa35 ứng viên:10 mô hình cha × raw/hiệu chỉnh nhân56 ngày prior4;9 đầu sửa residual trên ba cha;6 blend cố định với đối chứng. Mười cha gồm đối chứng, chuẩn hóa28/56 ngày, tỷ lệ quantity/order/basket gần đây, pooled Hàn Quốc, riêng LG U+ và cửa sổ học180 ngày. Chỉ mô hình LG U+ được phép thay trong đầu ra; không thay tham số hoặc output của chín tuyến khác.

Đặc trưng gần đây tính tại origin; label tổng7 phải kết thúc≤cutoff. Các teacher dùng8 hoặc4 tuần không chồng đã quan sát xong. Đầu residual fit weighted ridge cho residual/scale, trọng số tỷ lệ nghịch bình phương actual/scale, prior về0; head affine dùng mức dự báo, không dùng mức actual tương lai. Correction clip±25% scale tại cutoff và forecast≥0. Blend trọng số25%/50% đã khóa. Mã nghiên cứu riêng, không sửa estimator mặc định hoặc dashboard.

Hai cửa sổ lịch sử01–28/10/2024 và01–28/04/2025 chỉ chẩn đoán độ ổn định, top10 tính từ dữ liệu trước origin đầu kỳ. Validation chính vẫn01/07–30/09/2025; chọn MAPE h1–7 ngày dương, MAE rồi model ID, đủ coverage cả hai block. Không đổi tiêu chí dựa trên kết quả lịch sử/test. Khóa lựa chọn bằng hash trước test; chỉ chấm một lựa chọn nếu thắng đối chứng validation, không dùng test để chỉnh lại ứng viên.

Run mới giữ protocol/config/source/package/implementation hash, audit và fit/head logs. Raw, run đối chứng, run lịch, báo cáo published/dashboard/notebook/launcher/Word được đối chiếu hash trước/sau. Chín tuyến khác sao chép dự báo cũ và kiểm **chính xác** sau round trip CSV; kiểm selection và metric tương ứng. Tất cả đầu ra local, không push/upload hoặc đổi checkpoint đã khóa.

## Chạy và kiểm tra

```powershell
.venv\Scripts\python.exe -B -m M2.models.focus_experiment --run-id ten_run_moi
.venv\Scripts\python.exe -B -m pytest M2/models/tests/test_focus_experiment.py --basetemp tmp/focus-tests -o addopts='' -q
```

Năm tests mới đã đạt: chuẩn hóa/feature causal, parity hai đối chứng trên estimator thật, sửa toàn bộ order/quantity sau origin không đổi forecast, kiểm lại teacher/head/application và phát hiện actual log bị sửa, country pool không đọc sale quốc gia khác, blend chọn riêng khớp chạy chung, khóa chín tuyến/round trip CSV chính xác và từ chối thiếu cặp.

## Trạng thái

Lượt1 `m2_focus_20261011` hoàn tất: chọn chuẩn hóa56 ngày/đầu nhân56p4 bằng validation10,775820% so với đối chứng11,632703%. Test hồi cứu20,520981% so với20,688009%, vẫn9/10 và chưa đạt<20%. Giữ nguyên run và kết quả này; không chọn ứng viên khác trong35 bằng test.

Lượt2 đăng ký riêng trước fit theo [m2-hierarchy.json](../M2_CODE_MAP.md#khôi-phục-code-cũ):44 ứng viên gồm36 phân rã country forecast×tỷ trọng LG U+28/56/90 ngày,6 blend50% với ứng viên đã khóa lượt1 và hai đối chứng. Sáu country parents giữ họ LightGBM, thử scale28/56/90, leaf minimum100/30 và bỏ annual ở một cấu hình. Nhãn country là tổng quốc gia trong teacher logs; nhãn/metric đầu ra vẫn LG U+. Tỷ trọng chỉ tính tới origin, không dùng sale quốc gia thực của cửa sổ tương lai. Phải thắng validation10,775820% của lượt1 trước khi khóa/chấm một lựa chọn test. Lượt2 hoàn tất nhưng không thắng validation, không chấm test mới. Hai tests phân bổ/causal/nhãn/future/blend align đã đạt.

Lượt3 [m2-refinement.json](../M2_CODE_MAP.md#khôi-phục-code-cũ) đăng ký24 cấu hình trước fit: chuẩn hóa35/42/49/56/63/70/77/84 ngày, thêm training270/540 ngày, leaves5 và100 cây ở scale56, mỗi cha raw/hiệu chỉnh56p4. Khoảng tìm chọn quanh56 do thắng **validation** lượt1; không chọn cửa sổ từ lỗi test. Giữ cùng tiêu chí, phải thắng10,775820% trước khi khóa/chấm một lựa chọn. Lượt3 hoàn tất nhưng không thắng validation, không chấm thêm test. Đã dừng sau lượt tinh chỉnh hữu hạn này.

Đây là nghiên cứu tuần tự có test đã xem nhiều lần, không phải bằng chứng holdout độc lập. Mọi lượt được giữ, kể cả không đạt; không chọn mô hình theo test để báo cáo thành công.

Yêu cầu nghiệm thu không đổi; R05 ngày/R07/T14 giữ mở.

## Bảng kết quả và đầu ra

| Lượt | Số cấu hình gồm đối chứng | Validation h1–7 tốt nhất % | Test mới |
|---|---:|---:|---|
| [Bám nhu cầu/hiệu chỉnh/pool/blend](../M2/artifacts/m2_focus_20261011/README.md) | 35 | 10,775820 | Một lựa chọn:20,520981% |
| [Tổng Hàn Quốc × tỷ trọng](../M2/artifacts/m2_hierarchy_20261011/README.md) | 44 | 10,775820, giữ đối chứng lượt1 | Không thắng validation, không chấm |
| [Tinh chỉnh quanh56 ngày](../M2/artifacts/m2_refinement_20261011/README.md) | 24 | 10,775820, cùng cấu hình56 ngày | Không thắng validation, không chấm |

Đối chứng validation ban đầu11,632703%; ứng viên chọn `focus_scale56_mul56p4` giữ cùng LightGBM/150 cây/7 lá/học365 ngày/refit7 ngày, chỉ đổi scale chuẩn hóa90→56 ngày và giữ đầu nhân56p4. Cửa sổ lịch sử10/2024 và04/2025 có MAPE16,695279%/11,024749%, là chẩn đoán, không là holdout nghiệm thu.

| Chỉ số LG U+ trên test hồi cứu | Cũ | Ứng viên |
|---|---:|---:|
| MAPE h1–7, origin mỗi ngày % | 20,688009 | 20,520981 |
| MAE h1–7 | 11,436603 | 11,493482 |
| WAPE h1–7 % | 20,926550 | 21,030626 |
| Bias h1–7 | -5,654813 | -5,644805 |
| Coverage h1–7 | 100% | 100% |
| MAPE h1–7, cadence7 ngày % | 21,422030 | 20,667111 |
| MAPE h8–14, origin mỗi ngày % | 18,992036 | 20,156147 |
| MAPE h8–14, cadence7 ngày % | 20,672038 | 22,125581 |

MAPE chính giảm nhẹ nhưng MAE/WAPE và block2 kém hơn; không coi đây là cải thiện đồng đều hoặc kết quả đạt nghiệm thu. Không chấm những ứng viên còn lại trên test để thay lựa chọn đã khóa. Không kết luận bài toán không thể đạt20%; kết luận chỉ giới hạn trong các giả thuyết/budget đã đăng ký.

Đầu ra dùng để rà soát: [CSV dự báo LG U+](../M2/artifacts/m2_focus_20261011/focus_test_predictions.csv), [CSV trước/sau10 tuyến](../M2/artifacts/m2_focus_20261011/before_after_routes.csv), [metric đầy đủ](../M2/artifacts/m2_focus_20261011/overall_test_metrics.csv), [khóa trước test](../M2/artifacts/m2_focus_20261011/selection_lock.json). Mỗi run giữ protocol/config/hash/log/predictions và manifest riêng, không ghi đè lịch sử.

## Kiểm chứng và bàn giao

42 tests liên quan đạt:7 mới cho hai hướng nghiên cứu và35 hồi quy dữ liệu/LightGBM/weekly/calibration; `pip check` đạt. Không chạy lại full suite, SARIMA/Prophet hoặc CI remote. Các CLI đã chạy thật cả ba lượt; không thêm phụ thuộc. Mã nghiên cứu là module riêng, không thay core estimator trong lượt này.

Ba receipt độc lập: [focus](../M2/artifacts/m2_focus_20261011_review.json), [hierarchy](../M2/artifacts/m2_hierarchy_20261011_review.json), [refinement](../M2/artifacts/m2_refinement_20261011_review.json). Đã kiểm412 nhóm metric validation bằng phép tính trực tiếp,42 nhóm phân bổ country/share/blend, phương trình tối ưu residual và cutoff/actual teacher/head; run đối soát thêm nhãn và40 nhóm metric test. Hai đối chứng focus và cấu hình56 lặp lại có chênh forecast lớn nhất0. Chín tuyến có lựa chọn mô hình nguyên, dự báo/metric khớp chính xác; riêng metadata metric validation trong bản selection dẫn xuất lượt1 có round-trip tối đa3,55e-15, không đổi mô hình hoặc forecast và không sửa file selection gốc.

Manifest SHA-256 focus `7723ed69133f0d2a695acdacfdef065fab7d331b2a58e6196c241dce3f5e8204`; hierarchy `bcffdd029836589129764296d3d4cec6b6d4c8f4f1df725a0b516b47e4d23415`; refinement `3859c9023cb4bd87e857ede47b93e076c38e44f90c3d91364b26b7787a98661c`.25/16/15 artifact được seal; lượt cuối kiểm562 tệp protected nguyên hash. Raw vẫn SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`.

T08–T09/T12 đã đồng bộ TASK/PLAN/PROJECTMAP/review-log E67. Nhánh và toàn bộ đầu ra giữ local, chưa commit/push/upload. Phần nghiên cứu hữu hạn đã hoàn tất; mục tiêu<20%, R05 ngày/R07/T14 chưa đạt. Nếu mở nghiên cứu tiếp cần giả thuyết/budget mới dựa trên train/validation và tiếp tục công khai việc test đã xem nhiều lần; không tái dùng kết quả này như holdout độc lập.
