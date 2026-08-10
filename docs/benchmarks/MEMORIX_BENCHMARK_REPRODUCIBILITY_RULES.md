# MEMORIX BENCHMARK REPRODUCIBILITY RULES

To guarantee scientific validity and external auditability, the benchmark campaign must adhere strictly to the following reproducibility invariants.

## 1. Environment Lockdown
- **Git Commit:** The target codebase commit must be locked, logged, and untainted (e.g., `git status` must be completely clean before any run starts).
- **Python Dependencies:** Dependencies must be installed strictly from a hashed `requirements.txt` or `poetry.lock`. Floating dependencies (e.g., `package>=1.0`) are forbidden.
- **Model Parameters:** The target LLM model identifier must be fully qualified (e.g., `opencode/big-pickle-2026-08-01` instead of `opencode/big-pickle-latest`). Temperature must be explicitly set (preferably 0.0 for deterministic evaluation, unless multi-seed variance testing requires a non-zero temperature, in which case it must be strictly logged).

## 2. Seed Control
- A fixed array of at least 5 seeds must be defined *before* the campaign begins.
- These exact seeds must be applied to the orchestrator, the dataset sampler, and the LLM API calls.
- Changing seeds mid-campaign to "fix" a failing run is scientific fraud and strictly prohibited.

## 3. Workspace Isolation
- Every single task run (regardless of condition) must execute in a freshly generated, isolated runtime folder.
- There must be no shared state, no shared `.env` files, and no shared memory databases between runs (except explicitly in the multi-agent shared Titan scenario).
- At the end of the run, the entire isolated folder must be zipped and archived.

## 4. Hardware Reporting
- The report must statically contain the hardware profile: OS, Total RAM, CPU Cores/Model, and Disk Type (SSD/HDD), as these impact latency and OOM failures.
- No dynamic hardware polling during the test to avoid arbitrary latency overheads.

## 5. Result Freezing
- Once a profile (e.g., Pilot, Standard, Large) completes, its raw results are immutable.
- If a bug in the benchmark harness is found later, the bug is fixed, and a *new* campaign with a new ID is run. The old flawed data cannot be patched.
