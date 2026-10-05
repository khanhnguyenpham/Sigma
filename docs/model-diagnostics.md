# Chẩn đoán mô hình và giải thích kết quả M2–M3

Ngày 06/10/2026, CHG-029/E56–E57. Tài liệu bổ sung bằng chứng cho [bộ trình diễn](m2m3-demo.md), không thay tiêu chí nghiệm thu hoặc bảo đảm điểm mentor. Sản phẩm giữ V13; Word và slide cũ chưa cập nhật.

## Chỉ tiêu phải trình bày riêng

| Nội dung | Kết quả hiện hành | Diễn giải |
|---|---|---|
| MAPE số bán từng ngày, h1–7 | 0/10 tuyến đạt ≤20%; 41,89–58,13% | R05 chưa đạt theo protocol hiện hành. |
| MAPE tổng số bán 7 ngày, origin mỗi ngày | 9/10 đạt ≤20%; trung bình 16,17%; LG U+ 21,19% | Phương án tuần cải thiện tính dự báo; mentor chưa xác nhận thay R05 ngày. |
| Chọn mô hình bằng validation | V13 có 10/10 đạt ≤20% validation | Khóa trước test; validation đạt không bảo đảm test đạt. Test đã xem trước, nên kết quả test là hồi cứu. |
| Chính sách tồn cơ sở | Đáp ứng 85,02%; thiếu 2.392 quantity | Kết quả mô phỏng theo giả định tồn/nhập/đối tác, chưa chứng minh hiệu quả doanh nghiệp. |
| Báo trước ≥7 ngày | 33,73% trên 2.867 sự kiện cạn mô phỏng | Giữ mẫu số, công khai ca muộn và bỏ sót. |

Nguồn: summary/CSV của `sigma_scaled_v11`, `sigma_weekly_boost_v13`, `sigma_weekly_policy_v4`, `sigma_day_week_comparison_v3`. Bộ khóa `sigma_m2m3_checkpoint_v3` giữ đúng các run này. Ảnh kickoff và điều mentor do người dùng thuật lại được phân biệt ở [đối chiếu nguồn](kickoff-checklist.md).

## Biến động ngày và tổng tuần

Chẩn đoán mới chỉ dùng train đến 30/06/2025 và validation 01/07–30/09/2025. Top 10 giữ theo quantity train. Hệ số biến thiên (CV) là độ lệch chuẩn chia trung bình, không phải MAPE.

Trên validation, CV ngày của top 10 là **0,454–0,598**; CV tổng 7 ngày **0,201–0,348**. Tổng tuần giảm một phần biến động ngày, phù hợp với kết quả dự báo tuần tốt hơn ngày. Cửa sổ tuần chồng lấn không phải mẫu độc lập.

Một kiểm tra hồi cứu rất thuận lợi cho mô hình lịch đã fit weighted median riêng theo tháng×weekday bằng chính dữ liệu từng split. MAPE ngày dương trên validation vẫn **24,54–36,86%**. Đây là fit nhìn lại dữ liệu; không dùng làm forecast, baseline ngoài mẫu hoặc cận dưới của mọi mô hình. Nó cho thấy chỉ thêm lịch tháng/weekday chưa giải thích toàn bộ dao động ngày; **không chứng minh ngưỡng 20% bất khả thi**.

MAPE nhạy với quantity nhỏ: sai 2 khi actual=2 tạo APE 100%; sai 2 khi actual=20 tạo APE 10%. Vì vậy báo cả MAE, WAPE, bias, số cặp dương và độ phủ. Ngày 0 giữ để tính metric tương ứng. Không xóa ngày bán thấp, spike hoặc đơn chưa activation nhằm giảm MAPE.

## Thử nghiệm mùa vụ mới đã loại khỏi top 10

