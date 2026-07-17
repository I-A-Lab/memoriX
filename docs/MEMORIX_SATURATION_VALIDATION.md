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
py -3.10 ".\scripts\memorix_capacity_benchmark.py" `
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
& ".\scripts\verify_memorix.ps1" -AllowDirty
```

Timing values are observations, not pass/fail thresholds. Safety contracts and
bounded allocation are the normative validation criteria.
