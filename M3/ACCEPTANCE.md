# M3 — Bằng chứng và các cổng chưa đóng

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo feature và thành phần dùng chung, sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

R05 tiếp tục M05 tổng30 trên test hồi cứu; forecast H14 phục vụ tồn không đổi. R06/R07 phải kiểm lại cho mode mới và cảnh báo ngưỡng; tách khỏi metric depletion. R08/R09 cần kiểm HTTP/React local sau gỡ Streamlit. Phần còn chưa có bundle tổng30 hiển thị `monthly_not_prepared`; không lấy số từ MD thay dữ liệu.

[Kế hoạch CHG-068 và cổng từng bước](../docs/planning/PLAN.md#chg-068).

Hiện trạng ngày 20/10/2026 (Asia/Saigon), E93/M05. Mentor do người dùng thuật lại đã chốt **tổng 30 ngày thay cho từng ngày**. Đây là bảng đối chiếu sản phẩm, không phải biên bản ký nghiệm thu. Tiêu chí ở [requirements](../docs/requirements.md); kết quả và nguồn kiểm chứng ở [MONTHLY](MONTHLY.md); cách chạy stack ở [IMPLEMENTATION](IMPLEMENTATION.md).

| Cổng | Bằng chứng thực có | Trạng thái và giới hạn |
|---|---|---|
| Nguồn/R01 | Import100.000dòng, quantity118.296,46tuyến/920item; sourceSHA nguyên, audit/dedup/UTC/activation không lọc sales. | Đã kiểm kỹ thuật E89/E90. A08 vẫn là đề xuất trên snapshot trạng thái, không tự xác nhận kế toán. |
| Forecast/R04 | Full46/H14,36selection validation, final10 giữ nguyên,185origins và2.382.800itemforecast kiểm bảo toàn/cutoff. | Đã triển khai. Final10 có lịch sử test hồi cứu/LG U+ test-selected; không gọi holdout độc lập. |
| Độ chính xác/R05 theo M05 | Tổng30 test: **10/10 tuyến ≤20%, mean11,621356%, coverage100%, 63 cửa sổ/tuyến**. Verifier nguồn chạy lại và đối soát route-day/nhãn/metric với DB M3. | **Đạt ngưỡng số học M05 trên test hồi cứu.** Hướng focus từng dựa vào test cũ; chưa có holdout mới độc lập. Ngày/tổng7 giữ làm chẩn đoán, không còn là điều kiện R05. |
| Tồn/R06 | Ledger giao dịch, strict closing<ROP, IP chỉQ,MOQ, ETA7, receipts đầu ngày, snapshot và replay; cơ sở fill90,4121%,shortage1531. | Đã kiểm kỹ thuật/độ nhạy; không có tiêu chí fill100% hoặc tồn thật. Các số là mô phỏng, không khẳng định đủ hàng mọi trường hợp. |
| Cảnh báo/R07 | Cơ chế ngày cạn/no-new-order replay cóTP/FP/FN/TN,dateMAE và mẫu số; early986/2867=34,3913%. Ca chuẩn6/7/14ngày cótests. | Đã triển khai/đã đo, **chưa nghiệm thu**. Không có ngưỡng precision/recall/early-rate tổng chính thức; không tự thêm100% hoặc nhận tỷ lệ này là đạt một ngưỡng chưa được chốt. |
| Dashboard/R08 | React6 màn hình/API/URL/filter/CSV/loading/error/null; thêm benchmark tổng30, metric từng tuyến, baseline và context SHA. | Local8000 và E94 Streamlit public7màn hình/what-if. Huấn luyện/import raw/worker/DB vẫn local; chưa quản trị cloud nhiều người dùng hoặc đặt hàng thật. |
| Tái lập/R09/T12 | E93: **97 Python, 11 frontend, TypeScript/build đạt**; Python 0 fail/error/skip. Kiểm API thật top10/46/null/CSV/snapshot binding; 17 Markdown/112 link M3/69 bảng không lỗi. | Bằng chứng local; CI của commit mới kiểm riêng trên GitHub. Chưa thay diễn tập toàn dữ liệu trên máy nhóm khác. Golden1e-8 kiểm Windows; Linux có giới hạn Prophet đã công khai. |
| Bàn giao/T14 | Mã/tests/docs/Git, hướng dẫn chạy, dữ liệu riêng tư local, giới hạn và artifact receipt. R05 số học M05 đã đạt. | **Chưa ký nghiệm thu toàn bài**: mentor cần rà target A08, phạm vi mô phỏng/R07 và giới hạn holdout. Không tự cấp điểm hoặc ký thay mentor. |

R02/R03 và các sản phẩm M1/M2 lịch sử cần đối chiếu nhật ký riêng khi nghiệm thu toàn bài; lượt E92 không tái chạy EDA/lịch lễ hoặc khôi phục các tệp M2 đã dọn. Không dùng bảng M3 này để nâng trạng thái của các nguồn chưa kiểm lại.

## Phần chẩn đoán giữ riêng

Nghiên cứu ngày E91/E92 giữ lịch sử: validation từ phân bổ51,905954% xuống49,451918% rồi45,971604%; vẫn0/10. Theo M05 đây không còn là cổng chính R05. Tổng30 được kiểm riêng, không thay nhãn hoặc coi metric ngày đã tốt hơn. Không cần tiếp tục fit mô hình ngày chỉ để đáp ứng tiêu chí đã được mentor thay đổi.

Với R07,1550/2867sự kiện cạn trướcD+7; tại các origin/tồn đầu đó không còn đủ7ngày để báo sớm. Trần thời gian riêng replay này45,9365%, không phải trần mọi hệ thống.331ca đủ thời gian nhưng bỏ sót đều có tồn đầu≤2,311ca tồn1; forecast tổng14ngày thấp hơn tồn trong cả331ca. Dự báo điểm chưa chạm0 không đồng nghĩa rủi ro bằng0. Đây là phân tích sau replay, không dùng để đổi forecast, ngưỡng hoặc mẫu số.

Nếu cải thiện cảnh báo: nghiên cứu nhu cầu thưa/độ bất định trên dữ liệu quá khứ, kiểm calibration và trade-off false positives trước đổi profile; thay serving cần run/verify mới. Bàn giao hiện tại phân biệt rõ R05 số học đã đạt với R07 đã đo và T14 chờ mentor review.
