from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory.data.paths import (
    MEMORY_PACKAGE_ROOT,
    resolve_default_runtime_root,
)


class DefaultRuntimeRootTests(unittest.TestCase):
    def test_explicit_environment_runtime_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(
                os.environ,
                {
                    "MEMORIX_RUNTIME_ROOT": temporary_directory,
                    "LOCALAPPDATA": "ignored-local-app-data",
                },
                clear=True,
            ):
                resolved = resolve_default_runtime_root()

        self.assertEqual(
            resolved,
            Path(temporary_directory).resolve(),
        )

    def test_local_app_data_is_used_on_windows_style_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(
                os.environ,
                {
                    "LOCALAPPDATA": temporary_directory,
                },
                clear=True,
            ):
                resolved = resolve_default_runtime_root()

        self.assertEqual(
            resolved,
            (
                Path(temporary_directory)
                / "memoriX"
                / "runtime"
            ).resolve(),
        )

    def test_xdg_data_home_is_used_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(
                os.environ,
                {
                    "XDG_DATA_HOME": temporary_directory,
                },
                clear=True,
            ):
                resolved = resolve_default_runtime_root()

        self.assertEqual(
            resolved,
            (
                Path(temporary_directory)
                / "memoriX"
                / "runtime"
            ).resolve(),
        )

    def test_default_runtime_is_outside_repository_memory_package(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            resolved = resolve_default_runtime_root()

        package_root = MEMORY_PACKAGE_ROOT.resolve()

        self.assertNotEqual(
            resolved,
            package_root / "runtime",
        )

        self.assertFalse(
            resolved == package_root
            or package_root in resolved.parents
        )

    def test_resolution_does_not_create_runtime_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            expected = (
                Path(temporary_directory)
                / "memoriX"
                / "runtime"
            )

            with patch.dict(
                os.environ,
                {
                    "LOCALAPPDATA": temporary_directory,
                },
                clear=True,
            ):
                resolved = resolve_default_runtime_root()

            self.assertEqual(resolved, expected.resolve())
            self.assertFalse(expected.exists())


if __name__ == "__main__":
    unittest.main()