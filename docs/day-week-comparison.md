# So sánh dự báo ngày và tổng 7 ngày

Bản so sánh chính thức đã chạy theo yêu cầu CHG-027, không chờ nghiệm thu toàn bài như thứ tự lịch sử CHG-025. Nguồn quantity/success/UTC, split và top 10 train được giữ nguyên. Test đã từng được xem: đây là kết quả hồi cứu.

So sánh công bằng dùng **cùng 86 cửa sổ h1–7 đầy đủ trên mỗi tuyến**: cộng bảy dự báo của mô hình ngày rồi so với mô hình dự báo trực tiếp tổng 7 ngày. H8–14 dùng79 cửa sổ; lịch không chồng lấp13/12 báo riêng. Cả hai phương án vẫn refit theo thông tin quá khứ, không đưa nhãn tương lai vào feature/head.

| Tuyến | MAPE ngày R05 (%) | Tổng dự báo ngày, MAPE tuần (%) | Dự báo trực tiếp tuần, MAPE tuần (%) |
|---|---|---|---|
| Thailand / dtac | 43,29 | 16,88 | 14,17 |
| Thailand / AIS | 44,66 | 28,65 | 18,13 |
| Thailand / TrueMove H | 43,27 | 25,93 | 15,27 |
| Japan / SoftBank | 46,22 | 32,59 | 17,16 |
| Japan / au (KDDI) | 41,89 | 30,18 | 13,30 |
| Japan / NTT Docomo | 43,14 | 27,79 | 17,02 |
| South Korea / KT | 56,39 | 33,97 | 13,09 |
| South Korea / SKT | 45,21 | 36,18 | 12,67 |
| South Korea / LG U+ | 53,70 | 27,54 | **21,19** |
| China / China Mobile | 58,13 | 39,28 | 19,73 |

**Cột MAPE ngày có target khác hai cột tuần**, không dùng mức giảm giữa ngày/tuần để tuyên bố cùng một tiêu chí tốt lên. MAPE tuần trực tiếp thấp hơn tổng dự báo ngày ở cả10 tuyến; mean theo tuyến16,17%, **9/10 đạt≤20%**, LG U+ còn thiếu1,19 điểm phần trăm. R05 ngày vẫn0/10. Một số baseline tuần đơn giản tốt hơn mô hình được chọn trên test của từng tuyến; giữ lựa chọn validation đã khóa, không đổi model bằng kết quả test.

Bản local còn báo MAE, WAPE, bias, coverage, số actual dương/0 cho năm phương án: tuần trực tiếp, tổng daily model, naive, MA7, MA28. Cửa sổ chồng lấp không phải86 quan sát độc lập. Phân bổ tổng tuần xuống ngày và daily model được chấm cùng602 cặp h1–7/tuyến, khác grid R05 chính thức623 cặp: tổng tuần tốt hơn không bảo đảm mỗi ngày đạt20%.

So sánh tồn giữ **13 kịch bản cùng nhu cầu và cùng giả định**:

| Kết quả | Chính sách dự báo ngày | Chính sách dự báo tuần |
|---|---|---|
| Fill cơ sở | 83,52% | 85,02% |
| Thiếu hàng cơ sở (đơn vị) | 2.631 | 2.392 |
| Fill khi nhận50% lượng nhập | 40,99% | 42,27% |
| Fill khi nhập trễ3 ngày | 70,17% | 72,46% |
| Fill khi không nhập | 7,69% | 7,69% |
| Cảnh báo trước≥7 ngày | 33,10% | 33,73% |

Replay dùng cùng2.867 sự kiện/5.520 cửa sổ, giữ các ca cạn trước ngày7;1.099 đã cạn tại origin được loại theo cùng quy tắc gốc. Không tự đặt ngưỡng precision/recall mới. Tồn/nhập/mapping/lead time nhà cung cấp là mô phỏng; khách giao D+7 không trễ là giả định riêng.

Đầu ra đầy đủ nằm trong run private `outputs/sigma_day_week_comparison_v3/`: `comparison.md`, `comparison.html`, hình PNG và bốn CSV chi tiết; summary ghi hash nguồn/cha/từng artifact. Run này so weeklyV13 với dailyv11 và policyV4; kiểm cùng forecast/cửa sổ/source/13kịch bản/sự kiện đạt. V1/V2 và parityV12/V9 giữ làm lịch sử. BảnV13 dùng lựa chọn validation, không chọn từ bảng test này. Không đưa các outputs vào GitHub.

Tạo bản mới bằng [CLI so sánh](../sigma/analysis/comparison.py):

```powershell
.\.venv\Scripts\python.exe -m sigma compare --weekly-run sigma_weekly_boost_v13 --daily-run sigma_scaled_v11 --policy-run sigma_weekly_policy_v4 --output-id comparison_new
```

Mỗi `output-id` phải mới; chương trình từ chối nguồn/protocol khác, thiếu cặp, actual khác nhau hoặc policy forecast không khớp. Xem [cấu trúc mã](code-map.md) và [requirements](requirements.md) để phân biệt so sánh với nghiệm thu.
