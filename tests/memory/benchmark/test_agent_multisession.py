from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.agent_multisession import (
    NoMemoryAgent,
    PersistentMemoryAgent,
    build_agent,
    run_agent_multisession_benchmark,
    validate_agent_report,
    write_agent_results,
)
from memory.benchmark.memory_pure_benchmark import DeterministicLexicalEngine


class AgentMultisessionTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        records = [
            {"record_id":"r1","content":"favorite color violet","canonical_fact":{"key":"favorite_color","value":"violet"},"active":True,"should_retrieve":True},
            {"record_id":"r2","content":"obsolete color green","canonical_fact":{"key":"favorite_color","value":"green"},"active":False,"should_retrieve":False},
        ]
        queries = [
            {"query_id":"q1","family":"user_profile","query":"favorite color violet","expected_record_ids":["r1"],"forbidden_record_ids":[],"expected_value":"violet"},
            {"query_id":"q2","family":"forget","query":"obsolete color green","expected_record_ids":[],"forbidden_record_ids":["r2"],"expected_value":None},
        ]
        for name, rows in (("records.jsonl", records), ("queries.jsonl", queries)):
            (root/name).write_text("".join(json.dumps(row)+"\n" for row in rows), encoding="utf-8")
        return root

    def test_no_memory_loses_cross_session_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            metrics, _ = run_agent_multisession_benchmark(self.fixture(Path(temp)), NoMemoryAgent())
            self.assertLess(metrics.task_success_rate, 1.0)
            self.assertEqual(metrics.forbidden_information_use_rate, 0.0)

    def test_persistent_lexical_reuses_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            agent = PersistentMemoryAgent(DeterministicLexicalEngine())
            metrics, _ = run_agent_multisession_benchmark(self.fixture(Path(temp)), agent)
            self.assertEqual(metrics.task_success_rate, 1.0)
            self.assertEqual(metrics.forbidden_information_use_rate, 0.0)

    def test_invalid_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_agent(mode="invalid", backend="lexical")

    def test_memorix_backend_requires_runtime(self) -> None:
        with self.assertRaises(ValueError):
            build_agent(mode="memorix_core", backend="memorix")

    def test_results_are_immutable_and_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); dataset=self.fixture(root/"dataset")
            metrics, rows=run_agent_multisession_benchmark(dataset, PersistentMemoryAgent(DeterministicLexicalEngine()))
            report=write_agent_results(root/"results", metrics, rows, mode="memorix_core", backend="lexical", dataset_id="fixture")
            payload=validate_agent_report(report)
            self.assertEqual(payload["suite"], "agent_multisession")
            with self.assertRaises(FileExistsError):
                write_agent_results(root/"results", metrics, rows, mode="memorix_core", backend="lexical", dataset_id="fixture")

    def test_invalid_top_k_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                run_agent_multisession_benchmark(self.fixture(Path(temp)), NoMemoryAgent(), top_k=0)


if __name__ == "__main__":
    unittest.main()
