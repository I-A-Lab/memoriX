[CmdletBinding()]
param(
    [switch]$AllowDirty,
    [switch]$KeepRuntime,
    [int]$TypeScriptTimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDirectory ".."))
Set-Location $ProjectRoot

$Results = New-Object System.Collections.Generic.List[object]
$RuntimeRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("memorix-verify-" + [guid]::NewGuid().ToString("N"))
$PreviousEnvironment = @{
    MEMORIX_RUNTIME_ROOT = $env:MEMORIX_RUNTIME_ROOT
    OMP_NUM_THREADS = $env:OMP_NUM_THREADS
    MKL_NUM_THREADS = $env:MKL_NUM_THREADS
    OPENBLAS_NUM_THREADS = $env:OPENBLAS_NUM_THREADS
    NUMEXPR_NUM_THREADS = $env:NUMEXPR_NUM_THREADS
}

function Add-Result {
    param([string]$Name, [string]$Status, [string]$Details = "")
    $Results.Add([pscustomobject]@{ Name = $Name; Status = $Status; Details = $Details })
}

function Invoke-NativeCommand {
    param([string]$Description, [scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw ($Description + " failed with exit code " + $LASTEXITCODE + ".")
    }
}

function Invoke-VerificationStep {
    param([string]$Name, [scriptblock]$Action)
    Write-Host ""
    Write-Host ("=== " + $Name + " ===") -ForegroundColor Cyan
    try {
        & $Action
        Add-Result -Name $Name -Status "PASS"
        Write-Host ($Name + " : PASS") -ForegroundColor Green
    } catch {
        Add-Result -Name $Name -Status "FAIL" -Details $_.Exception.Message
        Write-Host ($Name + " : FAIL") -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        throw
    }
}

function Restore-EnvironmentVariable {
    param([string]$Name, [AllowNull()][string]$Value)
    if ($null -eq $Value) {
        Remove-Item ("Env:" + $Name) -ErrorAction SilentlyContinue
    } else {
        Set-Item ("Env:" + $Name) $Value
    }
}

function Show-Summary {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "memoriX verification summary" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    foreach ($Result in $Results) {
        $Color = if ($Result.Status -eq "PASS") { "Green" } else { "Red" }
        Write-Host ("{0,-28} {1}" -f $Result.Name, $Result.Status) -ForegroundColor $Color
        if (-not [string]::IsNullOrWhiteSpace($Result.Details)) {
            Write-Host ("  " + $Result.Details) -ForegroundColor DarkGray
        }
    }
    Write-Host "========================================" -ForegroundColor Cyan
}

$VerificationFailed = $false

try {
    Invoke-VerificationStep "Prerequisites" {
        foreach ($CommandName in @("git", "py", "bun")) {
            if ($null -eq (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
                throw ("Required command not found: " + $CommandName)
            }
        }
        foreach ($RequiredPath in @(
            "memory",
            "packages\opencode",
            "scripts\memorix_live_probe.py",
            "scripts\start_opencode_with_memorix.ps1"
        )) {
            if (-not (Test-Path $RequiredPath)) {
                throw ("Required path not found: " + $RequiredPath)
            }
        }
        $Branch = (git branch --show-current).Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Branch)) {
            throw "Unable to determine the active Git branch."
        }
        Write-Host ("Branch: " + $Branch)
    }

    Invoke-VerificationStep "Git initial state" {
        Invoke-NativeCommand "git diff --check" { git diff --check }
        if (-not $AllowDirty) {
            $DirtyEntries = @(git status --porcelain)
            if ($LASTEXITCODE -ne 0) { throw "Unable to read the Git status." }
            if ($DirtyEntries.Count -gt 0) {
                $DirtyEntries | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
                throw "The repository is not clean. Use -AllowDirty only while developing this script."
            }
        } else {
            Write-Host "Dirty repository allowed for this run." -ForegroundColor Yellow
        }
    }

    Invoke-VerificationStep "Runtime isolation" {
        New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
        $ResolvedRuntime = (Resolve-Path $RuntimeRoot).Path
        $ForbiddenRuntime = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "memory\runtime"))
        if ($ResolvedRuntime -eq $ForbiddenRuntime -or $ResolvedRuntime.StartsWith($ForbiddenRuntime + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "The verification runtime is inside the repository."
        }
        $env:MEMORIX_RUNTIME_ROOT = $ResolvedRuntime
        $env:OMP_NUM_THREADS = "1"
        $env:MKL_NUM_THREADS = "1"
        $env:OPENBLAS_NUM_THREADS = "1"
        $env:NUMEXPR_NUM_THREADS = "1"
        Write-Host ("Runtime: " + $ResolvedRuntime)
    }

    Invoke-VerificationStep "Python compilation" {
        Invoke-NativeCommand "Python compilation" {
            py -3.10 -m compileall -q -f "memory" "scripts" "tools\memorix" "tests\memory"
        }
        Write-Host "All memoriX Python source files compiled."
    }

    Invoke-VerificationStep "Python tests" {
        Invoke-NativeCommand "Python memory tests" {
            py -3.10 -m unittest discover -s "tests\memory" -p "test_*.py"
        }
    }

    Invoke-VerificationStep "TypeScript typecheck" {
        if (-not (Test-Path "packages\opencode\node_modules" -PathType Container)) {
            throw "packages/opencode/node_modules is missing. Install dependencies before verification."
        }
        Invoke-NativeCommand "OpenCode typecheck" {
            bun run --cwd "packages\opencode" typecheck
        }
    }

    Invoke-VerificationStep "TypeScript memoriX tests" {
        $MemoriXTestFiles = @(
            Get-ChildItem `
                "packages\opencode\test\memorix" `
                -Filter "*.test.ts" `
                -File |
            Sort-Object FullName
        )

        if ($MemoriXTestFiles.Count -eq 0) {
            throw "No TypeScript memoriX test file was found."
        }

        $PassedMemoriXTestFiles = 0

        foreach ($MemoriXTestFile in $MemoriXTestFiles) {
            $RelativeTestPath = $MemoriXTestFile.FullName.Substring(
                (Resolve-Path "packages\opencode").Path.Length + 1
            )

            Write-Host ("Running isolated test file: " + $RelativeTestPath)

            Invoke-NativeCommand ("OpenCode memoriX test " + $RelativeTestPath) {
                $PreviousSkipRuntimeDispose = $env:MEMORIX_SKIP_TEST_RUNTIME_DISPOSE
                $env:MEMORIX_SKIP_TEST_RUNTIME_DISPOSE = "true"

                try {
                    bun test `
                        --cwd "packages\opencode" `
                        --timeout 30000 `
                        $RelativeTestPath
                }
                finally {
                    if ($null -eq $PreviousSkipRuntimeDispose) {
                        Remove-Item `
                            Env:\MEMORIX_SKIP_TEST_RUNTIME_DISPOSE `
                            -ErrorAction SilentlyContinue
                    }

                    if ($null -ne $PreviousSkipRuntimeDispose) {
                        $env:MEMORIX_SKIP_TEST_RUNTIME_DISPOSE = `
                            $PreviousSkipRuntimeDispose
                    }
                }
            }

            $PassedMemoriXTestFiles += 1
        }

        Write-Host (
            [string]$PassedMemoriXTestFiles +
            " isolated TypeScript memoriX test file(s) passed."
        )
    }

    Invoke-VerificationStep "Launcher validation" {
        & "scripts\start_opencode_with_memorix.ps1" -RuntimeRoot $RuntimeRoot -ValidateOnly
        if ($LASTEXITCODE -ne 0) {
            throw ("The memoriX launcher validation failed with exit code " + $LASTEXITCODE + ".")
        }
    }

    Invoke-VerificationStep "Release readiness" {
        $ReadinessOutput = & py -3.10 "scripts\memorix_release_readiness.py" --project-root $ProjectRoot --runtime-root $RuntimeRoot
        if ($LASTEXITCODE -ne 0) {
            Write-Host $ReadinessOutput
            throw "The final release-readiness inspection failed."
        }
        $ReadinessReport = ($ReadinessOutput -join [Environment]::NewLine) | ConvertFrom-Json
        if ($ReadinessReport.status -ne "ready") {
            throw "The final release-readiness report is not ready."
        }
        Write-Host "Release readiness: ready"
    }

    Invoke-VerificationStep "Live Probe" {
        $ProbeOutput = & py -3.10 "scripts\memorix_live_probe.py" $RuntimeRoot --compact
        $ProbeExitCode = $LASTEXITCODE
        if ($ProbeExitCode -ne 0) {
            Write-Host $ProbeOutput
            throw ("The Live Probe failed with exit code " + $ProbeExitCode + ".")
        }
        try {
            $ProbeReport = ($ProbeOutput -join [Environment]::NewLine) | ConvertFrom-Json
        } catch {
            throw "The Live Probe did not return valid JSON."
        }
        if ($null -eq $ProbeReport.status) { throw "The Live Probe report has no status." }
        Write-Host ("Live Probe status: " + [string]$ProbeReport.status)
    }

    Invoke-VerificationStep "Repository runtime guard" {
        if (Test-Path "memory\runtime") {
            throw ("Forbidden repository runtime exists: " + (Join-Path $ProjectRoot "memory\runtime"))
        }
        $TrackedRuntimeFiles = @(git ls-files "memory/runtime" "memory/runtime/**")
        if ($LASTEXITCODE -ne 0) { throw "Unable to inspect tracked runtime files." }
        if ($TrackedRuntimeFiles.Count -gt 0) {
            $TrackedRuntimeFiles | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
            throw "Runtime files are tracked by Git."
        }
    }

    Invoke-VerificationStep "Git final integrity" {
        Invoke-NativeCommand "git diff --check" { git diff --check }
        if (-not $AllowDirty) {
            $FinalDirtyEntries = @(git status --porcelain)
            if ($LASTEXITCODE -ne 0) { throw "Unable to read the final Git status." }
            if ($FinalDirtyEntries.Count -gt 0) {
                $FinalDirtyEntries | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
                throw "Verification modified the repository."
            }
        }
    }
} catch {
    $VerificationFailed = $true
} finally {
    Restore-EnvironmentVariable -Name "MEMORIX_RUNTIME_ROOT" -Value $PreviousEnvironment.MEMORIX_RUNTIME_ROOT
    Restore-EnvironmentVariable -Name "OMP_NUM_THREADS" -Value $PreviousEnvironment.OMP_NUM_THREADS
    Restore-EnvironmentVariable -Name "MKL_NUM_THREADS" -Value $PreviousEnvironment.MKL_NUM_THREADS
    Restore-EnvironmentVariable -Name "OPENBLAS_NUM_THREADS" -Value $PreviousEnvironment.OPENBLAS_NUM_THREADS
    Restore-EnvironmentVariable -Name "NUMEXPR_NUM_THREADS" -Value $PreviousEnvironment.NUMEXPR_NUM_THREADS

    if (-not $KeepRuntime -and (Test-Path $RuntimeRoot)) {
        Remove-Item $RuntimeRoot -Recurse -Force -ErrorAction SilentlyContinue
    } elseif ($KeepRuntime) {
        Write-Host ("Runtime preserved: " + $RuntimeRoot) -ForegroundColor Yellow
    }

    Show-Summary
}

if ($VerificationFailed) {
    Write-Host ""
    Write-Host "MEMORIX VERIFICATION FAILED" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "ALL MEMORIX CHECKS PASSED" -ForegroundColor Green
exit 0
