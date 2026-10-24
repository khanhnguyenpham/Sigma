# M3 — kiểm thử, nghiệm thu và bàn giao

**CHG-069 — kiểm refactor FE bước8–9 (dự kiến):** [cấu trúc mới](04-frontend-spec.md#frontend-target-chg069) dùng pages/layouts/components cùng services/hooks/types/utils/config. Giữ tests tại frontend/tests, cập nhật import khi chuyển code; kiểm sáu URL, context/Back/refresh, abort/stale, read30s/write90s/không autoretry write, loading/error/retry đọc, Escape/focus/mobile và CSV/null khác0. Lượt đổi đặc tả chỉ kiểm Markdown; không lấy kết quả test lịch sử làm kiểm mới.

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo pages, layouts và component dùng chung (CHG-069), sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Kiểm15bước theo PLAN. Baseline trước refactor: API/CSV, pure inventory, forecast fixture1e-8, FE và hash protected. Kiểm4tổ hợp mode, history thiếu/zero/NaN/overflow, causal future mutation; cảnh báo ROP−1/=ROP/+1, N/N+1, receipts và dedup; migration/snapshot cũ; UI lưu→run→tồn/cảnh báo→CSV và stale/error/focus/mobile. Cuối cùng replay local run mới, đối soát độc lập, không refit model vì sửa MD.

[Kế hoạch CHG-068 và cổng từng bước](../../docs/planning/PLAN.md#chg-068).

**Cập nhật M05/E93 — 20/10/2026:** [R05 tổng30 và implementation hiện hành](../MONTHLY.md) thay cổng độ chính xác ngày bằng tổng D+1…D+30 theo mentor do người dùng thuật lại. Đã đối soát 10/10≤20% hồi cứu. Benchmark chỉ đọc có manifest/source/target/hash riêng, API/UI/CSV; không thêm bảng DB hoặc thay forecast tồn H14. Các mục R05 ngày dưới đây mô tả thiết kế trước M05; A08 và nghiệm thu mentor vẫn tách riêng.

**E91 kiểm trực tiếp:**86tests Python (54M3+32M2),9FE/build đạt. Ca mới kiểm ranh6/7/14ngày, mẫu số/không sự kiện/null, chặn filter/summary lệch/run sai kind/failed, mutation tương lai không đổi feature/nhãn fit nghiên cứu và stale UI khi đổi run. Đây là số kiểm phần mềm, không đóng R05/R07/T14.

**Hiện hành E90:** ứng dụng đã có code và fullrun local theo profile này. Xem [implementation, số kiểm thực và giới hạn](../IMPLEMENTATION.md). Nội dung E76/E89 có chữ “dự kiến/chưa triển khai” bên dưới là lịch sử thiết kế/checkpoint; không dùng làm trạng thái hiện hành hoặc bằng chứng chạy. R05/R07/T14 vẫn mở.

**Cập nhật implementation E89:** E89:35tests M3 đã thực chạy, gồm PostgreSQL/API/concurrency, và32tests M2 hồi quy đạt; ML36/fullreplay/FE/E2E chưa chạy. Các ca còn lại bên dưới giữ vai trò testplan. [Phạm vi thực](../README.md#implementation-e89). Các nhãn “chưa có/dự kiến” bên dưới là trạng thái đặc tả ban đầu, chỉ được thay thế trong phần đã liệt kê.

**Trạng thái:** test plan/lịch dự kiến, chưa có tests ứng dụng hoặc run ML M3 mới. CHG-048 chỉ chạy kiểm Markdown, đặc tả và bảo toàn file. Bằng chứng thực ở [review-log E76](../../docs/review-log.md#e76).

## 1. Cổng hoàn thành

| Cổng | Đầu ra | Truy vết |
|---|---|---|
| Đặc tả | 7MD,13 bảng/ERD,API/FE/source nhất quán; nguồn/giả định; commit/push nhánh riêng. | T01/T10/T11/T12; CHG-048 |
| Forecast | ML36 mới/final10 nguyên; validation selection khóa;46/H14/allocation causal. | T08/T09; R04/R05 |
| Tồn/cảnh báo | ROP/MOQ/ETA7/ledger; replay độc lập và policy liên tục; mẫu số/độ nhạy. | T10/T12; R06/R07 |
| UI tích hợp | Sáu trang/API/DB local; E2E giả; số/chart/export khớp run. | T11/T12; R08/R09 |
| Bàn giao | Manifest/hash/demo/lệnh chạy đã kiểm; trạng thái từngR và giới hạn. | T13/T14 |

Cổng đặc tả không kéo cổng khác thành đạt. R05 ngày vẫn top10/ngày dương≤20% kèm coverage/MAE/WAPE/bias, không thay bằng mean46/tổng7. R07 cần replay thực, không đóng chỉ vì có UI hoặc ca tính tay.

## 2. Kiểm Markdown trong lượt hiện tại

Kiểm UTF-8/link tương đối/anchor mới, bảng đúng cột, fence đóng, ERD đúng13 tên bảng/quan hệ, API không trùng method/path, schema/DTO/FE cùng field. Số giả kiểm công thức ROP/MOQ/ETA và precision/recall là kiểm đặc tả, không là test implementation. Source/CLI chưa tồn tại chỉ ghi trong backtick/khối dự kiến, không tạo link giả.

Kiểm git diff --check, allowlist Markdown, không private rows/credential/ảnh/raw mới. Giữ SHA CSV và file code/config/report/forecast được bảo vệ. Link lịch sử thiếu nguồn ghi giới hạn, không khôi phục. Kết quả đếm kiểm thực ghi E76 sau khi chạy; không điền số tests ứng dụng giả.

## 3. Forecast và leakage — dự kiến

| Ca | Cách kiểm độc lập | Kỳ vọng |
|---|---|---|
| Catalog | Đếm route/item snapshot audit và tuyến train. | 46 kho/920 catalog item; tại origin chỉ first_seen≤origin. |
| Final10 | So từng origin/block với bundle final cùng source/protocol. | Lựa chọn/hash cha nguyên; forecast≤1e-8; không pool46 vào final10. |
| Selection36 | Tính lại metric validation6 ứng viên/tuyến và tie. | Full coverage; MAPE→MAE→ID; không tuần dương dùngMAE; không chọn theo test. |
| Nhãn | Sửa dữ liệu sau origin và nhãn tuần chưa kết thúc. | Forecast/features/selection ở origin trước giữ nguyên. |
| Phân bổ | Block1=70/block2=140, weekday đều, shares0,6/0,4. | Ngày10→item6/4 và ngày20→item12/8; tổng70/140. |
| Cửa sổ | 30 ngày0/90 có bán; cả hai0; nguồn thiếu ngày. | Dùng90; thiếu basis thì lỗi; thiếu nguồn khác ngày bán0. |
| Metric | Actual [0,10], forecast [5,12]. | MAPE20%;MAE3,5;WAPE70%;bias+3,5;positive1/labeled2. |
| Future | Cutoff31/12/2025, forecast01–14/01/2026. | Actualnull, không chấm; activation không là actual sales. |

Negative clipping có counter; không bỏ forecast xấu khỏi mẫu số. Fit log có max_label_end≤cutoff; future mutation kiểm cả allocation/item eligibility. Không mở sweep mới theo test.

## 4. Tồn, lô nhập và policy — dự kiến

Fixture giả f[h]=10/safety2/floor100/MOQ50 → SS20/ROP_forecast90/ROP100/S110.

| Ca | Input | Kỳ vọng |
|---|---|---|
| Dưới | Closing99/pending0 | Triggertrue/Q_raw11/Q50. |
| Bằng/trên | Closing100 hoặc101 | Triggerfalse/Q0 dùMOQ50. |
| Pending đủ | Closing80/pending40 | IP120/triggertrue/Q0/pending_covers. |
| Supplier khác | Floor150/MOQ100,closing80 | ROP150/S160/Q100, khác supplierA Q50. |
| Floor0 | Closing80 | ROP90/S100/Q50; forecast vẫn quyết định. |
| ETA | Ordered31/10/2025 cuối ngày qty50 | Nhận đầu 07/11 đúng một lần, gồm weekend. |
| Cân bằng | Opening12/receipt5, yêu cầu7 rồi15 | Fulfilled17/shortage5/closing0/sales22. |
| Không âm | Opening0/sales3 | Fulfilled0/shortage3/closing0; sales vẫn3. |
| Retry | Lặp decision/receipt cùng key | Một lô/một receipt, pending/tồn không nhân đôi. |
| Version | Hai request cùng expected_version | Một thắng/một409; run cũ giữ snapshot. |
| Chồng khoảng | Hai supplier/item cùng ngày hiệu lực | Từ chối; không chọn supplier ngầm. |
| Thiếu config | Thiếu policy/vector14 | Lỗi rõ, run khôngcomplete; Q/ROP thiếu khác0. |

Không dùng stress lead time1/3 hoặc nhận trễ nghiệm thu profile L7 cố định. Độ nhạy cover3/7/14 và safety multiplier0,5/1/1,5, đổi một trục mỗi lần. Ghi đảo chiều cảnh báo/fill/tồn, không chọn số chỉ để đạt điểm.

## 5. Cảnh báo và mẫu số — dự kiến

| Ca | Điều kiện | Kỳ vọng |
|---|---|---|
| Sớm | Tồn100/f10 không receipt | CạnD+10/lead10/early. |
| Muộn | Tồn30/f10 | CạnD+3/urgent, không tính sớm. |
| Đã cạn | Origin tồn0 | already_depleted, ngoài mẫu sự kiện tương lai. |
| NgoàiH | Tồn200/f10 | not_within_horizon/null ngày; không bịaD+20. |
| ETA | Tồn100/f10,receipt100 D+7 | Nhận trước bánD+7; không cạn trong 14, không cộng lùiD+1. |
| Một event | Nhiều ngày tiếp tục0 | Chỉ first depletion/item/window. |
| Confusion | A dự đoán/thựcD+10; B dự đoánD+3/thực không cạn; C không dự đoán/thựcD+9 | TP1/FP1/FN1;precision0,5/recall0,5;early1/2=0,5. |
| Không mẫu | Không cảnh báo hoặc sự kiện | Tỷ lệ có mẫu số0=null, kèm counts. |

Replay14 không chồng từ 30/09/2025, đủ nhãn, no-new-order/receipts biết trước. Có 6 đợt đủ nhãn, origin cuối09/12 và kết thúc23/12/2025; 8 ngày24–31/12 ngoài các đợt đủ14 được công khai, không chấm như đủ nhãn. Policy replay có đặt/ETA là lượt khác; không coi ngăn cạn là FP. Lưu ca bị loại và lý do; không bỏ ca báo muộn.

## 6. API/DB/FE — dự kiến

PostgreSQL integration với fixture giả: PK/FK/UNIQUE/CHECK, overlap hai transaction, receipt một lần, idempotency body conflict, parent mismatch/complete gate. Migration DB mới/upgrade, đúng13 bảng nghiệp vụ. Worker restart giữ interrupted/failed; worker thứ hai không chạy; HTTP không đợi fit.

BE pytest/TestClient kiểm DTO/filter/pagination/null/202/status/404/409/422/503/export. Mismatch source/config phải fail; không trả rows partial như complete. Adapter smoke dùng predictor giả. FE Vitest/RTL kiểm loading/empty/error/null/coverage/URL/stale response/filter/version409/double click.

Playwright: chọn synthetic forecast → scenario → policy replay → complete → inventory/alert/nhập → export cùng filter. Chart/table/export đối soát API/DB; keyboard/labels,1366×768 và 768px. Không đưa raw ID vào schema/log/fixture public.

Raw/hash trước–sau full local; output riêng, notebook không private output, env/DB ignored. Demo public chỉ synthetic; CSV thật chỉ local. R09 cần manifest/lệnh chạy đã kiểm, không chỉ sơ đồ kiến trúc.

## 7. Chạy thật và bàn giao sau implementation

Sau unit/integration mới chạy ML36 local: lưu duration/versions/spec/selection/hash/coverage/metric từng tuyến; đối soát final10. Sau đó hai loại replay cùng source/forecast/scenario khóa, counters ledger/events/orders/bảo toàn/mẫu số thật. Không đổi ngưỡng/ngày/tuyến để làm đẹp kết quả; không đạt ghi đúng.

Bàn giao theo [development](../../docs/development.md#handoff): thời điểm/thư mục; Txx/Rxx/Axx/decision; file thực/dự kiến; lệnh/check thực; kết quả/run/hash; chưa chạy/giới hạn; kết quả cần kiểm lại; bước tiếp. R05/R07/T14 chỉ đóng khi đủ bằng chứng. Gói hiện tại chưa chứng minh app/ML/DB M3 chạy.

## 8. Lịch triển khai dự kiến

| Mốc mục tiêu năm2026 | Công việc/phụ thuộc/sản phẩm | Task hiện hữu |
|---|---|---|
| 19–22/10 | Đặc tả/schema/API/FE review; setup/migration sau khi nhận việc code. | T01/T10/T11/T12 |
| 23–28/10 | AdapterM2/ML36/selection/allocation46; catalog/policy seed giả. | T08/T09/T10 |
| 29/10–02/11 | Ledger/ROP/MOQ/ETA7/worker/API; hai replay/test DB. | T10/T11/T12 |
| 03–05/11 | Sáu màn hình/E2E giả/full local/đối soát; công khai chưa đạt. | T11/T12 |
| 06–07/11 | Freeze run/config/demo/báo cáo/trạng thái nghiệm thu. | T13/T14 |

Lịch mục tiêu chưa đo công sức, không cam kết ML/cảnh báo chắc chắn đạt. Nếu forecast36 lỗi/allocation thiếu thì gate failed, xử lý phần độc lập; không che bằng0 hoặc giảm scope46 ngầm. Giữ hệ Txx hiện hữu, không tự phân công lại nhóm từ lịch sử.
