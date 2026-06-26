import json

from app.config import AppConfig, load_config_from_env, load_saved_config, save_config


def test_saved_config_round_trips_user_preferences(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    config = AppConfig(
        baseline_watts=48.5,
        always_on_top=False,
        display_mode="panel",
        watt_font_size=72,
        text_color_name="Cyan",
    )

    save_config(config, settings_path)
    loaded = load_saved_config(settings_path)

    assert loaded.baseline_watts == 48.5
    assert loaded.always_on_top is False
    assert loaded.display_mode == "panel"
    assert loaded.watt_font_size == 72
    assert loaded.text_color_name == "Cyan"


def test_saved_config_falls_back_when_file_is_invalid(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not valid json", encoding="utf-8")

    loaded = load_saved_config(settings_path)

    assert loaded == AppConfig()


def test_env_baseline_override_keeps_saved_preferences(tmp_path, monkeypatch) -> None:
    settings_dir = tmp_path / "PowerMonitorDesktop"
    settings_dir.mkdir()
    (settings_dir / "settings.json").write_text(
        json.dumps(
            {
                "baseline_watts": 41,
                "always_on_top": False,
                "display_mode": "panel",
                "watt_font_size": 64,
                "text_color_name": "Amber",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("POWER_MONITOR_BASELINE_WATTS", "55")

    loaded = load_config_from_env()

    assert loaded.baseline_watts == 55
    assert loaded.always_on_top is False
    assert loaded.display_mode == "panel"
    assert loaded.watt_font_size == 64
    assert loaded.text_color_name == "Amber"
