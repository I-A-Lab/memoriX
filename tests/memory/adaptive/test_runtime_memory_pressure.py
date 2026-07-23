from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from memory.adaptive import inspect_runtime_memory_pressure, inspect_runtime_memory_pressure_item
from memory.data import MemoryStoragePaths

class RuntimeMemoryPressureTests(unittest.TestCase):
    def test_empty_runtime_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"runtime"
            report=inspect_runtime_memory_pressure(runtime_root=root)
            self.assertFalse(root.exists())
        self.assertEqual(report.snapshot.memory_count,0)
        self.assertFalse(report.neural_model_loaded)
        self.assertFalse(report.cold_site_accessed)

    def test_latest_metadata_is_assessed_without_cold_access(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=MemoryStoragePaths.from_runtime_root(directory)
            paths.titan_metadata.parent.mkdir(parents=True,exist_ok=True)
            records=[
              {"memory_id":"old","stored_at":"2024-01-01T00:00:00+00:00","active":True,"metadata":{"importance":0.1,"access_count":0}},
              {"memory_id":"old","stored_at":"2024-01-01T00:00:00+00:00","active":False,"metadata":{"importance":0.0,"access_count":0}},
              {"memory_id":"new","stored_at":"2026-07-01T00:00:00+00:00","active":True,"metadata":{"importance":1.0,"access_count":20,"supersedes_memory_id":"old","pinned":True}},
            ]
            paths.titan_metadata.write_text("".join(json.dumps(x)+"\n" for x in records),encoding="utf-8")
            report=inspect_runtime_memory_pressure(runtime_root=directory, observed_at="2026-07-17T00:00:00+00:00")
            item=inspect_runtime_memory_pressure_item(runtime_root=directory,memory_id="old",observed_at="2026-07-17T00:00:00+00:00")
            self.assertFalse(paths.cold_archive_events.exists())
        self.assertEqual(report.metadata_records,3)
        self.assertEqual(report.unique_memories,2)
        self.assertEqual(report.snapshot.replaced_count,1)
        self.assertIsNotNone(item)
        self.assertEqual(item.memory_id,"old")

    def test_assessment_limit_does_not_change_aggregates(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=MemoryStoragePaths.from_runtime_root(directory)
            paths.titan_metadata.parent.mkdir(parents=True,exist_ok=True)
            paths.titan_metadata.write_text("".join(json.dumps({"memory_id":f"m{i}","stored_at":"2020-01-01T00:00:00+00:00","active":False,"metadata":{}})+"\n" for i in range(5)),encoding="utf-8")
            report=inspect_runtime_memory_pressure(runtime_root=directory,assessment_limit=2,observed_at="2026-07-17T00:00:00+00:00")
        self.assertEqual(report.snapshot.memory_count,5)
        self.assertEqual(len(report.snapshot.assessments),2)
        self.assertTrue(report.assessments_truncated)

    def test_six_million_simulation_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"runtime"
            report=inspect_runtime_memory_pressure(runtime_root=root,simulated_memory_count=6_000_000,assessment_limit=1)
            self.assertFalse(root.exists())
        self.assertEqual(report.snapshot.memory_count,6_000_000)
        self.assertLessEqual(len(report.snapshot.assessments),1)
        self.assertEqual(report.snapshot.pruning_candidate_count,6_000_000)
        self.assertTrue(report.simulated)

if __name__ == "__main__": unittest.main()
