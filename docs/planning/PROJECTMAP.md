# Bản đồ project SIGMA

**CHG-074 mốc 3 — 27/10/2026, local đạt:** người dùng giao riêng verifier độc lập từ `253590b` trên nhánh thử. Verifier tự dựng lại tồn/SS/ROP/đặt/ETA/projection/episode/metric, không gọi helper nghiệp vụ của runner làm kỳ vọng. 317 Python (46ca mới), pipcheck/help/synthetic CLI19configs đạt; receipt synthetic idempotent, artifact cũ nguyên. 14bảng và1.231hash protected nguyên. Chưa chạy validation/test thật hoặc chọn cấu hình; mốc4–5 chờ giao tiếp. R07/T14 chưa nghiệm thu. [Chi tiết](../../M3/docs/research.md#inventory-alert-safety-step3).

**CHG-074 mốc 2 — 27/10/2026, hoàn tất:** người dùng giao riêng CLI và phép tính A/B/C/D trên `codex/alert-safety-stock-experiments` từ `467c6a3`. Có 19 cấu hình, 26 ca mới; 271 Python BE/M2 và pip check đạt. CLI/snapshot PostgreSQL chỉ đọc đã kiểm bằng synthetic; đầu ra `calculated_unverified`, verify hiện chỉ kiểm toàn vẹn artifact. Chưa chạy validation/test thật, chọn cấu hình hoặc viết verifier độc lập; mốc 3–5 chờ giao tiếp. Commit `8436eaabd502b6aaa078bde3e76ebe97960a953f` đã push thường, remoteSHA khớp và hai workflow CI completed/success. Giữ baseline986/2867, R07/T14 chưa nghiệm thu. [Chi tiết](../../M3/docs/research.md#inventory-alert-safety-step2).

**CHG-074 mốc 1 — 27/10/2026, hoàn tất:** đã tạo nhánh `codex/alert-safety-stock-experiments` từ `a2241dbe`, lưu kế hoạch/protocol và kiểm lại hai đối chứng bằng verifier độc lập, DB chỉ đọc. A giữ 986/2.867, loại 1.099; policy đáp ứng 14.437/15.968, thiếu 1.531. 245 Python đạt, 14 bảng và 1.184 hash protected nguyên. Commit `f1bd4de2d478f96f2eeb5e0979d807b3ae1e6319` đã push thường, remoteSHA khớp và hai workflow CI completed/success. Lượt này dừng sau mốc 1; mốc 2–5 chưa bắt đầu. Chưa tạo replay run mới hoặc triển khai CLI/B/C/D; R07/T14 chưa nghiệm thu. [Kế hoạch](PLAN.md#chg-074).

**CHG-068 bước 15 — 27/10/2026, hoàn tất:** đã chạy hai replay thật mới với cấu hình cơ sở khóa trước kết quả; worker và verifier độc lập đạt. Policy fill 90,4121%, thiếu 1.531/15.968; depletion báo sớm 986/2.867 = **34,391350%, chưa đạt mục tiêu làm việc 45%**. Metric xuống ROP giữ riêng (TP101/FP89/FN0/TN619). 245 Python, 50 React, build/pip check, API/CSV/browser đạt; 1.038 hash protected, 140 artifact sealed và hàng cũ của 13 bảng nghiệp vụ + Alembic nguyên. Schema 0003_threshold/0diff; chỉ thêm hai run local, không refit/tuning. R07/T14 chưa nghiệm thu. Commit `2658b8116accbed4354fdc18b55d7ed52f436f7c` đã push thường, remoteSHA khớp và2workflowCI completed/success. [Bằng chứng và cách kiểm lại](../development.md#handoff-chg068-step15). Các checkpoint bên dưới giữ vai trò lịch sử.

**CHG-068 bước14 — 26/10/2026, hoàn tất:** sau cổng13 mã73d6f39/remoteSHA/2CI success, người dùng giao14. React hiển thị ROP/SS/mode/N, ngày xuống ROP riêng ngày cạn, lý do/đường projection/bảng UTC; filter/export và metric threshold riêng depletion. Workspace thêm warning_items/projected_below_rop_items đếm item duy nhất; inventory API/CSV đọc5tham số từ policy frozen, công thức fixed hiển thị đúng.245Python (3ca mới),50React (7ca mới,1worker)/build/pipcheck và browser desktop/mobile390px trên2run synthetic đạt;1027protectedhash và3app run nguyên, schema0003_threshold giữ. Commit mã37c4525b90cb361d8eeabc23c46cfc82fb39f8dc đã push thường, remoteSHA khớp và2workflowCI completed/success; bước15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật mới chứng minh45%.

**CHG-068 bước13 — 26/10/2026, hoàn tất:** sau cổng bước12 mã14b1841/remoteSHA/2CI success, người dùng giao tiếp tục bước13. Form React policy/scenario có SS days/volatility, ROP fixed/forecast, lookback/factor/N; override trống kế thừa,0giữ đúng, chỉ trường phù hợp mode hiển thị/gửi. Giữ version/effective date/conflict/cấu hình cũ; bảng policy phân biệt tham số đang áp dụng.43React (9ca mới, chạy mặc định và1worker)/build/browser synthetic save-reload-Escape-focus đạt;1029protectedhash và3app run nguyên, schema0003_threshold giữ. 242Python BE/M2/pipcheck đạt; commit mã73d6f398de4fb069ab2484a85cecf71bc345147c đã push thường, remoteSHA khớp và2workflowCI completed/success; bước14–15 chưa bắt đầu, R07/T14 chưa nghiệm thu.

**CHG-068 bước12 — 26/10/2026, hoàn tất:** cảnh báo projected_below_rop/threshold_warning với predicted_threshold_date đã qua hàm thuần/simulation/worker, DTO/filter/CSV và verifier độc lập. Giữ ROP tại decision origin, chỉ receipts đã biết trước Q mới, strict < trong N ngày; metric threshold riêng depletion.242Python BE/M2 (28ca mới),34React chạy1worker/build/pipcheck/API-worker smoke đạt;9inventory golden/M2 parity và1024protectedhash nguyên. DB app đã backup/nâng0003_threshold, hash mọi cột cũ13bảng/3run nguyên, schema0diff. Commit mã14b18415014ee2867fac436e6bd7530d74b12188 đã push thường, remoteSHA khớp và2workflowCI completed/success; bước13–15 chưa bắt đầu, R07/T14 chưa nghiệm thu, chưa có replay thật chứng minh45%.

**CHG-073 — 25/10/2026, bổ sung tài liệu:** [R07 mục tiêu làm việc45%](../requirements.md#r07-target-chg073), [PLAN](PLAN.md#chg073) và đặc tả chức năng/kiểm/bảng nghiệm thu được đồng bộ; nguồn là mentor do người dùng thuật lại, tính bắt buộc/phạm vi còn cần làm rõ. Không đổi cây mã/API/DB/cấu hình hoặc chạy replay. Bước11 đã hoàn tất; bước12–15 chưa bắt đầu, R07/T14 chưa nghiệm thu. [Bàn giao](../development.md#handoff-chg073).

**Tính policy bước11 CHG-068 — 25/10/2026:** inventory/service có2mode SS và2mode ROP, simulation chọn lịch sử causal theo decision origin, independent verifier tự đối soát từng dòng. Mode đã lưu từ bước10 nay chạy được, không guard tạm; API/schema13bảng/FE/default legacy giữ, cấu trúc web của CHG-072 giữ. [Công thức và ví dụ](../../M3/docs/01-functional-spec.md#configurable-calculation-step11), [kiểm và bàn giao](../development.md#handoff-chg068-step11). Bước12–15 chưa bắt đầu; các trạng thái trước bước11 bên dưới là checkpoint lịch sử.

**Hiện hành CHG-072 — 25/10/2026:** frontend ở web/frontend, configs/research code/env ở web/backend; M3 chỉ giữ Markdown và protocol nghiên cứu. Backend serve/build/launcher/CI đã đổi đường; tên env/DB, FE/nghiệp vụ/API/13bảng/snapshot giữ nguyên. [Cây thực](../../M3/docs/05-source-architecture.md#web-layout-chg072), [bàn giao](../development.md#handoff-chg072). Bước11–15 chưa bắt đầu; các mốc đường M3/frontend/configs/research/env dưới đây là lịch sử trước chuyển vị trí, các lệnh chạy đã cập nhật.

**Backend bước10 CHG-068 — 25/10/2026:** configuration models/schemas/service/context lưu5tham số policy/override, migration0002_policy giữ13bảng. core/run_context diễn giải default của policy cũ trong bản sao; inventory/policy_at chặn mode chưa tính tới bước11. FE giữ nguyên bước9. [Bàn giao](../development.md#handoff-chg068-step10), [schema hiện hành](../../M3/docs/02-data-model.md#policy-persistence-step10). Bước11–15 chưa bắt đầu.

**Frontend sau bước9 CHG-068 — 25/10/2026:** FE vẫn M3/frontend; App ghép6pages với AppLayout/Sidebar/Header/ContextFilters, state/effect ở useAppContext. useConfiguration giữ ghi cấu hình; form policy/scenario và3drawer tách component. index.css giữ byte của styles.css, import tại main. Không dependency/nghiệp vụ mới. [Cây thực](../../M3/docs/04-frontend-spec.md#step9-actual), [kiểm và bàn giao](../development.md#handoff-chg068-step9). Backend/dữ liệu không đổi; bước10–15 chưa bắt đầu.

**Hiện hành CHG-068 bước7 — 25/10/2026:** đủ8module backend; inventory chứa ledger/event/phép tính/simulation/seeding/workspace, purchasing chứa Replenishment/receipt/workbench/CSV, alerts chứa model/project/metric/diagnostic/router. models.py chỉ giữ registry13model chung Base; api/services cũ đã bỏ source. Entry point/launcher/API/DDL và FE giữ nguyên. [Cây thực](../../M3/docs/05-source-architecture.md#step7-actual), [bàn giao](../development.md#handoff-chg068-step7). Bước8–15 chưa bắt đầu; các cây trước ở dưới là checkpoint lịch sử.

**Hiện hành CHG-068 bước6 — 25/10/2026:** backend đã tách modules/forecasting (model/import/forecast/allocation/M2 adapter), modules/runs (model/DTO/service/router/verification), modules/reporting (filter/read model/metric/CSV/monthly). Core có serialization dùng chung; worker/CLI/launcher giữ entry point. models.py còn registry13bảng và4model tồn; root schemas.py đã chuyển vào runs. [Cây thực](../../M3/docs/05-source-architecture.md#step6-actual). API/DDL/nghiệp vụ giữ nguyên; bước7–15 chưa bắt đầu. Các mốc cấu trúc bên dưới là checkpoint lịch sử.

**CHG-071 — cây backend mới:** web/backend/src gồm api/, core/, modules/, services/ và main.py/worker.py/cli.py/models.py/schemas.py trực tiếp. web/backend/scripts chứa6script API/worker/stack/load_env. Worker không tách service; namespace sigma_m3 đã bỏ theo yêu cầu mới, distribution sigma-m3 và DB/env giữ tên cũ. Root src/ vẫn M2; M3 giữ frontend/configs/research/env. [Cây mới](../../M3/docs/05-source-architecture.md#flat-backend-chg071).

**CHG-070 — vị trí code mới:** `web/backend/` là backend thực (src/sigma_m3, migrations, tests, requirements và pyproject); worker/CLI vẫn bên trong sigma_m3. `M3/frontend/`, `M3/configs/`, `M3/scripts/`, `M3/research/` giữ vị trí. Đích FE sau này: web/frontend với cấu trúc pages/layouts/components CHG-069. [Cây hiện hành](../../M3/docs/05-source-architecture.md#web-layout-chg070); [7Markdown đã bỏ](../review-log.md#removed-docs-chg070).

**CHG-069 — cây FE dự kiến mới:** src gồm components/config/hooks/layouts/pages/services/types/utils và App.tsx/main.tsx/index.css. [Trách nhiệm và ánh xạ](../../M3/docs/04-frontend-spec.md#frontend-target-chg069). Chưa triển khai: cây thực vẫn App.tsx/main.tsx/styles.css, api/, components/, pages/. Không có stores/lib/src-docs/examples; assets chỉ tạo khi có tệp dùng thực. Bước6–15 chưa bắt đầu.

**CHG-068 bước5 — 24/10/2026:** người dùng yêu cầu làm riêng bước5 sau checkpoint `992b8f5`. Đã tách core/catalog/configuration và rút main391→45dòng; giữ26route/OpenAPI đầy đủ, DDL13bảng và giao dịch/version/snapshot. Local107Python/26React/build/pipcheck/CLI/import/Alembic/smoke đạt,845protectedhash nguyên. Commit mã `db6c1d5` đã push, SHAremote khớp và cả2workflowCI completed/success. Bước5 hoàn tất; bước6–15 chưa bắt đầu. [Cây thực core/module](../../M3/docs/05-source-architecture.md#step5-actual). models.py còn registry/8model, schemas.py còn RunCreate; api/services còn phần bước6–7. FE không đổi. Hiện trạng sau bước4 ở dưới là checkpoint trước refactor.

**Hiện trạng sau bước4 CHG-068:** worktree `m3-modular-config/Sigma`, nhánh `m3-implementation`. M3 dùng React→HTTP→FastAPI/PostgreSQL; đã gỡ M3/streamlit, cloud bridge/build và M2/final_app.py, scripts/start_m2.ps1, .streamlit/config.toml cùng dependency. M2 CLI/notebook/HTML giữ nguyên. BE còn main/models/schemas/api/services; FE còn App/pages/components/api; cây module/feature chỉ là đích bước5–9, chưa triển khai. Dừng theo người dùng, [tiếp tục từ bước5](../development.md#handoff-chg068-step4).

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo pages, layouts và component dùng chung (CHG-069), sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.


[Kế hoạch CHG-068 và cổng từng bước](PLAN.md#chg-068).

**CHG-067/E99 — 21/10/2026, hoàn thiện bản nộp:** bổ sung phục hồi khi tải lỗi/mất kết nối, giới hạn chờ RPC, màn hình lỗi có lối thử lại, làm mới trong phiên, hướng dẫn nghiệp vụ, điều hướng Back/Escape và hỗ trợ bàn phím. Tạo phương án online chỉ chọn93ngày có đủ closing920item và forecast H14 (30/09–31/12/2025).120Python+31React đạt; dữ liệu/metric/run khóa giữ nguyên. [Hướng dẫn nộp và kiểm sản phẩm](../../M3/SUBMISSION.md). Đã push deploy `10dd4e19af9fa26d1aeb05124a05bbd5fdcf78ce`; kiểm browser/CI mới ghi riêng E99. Không nâng nghiệm thu R07/T14 hoặc bổ sung auth/PO/DB bền vững.


**CHG-066/E98 — React công khai trên Streamlit:** đã cập nhật [SIGMA](https://sigma-demand-inventory.streamlit.app/) sang giao diện quản lý React sáu màn hình; Python xử lý qua component hai chiều. Repo triển khai riêng tư `Sigma-M3-App/main`, commit `77b0b3d9406ba2131f678466b86f6615af6636e4`, release `m3-react-public-20261020-v2`.117Python và23React đạt; build local/Streamlit, đối soát aggregate/privacy và tạo phương án trong phiên đã kiểm. [Phạm vi và cách chạy](../review-log.md#removed-docs-chg070). Cấu hình/phương án mới riêng phiên; import/fit/replay giao dịch/DB dùng chung vẫn local. R05/M05/R07/T14 không đổi. Các mốc E94–E97 bên dưới giữ lịch sử.


**CHG-065/E97 — 20/10/2026:** người dùng đã làm rõ muốn giao diện/quy trình như phần mềm doanh nghiệp. React chuyển trọng tâm sang công việc điều hành và bàn nhập hàng: Cần bổ sung/Đang về/Lịch sử theo ngày, tìm kiếm trước phân trang, sắp xếp, chi tiết/CSV và liên kết tồn ↔ nhập ↔ cảnh báo đúng SKU. Bỏ dãy bước hướng dẫn E96.111Python+19React/build/Ruff đạt; browser/API thật đã đối soát793đề xuất/5866đơn vị,1lô20đơn vị. [Hướng dẫn và giới hạn](../../M3/IMPLEMENTATION.md#purchasing-e97). Không tạo PO thật/duyệt/nhận hàng thủ công/auth hoặc đổi model, DB schema, metric/nghiệm thu.


**CHG-064/E96 — 20/10/2026:** bổ sung ngữ cảnh bài M3 cho React: nhãn kho SIM/gói data, lối đi bốn bước dự báo → tồn → kế hoạch nhập → cảnh báo, diễn giải tiếng Việt các trường nhập hàng/cấu hình. Là điều chỉnh cách trình bày và điều hướng có sẵn, không thêm quy trình vận hành doanh nghiệp hoặc thay phép tính/API.17React/build đạt; browser kiểm điều hướng giữ run/ngày và không tràn ở390/1440px. [Hướng dẫn hiện hành](../../M3/IMPLEMENTATION.md#react-management-e95).109Python và CI E95 là bằng chứng lượt trước, không nhận vừa chạy lại backend.


**CHG-063/E95 — 20/10/2026:** đã thiết kế lại React thành web quản lý M3 với sáu màn hình: Tổng quan, Tồn kho, Dự báo nhu cầu, Nhập hàng, Cảnh báo, Cấu hình. Màn hình chính ưu tiên tồn/công việc; chất lượng mô hình và đánh giá replay thu gọn. API tổng quan chỉ đọc theo run/ngày/bộ lọc; lô đang về xét ngày đặt/ETA thay trạng thái cuối kỳ.109Python+17React/build đạt; tạo phương án từ UI đã complete/verified. [Phạm vi, hướng dẫn cho nhóm và bằng chứng](../../M3/IMPLEMENTATION.md#react-management-e95). Không đổi model/ledger/M05/R07/T14. Bản React chạy FastAPI/PostgreSQL local; Streamlit E94 là ứng dụng riêng, chưa nhận đã cập nhật React lên đó.


**CHG-062/E94 — 20/10/2026:** theo yêu cầu người dùng đã đưa [SIGMA lên Streamlit công khai](https://sigma-demand-inventory.streamlit.app/), release `m3-public-20261020-v1`, repo triển khai riêng tư `Sigma-M3-App` commit `779b6c44f56aefbbba1c907a57a3acc4144563ef`. Giao diện Streamlit7màn hình đọc aggregate M3 L7/R1/H14 và benchmark30 M05; có what-if riêng từng phiên/CSV. Huấn luyện/import raw/worker/DB bền vững vẫn local. [Phạm vi, gói và cách chạy](../review-log.md#removed-docs-chg070). R05 vẫn10/10 hồi cứu; R07/T14 không tự nâng nghiệm thu.

**CHG-061/E93/M05 — 20/10/2026, hiện hành:** mentor do người dùng thuật lại đã chốt **R05 tổng 30 ngày thay ngày**. Verifier nguồn và đối soát DB M3 xác nhận 10/10≤20%, mean11,621356%, coverage100%, 63 cửa sổ/tuyến; test hồi cứu. API/React tích hợp benchmark tổng 30 chỉ đọc, tách forecast H14 dùng tồn. Xem [kết quả và cách chạy](../../M3/MONTHLY.md). Các mốc trước M05 bên dưới giữ lịch sử; không dùng số ngày ở E92 làm cổng R05 hiện tại. T14 vẫn cần mentor nghiệm thu, R07 chưa có ngưỡng tỷ lệ tổng chính thức.

**E92 — 20/10/2026:** [M3/ACCEPTANCE](../../M3/ACCEPTANCE.md) phân biệt cổng kỹ thuật/độ chính xác/nghiệm thu. daily_panel.py nghiên cứu counts/annual/market dùng evaluate_frame chung với v1; không đổi app/DB/adapter/model serving.89Python đạt; nghiên cứu validation45,971604%,0/10≤20%.

**E91 hiện hành:** Cảnh báo có phân tích thời điểm cạn; M3/research/daily_validation.py là nghiên cứu validation riêng, không thay adapter/final10/forecast phục vụ.86Python+9FE/build đạt; xem [phạm vi/giới hạn](../../M3/IMPLEMENTATION.md). E90 bên dưới giữ mốc trước bổ sung.

**CHG-058/E90 — implementation M3, 19/10/2026:** đã chạy forecast46/H14, giữ final10, chọn36 bằng validation, phân bổ2.382.800 dòng, policy/alert replay và snapshotL7; có API kết quả/export, worker verify/heartbeat và React6màn hình.78 tests Python +7 tests FE, build/DB/đối soát thực; xem [bằng chứng, giới hạn và cách chạy](../../M3/IMPLEMENTATION.md). Phần mềm đã triển khai không đồng nghĩa đạt toàn bộ chỉ tiêu: fixed10 tổng7 đạt10/10 hồi cứu, new36 chỉ2/36; ngày phân bổ top10 là0/10, early cơ sở34,3913%. R05/R07/T14 vẫn mở. Người dùng cho phép push code/config/tests/docs; raw/run/DB/env giữ local. Các mốc E76/E89 dưới đây là lịch sử.

**CHG-057/E89 — bắt đầu implementation M3, 19/10/2026:** nhánh `codex/m3-implementation` lấy nền `M3-design-plan`20a3c45, checkout riêng tại `outputs/workspaces/m3-implementation` trong workspace gốc. Đã có Python3.12/backend lock, migration13bảng PostgreSQL18, API nền/queue, worker import, catalog/policy version, seed và các hàm tính L7/R1/H14. Source import thật đã đối soát100.000dòng/118.296quantity/46tuyến/920item/672.520dailyrows;35tests M3 và32tests M2 đạt. Chưa ML36/adapterfinal10/replay tích hợp/React/E2E; R05/R07/T14 còn mở. [Cách chạy và phạm vi thực có](../../M3/README.md#implementation-e89). Không dùng mốc nền để nhận hoàn thành toàn bộ M3.

**CHG-048/E76 — 19/10/2026:** điểm bắt đầu M3 mới là [M3/README](../../M3/README.md). Thư mục M3 hiện chỉ có 7 Markdown; backend/frontend/migrations/config/tests trong cây source là **dự kiến**, chưa tồn tại. Code M2 final vẫn là implementation hiện hành; không khôi phục code M3 cũ. Profile46 kho/L7/supplier-item cần bằng chứng mới trước nghiệm thu.

**CHG-045/E73 — 14/10/2026:** nhánh `cleanup/m2-final` chỉ giữ code M2 final. Xem [bản đồ code hiện hành](../../M2/README.md) và [khôi phục code cũ](../review-log.md#removed-docs-chg070). Các lệnh/đường code M1, M3, V13 và thử nghiệm bên dưới là lịch sử, cần nhánh backup để chạy; dữ liệu, kết quả, bằng chứng và tiêu chí nghiệm thu không đổi.

**CHG-042/E70 — 11/10/2026:** bộ [M2 final](../../M2/reports/final_m2_20261011/README.md) trên nhánh `M2-final-report` đã fit mới và kiểm độc lập10 lựa chọn cố định: tổng7 test10/10<20%, mean15.745366%, coverage100%; LG U+19,265900%. Chín tuyến cũ tái lập forecast validation/test trong1e-8. Chín lựa chọn validation giữ nguyên; LG U+ chọn từ test-sweep theo yêu cầu mới, nên test hồi cứu. H8–14 LG U+20,255792%; R05 ngày/R07/T14 mở. Có bảng cấu hình/metric/HTML và dashboard final; raw, run cũ, published07/10 và tồn/M3 giữ nguyên. Mã/cấu hình/bảng tổng hợp đã push GitHub; CI Windows của commit mã0cbeaf0 đạt toàn bộ checks; raw/daily/per-origin/draft giữ local.

**CHG-041/E69 — hoàn tất 11/10/2026:** [so sánh test toàn bộ160 lượt](../test-sweep-experiment.md) qua `M2/models/retrospective_sweep.py`, config `data/configs/m2-test-sweep.json`, tests `test_retrospective_sweep.py`. Run `M2/artifacts/m2_test_sweep_20261011_fixed` complete43 artifact và receipt `_review.json`; run đầu giữ failed35 artifact do đường dẫn baseline, forecast tái dùng khớp chính xác.17 lượt<20%, tốt nhất19,265900%/coverage100%;25 tests/đối soát640 metric đạt, raw/757 tệp và chín tuyến nguyên. Không lọc validation; xếp hạng test chỉ hồi cứu khám phá, lựa chọn cũ và sản phẩm khóa giữ nguyên.

**CHG-040/E68 — hoàn tất 11/10/2026:** module/config/tests `adaptive_experiment.py`/`m2-adaptive.json`/`test_adaptive_experiment.py` và `composition_experiment.py`/`m2-composition.json`/`test_composition_experiment.py`. [Lượt21](../adaptive-experiment.md), [lượt26 và CSV/receipt](../composition-experiment.md) tại `M2/artifacts/m2_adaptive_20261011` và `m2_composition_20261011_fixed`, hai receipt `_review.json` độc lập. Run đầu `m2_composition_20261011` giữ failed/invalidated19 artifact. Validation mới10,616717%, test20,446740% chưa<20%;29 tests đạt, raw/630 tệp và chín tuyến nguyên. Không đổi dashboard hoặc nghiệm thu.

**CHG-039/E67 — 11/10/2026:** nghiên cứu riêng LG U+ tại `M2/models/focus_experiment.py`, `hierarchy_experiment.py`, `refinement_experiment.py`; config tương ứng trong data/configs. Ba run local `m2_focus_20261011`, `m2_hierarchy_20261011`, `m2_refinement_20261011` complete, receipt `_review.json` bên ngoài run sealed. [Protocol/CSV/kết quả](../focus-experiment.md): validation10,775820%, test hồi cứu20,520981%, chưa<20%;42 tests đạt. Chín tuyến forecast/metric nguyên, dashboard/báo cáo khóa và raw giữ nguyên; R05/R07/T14 mở.

**CHG-038/E66 — 11/10/2026:** nhánh mới `codex/m2-calendar-forecast`; mã `M2/models/calendar_reference.py`, `calendar_experiment.py`, tests `test_calendar_experiment.py`, config `data/configs/m2-calendar.json`. Lịch local `data/reference/calendar_features.csv` đi cùng catalog `.events.json`; run20 artifact tại `M2/artifacts/m2_calendar_20261011`, receipt độc lập `M2/artifacts/m2_calendar_20261011_review.json`. [Hướng dẫn/kết quả](../calendar-experiment.md):10 ứng viên validation không thắng đối chứng LG U+11,632703%, không chấm test mới,35 tests đạt. Raw/báo cáo/dashboard cũ nguyên; R05/R07/T14 mở.

**CHG-037/E65 — 09/10/2026:** M2 đã tái chạy local tại `M2/artifacts/m2_reproduce_20261009_full`, verifier và [báo cáo](../../M2/reports/m2_reproduce_20261009_full_review/README.md) tại `M2/reports/m2_reproduce_20261009_full_review`. Dữ liệu dẫn xuất tại `data/processed/m2_reproduce_20261009_full` và `data/training/m2_reproduce_20261009_full`; đủ26 biến thể/50 cấu hình. Mở `scripts/start_m2.ps1 -RunId m2_reproduce_20261009_full`; notebook dùng run này mặc định hoặc biến môi trường SIGMA_M2_RUN_ID. Kết quả khớp published: tuần9/10,15,89%; ngày0/10,46,74%; R05/R07/T14 mở. Mã từ nhánh trong ảnh đã nằm trong HEAD; raw/báo cáo/Word cũ nguyên, không push. Các thư mục run lịch sử v1/V13/M3 chưa phục hồi.

**CHG-036/E64 — 06/10/2026:** theo yêu cầu người dùng, nhánh báo cáo đổi thành `m2-forecast-report`, bỏ tiền tố codex. Email author/committer ba commit M2 trên nhánh mới được đổi sang `chaoskid1415@gmail.com`; cấu hình Git chỉ áp dụng repo này. Nội dung ba commit giữ nguyên, cập nhật tên nhánh trong hướng dẫn và metadata báo cáo; kết quả9/10/LG U+ chưa đạt không đổi. Nhánh GitHub cũ được thay bằng nhánh mới sau khi xác nhận push. [Báo cáo M2](../../M2/reports/published_m2_20261007/README.md).

**CHG-035/E63 — 06/10/2026:** đã xuất bản nhánh GitHub `codex/m2-report-20261007` theo yêu cầu người dùng với [báo cáo M2 tổng hợp](../../M2/reports/published_m2_20261007/README.md), HTML offline, biểu đồ, CSV metric/lựa chọn và hash đối soát. Remote head commit báo cáo `88ddbba` đã kiểm khớp local. Giữ kết quả9/10 tổng7,15,89%, LG U+20,69% hoãn tối ưu; ngày0/10, test hồi cứu. Raw, train từng ngày và artifact forecast giữ local, không refit hoặc đổi nghiệm thu.

**CHG-034/E62 — 06/10/2026:** tạo nhánh local `codex/m2-report-20261007` để báo cáo M2 ngày07/10. Clean root33→6 tệp, chuyển39 tệp vào data/configs, src/sigma, scripts, legacy và docs/planning/archive. Đóng gói dữ liệu train/validation/test top10 và báo cáo HTML/Streamlit đọc run đã khóa9/10 tổng7,15,89%, LG U+20,69% để tối ưu sau. Không refit raw hoặc đổi lựa chọn; ngày0/10/R05/R07/T14 còn mở. [Kịch bản trình bày](../../M2/reports/presentation-guide.md).

**CHG-033/E61 — đã triển khai và đối soát 06/10/2026:** 12 biến thể đối chứng +14 mới,26 biến thể/50 cấu hình ngày–tổng7, tối đa3 worker. Run `m2_improved_models_20261006_fixed` complete, lựa chọn khóa theo validation: LightGBM9 tuyến/Prophet au(KDDI) cho tổng7, test hồi cứu 9/10, MAPE 15.89%, LG U+20,69%; ngày0/10,46.74%. 40 kiểm tra liên quan và verifier 401,600 dòng/9,160 nhóm metric đạt. Raw và583 tệp lịch sử nguyên; R05/R07/T14 còn mở, sản phẩm V13 giữ hiện hành. [Báo cáo cải tiến](../../M2/reports/m2_improved_models_20261006_handoff.md).

**CHG-032/E60 — 06/10/2026:** mã riêng từng họ nằm tại M2/models/LightGBM/model.py, SARIMA/model.py và Prophet/model.py; mỗi thư mục có variants.json và README. [Hướng dẫn mở rộng](../../M2/models/README.md), registry.py, common.py và families.py xác định giao diện và protocol chung. Báo cáo đối soát hiện tại ở M2/reports/m2_three_models_20261006_modular; bằng chứng parity24 trường hợp và bảo toàn583 tệp ở M2/artifacts/model_split_checked.json. 15 tests/221.280 dòng/2.040 nhóm metric đạt; không chạy lại huấn luyện dữ liệu thật.

**CHG-031/E59 — 06/10/2026:** [M2](../../M2/README.md) là nơi chính cho artifacts/models/notebooks/reports. Mã ba họ tại M2/models/families.py, verifier tại M2/models/verify.py, cấu hình tại M2/models/model_families.json, tests tại M2/models/tests, notebook tại M2/notebooks/model_comparison.ipynb. Mã ở sigma/forecasting/families.py và sigma/verification/model_families.py nay là alias; các đường outputs cũ là liên kết tương thích. 583 tệp kết quả nguyên byte; CLI/13 tests/notebook và verifier221.280 dòng/2.040 metric đạt. Báo cáo có đường mới tại M2/reports/m2_three_models_20261006_organized.

**CHG-030/E58 — 06/10/2026:** thêm `sigma/forecasting/families.py`, `sigma/verification/model_families.py`, `configs/model_families.json`, `tests/test_model_families.py` và [hướng dẫn/kết quả](../model-families.md). CLI `model-families` tạo ba thư mục LightGBM/SARIMA/Prophet với hai mục tiêu/họ; run `m2_three_models_20261006` complete,309 artifact. CLI `verify-model-families` đối soát221.280 dòng/2.040 nhóm metric và tạo `m2_three_models_20261006_review`. 9 kiểm tra mới,45 kiểm tra liên quan và pip check đạt. Raw/58 artifact ngày cũ/run tuần V13 local nguyên; CI chưa chạy, sản phẩm hiện hành chưa đổi.

**Bổ sung CHG-029/E56–E57 — 06/10/2026:** `sigma/experiments/seasonal_weekly.py` và verifier chạy validation-only, không cải thiện top 10 nên chưa tích hợp; run local `sigma_seasonal_validation_v14`, đối soát `sigma_seasonal_verification_v14`. `sigma/analysis/alert_diagnostics.py` bổ sung bảng giải thích sự kiện vào dashboard tồn, không sửa policy/forecast/mẫu số. 225 tests local và AppTest mới sáu trang/bốn kịch bản/SKU–loại đạt; CI bổ sung chưa xác minh. [Tài liệu chẩn đoán](../model-diagnostics.md) và hướng dẫn demo được cập nhật; run sản phẩm V13, raw/sealed ngày và Word/slide giữ nguyên.

**Hiện hành CHG-028/E53–E55 — 06/10/2026:** sản phẩm mặc định dùng V13 với 58 ứng viên chọn bằng validation, cùng policy V4, stock V7, customer V6 và comparison V3. Bộ báo cáo đã khóa tại sigma_m2m3_checkpoint_v3; mở start_m2m3.ps1 ở cổng 8504. **214 tests và CI Windows của commit 183ed10 đạt**; đã đối soát 447.810 cặp dự báo, 42.136 hệ số hiệu chỉnh, 1.100.320 dòng sổ, 267.908 giao dịch/nhập và 920 mặt hàng. AppTest sáu trang, bốn kịch bản và bộ lọc SKU/loại đạt. Job Windows 07:00 đã cài, chạy thử mã 0. Tuần đạt 9/10, MAPE trung bình 16,17%, LG U+ 21,19%; R05 ngày vẫn 0/10, tỷ lệ báo sớm 33,73% trên 2.867 sự kiện. **Chưa nghiệm thu toàn bài.** Dữ liệu gốc và 59 artifact v11 nguyên; src/ và run.py không đổi, app.py chỉ thêm khóa bộ run. Word/slide chưa làm lại; các cập nhật cũ bên dưới là lịch sử.

**Lịch sử CHG-027/E43–E49 — 05/10/2026:** sản phẩm mặc định dùng sigma_weekly_refactored_v12; đã hoàn tất bản so sánh ngày/tổng7 ngày và tổ chức mã sigma/ +29 entry points legacy/ +configs/experiments. 192 tests đạt; parity364.320 validation cache/7.590 fresh test/92 future/644 daily rows ở1e-8, cùng46 lựa chọn; raw/59 v11 files nguyên. Full policyV3 kiểm13 kịch bản/1.100.320 ledger/267.812 events; snapshotV6 kiểm920 items từ đúng policy; customerV5 kiểmD+7; AppTest6 trang và4 bộ lọc scenario đạt. Tuần9/10, mean16,19%, LG U+21,19%; R05 ngày0/10, early≥7 ngày33,80% cùng2867 events; chưa nghiệm thu toàn bài. CHG-027 thay thứ tự hoãn CHG-025; Word/slide không làm lại. Các cập nhật bên dưới E37–E41 là lịch sử.

**Cập nhật 05/10/2026 — CHG-024/025, E37–E39:** đã áp dụng **khách đặt D → giao D+7 ngày lịch UTC**, không trễ giao, gồm cuối tuần; không đổi lead time nhập kho. Người dùng mô tả snapshot order là giả định; đây là nguồn thuật lại, vẫn giữ dữ liệu/outputs private và raw nguyên. [Sản phẩm chung và lịch giao](../customer-delivery.md) mở bằng `start_product.ps1` tại cổng 8503. Run tuần hiện hành `sigma_weekly_calibrated_v5`: test hồi cứu **9/10**, mean **15,97%**, LG U+ **21,36%**; chọn validation rồi khóa trước test. 920 khuyến nghị tồn từ phân bổ tuần đã đối soát, replay cùng 5.520 cửa sổ báo sớm **33,73%**; chưa chạy lại toàn bộ chính sách liên tục bằng tuần. 150 tests đạt, AppTest năm trang/không exception; job refresh/skip chạy thật, script đăng ký lịch nền được chuẩn bị nhưng chưa cài. R05 ngày **0/10**, R07/T14 vẫn mở. **Sau khi đủ điều kiện nghiệm thu mới làm bản so sánh chính thức ngày/tổng 7 ngày và tổ chức lại code**, đúng thứ tự người dùng yêu cầu; chưa làm lại Word/slide. Những cập nhật E36/v1 bên dưới là lịch sử.

**Nguồn và phương án mới 05/10/2026 — E35/E36:** ảnh kickoff JPG mới đã xem trực tiếp, lưu bản sao ignored local; [đối chiếu nguồn](../kickoff-checklist.md) thay tình trạng thiếu ảnh kickoff ở các ghi nhận cũ bên dưới. PDF và ảnh M01/M02 vẫn chưa có; không phục hồi tệp bị xóa. [weekly_forecast.py](../review-log.md#removed-docs-chg070), [config.weekly.json](../review-log.md#removed-docs-chg070), [verify_weekly.py](../review-log.md#removed-docs-chg070), [weekly_app.py](../review-log.md#removed-docs-chg070), [launcher](../review-log.md#removed-docs-chg070), [tests](../review-log.md#removed-docs-chg070), [hướng dẫn tuần](../weekly-forecast.md) đã có thật. Run `outputs/sigma_weekly_v1/` và verification_v2 giữ private; test tuần 9/10, AIS 22,14%, chưa thay R05 ngày. 125 tests/AppTest đạt; mã core ngày/v11 không sửa. Các tình trạng thiếu nguồn ở E34 và ngày02/10 là lịch sử.

**Hiện trạng 05/10/2026:** Workspace hiện tại `C:/Users/nguye/OneDrive/Desktop/TTDN_Sigma`. Đã có `src/`, `tests/`, `config.json`, `run.py`, `app.py`, khóa phụ thuộc, notebook, script dashboard và CI. Run local thật hiện hành `outputs/sigma_scaled_v11/`; demo giả `outputs/demo_scaled_v11_verify/`; Word/slide local `reports/M2/`. Dữ liệu và outputs không thuộc gói Git. Các cây/tình trạng ngày 02/10 bên dưới là lịch sử trước triển khai; trạng thái hiện hành tại TASK và README. Git root đã kiểm tra nằm đúng project, không còn dùng giới hạn kho cha cũ để mô tả workspace này.

**Nghiên cứu E32:** Có [validation_campaign.py](../review-log.md#removed-docs-chg070) và [bốn ca kiểm](../review-log.md#removed-docs-chg070); 111 tests hiện hành đạt. Campaign 12 cấu hình chọn trên tháng 5–6 nằm trong train, sau đó chấm toàn validation tháng 7–9: 0/10 đạt 20%, chưa tích hợp. Output riêng `outputs/sigma_ablation_campaign_v1/`, đối soát/so sánh `outputs/sigma_ablation_analysis_v3/`, đều private local. Mã production, 59 tệp sealed v11 và raw hash giữ nguyên; không chạy test mới, không sửa Word/slide.

**Lịch sử phạm vi CHG-012/013:** tập trung hoàn thiện project, chưa làm tiếp Word/slide. Có `validate_context.py`, `src/context_models.py`, tests và kết quả validation local `outputs/context_validation_v1/`; chưa tích hợp mô hình context vào production. E16 ghi kiểm tra trực tiếp; R05/R07 vẫn mở.

**Báo cáo tiến độ M2 E33 / CHG-022:** Người dùng yêu cầu ưu tiên Word báo cáo chi tiết và slide để nộp mentor trước. Bản hiện hành local tại `reports/M2_2026-10-05/`: `SIGMA_Bao_cao_tien_do_M2_Nop_mentor_2026-10-05_v3.docx` (18 trang), `SIGMA_Slide_bao_cao_M2_Nop_mentor_2026-10-05_v2.pptx` (24 slide có ghi chú). Đã kiểm bố cục và không có định danh nguồn; dùng số liệu sealed v11 và nghiên cứu E32. Run/mã production không sửa, R05/R07/T14 vẫn mở; không tự upload báo cáo.

**Nghiên cứu E34:** [calibrate_campaign.py](../review-log.md#removed-docs-chg070), [verify_calibration.py](../review-log.md#removed-docs-chg070) và [bốn ca kiểm](../review-log.md#removed-docs-chg070) đã chạy; toàn suite 115 tests đạt. Head phối hợp/hiệu chỉnh học tháng 5, chọn tháng 6 trong train rồi khóa trước validation; refit 7 ngày chỉ dùng nhãn đã qua. Run riêng `outputs/sigma_calibration_campaign_v2/`, đối soát `outputs/sigma_calibration_verification_v1/`: vẫn 0/10 đạt 20%, 38,64–52,10%; mean kém v11 validation. Không tích hợp, không chấm test mới hoặc sửa sealed v11. Chẩn đoán train theo tháng/weekday là in-sample, không phải cận dưới cho mọi mô hình. Ảnh/PDF kickoff gốc vẫn thiếu; đã đề nghị đối chiếu nguyên văn, chưa tự thay tiêu chí.

**Thời điểm đối chiếu:** 02/10/2026 (Asia/Saigon). **Thư mục project:** `C:/Users/asus/OneDrive/Máy tính/sigma/Sim-Demand-Forecasting-main`.

Bản đồ này ghi tệp thực tế và sai khác nguồn; [PLAN 2.0](PLAN.md) vẫn giữ thiết kế chi tiết, [requirements](../requirements.md) giữ nghiệm thu, [review-log](../review-log.md) giữ lịch sử. Mô tả khảo sát chỉ đọc ngày 02/10 bên dưới giữ làm lịch sử. Pipeline hiện đã chạy, xem E11–E15; ảnh/PDF nguồn vẫn thiếu và không nhận đã đọc lại.

<a id="actual-tree"></a>
## Cây trước triển khai — lịch sử 02/10/2026

```text
Sim-Demand-Forecasting-main/
├── AGENTS.md                       # Mới: quy tắc và điều hướng cho Codex
├── TASK.md                         # Mới: điều phối T01–T14
├── PROJECTMAP.md                   # Mới: hiện trạng, cấu trúc, sai khác
├── README.md                       # Mới: giới thiệu và điểm bắt đầu
├── PLAN.md                         # Có trước: kế hoạch chi tiết 2.0, giữ nguyên
├── data/
│   └── sigma_sim_data_orders.csv   # Có trước: nguồn riêng tư, giữ nguyên byte
└── docs/
    ├── requirements.md             # Có trước: R01–R09, giữ nguyên
    ├── review-log.md               # Có trước: bằng chứng/lịch sử, giữ nguyên
    ├── data-contract.md            # Mới: schema và hợp đồng dữ liệu dự kiến
    └── development.md              # Mới: triển khai, kiểm tra và bàn giao
```

Bốn tệp có trước và sáu tài liệu mới là toàn bộ tệp hiện có trong project tại lần đối chiếu này. Chưa có mã nguồn, cấu hình, môi trường dự án, tests, notebook, outputs hoặc báo cáo chạy. Không tìm thấy AGENTS áp dụng trong project/các thư mục cha ở bước khảo sát trước khi tạo AGENTS mới. Vai trò và lộ trình đọc từng tài liệu tại [README](../../README.md).

<a id="planned-tree"></a>
## Cấu trúc thiết kế trước triển khai — lịch sử 02/10/2026

Trích nhóm sản phẩm từ PLAN mục 4; cây dưới chỉ liệt kê phần kỹ thuật còn thiếu. Tên/path không chứng minh sản phẩm tồn tại; không tạo thư mục rỗng hoặc khôi phục tệp cũ để làm đủ cây.

```text
Sim-Demand-Forecasting-main/
├── config.json                    # Target, split, mô hình, đối tác, giả định
├── requirements.txt               # Phụ thuộc huấn luyện local, chưa khóa
├── requirements-demo.txt          # Phụ thuộc dashboard, chưa khóa
├── run.py                         # CLI dự kiến
├── app.py                         # Streamlit dự kiến
├── notebooks/run_local.ipynb      # Dùng cùng mã với CLI
├── src/
│   ├── data.py                    # Audit và dữ liệu dẫn xuất
│   ├── models.py                  # Baseline/SARIMA/LightGBM có điều kiện
│   ├── evaluation.py              # Backtest và metric
│   ├── inventory.py               # Phân bổ, ledger, chính sách/cảnh báo
│   └── reporting.py               # Bảng, hình và gói kết quả
├── tests/
│   ├── test_data.py
│   ├── test_forecasting.py
│   └── test_inventory.py
├── data/
│   ├── reference/holidays.csv      # Lịch công khai có nguồn
│   ├── scenarios/
│   │   ├── partner_map.csv         # Mapping giả định
│   │   ├── inventory.csv           # Snapshot mô phỏng
│   │   └── receipts.csv            # Hàng về giả định/mô phỏng
│   └── processed/daily_sales.csv
├── outputs/<run_id>/               # Riêng tư; manifest/audit/forecast/metric
│   ├── manifest.json
│   ├── data_audit.json
│   ├── top_routes.csv
│   ├── predictions.csv
│   ├── metrics.csv
│   ├── selected_models.csv
│   ├── inventory_ledger.csv
│   ├── inventory_recommendations.csv
│   ├── alerts.csv
│   ├── simulation_metrics.csv
│   ├── figures/
│   └── checks.txt
└── reports/
    ├── report.md
    ├── report.pdf
    ├── slides.pptx
    └── demo-script.md
```

Ảnh/PDF nguồn được PLAN đưa trong cây thiết kế được liệt kê ở phần nguồn thiếu bên dưới, không phải tệp kỹ thuật sẽ tự sinh. Mô hình dữ liệu đầu ra mới ở mức [giao diện dự kiến](../data-contract.md#outputs), chưa có API/schema thực thi. T12 tập hợp kiểm thử nghiệm thu; các kiểm tra cần thiết vẫn được viết/chạy cùng từng task kỹ thuật trước đó.

## Luồng dự kiến và điểm kiểm soát

```text
order gốc → audit → daily sales → EDA/lịch → baseline/backtest
→ chọn mô hình bằng validation → khóa lựa chọn → test
→ forecast → phân bổ SKU × product_type
→ mô phỏng tồn kho/cảnh báo → dashboard/báo cáo
```

CSV không bị ghi đè. Mỗi sản phẩm dẫn xuất truy về target/cutoff/run; tồn và cảnh báo thêm scenario/assumption version. Forecast sales chấm trên order holdout; kết quả tồn đánh giá theo kịch bản. Giao diện không được trộn actual, dự báo, giả định và mô phỏng.

| Thay đổi | Thành phần phải rà soát/tính lại | Kiểm tra bắt buộc liên quan |
|---|---|---|
| Target, bộ lọc A08, timezone | Data contract/config; T03–T14: chuỗi, EDA, top 10, mô hình, metric, phân bổ, tồn, hình/báo cáo | Quantity, UTC, activation độc lập; hash gốc; truy phiên bản target |
| Split, cutoff, origin/horizon | Config/backtest/top 10/selection/forecast; T04–T14 và nhãn dashboard | Top 10 chỉ train; feature/nhãn đúng cutoff; cùng cặp chấm; H đủ L+R; công khai test đã dùng |
| Mô hình, feature, refit hoặc lựa chọn | models/evaluation dự kiến; predictions/metrics/selected_models; các đầu ra tồn/báo cáo phụ thuộc forecast | Không nhìn tương lai; chọn bằng validation; metric tính tay; không dùng test chọn lại |
| Mapping, tồn đầu, lead time, safety, MOQ, receipts | A09–A16/config/scenario; T06/T10–T14, manifest/ledger/alerts/độ nhạy | Ngưỡng riêng, strict <, IP/Q, ETA, cân bằng tồn, event duy nhất; A12 không đòi fit lại forecast nếu độc lập |
| Chỉ nhãn hoặc trình bày | Tài liệu/hình/dashboard liên quan | Link/đơn vị/nguồn, khớp số và nhãn thực/dự kiến; không thực nghiệm lại nếu phép tính không đổi |

<a id="source-gaps"></a>
## Nguồn thiếu và sai khác cần giữ rõ

| Vị trí / nguồn | Đối chiếu trực tiếp và trạng thái | Tác động / cách sử dụng |
|---|---|---|
| PLAN mục 3, review-log E01/E02, requirements S01/S02 | `docs/PROJECT_REQUIREMENTS.png` và `docs/Báo cáo chi tiết Sigma.pdf`: **được tài liệu tham chiếu nhưng chưa có trong workspace**. Bốn liên kết cũ tới hai tệp này chưa phân giải được | Không nhận đã đọc/kiểm chứng lại ảnh hoặc 45 trang PDF. Giữ nhận xét E/RV như lịch sử, không tạo tệp giả hoặc khôi phục |
| M01/M02, review-log E08 | Hai ảnh mentor chỉ được người dùng thuật lại trong nguồn 2.0; chưa có tệp để đọc trực tiếp | Giữ nguồn thuật lại, không gán bộ lọc success, mapping hoặc số ngưỡng cho mentor |
| review-log E02 | Hash/kích thước CSV hiện tại khác bản lịch sử; chuyển LF→CRLF trong bộ nhớ khớp đúng hash/kích thước E02 | Ghi cả hai dấu vết tại [data-contract](../data-contract.md#source-check). Không coi byte hiện tại giống byte lịch sử, không sửa xuống dòng để ép khớp |
| PLAN mục 3, review-log E01/E10, QA-DOC-001/002 | Khảo sát chuẩn bị chạy `git rev-parse --show-toplevel` gặp dubious ownership tại kho cha `C:/Users/asus`; project không có `.git` riêng | Chưa xác minh tracked CSV, danh sách 26 tệp bị xóa hay diff hiện tại. Đây là ghi nhận lịch sử, không phát hiện mới. Không sửa safe.directory/global Git; dùng danh sách tệp/hash trong project |
| Đầu ba nguồn 2.0, U03/U05, DEC13/DEC21 | Phạm vi “ba Markdown” thuộc lượt cũ; yêu cầu hiện tại cho phép bổ sung sáu tài liệu | Giữ nguyên nguồn, không diễn giải giới hạn cũ thành cấm tạo sáu tài liệu hiện tại; chưa có quyền triển khai kỹ thuật trong lượt này |
| PLAN mục 6.1 / CSV; PLAN mục 4.2 / requirements R04 | CSV dùng `sku`, mô tả khóa dùng `SKU`; forecast interface ghi `forecast_date`, tiêu chí ghi `target_date` | Giữ `sku` ở nguồn; ghi khác biệt tên ngày mục tiêu trong data-contract. Giao diện đầu ra chưa triển khai, cần chốt khi làm kỹ thuật, không đổi nguồn âm thầm |
| PLAN T01/T10 so với requirements R01–R09 | PLAN gắn T01 với R01–R09, trong requirements T01 được liệt kê trực tiếp ở R01/R09; R09 liệt kê T10 nhưng PLAN T10 ghi R06/R07 | Mức liệt kê truy vết chưa đối xứng. TASK giữ Rxx theo PLAN; ghi rõ đối chiếu này, không bỏ nghĩa vụ R09 hoặc tự sửa ba nguồn |
| review-log E06 và QA-DOC-001/002 | E06 là MA7 activation, không có script/CSV kết quả hiện hành; các QA cũ thuộc bộ ba nguồn ở thời điểm cũ | Không dùng như baseline sales hoặc kiểm tra bộ sáu tệp mới; T02–T14 vẫn chưa làm |

Các sai khác trên không tự xác nhận hoặc bác bỏ nghiệp vụ đã được thuật lại. Thiếu ảnh/PDF hoặc dữ liệu tồn thật không tạo yêu cầu xin thêm dữ liệu doanh nghiệp; triển khai sau này dựa trên yêu cầu/giả định có nhãn và công khai giới hạn.

<a id="doc-checks"></a>
## Kiểm tra lượt bổ sung tài liệu

**Kết quả ngày 02/10/2026: đạt kiểm tra tài liệu trong phạm vi dưới đây.** Đã chạy kiểm tra chỉ đọc bằng Python standard library qua `python -B -` trong PowerShell; mã kiểm tra truyền qua stdin, không tạo script hoặc kết quả kỹ thuật giả trong project.

- Đúng 10 tệp hiện có: bốn tệp nền và sáu Markdown mới; không tạo thêm tệp ngoài danh sách.
- Sáu Markdown đọc UTF-8 hợp lệ; 72 liên kết tương đối/anchor hợp lệ; 15 bảng đúng số cột; 9 khối mã đóng đủ.
- Bảng điều phối đủ đúng một dòng cho mỗi T01–T14; tên, tập phụ thuộc và Rxx khớp PLAN. T01 vẫn đang làm, T02–T14 chưa làm; giữ điều kiện T08 và vai trò T06/T09 với T10. Ba nguồn giữ đủ chín định nghĩa R01–R09.
- Từ điển đủ 20 cột theo đúng thứ tự header CSV; phân biệt kiểu quan sát/kiểu dự kiến và ý nghĩa suy luận. Đã rà nội dung target sales/A08 đề xuất, split, top 10 train, H14/h1–7/h8–14, metric và trigger strict < theo nguồn 2.0.
- SHA-256 của CSV, PLAN, requirements và review-log khớp mốc đầu lượt tạo tài liệu (4/4); không khôi phục nguồn thiếu hoặc đổi Git config. Kiểm chứng phạm vi bằng inventory/hash, không tuyên bố có Git diff hợp lệ.
- Bốn liên kết trong hai tài liệu nguồn tới ảnh/PDF thiếu vẫn là giới hạn đã ghi ở bảng trên; không tính chúng là liên kết mới đạt kiểm tra. Bằng chứng lịch sử và kiểm tra trực tiếp đã được tách rõ.

Đây là kiểm tra Markdown/schema/truy vết và bảo toàn nguồn, **không phải kiểm thử pipeline hoặc nghiệm thu T02–T14/M1/M2/M3**. Chưa cài thư viện, huấn luyện hoặc mô phỏng. Bước tiếp theo: rà soát đóng phần tài liệu T01 theo tiêu chí trong PLAN; T02 chỉ bắt đầu khi được giao kỹ thuật và điều kiện T01 có bằng chứng, sau đó T03 → T04 → T05.

**Cập nhật CHG-014:** Có `src/seasonal_models.py`, `src/validation_cache.py`, `verify_release.py`, config 1.3.0 và run tích hợp v5 đang kiểm tra. Context đã tích hợp CLI; mô tả chưa tích hợp CHG-013 bên trên chỉ kết quả lịch sử. Demo `demo_integrated_v5_verify` trong môi trường thứ hai tái lập 14 bảng. R05 vẫn 0/10, không gọi toàn bài đã đạt.

**Cập nhật CHG-015/E19:** `src/count_models.py`, config 1.4.0 và v6 đã kiểm tra kỹ thuật (59 tests/50 sealed files/AppTest), 51 ứng viên chọn bằng validation; R05 vẫn 0/10. R06 còn bổ sung thứ tự giao dịch; không nâng ledger tổng ngày thành bằng chứng giao dịch.

**Cập nhật CHG-016/E21:** Có `src/transactions.py`, config 1.5.0, `config.integrated-v6.json` và run v7 đã đối soát event/day/nguồn audited. 75 tests đạt; mã hiện hành xử lý thứ tự giao dịch thật trong mô phỏng, không chỉ chứng minh tương đương tổng ngày. Prototype cohort CHG-017 chỉ validation, chưa tích hợp production.

**Cập nhật CHG-017/E23:** Có `src/cohort_models.py`, config 1.6.0, config v7 lưu và run v8 đã kiểm 83 tests/53 hashes/AppTest. Cohort đã tích hợp CLI sau validation, không còn chỉ prototype. R05 vẫn 0/10; dữ liệu/proxy/giả định giữ nhãn.

**Cập nhật CHG-018/019/E25:** Config 1.7.0, catalog 57 và run sigma_monthly_v9 đã kiểm 92 tests/55 hashes/nguồn/top/selection/actual/AppTest. Có tests/test_operational_guards.py, AllocationPlan causal và nguồn giả riêng trong mỗi run. R05 vẫn 0/10; Word/slide chưa làm tiếp.

**Cập nhật CHG-020/E27:** Có src/hierarchical_models.py, tests/test_hierarchical_models.py và tests/test_release_verification.py. Config 1.8.0/catalog 59; v10 đã kiểm 100 tests/nguồn và metric validation/top/selection/actual/ledger/events/AppTest. R05 vẫn 0/10, không chọn bằng test; Word/slide chưa làm tiếp.

**Cập nhật CHG-021/E31:** Có check_data.py, src/monthly_lad.py và tests chuẩn hóa/scaler. Config 1.9.0, v11 kiểm 107 tests/59 sealed hashes/nguồn/validation/ledger/events/AppTest. Chuẩn hóa độc lập và scaler causal được kiểm; test vẫn 0/10, không chọn lại bằng test; Word/slide chưa làm tiếp.

<a id="m3-design-v1"></a>
## Bản đồ M3 mới — đặc tả, chưa có source

Thực có: `M3/README.md`, sáu file `M3/docs/01…06`. Dự kiến: `web/backend/src/sigma_m3`, migrations/tests,`M3/frontend/src`, configs/scripts; cây chi tiết tại [05](../../M3/docs/05-source-architecture.md). Những đường này không phải file đã triển khai hoặc lệnh đã chạy.

Nguồn M2 dùng lại qua adapter: src/data/evaluation/common, weekly và spec LightGBM/Prophet, final10/focus/calibration. Không khôi phục source M3 từ backup. Source data/private artifacts vẫn tại workspace local, không copy vào nhánh docs. Graph dữ liệu: source import→forecast46→allocation→policy hoặc alert replay→API/FE; mọi kết quả có parent/hash/config snapshot.
