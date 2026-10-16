# Tổng 30 ngày và sản phẩm M3

**CHG-050/E78 — giao diện trình diễn mentor:** [hướng dẫn 5–7 phút](mentor-demo.md) đi kèm 7 màn hình mới. Timeline kịch bản được tổng hợp từ ledger đã đối soát, bộ lọc quốc gia/nhà mạng có hiệu lực lên chỉ số mô phỏng. Mô hình, policy và các run sealed giữ nguyên; đổi cách trình bày không làm các tiêu chí còn thiếu thành đạt.

**Cập nhật CHG-049/E77:** giao diện đã có hướng xử lý tồn, so sánh 13 kịch bản và giải thích cơ hội cảnh báo. Hai thử nghiệm mô hình đã chạy/đối soát, nhưng chưa cải thiện ổn định nên không đổi bộ dự báo mặc định. [Protocol, kết quả và giới hạn](aggregate-refinement.md). Số liệu nguồn bài dưới đây giữ nguyên.

## Đã làm và cách mở

Ngày 16/10/2026, người dùng thuật lại mentor yêu cầu chạy tổng 30 và giao hoàn thiện M3. Nhánh local `codex/30day-m3` đã hợp nhất phần Khang tại `origin/M2-final-report` (b141528); nhánh `M2-final-cleanup` (261c631) được đọc đối chiếu, không dùng làm base vì đã bỏ M3. [Bộ final M2 Khang](../M2/reports/final_m2_20261011/README.md) đã kiểm hash qua loader; không nhận đã refit lại private run của Khang trên máy này.

```powershell
.\scripts\start_m3.ps1
```

Mở **http://127.0.0.1:8507**. Màn hình đọc kết quả đã đối soát, không train khi mở. Bộ lọc quốc gia, nhà mạng, loại/SKU, 13 kịch bản; tải CSV tổng hợp từ giao diện. Giữ rõ snapshot đến 31/12/2025, dự báo 01–30/01/2026 chưa có actual và tồn là mô phỏng.

## Kết quả chạy thực

| Phương án mới | Đạt ≤20% | MAPE trung bình top 10 | Cửa sổ đủ nhãn/tuyến | Không chồng lấn | Coverage |
|---|---|---|---|---|---|
| Tổng 7 | 9/10 | 15,485424% | 86 | 13 | 100% |
| Tổng 30 | 9/10 | 11,786316% | 63 | 3 | 100% |

Tổng 30 còn China Mobile 20,333443%; tuyến này dùng lgbm_ratio7, validation 11,720299%. Lựa chọn từ validation, không đổi bằng test. Giá trị MAPE làm tròn không đổi kết luận chưa đạt. MAPE của hai target có mẫu số khác nhau; không suy chênh MAPE là mức cải thiện dự báo ngày. Bộ final 7 của Khang 10/10 (LG U+ test-selected) được giữ riêng; bảng 7 ở đây là đối chứng từ pool mới cùng tổng 30.

[Mẫu CSV kết quả 30 local](../reports/M3_2026-10-16/ket_qua_30_ngay.csv) · [So sánh 7/30 local](../reports/M3_2026-10-16/so_sanh_7_30.csv). Các file reports/outputs chỉ hiện trên máy tạo run.

## Dữ liệu, mô hình và chống rò rỉ

