# Third-Party Notices

This file summarizes third-party packages used by Power Monitor Desktop. It is
provided for attribution and license tracking, not as legal advice.

## Runtime Python Packages

| Package | Purpose | License | Source |
| --- | --- | --- | --- |
| pythonnet | Python to .NET CLR integration | MIT | https://github.com/pythonnet/pythonnet |
| clr-loader | .NET runtime loader used by pythonnet | MIT | https://github.com/pythonnet/clr-loader |

## Build And Test Packages

| Package | Purpose | License | Source |
| --- | --- | --- | --- |
| PyInstaller | Windows exe packaging | GPL-2.0-or-later with PyInstaller bootloader exception | https://pyinstaller.org/ |
| pyinstaller-hooks-contrib | PyInstaller hook collection | Apache-2.0 or GPL-2.0-or-later | https://github.com/pyinstaller/pyinstaller-hooks-contrib |
| pytest | Test runner | MIT | https://docs.pytest.org/ |

## Vendored LibreHardwareMonitor Assemblies

The `vendor/` directory contains DLLs extracted from the official
LibreHardwareMonitor release package.

| DLL / package | License | Source |
| --- | --- | --- |
| LibreHardwareMonitorLib.dll | MPL-2.0 | https://github.com/LibreHardwareMonitor/LibreHardwareMonitor |
| DiskInfoToolkit.dll | MPL-2.0 | https://github.com/Blacktempel/DiskInfoToolkit |
| RAMSPDToolkit-NDD.dll | MPL-2.0 | https://www.nuget.org/packages/RAMSPDToolkit-NDD/ |
| BlackSharp.Core.dll | MPL-2.0 | https://www.nuget.org/packages/BlackSharp.Core/ |
| HidSharp.dll | Apache-2.0 | https://github.com/IntergatedCircuits/HidSharp |
| OxyPlot.dll, OxyPlot.WindowsForms.dll | MIT | https://github.com/oxyplot/oxyplot |
| Microsoft.Win32.TaskScheduler.dll | MIT | https://www.nuget.org/packages/TaskScheduler/ |
| System.*.dll and Microsoft.Bcl.*.dll companion assemblies | MIT for NuGet library packages | https://github.com/dotnet/runtime |
| Aga.Controls.dll | CPOL-1.02 | https://github.com/AlexandrSurkov/PKStudio/blob/master/Aga.Controls/Aga.Controls%20license.txt |

## Notes

- MPL-2.0 components require preserving their license notices when distributing
  the covered software.
- MIT and Apache-2.0 components require preserving their copyright and license
  notices.
- The application code in this repository does not currently declare its own
  project-level license. Add a top-level `LICENSE` file if you want to publish
  the application code under a specific open-source license.
