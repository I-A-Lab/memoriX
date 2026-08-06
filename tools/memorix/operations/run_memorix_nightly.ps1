[CmdletBinding()]
param(
    [string]$RuntimeRoot,
    [switch]$KeepShortTerm,
    [ValidateSet("manual", "task_scheduler", "opencode")]
    [string]$Trigger = "manual",
    [int]$LockTimeoutHours = 6,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $null
$CandidateDirectory = [System.IO.DirectoryInfo]$ScriptRoot

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

if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
    $RuntimeRoot = Join-Path $env:LOCALAPPDATA "memoriX\runtime"
}

$ResolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$ResolvedRuntimeRoot = [System.IO.Path]::GetFullPath($RuntimeRoot)
if ($ResolvedRuntimeRoot.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The memoriX runtime root must remain outside the repository."
}

$Python = Get-Command py.exe -ErrorAction SilentlyContinue
if ($null -eq $Python) {
    throw "py.exe was not found. Python 3.10 is required."
}

$Launcher = Join-Path $ScriptRoot "memorix_nightly.py"
if (-not (Test-Path $Launcher)) {
    throw "Nightly launcher not found: $Launcher"
}

$Arguments = @(
    "-3.10"
    $Launcher
    "--runtime-root"
    $ResolvedRuntimeRoot
    "--trigger"
    $Trigger
    "--lock-timeout-hours"
    $LockTimeoutHours.ToString()
    "--pretty"
)
if ($KeepShortTerm) {
    $Arguments += "--keep-short-term"
} else {
    $Arguments += "--clear-after-success"
}

if ($ValidateOnly) {
    [pscustomobject]@{
        ProjectRoot = $ResolvedProjectRoot
        RuntimeRoot = $ResolvedRuntimeRoot
        Python = $Python.Source
        Launcher = $Launcher
        Arguments = $Arguments -join " "
        Valid = $true
    }
    exit 0
}

New-Item -ItemType Directory -Path $ResolvedRuntimeRoot -Force | Out-Null
$Previous = @{
    OMP_NUM_THREADS = $env:OMP_NUM_THREADS
    MKL_NUM_THREADS = $env:MKL_NUM_THREADS
    OPENBLAS_NUM_THREADS = $env:OPENBLAS_NUM_THREADS
    NUMEXPR_NUM_THREADS = $env:NUMEXPR_NUM_THREADS
}
try {
    $env:OMP_NUM_THREADS = "1"
    $env:MKL_NUM_THREADS = "1"
    $env:OPENBLAS_NUM_THREADS = "1"
    $env:NUMEXPR_NUM_THREADS = "1"
    & $Python.Source @Arguments
    $ExitCode = $LASTEXITCODE
} finally {
    foreach ($Name in $Previous.Keys) {
        if ($null -eq $Previous[$Name]) {
            Remove-Item "Env:$Name" -ErrorAction SilentlyContinue
        } else {
            Set-Item "Env:$Name" $Previous[$Name]
        }
    }
}
exit $ExitCode
