# M2 — LightGBM, SARIMA và Prophet

**CHG-033/v2 — đã chạy và đối soát:**12 biến thể đối chứng và14 mới,26 biến thể/50 cấu hình mục tiêu. Xem [biến thể và giao diện](../models/README.md). Các kết quả E58 dưới đây là đối chứng lịch sử; không nhận chúng là kết quả v2. Lệnh mặc định dùng config v2 nên chạy bằng run-id mới.

CHG-030: người dùng yêu cầu triển khai dự báo ngày và trực tiếp tổng7 bằng ba họ, lưu kết quả vào ba thư mục riêng. Pool nghiên cứu này chỉ top10 theo train; sản phẩm V13 và tiêu chí R05 ngày có phạm vi riêng.

```powershell
.venv\Scripts\python.exe -m sigma model-families --run-id m2_three_models_20261006
.venv\Scripts\python.exe -m sigma verify-model-families --run-id m2_three_models_20261006 --output-id m2_three_models_20261006_review
```

Lệnh từ chối ghi đè run đã có; dùng run-id mới khi chạy lại. [Cấu hình chạy](../models/model_families.json) trỏ tới `variants.json` riêng của mỗi họ; [pipeline](../models/families.py) tái sử dụng audit, top10, daily feature contract, weekly feature/fit và metric. [Hướng dẫn tổ chức mã và thêm mô hình](../models/README.md) mô tả các thư mục LightGBM/SARIMA/Prophet. Prophet1.5.0 được bổ sung vào môi trường/requirements local.

## Ba thư mục

```text
M2/artifacts/m2_three_models_20261006/
├── LightGBM/
│   ├── daily/
│   └── direct_7d/
├── SARIMA/
│   ├── daily/
│   └── direct_7d/
├── Prophet/
│   ├── daily/
│   └── direct_7d/
├── manifest.json
├── protocol.json
├── top_routes.csv
├── family_selected_models.csv
├── overall_selected_models.csv
├── selection_lock.json
├── validation_metrics.csv
├── baseline_predictions.csv
├── baseline_metrics.csv
├── summed_daily_predictions.csv
├── comparison_metrics.csv
├── overall_test_predictions.csv
├── overall_test_metrics.csv
└── summary.csv
```

Mỗi nhánh có validation/test/future predictions, metrics, selected_models và fit logs. SARIMA/Prophet lưu thêm checkpoint dự báo từng ứng viên/tuyến. Lỗi hội tụ làm candidate mất eligibility, có log; không thay bằng baseline rồi gọi đó là họ mô hình đã yêu cầu. `manifest.status=complete` chỉ khi toàn bộ run xong.

Verifier tạo thư mục `M2/reports/m2_three_models_20261006_review/`: `M2_three_models.md`, `comparison.png`, `route_comparison.csv`, `summary.json`. Verifier đọc raw để đối chiếu quantity, top10, nhãn, metric, độ phủ, lựa chọn, khóa và actual tương lai.

## Protocol đăng ký trước fit

