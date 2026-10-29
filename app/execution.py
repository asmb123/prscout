from __future__ import annotations

import subprocess
import time
from pathlib import Path

from app.config import CommandConfig
from app.models import CheckResult


def run_command(command: CommandConfig, cwd: Path, output_limit: int = 20_000) -> CheckResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [command.command], cwd=cwd, capture_output=True, text=True,
            timeout=command.timeout_seconds, check=False,
        )
        return CheckResult(command.command, completed.returncode, completed.stdout[:output_limit],
                           completed.stderr[:output_limit], time.monotonic() - started)
    except subprocess.TimeoutExpired as exc:
        return CheckResult(command.command, None, str(exc.stdout or "")[:output_limit],
                           str(exc.stderr or "")[:output_limit], time.monotonic() - started, True)