- Giữ nguyên raw SHA `6aa5aa599938db8409b57327166eaae042014e218a4a97d4d44a202b7db15d0b`, 100.000 dòng/118.296 quantity; top 10 theo train. A08 success/ngày đặt UTC vẫn đề xuất. Không dùng activation loại sale, không xóa spike/tụt hợp lệ.
- Tổng 30 là 30 ngày liên tiếp D+1…D+30, không phải tháng lịch. Giữ train 01/01/2024–30/06/2025, validation quý 3/test quý 4/2025; không thay R05 ngày hoặc h1–7/h8–14 của benchmark cũ.
- Pool đăng ký trước fit trong [aggregate.json](../data/configs/aggregate.json): 4 baseline, 4 LightGBM, 1 Prophet, 1 SARIMA. Học 540 ngày, lịch sử tối thiểu 90, refit 7, seed 42, tối đa 3 worker. Có 12 ứng viên tuyến/cửa sổ bị lỗi và được ghi log/loại khỏi lựa chọn, không bỏ riêng điểm dự báo xấu.
- Feature lag/tổng quá khứ 7/14/28/56/90, weekday/tháng/sin-cos và lượng cùng kỳ đã biết. LightGBM ratio chia theo mean 90 × window và hoàn nguyên. Prophet/SARIMA học tổng trượt kết thúc tại timestamp, dự báo điểm D+window; không lấy S(D+1) thay cho tổng tương lai.
- Chỉ nhãn hoàn tất trước cutoff được fit; chọn validation MAPE → MAE → ID, đủ coverage toàn phase. Khóa 92 lựa chọn trước test, tuyến ngoài top 10 dùng baseline. Test đã được xem trong lịch sử, là hồi cứu. Báo MAPE/MAE/WAPE/bias/zero/coverage và cadence riêng.
- Phân bổ tổng 30 về ngày theo weekday 90 ngày, rồi SKU/loại theo lịch sử 30, fallback 90; bảo toàn tổng và gắn nhãn phân bổ. Không gọi đây là 30 dự báo ngày độc lập.

## M3 đã triển khai

1. Sổ theo tuyến×SKU×loại, nhập đầu ngày UTC, giao dịch theo timestamp rồi ID; đối soát từng sự kiện và ngày.
2. SS/ROP/S, trigger strict tồn hiện có < ROP; IP dùng tính Q. Hàng đang về không cộng vào tồn trước ETA, tránh đặt trùng khi pending đủ.
3. 13 kịch bản gồm cơ sở, bán sụt 1 ngày/còn 30%/tăng gấp 2, nhận 50%/trễ 3 ngày/không nhận và độ nhạy cover/lead/safety.
4. Replay cảnh báo H14 giữ 5520 cửa sổ/2867 sự kiện như benchmark gốc; nhìn trước 30 và replay H30 lưu riêng. Không dùng policy có đặt hàng để chấm false alarm.
5. Khách đặt D → giao D+7 ngày lịch, gồm cuối tuần; giữ riêng lead time nhập kho. Bảy ngày đầu 1885 quantity từ đơn đã đặt; ngày 8–37 từ dự báo đơn tương lai. Actual giao để trống; tồn không trừ lần hai lúc giao.
6. Quan sát sụt quantity và sụt doanh thu riêng, so 28 ngày trước; số tiền lỗi giữ thiếu. Không tuyên bố biết trước cú sốc không có tín hiệu.
7. Giao diện 7 tab, lọc route/SKU/loại/scenario, CSV tải về; kiểm receipt/hash/nguồn trước mở. Job chống chạy trùng, skip khi input không đổi, giữ last-good khi lỗi, từ chối nguồn thay đổi khi chưa có forecast mới đã đối soát.

Cơ sở đáp ứng **85,971944%**, vẫn có thiếu hụt; nhận 50% chỉ đáp ứng 46,4867%, trễ 3 ngày 74,1796%, không nhận 7,6904%. Các con số là mô phỏng, không phải hiệu quả kho doanh nghiệp. Cảnh báo H14: TP 2254/FP 1011/FN 613; báo trước ≥ 7 ngày 1053/2867 = 36,728287%. R07 chưa bảo đảm mọi ca, R05/T14 còn mở.

## Kiểm tra và tái lập

Run nguồn bài:

