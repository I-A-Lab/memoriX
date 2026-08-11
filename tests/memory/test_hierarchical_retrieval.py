from __future__ import annotations

import tempfile
import unittest

import torch

from memory.data import MemoryStoragePaths, RetrievalSource
from memory.gateway import MemoriXGateway
from memory.hot_site.short_term_memory import ShortTermEventStore


class HierarchicalRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = MemoryStoragePaths.from_runtime_root(self.tmp.name)
        torch.manual_seed(101)
        self.gateway = MemoriXGateway(
            storage_paths=self.paths,
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

    def record(
        self,
        event_id: str,
        content: str,
        *,
        project_id: str = "P1",
        user_id: str = "U1",
    ):
        return self.gateway.record_memory_event(
            event_id=event_id,
            content=content,
            event_type="retrieval_test",
            source="test",
            project_id=project_id,
            session_id="S1",
            metadata={"user_id": user_id},
        )

    def test_priority_stm_then_hot_then_cold(self) -> None:
        self.record("event-recent", "Priority value TOKEN-42.")
        candidate = self.gateway.propose_memory_candidate(
            content="Validated priority value TOKEN-42.",
            reason="priority",
            source_event_ids=("event-other",),
            metadata={"project_id": "P1", "user_id": "U1"},
        )
        memory = self.gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="reviewer",
            validation_reason="approved",
        )

        stm = self.gateway.retrieve_memory(
            "TOKEN-42", project_id="P1", user_id="U1"
        )
        self.assertEqual(stm.source, RetrievalSource.SHORT_TERM)
        self.assertEqual(stm.matches[0].memory_id, "event-recent")
        self.assertEqual(stm.matches[0].metadata["trust_level"], "recent_unvalidated")

        ShortTermEventStore(self.paths.short_term_events).clear()
        hot = self.gateway.retrieve_memory(
            "TOKEN-42", project_id="P1", user_id="U1"
        )
        self.assertEqual(hot.source, RetrievalSource.HOT_SITE)
        self.assertEqual(hot.matches[0].memory_id, memory.memory_id)

        self.gateway.forget_memory(
            memory.memory_id,
            validated_by="reviewer",
            reason="test cold fallback",
        )
        cold = self.gateway.retrieve_memory(
            "TOKEN-42", project_id="P1", user_id="U1"
        )
        self.assertEqual(cold.source, RetrievalSource.COLD_SITE)
        self.assertEqual(cold.matches[0].metadata["trust_level"], "historical_unvalidated")

    def test_scopes_apply_to_short_term_and_cold(self) -> None:
        self.record("a", "Scoped token SAME-TOKEN A.", project_id="P1", user_id="U1")
        self.record("b", "Scoped token SAME-TOKEN B.", project_id="P2", user_id="U2")

        stm = self.gateway.retrieve_memory(
            "SAME-TOKEN", project_id="P1", user_id="U1"
        )
        self.assertEqual(stm.source, RetrievalSource.SHORT_TERM)
        self.assertEqual({m.memory_id for m in stm.matches}, {"a"})

        ShortTermEventStore(self.paths.short_term_events).clear()
        cold = self.gateway.retrieve_memory(
            "SAME-TOKEN", project_id="P2", user_id="U2"
        )
        self.assertEqual(cold.source, RetrievalSource.COLD_SITE)
        self.assertEqual({m.memory_id for m in cold.matches}, {"b"})

    def test_candidate_source_event_is_not_reintroduced_from_cold(self) -> None:
        self.record("candidate-source", "Rejected fact REJECT-ME-55.")
        candidate = self.gateway.propose_memory_candidate(
            content="Rejected fact REJECT-ME-55.",
            reason="review",
            source_event_ids=("candidate-source",),
        )
        self.gateway.reject_memory_candidate(
            candidate.candidate_id,
            rejected_by="reviewer",
            rejection_reason="not trusted",
        )
        ShortTermEventStore(self.paths.short_term_events).clear()

        result = self.gateway.retrieve_memory("REJECT-ME-55")
        self.assertEqual(result.source, RetrievalSource.COLD_SITE)
        self.assertEqual(result.matches, ())

        audit = self.gateway.search_cold_site_history("REJECT-ME-55")
        self.assertEqual(audit.source, RetrievalSource.COLD_AUDIT)
        self.assertEqual(len(audit.matches), 1)


if __name__ == "__main__":
    unittest.main()
