"""Create the first admin interactively; passwords are never CLI arguments."""
import getpass
from sqlalchemy import select, text
from core.db import database
from core.settings import Settings
from models import User  # Register all foreign-key targets for standalone bootstrap.
from modules.auth.schemas import UserCreate
from modules.auth.service import create_user


def main():
    settings = Settings.from_env()
    username = input("Tên đăng nhập admin: ").strip()
    name = input("Tên hiển thị: ").strip()
    password = getpass.getpass("Mật khẩu (ít nhất 12 ký tự): ")
    if password != getpass.getpass("Nhập lại mật khẩu: "):
        raise SystemExit("Mật khẩu không khớp.")
    payload = UserCreate(username=username, display_name=name, password=password, role="admin")
    engine, sessions = database(settings.database_url)
    try:
        with sessions.begin() as session:
            session.execute(text("SELECT pg_advisory_xact_lock(1900010010)"))
            if session.scalar(select(User.id).where(User.role == "admin")) is not None:
                raise SystemExit("Admin đã tồn tại. Dùng màn hình quản lý tài khoản.")
            create_user(session, payload)
        print("Đã tạo admin. Không có mật khẩu mặc định.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
