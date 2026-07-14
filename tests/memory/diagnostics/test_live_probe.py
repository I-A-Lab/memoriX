from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.diagnostics import (
    ProbeStatus,
    run_live_probe,
)


class LiveProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.root = Path(
            self.temporary_directory.name
        )

    def test_empty_existing_runtime_is_healthy(
        self,
    ) -> None:
        before = tuple(
            self.root.rglob("*")
        )

        report = run_live_probe(
            self.root,
            probe_id="probe_empty",
            generated_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        )

        after = tuple(
            self.root.rglob("*")
        )

        self.assertEqual(
            report.status,
            ProbeStatus.HEALTHY,
        )
        self.assertEqual(
            report.probe_id,
            "probe_empty",
        )
        self.assertEqual(before, after)
        self.assertTrue(
            report.safety["read_only"]
        )
        self.assertFalse(
            report.safety[
                "runtime_modified"
            ]
        )

    def test_valid_runtime_files_are_counted(
        self,
    ) -> None:
        short_term = (
            self.root
            / "short_term"
            / "events.jsonl"
        )
        cold = (
            self.root
            / "cold"
            / "events.jsonl"
        )

        short_term.parent.mkdir(
            parents=True
        )
        cold.parent.mkdir(
            parents=True
        )

        short_term.write_text(
            json.dumps({"id": 1}) + "\n",
            encoding="utf-8",
        )

        cold.write_text(
            "\n".join(
                (
                    json.dumps({"id": 1}),
                    json.dumps({"id": 2}),
                    "",
                )
            ),
            encoding="utf-8",
        )

        report = run_live_probe(
            self.root
        )

        self.assertEqual(
            report.status,
            ProbeStatus.HEALTHY,
        )
        self.assertGreaterEqual(
            report.counters[
                "reported_records"
            ],
            3,
        )
        self.assertEqual(
            report.counters[
                "checks_failed"
            ],
            0,
        )

    def test_invalid_jsonl_makes_probe_unavailable(
        self,
    ) -> None:
        path = (
            self.root
            / "cold"
            / "events.jsonl"
        )
        path.parent.mkdir(parents=True)
        path.write_text(
            "not-json\n",
            encoding="utf-8",
        )

        report = run_live_probe(
            self.root
        )

        self.assertEqual(
            report.status,
            ProbeStatus.UNAVAILABLE,
        )
        self.assertGreater(
            report.counters[
                "checks_failed"
            ],
            0,
        )

    def test_missing_runtime_is_unavailable(
        self,
    ) -> None:
        missing = self.root / "missing"

        report = run_live_probe(
            missing
        )

        self.assertEqual(
            report.status,
            ProbeStatus.UNAVAILABLE,
        )
        self.assertFalse(
            missing.exists()
        )

    def test_probe_does_not_initialize_gateway(
        self,
    ) -> None:
        report = run_live_probe(
            self.root
        )

        self.assertFalse(
            report.safety[
                "gateway_instantiated"
            ]
        )
        self.assertFalse(
            report.safety["titan_loaded"]
        )
        self.assertFalse(
            report.safety[
                "retrieval_called"
            ]
        )
        self.assertFalse(
            report.safety[
                "adaptive_actions_applied"
            ]
        )


if __name__ == "__main__":
    unittest.main()
