# M3 — Đặc tả vòng đời mua bán SIM/eSIM (CHG-085)

<a id="phase8-validated"></a>
### CHG-085 giai đoạn 8 — 03/11/2026, kiểm run lịch sử và các kịch bản mới

**CHG-085 giai đoạn 8 — 03/11/2026, hoàn tất local:** đã đọc và verify 7 run cũ, đối chiếu API/CSV cho 12 cặp DB–run; chạy 4 run mới trên bản sao dùng nguồn/forecast có sẵn và 1 run synthetic cho hai kho. Worker, verifier độc lập, API/CSV và browser 1440/390px đạt. Ca bổ sung chặn 19 đơn vị nguồn trong mô phỏng; ca synthetic có 280 = 150 được phép bán + 130 bị chặn. Sửa nhãn quyền mua/bán trong bảng projection; 89 React và build đạt. App ở 0008 với 3 run ban đầu; 4 DB bảo vệ và 1.412 tệp giữ hash. Không refit/tuning hoặc viết lại bằng chứng CHG-084; R07/T14 giữ mở. Thay đổi giai đoạn 7–8 chưa commit/push. [Bằng chứng/giới hạn](../../docs/development.md#handoff-chg085-phase8). Run cũ chỉ đọc/verify theo snapshot/profile gốc, không chạy lại worker để sửa chúng. Các runtrade_v2 mới giữ hai lịch sử/known cutoff, source=allowed+blocked, nhận lô cũ và giữ blocked stock; cùng API/CSV/UI frozen. Lịch sử/config live sửa sau enqueue không làm đổi run đã lưu. Các câu “chưa triển khai/chưa chạy8” phía dưới là checkpoint lịch sử; R07/T14 không tự đóng.


<a id="phase7-implemented"></a>
### CHG-085 giai đoạn 7 — 03/11/2026, đã cutover ứng dụng local

**CHG-085 giai đoạn 7 — 03/11/2026, hoàn tất tích hợp/cutover local:** backup 31.536.707 byte đã restore trên DB rehearsal riêng; nâng/hạ/nâng với lịch sử cũ không rỗng và từ chối downgrade khi có stop cùng ngày đạt. DBapp đã nâng `0008_trade_lifecycle`, giữ hash toàn bộ cột cũ của 14 bảng nghiệp vụ/3 run; 1.053 tệp và hai DB bản sao CHG-084 giữ nguyên. 478 Python BE/M2, 88 React, build/pipcheck, API/CSV 920 và browser 1440/390px đạt. API/worker cùng bản mã 99395aa và FE build mới chạy cổng 8000; thử ghi chỉ trên DBtest/bản rehearsal, worker chỉ synthetic DBtest, không tạo run nguồn thật hoặc khai báo stop/notice trên app. Giai đoạn 8 chưa được giao, R07/T14 giữ mở. [Bàn giao/rollback/kiểm](../../docs/development.md#handoff-chg085-phase7). Đây là trạng thái hiện hành; các checkpoint “app0007/chưa cutover” bên dưới giữ làm lịch sử. Profile cũ không tự nâng, cấu hình mới không sửa frozen; app0008 mở capability cho thao tác và tạo inventorytrade_v2 mới khi người dùng yêu cầu. Chưa có runtrade_v2 hoặc thông báo/stop thật trên app trong lần cutover này.


<a id="status"></a>
## 1. Thiết kế mới và phần đang chạy

<a id="phase6-implemented"></a>
### CHG-085 giai đoạn 6 — 02/11/2026, FE đã triển khai trên DBtest

**CHG-085 giai đoạn 6 — 02/11/2026, hoàn tất local FE:** modal ngừng nhập nội bộ cùng ngày, trang thông báo nhà mạng/phạm vi nhiều kho, preview và hai quyền riêng; vận hành hiển thị lượng bán/tồn bị chặn/Q/cap từ frozen. Baseline74, suite cuối88React (gồm22ca liên quan), 37ca hợp đồng BE, build/pipcheck và browser1440/390px synthetic đạt. DBapp vẫn0007; không cutover/nguồn thật/bước8 cũ. Bước4–6cònlocal, chưa commit/push; dừng trước7, R07/T14 giữ mở. [Lệnh/giới hạn/bảo toàn](../../docs/development.md#handoff-chg085-phase6), [đặc tả FE](04-frontend-spec.md#lifecycle-chg085). Các checkpoint3–5bên dưới giữ lịch sử; FE6chỉ bật hành vi mới khi API báo schema hỗ trợ.

| Luồng | Hành vi thực có |
|---|---|
| Nội bộ | ProductDetail summary → modal một action stop/cancel_stop/resume; ngày cùng ngày/min0, target/version/history, preview và xác nhận lưu. Nhà mạng còn chặn thì vẫn nêu riêng. |
| Nhà mạng | #provider-notices → #provider-notice-new / #provider-notice:ID; nhiều SKU/type/thị trường/kho khai báo rõ, nguồn giả định bắt buộc/URL tùy chọn, full scope totals và sample page. Cancel và resume_supply riêng, lịch sử append. |
| Lỗi/lưu | Preview hết hạn khi sửa; không tự retry POST. 409giữ reason/source,422focus, save-confirmed/refetch-failed chỉ GET retry; Back/modal/focus/dirty confirmation và schema0007 khóa ghi. |
| Vận hành | Hai quyền/trạng thái; tổng tồn/được bán/bị chặn, Q_policy/Q_final/cap, lô cũ cần xử lý, no CTA trái quyền. Filter/CSV dùng stored result cùng scope, thiếu diagnostic không giả0. |
| Dự báo/metric | Bán theo ràng buộc và blocked/stock shortage riêng, input model trong details; metric toàn run có phạm vi/exclusions và source/scenario/blocked. Raw score giữ raw source sales, không đổi R05/M05. |
| Tạo inventory run | Tự gửi trade marker khi catalog trade_schema_ready=true; không có lựa chọn profile kỹ thuật, không gửi vào source/forecast. App0007 vẫn reader/profile tương thích và không mở ghi mới. |

Không tính Q/projection/forecast tại FE hoặc trong preview mới. Cấu hình hiện tại có thể khác frozen; lưu không tự enqueue, thay snapshot hay viết lại CSV cũ. Bố cục kiểm1440/390px dùng form một cột ởmobile, table có vùng cuộn ngang và bảng thay thế đồ thị. 88React/22ca liên quan, 37ca BE hợp đồng, build/pipcheck và browser synthetic đạt; đây không phải cutover7 hoặc kiểm run thật8.


<a id="phase5-implemented"></a>
### CHG-085 giai đoạn 5 — 02/11/2026, read model/API/CSV đã triển khai trên DBtest

**CHG-085 giai đoạn 5 — 02/11/2026, hoàn tất local:** đã mở API kết quả/CSV trade_v2 từ ledger, projection và snapshot frozen; lọc hai quyền/trạng thái trước count/page/aggregate, counters riêng và metric có scope/exclusions. Baseline11/targeted62/suite478 Python BE/M2 và pip check đạt. DB ứng dụng vẫn 0007, hai bản sao/bằng chứng cũ giữ nguyên; không FE/cutover/nguồn thật. Chưa commit/push bước 4–5; dừng trước 6. R07/T14 giữ mở. [Lệnh kiểm và bảo toàn](../../docs/development.md#handoff-chg085-phase5). Các guard/checkpoint3–4phía dưới giữ đúng lịch sử, guard result đã được mở trong5.

[reporting/trade.py](../../web/backend/src/modules/reporting/trade.py) và [service](../../web/backend/src/modules/reporting/service.py) dispatch profile; API/CSV/workspace/purchasing dùng cùng dataset. Số lượng lấy ledger/projection/diagnostic đã lưu, chỉ metadata quyền giải từ snapshot, không gọi live resolver hoặc tính lại forecast/ROP/SS/Q/path. Profile lạ/rules hoặc marker thiếu trả409invalid_trade_history; legacy yêu cầu quyền mới409feature_not_in_run, filter sai422.

| Dataset | Date/origin và lượng thực có |
|---|---|
| inventory | as_of_date lọc ngày ledger của trade_v2; window_origin chọn window; total_qty=closing_qty, sellable_qty/blocked_qty theo quyền frozen; source_sales_qty/scenario_sales_qty/actual_blocked_qty. |
| alerts | as_of_date là ngày quyết định lưu; quyền/stock/Q diagnostic và exclusion của chính origin, không nối cấu hình mới. |
| replenishments/purchasing | as_of_date là ngày xem, chỉ đơn đã biết; không lộ trạng thái nhận lô tương lai. Quyền tại ngày xem/ETA và needs_supplier_action; lượng tồn tác động thiếu thì stock_impact_availablefalse, không giả0 hoặc nhận đã tính FIFO. |
| sell-through | as_of_date là projection origin (mặc định run origin), date_from/to lọc target date; đọc nguyên14hàng projection lưu, không tính lại. window_origin phân biệt cửa sổ replay. |
| metrics | Mặc định summary stored. Alert as_of/date_from/to chọn whole origin-window; policy chọn ngày ledger. Scope rỗng trả[]; fill_allowed null khi allowed0. Metric allocated_daily vẫn raw_source_sales. |

Filters mới: sku chính xác (1–200 ký tự), destination_country/carrier chính xác (1–100), window_origin date; internal_status active/scheduled_stop/stopped; provider_status clear/scheduled_stop/stopped/scheduled_resume; replenishment_allowed/sales_allowed boolean. Các nhóm AND trước count/page/aggregate/export; blockers trong item OR. Không dùng filter quyền trên raw forecast/allocated metric; raw metric không hỗ trợ scope item/type/supplier/date phải422 thay vì âm thầm bỏ filter.

Inventory/alerts trả q_policy/q_final/cap_reason/sellable_budget/provider_stop_on/cap_eta/forecast_coverage_complete và quantity_diagnostics_available; cap_eta riêng để không ghi đè ETA thật của lô. Q_final inventory luôn lấy recommended_qty đã lưu. Khi alert ledger ngoài origin không có diagnostic, Q_policy/cap đểnull/availabilityfalse, không suy diễn. supply_status alias nội bộ; provider_notice_ids/provider_reasons/provider_sources giữ ID/source giả định frozen. Context có config/source hash/profile/units/metric_basis/run_as_of_date/run_status; legacy không thêm số blocked=0 giả.

Workspace/purchasing chọn newest window từng item trước rights filter. Counters internal_stopped_items/provider_blocked_items/blocked_stock_items/purchase_limited_items/needs_supplier_action_items riêng, affected_items distinct; stock trống lànull. Không tính stopped/capped thành healthy vì Q0. Aggregate sell-through route/day giữ window/origin, tổng input/projected_sales/blocked/unserved/stock và rights/status counts, union notice IDs/reasons/sources, không ép tổng constrained sales bằng route forecast.

Metric scoped chỉ aggregate từ case/ledger đã lưu; threshold crossing actual lấy closing ledger dưới ROP origin trong N đã lưu, không project lại. Whole-window exclusions từ summary luôn đi cùng mẫu số và nguồn/allowed/blocked. CSV dùng cùng filter/dataset, xuất mọi trang (đã kiểm5040hàng qua batch5000), có JSON nested/escape công thức. Preview chỉ bổ sung lượng trade frozen khi đủ dữ liệu; Q của cấu hình đề xuất mới vẫn không tự tính. Không đổi reader/profile/persisted JSON/CSV lịch sử.


<a id="phase4-implemented"></a>
### CHG-085 giai đoạn 4 — 02/11/2026, worker/projection/verifier đã triển khai trên DBtest

**CHG-085 giai đoạn 4 — 02/11/2026, hoàn tất local:** worker/projection và verifier độc lập đã thực thi trade_v2; 40 ca trade mới, 152 ca targeted và toàn suite 459 Python BE/M2 đạt, pip check đạt. Tồn tổng được giữ, sale bị chặn ghi riêng, Q áp cap nguyên lô/ETA/coverage và metric loại cả item-window bị chặn. DB ứng dụng/bản sao cũ chỉ đọc, không cutover hoặc chạy nguồn thật. Bước 5–8 chưa làm; chưa commit/push bước 4 trong lượt này. R07/T14 giữ mở. [Bàn giao và lệnh kiểm](../../docs/development.md#handoff-chg085-phase4). Các checkpoint giai đoạn 1–3 phía dưới giữ nguyên bối cảnh thời điểm đó.

[inventory/trade.py](../../web/backend/src/modules/inventory/trade.py) tính quyền frozen, projection và cap; [simulation.py](../../web/backend/src/modules/inventory/simulation.py) ghi ledger/events/orders/alerts/summary. Nhận lô trước sale, provider block giữ total và ghi sale_blocked, nội bộ chỉ chặn Q. Projection chứa forecast_input_qty/forecast_demand_qty alias, projected_sales_qty/sales_blocked_qty/unserved_stock_qty, unserved_demand_qty=blocked+stock-shortage, available_total/sellable_qty/blocked_stock_before_sale/closing_total/closing_sellable/closing_blocked cùng trạng thái/blockers.

Explanation tại origin có q_policy/q_final/cap_reason/sellable_budget/provider_stop_on/eta/forecast_coverage_complete, hai quyền/lý do, stock_below_rop/actionable và needs_supplier_action cho pending bị chặn tại ETA. Lý do cap: internal_stopped, provider_blocked, eta_at_or_after_provider_stop, insufficient_forecast_coverage, fixed_lot_exceeds_sellable_budget. Giữ nguyên ROP/SS/S/IP; cap không sửa lô cố định hoặc thêm Q vào đường nền. B floor tổng unserved_stock từ ETA tới T−1; thiếu coverage chặn. Alert fixed-origin chỉ dùng phần vector còn lại tới origin+14 trong các quyết định ledger, không lặp forecast ra ngoài coverage.

Producer profile mới ghi hai cột source_sales_qty/actual_blocked_qty ở mọi hàng (gồm 0 khi không block); sales_qty là scenario sales. Summary công khai source/scenario/blocked, fill_allowed, blocked_source_rate, metric_basis=allowed_scenario_sales và exclusions theo whole item-window với dates/notice IDs/reasons. Denominator 0 trả null. Alert/depletion/threshold vẫn lưu chẩn đoán scenario cho window bị loại, is_evaluable=false/evaluation_class=null/exclusion_reason=provider_sales_blocked.

[trade_verification.py](../../web/backend/src/modules/runs/trade_verification.py) tự kiểm snapshot/scope/identity/rules và tính quyền/path/cap, không import resolver/project/recommend/producer. [verification.py](../../web/backend/src/modules/runs/verification.py) đối chiếu balance/nguồn/bán bị chặn, receipt đúng ETA một lần, Q và đơn phát sinh, coverage ngày/item/window, projection/diagnostic/totals/metric/exclusions và parent checksum. Validator cấu trúc cũng được worker gọi trước tính; arithmetic vẫn độc lập. Gỡ stage_not_implemented cho trade_v2, giữ lỗi profile lạ và snapshot lỗi; result/CSV vẫn guard 409 tới bước 5, API preview chưa nối Q-cap từ stored result. Không sửa run/profile/JSON cũ hoặc nối live vào kết quả frozen.


<a id="phase3-implemented"></a>
### CHG-085 giai đoạn3 — 02/11/2026, API/snapshot/tương thích đã triển khai trên DBtest

Người dùng giao tiếp3 và sau đó giao hoàn tất thì đẩy GitHub. Đã thêm [provider_schemas](../../web/backend/src/modules/catalog/provider_schemas.py), [provider_router](../../web/backend/src/modules/catalog/provider_router.py), [provider_read](../../web/backend/src/modules/catalog/provider_read.py), [trade_preview](../../web/backend/src/modules/catalog/trade_preview.py) và [trade_service](../../web/backend/src/modules/catalog/trade_service.py); dùng domain/persistence/model0008của2. Baseline65/targeted83/full419Python BE/M2 vàpipcheck đạt. Chỉ DBtest/synthetic; DBapp/bản sao không nâng/ghi, không tiếp tục bước8 cũ. [Bàn giao](../../docs/development.md#handoff-chg085-phase3). Publish thường final-report gồm code2cònlocal làm phụ thuộc, kiểm SHAremote/CI rồi dừng trước4.

**API thực có:** GET/POST provider-product-notices; GET /{id}, /{id}/events, /{id}/items; POST /preview, /{id}/cancel, /{id}/resume; POST products/{id}/internal-stop-preview; products list/detail thêm internal_status/provider_status/replenishment_allowed/sales_allowed/notice IDs/versions/reasons/trade_schema_ready. supply_status/supply_version giữ alias nội bộ/latest như cũ. Lọc các nhóm bằng AND trước total/page; notice được tính một lần dù nhiều member. Các read mới dùng batch dữ liệu trước phân trang, chưa có chỉ mục trạng thái tổng hợp hoặc bảng cache riêng; quy mô920item hiện tại dùng hàm thuần, chưa đẩy status predicate provider vào SQL.

Preview provider nhận DTO phân biệt action=stop (supplier_id/scope_definition) hoặc cancel_stop/resume_supply (notice_id/target_event_id). Các trường chung: known_on/effective_on/reason/source_description/source_ref tùy chọn/expected_version; impact_run_id/impact_as_of_date tùy chọn. List dùng page≥1/page_size1–100, supplier_id/item_id/warehouse_id/sku/product_type/destination_country/status/as_of_date/search; filter sai hoặc extra trả422, status thiếu ngày422. Detail có latest_action/latest_known_on/latest_version riêng state theo ngày, để phân biệt hủy và phục hồi dù quyền cùng clear; lịch sử giảm version ở /events.

POSTcreate dùng các trường stop và preview_fingerprint64hex bắt buộc. POSTcancel/resume có path xác định hành động, body chỉ trường chung+target_event_id+fingerprint, không lặp notice_id/action. Server khóa Supplier→Notice(nếu có)→Item→Warehouse rồi tính lại payload chuẩn hóa/membership/catalog identity-version/lịch sử hai nguồn/run-hash/ngày tác động; FP khác trả409preview_stale, version khác409version_conflict; sai trạng thái409, payload/source/scope/ngày cấu trúc sai422, ID thiếu404, schema thiếu503. Root/members/event lưu cùng transaction; retry create với FP cũ bị409, không tạo notice trùng. Scope và tổng preview tính toàn bộ trước page; FP không phụ thuộc trang đang xem.

Nội bộ cùng ngày/short notice hoặc có impact context cần preview_fingerprint; preview và save dùng min0, vẫn bán tồn được phép, mở lại nội bộ không gỡ provider. Đường+7/hủy/mở lại cũ không fingerprint tiếp tục tương thích cho client cũ (min7 ở service mặc định). Payload không được truyền min_notice/profile để vượt quyền. Schema0007 vẫn đọc catalog/trạng thái nội bộ/stock/API/CSV cũ; quyền provider không biết trảnull/trade_schema_readyfalse, yêu cầu tính năng mới trả503. Không auto-migrate.

**Tác động preview:** chỉ đọc inventory/lô đã lưu của impact_run_id complete tại ngày được chọn, chọn một window mới nhất/item, chỉ đơn đã biết và ETA theo known_orders_through. Tổng tồn/pending/số lô chỉ có số khi phạm vi/ngày đủ; thiếu thì null và inventory_completefalse. Không có impact run vẫn cho preview/lưu cấu hình hợp lệ nhưng số lượng null. Legacy chưa có tồn được bán/bị chặn giữ null/rights_quantities_availablefalse, không tính từ live để sửa run. Quyền trước/sau là giả định cấu hình tại rights_on=max(known_on,effective_on), tách rõ ngày số tồn frozen. recommended_qty_after chỉ0 khi quyền nhập bị chặn, còn lại null; quantity_limit_status chưa tính cap v2 ở3. Không chạy model/worker ngầm hoặc nhận đã tính lượng bán/Q trước hạn mới.

**Snapshot chuyển tiếp:** request inventory có thể bổ sung trường kỹ thuật sau, không phải bộ chọn nghiệp vụ trên FE:

```json
{"trade_lifecycle_profile":"internal_provider_trade_v2"}
```

Khi có marker: freeze internal_supply_snapshot, provider_notice_snapshot(root/scope/item_ids/item_snapshot/events prefix) và trade_rules; không kèm supply_lifecycle_profile notice7. Scope lưu cả member ở ngoài catalog của run với identity frozen để kiểm phạm vi, nhưng không kéo demand/forecast của item ngoài catalog vào run hoặc phân phối lại. Khoá chia sẻ Supplier→Item→Warehouse giữ các writer cấu hình liên quan trước khi đọc policies/hai lịch sử; provider writer bị khóa tại Supplier, internal/policy writer tại Item. Chỉ hàng đã commit ở ranh giới freeze và known_on≤origin lớn nhất; mỗi origin cụ thể do consumer4sẽ lọc prefix. created_at là thời điểm thao tác kỹ thuật, không dùng ngày hệ thống hoặc Run.created_at thay known_on. Retry key trả snapshot cũ trước đọc live.

Trong staging3, request không marker vẫn freeze notice7 **chỉ khi** scope/cutoff không có provider history và không có stop nội bộ<7ngày đã biết; ngược lại409trade_profile_required. Vì vậy không thể bỏ marker để lờ hạn chế mới. Việc chọn mặc định/đưa marker tự động cho UI khi mở tính năng thuộc6–7, không thêm lựa chọn profile vào form nghiệp vụ. Các profile/JSON/hash/artifact cũ không backfill hoặc nối cấu hình live.

simulate_run và verifier gặp trade_v2 trả stage_not_implemented; profile mới lạ trả invalid_trade_history. Reader result gặp trade_v2 trả409feature_not_in_run, không giả legacy/null profile thành allowed=true. Ca worker synthetic kiểm run fail đúng guard/0ledger; **chưa có run trade_v2 được verified**, chưa triển khai phép tính4 hoặc result/CSV5/FE6. Các đoạn chưa API/snapshot ở checkpoint2phía dưới là lịch sử.

<a id="phase2-implemented"></a>
### CHG-085 giai đoạn2 — 02/11/2026, đã có DB/nghiệp vụ trên DBtest

Người dùng giao riêng2 sau khi bước1 đã push92243b8/SHAremote/2CI success. Mã hiện có migration [0008_trade_lifecycle](../../web/backend/migrations/versions/0008_trade_lifecycle.py),3model provider trong catalog/models,2cột ledger nullable trong inventory/models, [provider.py](../../web/backend/src/modules/catalog/provider.py) thuần và [provider_service.py](../../web/backend/src/modules/catalog/provider_service.py) persistence. Chỉ migrate/ghi fixture sigma_m3_test; DBapp và hai bản sao bước8 không nâng/ghi. [Kiểm và giới hạn](../../docs/development.md#handoff-chg085-phase2). Chưa được giao commit/push code giai đoạn2.

Đã kiểm kê trực tiếp read-only: app0007/14bảng/3run/0stop; validation0007/14bảng/4run/1stop; history0005_carrier/13bảng/5run. Điều này thay giới hạn chưa kết nối được ở giai đoạn1, không xóa bằng chứng cũ. 0007 không sửa; mã schema hiện17bảng, app vẫn14. Migration0008 thêm3bảng và2cột không default/backfill, nới CHECK action/ngày nội bộ và event_kind. Source/blocked CHECK giữ cân bằng và yêu cầu cả hai cột cùng null (legacy) hoặc cùng không âm/source=sales_qty+blocked. Downgrade giữ bảng khóa trong kiểm, từ chối notice, stop<known+7, ledger mới, sale_blocked hoặc run có trade_lifecycle_profile.

Ngừng nhập cùng ngày đã có ở validate_supply_change(..., minimum_notice_days=0); default7 cố ý giữ cho DTO/service API cũ và notice7 profile. Chưa nối min0 vào API hoặc freeze v2, tránh dữ liệu chưa được worker/verifier hỗ trợ. Hàm provider_notice_state lọc known_on tại origin rồi giải interval target, resume tương lai không gỡ chặn sớm; trade_state hợp hai quyền và giữ blocker/reason độc lập. resolve_provider_scope kiểm mọi kho/thị trường đã khai báo, carrier/SKU/loại chính xác và dedup membership. Lịch sử/nguồn nhập được validate trước persist; không có update/delete service.

Scope JSON cụ thể được service lưu bất biến theo dạng sau (ví dụ synthetic, không phải scope đã ghi DBapp):

```json
{"products":[{"sku":"PLAN","product_type":"eSIM","destination_countries":["A","B"],"warehouse_ids":[1,2]}]}
```

Mỗi tổ hợp bắt buộc đủ4trường; không nhận extra hoặc cờ all-carrier. Mọi kho phải có đúng sản phẩm/nhà mạng và tập thị trường khớp các kho được chọn; một thông báo có thể nhiều tổ hợp. Persistence create_provider_notice khóa Supplier rồi Item tăng dần, so expected_version=0 và expected_item_ids nếu caller cung cấp để bắt membership đổi; root/membership/event1 trong cùng transaction caller. append_provider_notice_event khóa Supplier→Notice→Item, so latest expected_version rồi append event2 hủy/resume đúng target. Chỉ một follow-up cho một stop; muốn ngừng lần nữa tạo notice mới. Lỗi rollback qua transaction caller, chưa có commit ngầm. Fingerprint/impact preview/HTTP thuộc3, không được coi expected_item_ids là fingerprint hoàn chỉnh.

Để mã ORM mới không làm hỏng đọc trước cutover, reporting/service hiện defer hai cột mới, COUNT chỉ lấy ID và serialization không xuất chúng; đã kiểm API/CSV trên0007 có ledger. Đây chỉ là bảo toàn hợp đồng đọc cũ, không phải read model v2 của5. Không đổi OpenAPI/route/worker/verifier/FE hoặc công thức Q/ROP/SS; ngừng bán/actual/source split hiện chỉ schema và nghiệp vụ thuần, chưa chạy simulation theo v2. Các phần mục tiêu3–8bên dưới vẫn dự kiến. Những đoạn chỉMD/14bảng và API+7phía dưới là checkpoint CHG-084/giai đoạn1, không phủ nhận tiến độ2.

**Checkpoint giai đoạn1, 02/11/2026: khi đó chỉ Markdown, CHG-085 chưa triển khai.** Người dùng giao kiểm rồi publish MD, sau đó đã giao giai đoạn2 được cập nhật ở trên. Lịch sử bước1không sửa code/migration/DB hoặc chạy worker/model/run vẫn giữ đúng phạm vi thời điểm đó. [Lộ trình và hiện trạng bước8 cũ](../../docs/planning/PRODUCT_SUPPLY_LIFECYCLE_PLAN.md#status).

<a id="step2-implemented"></a>
<a id="step3-implemented"></a>
<a id="step4-implemented"></a>
<a id="step5-implemented"></a>
<a id="step6-implemented"></a>
<a id="step7-implemented"></a>
### 1.1. CHG-084 đã có trong mã, giữ nghĩa ngừng nhập nội bộ

Các anchor stepN-implemented được giữ để liên kết lịch sử vẫn tra cứu được; bằng chứng kiểm từng lượt nằm tại [bàn giao gốc](../../docs/development.md#handoff-chg084). Không lấy số test lịch sử làm kiểm hiện tại.

| Tệp/khối thực tế đã đọc | Hành vi hiện tại / khoảng trống |
|---|---|
| [0007](../../web/backend/migrations/versions/0007_product_supply_lifecycle.py), [catalog models](../../web/backend/src/modules/catalog/models.py) | item_supply_changes; stop effective≥known+7; cancel/resume effective=known; unique item/version, FK target cùng item, provenance mô phỏng. Không có thông báo nhà mạng hoặc scope nhiều kho. |
| [supply.py](../../web/backend/src/modules/catalog/supply.py), [service](../../web/backend/src/modules/catalog/supply_service.py), [schemas](../../web/backend/src/modules/catalog/schemas.py) | Resolver prefix known_on≤origin; service khóa Item/expected_version; ngày ghi nhận không lùi. Validator/DTO còn bắt buộc7ngày. |
| [catalog router](../../web/backend/src/modules/catalog/router.py), [configuration context](../../web/backend/src/modules/configuration/context.py) | GET/POST products/{id}/supply-changes, product filter; freeze notice7_sellthrough_v1 và supply_lifecycle_snapshot. |
| [inventory service](../../web/backend/src/modules/inventory/service.py), [simulation](../../web/backend/src/modules/inventory/simulation.py) | Giữ ROP/SS/IP; chặn Q/tạo lô khi nội bộ stopped, nhận lô cũ, replay actual không chặn bán; projection min(forecast,tồn+receipts). Chưa cap ETA/hạn bán. |
| [supply verifier](../../web/backend/src/modules/runs/supply_verification.py), [reporting](../../web/backend/src/modules/reporting/supply.py) | Verifier profile notice7 độc lập; API/CSV đọc frozen/projection. Legacy thiếu sell-through409; chưa có blocked_sales hoặc tồn bị chặn. |
| [ProductSupplyForm](../../web/frontend/src/components/products/ProductSupplyForm.tsx), [Products](../../web/frontend/src/pages/Products.tsx) | Form trên chi tiết, nhãn “cung cấp”, gợi ý/kiểm+7 và action tùy trạng thái. CHG-085 cần tách modal nội bộ và trang thông báo nhà mạng. |

Tại checkpoint giai đoạn1 mã schema có14bảng và kết nối read-only trả OperationalError nên chưa xác nhận live. Giai đoạn2 đã kiểm kê được như phần cập nhật trên; trước cutover7 vẫn phải kiểm lại revision/constraints/sự kiện/provenance/run/profile/hash/catalog nếu có phát sinh. 0007 là migration đã triển khai, không sửa file lịch sử hoặc giả định DB rỗng.

<a id="states-and-time"></a>
## 2. Hai lịch sử, thời gian và quyền

Nội bộ: active → scheduled_stop → stopped; stop mới cho effective_on≥known_on (cùng ngày hợp lệ). cancel_stop chỉ khi known_on<ngày stop; resume chỉ khi stop đã hiệu lực, có hiệu lực bằng known_on. Không sửa policy để đổi trạng thái này. known_on không giảm theo version của cùng item, hủy/mở lại phải target đúng stop; giữ quy tắc một chu kỳ nội bộ đang mở.

Nhà mạng: thông báo stop được biết vào known_on, effective_on có thể trong quá khứ, cùng ngày hoặc tương lai. Trước hiệu lực có thể cancel_stop; đã hiệu lực dùng resume_supply riêng với effective_on≥known_on (ngay hoặc tương lai), không phục hồi hồi tố. Một lần stop có tối đa một cancel hoặc một resume_supply; muốn ngừng lại tạo thông báo mới. Resume có lịch tương lai vẫn chặn đến ngày phục hồi. Không dùng resume nội bộ thay resume_supply; không cho sửa ngày/lý do/phạm vi đã lưu. Sai phạm vi: hủy thông báo chưa hiệu lực rồi tạo mới, hoặc phục hồi rồi khai báo thông báo đúng, giữ audit; sửa dữ liệu lịch sử không thuộc v1.

| Trường | Nghĩa / ràng buộc |
|---|---|
| known_on | Ngày UTC nghiệp vụ hệ thống biết thông tin trong kịch bản, do người dùng khai báo, không suy từ created_at. Nondecreasing theo version mỗi chuỗi. |
| effective_on | Ngày UTC bắt đầu hiệu lực; nội bộ stop không trước known_on; nhà mạng stop có thể trước known_on để ghi nhận muộn. |
| created_at | Timestamp UTC thao tác kỹ thuật thực, server cấp; chỉ sự kiện đã tồn tại lúc freeze mới được vào run. Không thay origin lịch sử bằng đồng hồ thực. |
| decision_origin o / target_date d | Lọc known_on≤o, sau đó xét hiệu lực tại d≥o. Policy replay cuốn o theo ngày; alert replay giữ o của cửa sổ; stock projection giữ as_of_date. |
| version | Latest version kiểm ghi, độc lập ngày xem và version policy; version prefix trong snapshot phục vụ giải trạng thái. |

Đối với một thông báo nhà mạng: chỉ dùng các event visible tại o; interval chặn bắt đầu effective_on của stop, kết thúc effective_on của resume đã visible, hoặc không có interval nếu cancel hợp lệ đã visible. Không dùng cách “thấy resume là xóa stop mọi ngày”, vì resume có thể hiệu lực tương lai. Thông báo biết muộn ngày10 nhưng effective ngày5: quyết định ngày9 không thấy; quyết định ngày10 mới chặn, không viết lại ngày5–9. Cửa sổ alert origin9 tiếp tục không thấy thông báo dù target≥10; đây là kết quả tại thông tin origin9, không phải cấu hình mới nhất.

Tính internal_allowed và danh sách provider_blockers độc lập theo item/o/d. replenishment_allowed=internal_allowed AND provider_blockers rỗng; sales_allowed=provider_blockers rỗng. Trả internal_status, provider_status (clear/scheduled_stop/stopped/scheduled_resume), internal_reason, provider_reasons kèm notice/event IDs và hai quyền; nhiều thông báo active dùng OR để chặn. scheduled_stop tương lai không chặn hôm nay nhưng tham gia cap ETA. Một resume chỉ kết thúc đúng thông báo target; không triệt tiêu thông báo khác hoặc stop nội bộ.

<a id="database"></a>
## 3. DB đề xuất: migration kế tiếp, không viết migration ở giai đoạn1

Ưu tiên tận dụng item_supply_changes và thêm đúng3 bảng cho nghiệp vụ nhà mạng: một thông báo chung, các event lịch sử và quan hệ item. Không bảng trạng thái tổng hợp, không bảng tồn bị chặn riêng hoặc framework sự kiện đa năng.

| Bảng dự kiến | Trường chính và ý nghĩa |
|---|---|
| item_supply_changes (giữ) | Giữ ID/version/action/target/known/effective/reason/created_at/provenance hiện có. Chỉ nới CHECK stop effective≥known; mọi hàng CHG-084 vẫn là nội bộ. Không backfill thành thông báo nhà mạng. |
| provider_product_notices (mới) | id, supplier_id FK suppliers, scope_definition JSON bất biến, created_at. scope_definition chứa SKU/gói, product_type, destination_country/thị trường và warehouse_ids được khai báo; không có cờ chặn toàn carrier mặc định. |
| provider_product_notice_items (mới) | notice_id + item_id làm PK/FK RESTRICT, index item_id/notice_id; tập item đã resolve và preview, bất biến sau lưu. Nhiều kho dùng cùng notice_id. |
| provider_product_notice_events (mới) | id, notice_id, version≥1, action stop/cancel_stop/resume_supply, target_event_id, known_on/effective_on, reason, source_description bắt buộc, source_ref tùy chọn, is_assumed=true, created_at. unique(notice_id,version), FK target cùng notice, CHECK ngày/action/provenance. |

Event version1 bắt buộc stop/target null; event sau target stop cùng notice. Root và membership tạo cùng transaction với event1; không có notice không event hoặc scope rỗng. Không PATCH/DELETE lịch sử, không cascade xóa item/notice đang được tham chiếu. Constraint DB lo unique/FK/ngày/lý do không trắng; service lo trạng thái, scope và version. Nội bộ giữ assumption_source cũ; nhà mạng dùng nguồn mô tả giả định rõ ràng, không bắt URL giả. source_ref nếu là link chỉ cho http/https; FE hiển thị reason/source như text, CSV chống công thức.

Scope: đối chiếu supplier_id với carrier của warehouse, SKU chính xác và loại eSIM/physical_SIM, thị trường/tuyến và kho đã chọn. Cùng SKU khác loại/carrier/thị trường không tự bị ảnh hưởng. Preview phải liệt kê **mọi** item khớp trong phạm vi chọn; không cho loại lẻ một kho khỏi phạm vi thông báo rồi vẫn ghi rằng áp dụng cả thị trường. Nếu thông báo thực chỉ một nhóm kho thì người dùng phải chọn/khai báo nhóm đó rõ ràng. Không tự match toàn carrier. Một thông báo có thể chứa nhiều tổ hợp sản phẩm được khai báo rõ; membership dedup.

Membership freeze theo catalog tại lưu, không tự mở rộng khi thêm item về sau. Trước khi mở item mới trùng scope đang bị chặn, service catalog phải phát hiện và yêu cầu bổ sung một thông báo có scope mới rõ ràng trước khi cho item hoạt động; không âm thầm bỏ hạn chế hoặc sửa scope lịch sử. Chưa xây catalog gói thay thế hoặc batch automation ngoài yêu cầu.

Khóa ghi: nội bộ tiếp tục SELECT Item FOR UPDATE rồi latest supply version. Nhà mạng khóa Supplier trước, notice hiện hữu theo ID tăng, sau đó Item theo ID tăng; tạo notice cũng khóa Supplier để serialize preview/ghi scope cùng carrier. Mọi đường ghi catalog tác động scope tuân cùng thứ tự khi dùng các khóa này. Kiểm expected_version của notice (0 khi tạo), validate target/state/scope, append nguyên tử toàn bộ membership/event; lỗi ở một item rollback cả thông báo. Hai request cùng version chỉ một thành công; retry body cũ409, không nhân đôi. Policy version độc lập. Supplier lock đơn giản phù hợp 46 carrier hiện có, chưa thêm lock service riêng.

Migration dự kiến `0008_trade_lifecycle` nối0007: thay đúng ck_supply_action_dates, thêm3 bảng/index/constraints; thêm2cột nullable source_sales_qty/actual_blocked_qty vào inventory_daily và nới CHECK inventory_events cho sale_blocked theo mục6.2. Tổng dự kiến17 bảng nghiệp vụ nếu hiện trạng khớp14; Alembic tách riêng. Không sửa0007 hoặc tự gán active row cho920item. Có lịch sử nội bộ bất kỳ vẫn giữ hàng/ID/giá trị các cột cũ; khi unknown action/provenance/constraint lệch thì dừng migration, báo dữ liệu không tương thích, không “làm sạch” tự động. Trước/sau rehearsal so hash trên cùng tập cột cũ của13bảng gốc + lịch sử nội bộ, cùng hash run/snapshot/artifact; full-row JSON hash inventory_daily sẽ có thêm khóa null do schema mới nên không lấy nó làm bằng chứng sửa giá trị cũ. Kiểm restore có sự kiện chứ không chỉ DB rỗng.

Downgrade0008: từ chối nếu có notice, stop nội bộ không thỏa CHECK+7 cũ, run profile mới, source_sales_qty/actual_blocked_qty đã được ghi hoặc event sale_blocked; không xóa hàng/cột có dữ liệu để ép downgrade. Khi đã có run profile mới, bản ứng dụng rollback phải vẫn đọc/verify được profile đó; nếu không thì phục hồi backup trước cutover trong môi trường riêng và lập phương án bảo toàn phần mới, không rollback mất dữ liệu. Giai đoạn7 mới quyết định cutover được giao.

<a id="api"></a>
## 4. API đề xuất và preview

Giữ /api/v1, DTO extra-forbid/int strict, date ISO UTC, reason/source trim1–1000, page≥1/page_size1–100; lọc/count/tổng trước offset/limit. Ngày xem bắt buộc cho quyền/preview; thiếu ngày trả quyền null, không tự chọn ngày thực. Đọc latest version không hạ version theo ngày xem quá khứ.

| Endpoint dự kiến | Đọc/ghi và phản hồi |
|---|---|
| GET/POST /products/{id}/supply-changes | Giữ URI/action/shape cũ để tương thích, nghĩa rõ nội bộ; POST cho stop cùng ngày sau cutover đồng bộ. GET lịch sử giảm version, latest supply_version và state theo as_of_date. |
| POST /products/{id}/internal-stop-preview | known_on/effective_on/reason/action/target/expected_version và impact_run_id/as_of_date tùy chọn. Preview quyền/balance/lô theo snapshot đã chọn, không lưu. |
| GET /provider-product-notices | Bộ lọc supplier/SKU/type/market/warehouse/item/status/as_of_date/search, phân trang; trả mỗi thông báo một lần dù nhiều item. |
| POST /provider-product-notices/preview | action và payload tương ứng, scope cho create; trả số item/kho, membership phân trang, versions/scope hash, mốc ngày/quyền thay đổi; tồn/lô/ETA ảnh hưởng từ impact_run_id đã chọn. |
| POST /provider-product-notices | Tạo root+membership+event stop. expected_version=0, preview_fingerprint và cùng scope/payload; trả201 notice/event/version/scope totals. |
| GET /provider-product-notices/{id} và /{id}/events, /{id}/items | Header/scope/lịch sử và item phân trang; state theo ngày, latest_version, lý do/nguồn và các hạn chế chồng lấp. |
| POST /provider-product-notices/{id}/cancel | target_event_id, known_on, effective_on=known_on, reason/source, expected_version, fingerprint; chỉ trước stop hiệu lực. |
| POST /provider-product-notices/{id}/resume | resume_supply riêng, effective_on≥known_on, target/nguồn/lý do/version/preview; không sửa stop cũ hoặc mở nhập nội bộ. |
| GET /products và /products/{id} | Thêm internal_status/provider_status/replenishment_allowed/sales_allowed/notice IDs/reasons và filter độc lập. supply_status/supply_version cũ chỉ alias nội bộ được ghi rõ, không dùng làm trạng thái tổng hợp mới. |
| GET /runs/{id}/sell-through và exports/sell_through | URI hiện có, profile dispatch; profile mới thêm sales_blocked_qty/unserved_stock_qty/tồn tổng-được bán-bị chặn, quyền/nguồn/lý do và counts, không đổi dữ liệu lưu run cũ. |

Preview đối chiếu scope với catalog thực, trả scope_definition rõ thị trường/loại/kho, số item/tổng toàn scope và trang mẫu chỉ để xem. Tồn/lô phải có runID/origin/window được chọn, gồm total/sellable/blocked, lô cũ sẽ về sau hạn, Q trước/sau và lý do cap nếu có projection đủ coverage. Không có run/dữ liệu thì ghi “Chưa có dữ liệu tác động”, quantity=null, vẫn cho lưu cấu hình hợp lệ sau khi người dùng thấy thiếu số liệu; không gán0. Đây không phải tính run thử hoặc worker ngầm trong preview.

Fingerprint là hash do BE tính từ payload chuẩn hóa, membership/catalog identity, latest versions của các hạn chế liên quan, impact_run/config hash và ngày; không cần bảng token preview. Khi lưu, BE resolve/khóa lại, tính lại hash, kiểm expected_version; khác thì409 preview_stale và bắt xem lại. Fingerprint không thay validation hoặc quyền truy cập. Nếu catalog mới có item khớp thì trả409 thay vì âm thầm thêm item. Không dùng lượng tồn preview để ghi thay ledger.

Lỗi404 item/notice/run không tồn tại;422 ngày/scope/nguồn/payload/filter sai, thiếu ngày khi filter trạng thái;409 version_conflict/preview_stale/state_conflict/feature_not_in_run;503 trade_schema_required khi DB/code chưa đồng bộ. Không migrate từ API, không giả active khi schema mới thiếu. Atomic nhiều kho; 201 khi append thành công, GET/preview200. Cancel/resume có modal riêng nhưng dùng chung validation nghiệp vụ với CLI; không API vượt restriction. Các API hiện có không trở thành endpoint đặt hàng thật.

<a id="snapshots-and-causality"></a>
## 5. Snapshot, profile và tương thích run

Run inventory mới sau cutover đóng băng `trade_lifecycle_profile=internal_provider_trade_v2`, `internal_supply_snapshot`, `provider_notice_snapshot` (root/scope/member IDs/events/version), catalog identity và `trade_rules` gồm UTC/cutoff, full_fixed_lot, coverage_required, actual_blocking và metric exclusions. Hash snapshot/config và artifact manifest theo cơ chế hiện có. Profile mới tách khỏi supply_lifecycle_profile notice7 cũ; không ghi hai marker mâu thuẫn. Chỉ lấy hàng đã tồn tại tại transaction enqueue và known_on≤origin quyết định lớn nhất của run. Snapshot transaction nhất quán cho cả hai nguồn/membership/catalog; không trộn scope trước ghi và event sau ghi.

- stock_projection: o=as_of_date cố định; mọi target H14 chỉ dùng thông tin biết tại o.
- policy_replay: o cuốn mỗi ngày quyết định, filter prefix **trước** giải quyền; xử lý bán ngày d với thông tin biết tại d, không dùng receipt/sale tương lai.
- alert_replay: mỗi cửa sổ giữ o; mọi sale giả định/projection trong cửa sổ dùng cùng tập biết tại o, dù run đã freeze cả các event biết ở origin sau.
- cancel/resume biết sau o không tác động kết quả tại o. Late notice không sửa quyết định/ledger trước ngày được biết; created_at sau enqueue không được nối thêm, kể cả known_on người dùng nhập lùi.
- Idempotency-Key enqueue retry trả run/snapshot cũ, không refreeze cấu hình mới.

Dispatch rõ: không có lifecycle profile→reader/verifier legacy; notice7_sellthrough_v1→CHG-084 đúng nghĩa nội bộ/7ngày/actual không bị chặn; internal_provider_trade_v2→quy tắc mới. Profile lạ hoặc snapshot thiếu dữ liệu bắt buộc thì lỗi có nghĩa, không fallback. Guard stage_not_implemented phải có trước khi API cho enqueue profile mới và chỉ gỡ khi worker/verifier hỗ trợ đầy đủ.

Run cũ giữ nguyên snapshot/JSON/artifact/hash/metric và cách đọc, không JOIN lịch live, không ghi thêm trường mới vào persisted result. API mới có thể trả feature availability dựa profile; trường quyền bán/blocked không được tính bằng live hoặc trả0 giả cho legacy. Tính năng mới thiếu trong run trả409 feature_not_in_run, UI mời tạo kế hoạch mới. Reader alias supply_status cũ luôn nghĩa nội bộ, không gán thành provider_status.

<a id="forecast-and-worker"></a>
## 6. Worker, projection, ledger và metric đề xuất

Giữ target quantity bán, lịch sử actual, raw route/item forecast, allocation/share, model selection và M05/R05. Raw forecast là đầu vào từ lượng bán quan sát, không đại diện đo lường đầy đủ nhu cầu thị trường. Không chia phần bị chặn sang SKU khác, không refit chỉ vì thêm thông báo.

### 6.1. Projection từng ngày và Q

Nhận lô cũ trước, resolve quyền theo (o,d), sau đó tính:

```text
available_total = opening_total + known_receipts
sellable_qty = available_total nếu sales_allowed, ngược lại 0
blocked_stock_before_sale = available_total - sellable_qty
projected_sales_qty = min(forecast_input_qty, sellable_qty)
sales_blocked_qty = forecast_input_qty nếu bị nhà mạng chặn, ngược lại 0
unserved_stock_qty = forecast_input_qty - projected_sales_qty - sales_blocked_qty
closing_total = available_total - projected_sales_qty
closing_sellable = closing_total nếu sales_allowed, ngược lại 0
closing_blocked = closing_total - closing_sellable
```

Nonnegative; forecast_input = projected_sales + sales_blocked + unserved_stock, total=sellable+blocked ở mọi mốc. Khi nhà mạng chặn và hết hàng đồng thời, toàn input ngày đó là blocked, không gán đồng thời thiếu hàng. Giữ số thực cho projection; ledger actual giữ quantity nguyên. Thiếu forecast/actual vẫn là thiếu dữ liệu, không đổi thành0.

Ví dụ đầu ngày tồn10/input4: nội bộ ngừng nhập thì sales4/closing6/unserved0/blocked0; nhà mạng ngừng thì sales0/closing10/blocked_stock10/sales_blocked4. Lô cũ về5 khi đang chặn→total15/blocked15, không bán. Provider resume khi nội bộ vẫn stop→stock bán được lại, Q vẫn0.

Tính ROP/SS/S/IP/Q_policy như hiện tại để chẩn đoán, rồi áp hai quyền và [cap nguyên lô/ETA/coverage](../../docs/planning/PRODUCT_SUPPLY_LIFECYCLE_PLAN.md#inventory-and-orders). Cả recommendation và nhánh tạo Replenishment đều kiểm lại guard; Q0 không được tạo lô0. Projection chỉ cộng lô đã biết trước Q mới, không đưa chính Q khuyến nghị vào path để tự chứng minh khả năng bán. Không cộng tồn blocked vào tồn có thể đáp ứng; ghi raw low-stock riêng với actionability để không phát CTA trái hạn chế. Không sửa công thức policy để che cap.

### 6.2. Replay actual sau ngừng bán giả định

Nguồn actual giữ nguyên và không tự coi mọi sale sau effective là hợp lệ. Với từng sự kiện sale trong replay:
- Nếu restriction đã biết và hiệu lực theo cutoff của loại replay: source_sales_qty giữ lượng nguồn; scenario_sales_qty=0; actual_blocked_qty=source_sales_qty; fulfilled/shortage do thiếu hàng đều0, không xuất tồn.
- Nếu chưa bị chặn tại cutoff: scenario_sales_qty=source_sales_qty, fulfill theo tồn; actual_blocked0, scenario_sales=fulfilled+shortage. Sale trước known_on của late notice vẫn theo quyết định lúc đó, không hồi tố.
- Ledger luôn opening+receipts−fulfilled=closing; source_sales=scenario_sales+actual_blocked. Inventory event bị chặn vẫn lưu source_sequence/thời gian đối chiếu, event_kind=sale_blocked và quantity nguồn, fulfilled/shortage0/balance không giảm; không xóa event hoặc sửa DailySales.
- Không vừa ghi sale_blocked vừa sale hợp lệ cho cùng source event; idempotent receipt một lần và source event một lần theo window.

Đề xuất migration0008 cùng giai đoạn2 thêm hai cột nullable source_sales_qty, actual_blocked_qty; producer profile mới bắt buộc ghi cả hai, actual_blocked_qty=0 khi không chặn. Profile mới định nghĩa inventory_daily.sales_qty là scenario_sales_qty, không phải source_sales_qty. **Run cũ không backfill hay UPDATE**: cột mới không có server default, hàng lịch sử vẫn null, reader cũ lấy sales_qty theo nghĩa cũ. CHECK mới yêu cầu hai cột cùng null hoặc cùng không âm và source_sales_qty=sales_qty+actual_blocked_qty; CHECK balance/sales_qty=fulfilled+shortage hiện có giữ nguyên. Mã InventoryEvent hiện chỉ cho sale/receipt/initial_stock qua CHECK: 0008 sẽ nới đúng CHECK này cho sale_blocked, bắt buộc source_sequence, không replenishment_order_id, fulfilled/shortage0. quantity lưu lượng nguồn. Không sửa migration cũ. Các cột projection/tồn được phép/bị chặn lưu explanation/artifact, không nhân đôi bảng ledger tồn.

Mẫu số/metric profile mới: báo riêng tổng source quantity, allowed scenario quantity, blocked quantity, fulfilled/shortage và fill_allowed=fulfilled/allowed khi allowed>0 (ngược lại null). Báo blocked/source riêng; không gọi blocked là shortage. Metric depletion/threshold cần tách phạm vi item-window không bị chặn và các window có chặn bị loại khỏi **đánh giá cảnh báo cơ sở**, kèm số/IDs/reasons/thời đoạn loại; vẫn xuất chẩn đoán scenario cho mọi window. Nếu hạn chế giữa cửa sổ, loại cả item-window khỏi đối chiếu cơ sở, không chỉ bỏ ngày xấu. Không gộp mẫu số mới với baseline; run không có hạn chế bán phải parity metric cơ sở. M05/R05 raw forecast vẫn đối chiếu nguồn actual theo hợp đồng cũ, không dùng actual đã chặn để tuyên bố forecast tốt hơn. Không nâng R07/T14 từ fill hoặc giảm episode sau khi chặn bán.

### 6.3. Lưu và verify

Projection/explanation mới chứa input forecast (giữ forecast_demand_qty như alias đầu vào để tương thích), projected_sales_qty, sales_blocked_qty, unserved_stock_qty, receipts, closing_total/sellable/blocked, internal/provider state, blocker IDs/reasons và Q_policy/Q_final/cap_reason/B/T/ETA/coverage. Các tổng phải cùng run/origin/window/item/date. Không đổi unserved_demand_qty cũ âm thầm: ở profile mới nếu giữ alias, nó bằng unserved_stock_qty+sales_blocked_qty và luôn có breakdown; UI/CSV ghi rõ tổng không chuyển thành bán.

Verifier chọn theo profile, tự giải intervals/overlap/prefix và scope từ snapshot; tự tính balance/rights/cap Q/receipt/projection/sale_blocked và metric/exclusions, không gọi supply_state/recommend/project của producer để tự xác nhận. Kiểm membership đầy đủ đúng carrier/SKU/type/market/kho, không ảnh hưởng ngoài scope; nguyên hash source/forecast parent. Khi biết muộn/resume giữa H14 cần ca tính tay độc lập, không chỉ so metadata producer.

<a id="read-model"></a>
## 7. Read model, CSV và trạng thái vận hành

Đọc kết quả đã lưu, không chạy lại resolver live hoặc projection trong request. Có thể giải frozen timeline cho metadata theo profile/ngày như CHG-084; số lượng phải lấy ledger/projection đã lưu. Inventory: total_qty/sellable_qty/blocked_qty; purchasing: Q_policy/Q_final, quyền nhập và từng lý do, pending cũ và cờ needs_supplier_action; forecast: projected sales chính, input model trong chi tiết, stock shortage và sales blocked riêng. Alerts giữ raw diagnostics, actionability và hạn chế; workspace không tính blocked hoặc stopped thành healthy chỉ vì Q0.

Filters internal_status/provider_status/replenishment_allowed/sales_allowed/supplier/item/warehouse/type/date/origin/window thực hiện trước count/aggregate/pagination; OR/AND nêu rõ: các nhóm filter kết hợp AND, blockers trong một item là OR. Tổng theo tuyến/ngày cộng toàn item trong phạm vi snapshot, không lấy một trang và không ép tổng constrained sales bằng route forecast. Counter internal_stopped/provider_blocked/blocked_stock riêng; item có cả hai có thể thuộc cả hai counter, tổng affected_items dùng distinct.

CSV cùng dataset/filter/profile với API, xuất toàn phạm vi, có run/config/source/profile/origin/window/target date/units, hai quyền/lý do/IDs, các lượng và metric basis; chống công thức cho reason/source. CSV sealed cũ không viết lại. FE không có field của profile cũ hiển thị “Không có trong kế hoạch này”, không vẽ đường0 giả.

<a id="frontend"></a>
## 8. FE: ba chức năng rõ nghĩa

[Đặc tả điều hướng, wireframe, hành động, lỗi và responsive](04-frontend-spec.md#lifecycle-chg085) là thiết kế mục tiêu; mã ProductSupplyForm trên chi tiết hiện tại chưa được chuyển.

1. ProductDetail chỉ summary nội bộ/nhà mạng, quyền tại ngày xem, lý do và link tới nghiệp vụ; policy vẫn form riêng đúng nghiệp vụ. Không nhét form hai loại vào chi tiết.
2. “Ngừng nhập nội bộ” modal riêng theo item/kho, ngày/lý do/preview tồn-lô, vẫn bán tồn; lịch sử và hủy/mở lại riêng theo trạng thái.
3. “Thông báo ngừng sản phẩm” trang quản lý riêng: list/create/detail; chọn scope một lần cho nhiều kho, known/effective/source/reason, preview toàn scope, lịch sử, cancel hoặc resume riêng.

Danh mục/config mới nhất và kế hoạch frozen luôn có nhãn/ngày/run rõ ràng. Sau save refetch config/version, giữ run đang xem, nhắc tạo kế hoạch mới; không cập nhật số liệu run tại chỗ. CTA tạo kế hoạch phải để người dùng chủ động, không enqueue ngầm.

<a id="test-matrix"></a>
## 9. Ma trận kiểm bắt buộc khi triển khai

| Ca | Kết quả cần kiểm / giai đoạn |
|---|---|
| Nội bộ stop cùng ngày/lịch tương lai | effective=known được nhận, ngày trước known422; vẫn bán tồn; L7 không thành notice7 (2/4/6). |
| Nội bộ hủy/mở lại/sửa policy | Hủy trước stop; sau stop phải resume; sửa ROP/SS/Q không mở lại (2/3/6). |
| Nhà mạng dừng còn tồn | sales0, blocked stock=total, ledger không mất hàng/tổn thất (2/4/5). |
| Lô cũ về sau hạn | Receipt đúng một lần, total tăng/blocked tăng, needs_supplier_action (4/5/6). |
| Q trước hạn/ETA chạm hoặc sau hạn | ETA≥T→0; B≥fixed→nguyên lô, B<fixed→0; thiếu coverage→0 có lý do; không đổi policy (4). |
| Một notice nhiều kho và ngoài phạm vi | Cùng notice/membership áp đồng nhất; SKU/type/carrier/market/kho ngoài scope không đổi; scope mới409 stale (2/3/4). |
| Hai nguồn hạn chế và nhiều notice chồng | Gỡ từng hạn chế chỉ gỡ đúng nguồn/notice; provider resume + nội bộ stop vẫn Q0, bán được (2/4/6). |
| Hiệu lực trong ngày/biết muộn | effective<known hợp lệ cho provider; không viết lại ledger trước known (2/4). |
| Cancel/resume tương lai | Cancel trước hiệu lực; resume_supply không xóa block trước ngày phục hồi dù đã biết (2/4). |
| Known sau origin, created sau enqueue | Policy rolling/alert fixed origin; snapshot không tải thêm live; retry enqueue giữ snapshot (3/4). |
| Replay actual sau stop giả định | Actual nguồn/hash nguyên; source=allowed+blocked; allowed=fulfilled+shortage; sale_blocked không xuất tồn (4/8). |
| Metric và mẫu số | Nguồn/blocked/allowed/excluded window công khai; null khi denominator0; không nâng R07/T14, không đổi R05 (4/5/8). |
| Run cũ/profile cũ | Hash/snapshot/artifact/reader cũ nguyên; notice7 không diễn giải thành provider; thiếu feature409 (3/7/8). |
| API/CSV/FE frozen | Cùng run/origin/window/filter; aggregate trước page, CSV đủ scope; không nối live (5/6/8). |
| Version/preview/save atomic | Hai ghi một success một409; scope/versions đổi phải preview lại; fail một item rollback cả notice (2/3). |
| Migration dữ liệu không rỗng | Upgrade giữ mọi event cũ; downgrade bị chặn nếu mất history/vi phạm+7; không sửa0007 (2/7). |
| FE states/desktop/390px | loading/empty/error/conflict/save–reload/Back/focus, nhãn nguyên nhân, không CTA nhập/bán trái quyền (6/7). |

Giai đoạn1 chỉ kiểm tài liệu/link/anchor/bảng/fence/sơ đồ/nhất quán/diff; các ca trên chưa chạy cho CHG-085. Không chạy suite/model để xác thực tài liệu.

<a id="step8-run-validation"></a>
## 10. Giai đoạn8 mới và bằng chứng CHG-084 tạm dừng

[Kiểm kê bằng chứng đã có và phần còn lại](../../docs/planning/PRODUCT_SUPPLY_LIFECYCLE_PLAN.md#step8-run-validation). Các bản sao cũ có báo cáo nên không ghi “chưa chạy gì”; không chuyển profile của run b2fb2e42 hoặc dùng nó chứng minh chặn bán.

Khi được giao8 mới: kiểm read-only danh sách run/app/archive/bản sao trước; hash mọi hàng/snapshot/artifact trước–sau; reader/verifier riêng từng profile; lập DB/output riêng cho kịch bản mới có thông báo multiwarehouse, tồn còn, lô cũ sau hạn, ETA mới chạm hạn, overlap nội bộ, late known và actual sau stop giả định. Khóa nguồn/forecast/seed/config/ngày/scope/giả định trước kết quả, không tuning hoặc refit để ép kết luận. Đối soát worker→verifier→API/CSV/UI desktop/390px cùng snapshot và metric/exclusions. Run/archive không đọc được ghi thiếu có lý do; không sửa hash để qua. Đây là kế hoạch, chưa thực hiện trong lượt1.
