# Cập nhật web local từ main

Mã React/API/auth/sổ kho dùng chung nhánh `main`. Dữ liệu, tài khoản, PostgreSQL, `.env` và bản build của mỗi máy vẫn ở máy đó: push GitHub không tự cập nhật DB hay web đang chạy trên máy khác. Mỗi lần kéo bản mới, làm đủ các bước dưới đây trên máy của mình.

Bản hiện hành (19/11/2026) cần DB ở migration **`0017_item_forecast_basis_date`**. Khi DB còn cũ, API vẫn khởi động nhưng `/api/v1/ready` trả 503 và giao diện không dùng được cho tới khi chạy migration ở bước 4.

## 1. Trước khi cập nhật

- Chờ công việc đang chạy kết thúc, dừng API/worker bằng launcher hoặc terminal đã mở chúng. Nếu dùng `web/backend/scripts/start_m3.ps1`, dừng bằng `web/backend/scripts/stop_m3.ps1`. Không dừng toàn bộ Python/PostgreSQL của máy.
- **Sao lưu DB, bắt buộc.** Migration `0016` bỏ các cột hash cũ của `runs`; quay lui không khôi phục được hết, nên bản sao lưu là đường quay lại duy nhất. Với `pg_dump` cùng phiên bản PostgreSQL của máy (thay host, cổng, user, tên DB theo `.env` của bạn; lệnh hỏi mật khẩu):

  ```powershell
  pg_dump -h 127.0.0.1 -p 55432 -U sigma_m3_app -d sigma_m3 -Fc -f sigma_m3_before_update.dump
  ```

  Kiểm tệp `.dump` có dung lượng hợp lý trước khi đi tiếp. Lưu tệp ngoài repo hoặc trong `outputs/` (đã được Git bỏ qua). Có thể dùng pgAdmin thay cho lệnh trên.
- Giữ nguyên `.env`, dữ liệu nguồn và thư mục artifact. Không chạy reset/seed trên DB đang dùng.
- Kiểm `git status`. Nếu có sửa chưa commit, lưu công việc của bạn trước; không dùng `reset --hard`, `clean` hoặc ghi đè để ép cập nhật.

## 2. Kéo main

