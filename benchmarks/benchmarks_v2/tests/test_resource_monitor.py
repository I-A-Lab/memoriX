from __future__ import annotations

import time

import pytest

from benchmarks.orchestrator.resource_monitor import ResourceMonitor


class TestPeakRssPositive:
    def test_peak_rss_positive(self, tmp_path):
        """Peak RSS is positive after monitoring."""
        monitor = ResourceMonitor(output_dir=tmp_path)
        monitor.start()
        _ = [bytearray(1024) for _ in range(100)]
        time.sleep(0.05)
        monitor.stop()
        summary = monitor.get_summary()
        assert summary["peak_rss_mb"] > 0


class TestMeanCpuNonNegative:
    def test_mean_cpu_non_negative(self, tmp_path):
        """Mean CPU is non-negative."""
        monitor = ResourceMonitor(output_dir=tmp_path)
        monitor.start()
        time.sleep(0.05)
        monitor.stop()
        summary = monitor.get_summary()
        assert summary["mean_cpu_percent"] >= 0


class TestDiskIONonNegative:
    def test_disk_io_non_negative(self, tmp_path):
        """Disk I/O values are non-negative."""
        monitor = ResourceMonitor(output_dir=tmp_path)
        monitor.start()
        test_file = tmp_path / "io_test.bin"
        test_file.write_bytes(b"X" * 10240)
        time.sleep(0.05)
        monitor.stop()
        summary = monitor.get_summary()
        assert summary["disk_read_bytes"] >= 0
        assert summary["disk_write_bytes"] >= 0


class TestSummaryContainsAllKeys:
    def test_summary_contains_all_keys(self, tmp_path):
        """Summary dict contains all expected keys."""
        monitor = ResourceMonitor(output_dir=tmp_path)
        monitor.start()
        time.sleep(0.02)
        monitor.stop()
        summary = monitor.get_summary()

        expected_keys = {
            "peak_rss_mb",
            "mean_cpu_percent",
            "disk_read_bytes",
            "disk_write_bytes",
            "wall_time_seconds",
        }
        assert expected_keys.issubset(set(summary.keys()))
