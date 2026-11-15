# PLAN khảo sát và cải tiến SIGMA từ main

Ngày lập: **14/11/2026, Asia/Saigon**.

**Cập nhật sau khi nhận góp ý:** Người dùng đã gửi yêu cầu UI, QR, auth, ETA, Redis/worker, DB, snapshot, hash và allocation. [PLAN nâng cấp theo góp ý](PRODUCT_UPGRADE_PLAN_20261114.md) là kế hoạch tiếp theo; các mục “chưa nhận góp ý” bên dưới mô tả checkpoint khảo sát ban đầu, không còn là trạng thái hiện tại. Chưa triển khai code mới; D01–D03 trong PLAN nâng cấp còn chờ làm rõ.

## 1. Phạm vi và trạng thái

- Nguồn đã lấy: `https://github.com/khanhnguyenpham/Sigma.git`, nhánh `main`, commit **`2d0d5f1052a3a3bea1711e2635822ca3cc6f9915`**, ngày 13/11/2026, nội dung `Refine scenario alerts and update C00 evaluation`.
- Nhánh tài liệu: `codex/main-review-plan-20261114`, xuất phát đúng commit trên. Không chuyển lịch sử hoặc mã cũ từ những worktree trong hội thoại trước vào main mới.
- Thư mục project cũ không còn tại đường dẫn đã lưu. Lượt này clone mới main; không khôi phục CSV, database, backup, môi trường hoặc outputs cũ.
- **Đã khảo sát các điểm vào và luồng nghiệp vụ trọng tâm; chưa đọc kiểm chứng từng dòng của toàn bộ repo.** Những mục đọc sâu còn lại nằm trong bảng triển khai bên dưới.
- **Lượt hiện tại chỉ đọc mã và viết kế hoạch.** Không triển khai tính năng, cài dependency, khởi động app, ghi DB, enqueue job, refit, commit, push hoặc deploy.
- Góp ý mới trong nhóm chưa được gửi trong lượt này. Các vấn đề đề xuất từ khảo sát được ghi riêng, không nhận là yêu cầu mentor đã chốt. Phần phụ thuộc góp ý chỉ chốt sau khi có nội dung thực tế.
- Không lấy code, test được khai báo trong tài liệu hoặc JSON có nhãn `verified` làm bằng chứng ứng dụng vừa chạy thành công trên máy này.

## 2. Những gì thực sự có trong source

