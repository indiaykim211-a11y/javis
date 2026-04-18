from __future__ import annotations

import subprocess


class PowerShellError(RuntimeError):
    """Raised when a PowerShell command fails."""


def run_powershell(script: str, timeout: int = 25) -> str:
    prefixed_script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$OutputEncoding = [System.Text.Encoding]::UTF8; "
        + script
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", prefixed_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "PowerShell failed."
        raise PowerShellError(message)
    return completed.stdout.strip()
