[CmdletBinding()]
param(
    [string]$RuntimeRoot = "",

    [switch]$ValidateOnly,

    [switch]$ResetRuntime,

    [switch]$CaptureMessages,

    [switch]$CaptureToolResults,

    [int]$TimeoutMs = 15000,

    [int]$TitanDModel = 256,

    [int]$TitanHiddenDim = 256,

    [int]$TitanMaxItems = 50000,

    [string]$TitanDevice = "cpu",

    [int]$TitanTopK = 5,

    [double]$TitanMinScore = 0.12,

    [int]$MaxMessageCharacters = 12000,

    [int]$MaxToolOutputCharacters = 16000,

    [string]$IgnoredTools = "memory_store,memory_retrieve,memory_candidates_list,memory_candidate_validate,memory_candidate_reject,memory_consolidate,memory_status",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OpenCodeArguments
)

$ErrorActionPreference = "Stop"

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDirectory "..")).Path

Set-Location $ProjectRoot

$CurrentBranch = (git branch --show-current).Trim()

if ($LASTEXITCODE -ne 0) {
    throw "Impossible de déterminer la branche Git."
}

if ([string]::IsNullOrWhiteSpace($CurrentBranch)) {
    throw "Aucune branche Git active n'a été détectée."
}

$PythonExe = (
    py -3.10 -c "import sys; print(sys.executable)"
).Trim()

if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10 est introuvable."
}

if (-not (Test-Path $PythonExe -PathType Leaf)) {
    throw "Exécutable Python introuvable : $PythonExe"
}

$BunCommand = Get-Command bun -ErrorAction SilentlyContinue

if ($null -eq $BunCommand) {
    throw "Bun est introuvable dans le PATH."
}

$McpLauncher = Join-Path $ProjectRoot "scripts\memorix_mcp_server.py"

if (-not (Test-Path $McpLauncher -PathType Leaf)) {
    throw "Serveur MCP memoriX introuvable : $McpLauncher"
}

$OpenCodePackage = Join-Path $ProjectRoot "packages\opencode"

if (-not (Test-Path $OpenCodePackage -PathType Container)) {
    throw "Package OpenCode introuvable : $OpenCodePackage"
}

if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
    if (-not [string]::IsNullOrWhiteSpace($env:MEMORIX_RUNTIME_ROOT)) {
        $RuntimeRoot = $env:MEMORIX_RUNTIME_ROOT
    } elseif (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $RuntimeRoot = Join-Path $env:LOCALAPPDATA "memoriX\runtime"
    } elseif (-not [string]::IsNullOrWhiteSpace($env:TEMP)) {
        $RuntimeRoot = Join-Path $env:TEMP "memoriX\runtime"
    } else {
        throw (
            "Impossible de déterminer un runtime memoriX hors du dépôt. " +
            "Utilise -RuntimeRoot ou MEMORIX_RUNTIME_ROOT."
        )
    }
}

if (-not [System.IO.Path]::IsPathRooted($RuntimeRoot)) {
    $RuntimeRoot = Join-Path $ProjectRoot $RuntimeRoot
}

$RuntimeRoot = [System.IO.Path]::GetFullPath($RuntimeRoot)
$ForbiddenProjectRuntime = [System.IO.Path]::GetFullPath(
    (Join-Path $ProjectRoot "memory\runtime")
)

$RuntimeSeparator = [System.IO.Path]::DirectorySeparatorChar
$ForbiddenRuntimePrefix = (
    $ForbiddenProjectRuntime.TrimEnd($RuntimeSeparator) +
    $RuntimeSeparator
)

if (
    $RuntimeRoot -eq $ForbiddenProjectRuntime -or
    $RuntimeRoot.StartsWith(
        $ForbiddenRuntimePrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )
) {
    throw (
        "Le runtime memoriX doit rester hors du dépôt. " +
        "Chemin refusé : $RuntimeRoot"
    )
}

if ($ResetRuntime) {
    if (Test-Path $RuntimeRoot) {
        Write-Host "Suppression du runtime de test :" -ForegroundColor Yellow
        Write-Host $RuntimeRoot

        Remove-Item $RuntimeRoot -Recurse -Force
    }
}

if (-not (Test-Path $RuntimeRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
}

$RuntimeItem = Get-Item $RuntimeRoot

if ($RuntimeItem.Attributes -band [System.IO.FileAttributes]::ReadOnly) {
    throw "Le runtime de test est marqué en lecture seule : $RuntimeRoot"
}

Write-Host "`n=== Prévalidation memoriX ===" -ForegroundColor Cyan

& $PythonExe -m py_compile $McpLauncher

if ($LASTEXITCODE -ne 0) {
    throw "Le serveur MCP Python ne compile pas."
}

& $PythonExe -c "from memory.gateway.public_api import MemoriXGateway; print('MemoriXGateway import OK')"

if ($LASTEXITCODE -ne 0) {
    throw "La gateway memoriX ne peut pas être importée."
}

$env:MEMORIX_ENABLED = "true"
$env:MEMORIX_PYTHON_EXECUTABLE = $PythonExe
$env:MEMORIX_RUNTIME_ROOT = $RuntimeRoot
$env:MEMORIX_TIMEOUT_MS = [string]$TimeoutMs
$env:MEMORIX_TITAN_D_MODEL = [string]$TitanDModel
$env:MEMORIX_TITAN_HIDDEN_DIM = [string]$TitanHiddenDim
$env:MEMORIX_TITAN_MAX_ITEMS = [string]$TitanMaxItems
$env:MEMORIX_TITAN_DEVICE = $TitanDevice
$env:MEMORIX_TITAN_TOP_K = [string]$TitanTopK
$env:MEMORIX_TITAN_MIN_SCORE = [string]$TitanMinScore
$env:MEMORIX_HOOK_CAPTURE_MESSAGES = "false"
if ($CaptureMessages.IsPresent) {
    $env:MEMORIX_HOOK_CAPTURE_MESSAGES = "true"
}
$env:MEMORIX_HOOK_CAPTURE_TOOL_RESULTS = "false"
if ($CaptureToolResults.IsPresent) {
    $env:MEMORIX_HOOK_CAPTURE_TOOL_RESULTS = "true"
}
$env:MEMORIX_HOOK_MAX_MESSAGE_CHARACTERS = [string]$MaxMessageCharacters
$env:MEMORIX_HOOK_MAX_TOOL_OUTPUT_CHARACTERS = [string]$MaxToolOutputCharacters
$env:MEMORIX_HOOK_IGNORED_TOOLS = $IgnoredTools

Write-Host "`n=== Configuration de lancement ===" -ForegroundColor Cyan
Write-Host "Projet                    : $ProjectRoot"
Write-Host "Branche                   : $CurrentBranch"
Write-Host "Python                    : $PythonExe"
Write-Host "Bun                       : $($BunCommand.Source)"
Write-Host "Runtime                   : $RuntimeRoot"
Write-Host "memoriX activé            : $env:MEMORIX_ENABLED"
Write-Host "Capture messages          : $env:MEMORIX_HOOK_CAPTURE_MESSAGES"
Write-Host "Capture résultats outils  : $env:MEMORIX_HOOK_CAPTURE_TOOL_RESULTS"
Write-Host "Timeout MCP               : $env:MEMORIX_TIMEOUT_MS ms"
Write-Host "Titan d_model             : $env:MEMORIX_TITAN_D_MODEL"
Write-Host "Titan hidden_dim          : $env:MEMORIX_TITAN_HIDDEN_DIM"
Write-Host "Titan max_items           : $env:MEMORIX_TITAN_MAX_ITEMS"
Write-Host "Titan device              : $env:MEMORIX_TITAN_DEVICE"
Write-Host "Titan top_k               : $env:MEMORIX_TITAN_TOP_K"
Write-Host "Titan min_score           : $env:MEMORIX_TITAN_MIN_SCORE"

if ($ValidateOnly) {
    Write-Host `
        "`nPrévalidation terminée. OpenCode ne sera pas lancé." `
        -ForegroundColor Green
    exit 0
}

Write-Host "`nLancement d'OpenCode..." -ForegroundColor Green
Write-Host "Ferme OpenCode normalement pour arrêter le serveur MCP."

& $BunCommand.Source run --cwd "packages\opencode" dev -- $ProjectRoot @OpenCodeArguments

$OpenCodeExitCode = $LASTEXITCODE

Write-Host "`nOpenCode terminé avec le code : $OpenCodeExitCode" -ForegroundColor Cyan

exit $OpenCodeExitCode