| Thành phần | Tệp đã đọc / điểm cần lần theo | Nhận định từ mã, không phải nghiệm thu runtime |
| --- | --- | --- |
| Audit dữ liệu | [src/data.py](../../src/data.py), [src/common.py](../../src/common.py), [src/evaluation.py](../../src/evaluation.py) | Audit schema 20 cột, UTC, quantity, duplicate, trạng thái; phân biệt actual thiếu và số 0; top train; MAPE/MAE/WAPE/bias. Không bỏ audit chỉ để app dễ chạy. |
| Điểm khởi động | [src/start_demo.py](../../src/start_demo.py) | Điều khiển runtime demo riêng, kiểm fingerprint/build/readiness và PostgreSQL; phụ thuộc bộ prepared/runtime nằm ngoài Git. Không phải launcher chạy được ngay sau clone. |
| M2 / dự báo nền | [registry](../../M2/models/registry.py), [forecast service](../../web/backend/src/modules/forecasting/service.py), [allocation](../../web/backend/src/modules/forecasting/allocation.py) | Backend dùng lại mã M2; có khóa lựa chọn theo validation, quan hệ nguồn/forecast cha, phân bổ xuống item/ngày. Demo vận hành H14; không tự thêm lại giao diện Tổng30. |
| API | [main.py](../../web/backend/src/main.py), [settings](../../web/backend/src/core/settings.py), [run schema](../../web/backend/src/modules/runs/schemas.py) | FastAPI ghép catalog/config/run/inventory/purchasing/alerts/reporting. Database PostgreSQL; local/demo có validation riêng. API không fit mô hình trực tiếp trong request. |
| Queue và worker | [run service](../../web/backend/src/modules/runs/service.py), [worker.py](../../web/backend/src/worker.py) | Idempotency-Key, kiểm nguồn cha, freeze cấu hình, nhận job, heartbeat, xử lý lỗi, verifier trước complete và manifest/hash. Chưa kiểm restart/concurrency trên môi trường lượt này. |
| Freeze cấu hình | [configuration/context.py](../../web/backend/src/modules/configuration/context.py) | Chốt policy, kịch bản, lịch cung cấp và kho nhận; không dùng cấu hình live để viết lại run cũ. |
| Nghiệp vụ tồn | [inventory/service.py](../../web/backend/src/modules/inventory/service.py), [simulation.py](../../web/backend/src/modules/inventory/simulation.py), [trade.py](../../web/backend/src/modules/inventory/trade.py) | Có SS, ROP, IP, lượng lô, ETA, nhận/bán/chốt tồn, projection/replay và quyền mua/bán. Giữ đường đọc snapshot lịch sử. |
| Cảnh báo | [alerts/service.py](../../web/backend/src/modules/alerts/service.py), [EarlyWarningResult](../../web/frontend/src/components/alerts/EarlyWarningResult.tsx), [AlertOpportunity](../../web/frontend/src/components/alerts/AlertOpportunity.tsx), [C00Evaluation](../../web/frontend/src/components/alerts/C00Evaluation.tsx) | Có tỷ lệ đủ cơ hội, tỷ lệ toàn đợt cạn, precision/recall; phân biệt policy replay, alert replay và khối C00 cố định. Chặn bán/gián đoạn được theo dõi riêng. |
| React | [useAppContext](../../web/frontend/src/hooks/useAppContext.ts), [Inventory](../../web/frontend/src/pages/Inventory.tsx), [Products](../../web/frontend/src/pages/Products.tsx), [Scenarios](../../web/frontend/src/pages/Scenarios.tsx), [useResource](../../web/frontend/src/hooks/useResource.ts) | Có URL context, danh sách kho, lọc, cấu hình sản phẩm, phiên bản kịch bản, trạng thái job, kết quả và CSV. Cần test tương tác trình duyệt, không chỉ đọc JSX. |
| Database và CI | [backend pyproject](../../web/backend/pyproject.toml), [CI M3](../../.github/workflows/m3.yml), [frontend package](../../web/frontend/package.json) | Migration đến 0009 hiện có trong cây mã. CI định nghĩa PostgreSQL test riêng, backend, M2 regression Windows, React và build; chưa kiểm CI online của SHA hiện tại. |

**Ranh giới cấu trúc:** root `src/` chủ yếu là audit, cấu hình, metric và launcher. Mã ứng dụng nằm ở `web/frontend/src/` và `web/backend/src/`; mô hình nằm trong `M2/models/`. Không gom mọi thứ vào root `src/` hoặc đổi tên toàn bộ trước khi có baseline.

## 3. Thay đổi mới cần giữ khi tiếp tục