- Success quantity theo ngày đặt UTC, không lọc activation; raw giữ nguyên hash. Train01/01/2024–30/06/2025; validation01/07–30/09/2025; test01/10–31/12/2025. Top10 chỉ theo train.
- Horizon14, refit7 ngày, cửa sổ nhãn train365 ngày. LightGBM pooled top10, SARIMA/Prophet riêng tuyến. SARIMA cập nhật quan sát đã qua giữa lần refit; Prophet giữ tham số đến lần refit sau; LightGBM dùng feature mới tại origin. Nhãn fit kết thúc≤cutoff.
- Bốn biến thể/họ/mục tiêu:24 cấu hình mục tiêu,240 candidate/tuyến validation. LightGBM Poisson, weightedL1, annualL1, annualL1 15lá. WeightedL1 có trọng số1/y khi y>0, trọng số0 khi y=0; ngày0 vẫn chấm MAE/WAPE/bias/coverage. Ngày tái sử dụng lag/rolling/horizon/lịch, annual thêm sin/cos năm; tổng7 dùng feature tuần hiện có, annual thêm lịch sử cùng kỳ năm trước.
- SARIMA `(1,0,0)×(1,0,0,7)`, `(1,1,1)×(0,1,1,7)`, log1p của cấu hình đầu, SARIMAX của cấu hình đầu với sin/cos năm. Log1p dùng expm1 dự báo điểm, chưa thêm hiệu chỉnh bias.
- Prophet additive, multiplicative, additive với changepoint prior0.01, additive tắt weekly seasonality; cấu hình khác dùng prior0.05. Fourier năm bậc3, không mùa vụ trong ngày, uncertainty_samples0, seed42. Chỉ365 ngày train nên phân rã trend/năm có thể chưa ổn định; cấu hình không bảo đảm phù hợp trước thực nghiệm.
- SARIMA/Prophet tổng7 học `S(t)=sum(y[t−6:t])`. TạiD dự báo S(D+7) cho D+1…D+7, S(D+14) cho D+8…D+14. Không lấy bướcD+1 hoặc cộng bảy dự báo ngày để gọi trực tiếp.
- Từng họ/mục tiêu/tuyến chọn MAPE positive validation block1, rồi MAE, lexical model id; yêu cầu toàn bộ forecast candidate đầy đủ, kể cả block2. Chọn giữa ba họ bằng MAPE, MAE, family, model. Khóa cả sáu nhánh trước mọi test. Test chỉ chấm biến thể đã chọn từng họ, không dò toàn bộ grid.
- Baseline đối chứng riêng, không tham gia pool. Báo MAPE positive, MAE, WAPE, bias quantity, số mẫu và coverage; h1–7/h8–14 riêng. Tổng chỉ chấm cửa sổ đủ nhãn trong split: test86/79 cửa sổ rolling, cadence7 ngày13/12. Future tại31/12/2025 có actual trống.
- Tổng từ mô hình ngày giữ lựa chọn theo metric ngày, so với tổng trực tiếp trên cùng origin/cửa sổ/actual. So sánh này đánh giá hai quy trình sử dụng, không cô lập riêng tác động kiến trúc. MAPE ngày và MAPE tổng có mẫu số khác nhau.

Test đã được xem: đây là đánh giá hồi cứu, không kiểm định độc lập. R05/R07 giữ nguyên; tổng7 không thay nghiệm thu ngày. Chưa thay sản phẩm46 tuyến, chính sách tồn, cảnh báo, lịch Windows hoặc báo cáo Word/slide.

## Kết quả chạy thật E58

Run `m2_three_models_20261006` complete với309 artifact. Mỗi ô dưới là MAPE test trung bình theo tuyến; biến thể từng họ được chọn bằng validation, không chọn lại bằng test.

| Họ | Ngày h1–7 | Cộng dự báo ngày thành tổng7 | Trực tiếp tổng7 | Tuyến đạt20% tổng trực tiếp |
|---|---:|---:|---:|---:|
| LightGBM | 47,77% | 36,53% | 16,83% | 8/10 |
| SARIMA | 54,63% | 20,67% | 16,92% | 8/10 |
| Prophet | 57,28% | 23,70% | 26,43% | 3/10 |

Độ phủ100% tất cả các kết quả trên; cả ba họ dự báo ngày0/10 đạt20%. LightGBM thắng validation tất cả10 tuyến cho cả hai mục tiêu trong grid đăng ký. Trực tiếp tổng7 tốt hơn cộng ngày ở LightGBM/SARIMA về trung bình; Prophet có kết quả ngược lại, không kết luận trực tiếp luôn tốt hơn. Baseline MA28 tổng7 test18,09%,7/10 đạt20%.

Trong nhóm được chọn bằng validation, LightGBM tổng7 còn au(KDDI)20,11% và LG U+22,02%. Một số tuyến SARIMA/Prophet có test tốt hơn LightGBM, nhưng không dùng thông tin này để chọn lại. Kết quả này khác pool58 ứng viên V13, không thay thành tích9/10 của pool cũ bằng8/10 hoặc ngược lại.

Verifier `m2_three_models_20261006_review` đạt:221.280 dòng dự báo,2.040 nhóm metric;0 candidate lỗi, khóa lựa chọn nguyên, raw hash nguyên, future actual trống. 45 kiểm tra liên quan (gồm9 mới) và pip check đạt;58 artifact ngày `sigma_full_m2_20261005` và toàn bộ artifact run tuần `sigma_weekly_v13_m2_analysis_20261006` local nguyên. CI/full suite toàn project chưa chạy lại.

