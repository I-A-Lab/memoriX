from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = PROJECT_ROOT / "tools" / "memorix"
RUNTIME_ROOT = TOOLS_ROOT / "runtime"
OPERATIONS_ROOT = TOOLS_ROOT / "operations"

EXPECTED_RUNTIME_TOOLS = {
    "memorix_mcp_server.py",
    "start_opencode_with_memorix.ps1",
    "start_memorix.ps1",
}

EXPECTED_OPERATION_TOOLS = {
    "install_memorix_nightly_task.ps1",
    "install_memorix_opencode_command.ps1",
    "install_memorix_command.ps1",
    "memorix_nightly.py",
    "memorix_runtime_backup.py",
    "memorix_runtime_restore.py",
    "remove_memorix_nightly_task.ps1",
    "remove_memorix_opencode_command.ps1",
    "remove_memorix_command.ps1",
    "run_memorix_nightly.ps1",
}


class MemoriXRuntimeOperationsToolLayoutTests(unittest.TestCase):
    def test_tools_have_moved_from_legacy_scripts_directory(self) -> None:
        runtime = {
            path.name
            for path in RUNTIME_ROOT.iterdir()
            if path.is_file() and path.name != "README.md"
        }
        operations = {
            path.name
            for path in OPERATIONS_ROOT.iterdir()
            if path.is_file() and path.name != "README.md"
        }
        self.assertEqual(runtime, EXPECTED_RUNTIME_TOOLS)
        self.assertEqual(operations, EXPECTED_OPERATION_TOOLS)
        self.assertFalse((PROJECT_ROOT / "scripts").exists())

    def test_repository_helper_finds_root_from_runtime_and_operations(self) -> None:
        helper_path = TOOLS_ROOT / "_repository.py"
        spec = importlib.util.spec_from_file_location(
            "memorix_tool_repository", helper_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.find_repository_root(RUNTIME_ROOT / "memorix_mcp_server.py"),
            PROJECT_ROOT,
        )
        self.assertEqual(
            module.find_repository_root(OPERATIONS_ROOT / "memorix_nightly.py"),
            PROJECT_ROOT,
        )

    def test_operations_cli_runs_outside_repository_working_directory(self) -> None:
        script = OPERATIONS_ROOT / "memorix_nightly.py"
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--runtime-root", completed.stdout)

    def test_internal_bindings_use_new_runtime_paths(self) -> None:
        client = (
            PROJECT_ROOT / "packages" / "opencode" / "src" / "memorix" / "client.ts"
        ).read_text(encoding="utf-8-sig")
        readiness = (PROJECT_ROOT / "memory" / "release" / "readiness.py").read_text(
            encoding="utf-8-sig"
        )
        verifier = (TOOLS_ROOT / "validation" / "verify_memorix.ps1").read_text(
            encoding="utf-8-sig"
        )
        launcher = (RUNTIME_ROOT / "start_opencode_with_memorix.ps1").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn(
            'path.join(projectRoot, "tools", "memorix", "runtime", "memorix_mcp_server.py")',
            client,
        )
        self.assertIn("tools/memorix/runtime/start_opencode_with_memorix.ps1", readiness)
        self.assertIn(r"tools\memorix\runtime\start_opencode_with_memorix.ps1", verifier)
        self.assertIn(r"tools\memorix\runtime\memorix_mcp_server.py", launcher)
        legacy_root = "scr" + "ipts"
        legacy_paths = (
            legacy_root + "/memorix_mcp_server.py",
            legacy_root + r"\memorix_mcp_server.py",
            legacy_root + "/start_opencode_with_memorix.ps1",
            legacy_root + r"\start_opencode_with_memorix.ps1",
        )
        for source in (client, readiness, verifier, launcher):
            for legacy_path in legacy_paths:
                self.assertNotIn(legacy_path, source)


if __name__ == "__main__":
    unittest.main()
