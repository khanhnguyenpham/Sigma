# M3 — kiểm thử, nghiệm thu và bàn giao

**CHG-087 — 03/11/2026, chỉMarkdown:** [kế hoạch demo đầy đủ dùng chung](../../docs/planning/RENDER_VERCEL_DEPLOYMENT_PLAN.md) thay giai đoạn chỉ đọc củaCHG086. Cổng kiểm dự kiến gồm chuỗi import→forecast→3loại run tồn, tổng30 đúng nguồn, kho/policy/lifecycle, hai khách/version409, queue/quota/retry, mobile/CSV, restart/worker/disk và resetDB+artifact. Chưa chạy các cổng online này. Không cần login/tenant/RBAC cho chức năng nghiệp vụ theo lựa chọn người dùng; reset chỉ bằng công cụ vận hành. [Bàn giao và phạm vi publishMD](../../docs/development.md#handoff-chg087). Các test/DBhashCHG086 dưới đây là bằng chứng lịch sử, không phải vừa kiểm lại hoặc nghiệm thuD1–D6.

**CHG-086 — 03/11/2026:** đã kiểmS25 bằng physical reconstruction/projection/scoring độc lập,483Python BE/M2 vàpipcheck đạt;4DB/1.466tệp bảo vệ nguyên, app0008/3run. [Báo cáo](S25_CURRENT_REVIEW.md), [lệnh/bằng chứng](../../docs/development.md#handoff-chg086). Không đổi mã phục vụ/DB/FE nên không nhận đã chạy lại browser/React ở lượt này. [Kế hoạch Render/Vercel](../../docs/planning/RENDER_VERCEL_DEPLOYMENT_PLAN.md) bổ sung các cổng chỉ đọc/ẩn danh/staging/restart/restore/rollback; chưa thực hiện online. R05/R07/T14 mở,45% không là cổng sản phẩm đơn lẻ theo yêu cầu người dùng mới.

**CHG-085 giai đoạn 8 — 03/11/2026, hoàn tất local:** đã đọc và verify 7 run cũ, đối chiếu API/CSV cho 12 cặp DB–run; chạy 4 run mới trên bản sao dùng nguồn/forecast có sẵn và 1 run synthetic cho hai kho. Worker, verifier độc lập, API/CSV và browser 1440/390px đạt. Ca bổ sung chặn 19 đơn vị nguồn trong mô phỏng; ca synthetic có 280 = 150 được phép bán + 130 bị chặn. Sửa nhãn quyền mua/bán trong bảng projection; 89 React và build đạt. App ở 0008 với 3 run ban đầu; 4 DB bảo vệ và 1.412 tệp giữ hash. Không refit/tuning hoặc viết lại bằng chứng CHG-084; R07/T14 giữ mở. Thay đổi giai đoạn 7–8 chưa commit/push. [Bàn giao/giới hạn](../../docs/development.md#handoff-chg085-phase8). Các checkpoint bên dưới là lịch sử.

**CHG-085 giai đoạn 6 — 02/11/2026, hoàn tất local FE:** modal ngừng nhập nội bộ cùng ngày, trang thông báo nhà mạng/phạm vi nhiều kho, preview và hai quyền riêng; vận hành hiển thị lượng bán/tồn bị chặn/Q/cap từ frozen. Baseline74, suite cuối88React (gồm22ca liên quan), 37ca hợp đồng BE, build/pipcheck và browser1440/390px synthetic đạt. DBapp vẫn0007; không cutover/nguồn thật/bước8 cũ. Bước4–6cònlocal, chưa commit/push; dừng trước7, R07/T14 giữ mở. [Lệnh và bằng chứng](../../docs/development.md#handoff-chg085-phase6). Browser dùng Vite5176/API8306/sigma_m3_test riêng; không dùng API/worker app. 409/422/future-resume/refetch-failure/double-submit kiểm React; browser kiểm save/load/Back/Escape/CSV và frozen sau cấu hình mới. Bằng chứng local không đưa Git.

**CHG-085 giai đoạn 5 — 02/11/2026, hoàn tất local:** đã mở API kết quả/CSV trade_v2 từ ledger, projection và snapshot frozen; lọc hai quyền/trạng thái trước count/page/aggregate, counters riêng và metric có scope/exclusions. Baseline11/targeted62/suite478 Python BE/M2 và pip check đạt. DB ứng dụng vẫn 0007, hai bản sao/bằng chứng cũ giữ nguyên; không FE/cutover/nguồn thật. Chưa commit/push bước 4–5; dừng trước 6. R07/T14 giữ mở. [Lệnh, ca và bảo toàn](../../docs/development.md#handoff-chg085-phase5). Có CSV5040hàng qua batch5000, scope trộn/AND/page/aggregate, hai window đổi prefix, metric TP/FN/blocked/null, preview lượng trade, legacy0007 và chứng minh GET không ghi/tự project. Chưa browser/FE, không dùng synthetic làm nghiệm thu R07.

**CHG-085 giai đoạn 4 — 02/11/2026, hoàn tất local:** worker/projection và verifier độc lập đã thực thi trade_v2; 40 ca trade mới, 152 ca targeted và toàn suite 459 Python BE/M2 đạt, pip check đạt. Tồn tổng được giữ, sale bị chặn ghi riêng, Q áp cap nguyên lô/ETA/coverage và metric loại cả item-window bị chặn. DB ứng dụng/bản sao cũ chỉ đọc, không cutover hoặc chạy nguồn thật. Bước 5–8 chưa làm; chưa commit/push bước 4 trong lượt này. R07/T14 giữ mở. [Ca kiểm và lệnh thực](../../docs/development.md#handoff-chg085-phase4). Có mutation projection/cap/source split/receipt/summary, policy rolling và hai alert windows có prefix riêng; legacy golden giữ nguyên. Không chạy browser/FE hoặc dùng ca synthetic làm bằng chứng R07 đạt.

**CHG-085 giai đoạn3 — 02/11/2026:** baseline65, targeted83 và full419Python BE/M2 đạt, pipcheck đạt. test_trade_api.py có18ca: scope nhiều kho/filter trước page, preview/FP/stale/concurrency, cancel/resume/late known, source/extra strict, schema0007, stored impact null, snapshot3kind/idempotence/source parent hash, transaction2nguồn và guard worker/verifier/result. Golden gốc không sửa; không dùng kết quả2thay kiểm3. [Bàn giao và bảo toàn](../../docs/development.md#handoff-chg085-phase3). Không chạy FE/browser hoặc nguồn thật; người dùng giao publish2–3/SHAremote/CI rồi dừng trước4.

**CHG-085 giai đoạn2 — 02/11/2026:** baseline51ca, targeted84ca và suite cuối401Python BE/M2 đạt,0failure/error/skip; pip check đạt. Test upgrade có ledger/history cũ và API/CSV ở0007, metadata0diff, source split/event/FK, concurrency, downgrade chặn mất dữ liệu. Không sửa golden gốc; đã sửa helper fixture, count query và phép đối chiếu bảng/cột tại mốc0004 trong test supplier; kết quả failing không tính đạt. [Kiểm cuối và giới hạn](../../docs/development.md#handoff-chg085-phase2). Không chạy FE/model thật hoặc ghi DBapp/bản sao bước8.

## CHG-085 — Cổng kiểm tài liệu và triển khai dự kiến

Giai đoạn1 chỉ kiểm link/anchor, bảng/fence/sơ đồ, thuật ngữ/ngày/phạm vi/profile, diff Markdown; không chạy suite/model/migration/run. Người dùng bổ sung giao kiểm xong commit/push thường final-report, SHA remote/CI rồi dừng trước2. [Ma trận bắt buộc khi triển khai](07-product-supply-lifecycle.md#test-matrix), [8giai đoạn và điểm dừng](../../docs/planning/PRODUCT_SUPPLY_LIFECYCLE_PLAN.md#steps).

**Bước8 CHG-084 đã làm một phần, đang tạm dừng:** có report verifier6run cũ và policy_replay b2fb2e42 trên bản sao, API/CSV/plot và báo cáo ngừng nhập; chưa thấy preserved.json/final browser/handoff. Không chạy lại hoặc sửa bằng chứng, không coi là nhà mạng ngừng bán. [Kiểm kê trực tiếp file và phần còn lại](../../docs/planning/PRODUCT_SUPPLY_LIFECYCLE_PLAN.md#step8-run-validation). Những dòng “chưa chạy bước8” ở checkpoint dưới đây chỉ đúng tại thời điểm cũ. R07/T14 chưa nghiệm thu.

**CHG-084 bước7 — 02/11/2026:** suite mới368Python BE/M2 và74React đạt, build/pipcheck đạt. Regression test tái hiện rồi chặn tự điền ngày đã xóa khi API run list lỗi/phục hồi. Backup restore vào sigma_m3_test, kiểm đủ13bảng ở0006 rồi nâng diễn tập0007/schema0diff; sau đó mới nâng app, giữ3run/1.052file/history mới0. API/CSV920, browser app1440/390px và synthetic form→API→worker→verifier→CSV đạt. [Bằng chứng, lỗi môi trường và giới hạn](../../docs/development.md#handoff-chg084-step7). Không dùng synthetic thay kịch bản nguồn thật bước8; bước8 chưa chạy, R07/T14 giữ mở.

**CHG-084 bổ sung bước8 — 02/11/2026, chưa thực hiện:** sau bước7 và khi được giao, kiểm danh sách run cũ còn truy cập (kể cả archive), reader/verifier theo profile và hash trước–sau; chạy một policy_replay mới trên DB bản sao với một stop giả định giữa kỳ. Khóa thông báo/ngày dừng≥7ngày và pending đã biết tại origin; kiểm không đặt mới từ ngày dừng, nhận lô cũ, bán tồn/unserved/cutoff và API/CSV/UI. [Protocol](../../docs/planning/PRODUCT_SUPPLY_LIFECYCLE_PLAN.md#step8-run-validation), [bằng chứng cần có](07-product-supply-lifecycle.md#step8-run-validation), [bàn giao MD](../../docs/development.md#handoff-chg084-step8-plan). Đây chưa là test/run đã chạy, không đổi R07/T14.

**CHG-084 bước6 — 02/11/2026:** suite React đạt73/73, gồm8ca supply-management mới; build/pipcheck đạt. Browser synthetic trên DBtest kiểm mở lại/dừng/hủy/reload/history, biên7ngày, Back/focus, lọc và tải CSV14dòng, desktop1440/390px không tràn ngang trang. 409/giữ lý do/chống gửi lặp/unmount/thiếu ngày/legacy/CTA được kiểm trong React. [Bàn giao và giới hạn](../../docs/development.md#handoff-chg084-step6). Không chạy lại suite BE/M2 local hoặc model thật cho thay đổi chỉ FE; CI kiểm đúng commit saupush. DBapp chỉ đọc, bước7 vẫn chờ giao, R07/T14 chưa nghiệm thu.

**CHG-084 bước5 — 02/11/2026:** test_sell_through_api.py kiểm3kind API/CSV/frozen sau live resume, bộ lọc/aggregate trước pagination, synthetic5040dòng qua nhiều batch export, legacy409 và ranh giới replay. Kết quả thực tại [bàn giao](../../docs/development.md#handoff-chg084-step5). Chỉ DBtest, không nâng DBapp/FE hoặc chạy model/replay thật; R07/T14 giữ mở.

**CHG-084 bước4 — 02/11/2026:** test_supply_simulation.py thêm ca tính tay, stop/resume/cutoff/receipts/actual/parity và worker thật cho3kind; tamper Q/dự kiến bán/unserved/status và lịch sử invalid phải bị verifier chặn. Kết quả thực tại [bàn giao](../../docs/development.md#handoff-chg084-step4). Chỉ DBtest, không chạy model/replay thật hoặc nâng DBapp; R07/T14 chưa nghiệm thu.

**CHG-084 bước3 — 02/11/2026:** test_supply_api.py kiểm HTTP/validation/trạng thái/lịch sử, ghi đồng thời, lọc trước pagination, idempotency/cutoff/frozen và schema0006 tương thích. Guard worker được kiểm để không verify nhầm run có lịch sử. Kết quả thực tại [bàn giao](../../docs/development.md#handoff-chg084-step3); không coi API/snapshot là đã có FE hoặc simulation cung cấp.

**CHG-084 bước2 — 02/11/2026:** thêm test_supply_lifecycle.py kiểm timeline, biên ngày, nhân quả, constraint/migration/bảo toàn và chặn downgrade có dữ liệu. Golden13bảng/OpenAPI cũ giữ; contract chỉ loại đúng bảng mới khi đối chiếu DDL lịch sử. Chạy trên sigma_m3_test, không trên DBứng dụng. Kết quả thực tại [bàn giao bước2](../../docs/development.md#handoff-chg084-step2); ma trận FE/API/worker vẫn là kiểm dự kiến cho bước sau.

## CHG-084 — Cổng kiểm và điểm dừng

02/11/2026: bước1 chỉ kiểm MD/link/anchor/bảng/Mermaid/tính nhất quán và diff bảo toàn; không chạy model/migration hoặc nhận các kiểm ứng dụng đã đạt. Sau kiểm, commit/push thường phần MD trên final-report, đối chiếu SHA remote và CI rồi dừng chờ duyệt bước2. [Ma trận kiểm dự kiến](07-product-supply-lifecycle.md#test-matrix), [7bước/T01/T10/T11/T12](../../docs/planning/PRODUCT_SUPPLY_LIFECYCLE_PLAN.md#steps), [bàn giao thực](../../docs/development.md#handoff-chg084). Bước2–7 còn chờ; DBapp chỉ cutover sau backup/restore thử ở bước7, giữ R07/T14 chưa nghiệm thu.

**CHG-068 bước 15 — 27/10/2026, hoàn tất:** đã chạy hai replay thật mới với cấu hình cơ sở khóa trước kết quả; worker và verifier độc lập đạt. Policy fill 90,4121%, thiếu 1.531/15.968; depletion báo sớm 986/2.867 = **34,391350%, chưa đạt mục tiêu làm việc 45%**. Metric xuống ROP giữ riêng (TP101/FP89/FN0/TN619). 245 Python, 50 React, build/pip check, API/CSV/browser đạt; 1.038 hash protected, 140 artifact sealed và hàng cũ của 13 bảng nghiệp vụ + Alembic nguyên. Schema 0003_threshold/0diff; chỉ thêm hai run local, không refit/tuning. R07/T14 chưa nghiệm thu. Commit `2658b8116accbed4354fdc18b55d7ed52f436f7c` đã push thường, remoteSHA khớp và2workflowCI completed/success. [Bằng chứng và cách kiểm lại](../../docs/development.md#handoff-chg068-step15). Các checkpoint bên dưới giữ vai trò lịch sử.

**CHG-068 bước14 — 26/10/2026, hoàn tất:** sau cổng13 mã73d6f39/remoteSHA/2CI success, người dùng giao14. React hiển thị ROP/SS/mode/N, ngày xuống ROP riêng ngày cạn, lý do/đường projection/bảng UTC; filter/export và metric threshold riêng depletion. Workspace thêm warning_items/projected_below_rop_items đếm item duy nhất; inventory API/CSV đọc5tham số từ policy frozen, công thức fixed hiển thị đúng.245Python (3ca mới),50React (7ca mới,1worker)/build/pipcheck và browser desktop/mobile390px trên2run synthetic đạt;1027protectedhash và3app run nguyên, schema0003_threshold giữ. Commit mã37c4525b90cb361d8eeabc23c46cfc82fb39f8dc đã push thường, remoteSHA khớp và2workflowCI completed/success; bước15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật mới chứng minh45%.

<a id="warning-ui-tests-step14"></a>
## Kiểm hiển thị bước14 thực chạy — 26/10/2026

Baseline bước13 có242Python/43React và2CI success. Sau thay đổi:245Python/0failure/error/skip, thêm3ca worker/read model/API/CSV kiểm item duy nhất khi hai tín hiệu, loại no-event khỏi số cảnh báo, filter, frozen policy khi sửa live và defaults của run legacy.9inventory golden/M2 parity và OpenAPI/DDL contract giữ.

50React đạt --maxWorkers=1, thêm7ca: type/state/export/page reset, drawer ROP/N/hai ngày/UTC, metric giữ mẫu số, stale context, Overview unique count, fixed formula và ratio null. Lượt mặc định khi chạy cùng Python có1ca Back/reload cũ timeout5000ms (49/50); không đổi timeout hoặc code test cũ, chạy lại1worker50/50. TypeScript/Vite build/pipcheck đạt.

Browser/API thật trên2run synthetic stock_projection và alert_replay đã worker/verifier complete:2signals/1item, filteredCSV1row, ROP20/N7/ngày threshold01/11 riêng depletion09/11; hai panel metric không gộp. Desktop1280×720 và mobile viewport390×844, chart/scroll/Escape/focus đạt; reset viewport/đóng tab/dừng stack.1027protectedhash nguyên, app3run hash nguyên trong transaction readonly và revision0003_threshold giữ. Không replay dữ liệu thật hoặc tự đóng R07/T14. [Bàn giao](../../docs/development.md#handoff-chg068-step14).

<a id="policy-form-tests-step13"></a>
## Kiểm form bước13 thực chạy — 26/10/2026

Baseline nhận từ bước12:242Python/34React đã đạt local và2CI. Sau sửa FE:43React (thêm9ca) đạt cả mặc định và1worker, TypeScript/Vite build đạt;9ca kiểm payload volatility/fixed, giữ inactive policy values khi đổi mode, policy lịch sử/expected_version/effective date và409,6biên native chặn POST, scenario partial override/blank/0/bỏ inactive fields. Các ca34cũ tiếp tục kiểm nativefields/URL/Back/Escape/focus/batched update; cập nhật kỳ vọng payload đúng5trường mới.

Browser713×615 gọi API thật trên DB test: lưu policyv2, đọc lại lookback90/factor0/N14/mode sau reload, giữ tham sốv1 và hết hiệu lực đúng ngày; scenario lưu chỉ item/mode/factor0/N1, trường trống không ghi đè. Escape đóng modal/trả focus dòng đã mở; form cuộn tới nút lưu được. Stack test dừng.1029protectedhash nguyên, chỉ source FE được giao cùng build dist/cache được phép thay; app3run hash nguyên trong transaction readonly, schema0003_threshold. Kiểm Python hiện tại ghi ở bàn giao; không chạy replay thật/đổi metric hoặc nâng R07/T14. [Bàn giao](../../docs/development.md#handoff-chg068-step13).

**CHG-068 bước12 — 26/10/2026, hoàn tất:** cảnh báo projected_below_rop/threshold_warning với predicted_threshold_date đã qua hàm thuần/simulation/worker, DTO/filter/CSV và verifier độc lập. Giữ ROP tại decision origin, chỉ receipts đã biết trước Q mới, strict < trong N ngày; metric threshold riêng depletion.242Python BE/M2 (28ca mới),34React chạy1worker/build/pipcheck/API-worker smoke đạt;9inventory golden/M2 parity và1024protectedhash nguyên. DB app đã backup/nâng0003_threshold, hash mọi cột cũ13bảng/3run nguyên, schema0diff. Commit mã14b18415014ee2867fac436e6bd7530d74b12188 đã push thường, remoteSHA khớp và2workflowCI completed/success; bước13–15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật chứng minh45%.

<a id="threshold-tests-step12"></a>
## Kiểm bước12 thực chạy — 26/10/2026

Baseline HEAD8233a96 ở source snapshot ignored:214Python đạt. Sau thay đổi242Python/0failure/error/skip, thêm28ca trong test_threshold_alerts.py: ROP−1/=ROP/+1,0, N/N+1/14, horizon không hợp lệ, receipts/ETA/causal, hai item với ROP riêng, dedup/current-low riêng, confusion/exclusion/null,3worker kind/manifest/API/filter/CSV, tamper ngày/xóa tín hiệu/mẫu số và migration/check/unique/downgrade an toàn. Verifier tự dựng projection từ frozen forecast/ledger/orders/policy, không gọi helper sản xuất để làm kỳ vọng.

9golden tồn so mọi trường legacy sau khi loại đúng phần additive bước12; fixture cũ không sửa. OpenAPI/DDL golden vẫn giữ, contract chỉ loại đúng trường/filter/DTO/check được phép thêm. M2 parity1e-8 giữ.34React đạt khi chạy npm test -- --maxWorkers=1; lượt chạy song song ban đầu33/34 do timeout5000ms, không sửa FE/test timeout. Build/pipcheck/API-worker smoke đạt,1024protectedhash nguyên. [Bàn giao đầy đủ](../../docs/development.md#handoff-chg068-step12).

**CHG-073 — 25/10/2026, lượt này chỉ Markdown:** bổ sung [mục tiêu làm việc R07≥45%](../../docs/requirements.md#r07-target-chg073) theo lời mentor được người dùng thuật lại; tính bắt buộc/phạm vi còn cần làm rõ. Chưa thêm/sửa test code hoặc chạy replay mới. Các ca CHG-073 bên dưới là kỳ vọng cần kiểm khi được giao kỹ thuật, không phải kết quả đã chạy; bước12–15 chưa bắt đầu, R07/T14 chưa nghiệm thu.

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

**Bổ sung CHG-073 — ca kiểm dự kiến, chưa thực thi trong lượt MD:**

| Ca | Cách kiểm khi được giao kỹ thuật | Kỳ vọng |
|---|---|---|
| Mục tiêu45% | Counts giả44/100,45/100,46/100 sau kiểm điều kiện báo trước≥7ngày | Lần lượt dưới/chạm/vượt mục tiêu làm việc; không dùng làm bằng chứng dữ liệu thật hoặc ngưỡng nghiệm thu đã chốt. |
| Không sự kiện | Event denominator0 | Tỷ lệ null; không nhận đạt45% bằng0/0 hoặc mặc định100%. |
| Thời gian báo trước | Có cảnh báo ở origin, ngày cạn trong replay D+6/D+7; giữ ca D+6 trong mẫu số | D+6 không tính sớm, D+7 được tính; không dùng ngày cạn dự báo thay ngày cạn replay để chấm thời gian báo trước. |
| N khác mốc7ngày | Tín hiệu xuống ROP trong N ngày, chưa có dự báo cạn | Đánh giá cảnh báo ngưỡng riêng; không tự tăng tử số depletion cũ hoặc nhận N=7 là đạt báo trước≥7ngày. |
| Tăng safety | Cùng source/forecast/tồn đầu/receipts/origin, alert replay không đặt mới | Đường tồn/ngày cạn/metric depletion giữ nguyên; ROP/đề nghị nhập có thể đổi. Không coi tăng SS là bảo đảm đạt45%. |
| Đổi tập sự kiện | Thay cover/tồn đầu/receipts hoặc origin | Báo riêng config/version/hash, numerator/denominator và sự kiện/ca loại thay đổi; không gọi là cải thiện trên cùng mẫu. |
| Tái lập và phạm vi | Đối soát event đầu tiên/item/cửa sổ, counts toàn lượt và bộ lọc bảng | Giữ mẫu số, không bỏ ca D+1…D+6; ≥45% không suy thành yêu cầu cho từng tuyến/SKU; khóa cách đánh giá trước run mới. |

Baseline986/2.867 và trần thời điểm1.317/2.867=45,936519% là số lịch sử. Mốc45% trên cùng tập cần1.291ca, thêm305ca; không điều chỉnh forecast/policy theo actual test cũ để ép số. Báo precision/recall, số muộn, coverage/ca loại và sai số ngày cạn cùng tỷ lệ. [Nguồn và giới hạn CHG-073](../../docs/review-log.md#chg073).

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
