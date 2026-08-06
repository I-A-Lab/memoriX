from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

REPOSITORY_ROOT = find_repository_root(Path(__file__))
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory.benchmark.system_instrumentation import (
    run_instrumented_command,
    validate_system_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--request", required=True)
    run_parser.add_argument("--output", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--report", required=True)

    args = parser.parse_args()

    if args.command == "validate":
        payload = validate_system_report(Path(args.report).resolve())
        print("MEMORIX_SYSTEM_REPORT_VALID")
        print(json.dumps(payload, sort_keys=True))
        return 0

    request_path = Path(args.request).resolve()
    request = json.loads(request_path.read_text(encoding="utf-8-sig"))
    if not isinstance(request, dict):
        raise ValueError("Instrumentation request must be a JSON object.")

    command = request.get("command")
    if not isinstance(command, list) or not command:
        raise ValueError("request.command must be a non-empty list.")

    working_directory = Path(request.get("working_directory", "."))
    if not working_directory.is_absolute():
        working_directory = (REPOSITORY_ROOT / working_directory).resolve()

    tracked_directories: dict[str, Path] = {}
    raw_tracked = request.get("tracked_directories", {})
    if not isinstance(raw_tracked, dict):
        raise ValueError("tracked_directories must be an object.")
    for name, raw_path in raw_tracked.items():
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = (working_directory / path).resolve()
        tracked_directories[str(name)] = path

    benchmark_report_path = None
    raw_benchmark_report = request.get("benchmark_report_path")
    if raw_benchmark_report:
        benchmark_report_path = Path(str(raw_benchmark_report))
        if not benchmark_report_path.is_absolute():
            benchmark_report_path = (working_directory / benchmark_report_path).resolve()

    report = run_instrumented_command(
        [str(value) for value in command],
        working_directory=working_directory,
        output_directory=Path(args.output),
        timeout_seconds=float(request.get("timeout_seconds", 60.0)),
        sample_interval_seconds=float(request.get("sample_interval_seconds", 0.1)),
        ready_marker=request.get("ready_marker"),
        tracked_directories=tracked_directories,
        benchmark_report_path=benchmark_report_path,
        environment=request.get("environment"),
    )
    print("MEMORIX_SYSTEM_BENCHMARK_OK")
    print(json.dumps(report.to_dict(), sort_keys=True))
    return 0 if report.exit_code == 0 and not report.timed_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
