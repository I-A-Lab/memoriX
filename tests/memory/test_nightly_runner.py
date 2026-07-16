from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from memory.data.paths import MemoryStoragePaths
from memory.sync.nightly_runner import EXIT_ALREADY_RUNNING, EXIT_COMPLETED, EXIT_FAILED, NightlyLock, NightlyRunner


class _Report:
    active_memories_replayed = 2
    short_term_events_cleared = 3
    cold_site_modified = False
    automatic_candidate_validation = False
    def to_dict(self):
        return {'consolidation': {'candidates_created': 1}}


class NightlyRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'runtime'
    def tearDown(self):
        self.temp.cleanup()

    @patch('memory.sync.nightly_runner.MemoriXGateway')
    def test_success_writes_status_and_releases_lock(self, gateway):
        gateway.return_value.run_nightly_consolidation.return_value = _Report()
        result = NightlyRunner(self.root).run()
        paths = MemoryStoragePaths.from_runtime_root(self.root)
        self.assertEqual(result.exit_code, EXIT_COMPLETED)
        self.assertFalse(paths.nightly_lock.exists())
        self.assertEqual(json.loads(paths.nightly_latest.read_text())['status'], 'completed')
        self.assertEqual(len(paths.nightly_runs.read_text().splitlines()), 2)

    @patch('memory.sync.nightly_runner.MemoriXGateway')
    def test_failure_releases_lock(self, gateway):
        gateway.return_value.run_nightly_consolidation.side_effect = RuntimeError('boom')
        result = NightlyRunner(self.root).run()
        paths = MemoryStoragePaths.from_runtime_root(self.root)
        self.assertEqual(result.exit_code, EXIT_FAILED)
        self.assertFalse(paths.nightly_lock.exists())

    def test_second_runner_is_rejected(self):
        paths = MemoryStoragePaths.from_runtime_root(self.root)
        lock = NightlyLock(paths.nightly_lock, timeout_hours=6, runtime_root=self.root.resolve())
        lock.acquire()
        try:
            result = NightlyRunner(self.root).run()
            self.assertEqual(result.exit_code, EXIT_ALREADY_RUNNING)
        finally:
            lock.release()

    def test_status_only_read_does_not_create_files(self):
        runner = NightlyRunner(self.root)
        self.assertIsNone(runner.latest_status())
        self.assertFalse(self.root.exists())

    def test_repository_runtime_is_rejected(self):
        with self.assertRaises(ValueError):
            NightlyRunner(Path(__file__).resolve().parents[2] / 'memory' / 'runtime')

if __name__ == '__main__':
    unittest.main()
