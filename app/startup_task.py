from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

from app.config import TASK_NAME, project_root


def startup_exe_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return project_root() / "dist" / "power-monitor.exe"


def is_startup_task_installed() -> bool:
    if platform.system() != "Windows":
        return False

    result = _run_powershell(
        f"$Task = Get-ScheduledTask -TaskName {_ps_quote(TASK_NAME)} "
        "-ErrorAction SilentlyContinue; if ($null -eq $Task) { exit 1 }"
    )
    return result.returncode == 0


def set_startup_task_enabled(enabled: bool) -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Startup task is only supported on Windows.")

    if enabled:
        _install_startup_task()
    else:
        _uninstall_startup_task()


def _install_startup_task() -> None:
    exe_path = startup_exe_path()
    if not exe_path.exists():
        raise FileNotFoundError(
            f"Missing {exe_path}. Build the exe before enabling startup."
        )

    working_dir = exe_path.parent.parent if exe_path.parent.name == "dist" else exe_path.parent
    script = f"""
$TaskName = {_ps_quote(TASK_NAME)}
$ExePath = {_ps_quote(str(exe_path))}
$WorkingDirectory = {_ps_quote(str(working_dir))}
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Action = New-ScheduledTaskAction -Execute $ExePath -WorkingDirectory $WorkingDirectory
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 0)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Start Power Monitor desktop app when the current user logs on." -Force | Out-Null
"""
    result = _run_powershell(script)
    if result.returncode != 0:
        raise RuntimeError(_powershell_error(result))


def _uninstall_startup_task() -> None:
    script = (
        f"Unregister-ScheduledTask -TaskName {_ps_quote(TASK_NAME)} "
        "-Confirm:$false -ErrorAction SilentlyContinue"
    )
    result = _run_powershell(script)
    if result.returncode != 0:
        raise RuntimeError(_powershell_error(result))


def _run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        check=False,
        **_hidden_subprocess_options(),
        text=True,
        timeout=30,
    )


def _powershell_error(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr or result.stdout or "PowerShell command failed.").strip()


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _hidden_subprocess_options() -> dict[str, object]:
    if platform.system() != "Windows":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }
