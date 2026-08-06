from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = PROJECT_ROOT / "tools" / "memorix"
DIAGNOSTICS_ROOT = TOOLS_ROOT / "diagnostics"
VALIDATION_ROOT = TOOLS_ROOT / "validation"

EXPECTED_DIAGNOSTIC_TOOLS = {
    "memorix_adaptive_controller_dry_run.py",
    "memorix_adaptive_routing.py",
    "memorix_capacity_dry_run.py",
    "memorix_capacity_status.py",
    "memorix_memory_pressure.py",
    "memorix_policy_search.py",
    "memorix_pressure_observation.py",
    "memorix_pruning_dry_run.py",
    "memorix_retention_ranking.py",
    "memorix_retrieval_diagnostic.py",
    "memorix_tenant_contradiction_audit.py",
    "memorix_topic_blocks_observation.py",
}

EXPECTED_VALIDATION_TOOLS = {
    "memorix_demo_smoke.py",
    "memorix_live_probe.py",
    "memorix_release_readiness.py",
    "memorix_topic_routing_integration.py",
    "verify_memorix.ps1",
}


class MemoriXDiagnosticValidationToolLayoutTests(unittest.TestCase):
    def test_tools_have_moved_from_legacy_scripts_directory(self) -> None:
        diagnostics = {path.name for path in DIAGNOSTICS_ROOT.glob("memorix_*.py")}
        validations = {path.name for path in VALIDATION_ROOT.iterdir() if path.is_file() and path.name != "README.md"}
        self.assertEqual(diagnostics, EXPECTED_DIAGNOSTIC_TOOLS)
        self.assertEqual(validations, EXPECTED_VALIDATION_TOOLS)
        for name in EXPECTED_DIAGNOSTIC_TOOLS | EXPECTED_VALIDATION_TOOLS:
            self.assertFalse((PROJECT_ROOT / "scripts" / name).exists(), name)

    def test_repository_helper_finds_root_from_both_nested_groups(self) -> None:
        helper_path = TOOLS_ROOT / "_repository.py"
        spec = importlib.util.spec_from_file_location("memorix_tool_repository", helper_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.find_repository_root(DIAGNOSTICS_ROOT / "memorix_capacity_status.py"), PROJECT_ROOT)
        self.assertEqual(module.find_repository_root(VALIDATION_ROOT / "memorix_live_probe.py"), PROJECT_ROOT)

    def test_diagnostic_cli_runs_outside_repository_working_directory(self) -> None:
        script = DIAGNOSTICS_ROOT / "memorix_capacity_status.py"
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run([sys.executable, str(script), "--help"], cwd=directory, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--simulate-active-items", completed.stdout)

    def test_validation_cli_runs_outside_repository_working_directory(self) -> None:
        script = VALIDATION_ROOT / "memorix_release_readiness.py"
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run([sys.executable, str(script), "--help"], cwd=directory, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--project-root", completed.stdout)


if __name__ == "__main__":
    unittest.main()
