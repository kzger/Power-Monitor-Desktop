from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Power Monitor"
DEFAULT_BASELINE_WATTS = 35.0
UPDATE_INTERVAL_MS = 1000
TASK_NAME = "PowerMonitorDesktop"
DLL_NAME = "LibreHardwareMonitorLib.dll"


@dataclass(frozen=True)
class AppConfig:
    baseline_watts: float = DEFAULT_BASELINE_WATTS
    update_interval_ms: int = UPDATE_INTERVAL_MS
    always_on_top: bool = True


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def bundled_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return project_root()


def libre_hardware_monitor_dll_path() -> Path:
    return bundled_root() / "vendor" / DLL_NAME


def load_config_from_env() -> AppConfig:
    baseline = DEFAULT_BASELINE_WATTS
    raw_baseline = os.getenv("POWER_MONITOR_BASELINE_WATTS")
    if raw_baseline:
        try:
            baseline = max(0.0, float(raw_baseline))
        except ValueError:
            baseline = DEFAULT_BASELINE_WATTS

    return AppConfig(baseline_watts=baseline)
