# LG U+ — dự báo số đơn và cơ cấu quantity

**Cập nhật CHG-041/E69:** [chấm toàn bộ160 lượt trên test](test-sweep-experiment.md) theo yêu cầu mới đã tìm được ứng viên19,265900%/coverage100%. Đây là xếp hạng bằng test hồi cứu, không thay lựa chọn validation20,446740% hoặc các kết quả lịch sử E68 bên dưới; chín tuyến/dashboard nguyên.

CHG-040/E68,11/10/2026; hai giả thuyết còn lại sau [lượt hiệu chỉnh/cập nhật](adaptive-experiment.md), theo phạm vi đã đề xuất và người dùng cho phép bắt đầu. Nhánh local `codex/m2-calendar-forecast`, target quantity success/ngày đặt UTC, top10 train, split/H14/R05 ngày giữ nguyên. Không sửa chín tuyến/dashboard/báo cáo khóa hoặc run trước; không push/upload.

**Kết quả hoàn tất:** chọn `composition_both56_mul56p4` bằng validation10,616717142432643%, tốt hơn10,77582022385683% trước. Khóa rồi chấm đúng một ứng viên: test hồi cứu **20,446740131508527%**, giảm từ20,520981% nhưng **chưa<20%**. Vẫn9/10 tuyến đạt ngưỡng; chín tuyến cũ giữ chính xác1.656 forecast và mọi metric. Dừng hai lượt21+26 cấu hình đã đăng ký, không thử ứng viên khác bằng test để tìm số đạt.

Run đầu `m2_composition_20261011` bị guard nhãn chặn trước selection/test và đã seal `failed`/`invalidated` với19 artifact: phép nhân count×basket điền quantity actual từ snapshot vượt cuối validation. Đã sửa để giữ actual trống khi cửa sổ của count component chưa hoàn tất split, thêm regression test cho snapshot còn order sau split. Không thay tham số/feature/candidate/tiêu chí; run sửa phải đối chiếu toàn bộ forecast với run vô hiệu hóa trong1e-8. Giữ run lỗi để truy lịch sử, không dùng metric của nó làm kết quả hoặc cache.

[Config](../data/configs/m2-composition.json) đăng ký26 cấu hình trước fit:

- Tám bản dự báo quantity: đối chứng56 ngày, feature đơn lớn, feature độ phân tán quantity/đơn, hoặc cả hai; mỗi bản raw/nhân56p4.
- Mười tám bản dự báo số đơn × lượng trung bình/đơn: count model chuẩn hóa28/56/90 ngày × raw/nhân56p4 × basket trailing28/56/90 ngày. Basket là dự báo trung bình lịch sử cố định cho từng block; không dùng số đơn hoặc basket thực của cửa sổ tương lai. Nhãn teacher/head count là order_count, nhãn/metric cuối luôn quantity thật.

Đơn lớn định nghĩa trước là quantity≥3. Feature gồm tỷ trọng số đơn lớn và quantity từ đơn lớn28/56 ngày, tốc độ số đơn lớn7/28 ngày, hệ số biến thiên quantity/đơn28/56 ngày. Chỉ tính rolling quá khứ tại origin; không có cờ peak nhìn tương lai hoặc thống kê toàn bộ test. Audit lại raw; chặn nếu snapshot không có một dòng mỗi order vì moment theo dòng sẽ không đại diện phân phối đơn. Dẫn xuất chỉ gồm ngày/tuyến/quantity/order_count/moments, không xuất ID.

Hai fold01–28/10/2024 và01–28/04/2025 chẩn đoán, population tính từ quá khứ. Chọn MAPE validation chính h1–7 origin mỗi ngày, MAE rồi ID, đủ coverage cả hai block. Phải thắng10,77582022385683% với dung sai1e-8 mới khóa một lựa chọn và chấm test hồi cứu một lần. Dừng sau lượt26 này; không thử ứng viên khác bằng test để tìm số dưới20%.

[Module riêng](../M2/models/composition_experiment.py) và [tests](../M2/models/tests/test_composition_experiment.py) tái dùng estimator/calibration/metric và bảo toàn cũ, không thêm phụ thuộc. Không sửa mã hoặc config đã seal của lượt trước.

```powershell
.venv\Scripts\python.exe -B -m M2.models.composition_experiment --run-id ten_run_moi
.venv\Scripts\python.exe -B -m pytest M2/models/tests/test_composition_experiment.py --basetemp tmp/composition-tests -o addopts='' -q
```

Test đã xem nhiều lần nên kết quả nếu đạt vẫn là hồi cứu, không là holdout độc lập; không đóng R05 ngày/R07/T14 bằng metric tuần.

## Bảng kết quả

| Hướng mới | Số cấu hình | MAPE validation tốt nhất % |
|---|---:|---:|
| Hiệu chỉnh/cập nhật, gồm đối chứng | 21 | 10,775820, giữ đối chứng |
| Quantity + feature đơn lớn riêng | 2 | 11,253100 |
| Quantity + độ phân tán riêng | 2 | 10,820670 |
| Quantity + cả hai nhóm feature | 2 | **10,616717** |
| Count × basket | 18 | 11,850157 |
| Đối chứng quantity56 lặp lại lượt26 | 2 | 10,775820 |

