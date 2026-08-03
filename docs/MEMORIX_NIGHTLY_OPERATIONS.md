# memoriX — Nightly consolidation operations

## Purpose

The nightly job converts eligible short-term events into pending candidates while preserving memoriX safety contracts:

- no automatic candidate validation;
- no automatic cold-to-hot rehydration;
- no physical cold-site deletion;
- Project Archive remains untouched;
- a lock prevents concurrent nightly runs;
- short-term cleanup occurs only after a successful run and only when enabled.

## Execution paths

The same protected Python runner is used by every entry point:

```text
Windows Task Scheduler
    -> scripts/run_memorix_nightly.ps1
    -> scripts/memorix_nightly.py
    -> memory.sync.nightly_runner.NightlyRunner

OpenCode memory_nightly_run
    -> TypeScript client/service
    -> MCP memorix_run_nightly
    -> NightlyRunner
```

## Runtime location

The recommended Windows runtime is outside the repository:

```text
%LOCALAPPDATA%\memoriX\runtime
```

Nightly operational files are stored under:

```text
<runtime>\operations\nightly\
├── latest.json
├── runs.jsonl
└── nightly.lock
```

- `latest.json` contains the latest terminal status;
- `runs.jsonl` is an append-only operational history;
- `nightly.lock` exists only while a run owns the lock.

## Manual execution

Keep short-term events after a successful test run:

```powershell
$RuntimeRoot = Join-Path $env:LOCALAPPDATA "memoriX\runtime"

& ".\scripts\run_memorix_nightly.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -KeepShortTerm `
    -Trigger "manual"
```

Use normal cleanup behavior:

```powershell
& ".\scripts\run_memorix_nightly.ps1" `
    -RuntimeRoot $RuntimeRoot `
    -Trigger "manual"
```

Read the latest status without creating a runtime:

```powershell
py -3.10 ".\scripts\memorix_nightly.py" `
    --runtime-root $RuntimeRoot `
    --status-only `
    --pretty
```

## Windows scheduled task

Validate the task definition without modifying Windows:

```powershell
& ".\scripts\install_memorix_nightly_task.ps1" `
    -TaskName "memoriX Nightly Consolidation" `
    -RuntimeRoot $RuntimeRoot `
    -DailyAt "02:00" `
    -ValidateOnly
```

Install or replace the daily task:

```powershell
& ".\scripts\install_memorix_nightly_task.ps1" `
    -TaskName "memoriX Nightly Consolidation" `
    -RuntimeRoot $RuntimeRoot `
    -DailyAt "02:00"
```

Inspect it:

```powershell
Get-ScheduledTask `
    -TaskName "memoriX Nightly Consolidation"

Get-ScheduledTaskInfo `
    -TaskName "memoriX Nightly Consolidation"
```

Run it immediately:

```powershell
Start-ScheduledTask `
    -TaskName "memoriX Nightly Consolidation"
```

Remove it:

```powershell
& ".\scripts\remove_memorix_nightly_task.ps1" `
    -TaskName "memoriX Nightly Consolidation"
```

The scheduled task references the current repository path. Reinstall it after moving or renaming the repository.

## OpenCode tool

The native tool is:

```text
memory_nightly_run
```

It requires OpenCode approval and forwards:

```text
clear_short_term_after_success
```

The default is `true`. The tool is excluded from all memoriX hooks to prevent self-recording loops.

## Result interpretation

A successful run must have:

```text
status: completed
```

A Windows scheduled execution must also have:

```text
trigger: task_scheduler
clear_short_term_after_success: true
```

Expected Task Scheduler state after completion:

```text
State: Ready
LastTaskResult: 0
```

## Lock behavior

A live lock causes the run to exit without launching a concurrent consolidation. A stale lock may be reclaimed after the configured timeout, which defaults to six hours.

The lock must be absent after every terminal outcome. If `nightly.lock` remains after a crashed process, inspect `latest.json` and `runs.jsonl` before removing it manually.

## Operational verification

Run the complete repository verification:

```powershell
& ".\tools\memorix\validation\verify_memorix.ps1"
```

Then verify the task and latest memoriX result:

```powershell
$TaskName = "memoriX Nightly Consolidation"
$RuntimeRoot = Join-Path $env:LOCALAPPDATA "memoriX\runtime"

Get-ScheduledTaskInfo -TaskName $TaskName

Get-Content `
    (Join-Path $RuntimeRoot "operations\nightly\latest.json") `
    -Raw |
    ConvertFrom-Json
```

## Troubleshooting

### Runtime rejected

The runtime must remain outside the repository. Do not use `memory\runtime`.

### `py.exe` missing

Install Python 3.10 and ensure the Windows Python launcher is available.

### Non-zero `LastTaskResult`

Run `scripts\run_memorix_nightly.ps1` manually with the same runtime and inspect its JSON output.

### Task remains `Running`

Wait for the configured execution limit, then inspect the operational log and lock. Do not start a second run manually while a valid lock exists.

### Repository moved

Remove and reinstall the scheduled task so its action points to the new absolute path.
