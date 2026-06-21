param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DllPath = Join-Path $ProjectRoot "vendor\LibreHardwareMonitorLib.dll"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv first, then run this script again."
}

if (-not (Test-Path -LiteralPath $DllPath)) {
    throw "Missing vendor\LibreHardwareMonitorLib.dll. Download LibreHardwareMonitor and place the DLL in the vendor directory."
}

Push-Location $ProjectRoot
try {
    uv sync --extra dev

    if ($Clean) {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "build", "dist", "power-monitor.spec"
    }

    $VendorDlls = Get-ChildItem -LiteralPath "vendor" -Filter "*.dll"
    if ($VendorDlls.Count -eq 0) {
        throw "No DLL files found in vendor."
    }

    $PyInstallerArgs = @(
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "power-monitor",
        "--hidden-import", "clr"
    )

    foreach ($Dll in $VendorDlls) {
        $PyInstallerArgs += @("--add-binary", "vendor\$($Dll.Name);vendor")
    }

    $PyInstallerArgs += "app\main.py"

    uv run pyinstaller @PyInstallerArgs

    Write-Host "Built dist\power-monitor.exe"
}
finally {
    Pop-Location
}
