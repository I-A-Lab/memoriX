from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from memory.release import (
    create_runtime_backup,
    inspect_runtime_backup,
    restore_runtime_backup,
)


class RuntimeArchiveTests(unittest.TestCase):
    def test_backup_and_restore_preserve_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            (runtime / "short_term").mkdir(parents=True)
            (runtime / "short_term/events.jsonl").write_text(
                '{"event_id":"one"}\n', encoding="utf-8"
            )
            (runtime / "hot_site").mkdir()
            (runtime / "hot_site/titan_memory.pt").write_bytes(b"titan")
            archive = root / "backup.zip"
            manifest = create_runtime_backup(runtime, archive)
            inspected = inspect_runtime_backup(archive)
            restored = root / "restored"
            restore_runtime_backup(archive, restored)
            self.assertEqual(manifest, inspected)
            self.assertEqual(manifest.file_count, 2)
            self.assertEqual(
                (restored / "short_term/events.jsonl").read_text(encoding="utf-8"),
                '{"event_id":"one"}\n',
            )
            self.assertEqual(
                (restored / "hot_site/titan_memory.pt").read_bytes(),
                b"titan",
            )

    def test_restore_refuses_non_empty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            runtime.mkdir()
            (runtime / "state.json").write_text("{}", encoding="utf-8")
            archive = root / "backup.zip"
            create_runtime_backup(runtime, archive)
            destination = root / "destination"
            destination.mkdir()
            (destination / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                restore_runtime_backup(archive, destination)

    def test_inspection_rejects_unsafe_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as stream:
                stream.writestr("../escape.txt", "bad")
                stream.writestr("memorix-runtime-manifest.json", "{}")
            with self.assertRaises(ValueError):
                inspect_runtime_backup(archive)
