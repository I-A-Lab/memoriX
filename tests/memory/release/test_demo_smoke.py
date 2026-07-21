from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.release import run_demo_smoke


class DemoSmokeTests(unittest.TestCase):
    def test_complete_quicktemp_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            report = run_demo_smoke(runtime)
            self.assertEqual(report.status, "passed")
            self.assertEqual(report.short_term_event_count, 1)
            self.assertEqual(report.cold_event_count, 1)
            self.assertEqual(report.pending_before_validation, 1)
            self.assertEqual(report.validated_candidate_count, 1)
            self.assertGreaterEqual(report.retrieved_memory_count, 1)
            self.assertEqual(report.project_archive_entry_count, 1)
            self.assertTrue((runtime / "hot_site/titan_metadata.jsonl").is_file())