- Forecast `sigma_aggregate_30d_20261016`, summary SHA `8d47a36e71c1d37fd7f55dd3bbd20ea8d2e3132b7912a1d3f27b303b23168d16`.
- Product `sigma_m3_30d_20261016_precision_v2`, summary SHA `7086d711dfc7239adb972d2caa4bb2aac68857c338f2f42add543c385c7557ef`.
- Verifier forecast audit lại raw/top 10/nhãn, 92 lựa chọn khóa, 697 cutoff, 1160 nhóm metric, 8556 nhóm phân bổ; 12 lỗi candidate đã công khai.
- Verifier M3 kiểm 1.100.320 ledger/khuyến nghị/pending clocks, 85.560 ngưỡng SKU, 266.123 sự kiện và 8280 cửa sổ cảnh báo H14/H30. Lần đầu phát hiện một SS lệch 1 do parser CSV; dùng float_precision round_trip, giữ run cũ và chạy v2. Không đổi công thức/threshold hoặc forecast để vượt kiểm.
- **310 tests đạt**, 0 lỗi/skip; AppTest 7 tab/11 trường hợp trên nguồn bài đạt; demo UI đạt. Đã xem trực tiếp tổng quan/tồn/biểu đồ trong trình duyệt; ảnh [dashboard local](../reports/M3_2026-10-16/dashboard.png).

Các lệnh đã dùng (run tồn tại thì chọn ID mới khi tạo lại):

```powershell
.\.venv\Scripts\python.exe -m sigma aggregate --run-id aggregate_new
.\.venv\Scripts\python.exe -m sigma verify-aggregate --run-id aggregate_new
.\.venv\Scripts\python.exe -m sigma m3 --aggregate-run aggregate_new --run-id m3_new
.\.venv\Scripts\python.exe -m sigma verify-m3 --run-id m3_new
```

Cấu hình [product30.json](../data/configs/product30.json) trỏ đúng aggregate_run/product_run, không trộn bộ cha. Receipt và summary phải khớp. Không sửa manifest/run cũ hoặc tự đổi split để nhận đạt.

## Job và máy clone mới

Task Windows **SigmaM3Refresh**, 07:00 mỗi ngày theo SE Asia Standard Time; chạy thử 16/10 trả 0, lần kế 17/10/2026 lúc 07:00. Job nhận bộ v2 đã kiểm, lượt sau skip_unchanged. Job chỉ cập nhật từ bộ dự báo đã đối soát; không tự train/sửa split khi nguồn CSV đổi, không gửi đơn nhập thật. Đầu vào mới cần pipeline/đối soát riêng; sản phẩm hiện tại là snapshot lịch sử đã nêu.

```powershell
.\.venv\Scripts\python.exe -m sigma refresh-m3
# Trên máy mới, tạo task khi muốn bật lịch (tên đã có thì script từ chối ghi đè):
.\scripts\install_m3_task.ps1 -TaskName SigmaM3Refresh -At '07:00'
# Kiểm toàn bộ bằng dữ liệu tự sinh, chọn prefix mới mỗi lần:
.\.venv\Scripts\python.exe -m sigma demo 30 --prefix demo_m3_team
.\scripts\start_m3.ps1 -Config outputs/demo_m3_team_bundle/product30.json
```

Demo dùng 3 tuyến và 6 mặt hàng, 13 kịch bản; không đọc raw bài, có đối soát forecast/policy và UI. Không lấy điểm demo 3/3 hoặc fill 100% thay kết quả nguồn bài. CI đã bổ sung luồng tự sinh này, chưa push/chạy CI remote trong lượt hiện tại.

## Giới hạn và bước tiếp

Đã bàn giao sản phẩm chạy local, còn tiêu chí chưa đạt: China Mobile tổng 30 >20%, R05 ngày chưa nghiệm thu, R07 chưa bao phủ mọi sự kiện. Cần tiếp tục nghiên cứu bằng train/validation và giữ test hồi cứu; không ép dữ liệu hoặc chọn bằng test để nhận đạt. Tồn/lead time/mapping vẫn giả định vì chỉ được cung cấp order. Raw/run/ảnh/báo cáo giữ local; code mới ở nhánh codex/30day-m3 chưa push.
