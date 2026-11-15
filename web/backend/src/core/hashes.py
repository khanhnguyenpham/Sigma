"""Stable JSON digest and fingerprints of the current source checkout."""
import hashlib
import json
import os
import re
from core.settings import PROJECT_ROOT


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False
        ).encode()
    ).hexdigest()


def code_digest():
    reference = runtime_reference()
    if reference:
        # Legacy storage token; production identity comes from the immutable release, not a file scan.
        return digest(reference)
    project = PROJECT_ROOT
    paths = [
        p
        for folder in ["web/backend/src", "src", "M2/models"]
        for p in (project / folder).rglob("*.py")
    ]
    paths.append(project / "M2/final_report.py")
    paths.append(project / "web/backend/scripts/demo_stack.py")
    return digest(
        {
            p.relative_to(project).as_posix(): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sorted(paths)
        }
    )


def revision():
    reference = runtime_reference()
    if reference:
        return reference['version']
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


def runtime_reference():
    version = os.environ.get('M3_RELEASE_VERSION','')
    if not version:
        return None
    if len(version)>64 or not re.fullmatch(r'(?:[a-f0-9]{40}|v\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)',version):
        raise ValueError('M3_RELEASE_VERSION requires a commit SHA or semantic release version')
    return {'mode':'immutable-release-v1','version':version}
