# memoriX — Usage and Validation Guide

## Preparation

```powershell
Set-Location "D:\Ecole\Vietnam Projet\memoriX"

$PythonExe = (
    py -3.10 -c "import sys; print(sys.executable)"
).Trim()
```

## Runtime Rule

Manual tests and validations must use a runtime outside the repository:

```powershell
$RuntimeRoot = Join-Path `
    $env:TEMP `
    "memorix-runtime"
```

The `memory/runtime` folder must not be created by tests.

## Application Launcher Pre-validation

```powershell
& "tools\memorix\runtime\start_opencode_with_memorix.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -ValidateOnly
```

## Launching the Application with memoriX

```powershell
& "tools\memorix\runtime\start_opencode_with_memorix.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -ResetRuntime
```

## Native Tools

- `memory_store` ;
- `memory_retrieve` ;
- `memory_candidates_list` ;
- `memory_candidate_validate` ;
- `memory_candidate_reject` ;
- `memory_consolidate` ;
- `memory_status`;
- `project_archive_record` — mutation with confirmation;
- `project_archive_list` — read-only;
- `project_snapshot_rebuild` — mutation with confirmation;
- `project_snapshot_get` — read-only.

A pending or rejected candidate must never be returned by `memory_retrieve`.

## Typecheck

```powershell
bun run --cwd "packages\opencode" typecheck
```

## memoriX TypeScript Tests

```powershell
bun test `
    --cwd "packages\opencode" `
    --timeout 120000 `
    "test/memorix"
```

## Python Tests

Limiting numeric threads avoids excessive slowdowns from Torch and BLAS:

```powershell
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"

$env:MEMORIX_RUNTIME_ROOT = Join-Path `
    $env:TEMP `
    "memorix-python-tests"

& $PythonExe -m unittest discover `
    -s "tests\memory" `
    -p "test_*.py"
```

On Windows PowerShell 5.1, `unittest` may write its normal output to stderr. Actual validation relies on `$LASTEXITCODE` and the `OK` line.

## MCP Server

```powershell
& $PythonExe "tools\memorix\runtime\memorix_mcp_server.py"
```

The server expects JSON-RPC requests on stdin and responds on stdout.

## Adaptive Benchmark

```powershell
& $PythonExe `
    "tools\memorix\research\memorix_adaptive_design_benchmark.py"
```

The benchmark uses synthetic scenarios and does not apply any actions.

## Live Probe

```powershell
& $PythonExe `
    "tools\memorix\validation\memorix_live_probe.py" `
    $RuntimeRoot
```

Expected output:

```text
status: healthy
checks_failed: 0
read_only: true
runtime_modified: false
```

## Main Variables

- `MEMORIX_ENABLED` ;
- `MEMORIX_PYTHON_EXECUTABLE` ;
- `MEMORIX_PROJECT_ROOT` ;
- `MEMORIX_RUNTIME_ROOT` ;
- `MEMORIX_TIMEOUT_MS` ;
- `MEMORIX_TITAN_*` parameters ;
- `MEMORIX_HOOK_*` parameters.

## Security Contracts

- hot-site only retrieval ;
- explicit cold search only ;
- no automatic validation ;
- no automatic rehydration ;
- no physical deletion from the cold site ;
- adaptive functions in observation or dry-run ;
- memory tools excluded from hooks ;
- memoriX failure is non-blocking for the main application.

## Git Checks

```powershell
git status --short
git diff --check
git log -10 --oneline
```

## Project Archive

The Project Archive is an explicit append-only cold storage:

```text
<runtime>/cold_site/project_archive/
├── project_entries.jsonl
└── project_snapshots.jsonl
```

MCP Tools:

- `memorix_project_entry_record`;
- `memorix_project_entries_list`;
- `memorix_project_snapshot_rebuild`;
- `memorix_project_snapshot_get`.

Structured entries are immutable. Each rebuild adds a new snapshot version. None of these operations write to Titan and no Project Archive data is used as a retrieval fallback.

Application Permissions:

- `project_archive_record` : `ask`;
- `project_snapshot_rebuild` : `ask`;
- `project_archive_list` : read-only;
- `project_snapshot_get` : read-only.

All four tools are mandatory exclusions from hooks.

## Protected Nightly

The nightly uses a unique runner with a lock, append-only history, and terminal state:

```text
<runtime>/operations/nightly/
├── latest.json
├── runs.jsonl
└── nightly.lock
```

Main commands:

```powershell
$RuntimeRoot = Join-Path $env:LOCALAPPDATA "memoriX\runtime"

& ".\tools\memorix\operations\run_memorix_nightly.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -KeepShortTerm `
    -Trigger "manual"

& ".\tools\memorix\operations\install_memorix_nightly_task.ps1" `
    -TaskName "memoriX Nightly Consolidation" `
    -RuntimeRoot $RuntimeRoot `
    -DailyAt "02:00"
```

The native `memory_nightly_run` tool requires native permission before execution. It is excluded from hooks and uses `clear_short_term_after_success=true` by default.

The complete installation, verification, and troubleshooting procedure is described in [MEMORIX_NIGHTLY_OPERATIONS.md](MEMORIX_NIGHTLY_OPERATIONS.md).

## Capacity operations

Use `memory_capacity_status` for inspection,
`memory_capacity_plan` for a dry-run plan, and
`memory_capacity_prune` for explicitly approved soft deactivation. Capacity
logs are stored outside Git under `<runtime>/operations/capacity/`. Detailed
procedures are in `MEMORIX_CAPACITY_OPERATIONS.md`.

## Memory pressure operations

Use `memorix_memory_pressure.py` for local diagnosis, or the read-only MCP/native pressure tools. Synthetic counts up to 6,000,000 do not allocate equivalent objects.

## Retention-ranking operations

Use `tools/memorix/diagnostics/memorix_retention_ranking.py` for local diagnostics and the MCP/native retention-ranking tools for integrated inspection. All operations are read-only. The synthetic benchmark is `tools/memorix/research/memorix_retention_ranking_benchmark.py`.

## Adaptive-routing operations

Use `tools/memorix/diagnostics/memorix_adaptive_routing.py`, MCP `memorix_adaptive_routing_plan`, or native `adaptive_routing_plan` for read-only diagnostics.

## Policy-search operations

Use the policy-search CLI and benchmark scripts for dry-run inspection.

## Policy lifecycle operations

Use activation and rollback plans before applying registry changes; mutation tools require explicit permission.


## Topic-block operations

See `docs/MEMORIX_TOPIC_BLOCKS.md` and `docs/MEMORIX_TOPIC_BLOCKS_VALIDATION.md`.

## Part 26 - controlled consolidation

memoriX now supports reviewed consolidation plans, local session state, scheduling, recovery, MCP, and application integration.

## Part 27 - Observability

Bounded diagnostics, snapshots, alerts, drift comparison, and continuous evaluation are available without loading Titan or mutating memory policies.
## Final release operations

Use `memorix_release_readiness.py` before demonstrations, `memorix_demo_smoke.py` for an isolated full lifecycle check, and the verified runtime backup/restore scripts before moving or resetting operator data.
