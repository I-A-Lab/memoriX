from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from memory.release.path_safety import validate_destructive_runtime_path
from memory.release.runtime_archive import restore_runtime_backup, create_runtime_backup

class PathSafetyTests(unittest.TestCase):
    def test_rejects_project_runtime_for_destructive_operations(self):
        project=Path(__file__).resolve().parents[3]
        with self.assertRaises(ValueError):
            validate_destructive_runtime_path(project/'memory/runtime',project_root=project)

    def test_accepts_external_nested_runtime(self):
        with tempfile.TemporaryDirectory() as parent:
            target=Path(parent)/'memorix/runtime'
            self.assertEqual(validate_destructive_runtime_path(target),target.resolve())

    def test_restore_rejects_source_repository_destination(self):
        project=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as parent:
            source=Path(parent)/'source'; source.mkdir(); (source/'x.txt').write_text('x',encoding='utf-8')
            archive=Path(parent)/'backup.zip'; create_runtime_backup(source,archive)
            with self.assertRaises(ValueError):
                restore_runtime_backup(archive,project/'memory/runtime',overwrite=True)

if __name__ == '__main__': unittest.main()
