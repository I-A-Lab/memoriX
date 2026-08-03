# memoriX final release readiness

Part 28 closes the implementation with operator-facing release controls. It does not add another LLM-facing MCP tool. Backup, restore, command installation, and release validation remain explicit operator actions.

## Final readiness report

```powershell
py -3.10 .\tools\memorix\validation\memorix_release_readiness.py --pretty
```

The report is read-only. It verifies the repository layout, runtime isolation, OpenCode hooks, and launcher configuration without creating a runtime or loading Titan.

## One-command OpenCode launcher

```powershell
.\scripts\install_memorix_opencode_command.ps1 -Force
. $PROFILE
opencode
```

The installed command calls the repository launcher with message and tool-result capture enabled. The launcher keeps runtime data outside the Git repository and starts the MCP stdio child process on demand through OpenCode.

## Final smoke test

```powershell
py -3.10 .\tools\memorix\validation\memorix_demo_smoke.py --pretty
```

The isolated QuickTemp scenario checks short-term event storage, direct cold archival, candidate creation, explicit validation, Titan hot-site retrieval, and Project Archive recording.
