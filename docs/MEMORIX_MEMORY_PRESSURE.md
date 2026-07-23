# memoriX Memory Pressure

Memory pressure is a deterministic, read-only assessment of persisted hot-site metadata. It never loads Titan, accesses the cold site, applies pruning, or rehydrates history.

## Individual signals

The score combines age, low usage, low importance, low momentum, low surprise, inactivity, and replacement. Every component is normalized to `[0, 1]`. Protected memories always return `keep_protected`.

## Runtime commands

```powershell
py -3.10 .\scripts\memorix_memory_pressure.py --runtime-root $env:MEMORIX_RUNTIME_ROOT --pretty
py -3.10 .\scripts\memorix_memory_pressure.py --simulate-count 6000000 --assessment-limit 1 --pretty
```

## OpenCode tools

- `memory_pressure_status`: read-only aggregate and bounded assessments.
- `memory_pressure_inspect`: read-only assessment for one memory ID.

Both tools are excluded from automatic capture hooks.
