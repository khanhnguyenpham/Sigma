# README trước khi bỏ Streamlit — lịch sử

Nội dung dưới đây ghi phiên bản cũ. Launcher/dashboard Streamlit đã gỡ ở CHG-068 bước4; dùng README hiện hành để chạy React/FastAPI local.

# SIGMA — bộ code M2 final

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo feature và thành phần dùng chung, sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Bước3 đã gỡ Streamlit M3; React gọi HTTP/FastAPI local, dev Vite và build do FastAPI phục vụ. M2 Streamlit còn chờ bước4; HTML, CLI và notebook M2 được giữ. 71tests BE/26React/build và smoke API local đạt; chưa kiểm browser tương tác trong bước3. Tài liệu Streamlit phía dưới là lịch sử, không còn source M3 để chạy.

[Kế hoạch CHG-068 và cổng từng bước](../planning/PLAN.md#chg-068).

**CHG-067/E99 — 21/10/2026, hoàn thiện bản nộp:** bổ sung phục hồi khi tải lỗi/mất kết nối, giới hạn chờ RPC, màn hình lỗi có lối thử lại, làm mới trong phiên, hướng dẫn nghiệp vụ, điều hướng Back/Escape và hỗ trợ bàn phím. Tạo phương án online chỉ chọn93ngày có đủ closing920item và forecast H14 (30/09–31/12/2025).120Python+31React đạt; dữ liệu/metric/run khóa giữ nguyên. [Hướng dẫn nộp và kiểm sản phẩm](../../M3/SUBMISSION.md). Đã push deploy `10dd4e19af9fa26d1aeb05124a05bbd5fdcf78ce`; kiểm browser/CI mới ghi riêng E99. Không nâng nghiệm thu R07/T14 hoặc bổ sung auth/PO/DB bền vững.


**CHG-066/E98 — React công khai trên Streamlit:** đã cập nhật [SIGMA](https://sigma-demand-inventory.streamlit.app/) sang giao diện quản lý React sáu màn hình; Python xử lý qua component hai chiều. Repo triển khai riêng tư `Sigma-M3-App/main`, commit `77b0b3d9406ba2131f678466b86f6615af6636e4`, release `m3-react-public-20261020-v2`.117Python và23React đạt; build local/Streamlit, đối soát aggregate/privacy và tạo phương án trong phiên đã kiểm. [Phạm vi và cách chạy](m3-streamlit.md). Cấu hình/phương án mới riêng phiên; import/fit/replay giao dịch/DB dùng chung vẫn local. R05/M05/R07/T14 không đổi. Các mốc E94–E97 bên dưới giữ lịch sử.


**E94 — [SIGMA công khai trên Streamlit](https://sigma-demand-inventory.streamlit.app/):** đã cập nhật tổng30 M05 và profile M3 L7/R1/H14, có7màn hình/kết quả/CSV/what-if riêng từng phiên. [Source và phạm vi online](m3-streamlit.md). Huấn luyện/import raw/worker/DB bền vững giữ local; không gọi bản Streamlit là đã cloud hóa toàn bộ stack FastAPI/PostgreSQL.

**Cập nhật M05/E93, 20/10/2026:** R05 chấm tổng 30 ngày theo mentor được người dùng thuật lại. Đã kiểm lại **10/10 tuyến ≤20%, MAPE trung bình11,62%**, coverage100%, test hồi cứu. M3 FastAPI/React có tab tổng30, baseline và CSV. [Đọc kết quả/cách chạy](../../M3/MONTHLY.md); tồn/cảnh báo vẫn dùng H14.

**M3 đã triển khai trên nhánh `codex/m3-implementation`:** [hướng dẫn chạy, bản đồ source và kết quả kiểm](../../M3/IMPLEMENTATION.md). FastAPI/React/PostgreSQL local46tuyến, riêng với sản phẩm tổng30/Streamlit ở nhánh khác. R05/R07/T14 còn mở.

**M3 — thiết kế ngày 19/10/2026:** đọc [bộ tài liệu M3](../../M3/README.md) cho nghiệp vụ, 13 bảng PostgreSQL, BE/API, FE, source dự kiến và kiểm thử. Nhánh `M3-design-plan` chỉ bổ sung/cập nhật Markdown; chưa có ứng dụng hoặc lệnh M3 chạy được. Hướng dẫn M2 bên dưới vẫn là đường chạy có thật.

Nhánh `M2-final-cleanup` chuẩn bị báo cáo thứ Sáu 16/10/2026. Điểm bắt đầu để tìm và giải thích code: [M2_CODE_MAP.md](../../M2_CODE_MAP.md). Có 10 lựa chọn theo tuyến, 7 cấu hình: LightGBM pooled top 10 cho 9 tuyến và Prophet riêng au (KDDI).

[Báo cáo final đã khóa](../../M2/reports/final_m2_20261011/README.md) · [HTML offline](../../M2/reports/final_m2_20261011/index.html) · [Tham số 10 tuyến](../../M2/reports/final_m2_20261011/model_configurations.md) · Tài liệu học lịch sử tại `M2/reports/mentor_prep_20261014/README.md` là nguồn local chưa có trong worktree này.

```powershell
# Đã kiểm local bằng Python 3.12.14 trên Windows; CI cấu hình 3.14 chưa chạy lại.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\start_m2.ps1
```

Dashboard ở `http://127.0.0.1:8505`, chỉ đọc bảng aggregate đã kiểm hash, không cần raw để trình bày. Notebook [final_report.ipynb](../../M2/notebooks/final_report.ipynb) dùng cùng hàm đọc báo cáo. Có thể mở HTML offline trực tiếp.

```powershell
.\.venv\Scripts\python.exe -B -m pytest
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m M2.final_report --help
# Kiểm raw/nhãn/metric/log/hash của run lịch sử, không refit hoặc ghi đè receipt.
.\.venv\Scripts\python.exe -m M2.final_report --run-id m2_final_20261011_local --stage verify-artifacts
```

Lệnh fit/refit, forecast và export sang run mới tại [bản đồ code](../../M2_CODE_MAP.md#lệnh-dùng-tại-root-project). Raw và artifact cha chỉ có local; không chạy training/sweep tự động để mở dashboard. Mỗi run mới giữ manifest/source/code/config/seed/version riêng; run/báo cáo cũ không bị ghi đè.

Tổng D+1…D+7 có 10/10 tuyến dưới 20%, mean 15,745366%, coverage 100%; h8–14 có 8/10. Chín tuyến giữ lựa chọn validation; LG U+ được chọn sau test-sweep nên test hồi cứu. Metric tổng 7 không thay nghiệm thu R05 theo ngày. R05/R07/T14 còn mở; M01/M02 là xác nhận mentor do người dùng thuật lại, A08–A17 vẫn là đề xuất/giả định.

Các luồng M1/M3, SARIMA, sweep, notebook thử nghiệm và CLI cũ đã bỏ khỏi nhánh cleanup. Dữ liệu nguồn, run, forecast, manifest, Word/PDF và tài liệu nghiên cứu được bảo toàn. [Cách so sánh và khôi phục từng file](../../M2_CODE_MAP.md#khôi-phục-code-cũ) từ `backup/m2-before-cleanup`; hướng dẫn cũ còn trong tài liệu lịch sử chỉ áp dụng cho nhánh backup. Người dùng cho phép push nhánh M2-final-cleanup ngày14/10/2026; không merge/deploy.

[AGENTS](../../AGENTS.md) · [Tiến độ](../planning/TASK.md) · [PLAN](../planning/PLAN.md) · [Yêu cầu](../requirements.md) · [Hợp đồng dữ liệu](../data-contract.md) · [Nhật ký bằng chứng](../review-log.md).
