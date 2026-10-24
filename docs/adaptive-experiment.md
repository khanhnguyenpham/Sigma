# LG U+ — hiệu chỉnh và cập nhật mô hình

**CHG-045/E73 — 14/10/2026:** nhánh `cleanup/m2-final` chỉ giữ code M2 final. Xem [bản đồ code hiện hành](../M2/README.md) và [khôi phục code cũ](review-log.md#removed-docs-chg070). Các lệnh/đường code M1, M3, V13 và thử nghiệm bên dưới là lịch sử, cần nhánh backup để chạy; dữ liệu, kết quả, bằng chứng và tiêu chí nghiệm thu không đổi.

CHG-040/E68,11/10/2026; tiếp tục theo yêu cầu người dùng trên nhánh local `codex/m2-calendar-forecast`. T08–T09/T12 mở thêm một lượt hữu hạn sau [ba lượt trước](focus-experiment.md). Chín tuyến khác và dashboard/bộ báo cáo đã khóa được bảo toàn; không push/upload. Target A08 success theo ngày đặt UTC, top10 train, split/H14 và R05 ngày giữ nguyên.

Lượt `m2_adaptive_20261011` đã hoàn tất21 cấu hình: **không cải thiện validation**, tốt nhất vẫn đối chứng10,77582022385683%. Không chấm test mới; mốc test nghiên cứu giữ20,520981%, mục tiêu<20% chưa đạt. Theo phạm vi đã nêu, tiếp tục hai giả thuyết còn lại ở [lượt cơ cấu đơn](composition-experiment.md), không mở thêm grid cho lượt này.

## Đăng ký trước fit

[Config](review-log.md#removed-docs-chg070) khóa21 ứng viên trước fit:

- Bảy bản trên mô hình chuẩn hóa56 ngày: raw, đầu nhân56p4, đầu cộng28p2/56p2/84p4, affine56p4/84p4. Mã residual cũ được tái dùng; prior về0 và clip±25% scale ở cutoff. Các bản cộng/affine này chưa chạy trên chính mô hình56 ngày ở lượt trước.
- Sáu bản tăng trọng số dữ liệu gần: half-life28/56/112 ngày, mỗi bản raw/nhân56p4. Tuổi tính theo ngày cuối nhãn đã hoàn tất; trọng số inverse-target hiện hành nhân với `2^(-age/half_life)`, chuẩn hóa tổng bằng tổng trọng số đối chứng. Nhãn0 vẫn trọng số0 như mô hình cha.
- Bốn bản refit mỗi1/3 ngày, mỗi bản raw/nhân56p4.
- Bốn bản kết hợp half-life56 và refit1/3 ngày, mỗi bản raw/nhân56p4.

Các teacher lịch sử fit tại origin riêng và chỉ học nhãn đã hoàn tất; head dùng4/8/12 tuần không chồng, block2 bỏ tuần chưa đủ nhãn. Model/head chính refit cùng cadence tính từ origin đầu split; giữa các lần refit vẫn cập nhật feature tại origin. Teacher trong nghiên cứu không phải forecast đã phát hành thật. Snapshot trạng thái cuối của order vẫn là giới hạn hồi cứu.

Hai fold01–28/10/2024 và01–28/04/2025 chỉ chẩn đoán, top10 tính từ dữ liệu trước fold. Chọn bằng MAPE validation h1–7 origin mỗi ngày, MAE rồi model ID; đủ coverage cả hai block. Phải thắng10,77582022385683% với dung sai1e-8 mới khóa một lựa chọn và chấm test một lần. Không dùng lỗi test để đổi ứng viên hoặc mở thêm grid. Dừng sau lượt21 ứng viên này.

## Mã và lệnh

[Module](review-log.md#removed-docs-chg070) riêng tái dùng feature, hiệu chỉnh, metric và cơ chế bảo toàn của lượt trước; không sửa module/config/run cũ. [Bốn tests](review-log.md#removed-docs-chg070) đã đạt trước run: trọng số và population/tổng weight, parity estimator thật, sửa order tương lai không đổi forecast/head, kiểm cadence refit và selected-only khớp chạy chung.

```powershell
.venv\Scripts\python.exe -B -m M2.models.adaptive_experiment --run-id ten_run_moi
.venv\Scripts\python.exe -B -m pytest M2/models/tests/test_adaptive_experiment.py --basetemp tmp/adaptive-tests -o addopts='' -q
```

Manifest ghi config/source/package/implementation hash, nguồn daily dẫn xuất đã seal và toàn bộ tệp protected; kiểm lại raw hash/quantity/top10 train. Đối chứng phải tái lập ứng viên56 ngày trong1e-8. Sau khóa, chín tuyến có selection và forecast giữ nguyên chính xác qua CSV round trip. Metric h1–7/h8–14 và cadence không chồng giữ quy ước cũ. Test nếu có vẫn hồi cứu do đã xem nhiều lần; không đóng R05/R07/T14 chỉ vì đạt metric tuần.

## Kết quả và kiểm chứng

| Nhóm | MAPE validation tốt nhất % | Cấu hình |
|---|---:|---|
| Đối chứng56 ngày | 10,775820 | Nhân56p4 |
| Đầu cộng/affine trên56 ngày | 11,527652 | Cộng28p2 |
| Trọng số dữ liệu gần | 11,708249 | Half-life112, raw |
| Refit1/3 ngày | 10,816207 | Refit3, raw |
| Trọng số gần + refit nhanh | 13,321580 | Half-life56/refit3, raw |

Coverage100% cả hai block; đối chứng khớp dự báo trước với chênh lớn nhất0. Các cấu hình mới không thắng validation nên không có bằng chứng cải thiện test. Không suy rằng refit nhanh hoặc trọng số gần luôn có hại cho mọi tuyến.

[Run và bảng21 cấu hình](../M2/artifacts/m2_adaptive_20261011/README.md), [metric đầy đủ](../M2/artifacts/m2_adaptive_20261011/validation_metrics.csv), [receipt độc lập](../M2/artifacts/m2_adaptive_20261011_review.json). Manifest SHA `a2f1e3528149743f43839aa7ed0b3719e2a6b0903beb0184d4e6353751388686`,15 artifact seal.25 tests liên quan đạt (4 mới và21 hồi quy), `pip check` đạt. Receipt kiểm252 nhóm metric của validation và hai fold,733 weighted fits,1.192 head, population/tổng weight/cutoff/actual/cadence, selection chín tuyến nguyên chính xác. Raw hash/quantity/top10 train và591 tệp protected nguyên; không phát sinh dự báo test mới. Mã/config/run cũ không sửa; các thay đổi có sẵn của người dùng được giữ.
