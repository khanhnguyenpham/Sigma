# M3 — chức năng và quy tắc nghiệp vụ

<a id="configurable-calculation-step11"></a>
## Công thức thực sau bước11 CHG-068 — 25/10/2026

Backend đã thực hiện đủ4tổ hợp từ policy/override đóng băng; bỏ guard stage_not_implemented của bước10. Không thêm migration/route/dependency hoặc sửa FE; M3 giữ tài liệu, mã tại web. Đây là mở rộng tính toán, chưa có tín hiệu projected_below_rop hoặc control mode mới trên FE (bước12–14).

- SS days: ceil(safety_multiplier × safety_days × mean(f1…f14)), giữ thứ tự nhân/ceil của mặc định trước.
- SS volatility: ceil(safety_multiplier × safety_factor × std_population(quantity) × sqrt(7)); ddof0, không dùng sample std. Python statistics.pstdev dùng số đếm integer, tránh mất phương sai nhỏ khi quantity gần bigint max. Zero/std0 hoặc hệ số0 cho SS0 nhưng vẫn yêu cầu đủ lịch sử đã quan sát.
- ROP fixed = configured_rop_floor, không cộng SS lần nữa. ROP forecast = max(floor, ceil(sum(f1…f7)+SS)). Trường rop_forecast vẫn chứa ngưỡng chẩn đoán forecast ở cả hai mode; chỉ rop là ngưỡng được chọn. H14 đầy đủ vẫn bắt buộc cho S/projection/chẩn đoán.
- S=ROP+ceil(f8); IP=closing+pending; trigger closing<ROP (bằng ROP không trigger); Q chỉ khi trigger và S>IP, áp MOQ khi Q dương. ETA D+7 và receipts/pending/order timing giữ trước bước11. Bất kỳ SS/ROP/diagnostic/S/IP/Q vượt bigint hoặc tính không hữu hạn báo numeric_overflow, không sinh Q0 giả.

Cửa sổ volatility gồm đúng safety_lookback_days ngày lịch UTC đến ngày quyết định, từ DailySales của source frozen (không lấy fulfilled/lost-sales mô phỏng làm actual). Ngày thiếu, actual_available=false, null/NaN/Infinity/số âm/phân số/trùng ngày không được biến thành0; nguồn đủ ngày có quantity0 hợp lệ. Policy replay cập nhật cutoff mỗi ngày sau bán; alert replay giữ ngày origin trong cả cửa sổ, không dùng actual tương lai tính SS. Stock projection không bị chặn bởi nhãn chưa biết sau origin. Replay vẫn yêu cầu actual của các ngày được chấm/ghi ledger; tồn đầu vẫn dựa28ngày quan sát như trước.

Ví dụ tính tay: f1…7=2 mỗi ngày, f8=4, f9…14=6, safety_days2, m1,5, factor2, lịch sử7ngày [0,1,2,3,4,5,6], floor10, MOQ5, closing8, pending3. mean(f14)=27/7, std_population=2, IP11:

| Safety | ROP mode | SS | rop_forecast | ROP | S | Q |
|---|---|---|---|---|---|---|
| days | fixed |12|26|10|14|5|
| days | forecast |12|26|26|30|19|
| volatility | fixed |16|30|10|14|5|
| volatility | forecast |16|30|30|34|23|

