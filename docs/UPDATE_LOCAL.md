# Cập nhật web local từ main

Bản nâng cấp ngày15/11/2026 được đưa vào `main` theo yêu cầu nhóm. Mã React/API/auth/sổ kho dùng chung nhánh này; dữ liệu, tài khoản, PostgreSQL, `.env` và bản build của mỗi máy vẫn ở máy đó. Push GitHub không tự cập nhật một web đang chạy trên máy khác.

## 1. Trước khi cập nhật

- Chờ công việc đang chạy kết thúc, dừng API/worker bằng launcher hoặc terminal đã mở chúng. Nếu dùng `web/backend/scripts/start_m3.ps1`, dừng bằng `web/backend/scripts/stop_m3.ps1`. Không dừng toàn bộ Python/PostgreSQL của máy.
- Sao lưu DB hiện tại bằng công cụ PostgreSQL/pgAdmin đang dùng, kiểm backup thành công. Giữ nguyên `.env`, dữ liệu nguồn và thư mục artifact. Không chạy reset/seed trên DB đang dùng.
- Kiểm `git status`. Nếu có sửa chưa commit, lưu công việc của bạn trước; không dùng `reset --hard`, `clean` hoặc ghi đè để ép cập nhật.

## 2. Kéo main

Tại thư mục repo:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git log -1 --oneline
```

Nếu pull báo diverged/conflict, dừng và đối chiếu phần sửa của thành viên trước. Không force-push. Commit tính năng nền là `0d31923`; có thể có commit tài liệu/bảo trì mới hơn trên main.

## 3. Dependency và giao diện

Dùng Python3.12 và môi trường `.venv-m3` của dự án. Nếu chưa có môi trường:

```powershell
py -3.12 -m venv .venv-m3
```

Sau đó:

```powershell
.\.venv-m3\Scripts\python.exe -m pip install -r web/backend/requirements.txt
.\.venv-m3\Scripts\python.exe -m pip install --no-deps -e web/backend
.\.venv-m3\Scripts\python.exe -m pip check
```

Chỉ tiếp tục khi từng lệnh thành công. Với Node24/npm:

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

Head của bản nâng cấp này là `0011_operational_inventory`. Migration thêm bảng đăng nhập và sổ kho, không reset dữ liệu nguồn hoặc run cũ. Nếu chưa có admin, tạo một lần:

```powershell
.\.venv-m3\Scripts\python.exe -m modules.auth.bootstrap
```

Lệnh hỏi mật khẩu riêng tại terminal. Không có mật khẩu mặc định. Nếu admin đã có, không tạo lại; dùng tài khoản được cấp. [Chi tiết đăng nhập](AUTHENTICATION.md).

## 5. Mở web và kiểm tra

```powershell
.\web\backend\scripts\start_m3.ps1 -Port 8000
```

Mở **http://127.0.0.1:8000/**. Dùng cổng khác nếu máy đang dùng8000; không dừng dịch vụ khác để chiếm cổng. Launcher khởi động API/worker nền và dùng DB đã cấu hình.

- Đăng nhập admin: có **Vận hành kho**, **Đơn nhập**, **Chứng từ** và các màn hình kế hoạch cũ.
- Kiểm lại một kết quả kế hoạch đã lưu, chưa cần chạy lại mô hình.
- Sổ kho mới chưa có số dư là đúng; không tự biến tồn mô phỏng thành hàng thực. Chỉ tạo phiếu nhận/xuất/kiểm kê thử trên môi trường thử riêng, tránh ghi nhầm DB đang dùng.
- Supplier chỉ thấy dữ liệu thuộc tài khoản của mình. Admin có thể tạo tài khoản qua menu tài khoản.

Nếu trước đây dùng launcher demo `src/start_demo.py` có `prepared.json`, không sửa fingerprint để vượt thông báo `Runtime changed`. Cần cập nhật runtime đã duyệt sau backup/rehearsal; hướng dẫn này không tự chứng minh demo riêng đó đã được nâng cấp.

Phần đã có và giới hạn: [bảng trạng thái hiện hành](PRODUCT_STATUS.md), [giới hạn sổ kho](WAREHOUSE_OPERATIONS.md#phần-còn-thiếu). QR phiếu giao, Redis tùy chọn và tư vấn nhập đã có; host public và chứng minh tiêu chí dự báo trên dữ liệu nhóm vẫn chưa hoàn tất. Nếu bật Redis, cấu hình API và worker cùng driver/namespace theo [hướng dẫn queue](REDIS_QUEUE.md); không chạy song song hai worker của hai driver trên cùng stack.
