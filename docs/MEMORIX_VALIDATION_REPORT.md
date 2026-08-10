# memoriX — Validation Report After Part 18

## Audited Functional Review

- Branch: elwen
- Functional base commit: 429a4554ce3fea32b1dce451dee31dabd2871b82
- Initial validation part 17: 2026-07-15 14:24:26 +02:00
- Operational validation part 18: 2026-07-16
- Python: Python 3.10.11
- Bun: 1.3.14

## Automated Results

| Control | Result |
|---|---|
| OpenCode Typecheck | PASS |
| memoriX TypeScript tests | PASS |
| Complete Python suite, including Project Archive | PASS |
| Compilation of MCP, Live Probe, and benchmark scripts | PASS |
| Hot-only contract | PASS |
| Explicit cold search only | PASS |
| Test runtime isolation | PASS |
| Single canonical Titan implementation | PASS |
| Append-only Project Archive and versioned snapshots | PASS |
| MCP Project Archive tools | PASS |
| Project Archive OpenCode client, service, and tools | PASS |
| Project Archive native mutation permissions | PASS |
| Mandatory hook exclusions | PASS |
| Absence of Titan write by Project Archive | PASS |
| Protected nightly runner and exclusive lock | PASS |
| `latest.json` log and `runs.jsonl` history | PASS |
| Nightly CLI and PowerShell wrapper | PASS |
| Native OpenCode `memory_nightly_run` tool | PASS |
| Native permission before OpenCode nightly | PASS |
| Nightly exclusion in hooks | PASS |
| Daily Windows task at 02:00 | PASS |
| Immediate execution via Task Scheduler | PASS |
| `LastTaskResult = 0` and `completed` status | PASS |

## OpenCode Manual Validation

The complete candidate management scenario validated:

- `memory_status` on a clean runtime;
- empty list of initial candidates;
- creation of a pending candidate;
- absence of retrieval before validation;
- validation to the Titan hot site;
- retrieval of the validated active memory;
- creation and rejection of a second candidate;
- absence of retrieval for the rejected candidate;
- manual consolidation creating a pending candidate;
- no automatic validation.

Final state observed during this scenario:

- pending candidates: 1;
- validated candidates: 1;
- rejected candidates: 1;
- active Titan memories: 1;
- short-term events: 2;
- cold archive events: 2.

## Live Probe

- status: healthy;
- checks failed: 0;
- read-only: true;
- runtime modified: false;
- gateway instantiated: false;
- Titan loaded: false.

## Validated Architecture

1. short-term and cold archive writing;
2. pending candidates;
3. logical human validation;
4. rejection without Titan write;
5. Titan active hot site;
6. hot-only retrieval;
7. consolidation without automatic validation;
8. Python gateway;
9. MCP server;
10. TypeScript client and service;
11. native OpenCode tools;
12. configurable OpenCode hooks;
13. adaptive observations and dry-run;
14. isolated benchmark;
15. read-only Live Probe;
16. default runtime outside repository;
17. native mutation permissions;
18. mandatory hook exclusions;
19. append-only Project Archive;
20. versioned project snapshots;
21. Project Archive Gateway, MCP, and OpenCode integration;
22. protected nightly runner;
23. exclusive lock and stale lock recovery;
24. append-only operational log;
25. Python CLI and PowerShell wrapper;
26. native OpenCode `memory_nightly_run` tool;
27. nightly native permission;
28. nightly exclusion in hooks;
29. daily Windows task;
30. validated Task Scheduler execution with Windows result `0`.

## Nightly Operational Validation

The real Windows scenario validated:

- runtime `%LOCALAPPDATA%\memoriX\runtime`, outside repository;
- manual test preserving short-term memory;
- installation of `memoriX Nightly Consolidation` at 02:00;
- PowerShell action pointing to `run_memorix_nightly.ps1`;
- memoriX `task_scheduler` trigger;
- immediate launch by `Start-ScheduledTask`;
- final Windows state `Ready`;
- `LastTaskResult` equal to `0`;
- memoriX status `completed`;
- absence of residual lock;
- Git repository unchanged after operational tests.

## Remaining Limitations

- adaptive system connected to real runtime;
- general transactions;
- migrations and crash recovery;
- concurrency, corruption, saturation, and cross-platform tests.

Adaptive actions, automatic validation, cold-to-hot rehydration, and physical deletion remain intentionally disabled.

## Project Archive Validation

The validated flow covers:

1. creation of append-only structured entries;
2. filtering by project and type;
3. deterministic snapshot reconstruction;
4. version increment without overwriting;
5. persistence after gateway restart;
6. MCP `tools/call` protocol;
7. non-blocking TypeScript client and service;
8. native OpenCode tools;
9. mutation confirmations;
10. read access without mutation permission;
11. mandatory hook exclusion;
12. absence of writing to Titan.

## Part 19 capacity and saturation validation

Part 19 validates runtime capacity inspection, admission rejection before
Titan writes, pending-candidate preservation, controlled soft pruning,
operational locking and logs, MCP/OpenCode exposure, and bounded synthetic
scenarios through 6,000,000 active items. Benchmarks do not modify runtime data
or access the cold site.

## Part 20 memory-pressure validation

Part 20 adds deterministic per-memory metrics, read-only runtime inspection, CLI simulation, MCP and OpenCode exposure, bounded benchmarks, and safety documentation.

## Part 21 adaptive retention validation

Part 21 validates deterministic scoring, explainable decisions, persisted-runtime ranking, bounded simulation, MCP and OpenCode exposure, synthetic benchmarks, and the strict no-mutation/no-cold-site/no-Titan contract. Detailed evidence is in `docs/MEMORIX_RETENTION_VALIDATION.md`.

## Part 22 adaptive-routing validation

Part 22 validates deterministic decisions, runtime inspection, MCP/OpenCode contracts, and bounded simulations through 6,000,000 memories.

## Part 23 policy-search validation

Part 23 validates runtime-aware policy search, MCP, OpenCode, and bounded benchmarks.

## Part 24 policy lifecycle validation

Part 24 validates registry persistence, review, activation, rollback, MCP, OpenCode, and benchmarks.


## Part 25 topic-block validation

See `docs/MEMORIX_TOPIC_BLOCKS.md` and `docs/MEMORIX_TOPIC_BLOCKS_VALIDATION.md`.

## Part 26 - controlled consolidation

memoriX now supports reviewed consolidation plans, local session state, scheduling, recovery, MCP, and OpenCode integration.

## Part 27 - Observability

Bounded diagnostics, snapshots, alerts, drift comparison, and continuous evaluation are available without loading Titan or mutating memory policies.
## Part 28 validation

The final release suite covers read-only readiness inspection, safe runtime archive verification, atomic restore, path traversal rejection, and an isolated QuickTemp event-to-Titan acceptance workflow.
