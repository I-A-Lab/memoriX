from __future__ import annotations

import importlib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PythonMemoryPackageContractTests(unittest.TestCase):
    """Validate the current memoriX package and architecture contract."""

    def test_operational_packages_are_importable(self) -> None:
        modules = (
            "memory",
            "memory.adaptive",
            "memory.benchmark",
            "memory.cold_site",
            "memory.cold_site.long_term_store",
            "memory.cold_site.project_archive",
            "memory.consolidation",
            "memory.data",
            "memory.diagnostics",
            "memory.gateway",
            "memory.hot_site",
            "memory.hot_site.short_term_memory",
            "memory.hot_site.titan_active_memory",
            "memory.integrations",
            "memory.integrations.mcp",
            "memory.release",
            "memory.sync",
        )

        for module_name in modules:
            with self.subTest(module=module_name):
                imported_module = importlib.import_module(module_name)
                self.assertIsNotNone(imported_module)

    def test_titan_has_one_canonical_implementation(self) -> None:
        canonical = (
            PROJECT_ROOT
            / "memory"
            / "hot_site"
            / "titan_active_memory"
            / "titan_model.py"
        )
        obsolete_root_copy = PROJECT_ROOT / "memory" / "titan_model.py"

        self.assertTrue(canonical.is_file())
        self.assertFalse(obsolete_root_copy.exists())

    def test_architecture_contract_is_documented(self) -> None:
        architecture = PROJECT_ROOT / "memory" / "ARCHITECTURE.md"
        self.assertTrue(architecture.is_file())

        content = architecture.read_text(encoding="utf-8")

        required_phrases = (
            "short-term events are archived directly in the cold site",
            "validated candidates are stored in the hot site only",
            "normal retrieval uses a recency-first hierarchy: Short-Term Memory first, then Hot Site, then Cold Site as a final fallback",
            "normal retrieval falls back to Cold Site only after Short-Term Memory and Hot Site miss",
            "there is no automatic cold-to-hot rehydration",
            "Observability reports, snapshots, alerts and drift analysis",
        )

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, content)


if __name__ == "__main__":
    unittest.main()
