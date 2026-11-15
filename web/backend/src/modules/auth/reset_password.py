"""Recovery from an operator terminal with DB access; never takes passwords as arguments."""
import getpass
from core.db import database
from core.settings import Settings
from core.errors import DomainError
from modules.auth.service import operator_reset_password


def main():
    username = input('Tên đăng nhập cần khôi phục: ').strip().lower()
    password = getpass.getpass('Mật khẩu mới (12–128 ký tự): ')
    if password != getpass.getpass('Nhập lại mật khẩu mới: '):
        raise SystemExit('Mật khẩu không khớp.')
    engine, sessions = database(Settings.from_env().database_url)
    try:
        with sessions.begin() as session:
            operator_reset_password(session, username, password)
    except DomainError as failure:
        raise SystemExit(failure.message) from None
    finally:
        engine.dispose()
    print('Đã đặt lại mật khẩu và thu hồi các phiên đăng nhập. Tài khoản đã khóa vẫn giữ trạng thái khóa.')


if __name__ == '__main__':
    main()
