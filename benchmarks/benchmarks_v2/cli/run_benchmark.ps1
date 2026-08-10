<#
.SYNOPSIS
    memoriX Benchmark Infrastructure V2 CLI Wrapper.

.DESCRIPTION
    Runs the memoriX benchmark suite with configurable profiles, families, and options.

.PARAMETER Profile
    Benchmark profile name: smoke, pilot, standard, large, research.

.PARAMETER Families
    Space-separated list of family IDs to run. Default: all registered families.

.PARAMETER Seeds
    Space-separated list of integer seeds. Default: from profile config.

.PARAMETER Resume
    Resume a previously interrupted campaign from checkpoint.

.PARAMETER DryRun
    Validate configuration and create manifest without executing runs.

.PARAMETER Real
    Run real OpenCode execution (not dry-run simulation). Requires LLM API access.

.PARAMETER Model
    LLM model name passed to the orchestrator for real execution.

.PARAMETER Timeout
    Timeout per run in seconds. Default: 300.

.PARAMETER OutputDir
    Output directory for results. Default: $env:TEMP\memoriX-benchmarks.

.PARAMETER Estimate
    Print cost estimate and exit.

.PARAMETER Status
    Print campaign status and exit.

.PARAMETER Validate
    Run invariant validation checks and exit.

.PARAMETER Aggregate
    Aggregate results from the last run.

.PARAMETER Report
    Generate a report from aggregate data.

.PARAMETER Package
    Package results into a distributable ZIP archive.

.PARAMETER NoDocx
    Skip DOCX generation when combined with -Report.

.PARAMETER NoPdf
    Skip PDF generation when combined with -Report.

.PARAMETER NoFigures
    Skip figure generation when combined with -Report.

.PARAMETER Clean
    Remove the output directory before running.

.EXAMPLE
    .\run_benchmark.ps1 -Profile smoke
    .\run_benchmark.ps1 -Profile standard -Families f01 f02 f03 -Report
    .\run_benchmark.ps1 -Profile smoke -Estimate
    .\run_benchmark.ps1 -Profile smoke -Real -Model "gpt-4o"
    .\run_benchmark.ps1 -Profile standard -Report -NoDocx
    .\run_benchmark.ps1 -Profile smoke -Clean
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet("smoke", "pilot", "standard", "large", "research")]
    [string]$Profile = "smoke",

    [Parameter()]
    [string[]]$Families,

    [Parameter()]
    [int[]]$Seeds,

    [Parameter()]
    [switch]$Resume,

    [Parameter()]
    [switch]$DryRun,

    [Parameter()]
    [switch]$Real,

    [Parameter()]
    [string]$Model,

    [Parameter()]
    [ValidateRange(30, 3600)]
    [int]$Timeout = 300,

    [Parameter()]
    [string]$OutputDir = "$env:TEMP\memoriX-benchmarks",

    [Parameter()]
    [switch]$Estimate,

    [Parameter()]
    [switch]$Status,

    [Parameter()]
    [switch]$Validate,

    [Parameter()]
    [switch]$Aggregate,

    [Parameter()]
    [switch]$Report,

    [Parameter()]
    [switch]$Package,

    [Parameter()]
    [switch]$NoDocx,

    [Parameter()]
    [switch]$NoPdf,

    [Parameter()]
    [switch]$NoFigures,

    [Parameter()]
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$OrchestratorScript = Join-Path $RepoRoot "benchmarks\orchestrator\orchestrator.py"
$ReportGeneratorScript = Join-Path $RepoRoot "benchmarks\reporting\report_generator.py"

# ---------------------------------------------------------------------------
# Verify Python is available
# ---------------------------------------------------------------------------
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    $PythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $PythonCmd) {
    Write-Error "Python is not available on PATH. Please install Python 3.10+."
    exit 1
}
$Python = $PythonCmd.Source

# ---------------------------------------------------------------------------
# Resolve mutually exclusive flags: -Real implies !-DryRun
# ---------------------------------------------------------------------------
if ($Real -and $DryRun) {
    Write-Error "Cannot use -Real and -DryRun together. Choose one execution mode."
    exit 1
}

# If -Real is set without -DryRun, warn about LLM API requirement
if ($Real -and -not $DryRun) {
    Write-Host ""
    Write-Host "[WARN] Real execution mode selected. This requires LLM API access." -ForegroundColor Yellow
    Write-Host "       Ensure your API keys are configured before proceeding." -ForegroundColor Yellow
    Write-Host ""
}

# If neither -Real nor -DryRun is explicitly set, default to DryRun
if (-not $Real -and -not $DryRun) {
    $DryRun = $true
}

