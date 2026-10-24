"""Stable JSON digest and fingerprints of the current source checkout."""
import hashlib
import json
from sigma_m3.core.settings import PROJECT_ROOT


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False
        ).encode()
    ).hexdigest()


def code_digest():
    project = PROJECT_ROOT
    paths = [
        p
        for folder in ["web/backend/src/sigma_m3", "src", "M2/models"]
        for p in (project / folder).rglob("*.py")
    ]
    paths.append(project / "M2/final_report.py")
    return digest(
        {
            p.relative_to(project).as_posix(): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sorted(paths)
        }
    )


def revision():
    import subprocess
    import shutil

    try:
        executable = shutil.which("git") or "F:/code/Git/cmd/git.exe"
        return subprocess.check_output(
            [executable, "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted-source"
