from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Power Monitor"
DEFAULT_BASELINE_WATTS = 35.0
UPDATE_INTERVAL_MS = 1000
TASK_NAME = "PowerMonitorDesktop"
DLL_NAME = "LibreHardwareMonitorLib.dll"
SETTINGS_DIR_NAME = "PowerMonitorDesktop"
SETTINGS_FILE_NAME = "settings.json"
DEFAULT_DISPLAY_MODE = "overlay"
DEFAULT_WATT_FONT_SIZE = 42
DEFAULT_TEXT_COLOR_NAME = "White"


@dataclass(frozen=True)
class AppConfig:
    baseline_watts: float = DEFAULT_BASELINE_WATTS
    update_interval_ms: int = UPDATE_INTERVAL_MS
    always_on_top: bool = True
    display_mode: str = DEFAULT_DISPLAY_MODE
    watt_font_size: int = DEFAULT_WATT_FONT_SIZE
    text_color_name: str = DEFAULT_TEXT_COLOR_NAME


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


def settings_file_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME
    return Path.home() / ".config" / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME


def load_saved_config(path: Path | None = None) -> AppConfig:
    settings_path = path or settings_file_path()
    try:
        raw_data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw_data = {}

    return AppConfig(
        baseline_watts=_read_float(raw_data, "baseline_watts", DEFAULT_BASELINE_WATTS),
        update_interval_ms=UPDATE_INTERVAL_MS,
        always_on_top=_read_bool(raw_data, "always_on_top", True),
        display_mode=_read_display_mode(raw_data.get("display_mode")),
        watt_font_size=_read_int(raw_data, "watt_font_size", DEFAULT_WATT_FONT_SIZE),
        text_color_name=_read_string(raw_data, "text_color_name", DEFAULT_TEXT_COLOR_NAME),
    )


def save_config(config: AppConfig, path: Path | None = None) -> None:
    settings_path = path or settings_file_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "baseline_watts": max(0.0, config.baseline_watts),
        "always_on_top": config.always_on_top,
        "display_mode": _read_display_mode(config.display_mode),
        "watt_font_size": max(1, config.watt_font_size),
        "text_color_name": config.text_color_name,
    }
    settings_path.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_config_from_env() -> AppConfig:
    config = load_saved_config()
    baseline = config.baseline_watts
    raw_baseline = os.getenv("POWER_MONITOR_BASELINE_WATTS")
    if raw_baseline:
        try:
            baseline = max(0.0, float(raw_baseline))
        except ValueError:
            baseline = config.baseline_watts

    return AppConfig(
        baseline_watts=baseline,
        update_interval_ms=config.update_interval_ms,
        always_on_top=config.always_on_top,
        display_mode=config.display_mode,
        watt_font_size=config.watt_font_size,
        text_color_name=config.text_color_name,
    )


def _read_float(data: dict[str, object], key: str, default: float) -> float:
    try:
        return max(0.0, float(data.get(key, default)))
    except (TypeError, ValueError):
        return default


def _read_int(data: dict[str, object], key: str, default: int) -> int:
    try:
        return int(float(data.get(key, default)))
    except (TypeError, ValueError):
        return default


def _read_bool(data: dict[str, object], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "on"}
    return default


def _read_string(data: dict[str, object], key: str, default: str) -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) and value else default


def _read_display_mode(value: object) -> str:
    if isinstance(value, str) and value in {"overlay", "panel"}:
        return value
    return DEFAULT_DISPLAY_MODE
