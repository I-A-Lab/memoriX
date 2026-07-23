from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.diagnostics import (
    inspect_runtime_path,
)


class RuntimeFileInspectionTests(
    unittest.TestCase
):
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

    def test_missing_path_is_reported(
        self,
    ) -> None:
        observation = inspect_runtime_path(
            "missing",
            self.root / "missing.jsonl",
        )

        self.assertFalse(observation.exists)
        self.assertIsNone(observation.error)

    def test_valid_jsonl_is_counted(
        self,
    ) -> None:
        path = self.root / "events.jsonl"

        path.write_text(
            "\n".join(
                (
                    json.dumps({"id": 1}),
                    json.dumps({"id": 2}),
                    "",
                )
            ),
            encoding="utf-8",
        )

        observation = inspect_runtime_path(
            "events",
            path,
        )

        self.assertTrue(observation.exists)
        self.assertTrue(
            observation.valid_jsonl
        )
        self.assertEqual(
            observation.record_count,
            2,
        )
        self.assertIsNone(observation.error)

    def test_invalid_jsonl_is_reported(
        self,
    ) -> None:
        path = self.root / "events.jsonl"

        path.write_text(
            '{"id": 1}\nnot-json\n',
            encoding="utf-8",
        )

        observation = inspect_runtime_path(
            "events",
            path,
        )

        self.assertFalse(
            observation.valid_jsonl
        )
        self.assertIsNotNone(
            observation.error
        )

    def test_json_list_is_counted(
        self,
    ) -> None:
        path = self.root / "memories.json"

        path.write_text(
            json.dumps(
                [
                    {"id": 1},
                    {"id": 2},
                    {"id": 3},
                ]
            ),
            encoding="utf-8",
        )

        observation = inspect_runtime_path(
            "memories",
            path,
        )

        self.assertTrue(
            observation.valid_json
        )
        self.assertEqual(
            observation.record_count,
            3,
        )

    def test_directory_is_not_modified(
        self,
    ) -> None:
        directory = self.root / "cold"
        directory.mkdir()
        before = directory.stat().st_mtime_ns

        observation = inspect_runtime_path(
            "cold_root",
            directory,
        )

        after = directory.stat().st_mtime_ns

        self.assertTrue(
            observation.is_directory
        )
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
