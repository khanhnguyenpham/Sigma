# Gói chạy local bằng container

Gói `compose.local.yml` dùng cùng image cho API và worker, PostgreSQL18 và hai volume bền cho DB/artifact. React build trong image; không mang theo `.venv`, node_modules, DB, CSV nguồn hoặc outputs của người làm. Đây là lựa chọn chạy **local**, chưa phải bằng chứng host public đã triển khai. Máy hiện tại chưa có Docker nên cần kiểm build/compose trong CI trước khi nhận gói dùng được.

## Môi trường mới

Cần Docker Engine/Desktop với ComposeV2 và RAM phù hợp mô hình. Không tự cài Docker hoặc nâng gói hosting. Copy `web/deploy/.env.example` thành `.env` cùng thư mục, thay hai mật khẩu placeholder bằng hai chuỗi hex ngẫu nhiên độc lập. App dùng role `sigma` không superuser; `sigma_admin` chỉ dành khởi tạo/quản trị. Không gửi hoặc commit file thật.

Tại root repo:

```powershell
docker compose --env-file web/deploy/.env -f compose.local.yml config --quiet
docker compose --env-file web/deploy/.env -f compose.local.yml up -d database
docker compose --env-file web/deploy/.env -f compose.local.yml build
docker compose --env-file web/deploy/.env -f compose.local.yml --profile setup run --rm migrate
docker compose --env-file web/deploy/.env -f compose.local.yml run --rm api python -m modules.auth.bootstrap
docker compose --env-file web/deploy/.env -f compose.local.yml up -d api
```

Chỉ tiếp tục sau khi mỗi lệnh thành công. Mở http://127.0.0.1:8000/ và dùng admin vừa tạo. Đây là DB local **mới** trong volume Compose, không tự lấy DB hiện có của thành viên. Nếu muốn giữ DB cũ, dùng [cập nhật local hiện có](UPDATE_LOCAL.md) hoặc backup/restore riêng, không trỏ nhầm DB rồi seed lại.

`SIGMA_DATA_DIR` trỏ thư mục có nguồn riêng được phép dùng; mount chỉ đọc. Không có nguồn hiện tại thì phần dự báo không tự hoạt động bằng dữ liệu giả. Khi đã chuẩn bị dữ liệu và muốn chạy công việc, bật worker có chủ ý:

```powershell
docker compose --env-file web/deploy/.env -f compose.local.yml --profile jobs up -d worker
```

Không tự enqueue/refit khi khởi động. Hàng đợi hiện vẫn PostgreSQL; chưa có Redis transport trong gói này. API chỉ bind loopback; chưa mở public hoặc cấu hình HTTPS. Không dùng health DB/API để khẳng định model/artifact đã sẵn sàng.

## Nâng cấp và bảo toàn

Dừng API/worker đúng stack và đợi công việc kết thúc; backup DB bằng `pg_dump` của container database18, đồng thời sao lưu volume artifact. Khi restore phải đối chiếu cả hai phần. Sau đó pull main/build/migrate/start; không đổi mật khẩu volume hiện có để thử sửa lỗi kết nối. Không chạy `down -v`, reset hoặc xóa volume để cập nhật.

Đổi mật khẩu người dùng tại menu tài khoản. Khôi phục khi quên bằng `docker compose ... run --rm api python -m modules.auth.reset_password` từ terminal operator có quyền DB; không đặt mật khẩu trong tham số hoặc chia sẻ log env.

Container hiện giữ cơ chế fingerprint/queue cũ. Chưa hoàn thành Redis, tối ưu hiệu năng có benchmark, backup/restore rehearsal của gói mới hoặc hosting24/7. Không công bố image nhỏ/nhanh hơn khi chưa đo.

Đối chiếu kỹ thuật: [volume PostgreSQL18 chính thức](https://hub.docker.com/_/postgres) dùng mount `/var/lib/postgresql`; [psql18](https://www.postgresql.org/docs/18/app-psql.html) đọc mật khẩu app từ env bằng `\getenv`, không ghi credential thật trong SQL nguồn hoặc tham số lệnh.