Independent verifier đọc lại DailySales/forecast/frozen policy và tự tính SS/ROP/S/IP/Q, kiểm cutoff và khoảng hiệu lực; không gọi recommend/history_at của simulation. Chỉ dùng chung thư viện số học chuẩn.214Python/34React/build đạt, worker12tổ hợp4mode×3run, API/CSV/manifest và ca tamper SS/cutoff đã kiểm.9snapshot tồn và M2 golden1e-8 nguyên; projection app cũ920ngưỡng cũng verified trong transaction readonly. [Bàn giao, bằng chứng và giới hạn](../../docs/development.md#handoff-chg068-step11). R07/T14 vẫn chờ nghiệm thu, không dùng các ca synthetic để nâng trạng thái.


**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo pages, layouts và component dùng chung (CHG-069), sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Đặc tả bổ sung: SS_days=ceil(m×b×mean(f14)); SS_volatility=ceil(m×k×std_population(quantity_ngày_quá_khứ)×sqrt(7)). Cửa sổ đủ7–90ngày đến origin (mặc định28); missing source chặn, zero-sales hợp lệ. ROP_fixed=configured_rop_floor (đã chứa dự trữ, không cộng SS lại); ROP_forecast=max(floor,ceil(sum(f1..7)+SS)). S/IP/Q/MOQ/ETA giữ công thức cũ. Nếu tồn hiện tại≥ROP và projection trong N ngày có closing<ROP thì cảnh báo dự kiến; bằng ROP chưa báo. Giữ ROP tại origin, receipts biết ở origin, không thêm lô Q mới để che rủi ro. Cảnh báo depletion và metric cũ tách riêng.

[Kế hoạch CHG-068 và cổng từng bước](../../docs/planning/PLAN.md#chg-068).

**Cập nhật M05/E93 — 20/10/2026:** [R05 tổng30 và implementation hiện hành](../MONTHLY.md) thay cổng độ chính xác ngày bằng tổng D+1…D+30 theo mentor do người dùng thuật lại. Đã đối soát 10/10≤20% hồi cứu. Benchmark chỉ đọc có manifest/source/target/hash riêng, API/UI/CSV; không thêm bảng DB hoặc thay forecast tồn H14. Các mục R05 ngày dưới đây mô tả thiết kế trước M05; A08 và nghiệm thu mentor vẫn tách riêng.

**Hiện hành E90:** ứng dụng đã có code và fullrun local theo profile này. Xem [implementation, số kiểm thực và giới hạn](../IMPLEMENTATION.md). Nội dung E76/E89 có chữ “dự kiến/chưa triển khai” bên dưới là lịch sử thiết kế/checkpoint; không dùng làm trạng thái hiện hành hoặc bằng chứng chạy. R05/R07/T14 vẫn mở.

**Cập nhật implementation E89:** E89: đã có hàm tính thuần và seed/cấu hình policy được test; fullforecast/replay vẫn là đích thiết kế. [Phạm vi thực](../README.md#implementation-e89). Các nhãn “chưa có/dự kiến” bên dưới là trạng thái đặc tả ban đầu, chỉ được thay thế trong phần đã liệt kê.

**Phiên bản:** `m3-design-v1`, 19/10/2026. **Trạng thái:** thiết kế chưa thực thi. Nguồn và hiện trạng tại [README](../README.md); từ điển dữ liệu tại [02](02-data-model.md).

## 1. Chức năng bắt buộc và truy vết

| Chức năng | Kết quả người dùng nhận | Truy vết |
|---|---|---|
| Nhập snapshot order local | Audit, sales dẫn xuất, danh mục, lỗi chặn và hash nguồn. | R01/R02/R09; T03/T04/T12 |
| Dự báo đủ 46 tuyến | Hai tổng tuần và 14 ngày phân bổ; model/selection/coverage rõ. | R04/R05; T08/T09 |
| Cấu hình kho và supplier | Kho/tuyến, supplier/item, ROP floor/MOQ/safety có hiệu lực, phiên bản. | R06/R09; T10 |
| Mô phỏng nhập và tồn | Ledger, thiếu hụt, SS/ROP/S/IP/Q, ETA và giải thích. | R06; T10 |
| Cảnh báo cạn | Ngày cạn trongH14, mức khẩn/sớm, kết quả replay riêng. | R07; T10/T12 |
| Dashboard, xuất tổng hợp | Sáu màn hình cùng run/cutoff; actual/forecast/giả định phân biệt. | R08/R09; T11 |

## 2. Danh mục, kho và nhà cung cấp

Khóa tuyến `(destination_country, carrier)` giữ nguyên nguồn, kể cả `Europe (EU)` là nhóm điểm đến. `warehouses` có một dòng/tuyến, UNIQUE cặp tuyến; `items` có khóa `(warehouse_id, sku, product_type)`. Tồn item không bù qua item/tuyến khác. 920 là catalog toàn snapshot, không giả định cả 920 đã biết ở mọi origin. Chỉ item có `first_seen_date <= origin` tham gia phân bổ; danh mục tương lai không tạo feature ở origin cũ.

Seed kho lấy tuyến xuất hiện trong train, sắp thứ tự tên tuyến và cấp `WH-001`…`WH-046`, có `is_assumed=true`. Các tuyến cùng điểm đến dùng thành phố minh họa sau, giữ kho riêng. Không có khoảng cách hay hàm mục tiêu để nhận là tối ưu.

| Điểm đến | Thành phố giả định | Điểm đến | Thành phố giả định |
|---|---|---|---|
| Australia | Sydney | Cambodia | Phnom Penh |
| China | Shanghai | Europe (EU) | Frankfurt |
| Hong Kong | Hong Kong | India | Mumbai |
| Indonesia | Jakarta | Japan | Tokyo |
| Laos | Vientiane | Malaysia | Kuala Lumpur |
| Philippines | Manila | Singapore | Singapore |
| South Korea | Seoul | Taiwan | Taipei |
| Thailand | Bangkok | UAE | Dubai |
| USA | Los Angeles | Vietnam | Ho Chi Minh City |

Tạo supplier mô phỏng `SUP-001`…`SUP-046`, mỗi tuyến một supplier ban đầu; không coi tên carrier là bằng chứng supplier thật. Cấu hình cho phép đổi supplier từng item qua policy mới; không chọn nhiều nguồn cho cùng item tại một ngày. Một supplier có thể phục vụ nhiều item/kho.

## 3. Target, mô hình và thời gian

Target giữ A08: tổng quantity dòng `success` theo `order_datetime` UTC; không dùng activation lọc sales. Train01/01/2024–30/06/2025; validation01/07–30/09/2025; test01/10–31/12/2025. Top10 theo quantity train, giữ selection final. Snapshot trạng thái không chứng minh thông tin đã sẵn có khi vận hành thật.

| Nhóm | Nguồn forecast | Chính sách |
|---|---|---|
| Top10 | Import final cùng source hash/protocol; thiếu origin thì replay10 lựa chọn cố định qua adapter. | Giữ pool top10/override LG U+, không fit top10 bằng pool46 hoặc đổi lựa chọn. |
| 36 tuyến khác | 5 LightGBM trong `M2/models/LightGBM/variants.json` và Prophet `prophet_annual3_weekly_w540`. | LightGBM mới học pooled46; Prophet riêng tuyến. Không nhân biến thể LG U+ sang tuyến mới. |

Reuse `m2-reproduce.json`: minimum history90, rolling train365, refit7 origin, LightGBM150 cây/learning rate0,03/min child100/reg_lambda10; override có trong spec giữ nguyên. Prophet cửa sổ540 theo spec. Seed42. Không thêm tuning hoặc đổi target theo metric.

Tại mỗi cutoff fit, mọi nhãn tuần kết thúc không sau cutoff; teacher/head LG U+ cũng causal. Refit neo origin đầu mỗi split; origin giữa refit dùng model hiện có với lịch sử đến origin theo adapter. H14 xuất hai tổng **D+1…D+7** và **D+8…D+14**, không phải tổng tích lũy14.

Chọn từng tuyến mới bằng validation: ứng viên coverage100% trên cùng tập cửa sổ đủ nhãn; MAPE tuần dương → MAE → model ID tăng dần. Không có tuần dương thì MAPE=null, chọn MAE → model ID. Ứng viên lỗi/thiếu không thắng nhờ bỏ dòng; không còn ứng viên hợp lệ thì run failed. Lưu selection hash trước test. Test vẫn là hồi cứu vì lịch sử đã sử dụng, không gọi holdout độc lập. Báo h1–7/h8–14 riêng.

## 4. Phân bổ dự báo

1. Mỗi tuyến/origin: tính tổng sales từng weekday trên 90 ngày kết thúc origin, chuẩn hóa bảy tổng thành trọng số; chia mỗi khối tuần theo weekday tương ứng. Tổng lịch sử90 ngày bằng0 thì chia đều1/7, ghi `allocation_basis=uniform_zero_history`.
2. Tính share `(sku, product_type)` từ quantity30 ngày kết thúc origin, đủ ngày0; tổng tuyến0 thì dùng90 ngày. Item đã biết không bán trong cửa sổ có share0.
3. Cả30/90 đều0 → `missing_allocation_basis`; không gán forecast item0 hoặc đổi tuyến. Run phân bổ không complete, không tạo khuyến nghị cần vector thiếu. Không đồng nhất với fallback weekday bước1.
4. Nhân forecast ngày với share. Không làm tròn float; tổng item/ngày và tổng ngày/khối phải khớp forecast tuyến trong `1e-8`. Không dùng sales sau origin cho item mới.

Metric ngày phân bổ mang nhãn `allocated_daily`, không lấy kết quả tổng7 thay R05 ngày. Actual sau 31/12/2025 chưa có phải null; không lấy activation tháng01 hoặc forecast làm actual.

## 5. Chính sách và tồn đầu

Policy gồm supplier, item, version, khoảng `[effective_from, effective_to)`, `configured_rop_floor` nguyên≥0, MOQ nguyên≥1, safety_days≥0 và nhãn giả định. Lead time **7**/review **1** là hằng profile M3; FE không cho sửa tự do. Thiếu item policy không dùng ngưỡng chung/0.

Run đóng băng chuỗi policy cần cho kỳ mô phỏng, chọn theo ngày quyết định. Khoảng hiệu lực không chồng lấn trên item dù khác supplier. Không sửa giá trị policy đã được run tham chiếu. Đổi tương lai đóng khoảng cũ, thêm version mới trong một transaction; snapshot cũ trong run không đổi. Không coi khoảng hiệu lực giả định là lịch sử hợp đồng thật.

Seed demo là thủ tục tạo giả định, không phải fallback runtime: tại cutoff khởi tạo lấy μ28/item từ 28 ngày lịch quan sát. Supplier số lẻ: floor=`ceil(6×μ28)`, safety_days2; số chẵn: floor=`ceil(8×μ28)`, safety_days3. MOQ minh họa eSIM5, physical_SIM10. Ghi policy riêng mỗi item với nguồn `synthetic_seed_v1`; không tune số để làm đẹp kết quả. FE cho sửa từng bản. Ví dụ mục7 dùng số giả độc lập.

Tồn đầu=`ceil(cover_days×μ28)`, cơ sở cover7, độ nhạy3/7/14. Tính tại origin khởi tạo, không dùng actual trong đợt đánh giá. Đủ nguồn nhưng không bán → μ28=0 hợp lệ; thiếu nguồn ngày → chặn. Receipts đầu kỳ khai báo rỗng hoặc danh sách cụ thể. Tồn/nhập/ledger đều `is_simulated=true`.

## 6. Chu kỳ tồn và nhập

Với f[h] là forecast item h=1…14, b là safety_days của policy ngàyD:

```text
L = 7; R = 1; H = 14
SS = ceil(b × mean(f[1..14]))
ROP_forecast = ceil(sum(f[1..7]) + SS)
ROP = max(ROP_forecast, configured_rop_floor)
S = ROP + ceil(f[8])
IP = closing_on_hand + ordered_not_received
trigger = closing_on_hand < ROP
Q_raw = max(0, S - IP) if trigger else 0
Q = max(ceil(Q_raw), MOQ) if Q_raw > 0 else 0
```

`ordered_not_received` chỉ gồm lô đang mở của cùng run/nhánh kịch bản và item; không gồm Q vừa khuyến nghị. IP tính lượng đặt; trigger chỉ dùng tồn cuối. Thiếu vector14 phải chặn, không nối actual tương lai vào forecast.

Mỗi ngày UTC: tồn đầu → nhận ETA đầu ngày → bán theo timestamp, hòa theo khóa nguồn nội bộ → fulfilled=min(quantity,tồn), shortage=quantity−fulfilled → tồn cuối → forecast/chính sách sau chốt → tạo lô Q dương. ID nguồn chỉ phục vụ audit/sắp thứ tự nội bộ; lưu `source_sequence` sau audit trong event, không xuất ID nguồn. Không backorder hoặc tự hoàn nhập refunded.

Đặt cuốiD nhận đầuD+7 gồm cuối tuần; đặt31/10/2025 → ETA07/11/2025. Nhận một lần đúng ordered_qty trong cơ sở. Chưa mô phỏng nhận trễ/ít/không về ởv1 vì lead time cố định; kịch bản cũ là lịch sử riêng. Tồn giảm lúc nhận yêu cầu bán, không trừ lần hai theo lịch giao kháchD+7.

Q=0 khi pending đủ vẫn có thể tồn dướiROP; hiển thị “dưới ngưỡng, đã có hàng đang về”. Giữ `closing=opening+receipts−fulfilled`, `sales=fulfilled+shortage`, tồn không âm; không thay sales lịch sử bằng fulfilled.

## 7. Ví dụ giả tính tay

f[h]=10, b=2 → SS20, ROP_forecast90. Với floor100/MOQ50: ROP100/S110. Tồn80/pending0 → Q_raw30/Q50; tồn100 → không trigger/Q0; tồn80/pending40 → IP120/Q0. Supplier khác floor150/MOQ100 cùng forecast/tồn80 → S160/Q100. Các số chỉ minh họa, không gán mentor cung cấp.

## 8. Cảnh báo, replay và metric

Tách `below_rop` từ tồn cuối và `depletion` từ chiếu14 ngày bằng forecast/receipts đã biết ở origin. Projection không thêm đơn nhập do chính cảnh báo đó. Mỗi ngày nhận receipts đầu ngày rồi trừ forecast, clip tồn0; ngày đầu chạm0 là ngày cạn dự kiến. Origin tồn0 → `already_depleted`, không tính sớm. D+1…D+6 khẩn/muộn; D+7…D+14 sớm; không cạn trongH → `not_within_horizon`, ngày cạn null.

**Alert replay:** origin30/09/2025 rồi cách14 ngày, chỉ đợt đủ 14 ngày nhãn đến 31/12; tồn đầu dựng từ quá khứ từng đợt; không đặt mới, chỉ nhận receipts khai báo trước origin. Một sự kiện cạn đầu tiên/item/đợt; key không chứa ngày dự đoán để tránh nhân đôi. TP/FP/FN theo có/không sự kiện trong cùng cửa sổ, ghép cặp đó tính sai số ngày cạn. Early rate = số sự kiện thực mô phỏng được báo tại origin trước ngày cạn≥7 / tổng sự kiện thực mô phỏng; ca tồn0 tại origin báo riêng ngoài mẫu số sự kiện tương lai. FN gồm không cảnh báo nhưng có sự kiện. Không có mẫu số → null; công khai ca thiếu/bị loại.

**Policy replay:** liên tục01/10–31/12/2025, khởi tạo30/09, cho đặt mới/ETA7. Forecast đủ 14 ở tail dù actual tail chưa đủ chấm. Báo fill rate, shortage, tồn cuối bình quân, số lô/lượng nhập. Không coi cảnh báo ngăn được cạn là false positive.

Sales metric error=forecast−actual; MAPE chỉ actual>0, MAE/bias mọi cặp có nhãn, WAPE chia tổng actual; toàn actual0 → MAPE/WAPE null. Coverage=cặp forecast hợp lệ/cặp dự kiến có nhãn. Tách ngày/tổng tuần, h1–7/h8–14, rolling/nonoverlap. R07 chưa có ngưỡng precision/recall chính thức, không hứa mọi ca đều báo trước 7 ngày.

## 9. Hiển thị và thay đổi

Chỉ complete khi đủ thành phần và đối soát đạt; lỗi giữ failed cùng mã lỗi không chứa dòng nguồn. FE không ghép forecast mới với tồn cũ. Thay b/floor/MOQ/city/supplier tạo version/run mới; forecast độc lập được tái dùng, ledger/cảnh báo tính lại. Thay target/source tính lại mọi đầu ra phụ thuộc. Mọi thao tác nhập là mô phỏng, không gửi nhà cung cấp.
