import subprocess

from app import startup_task


def test_hidden_subprocess_options_hide_powershell_window(monkeypatch) -> None:
    monkeypatch.setattr(startup_task.platform, "system", lambda: "Windows")

    options = startup_task._hidden_subprocess_options()

    assert options["creationflags"] & subprocess.CREATE_NO_WINDOW
    startupinfo = options["startupinfo"]
    assert startupinfo.dwFlags & subprocess.STARTF_USESHOWWINDOW
    assert startupinfo.wShowWindow == getattr(subprocess, "SW_HIDE", 0)