| Nội dung | Bằng chứng đọc được | Quy tắc cho bước sau |
| --- | --- | --- |
| Tồn đầu dùng 28 ngày lịch sử | `initial_stock` trong simulation và freeze; [bàn giao](../development.md#handoff-28-day-stock-and-lot-trial) | Phân biệt **28 ngày lấy bình quân lịch sử** với **3/7/14 ngày phủ tồn** của kịch bản. Không nói tồn đầu đã đổi thành 28 ngày phủ. Giữ tương thích snapshot có fallback 90 ngày. |
| Lượng nhập demo 15 | [bàn giao 13/11](../development.md#handoff-base-lot15-demo) | Đây là cấu hình của runtime demo được nhật ký ghi nhận; không suy ra mọi clone hoặc mọi supplier có hợp đồng lượng 15. Không dùng lại lời demo cũ nhập 5/10 khi chưa đối chiếu run. |
| C00 mới | [JSON đang dùng ở FE](../../web/frontend/src/data/c00-forecast-floor-evaluation.json) | 107/228 = 46,93% trên ca đủ cơ hội; 107/229 = 46,72% toàn đợt cạn; precision 76,42%, recall 93,45%. Chỉ là dữ liệu tổng hợp được source đóng gói, chưa tái lập ở lượt này. |
| Chặn bán tách đoạn theo dõi | [bàn giao](../development.md#handoff-policy-sales-block-recall), `test_policy_alert_evaluation.py` | Không coi không bán được do nhà mạng là thiếu hàng. Không ghép cảnh báo trước đoạn chặn bán với đợt cạn sau khi mở bán lại theo cách thiếu căn cứ. |
| Chạy lại hai kịch bản v3 | [bàn giao](../development.md#handoff-supply-v3-rerun) | Nhật ký mới nêu run `36dd4931`, `a1591ee5`, cùng mốc 31/10/2025. Chưa có DB/artifact local để xác minh. Không dùng link/run cũ trong hội thoại làm nguồn hiện hành. |

## 4. Các điểm ưu tiên từ khảo sát

Các mục dưới đây là **cần kiểm hoặc đề xuất**, không mặc định là bug đã tái hiện.

1. **P0 — dựng lại baseline chạy được.** Clone mới thiếu CSV, DB, prepared runtime, `.env`, `node_modules`; Python shell hiện là 3.14.7 trong khi backend khai báo `>=3.12,<3.13`. Có mã không đồng nghĩa mở được app.
2. **P0 — chốt nghĩa của chỉ số.** Có đồng thời tỷ lệ đủ cơ hội và tỷ lệ toàn bộ đợt cạn. Tên thẻ, mẫu số, CSV và báo cáo phải giải thích thống nhất; không nâng nghiệm thu R07 chỉ vì đổi cách hiển thị tỷ lệ.
3. **P0 — truy vết cấu hình.** Xác minh tồn đầu 28 ngày lịch sử, policy lượng 15 có ngày hiệu lực, kho nhận và lịch ngừng đã được freeze đúng; run lịch sử tiếp tục đọc bằng quy tắc của chính nó.
4. **P1 — luồng chọn kế hoạch và bộ lọc.** Hội thoại trước có khó khăn với ô trạng thái và bộ lọc còn giữ khi đổi trang. Mã đã có reset khi đổi run/kho. Cần tái hiện trên main mới trước khi quyết định sửa; phân biệt thẻ KPI với ô chọn.
5. **P1 — tổng/bảng/CSV cùng phạm vi.** Mã Inventory chủ động dùng phạm vi riêng cho summary; cần xác định rõ thẻ nào phản ánh cả kho và thẻ nào phản ánh bộ lọc/trang bảng, tránh người dùng hiểu tổng thay đổi sai.
6. **P1 — tách giá trị cấu hình và giá trị tính.** Số ngày tồn an toàn khác lượng SS; ngưỡng tối thiểu khác ROP tính tại ngày; khuyến nghị khác lô đã đặt. UX phải nói rõ nhưng không đổi công thức để minh họa cho đẹp.
7. **P1 — tài liệu hiện hành.** TASK có cập nhật 13/11 nhưng đầu PROJECTMAP/IMPLEMENTATION và nhiều hướng dẫn còn checkpoint cũ. Chỉ bổ sung mục hiện hành và đánh dấu lịch sử; không xóa lịch sử kiểm chứng.
8. **P2 — vận hành/chia sẻ.** Launcher vẫn gắn các thư mục runtime lịch sử. Cần quy trình chuẩn bị demo có thể tái lập và báo thiếu thành phần rõ ràng trước khi bàn deploy; không mặc định tunnel cũ còn sống.

## 5. Tiếp nhận góp ý trong nhóm

Mỗi góp ý phải được ghi thành một hàng, giữ nguyên nội dung gốc khi có nguồn:

| ID | Nội dung / nguồn | Luồng, tệp liên quan | Phân loại | Điều kiện nghiệm thu | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| FB-001 | Đã nhận danh sách góp ý ngày 14/11; xem ma trận15 nhóm trong PLAN nâng cấp | Auth, QR, ETA, UI, DB, queue, allocation, hosting | Mở rộng sản phẩm và cải tiến | Ca N01–N12, cùng các quyết định D01–D07 | Đã lập PLAN, chưa triển khai |

Quy trình: góp ý gốc → đối chiếu code và hành vi → phân loại lỗi/UX/thay đổi nghiệp vụ/ngoài phạm vi → xác định test → mới triển khai. Không coi một đề xuất trong PLAN là xác nhận mentor. Nếu góp ý đã được main giải quyết, ghi tệp/test và kiểm lại, không tạo chức năng trùng.

Những điều cần chốt **nếu góp ý tác động đến chúng**: mẫu số nào là tiêu chí nghiệm thu báo sớm; lượng nhập cố định 15 là giả định demo hay quy tắc mới; có mở lại Tổng30 trên web không; có cần triển khai độc lập khỏi máy cá nhân không. Không hỏi lại các quyết định đã có chỉ để bắt đầu đọc/test.

## 6. Thứ tự triển khai và cổng kiểm

| Giai đoạn | Công việc cụ thể | Tệp/luồng chính | Kết quả cần bàn giao | Điều kiện chuyển bước |
| --- | --- | --- | --- | --- |
| **S0 — khảo sát** | Ghi SHA, cấu trúc, code path, thay đổi 13/11 và giới hạn local; đối chiếu góp ý khi nhận được | Tài liệu này, README, TASK, source map | Danh sách đã có/cần kiểm/đề xuất; ma trận FB | **Đã làm phần khảo sát; FB còn chờ.** Chưa nhận đã kiểm toàn bộ mã hoặc chạy app. |
| **S1 — môi trường test** | Tạo môi trường Python 3.12 đúng pin và FE theo lock; PostgreSQL test riêng; kiểm Alembic và entry point | requirements, backend pyproject, CI, tests/conftest | Baseline dependencies, lệnh thực chạy, SHA/schema và test log | DB tên `sigma_m3_test`, role không superuser; không dùng DB demo cho fixture TRUNCATE. Không tự tải raw hoặc chuẩn bị public demo. |
| **S2 — đọc sâu và kiểm nghiệp vụ** | Lần đầy đủ freeze → simulation → verifier → reporting; kiểm 28/90 ngày, policy theo ngày, kho nhận, ba kinds và lifecycle | configuration/context; inventory; runs/*verification; reporting; alerts | Từng ca tính tay + test tích hợp và bảng chênh lệch | Run mới đúng quy tắc, run cũ không bị viết lại. Nếu sửa metric, phải giữ phiên bản/đối chứng và nguồn quyết định. |
| **S3 — cải tiến luồng sử dụng** | Tái hiện góp ý về chọn kế hoạch, lọc, trạng thái, thông báo, nhận diện phạm vi và giải thích quyết định; sửa theo từng luồng đã chốt | useAppContext, ContextFilters, Inventory, Products, Scenarios, components/alerts, useResource | Luồng xem/chỉnh/lưu/chạy rõ ràng, loading/error/empty không hiển thị số cũ như mới | Test React cho hành vi liên quan, TypeScript/build, browser desktop và màn hình hẹp; không tạo lại chức năng đã có. |
| **S4 — kiểm tích hợp bằng synthetic** | Chạy ba kinds qua API/worker; đổi cấu hình live sau enqueue; kiểm CSV, phân trang, retry, idempotency, stale request | API → DB test → worker → verifier → FE/CSV | Bảng UAT bên dưới, artifact synthetic, ảnh và kết quả đối chiếu cùng run/ngày/bộ lọc | Không còn lỗi nghiêm trọng trong phạm vi FB đã chốt; thiếu dữ liệu được báo thiếu, không tự điền 0. |
| **S5 — kiểm demo thực tế có kiểm soát** | Nếu có bộ runtime được phép sử dụng: backup, ghi baseline, mở bản copy, đọc run hiện hành và luyện luồng báo cáo | src/start_demo.py, demo_stack, DEMO_RUNTIME, connection.json | URL local thực tế, danh mục run đã xác minh, bộ hướng dẫn đúng số mới | Không sửa trực tiếp DB/run đã chốt. Chỉ chạy lại/refit/kết nối nguồn khi phạm vi tiếp theo cho phép. Không áp số trong hội thoại cũ cho app mới. |
| **S6 — bàn giao** | Đồng bộ hướng dẫn hiện hành, TASK/PROJECTMAP, bằng chứng và giới hạn; chuẩn bị diff nhỏ theo hạng mục | README, M3/IMPLEMENTATION, DEMO_WEB_GUIDE, tài liệu liên quan FB | Danh sách tệp, kiểm thực chạy, lỗi còn lại, hướng dẫn mở app và rollback | Commit/push/deploy chỉ khi được giao ở lượt triển khai; rà payload, xác minh SHA/CI nếu có push. Không tự tạo Word/slide. |

**Thứ tự ưu tiên:** S1 → S2 → S3 → S4. S5 phụ thuộc runtime thật; S6 theo phạm vi bàn giao. S2 và S3 có thể chia thành thay đổi nhỏ theo góp ý, nhưng không đổi UI của một công thức chưa được xác minh.

Không mở lại dự án mô hình lớn chỉ để sửa nhãn hoặc lọc. Chỉ refactor khi đã có test bảo toàn hành vi; không đổi tên hàng loạt module/schema/route để làm cây mã có vẻ gọn.

## 7. Bộ ca bắt buộc cho lần triển khai tiếp

Các ca là kế hoạch kiểm, **chưa chạy trong lượt lập tài liệu**. Tái dùng test hiện có khi đã bao phủ, chỉ bổ sung cho hành vi còn thiếu.

| Ca | Điều cần kiểm | Nơi bắt đầu / bằng chứng mong đợi |
| --- | --- | --- |
| U01 | Chọn một run complete, đổi kho/item/ngày, quay lại bằng Back hoặc reload; filter cũ không khiến người dùng hiểu nhầm tổng | `warehouse-navigation`, `context-transition`, useAppContext; ảnh + bảng scope |
| U02 | Chọn Cần đặt thêm thực sự lọc theo điều kiện đặt; phân biệt dưới ROP nhưng pending đủ hoặc quyền nhập bị chặn | Inventory, reporting; `test_results_api`, `threshold-presentation`; đối chiếu API/UI/CSV |
| U03 | SS làm tròn đúng; tồn = ROP không kích hoạt; tồn < ROP nhưng IP >= S thì Q=0; Q lấy lô cố định khi đủ điều kiện | `test_configurable_inventory`, `test_fixed_order_quantity`, ca tính tay |
| U04 | Lịch sử 28 ngày đều 0 cho tồn đầu 0; snapshot 90 ngày cũ đọc theo quy tắc cũ; thiếu ngày quan sát không thành 0 | initial_stock; `test_policy_replay_initial_stock_uses_frozen_history_rule` |
| U05 | Ngày đặt D, ETA D+7; nhận đầu ngày đúng một lần; không nhận lô tương lai hoặc đếm pending thành tồn hai lần | simulation/service, `test_simulation`, `test_inventory_parity` |
| U06 | Cùng đầu vào nhưng ba loại công việc có hành vi tạo lô khác nhau; stock_projection không tự coi đề xuất là đã đặt | `test_scenario_workspace`, worker/verifier; ba run synthetic |
| U07 | Sửa policy hoặc kho nhận sau enqueue không đổi run cũ; ngày hiệu lực 2026 không viết lại kế hoạch 2025 | `test_policy_persistence`, `test_receiving_warehouse`, `test_receiving_migration` |
| U08 | Ngừng nhập nội bộ: chặn đặt mới từ ngày hiệu lực nhưng vẫn bán tồn/nhận lô cũ; ngừng nhà mạng: chặn mua/bán và xét ETA | `test_scenario_supply`, `test_trade_lifecycle`, `test_trade_simulation` |
| U09 | Lịch ngừng chỉ tác động phiên bản kịch bản; lưu không tự chạy; tạo phiên bản mới giữ kết quả cũ; xóa/khôi phục không mất lịch sử | configuration API; `scenario-workspace`, `test_scenario_supply` |
| U10 | Báo sớm: tử số/mẫu số đủ cơ hội và toàn đợt hiển thị riêng; mẫu số 0 hiện chưa xác định; bộ lọc bảng không đổi metric toàn lượt | `alert-opportunity`, `early-warning-result`, `c00-evaluation`, backend alerts |
| U11 | Bán bị chặn không thành shortage; cảnh báo trước/sau resume không bị ghép sai; ghi riêng theo dõi chưa đủ và có hàng bổ sung | `test_policy_alert_evaluation`, trade/reporting và `EarlyWarningResult` |
| U12 | Hai request cùng key không tạo hai job; cùng key nhưng khác body trả 409; restart/interrupted và retry tạo lượt mới có liên kết; chưa complete không trình bày là kết quả cuối | `test_postgres_api`, FE `demo-retry`, worker/run service |
| U13 | CSV cùng run/ngày/kho/item/state với bảng, xuất đủ phạm vi thay vì chỉ trang đầu; actual thiếu để trống | reporting/export, `test_forecast_origins_api`, `forecast-comparison`, results API |
| U14 | Mạng chậm/lỗi/đổi run liên tục: request cũ bị hủy, không hiện kết quả sai context; thao tác bàn phím với ô trạng thái | `http`, `resilience`, `context-transition`, `useResource`, browser |
| U15 | Máy mới thiếu prepared/DB/build: báo rõ thành phần thiếu; start/status/stop chỉ quản lý tiến trình sở hữu; credential/raw không đi vào bundle | `test_demo_entrypoint`, `test_demo_runtime`, launcher; không cần mở tunnel để kiểm |

## 8. Lệnh kiểm dự kiến

Chỉ chạy sau S1 với đúng môi trường đã chuẩn bị. Chạy baseline trước sửa; sau sửa chạy nhóm phù hợp rồi mới mở rộng nếu cần. Các lệnh dưới đây **chưa được chạy trong lượt lập PLAN**.

```powershell
# Ở project root, trong Python 3.12 đúng dependency lock và đã cài editable backend.
python -m pip check
python -m cli --help
python -m worker --help
python -B -m pytest web/backend/tests
python -B -m pytest tests M2/models/tests

# Trong web/frontend, với dependency từ package-lock.json.
npm ci
npm test
npm run build
```

Backend integration đòi `M3_TEST_DATABASE_URL` trỏ tới **sigma_m3_test** riêng. Fixture migrate và TRUNCATE; không trỏ vào `sigma_demo` hoặc database đang trình diễn. Không ghi URL/mật khẩu thực vào PLAN hoặc commit. Không bỏ qua test PostgreSQL rồi gọi toàn bộ backend đạt.

## 9. Tiêu chí hoàn thành kế hoạch triển khai

1. Mỗi FB đã nhận có phạm vi, tệp, trạng thái và ca nghiệm thu; yêu cầu còn thiếu ghi rõ, không suy diễn.
2. Baseline và kết quả sau sửa được ghi theo đúng SHA/môi trường; không lấy số test hoặc run trong nhật ký 13/11 làm số của lần chạy mới.
3. Kết quả UI/API/CSV/verifier đồng nhất trong phạm vi UAT; 3 loại công việc và 2 loại ngừng cung cấp được phân biệt.
4. Công thức, mẫu số, profile, dữ liệu gốc và snapshot được bảo toàn hoặc thay đổi có lý do/version được chấp thuận.
5. Tài liệu mô tả được current code; kết quả nghiên cứu hồi cứu tách với bằng chứng ứng dụng và tiêu chí được mentor xác nhận.
6. Không nhận “100%”, R05/R07/T14 đã đóng hoặc sản phẩm đã public chỉ vì source có đủ màn hình hoặc JSON có tỷ lệ cao.

## 10. Bàn giao lượt lập PLAN

- Main đã clone đúng SHA ở mục 1; không có bản local cũ tại đường dẫn để cập nhật trực tiếp.
- Đã đọc các luồng trọng tâm và đối chiếu test/doc liên quan; không chạy app, test suite, model hoặc database.
- Kiểm trong lượt này: cú pháp Python bằng AST, tính hợp lệ JSON, liên kết/cấu trúc của tài liệu mới và diff tài liệu. Đây là kiểm tĩnh, không chứng minh test hoặc ứng dụng chạy đúng. Kết quả được ghi ở thông báo bàn giao của lượt này.
- Chỉ sửa tài liệu PLAN và thêm chỉ dẫn từ TASK/PROJECTMAP/PLAN gốc. Không đụng các tệp S25/COMMIT_BLOCK_PLAN được khoanh giữ hoặc dữ liệu ngoài repo.
- **Bước tiếp hiện tại:** dùng PLAN nâng cấp theo góp ý, làm rõ D01–D03 và chuẩn bị baseline. Phạm vi auth/QR/Redis/ETA mới thay cho giả định chỉ cải tiến demo cũ; các chi tiết phụ thuộc quyết định chưa được coi là đã chốt.