Xem bảng tuyến, mô hình chọn và biểu đồ tại `M2/reports/m2_three_models_20261006_review/M2_three_models.md`. Báo cáo và các CSV private chỉ lưu local.


## Tổ chức thư mục CHG-031

Mã/cấu hình/tests chuyển vào M2/models; run mới vào M2/artifacts và báo cáo mới vào M2/reports. Notebook xem kết quả tại M2/notebooks/model_comparison.ipynb. Các run cũ chuyển nguyên byte, đường outputs tương thích bằng junction/hardlink. Xem M2/README.md từ gốc dự án. Nguồn lịch sử có snapshot đúng hash; không huấn luyện lại hoặc sửa kết quả khi di chuyển.

## Cải tiến CHG-033 / v2

Các biến thể và cấu hình mới được đăng ký trước fit trong manifest/protocol của run `m2_improved_models_20261006`. Lượt này được giữ nguyên để truy vết lỗi metadata actual ở hai calibration, không nhận verified. Run sửa là `m2_improved_models_20261006_fixed`, dùng forecast validation đã kiểm chứng tương đương estimator, dựng lại actual từ audit mới và fit test mới sau khóa lựa chọn. Giữ12 biến thể cũ, thêm14 theo kế hoạch được chốt:4 LightGBM,4 SARIMA,4 Prophet và2 hiệu chỉnh LightGBM chỉ tổng7. Danh sách theo mục tiêu là8/10,8/8,8/8, tổng50 cấu hình. Phương pháp/tên biến thể tại các README riêng.

Các nhánh có thêm validation_monthly_metrics.csv cho ba tháng; chỉ chấm cửa sổ đủ nhãn trong tháng, giữ anchor cadence validation. Đây là chẩn đoán, không thay luật lựa chọn toàn kỳ. Verifier tái tính teacher/head/factor/application, tổng quantity và metric; báo cáo tạo bảng trước/sau theo đối chứng v1 và lựa chọn đã khóa từng tháng.

Lịch dự kiến ban đầu:06–08/10 triển khai,09–11/10 validation,12/10 khóa,13–14/10 đối soát,15–16/10 báo cáo/demo,17/10 bàn giao. Được phép hoàn tất các bước sớm trong lượt triển khai; ngày thực chạy ghi trong manifest và review-log. Run sửa đã complete và verifier đạt; kết quả kiểm thực chạy tại E61 và báo cáo cải tiến. Mục tiêu10/10 tổng7 là hướng cải thiện, không cam kết nghiệm thu; R05 ngày/test hồi cứu giữ nguyên.

## Kết quả cải tiến E61 đã đối soát

| Họ | MAPE ngày / tuyến đạt | MAPE trực tiếp tổng7 / tuyến đạt |
|---|---:|---:|
| LightGBM | 46,74% /0 | 16,11% /8 |
| SARIMA | 54,63% /0 | 17,12% /7 |
| Prophet | 55,47% /0 | 16,51% /8 |

Lựa chọn phối hợp đã khóa theo validation: LightGBM9 tuyến và Prophet au(KDDI), test tổng7 đạt9/10,15,89%; LG U+20,69%. Ngày vẫn0/10. Tháng9 validation tổng7 của lựa chọn này18,70%,7/10, yếu hơn tháng7/8. [Báo cáo bàn giao và phân tích](m2_improved_models_20261006_handoff.md); [báo cáo độc lập](m2_improved_models_20261006_fixed_review/M2_three_models.md).

Verifier đạt 401,600 dòng/9,160 nhóm metric; 2 candidate SARIMA lỗi được loại, mọi lựa chọn test/future đủ độ phủ. 40 kiểm tra liên quan đạt. Bảo toàn raw/run cũ; nhãn actual lượt sửa dựng từ audit mới và metric/lựa chọn tính lại trước test fresh. Test hồi cứu; R05/R07/T14 còn mở, sản phẩm V13 và deadline17/10 giữ hiện hành.
