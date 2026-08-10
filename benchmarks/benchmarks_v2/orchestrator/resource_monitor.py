from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional

import psutil


class ResourceMonitor:
    """Monitor resource usage during benchmark execution."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self._output_dir = output_dir
        self._process = psutil.Process(os.getpid())
        self._start_time: float = 0.0
        self._start_disk_read: int = 0
        self._start_disk_write: int = 0
        self._peak_rss: int = 0
        self._cpu_samples: list[float] = []

    def start(self) -> None:
        """Capture baseline resource readings."""
        self._process.cpu_percent(None)
        self._start_time = time.monotonic()

        try:
            io_counters = self._process.io_counters()
            self._start_disk_read = io_counters.read_bytes
            self._start_disk_write = io_counters.write_bytes
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            self._start_disk_read = 0
            self._start_disk_write = 0

        self._peak_rss = self._get_rss()
        self._cpu_samples = []

    def stop(self) -> None:
        """Stop monitoring and take final readings."""
        self._sample()

    def _sample(self) -> None:
        """Take a resource sample."""
        rss = self._get_rss()
        if rss > self._peak_rss:
            self._peak_rss = rss

        try:
            cpu = self._process.cpu_percent()
            self._cpu_samples.append(cpu)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self._cpu_samples.append(0.0)

    def _get_rss(self) -> int:
        try:
            info = self._process.memory_info()
            return info.rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0

    def get_summary(self) -> Dict[str, float]:
        """Return a summary of resource usage."""
        # Take a final sample
        self._sample()

        wall_time = time.monotonic() - self._start_time

        try:
            io_counters = self._process.io_counters()
            disk_read = io_counters.read_bytes - self._start_disk_read
            disk_write = io_counters.write_bytes - self._start_disk_write
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            disk_read = 0
            disk_write = 0

        mean_cpu = sum(self._cpu_samples) / max(len(self._cpu_samples), 1)

        return {
            "peak_rss_mb": self._peak_rss / (1024 * 1024),
            "mean_cpu_percent": mean_cpu,
            "disk_read_bytes": max(0, disk_read),
            "disk_write_bytes": max(0, disk_write),
            "wall_time_seconds": wall_time,
        }
