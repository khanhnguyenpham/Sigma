# M3 — Bằng chứng và các cổng chưa đóng

**CHG-068 bước 15 — 27/10/2026, local đạt:** đã chạy hai replay thật mới với cấu hình cơ sở khóa trước kết quả; worker và verifier độc lập đạt. Policy fill 90,4121%, thiếu 1.531/15.968; depletion báo sớm 986/2.867 = **34,391350%, chưa đạt mục tiêu làm việc 45%**. Metric xuống ROP giữ riêng (TP101/FP89/FN0/TN619). 245 Python, 50 React, build/pip check, API/CSV/browser đạt; 1.038 hash protected, 140 artifact sealed và hàng cũ của 13 bảng nghiệp vụ + Alembic nguyên. Schema 0003_threshold/0diff; chỉ thêm hai run local, không refit/tuning. R07/T14 chưa nghiệm thu; đang chốt cổng commit/push/SHA/CI. [Bằng chứng và cách kiểm lại](../docs/development.md#handoff-chg068-step15). Các checkpoint bên dưới giữ vai trò lịch sử.

**CHG-073 — 25/10/2026, cập nhật chỉ Markdown:** người dùng thuật lại câu trả lời mentor “đạt 45% theo cấu hình”. [R07](../docs/requirements.md#r07-target-chg073) ghi early rate≥45% với báo trước≥7ngày làm mục tiêu làm việc; tính bắt buộc/phạm vi nghiệm thu còn cần làm rõ. Baseline34,391350% chưa đạt mục tiêu làm việc này, chưa có run mới hoặc bằng chứng cấu hình mới đạt45%. Không đổi code/metric/run; R07/T14 chưa nghiệm thu. Các phát biểu cũ “chưa có ngưỡng tổng” dưới đây là lịch sử trước thông tin thuật lại này, không xóa kết quả/giới hạn cũ.

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo feature và thành phần dùng chung, sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

R05 tiếp tục M05 tổng30 trên test hồi cứu; forecast H14 phục vụ tồn không đổi. R06/R07 phải kiểm lại cho mode mới và cảnh báo ngưỡng; tách khỏi metric depletion. R08/R09 cần kiểm HTTP/React local sau gỡ Streamlit. Phần còn chưa có bundle tổng30 hiển thị `monthly_not_prepared`; không lấy số từ MD thay dữ liệu.

[Kế hoạch CHG-068 và cổng từng bước](../docs/planning/PLAN.md#chg-068).

Bảng đối chiếu cập nhật 27/10/2026 (Asia/Saigon), E117; kết quả R05/M05 giữ bằng chứng hồi cứu E93. Các số E93 không được coi là vừa chạy lại trong E117. Mentor do người dùng thuật lại đã chốt **tổng 30 ngày thay cho từng ngày**. Đây là bảng đối chiếu sản phẩm, không phải biên bản ký nghiệm thu. Tiêu chí ở [requirements](../docs/requirements.md); kết quả và nguồn kiểm chứng ở [MONTHLY](MONTHLY.md); cách chạy stack ở [IMPLEMENTATION](IMPLEMENTATION.md).

| Cổng | Bằng chứng thực có | Trạng thái và giới hạn |
|---|---|---|
| Nguồn/R01 | E117 verify lại source cha:100.000dòng raw/118.296quantity,46tuyến/920item/672.520daily; sourceSHA nguyên. | Đạt kiểm kỹ thuật mới; snapshot trạng thái/A08 vẫn đề xuất, không thành xác nhận kế toán. |
| Forecast/R04 | E117 verifier độc lập lại forecast cha46/H14,17.020route/2.382.800itemforecast,selection/hash/cutoff/bảo toàn đạt; không refit. | Final10 giữ lịch sử hồi cứu/LG U+ test-selected; chưa có holdout mới độc lập. |
| Độ chính xác/R05 theo M05 | Tổng30 test: **10/10 tuyến ≤20%, mean11,621356%, coverage100%, 63 cửa sổ/tuyến**. Verifier nguồn chạy lại và đối soát route-day/nhãn/metric với DB M3. | **Đạt ngưỡng số học M05 trên test hồi cứu.** Hướng focus từng dựa vào test cũ; chưa có holdout mới độc lập. Ngày/tổng7 giữ làm chẩn đoán, không còn là điều kiện R05. |
| Tồn/R06 | E117 policy replay mới verified:85.560ledger/16.423events/3.245lô;fill90,412074%,shortage1.531/15.968; strict<,IP chỉQ,MOQ/ETA/receipt và hai mode có regression. | Đạt kiểm kỹ thuật; tồn/nhập/đối tác vẫn mô phỏng. Không có tiêu chí fill100% hoặc dữ liệu tồn thật. |
| Cảnh báo/R07 | E117 alert replay mới verified:early986/2867=34,391350%,TP2098/FP852/FN769/TN702;loại1099đã cạn origin,đuôi8ngày. Threshold riêngTP101/FP89/FN0/TN619. | **Chưa đạt mục tiêu làm việc45% ở cấu hình cơ sở; chưa nghiệm thu.** Giữ cả1550ca D+1…D+6 trong mẫu số; tính bắt buộc/phạm vi45% còn cần làm rõ. Không gộp threshold vào depletion. |
| Dashboard/R08 | E117 React6màn hình local,policy/scenario SS/ROP/N,filter/drawer/chart/UTC/CSV và metric riêng đã kiểm trên replay mới; Escape/focus/reload đạt. | React/FastAPI/PostgreSQL local; Streamlit đã gỡ khỏi source theo CHG-068. Thiếu bundle tổng30 giữ monthly_not_prepared. Chưa có auth/PO thật hoặc hosting mới. |
| Tái lập/R09/T12 | E117:245Python/50React/build/pipcheck; worker+verifier+SQL/API/CSV;1038protected/140sealed files/hàng cũ13bảng+Alembic nguyên,0003_threshold/0diff. | Run/nguồn/DB/env giữ local,Git chỉ aggregate MD; CI kiểm riêng sau push. Chưa diễn tập máy nhóm khác. |
| Bàn giao/T14 | E117 kiểm/bàn giao15bước CHG-068; run/hash/protocol/metric/giới hạn và lệnh verify mới có truy vết. | **Chưa ký nghiệm thu toàn bài**: R07 cơ sở chưa đạt mục tiêu45%, mentor còn rà A08/phạm vi mô phỏng/R07/holdout; R05/M05 giữ kết quả hồi cứu lịch sử. |

R02/R03 và các sản phẩm M1/M2 lịch sử cần đối chiếu nhật ký riêng khi nghiệm thu toàn bài; lượt E92 không tái chạy EDA/lịch lễ hoặc khôi phục các tệp M2 đã dọn. Không dùng bảng M3 này để nâng trạng thái của các nguồn chưa kiểm lại.

## Phần chẩn đoán giữ riêng

Nghiên cứu ngày E91/E92 giữ lịch sử: validation từ phân bổ51,905954% xuống49,451918% rồi45,971604%; vẫn0/10. Theo M05 đây không còn là cổng chính R05. Tổng30 được kiểm riêng, không thay nhãn hoặc coi metric ngày đã tốt hơn. Không cần tiếp tục fit mô hình ngày chỉ để đáp ứng tiêu chí đã được mentor thay đổi.

Với R07,1550/2867sự kiện cạn trướcD+7; tại các origin/tồn đầu đó không còn đủ7ngày để báo sớm. Trần thời gian riêng replay này45,9365%, không phải trần mọi hệ thống.331ca đủ thời gian nhưng bỏ sót đều có tồn đầu≤2,311ca tồn1; forecast tổng14ngày thấp hơn tồn trong cả331ca. Dự báo điểm chưa chạm0 không đồng nghĩa rủi ro bằng0. Đây là phân tích sau replay, không dùng để đổi forecast, ngưỡng hoặc mẫu số.

Đối chiếu mục tiêu làm việc45% của CHG-073 trên đúng tập2.867sự kiện cũ cần tối thiểu1.291ca báo sớm, thêm305ca so986, tương đương98,0258% trong1.317ca còn đủ thời gian. Phép tính này không là kết quả thử nghiệm mới hoặc bằng chứng mục tiêu chắc chắn đạt. Giữ cả ca D+1…D+6 trong mẫu số; không dùng tỷ lệ có điều kiện trong1.317ca thay tỷ lệ chính thức. Đổi cấu hình làm đổi tập sự kiện phải báo riêng counts và phạm vi; không so như cùng mẫu. [Hợp đồng đánh giá](../docs/requirements.md#r07-target-chg073), [quy ước CHG-073](../docs/planning/PLAN.md#chg073).

Nếu cải thiện cảnh báo: nghiên cứu nhu cầu thưa/độ bất định trên dữ liệu quá khứ, kiểm calibration và trade-off false positives trước đổi profile; thay serving cần run/verify mới. Bàn giao hiện tại phân biệt rõ R05 số học đã đạt với R07 đã đo và T14 chờ mentor review.
