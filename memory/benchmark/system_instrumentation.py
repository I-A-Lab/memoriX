"""System instrumentation for reproducible memoriX benchmark subprocesses."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

INSTRUMENTATION_VERSION = "34.1"


@dataclass(frozen=True, slots=True)
class ProcessSample:
    elapsed_ms: float
    rss_bytes: int
    cpu_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InstrumentationReport:
    schema_version: int
    instrumentation_version: str
    command: tuple[str, ...]
    working_directory: str
    started_at_utc: str
    duration_ms: float
    time_to_ready_ms: float | None
    timeout_seconds: float
    timed_out: bool
    exit_code: int | None
    sample_count: int
    peak_rss_bytes: int
    mean_rss_bytes: float
    mean_cpu_percent: float
    max_cpu_percent: float
    stdout_sha256: str
    stderr_sha256: str
    stdout_size_bytes: int
    stderr_size_bytes: int
    tracked_directories: dict[str, dict[str, int]]
    benchmark_report: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_instrumented_command(
    command: Sequence[str],
    *,
    working_directory: Path,
    output_directory: Path,
    timeout_seconds: float,
    sample_interval_seconds: float = 0.1,
    ready_marker: str | None = None,
    tracked_directories: Mapping[str, Path] | None = None,
    benchmark_report_path: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> InstrumentationReport:
    if not command:
        raise ValueError("command must not be empty.")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")
    if sample_interval_seconds <= 0:
        raise ValueError("sample_interval_seconds must be positive.")

    working_directory = working_directory.resolve()
    if not working_directory.is_dir():
        raise FileNotFoundError(str(working_directory))

    output_directory = output_directory.resolve()
    if output_directory.exists() and any(output_directory.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite non-empty instrumentation directory: {output_directory}"
        )
    output_directory.mkdir(parents=True, exist_ok=True)

    stdout_path = output_directory / "process.stdout.txt"
    stderr_path = output_directory / "process.stderr.txt"
    samples_path = output_directory / "process_samples.jsonl"
    report_path = output_directory / "system_report.json"

    tracked = {str(name): Path(path).resolve() for name, path in (tracked_directories or {}).items()}
    before_sizes = {name: _directory_size(path) for name, path in tracked.items()}

    child_environment = os.environ.copy()
    if environment:
        child_environment.update({str(key): str(value) for key, value in environment.items()})

    started_wall = time.perf_counter()
    started_at_utc = _utc_now()
    timed_out = False
    samples: list[ProcessSample] = []

    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        process = subprocess.Popen(
            [str(value) for value in command],
            cwd=str(working_directory),
            env=child_environment,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
            shell=False,
        )

        deadline = started_wall + timeout_seconds
        while True:
            now = time.perf_counter()
            rss_bytes, cpu_seconds = _process_usage(process.pid)
            samples.append(
                ProcessSample(
                    elapsed_ms=(now - started_wall) * 1000.0,
                    rss_bytes=max(0, int(rss_bytes)),
                    cpu_seconds=max(0.0, float(cpu_seconds)),
                )
            )

            exit_code = process.poll()
            if exit_code is not None:
                break

            if now >= deadline:
                timed_out = True
                _terminate_process(process)
                break

            time.sleep(sample_interval_seconds)

        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            _kill_process(process)
            process.wait(timeout=5.0)

    duration_ms = (time.perf_counter() - started_wall) * 1000.0
    exit_code = process.returncode

    samples_path.write_text(
        "".join(json.dumps(sample.to_dict(), sort_keys=True, separators=(",", ":")) + "\n" for sample in samples),
        encoding="utf-8",
        newline="\n",
    )

    stdout_bytes = stdout_path.read_bytes()
    stderr_bytes = stderr_path.read_bytes()
    time_to_ready_ms = _time_to_ready(stdout_bytes, ready_marker, duration_ms)
    peak_rss, mean_rss, mean_cpu, max_cpu = _aggregate_samples(samples)

    after_sizes = {name: _directory_size(path) for name, path in tracked.items()}
    directory_report = {
        name: {
            "before_bytes": int(before_sizes[name]),
            "after_bytes": int(after_sizes[name]),
            "growth_bytes": int(after_sizes[name] - before_sizes[name]),
        }
        for name in sorted(tracked)
    }

    benchmark_report = None
    if benchmark_report_path is not None:
        resolved_report_path = benchmark_report_path.resolve()
        if resolved_report_path.is_file():
            value = json.loads(resolved_report_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("benchmark report must be a JSON object.")
            benchmark_report = value

    report = InstrumentationReport(
        schema_version=1,
        instrumentation_version=INSTRUMENTATION_VERSION,
        command=tuple(str(value) for value in command),
        working_directory=str(working_directory),
        started_at_utc=started_at_utc,
        duration_ms=duration_ms,
        time_to_ready_ms=time_to_ready_ms,
        timeout_seconds=float(timeout_seconds),
        timed_out=timed_out,
        exit_code=exit_code,
        sample_count=len(samples),
        peak_rss_bytes=peak_rss,
        mean_rss_bytes=mean_rss,
        mean_cpu_percent=mean_cpu,
        max_cpu_percent=max_cpu,
        stdout_sha256=hashlib.sha256(stdout_bytes).hexdigest(),
        stderr_sha256=hashlib.sha256(stderr_bytes).hexdigest(),
        stdout_size_bytes=len(stdout_bytes),
        stderr_size_bytes=len(stderr_bytes),
        tracked_directories=directory_report,
        benchmark_report=benchmark_report,
    )
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def validate_system_report(report_path: Path) -> dict[str, Any]:
    if not report_path.is_file():
        raise FileNotFoundError(str(report_path))
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("system report must be a JSON object.")
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported system report schema_version.")
    if payload.get("instrumentation_version") != INSTRUMENTATION_VERSION:
        raise ValueError("Unsupported instrumentation_version.")
    if not isinstance(payload.get("command"), list) or not payload["command"]:
        raise ValueError("system report command must be a non-empty list.")
    if float(payload.get("duration_ms", -1)) < 0:
        raise ValueError("duration_ms must be non-negative.")
    if int(payload.get("sample_count", 0)) < 1:
        raise ValueError("sample_count must be positive.")
    if int(payload.get("peak_rss_bytes", -1)) < 0:
        raise ValueError("peak_rss_bytes must be non-negative.")
    for key in ("stdout_sha256", "stderr_sha256"):
        value = str(payload.get(key, ""))
        if len(value) != 64:
            raise ValueError(f"{key} must contain 64 hexadecimal characters.")
        int(value, 16)
    return payload


def _aggregate_samples(samples: Sequence[ProcessSample]) -> tuple[int, float, float, float]:
    if not samples:
        return 0, 0.0, 0.0, 0.0
    peak_rss = max(sample.rss_bytes for sample in samples)
    mean_rss = sum(sample.rss_bytes for sample in samples) / len(samples)
    cpu_percentages: list[float] = []
    for previous, current in zip(samples, samples[1:]):
        elapsed_seconds = (current.elapsed_ms - previous.elapsed_ms) / 1000.0
        cpu_delta = current.cpu_seconds - previous.cpu_seconds
        if elapsed_seconds > 0 and cpu_delta >= 0:
            cpu_percentages.append((cpu_delta / elapsed_seconds) * 100.0)
    if not cpu_percentages:
        return peak_rss, mean_rss, 0.0, 0.0
    return peak_rss, mean_rss, sum(cpu_percentages) / len(cpu_percentages), max(cpu_percentages)


def _time_to_ready(stdout_bytes: bytes, marker: str | None, duration_ms: float) -> float | None:
    if marker is None:
        return None
    if marker.encode("utf-8") not in stdout_bytes:
        return None
    # stdout is redirected to a file and not tailed during execution. The marker is still
    # validated, while duration is used as a conservative upper bound for readiness.
    return duration_ms


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return int(path.stat().st_size)
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += int(item.stat().st_size)
        except OSError:
            continue
    return total


def _process_usage(pid: int) -> tuple[int, float]:
    if os.name == "nt":
        return _windows_process_usage(pid)
    return _proc_process_usage(pid)


def _windows_process_usage(pid: int) -> tuple[int, float]:
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ,
        False,
        pid,
    )
    if not handle:
        return 0, 0.0
    try:
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        cpu_seconds = 0.0
        if ctypes.windll.kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            kernel_ticks = (kernel.dwHighDateTime << 32) | kernel.dwLowDateTime
            user_ticks = (user.dwHighDateTime << 32) | user.dwLowDateTime
            cpu_seconds = (kernel_ticks + user_ticks) / 10_000_000.0

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        rss_bytes = 0
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        ):
            rss_bytes = int(counters.WorkingSetSize)
        return rss_bytes, cpu_seconds
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _proc_process_usage(pid: int) -> tuple[int, float]:
    status_path = Path(f"/proc/{pid}/status")
    stat_path = Path(f"/proc/{pid}/stat")
    rss_bytes = 0
    cpu_seconds = 0.0
    try:
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                rss_bytes = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass
    try:
        fields = stat_path.read_text(encoding="utf-8").split()
        ticks = int(fields[13]) + int(fields[14])
        cpu_seconds = ticks / float(os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        pass
    return rss_bytes, cpu_seconds


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    try:
        process.terminate()
        process.wait(timeout=2.0)
    except (OSError, subprocess.TimeoutExpired):
        _kill_process(process)


def _kill_process(process: subprocess.Popen[bytes]) -> None:
    try:
        process.kill()
    except OSError:
        pass


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
