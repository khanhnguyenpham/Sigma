# M3 — Bằng chứng và các cổng chưa đóng

Hiện trạng ngày20/10/2026 (Asia/Saigon), E92. Đây là bảng đối chiếu cho sản phẩm M3, không phải biên bản mentor nghiệm thu toàn bộ M1–M3. Tiêu chí gốc ở [requirements](../docs/requirements.md); số run/hash và cách chạy ở [IMPLEMENTATION](IMPLEMENTATION.md).

| Cổng | Bằng chứng thực có | Trạng thái và giới hạn |
|---|---|---|
| Nguồn/R01 | Import100.000dòng, quantity118.296,46tuyến/920item; sourceSHA nguyên, audit/dedup/UTC/activation không lọc sales. | Đã kiểm kỹ thuật E89/E90. A08 vẫn là đề xuất trên snapshot trạng thái, không tự xác nhận kế toán. |
| Forecast/R04 | Full46/H14,36selection validation, final10 giữ nguyên,185origins và2.382.800itemforecast kiểm bảo toàn/cutoff. | Đã triển khai. Final10 có lịch sử test hồi cứu/LG U+ test-selected; không gọi holdout độc lập. |
| Độ chính xác/R05 | Serving allocated_daily test top10:0/10≤20%,mean51,919555%. Tổng7 fixed10:10/10 hồi cứu,15,745366%. | **Chưa đạt tiêu chí ngày.** Tuần không thay ngày. Nghiên cứu ngày v2 validation45,971604%,0/10; chưa chấm test hoặc thay serving. |
| Tồn/R06 | Ledger giao dịch, strict closing<ROP, IP chỉQ,MOQ, ETA7, receipts đầu ngày, snapshot và replay; cơ sở fill90,4121%,shortage1531. | Đã kiểm kỹ thuật/độ nhạy; không có tiêu chí fill100% hoặc tồn thật. Các số là mô phỏng, không khẳng định đủ hàng mọi trường hợp. |
| Cảnh báo/R07 | Cơ chế ngày cạn/no-new-order replay cóTP/FP/FN/TN,dateMAE và mẫu số; early986/2867=34,3913%. Ca chuẩn6/7/14ngày cótests. | Đã triển khai/đã đo, **chưa nghiệm thu**. Không có ngưỡng precision/recall/early-rate tổng chính thức; không tự thêm100% hoặc nhận tỷ lệ này là đạt một ngưỡng chưa được chốt. |
| Dashboard/R08 | React6màn hình/API/URL/filter/CSV/loading/error/null; kiểm trình duyệt và scenario mới qua worker. | Đã chạy local tại8000. Hosting/auth/multiuser/đặt hàng thật ngoài phạm vi profile. |
| Tái lập/R09/T12 | E92:89Python/0fail/skip; E91:9FE/build và haiCI đạt. V1 sau refactor giữ byte-exact95.760predictions/metrics/selection; v2 kiểm60metricgroups/168cutoffs. | Bằng chứng local và CI fixture, chưa thay diễn tập toàn dữ liệu trên máy nhóm khác. Golden1e-8 kiểm Windows; Linux có giới hạn Prophet đã công khai. |
| Bàn giao/T14 | Mã/tests/docs/Git, hướng dẫn chạy, dữ liệu riêng tư local, giới hạn và artifact receipt. | **Chưa nghiệm thu toàn bài** vì R05 chưa đạt và cần người có thẩm quyền rà kết quả/phạm vi. Không thể tự cấp điểm hay ký thay mentor. |

R02/R03 và các sản phẩm M1/M2 lịch sử cần đối chiếu nhật ký riêng khi nghiệm thu toàn bài; lượt E92 không tái chạy EDA/lịch lễ hoặc khôi phục các tệp M2 đã dọn. Không dùng bảng M3 này để nâng trạng thái của các nguồn chưa kiểm lại.

## Vì sao chạy thêm chưa đồng nghĩa đạt

MAPE≤20% là kết quả cần kiểm chứng, không phải tham số cài đặt. Nghiên cứu v1/v2 đã hạ lỗi validation từ phân bổ51,905954% xuống49,451918% rồi45,971604%; vẫn0/10. Chỉ chọn bằng validation, không dùng actual tương lai làm feature, sửa sales hoặc bỏ tuyến/ngày khó. Không có bằng chứng rằng mọi mô hình đều không thể đạt20%; cũng chưa có bằng chứng mô hình hiện tại đạt để báo thành công.

Với R07,1550/2867sự kiện cạn trướcD+7; tại các origin/tồn đầu đó không còn đủ7ngày để báo sớm. Trần thời gian riêng replay này45,9365%, không phải trần mọi hệ thống.331ca đủ thời gian nhưng bỏ sót đều có tồn đầu≤2,311ca tồn1; forecast tổng14ngày thấp hơn tồn trong cả331ca. Dự báo điểm chưa chạm0 không đồng nghĩa rủi ro bằng0. Đây là phân tích sau replay, không dùng để đổi forecast, ngưỡng hoặc mẫu số.

Việc tiếp theo thuộc T08–T12: nghiên cứu nhu cầu thưa/độ bất định trên dữ liệu quá khứ, kiểm calibration và trade-off cảnh báo/false positives trước đổi profile; bất kỳ thay đổi serving nào cần run/verify mới. T14 cần đối chiếu tiêu chí và mentor review, không ép phần mềm tự tuyên bố đạt.
