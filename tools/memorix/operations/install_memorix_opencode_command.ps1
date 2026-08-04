[CmdletBinding()]
param(
    [string]$ProfilePath = $PROFILE,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $null
$CandidateDirectory = [System.IO.DirectoryInfo]$ScriptDirectory

while ($null -ne $CandidateDirectory) {
    $CandidatePath = $CandidateDirectory.FullName
    $HasPackageJson = Test-Path (Join-Path $CandidatePath "package.json") -PathType Leaf
    $HasMemory = Test-Path (Join-Path $CandidatePath "memory") -PathType Container
    $HasOpenCode = Test-Path (Join-Path $CandidatePath "packages\opencode") -PathType Container

    if ($HasPackageJson -and $HasMemory -and $HasOpenCode) {
        $ProjectRoot = $CandidatePath
        break
    }

    $CandidateDirectory = $CandidateDirectory.Parent
}

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    throw "Impossible de localiser la racine du dépôt memoriX."
}
$Launcher = Join-Path $ProjectRoot "tools\memorix\runtime\start_opencode_with_memorix.ps1"
$StartMarker = "# BEGIN MEMORIX OPENCODE COMMAND"
$EndMarker = "# END MEMORIX OPENCODE COMMAND"
$LegacyStartMarker = "# BEGIN LOCAL MEMORIX OPENCODE"
$LegacyEndMarker = "# END LOCAL MEMORIX OPENCODE"

if (-not (Test-Path $Launcher -PathType Leaf)) {
    throw "Lanceur memoriX introuvable : $Launcher"
}

$ProfileDirectory = Split-Path -Parent $ProfilePath
if (-not (Test-Path $ProfileDirectory)) {
    New-Item -ItemType Directory -Path $ProfileDirectory -Force | Out-Null
}
if (-not (Test-Path $ProfilePath)) {
    New-Item -ItemType File -Path $ProfilePath -Force | Out-Null
}

$Current = Get-Content -Path $ProfilePath -Raw -ErrorAction SilentlyContinue
if ($null -eq $Current) {
    $Current = ""
}

$MarkerPairs = @(
    @($StartMarker, $EndMarker),
    @($LegacyStartMarker, $LegacyEndMarker)
)

$HasExisting = $false
foreach ($Pair in $MarkerPairs) {
    $Pattern = (
        "(?s)\r?\n?" +
        [regex]::Escape($Pair[0]) +
        ".*?" +
        [regex]::Escape($Pair[1]) +
        "\r?\n?"
    )

    if ([regex]::IsMatch($Current, $Pattern)) {
        $HasExisting = $true
    }
}

if ($HasExisting -and -not $Force) {
    throw "La commande opencode memoriX existe deja. Utilise -Force pour la remplacer."
}

foreach ($Pair in $MarkerPairs) {
    $Pattern = (
        "(?s)\r?\n?" +
        [regex]::Escape($Pair[0]) +
        ".*?" +
        [regex]::Escape($Pair[1]) +
        "\r?\n?"
    )

    $Current = [regex]::Replace(
        $Current,
        $Pattern,
        [Environment]::NewLine
    )
}

$EscapedLauncher = $Launcher.Replace("'", "''")

$FunctionLines = @(
    ""
    $StartMarker
    "function opencode {"
    "    [CmdletBinding()]"
    "    param("
    '        [string]$RuntimeRoot = "",'
    '        [switch]$ValidateOnly,'
    '        [switch]$ResetRuntime,'
    '        [Parameter(ValueFromRemainingArguments = $true)]'
    '        [string[]]$OpenCodeArguments'
    "    )"
    ""
    '    $Forward = @{}'
    '    foreach ($Entry in $PSBoundParameters.GetEnumerator()) {'
    '        $Forward[$Entry.Key] = $Entry.Value'
    '    }'
    '    $Forward["CaptureMessages"] = $true'
    '    $Forward["CaptureToolResults"] = $true'
    ""
    ("    & '{0}' @Forward" -f $EscapedLauncher)
    "}"
    $EndMarker
    ""
)

$Block = $FunctionLines -join [Environment]::NewLine
$NewProfile = $Current.TrimEnd() + $Block

try {
    [void][scriptblock]::Create($NewProfile)
}
catch {
    throw "Le profil genere contient une erreur de syntaxe : $($_.Exception.Message)"
}

Set-Content -Path $ProfilePath -Value $NewProfile -Encoding UTF8

Write-Host "Commande opencode memoriX installee dans : $ProfilePath" -ForegroundColor Green
Write-Host 'Recharge avec : . $PROFILE'
