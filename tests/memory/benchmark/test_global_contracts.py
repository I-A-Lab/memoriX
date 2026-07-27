from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.global_contracts import (
    BENCHMARK_ID,
    BenchmarkMode,
    BenchmarkSize,
    load_benchmark_contracts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOT = (
    PROJECT_ROOT
    / "benchmarks"
    / "memorix_vs_no_memory"
    / "configs"
)


class GlobalBenchmarkContractTests(unittest.TestCase):
    def test_repository_contracts_are_valid(self) -> None:
        contracts = load_benchmark_contracts(CONFIG_ROOT)

        self.assertEqual(
            {item.mode for item in contracts.modes},
            set(BenchmarkMode),
        )
        self.assertEqual(
            {item.size for item in contracts.sizes},
            set(BenchmarkSize),
        )
        self.assertEqual(
            contracts.to_dict()["benchmark_id"],
            BENCHMARK_ID,
        )

    def test_no_memory_contract_is_strictly_memory_free(self) -> None:
        contracts = load_benchmark_contracts(CONFIG_ROOT)
        no_memory = next(
            item
            for item in contracts.modes
            if item.mode is BenchmarkMode.NO_MEMORY
        )

        enabled_flags = {
            name
            for name, value in no_memory.to_dict().items()
            if name != "mode" and value is True
        }
        self.assertEqual(enabled_flags, set())

    def test_core_and_full_are_distinct_ablation_modes(self) -> None:
        contracts = load_benchmark_contracts(CONFIG_ROOT)
        by_mode = {item.mode: item for item in contracts.modes}
        core = by_mode[BenchmarkMode.MEMORIX_CORE]
        full = by_mode[BenchmarkMode.MEMORIX_FULL]

        self.assertFalse(core.consolidation_enabled)
        self.assertFalse(core.adaptive_routing_enabled)
        self.assertFalse(core.active_policy_enabled)
        self.assertTrue(full.consolidation_enabled)
        self.assertTrue(full.adaptive_routing_enabled)
        self.assertTrue(full.active_policy_enabled)

    def test_extreme_profile_never_runs_automatically(self) -> None:
        contracts = load_benchmark_contracts(CONFIG_ROOT)
        extreme = next(
            item
            for item in contracts.sizes
            if item.size is BenchmarkSize.EXTREME
        )
        self.assertFalse(extreme.automatic)

    def test_invalid_no_memory_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            for filename in ("configurations.json", "metrics.json", "sizes.json"):
                payload = json.loads(
                    (CONFIG_ROOT / filename).read_text(encoding="utf-8")
                )
                if filename == "configurations.json":
                    payload["modes"][0]["memory_tools_exposed"] = True
                (temp_root / filename).write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )

            with self.assertRaisesRegex(
                ValueError,
                "no_memory enables forbidden features",
            ):
                load_benchmark_contracts(temp_root)


if __name__ == "__main__":
    unittest.main()
