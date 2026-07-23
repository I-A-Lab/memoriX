from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from memory.adaptive.observability import (
    MemoryMetricSample,
    MemoryObservabilityStatus,
    audit_memory_observability,
    build_memory_observability_report,
    calculate_memory_health_indicators,
    collect_memory_observability_samples,
)


class MemoryObservabilityTests(unittest.TestCase):
    def _write_jsonl(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    def test_audit_is_read_only(self) -> None:
        result = audit_memory_observability()
        self.assertFalse(result.persistent_snapshots_present)
        self.assertFalse(result.runtime_modified)
        self.assertFalse(result.neural_model_loaded)

    def test_metric_sample_validates(self) -> None:
        sample = MemoryMetricSample("hot_site_utilization", 0.5, "ratio", "test")
        sample.validate()
        self.assertEqual(sample.to_dict()["metric_name"], "hot_site_utilization")

    def test_empty_runtime_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent) / "missing"
            result = collect_memory_observability_samples(root)
            self.assertFalse(root.exists())
            self.assertEqual(result.files_inspected, 0)
            self.assertEqual(result.samples[0].source, "runtime_observability")

    def test_collection_reads_hot_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            self._write_jsonl(root / "hot_site" / "titan_metadata.jsonl", [
                {"memory_id": "m1", "active": True, "capacity": 10, "metadata": {"protected": True}},
                {"memory_id": "m2", "active": False, "capacity": 10},
            ])
            result = collect_memory_observability_samples(root)
            values = {sample.metric_name: sample.metric_value for sample in result.samples}
            self.assertEqual(values["hot_site_utilization"], 0.2)
            self.assertEqual(values["protected_memory_ratio"], 0.5)
            self.assertEqual(values["inactive_memory_ratio"], 0.5)

    def test_latest_memory_record_wins(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            self._write_jsonl(root / "hot_site" / "titan_metadata.jsonl", [
                {"memory_id": "m1", "active": False},
                {"memory_id": "m1", "active": True},
            ])
            result = collect_memory_observability_samples(root)
            values = {sample.metric_name: sample.metric_value for sample in result.samples}
            self.assertEqual(values["inactive_memory_ratio"], 0.0)

    def test_malformed_lines_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            path = Path(parent) / "hot_site" / "titan_metadata.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text('{"memory_id":"m1","active":true}\nnot-json\n', encoding="utf-8")
            result = collect_memory_observability_samples(parent)
            self.assertEqual(result.malformed_record_count, 1)

    def test_collection_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            self._write_jsonl(root / "hot_site" / "titan_metadata.jsonl", [
                {"memory_id": f"m{index}", "active": True}
                for index in range(5)
            ])
            result = collect_memory_observability_samples(root, assessment_limit=2)
            self.assertTrue(result.truncated)
            self.assertEqual(dict(result.source_records)["hot_metadata"], 2)

    def test_topic_filter_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            self._write_jsonl(root / "hot_site" / "titan_metadata.jsonl", [
                {"memory_id": "m1", "active": True, "metadata": {"topic_block_id": "coding"}},
                {"memory_id": "m2", "active": False, "metadata": {"topic_block_id": "music"}},
            ])
            result = collect_memory_observability_samples(root, topic_block_id="coding")
            values = {sample.metric_name: sample.metric_value for sample in result.samples}
            self.assertEqual(values["inactive_memory_ratio"], 0.0)

    def test_topic_block_metrics_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            self._write_jsonl(root / "topic_blocks" / "topic_blocks.jsonl", [
                {"block_id": "block_general", "canonical_topic": "general", "status": "active", "memory_count": 80},
                {"block_id": "block_coding", "canonical_topic": "coding", "status": "active", "memory_count": 20},
            ])
            result = collect_memory_observability_samples(root)
            values = {sample.metric_name: sample.metric_value for sample in result.samples}
            self.assertEqual(values["general_block_ratio"], 0.8)
            self.assertEqual(values["largest_block_ratio"], 0.8)

    def test_health_indicators_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            collection = collect_memory_observability_samples(parent)
            indicators = calculate_memory_health_indicators(collection)
            self.assertTrue(all(0.0 <= indicator.score <= 1.0 for indicator in indicators))

    def test_report_creates_warning_alerts_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            self._write_jsonl(root / "topic_blocks" / "topic_blocks.jsonl", [
                {"block_id": "block_general", "canonical_topic": "general", "status": "active", "memory_count": 90},
                {"block_id": "block_other", "canonical_topic": "other", "status": "active", "memory_count": 10},
            ])
            collection = collect_memory_observability_samples(root)
            report = build_memory_observability_report(collection)
            self.assertIn(report.status, {MemoryObservabilityStatus.WARNING, MemoryObservabilityStatus.CRITICAL})
            self.assertTrue(any(alert.metric_name == "general_block_ratio" for alert in report.alerts))
            self.assertFalse(report.snapshot_saved)
            self.assertFalse(report.runtime_modified)

    def test_report_marks_missing_sources(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            report = build_memory_observability_report(collect_memory_observability_samples(parent))
            self.assertEqual(report.status, MemoryObservabilityStatus.UNKNOWN)
            self.assertIn("hot_site_metadata_unavailable", report.insufficient_data)


if __name__ == "__main__":
    unittest.main()
