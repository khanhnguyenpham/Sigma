"""Run each operator command in a fresh Python process against the test database."""
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import select

from modules.auth.models import User
from modules.auth.service import PASSWORDS


def test_standalone_auth_commands_create_admin_and_reset_password(pg, tmp_path):
    engine, sessions = pg
    source = Path(__file__).resolve().parents[1] / "src"
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("M3_")}
    env.update(
        M3_DATABASE_URL=engine.url.render_as_string(hide_password=False),
        PYTHONPATH=str(source),
        PYTHONIOENCODING="utf-8",
    )
    initial_password = "Synthetic-Bootstrap-2026"
    new_password = "Synthetic-Recovery-2026"

    def run(module, *answers):
        # Substitute stdin for getpass so the child never reads the operator's terminal.
        script = f"""
from unittest.mock import patch
from modules.auth import {module} as command

with patch.object(command.getpass, 'getpass', input):
    command.main()
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=tmp_path, env=env, input="\n".join(answers) + "\n",
            capture_output=True, encoding="utf-8", timeout=30,
        )
        assert result.returncode == 0, result.stderr

    run("bootstrap", "test-admin", "Synthetic admin", initial_password, initial_password)
    with sessions() as session:
        admin = session.scalars(select(User)).one()
        assert (admin.username, admin.role, admin.supplier_id, admin.dealer_id, admin.active) == (
            "test-admin", "admin", None, None, True,
        )
        assert PASSWORDS.verify(initial_password, admin.password_hash)

    run("reset_password", "test-admin", new_password, new_password)
    with sessions() as session:
        admin = session.scalars(select(User)).one()
        assert PASSWORDS.verify(new_password, admin.password_hash)
