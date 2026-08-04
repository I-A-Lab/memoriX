# memoriX tools

Command-line entry points are grouped by operational responsibility:

- `research/`: reproducible benchmarks, campaigns, datasets, and reports.
- `diagnostics/`: read-only diagnostics and isolated dry-run observations.
- `validation/`: release, probe, smoke, integration, and full verification tools.
- `runtime/`: MCP and OpenCode runtime launchers.
- `operations/`: nightly, backup, restore, and Windows installation helpers.

The legacy root `scripts/` directory is no longer used by memoriX. Windows Task
Scheduler and PowerShell profile bindings must point to the corresponding paths
under `tools/memorix/`.
