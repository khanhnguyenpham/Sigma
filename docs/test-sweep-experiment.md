# Chấm toàn bộ cấu hình LG U+ trên test — CHG-041/E69

Ngày11/10/2026, người dùng yêu cầu chấm test toàn bộ cấu hình, không cần thắng MAPE validation thấp nhất. Phạm vi mới cho phép so sánh hồi cứu tất cả ứng viên của sáu lượt trước; protocol và lựa chọn validation cũ giữ nguyên theo lịch sử. Bảng xếp hạng test phục vụ khám phá, không là đánh giá độc lập hoặc thay lựa chọn chính thức.

**Đã hoàn tất local:** chấm đủ160 lượt cấu hình, có17 lượt MAPE test h1–7<20%, coverage100%. Tốt nhất `tune56_w540_mul56p4` đạt **19,26589984972207%**, so với20,688009% đối chứng ban đầu và20,446740% lựa chọn validation mới nhất. Đây là ứng viên được nhận diện bằng test; lựa chọn chính thức, chín tuyến và dashboard/bộ báo cáo khóa giữ nguyên.

| Nhóm | Lượt cấu hình | Lượt test<20% | MAPE test tốt nhất | Validation của bản đó |
|---|---:|---:|---:|---:|
| Lịch lễ/mùa | 10 | 0 | 20,197995% | 12,123005% |
| Chuẩn hóa, pool, residual, blend | 35 | 5 | 19,688426% | 11,269570% |
| Tổng Hàn Quốc, tỷ trọng, blend | 44 | 0 | 20,520981% | 10,775820% |
| Cửa sổ chuẩn hóa và độ phức tạp | 24 | 12 | **19,265900%** | 11,336558% |
| Tuổi dữ liệu và refit | 21 | 0 | 20,520981% | 10,775820% |
| Cơ cấu đơn và count × basket | 26 | 0 | 20,130274% | 11,870341% |
| Tổng, gồm đối chứng lặp | 160 | 17 | | |

160 là số lượt cấu hình, có đối chứng và dự báo trùng nhau; đối soát nhận diện100 bộ dự báo hai block khác nhau tại dung sai1e-8, trong đó10 bộ có MAPE h1–7<20%. Không coi17 lượt đạt là17 bằng chứng độc lập. Bản `tune56_w540_raw` đồng hạng về toàn bộ forecast h1–7 và metric chính; h8–14 hơi khác.

## Cấu hình đạt và giới hạn

Bản tốt nhất học pooled top10 với cửa sổ540 ngày thay365, chuẩn hóa theo56 ngày, feature annual hiện có, LightGBM150 cây/7 lá/min-child100/learning-rate0,03/lambda10/seed42 và refit7 ngày. Giữ weighted-L1 và đầu nhân56 ngày/prior4 tuần. Không thêm lịch lễ hoặc feature cơ cấu đơn vào bản này. Toàn bộ nhãn học/teacher hoàn tất trước cutoff; dài cửa sổ học không cho phép đọc tương lai.

Validation11,336558% không thắng mốc10,775820% tại lượt refinement, nên bản này chưa được chấm test trong E67. Yêu cầu mới cho chấm mọi ứng viên phát hiện kết quả test thấp hơn; điều đó không biến test thành holdout độc lập. Lựa chọn đã khóa `composition_both56_mul56p4` vẫn có test20,446740% theo E68, không bị ghi đè bằng bản thắng test.

| Cửa sổ/cadence của bản tốt nhất | MAPE | MAE | WAPE | Bias | Coverage | Số cặp |
|---|---:|---:|---:|---:|---:|---:|
| h1–7, origin hàng ngày | **19,265900%** | 10,529504 | 19,266752% | -3,749518 | 100% | 86 |
| h1–7, không chồng lấn | 18,429381% | 9,857562 | 18,023672% | -3,373482 | 100% | 13 |
| h8–14, origin hàng ngày | 20,255792% | 11,173259 | 20,217304% | -3,890088 | 100% | 79 |
| h8–14, không chồng lấn | 20,990611% | 11,277809 | 20,289912% | -3,926234 | 100% | 12 |

h1–7 cải thiện1,422109 điểm phần trăm so với đối chứng ban đầu; MAE/WAPE/bias cũng tốt hơn. H8–14 còn>20% và kém mốc ban đầu18,992036%; không nhận cải thiện mọi horizon. Phân tầng lịch hồi cứu h1–7:16 cửa sổ có lễ đạt10,180162%,70 cửa sổ thường21,342640%, coverage100% mỗi nhóm. Không dùng phân tầng này làm feature/chọn model hoặc suy ra quan hệ nhân quả.

Danh sách model lấy từ bảng validation đã seal và đối chiếu config trước fit; không lọc bằng điểm validation. Giữ target quantity `success` theo ngày đặt UTC (A08 thực nghiệm), top10 theo train, train01/01/2024–30/06/2025, validation01/07–30/09/2025, test01/10–31/12/2025. Giữ H14, h1–7/h8–14 riêng và cấu hình/seed/refit từng ứng viên. Có92 origin test, hai block mỗi origin; chỉ cửa sổ đủ nhãn mới được chấm.