[Mã nghiên cứu](../sigma/experiments/seasonal_weekly.py) dùng bộ nhớ lịch tròn: bốn cấu hình quantity thô/ratio × bandwidth 28/56 ngày, thêm hai ratio với half-life 90 ngày. Ratio dùng mức bán 90 ngày tại origin. Sáu cấu hình áp dụng cho mọi tuyến, refit 7 ngày, nhãn lịch sử hoàn tất trước cutoff. Protocol ghi trước fit.

Run `sigma_seasonal_validation_v14` chấm **45.540 cặp**, đủ độ phủ. Phương án nghiên cứu tốt nhất từng tuyến chỉ có **4/10** đạt 20% validation và **0/10** tốt hơn lựa chọn V13. LG U+ là 15,53%, so với V13 10,96% trên cùng validation. Ba tuyến ngoài top 10 cải thiện validation; chưa tích hợp hoặc chấm test. Không đưa thử nghiệm này vào sản phẩm vì không cải thiện mục tiêu top 10; không dò test để tìm con số thuận lợi.

[Đối soát độc lập](../sigma/verification/seasonal_weekly.py) kiểm nhãn tổng quantity, 1.104 nhóm metric, lưới origin/horizon và 12 phép sửa dữ liệu sau origin trên sáu cấu hình tại hai mốc. Raw và toàn bộ artifact sealed ngày giữ nguyên. Bằng chứng này chưa đóng T09/R05.

```powershell
.\.venv\Scripts\python.exe -m sigma validate-seasonal-weekly --output-id seasonal_new
.\.venv\Scripts\python.exe -m sigma verify-seasonal-weekly --run-id seasonal_new --output-id seasonal_new_check
```

Dùng ID chưa tồn tại. Kết quả local gồm `dispersion.csv`, `validation_comparison.csv`, predictions, metrics, fit log và protocol/hash. Không đưa các file nguồn bài lên GitHub. Dùng lại validation không tạo kiểm định độc lập mới.

## Phân tích cảnh báo 7 ngày

Replay có 5.520 cửa sổ, loại riêng 1.099 ca hết tồn tại origin; còn 2.867 sự kiện cạn. **1.550 ca cạn trước ngày 7** kể từ origin đợt. Nếu bắt đầu theo dõi mặt hàng chỉ đủ bán ba ngày, cảnh báo lúc đó chỉ có ba ngày báo trước. Giao khách D+7 không tạo thêm tồn hoặc sửa thời điểm cạn trong sổ.

Còn **1.317 ca có cơ hội ≥7 ngày**, phát hiện 967 và bỏ sót 350: recall trên nhóm có cơ hội **73,42%**. Đây chỉ là chẩn đoán bổ sung. Tỷ lệ chính giữ **967/2.867 = 33,73%**, không thay bằng 73,42% để nhận đạt R07.

Trang **Tồn từ dự báo tuần → Giải thích từng ca cảnh báo trong replay** hiển thị origin, ngày cạn dự kiến/mô phỏng và nhóm giải thích, lọc tuyến/SKU/loại. Actual phục vụ đánh giá hồi cứu, không đi vào tín hiệu cảnh báo tại origin. Tồn/lịch nhập/mapping đối tác là giả định do không có dữ liệu doanh nghiệp tương ứng.

## Nội dung cần chốt trước nghiệm thu cuối

Mentor cần xác nhận dùng tổng 7 ngày có được thay chỉ tiêu ngày hay chỉ bổ sung phương án. Khách đặt D→giao D+7 đã được người dùng xác nhận; thông tin này không xác nhận metric tuần hoặc lead time nhà cung cấp. Nếu vẫn chấm R05 ngày, kết quả tuần không đóng yêu cầu đó.

Với R07, báo đồng thời tỷ lệ chính, ca gần cạn tại origin, bỏ sót và cảnh báo nhưng không cạn. Không tự đặt ngưỡng precision/recall nghiệm thu. Kết luận báo cáo tiến độ đúng là **đã có sản phẩm tích hợp và bằng chứng kiểm tra; còn R05 và chất lượng cảnh báo cần hoàn thiện**. Chưa nhận đạt 100%.
