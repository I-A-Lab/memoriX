[CmdletBinding()]
param([string]$TaskName = "memoriX Nightly Consolidation")
$ErrorActionPreference = "Stop"
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $Task) {
    Write-Host "Scheduled task already absent: $TaskName"
    exit 0
}
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Scheduled task removed: $TaskName" -ForegroundColor Green