Daily và moment cơ cấu đơn tái dùng từ hai run đã seal, kiểm lại raw SHA và quantity/count/top10. Không nhận audit raw mới. Lịch model đi qua provider biết thông tin tại origin; forecast/teacher chỉ dùng nhãn đã hoàn tất tại origin. Ba worker local, không thêm thư viện, không push/upload.

Mã [retrospective_sweep.py](../M2/models/retrospective_sweep.py), config [m2-test-sweep.json](../data/configs/m2-test-sweep.json), tests [test_retrospective_sweep.py](../M2/models/tests/test_retrospective_sweep.py). Lệnh:

```powershell
.venv/Scripts/python.exe -B -m M2.models.retrospective_sweep --run-id NEW_UNIQUE_RUN_ID
```

## Sản phẩm và kiểm tra

Run hoàn tất [m2_test_sweep_20261011_fixed](../M2/artifacts/m2_test_sweep_20261011_fixed/report.md),43 artifact sealed:

- [CSV toàn bộ160 cấu hình, validation cạnh test](../M2/artifacts/m2_test_sweep_20261011_fixed/test_leaderboard.csv).
- [640 nhóm metric h1–7/h8–14 và hai cadence](../M2/artifacts/m2_test_sweep_20261011_fixed/test_metrics.csv), [29.440 dòng dự báo](../M2/artifacts/m2_test_sweep_20261011_fixed/test_predictions.csv).
- [Metric dịp lễ/ngày thường](../M2/artifacts/m2_test_sweep_20261011_fixed/test_calendar_strata.csv), [tóm tắt sáu nhóm](../M2/artifacts/m2_test_sweep_20261011_fixed/pool_summary.csv).
- [Manifest nguồn/config/code/lineage/protected hashes](../M2/artifacts/m2_test_sweep_20261011_fixed/manifest.json), [receipt đối soát độc lập](../M2/artifacts/m2_test_sweep_20261011_fixed_review.json).

Run đầu `m2_test_sweep_20261011` đã tính đủ160 cấu hình và kiểm nhãn/metric từng nhóm, nhưng dừng ở bước đọc baseline do dùng sai tên `test_predictions.csv` thay `focus_test_predictions.csv`. Giữ nguyên35 artifact và seal `failed`; không dùng run thiếu báo cáo làm kết quả hoàn tất. Sửa đường dẫn, thêm kiểm tệp baseline trước fit và tạo run mới tái dùng các phase đã băm. Không huấn luyện lại, không sửa ứng viên/tham số;29.440 dòng forecast/actual/metadata trước/sau sửa khớp chính xác. Protocol/catalog của run đầu đăng ký trước fit; giờ protocol/execution của run sửa là giờ đối soát/tổng hợp từ dự báo có sẵn.

Lệnh hoàn tất phần tổng hợp từ phase đã seal:

```powershell
.venv/Scripts/python.exe -B -m M2.models.retrospective_sweep --run-id NEW_UNIQUE_RUN_ID --reuse-phases m2_test_sweep_20261011
```

Đối soát độc lập đọc lại CSV và kiểm29.440 nhãn/cặp,640 nhóm MAPE/MAE/WAPE/bias/coverage/mẫu số, toàn bộ điểm validation từ nguồn đã seal,2.116 head,349 weighted fits và60 nhóm country/share/blend/count×basket. Đối chứng ban đầu, bản56 và bản cơ cấu đơn tái lập184 cặp mỗi bản, sai khác forecast0. Chín tuyến có1.656 forecast test và mọi selection/metric cũ nguyên hash. Không tạo `selected_models.csv` mới.

25 tests liên quan đạt (2 mới,23 hồi quy), pip check đạt. Một test cũ ban đầu lỗi tạo thư mục tạm sandbox; chạy lại riêng bằng `--basetemp=tmp/pytest-test-sweep-20261011` đạt. Full suite/CI remote/SARIMA/Prophet mới không chạy. Raw và757 tệp protected nguyên; daily moment/lịch/ba split/quantity/top10 không đổi. Không commit/push/upload.

Manifest SHA `8b6167a5ace0b163fa0c0249e2d091e344be51e5d4a09a5f35cd121545fba0a0`; receipt SHA `fae92b2b5b6090ea3ff82d6eddc5bfdf8d797c80988404e2381d0c6a4fe2740f`; raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`.

Mục tiêu số học MAPE tổng7 test<20% đã tìm được ứng viên trong so sánh này. Test đã xem nhiều lần; chọn theo bảng là chọn bằng test, kết quả cùng tập có thể lạc quan. Snapshot trạng thái cuối không tái dựng dữ liệu vận hành tại origin. R05 theo ngày/R07/T14 giữ mở; không đổi nghiệm thu hoặc bộ báo cáo/dashboard đã khóa. Bước tiếp phù hợp là kiểm ổn định ngoài giai đoạn đã dùng và chỉ tích hợp khi người dùng giao phạm vi đó; không xin thêm dữ liệu doanh nghiệp đã xác định không có.
