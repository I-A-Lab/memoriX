# memoriX Saturation Validation

## Validated scenarios

The bounded benchmark covers:

```text
10,000
100,000
1,000,000
6,000,000 active items
```

Run it with:

```powershell
py -3.10 ".\tools\memorix\research\memorix_capacity_benchmark.py" `
    --runtime-root "$env:TEMP\memorix-capacity-benchmark-runtime" `
    --capacity 50000 `
    --repetitions 3 `
    --pretty
```

The report includes status latency, admission-decision latency, bounded-plan
latency, traced peak memory, pressure, available slots, and required free
slots.

## Safety assertions

The test suite verifies:

- synthetic data only;
- no runtime creation or modification;
- no cold-site access;
- no applied action;
- a bounded plan sample of at most 256 items;
- critical pressure and rejected admission at 6,000,000 active items;
- read-only OpenCode tools do not ask for mutation permission;
- pruning asks before the facade call;
- disabled TypeScript services remain non-blocking.

## Elastic capacity validation

The elastic capacity contract is verified by:

```powershell
py -3.10 -m unittest `
    "tests.memory.test_elastic_capacity" `
    "tests.memory.test_nightly_capacity_maintenance" `
    "tests.memory.benchmark.test_elastic_capacity_benchmark"
```

Verified behavior with exact numbers:

- expansion from baseline 50 to 63 (`max(50 + 10, ceil(50 * 1.25), 51)`);
- restoration to baseline 50 only when active <= floor(50 * 0.8) == 40;
- active 51 (> 40) stays expanded;
- benchmark scenario A (capacity 79, active 71) soft-forgets low-retention
  seeds but never shrinks;
- benchmark scenario B (capacity 63, active 51) forgets 20 seeds then
  shrinks back to baseline 50;
- `NightlyCapacityMaintenanceResult.to_dict()` exposes exactly the enforced
  12 keys in order;
- the cold archive stays byte-identical (sha256) through maintenance;
- the nightly runner keeps `status: completed` and includes both
  `consolidation` and `capacity_maintenance` in the latest status;
- a failing consistency gate blocks compaction and shrinking;
- default-policy pruning is reachable at >= 70% usage and respects pinned /
  protected memories;
- `max_automatic_deactivations=1` caps the nightly soft-prune to one forget.

## Required validation commands

```powershell
py -3.10 -m unittest `
    "tests.memory.benchmark.test_capacity_saturation" `
    "tests.memory.test_capacity_benchmark_cli"
```

```powershell
bun test `
    --cwd "packages\opencode" `
    --timeout 120000 `
    "test/memorix/capacity-client.test.ts" `
    "test/memorix/capacity-permissions.test.ts"
```

```powershell
& ".\tools\memorix\validation\verify_memorix.ps1" -AllowDirty
```

Timing values are observations, not pass/fail thresholds. Safety contracts and
bounded allocation are the normative validation criteria.
