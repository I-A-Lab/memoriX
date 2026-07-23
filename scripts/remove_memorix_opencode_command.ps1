[CmdletBinding()]
param([string]$ProfilePath = $PROFILE)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $ProfilePath -PathType Leaf)) {
    Write-Host "Aucun profil PowerShell à modifier."
    exit 0
}
$StartMarker = "# BEGIN MEMORIX OPENCODE COMMAND"
$EndMarker = "# END MEMORIX OPENCODE COMMAND"
$Current = Get-Content $ProfilePath -Raw
$Pattern = "(?s)\r?\n?" + [regex]::Escape($StartMarker) + ".*?" + [regex]::Escape($EndMarker) + "\r?\n?"
$Updated = [regex]::Replace($Current, $Pattern, [Environment]::NewLine)
Set-Content -Path $ProfilePath -Value $Updated.TrimEnd() -Encoding UTF8
Write-Host "Commande opencode memoriX retirée du profil." -ForegroundColor Green
