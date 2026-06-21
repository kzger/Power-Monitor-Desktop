$ErrorActionPreference = "Stop"

$TaskName = "PowerMonitorDesktop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ExePath = Join-Path $ProjectRoot "dist\power-monitor.exe"

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Missing dist\power-monitor.exe. Run scripts\build.ps1 first."
}

$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Action = New-ScheduledTaskAction -Execute $ExePath -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentUser `
    -LogonType Interactive `
    -RunLevel Highest

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Start Power Monitor desktop app when the current user logs on." `
    -Force | Out-Null

Write-Host "Installed scheduled task '$TaskName' for $CurrentUser."
