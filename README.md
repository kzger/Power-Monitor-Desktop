# Power Monitor Desktop

Windows 11 desktop power monitor written in Python. It uses
`LibreHardwareMonitorLib.dll` through `pythonnet`, displays a small Tkinter
window, and estimates total power from CPU, GPU, other readable power sensors,
and a configurable baseline value.

## Features

- Reads LibreHardwareMonitor `Power` sensors.
- Shows total estimate, CPU power, GPU power, and other / baseline power.
- Uses a 35 W default baseline.
- Refreshes every 1 second.
- Keeps a small always-on-top desktop window.
- Handles missing DLLs or missing sensors without crashing the GUI.
- Can be packaged as `dist\power-monitor.exe` with PyInstaller.
- Can auto-start at user logon through Windows Task Scheduler.

## Project Layout

```text
power-monitor/
  app/
    __init__.py
    main.py
    power_reader.py
    config.py
  vendor/
    LibreHardwareMonitorLib.dll
    README.md
  scripts/
    install_startup_task.ps1
    uninstall_startup_task.ps1
    build.ps1
  tests/
    test_power_reader.py
  pyproject.toml
  requirements.txt
  README.md
```

`vendor\LibreHardwareMonitorLib.dll` is not committed here. Place the real DLL
there before running the app against live hardware or building the exe. If you
download the official release ZIP, keep the companion `*.dll` files in `vendor`
too because LibreHardwareMonitor loads several dependency assemblies at runtime.

## Install Python Dependencies

This project is intended to be managed with `uv`.

```powershell
cd D:\python_project\power-monitor
uv sync --extra dev
```

If you only want runtime dependencies:

```powershell
uv sync
```

## LibreHardwareMonitor DLL

Get `LibreHardwareMonitorLib.dll` from the official LibreHardwareMonitor GitHub
project:

- Repository: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
- Releases: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases

Download a release archive or build `LibreHardwareMonitorLib` from source, then
copy the DLL to:

```text
D:\python_project\power-monitor\vendor\LibreHardwareMonitorLib.dll
```

Recommended: extract all `*.dll` files from `LibreHardwareMonitor.zip` into:

```text
D:\python_project\power-monitor\vendor\
```

The official repository warns that it is not affiliated with
`librehardwaremonitor.com`, so prefer GitHub releases for safety.

## Run in Development

```powershell
cd D:\python_project\power-monitor
uv run python -m app.main
```

Optional baseline override:

```powershell
$env:POWER_MONITOR_BASELINE_WATTS = "45"
uv run python -m app.main
```

## Baseline Power

`Baseline W` is a configurable estimate for power that is not reported by CPU
or GPU power sensors. It covers idle motherboard power, RAM, storage, fans,
USB devices, PSU conversion loss, and other components that LibreHardwareMonitor
does not expose as `Power` sensors.

The app calculates:

```text
Total Power Estimate = CPU Power + GPU Power + other power sensors + Baseline W
```

The default baseline is 35 W. Increase or decrease it if your system's idle
estimate looks too low or too high.

## Display Modes

The app has two display modes:

- Overlay view: only the current total wattage is visible. It uses white text
  with a black outline and shadow for high contrast over any desktop or app.
- Full menu view: shows the original control panel with total, CPU, GPU,
  other / baseline, baseline input, always-on-top, watt font size, watt text
  color, sensor count, status, and Exit.

Controls:

- Double-click the left mouse button to switch between Overlay view and Full
  menu view.
- Drag the wattage text in Overlay view to move the overlay.
- Use the mouse wheel over the wattage to change only the wattage font size.
- Press `+` / `-` to change only the wattage font size.
- Use `Watt text color` in Full menu view to change the overlay wattage color.
- Right-click the wattage for full menu, size controls, and Exit.
- Press `Esc` to close the app.

The app may need to run as Administrator for LibreHardwareMonitor to access all
hardware sensors.

## Run Tests

```powershell
cd D:\python_project\power-monitor
uv run pytest
```

## Build EXE

Put the DLL in `vendor` first, then run:

```powershell
cd D:\python_project\power-monitor
.\scripts\build.ps1
```

Clean rebuild:

```powershell
.\scripts\build.ps1 -Clean
```

The output is:

```text
dist\power-monitor.exe
```

The PyInstaller build includes:

```text
vendor\*.dll
```

inside the bundled executable extraction directory, so the app can find
LibreHardwareMonitor and its dependency assemblies when running as an exe.

## Packages And Licenses

This project uses these main packages:

- `pythonnet` and `clr-loader` to load .NET assemblies from Python. Both are
  MIT licensed.
- `LibreHardwareMonitorLib.dll` from LibreHardwareMonitor to read hardware
  sensors. LibreHardwareMonitorLib is MPL-2.0 licensed.
- `PyInstaller` to build the Windows executable. PyInstaller is GPL-2.0-or-later
  with its bootloader exception that allows distributing generated applications.
- `pytest` for development tests. pytest is MIT licensed.

The `vendor/` directory also includes LibreHardwareMonitor release companion
assemblies. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the
third-party package list, license names, and source links.

This repository does not currently declare a project-level license for the
application code itself. Third-party components remain governed by their own
upstream licenses.

## Install Startup Task

Build the exe first, then run PowerShell as Administrator:

```powershell
cd D:\python_project\power-monitor
.\scripts\install_startup_task.ps1
```

This creates a Windows Task Scheduler task:

```text
PowerMonitorDesktop
```

The task starts `dist\power-monitor.exe` when the current user logs on and uses
highest privileges. This is preferred for a GUI desktop app because it runs in
the user session where the window can be displayed.

## Remove Startup Task

Run PowerShell as Administrator:

```powershell
cd D:\python_project\power-monitor
.\scripts\uninstall_startup_task.ps1
```

## FAQ

### The app cannot read power sensors

Not every motherboard, CPU, GPU, or driver exposes power telemetry. Start
LibreHardwareMonitor itself and check whether it shows `Power` sensors. If the
standalone tool does not show them, this app cannot invent them.

### Do I need Administrator permissions?

Often, yes. LibreHardwareMonitor may need elevated permissions to load low-level
drivers and read hardware sensors. Run PowerShell, Python, or the packaged exe
as Administrator if sensors are missing.

### Why not use a Windows Service for the GUI?

Windows Services normally run in Session 0. Desktop users are in an interactive
user session, so a GUI launched from a service usually cannot display a normal
desktop window. If you need a true background service, keep it as a no-GUI data
collector and run a separate user-session GUI app for display.

### NVIDIA / AMD / Intel GPU power support

GPU support differs by vendor, model, driver version, and permissions:

- NVIDIA cards often expose board or GPU power on many desktop GPUs.
- AMD cards may expose ASIC, board, or package power depending on model and
  driver support.
- Intel integrated GPUs often expose less power telemetry than discrete GPUs.

When multiple GPU power sensors exist, the app prefers names such as
`GPU Power`, `GPU Board Power`, `Total Board Power`, and `ASIC Power`.

## Current Limits

- Total power is an estimate, not wall power.
- CPU and GPU sensor names vary by hardware and driver.
- Some sensor sets may double count internal rails; the app uses simple
  preferred-name filtering for common CPU/GPU totals.
- Baseline covers idle motherboard, RAM, storage, fans, PSU loss, and anything
  not reported as a sensor.