# ---------------------------------------------------------------------------
# Profile timeout overrides from config
# ---------------------------------------------------------------------------
$ProfileConfig = @{
    smoke    = @{ pairs = 5;    seeds = @(101);                   timeout = 240 }
    pilot    = @{ pairs = 30;   seeds = @(101, 202, 303);         timeout = 360 }
    standard = @{ pairs = 100;  seeds = @(101, 202, 303, 404, 505); timeout = 480 }
    large    = @{ pairs = 500;  seeds = @(101, 202, 303, 404, 505); timeout = 600 }
    research = @{ pairs = 1000; seeds = @(101, 202, 303, 404, 505, 606, 707, 808, 909, 1010); timeout = 900 }
}

# ---------------------------------------------------------------------------
# Clean output directory if requested
# ---------------------------------------------------------------------------
if ($Clean) {
    if (Test-Path $OutputDir) {
        Write-Host "Cleaning output directory: $OutputDir" -ForegroundColor Yellow
        Remove-Item -Path $OutputDir -Recurse -Force
        Write-Host "Output directory removed." -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# Determine execution mode for display
# ---------------------------------------------------------------------------
$ExecMode = if ($Real) { "Real" } else { "Dry-Run" }

# ---------------------------------------------------------------------------
# Compute estimated time based on profile
# ---------------------------------------------------------------------------
$EstimatedSeconds = $ProfileConfig[$Profile].timeout
if (-not $Seeds -and $ProfileConfig[$Profile].seeds) {
    $SeedCount = $ProfileConfig[$Profile].seeds.Count
} elseif ($Seeds) {
    $SeedCount = $Seeds.Count
} else {
    $SeedCount = 1
}
$Pairs = $ProfileConfig[$Profile].pairs
$EstimatedTotalMinutes = [math]::Round(($EstimatedSeconds * $Pairs * $SeedCount) / 60, 1)

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " memoriX Benchmark Infrastructure V2" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Execution Mode : $ExecMode" -ForegroundColor $(if ($Real) { "Yellow" } else { "White" })
if ($Model) {
    Write-Host "  Model          : $Model" -ForegroundColor White
}
Write-Host "  Profile        : $Profile ($Pairs pairs x $SeedCount seeds)" -ForegroundColor White
Write-Host "  Timeout/Run    : $Timeout s" -ForegroundColor White
Write-Host "  Output Dir     : $OutputDir" -ForegroundColor White
if ($Families) {
    Write-Host "  Families       : $($Families -join ', ')" -ForegroundColor White
}
if ($Seeds) {
    Write-Host "  Seeds          : $($Seeds -join ', ')" -ForegroundColor White
}
Write-Host "  Est. Duration  : ~$EstimatedTotalMinutes min" -ForegroundColor White
Write-Host "  Report         : $Report" -ForegroundColor White
if ($Report) {
    $GenList = @("Markdown")
    if (-not $NoDocx)  { $GenList += "DOCX" }
    if (-not $NoPdf)   { $GenList += "PDF" }
    if (-not $NoFigures) { $GenList += "Figures" }
    Write-Host "  Report Formats : $($GenList -join ', ')" -ForegroundColor White
}
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Build argument list for orchestrator
# ---------------------------------------------------------------------------
$Args = @($OrchestratorScript)
$Args += "--profile"
$Args += $Profile

if ($Families) {
    $Args += "--families"
    $Args += $Families
}

if ($Seeds) {
    $Args += "--seeds"
    $Args += $Seeds
}

if ($Resume) {
    $Args += "--resume"
}

if ($DryRun) {
    $Args += "--dry-run"
}

if ($Real) {
    $Args += "--real"
}

if ($Model) {
    $Args += "--model"
    $Args += $Model
}

if ($Timeout) {
    $Args += "--timeout"
    $Args += $Timeout
}

$Args += "--output"
$Args += $OutputDir

if ($Estimate) {
    $Args += "--estimate"
}

if ($Status) {
    $Args += "--status"
}

if ($Validate) {
    $Args += "--validate"
}

if ($Aggregate) {
    $Args += "--aggregate"
}

if ($Report) {
    $Args += "--report"
}

if ($Package) {
    $Args += "--package"
}

# ---------------------------------------------------------------------------
# Execute orchestrator
# ---------------------------------------------------------------------------
Write-Host "Executing: $Python $($Args -join ' ')" -ForegroundColor Gray
Write-Host ""
& $Python @Args
$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Host ""
    Write-Host "Benchmark completed successfully." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Benchmark finished with errors (exit code: $ExitCode)." -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# Post-run reporting: generate DOCX, PDF, and Figures via Python
# ---------------------------------------------------------------------------
if ($Report -and $ExitCode -eq 0) {
    Write-Host ""
    Write-Host "--- Post-Run Report Generation ---" -ForegroundColor Cyan

    $NeedsReport = (-not $NoDocx) -or (-not $NoPdf) -or (-not $NoFigures)

    if ($NeedsReport) {
        # Determine which report scripts to call
        $ReportArgs = @()
        $ReportArgs += "-OutputDir"
        $ReportArgs += $OutputDir
        $ReportArgs += "-Profile"
        $ReportArgs += $Profile

        if (-not $NoDocx) {
            $ReportArgs += "-Docx"
        }
        if (-not $NoPdf) {
            $ReportArgs += "-Pdf"
        }
        if (-not $NoFigures) {
            $ReportArgs += "-Figures"
        }
        if ($Model) {
            $ReportArgs += "-Model"
            $ReportArgs += $Model
        }

        $ReportScript = Join-Path $ScriptDir "generate_report.ps1"

        # Fall back to inline Python if the dedicated script does not exist
        if (Test-Path $ReportScript) {
            Write-Host "Running report generator: $ReportScript $($ReportArgs -join ' ')" -ForegroundColor Gray
            & $ReportScript @ReportArgs
            $ReportExit = $LASTEXITCODE
        } else {
            # Build an inline Python one-liner that calls the report generator
            $PyCode = @"
import sys, json
from pathlib import Path

output_dir = Path(r"$OutputDir")
profile = "$Profile"
no_docx = $(if ($NoDocx) { "True" } else { "False" })
no_pdf = $(if ($NoPdf) { "True" } else { "False" })
no_figures = $(if ($NoFigures) { "True" } else { "False" })

# Find the latest campaign directory
campaigns = sorted([d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("campaign-")], key=lambda p: p.stat().st_mtime, reverse=True)
if not campaigns:
    print("No campaign directories found in output_dir. Skipping report generation.")
    sys.exit(0)

campaign_dir = campaigns[0]
campaign_id = campaign_dir.name
raw_path = campaign_dir / "raw_results.json"

print(f"Generating reports for campaign: {campaign_id}")
print(f"  Output dir: {output_dir}")

# Import report generator
sys.path.insert(0, str(Path(r"$RepoRoot")))
from benchmarks.reporting.report_generator import ReportGenerator
from benchmarks.reporting.figures import FigureGenerator
from benchmarks.orchestrator.data_models import AggregateReport

gen = ReportGenerator(output_dir)

# Load raw results and build aggregate reports
import json
if raw_path.exists():
    with open(raw_path, "r", encoding="utf-8") as fh:
        raw_results = json.load(fh)
else:
    raw_results = []

# Build simple aggregate reports from raw data
from collections import defaultdict
families_data = defaultdict(list)
for r in raw_results:
    families_data[r["family"]].append(r)

aggregate_reports = []
for family_id, runs in families_data.items():
    total = len(runs)
    passed = sum(1 for r in runs if r["status"] == "passed")
    f1s = [r.get("f1", 0.0) for r in runs]
    latencies = [r.get("latency_ms", 0.0) for r in runs]
    latencies_sorted = sorted(latencies)
    aggregate_reports.append(AggregateReport(
        schema_version=1,
        campaign_id=campaign_id,
        family=family_id,
        precision=sum(f1s) / max(total, 1),
        recall=sum(f1s) / max(total, 1),
        f1=sum(f1s) / max(total, 1),
        pass_rate=passed / max(total, 1),
        median_latency=latencies_sorted[total // 2] if total else 0.0,
        p95_latency=latencies_sorted[int(total * 0.95)] if total else 0.0,
        total_runs=total,
        failed_runs=total - passed,
    ))

# Figures
if not no_figures:
    print("  Generating figures...")
    fig_gen = FigureGenerator(output_dir)
    raw_path_obj = raw_path if raw_path.exists() else None
    if raw_path_obj:
        fig_gen.generate_all(campaign_id, aggregate_reports, raw_results)
        print("  Figures generated.")
    else:
        print("  Skipping figures (no raw_results.json found).")

# DOCX
if not no_docx:
    print("  Generating DOCX...")
    try:
        docx_path = gen.generate_docx(campaign_id, profile, [r.family for r in aggregate_reports], aggregate_reports)
        print(f"  DOCX: {docx_path}")
    except Exception as e:
        print(f"  DOCX generation failed: {e}")

# PDF
if not no_pdf:
    print("  Generating PDF...")
    try:
        pdf_path = gen.generate_pdf(campaign_id, profile, [r.family for r in aggregate_reports], aggregate_reports)
        print(f"  PDF: {pdf_path}")
    except Exception as e:
        print(f"  PDF generation failed: {e}")

print("Report generation complete.")
"@

            Write-Host "Running inline report generation..." -ForegroundColor Gray
            & $Python -c $PyCode
            $ReportExit = $LASTEXITCODE
        }

        if ($ReportExit -eq 0) {
            Write-Host "Report generation completed successfully." -ForegroundColor Green
        } else {
            Write-Host "Report generation encountered errors (exit code: $ReportExit)." -ForegroundColor Yellow
        }
    } else {
        Write-Host "All report formats skipped (--NoDocx, --NoPdf, --NoFigures)." -ForegroundColor Gray
    }

    Write-Host "--- End Report Generation ---" -ForegroundColor Cyan
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host "Output: $OutputDir" -ForegroundColor Gray
exit $ExitCode
