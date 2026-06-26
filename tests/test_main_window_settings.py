from app.config import AppConfig
from app import main as main_module
from app.main import (
    PowerMonitorApp,
    clamp_font_size,
    overlay_settings,
    overlay_window_size,
    panel_settings,
)


def test_overlay_settings_are_high_contrast_and_transparent() -> None:
    settings = overlay_settings()

    assert settings.transparent_color == "#010203"
    assert settings.text_fill == "#ffffff"
    assert settings.text_outline == "#000000"
    assert ("White", "#ffffff") in settings.text_colors
    assert ("Amber", "#facc15") in settings.text_colors
    assert ("Cyan", "#22d3ee") in settings.text_colors
    assert settings.default_font_size == 42
    assert settings.min_font_size == 18
    assert settings.max_font_size == 120
    assert settings.always_on_top is True


def test_panel_settings_restore_full_control_menu_size() -> None:
    settings = panel_settings()

    assert settings.geometry == "400x480"
    assert settings.min_width == 340
    assert settings.min_height == 450


def test_overlay_window_size_scales_with_watt_text_and_font_size() -> None:
    assert overlay_window_size("198.3 W", 42) == (228, 75)
    assert overlay_window_size("1000.0 W", 72) == (403, 113)


def test_clamp_font_size_keeps_adjustment_in_readable_range() -> None:
    settings = overlay_settings()

    assert clamp_font_size(10, settings) == 18
    assert clamp_font_size(64, settings) == 64
    assert clamp_font_size(140, settings) == 120


def test_scheduled_refresh_reads_power_on_each_tick() -> None:
    root = FakeRoot()
    app = PowerMonitorApp.__new__(PowerMonitorApp)
    app.root = root
    app.config = AppConfig(update_interval_ms=1000)
    app._after_id = None
    app.refresh_count = 0

    def refresh_now() -> None:
        app.refresh_count += 1

    app.refresh_now = refresh_now

    app._schedule_refresh()

    assert app.refresh_count == 1
    assert root.delay_ms == 1000
    assert root.callback == app._schedule_refresh


def test_startup_task_status_check_keeps_checkbox_selectable(monkeypatch) -> None:
    root = FakeRoot()
    app = PowerMonitorApp.__new__(PowerMonitorApp)
    app.root = root
    app._closed = False
    app._startup_task_busy = False
    app.startup_enabled_var = FakeVar(False)
    app.status_var = FakeVar("")
    app.startup_task_checkbutton = FakeCheckbutton()

    class ImmediateThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    monkeypatch.setattr(main_module, "is_startup_task_installed", lambda: True)
    monkeypatch.setattr(main_module.threading, "Thread", ImmediateThread)

    app._check_startup_task_async()

    assert app.startup_enabled_var.get() is True
    assert app.startup_task_checkbutton.state == "normal"


class FakeRoot:
    def __init__(self) -> None:
        self.delay_ms: int | None = None
        self.callback = None

    def after(self, delay_ms: int, callback):
        self.delay_ms = delay_ms
        self.callback = callback
        if delay_ms == 0:
            callback()
        return "after-id"


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class FakeCheckbutton:
    def __init__(self) -> None:
        self.state = "normal"

    def configure(self, **kwargs) -> None:
        self.state = kwargs.get("state", self.state)
