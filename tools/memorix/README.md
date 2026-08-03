# memoriX tools

Command-line entry points are grouped by operational responsibility:

- `research/`: reproducible benchmarks, campaigns, datasets, and reports.
- `diagnostics/`: read-only diagnostics and isolated dry-run observations.
- `validation/`: release, probe, smoke, integration, and full verification tools.

Runtime and operator entry points remain in `scripts/` until phase 2A3 because
they are referenced by OpenCode, the Windows Task Scheduler, or PowerShell
profiles.
