[CmdletBinding()]
param(
    [string]$TaskName = "memoriX Nightly Consolidation",
    [string]$RuntimeRoot,
    [string]$DailyAt = "02:00",
    [switch]$RunWhetherUserIsLoggedOn,
    [switch]$ValidateOnly
)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $ScriptRoot "run_memorix_nightly.ps1"
if (-not (Test-Path $Runner)) { throw "Runner not found: $Runner" }
if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) { $RuntimeRoot = Join-Path $env:LOCALAPPDATA "memoriX\runtime" }
$ParsedTime = [datetime]::MinValue
if (-not [datetime]::TryParseExact($DailyAt, "HH:mm", [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$ParsedTime)) {
    throw "DailyAt must use HH:mm format."
}
$PowerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
$Arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -RuntimeRoot "{1}" -Trigger "task_scheduler"' -f $Runner, ([IO.Path]::GetFullPath($RuntimeRoot))
if ($ValidateOnly) {
    [pscustomobject]@{ TaskName=$TaskName; DailyAt=$DailyAt; Program=$PowerShell; Arguments=$Arguments; Valid=$true }
    exit 0
}
$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Arguments
$Trigger = New-ScheduledTaskTrigger -Daily -At $ParsedTime
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 6)
$Principal = if ($RunWhetherUserIsLoggedOn) {
    New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType S4U -RunLevel Limited
} else {
    New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
}
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal
Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null
Write-Host "Scheduled task installed: $TaskName" -ForegroundColor Green