Tại thư mục repo:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git log -1 --oneline
```

Nếu pull báo diverged/conflict, dừng và đối chiếu phần sửa của thành viên trước. Không force-push.

## 3. Dependency và giao diện

Dùng Python 3.12 và môi trường `.venv-m3` của dự án. Nếu chưa có môi trường:

```powershell
py -3.12 -m venv .venv-m3
```

Sau đó cài lại cả khi đã có môi trường, vì bản mới có thể thêm thư viện (ví dụ `pwdlib` cho đăng nhập):

```powershell
.\.venv-m3\Scripts\python.exe -m pip install -r web/backend/requirements.txt
.\.venv-m3\Scripts\python.exe -m pip install --no-deps -e web/backend
.\.venv-m3\Scripts\python.exe -m pip check
```

Chỉ tiếp tục khi từng lệnh thành công. Với Node 24/npm:

```powershell
Push-Location web/frontend
npm ci
npm run build
Pop-Location
```

Build tạo `web/frontend/dist` local; không commit thư mục này. API phục vụ bản build nên phải build lại, không chỉ pull code.

## 4. Cập nhật DB và đăng nhập

PostgreSQL phải đang chạy. Giữ cấu hình `web/backend/.env` của máy; xem mẫu ở [configs](../web/backend/configs/.env.example), không sao chép credential của máy khác. Nạp biến môi trường vào cùng terminal:

```powershell
. .\web\backend\scripts\load_env.ps1
.\.venv-m3\Scripts\python.exe -m alembic -c web/backend/alembic.ini current
.\.venv-m3\Scripts\python.exe -m alembic -c web/backend/alembic.ini upgrade head
.\.venv-m3\Scripts\python.exe -m alembic -c web/backend/alembic.ini current
```

Lệnh `current` cuối phải in `0017_item_forecast_basis_date (head)`. `upgrade head` chạy lần lượt mọi migration còn thiếu và an toàn khi chạy lại. Các migration từ bản 15/11 trở đi:

| Migration | Ảnh hưởng tới DB của bạn |
| --- | --- |
| `0010_auth_sessions`, `0011_operational_inventory` | Thêm bảng đăng nhập và sổ kho. Không đổi dữ liệu nguồn hoặc run cũ. |
| `0012_dealers` | Thêm đại lý và yêu cầu lấy hàng. **Tài khoản nhà cung cấp cũ bị khóa và không mở lại được**; admin cấp tài khoản đại lý thay thế. |
| `0013_adjustable_eta`, `0014_supplier_lead_simulation` | Cho phép đổi ngày dự kiến nhận và thời gian nhập theo nhà cung cấp (1–13 ngày trong mô phỏng). Dữ liệu cũ giữ nguyên. |
| `0015_item_policies` | Đổi tên bảng cấu hình (`supplier_item_policies` → `item_policies`, `ops_supplier_settings` → `supplier_settings`). Dữ liệu giữ nguyên. |
| `0016_run_tables` | Tách `runs` thành `run_configs` và `run_results`, bỏ các cột hash kiểm chứng. Run cũ vẫn đọc được; quay lui không khôi phục hash. |
| `0017_item_forecast_basis_date` | Thêm cột ngày basis cho phân bổ dự báo (để trống với run cũ). |

Nếu một migration báo lỗi, dừng lại, giữ nguyên thông báo lỗi và khôi phục từ bản sao lưu nếu cần (bước 6); không sửa tay bảng để vượt lỗi.

Nếu DB chưa có admin, tạo một lần:

```powershell
.\.venv-m3\Scripts\python.exe -m modules.auth.bootstrap
```

Lệnh hỏi tên đăng nhập và mật khẩu (tối thiểu 12 ký tự) riêng tại terminal. Không có mật khẩu mặc định. Nếu admin đã có, không tạo lại; dùng tài khoản được cấp. Quên mật khẩu admin thì người có quyền truy cập DB chạy `python -m modules.auth.reset_password` trong cùng terminal đã nạp `.env`. [Chi tiết đăng nhập](AUTHENTICATION.md).

## 5. Mở web và kiểm tra

```powershell
.\web\backend\scripts\start_m3.ps1 -Port 8000
```

Mở **http://127.0.0.1:8000/**. Dùng cổng khác nếu máy đang dùng 8000; không dừng dịch vụ khác để chiếm cổng. Launcher khởi động API/worker nền và dùng DB đã cấu hình. Sau mỗi lần pull có sửa backend, dừng rồi chạy lại launcher; trình duyệt cần tải lại trang (F5) để nhận bản build mới.

- Đăng nhập admin. Menu bên trái gồm các nhóm sổ xuống: **Kho** (Tồn kho, Chứng từ, Kho hàng), **Nhập hàng** (Đơn nhập, Đề xuất nhập), **Đại lý**, **Danh mục** (Sản phẩm, Nhà cung cấp), **Hệ thống** (Lịch sử thao tác, Tài khoản) và **Công cụ dự báo** (Dự báo, Kịch bản và các trang mô phỏng).
- Kiểm lại một kết quả kế hoạch đã lưu trong Công cụ dự báo, chưa cần chạy lại mô hình.
- Sổ kho mới chưa có kho, sản phẩm hay số dư là đúng; không tự biến tồn mô phỏng thành hàng thực. Thêm kho ở Kho › Kho hàng, sản phẩm ở Danh mục › Sản phẩm, rồi nhận hàng hoặc kiểm kê. Chỉ tạo chứng từ thử trên DB thử riêng, tránh ghi nhầm DB đang dùng.
- Tài khoản đại lý: tạo đại lý ở Đại lý › Danh sách đại lý rồi bấm **Cấp tài khoản**; khóa/mở khóa ở Hệ thống › Tài khoản. Mỗi tài khoản đại lý chỉ thấy sản phẩm, yêu cầu và hàng đã nhận của đại lý đó.
- Đề xuất nhập cần chính sách nhập của sản phẩm (Danh mục › Sản phẩm › Chính sách nhập). Khi chưa có dự báo cho ngày hiện tại, trang tính theo ngưỡng cố định và ghi rõ trên từng dòng.

### Dữ liệu thử dùng chung

Dữ liệu một thành viên tạo trên máy mình không đi kèm code. Để mọi người có cùng kiểu dữ liệu giả lập, chạy công cụ [seed_dev_data.py](../web/backend/scripts/seed_dev_data.py) trên **DB thử còn trống** (đã chạy bước 4 và đã có admin):

```powershell
. .\web\backend\scripts\load_env.ps1
.\.venv-m3\Scripts\python.exe web\backend\scripts\seed_dev_data.py --yes
```

- Cần bản CSV order của nhóm tại `<M3_SOURCE_ROOT>/data/sigma_sim_data_orders.csv`, hoặc truyền `--csv <đường dẫn>`. Thư mục `data/` không có trên GitHub.
- Script tạo 3 kho, mọi sản phẩm trong CSV kèm chính sách nhập, thời gian nhập giả lập 3–10 ngày cho nhà cung cấp chưa cấu hình, tồn đầu kỳ và phiếu bán của 24 sản phẩm bán chạy, đơn nhập ở nhiều trạng thái, 3 đại lý cùng tài khoản và yêu cầu lấy hàng. Mọi ghi chú có nhãn `[Dữ liệu giả lập]`.
- Mật khẩu tài khoản đại lý được sinh ngẫu nhiên và ghi vào `outputs/dev_seed/dealer-accounts.private.txt` (Git bỏ qua).
- Số liệu gần giống giữa các máy chứ không trùng khớp: mốc bắt đầu là 3 ngày trước ngày chạy, phiếu bán ghi tới hôm nay.
- Script từ chối chạy khi thiếu `--yes` hoặc khi sổ kho đã có kho/sản phẩm, nên không ghi chồng lên DB đang dùng. Muốn nạp lại, khôi phục DB trống hoặc tạo DB thử mới.

Bản sao lưu `.dump` của người khác chỉ dùng khi cả nhóm đồng ý chia sẻ, vì nó chứa tài khoản và dữ liệu của máy đó; không đưa tệp này lên GitHub.

Nếu trước đây dùng launcher demo `src/start_demo.py` có `prepared.json`, không sửa fingerprint để vượt thông báo `Runtime changed`. Cần cập nhật runtime đã duyệt sau backup/rehearsal; hướng dẫn này không tự chứng minh demo riêng đó đã được nâng cấp.

## 6. Quay lại bản trước khi cập nhật

Khi migration hỏng hoặc cần trả DB về trạng thái trước: dừng launcher, tạo một DB trống mới (giữ DB cũ để đối chiếu), khôi phục bản sao lưu vào đó rồi trỏ `M3_DATABASE_URL` trong `.env` sang DB mới. Ví dụ:

```powershell
createdb -h 127.0.0.1 -p 55432 -U sigma_m3_app sigma_m3_restore
pg_restore -h 127.0.0.1 -p 55432 -U sigma_m3_app -d sigma_m3_restore --no-owner sigma_m3_before_update.dump
```

Sau đó checkout lại commit tương ứng với DB đã khôi phục, cài dependency và build lại như bước 3, hoặc chạy lại bước 4 để nâng DB khôi phục lên bản mới.

Phần đã có và giới hạn: [bảng trạng thái hiện hành](PRODUCT_STATUS.md), [giới hạn sổ kho](WAREHOUSE_OPERATIONS.md#phần-còn-thiếu). QR phiếu giao, Redis tùy chọn và tư vấn nhập đã có; host public và chứng minh tiêu chí dự báo trên dữ liệu nhóm vẫn chưa hoàn tất. Nếu bật Redis, cấu hình API và worker cùng driver/namespace theo [hướng dẫn queue](REDIS_QUEUE.md); không chạy song song hai worker của hai driver trên cùng stack.
