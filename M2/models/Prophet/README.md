# Prophet final — au (KDDI)

[model.py](model.py) giữ fit/update/predict; [variants.json](variants.json) chỉ còn `prophet_annual3_weekly_w540`. `families.ts_job` refit mỗi7 origin trên nhãn tổng trượt7 đã hoàn tất, cửa sổ540 ngày, riêng tuyến au (KDDI).

Additive, yearly Fourier3, weekly bật, changepoint_prior_scale0,01, n_changepoints10, uncertainty_samples0 và seed42. Không chuẩn hóa ratio; predict chuỗi tổng trượt, lấy D+7 và D+14. Hệ số giữ cố định giữa các lần refit. [Bản đồ code](../../README.md).

Các biến thể Prophet cũ và runner so sánh được lưu trên `backup/m2-before-cleanup`; mọi báo cáo/run nghiên cứu vẫn giữ nguyên.
