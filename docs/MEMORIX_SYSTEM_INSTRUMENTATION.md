# memoriX System Instrumentation

Part 34 adds subprocess-level instrumentation for benchmark executions.

## Measurements

- total wall-clock duration;
- conservative time-to-ready marker;
- process peak and mean RSS;
- mean and maximum process CPU usage;
- stdout and stderr sizes and SHA-256 hashes;
- tracked directory size before, after, and growth;
- timeout and exit status;
- optional embedding of a memory-pure benchmark report.

The implementation uses Windows process APIs on Windows and `/proc` on Linux. No third-party package is required.

## Isolation

Generated reports, samples, logs, datasets, and runtimes must be written outside the repository. Existing non-empty output directories are never overwritten.

## Limitations

The current sampler measures the launched process itself. Child-process aggregation is intentionally deferred. Time-to-ready is a conservative upper bound because redirected stdout is evaluated after process termination.
