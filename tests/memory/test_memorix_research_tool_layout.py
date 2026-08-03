from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = PROJECT_ROOT / "tools" / "memorix" / "research"
EXPECTED_RESEARCH_TOOLS = {
    "memorix_ablation_benchmark.py",
    "memorix_adaptive_design_benchmark.py",
    "memorix_adaptive_routing_benchmark.py",
    "memorix_agent_multisession_benchmark.py",
    "memorix_benchmark_contracts.py",
    "memorix_benchmark_manifest.py",
    "memorix_capacity_benchmark.py",
    "memorix_consolidation_benchmark.py",
    "memorix_dynamic_memory_benchmark.py",
    "memorix_generate_datasets.py",
    "memorix_generate_final_report.py",
    "memorix_load_robustness_benchmark.py",
    "memorix_memory_pressure_benchmark.py",
    "memorix_memory_pure_benchmark.py",
    "memorix_multiseed_orchestrator.py",
    "memorix_observability_benchmark.py",
    "memorix_opencode_real_campaign.py",
    "memorix_opencode_resilient_campaign.py",
    "memorix_policy_lifecycle_benchmark.py",
    "memorix_policy_search_benchmark.py",
    "memorix_reference_campaign.py",
    "memorix_retention_ranking_benchmark.py",
    "memorix_sdlc_benchmark.py",
    "memorix_system_benchmark.py",
    "memorix_topic_blocks_benchmark.py",
}

class MemoriXResearchToolLayoutTests(unittest.TestCase):
    def test_research_tools_have_moved_from_legacy_scripts_directory(self) -> None:
        actual = {path.name for path in RESEARCH_ROOT.glob("memorix_*.py")}
        self.assertEqual(actual, EXPECTED_RESEARCH_TOOLS)
        for name in EXPECTED_RESEARCH_TOOLS:
            self.assertFalse((PROJECT_ROOT / "scripts" / name).exists(), name)

    def test_repository_helper_finds_root_from_nested_tool(self) -> None:
        helper_path = PROJECT_ROOT / "tools" / "memorix" / "_repository.py"
        spec = importlib.util.spec_from_file_location("memorix_tool_repository", helper_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        detected = module.find_repository_root(RESEARCH_ROOT / "memorix_benchmark_contracts.py")
        self.assertEqual(detected, PROJECT_ROOT)

    def test_research_cli_runs_outside_repository_working_directory(self) -> None:
        script = RESEARCH_ROOT / "memorix_benchmark_contracts.py"
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run([sys.executable, str(script), "--compact"], cwd=directory, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("schema_version", payload)

if __name__ == "__main__":
    unittest.main()