Hai nhóm feature kết hợp thắng validation; từng nhóm riêng và count×basket không thắng. Đây là bằng chứng thực nghiệm trong snapshot và protocol hiện hành, không chứng minh quan hệ nhân quả của đơn lớn với nhu cầu tương lai. Hai fold lịch sử của lựa chọn mới đạt17,327658%/10,914487%, chỉ chẩn đoán, không dùng đổi lựa chọn.

| LG U+ | Đối chứng ban đầu | Ứng viên56 trước | Ứng viên cơ cấu đơn |
|---|---:|---:|---:|
| Validation h1–7 MAPE % | 11,632703 | 10,775820 | 10,616717 |
| Test h1–7 MAPE % | 20,688009 | 20,520981 | **20,446740** |
| Test h1–7 MAE | 11,436603 | 11,493482 | 11,482204 |
| Test h1–7 WAPE % | 20,926550 | 21,030626 | 21,009990 |
| Test h1–7 bias | -5,654813 | -5,644805 | -5,921379 |
| Test h8–14 MAPE % | 18,992036 | 20,156147 | 20,292426 |
| Test coverage | 100% | 100% | 100% |

MAPE chính giảm0,074241 điểm phần trăm so với ứng viên trước và0,241268 so với đối chứng ban đầu; còn vượt20% khoảng0,446740 điểm phần trăm. MAE/WAPE vẫn kém đối chứng ban đầu, bias âm lớn hơn, block2 kém cả hai mốc. Không nhận cải thiện đồng đều. Cadence7 ngày của ứng viên mới: h1–7 MAPE20,526069%, h8–14 MAPE22,056650%; cùng coverage100%. Origin mỗi ngày có86/79 cặp được chấm ở block1/2; cadence7 ngày13/12 cặp, các cửa sổ origin mỗi ngày không độc lập.

Mô hình mới giữ pooled top10, chuẩn hóa56 ngày, LightGBM150 cây/7 lá, train365 ngày, refit7, seed42 và đầu nhân56p4; thêm bảy feature dimensionless về đơn lớn/CV. Không thay bộ lọc, split, top10, metric hoặc chọn lại theo test. Đầu ra vẫn là nghiên cứu local, dashboard/bộ báo cáo khóa giữ kết quả cũ.

## Đầu ra và kiểm chứng

[Run hoàn tất](../M2/artifacts/m2_composition_20261011_fixed/README.md), [dự báo LG U+](../M2/artifacts/m2_composition_20261011_fixed/focus_test_predictions.csv), [bảng trước/sau10 tuyến](../M2/artifacts/m2_composition_20261011_fixed/before_after_routes.csv), [metric đầy đủ](../M2/artifacts/m2_composition_20261011_fixed/overall_test_metrics.csv), [khóa trước test](../M2/artifacts/m2_composition_20261011_fixed/selection_lock.json), [CSV moment theo ngày](../M2/artifacts/m2_composition_20261011_fixed/daily_distribution.csv), [receipt độc lập](../M2/artifacts/m2_composition_20261011_fixed_review.json).

Run sửa complete38 artifact, manifest SHA `03aebcc02c444f25762958a616915e0e73b2f50f776b08eaff725b72371b8079`. Audit mới100.000 dòng/93.104 success/118.296 quantity/46 tuyến, không duplicate;33.626 dòng daily moment đối soát độc lập từ raw. Nguồn SHA vẫn `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`. Top10 train và630 tệp protected nguyên, gồm run lỗi đã vô hiệu hóa, nghiên cứu trước, mã/config trước, published/dashboard/notebook/launcher/Word. Đối chứng56 khớp0; toàn bộ7.696 forecast của hai fold và validation trước/sau sửa nhãn khớp chính xác0. Không dùng metric của run lỗi làm bằng chứng.

Receipt kiểm352 nhóm metric của hai fold/validation/test,54 nhóm count×basket,336 head về actual/cutoff/tối ưu factor/application,21 giá trị feature tính trực tiếp từ order, selection khóa trước test và chín selection/1.656 forecast/metric nguyên chính xác. Future hai dòng không có actual. Cộng lượt21:604 nhóm metric kiểm độc lập,733 weighted fits và1.528 head.29 tests liên quan đạt (8 mới,21 hồi quy) và `pip check` đạt; không chạy full suite/CI remote/SARIMA/Prophet mới.

T04/T08–T09/T12 đồng bộ TASK/PLAN/PROJECTMAP/review-log E68 và M2 README. Không đổi requirements hoặc nâng trạng thái nghiệm thu; mục tiêu tuần<20% chưa đạt, R05 ngày/R07/T14 giữ mở. Giữ local trên nhánh mới, chưa commit/push/upload. Hai lượt hữu hạn đã hoàn tất; nghiên cứu thêm cần giả thuyết mới dựa trên train/validation và công khai việc test đã xem nhiều lần.
