from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from memory.adaptive import (
    MemoryConsolidationAction,
    MemoryConsolidationCandidate,
    MemoryConsolidationCategory,
    audit_memory_consolidation,
    classify_memory_consolidation_pair,
    collect_memory_consolidation_candidates,
    detect_memory_consolidation_groups,
    plan_memory_consolidation,
)
from memory.data import MemoryStoragePaths


class ConsolidationPlanningTests(unittest.TestCase):
    def candidate(self, memory_id: str, content: str, **metadata):
        return MemoryConsolidationCandidate(
            memory_id=memory_id,
            content=content,
            active=True,
            created_at=None,
            validated_at=None,
            topic_block_id=metadata.pop("topic_block_id", None),
            tags=tuple(metadata.pop("tags", ())),
            source=None,
            project_id=metadata.pop("project_id", None),
            session_id=None,
            supersedes_memory_id=metadata.pop("supersedes_memory_id", None),
            protected=metadata.pop("protected", False),
            metadata=metadata,
        )

    def test_audit_is_read_only(self):
        audit = audit_memory_consolidation()
        self.assertTrue(audit.dry_run)
        self.assertFalse(audit.runtime_modified)
        self.assertFalse(audit.cold_site_accessed)
        self.assertFalse(audit.neural_model_loaded)

    def test_collection_missing_runtime_does_not_create_it(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "missing"
            report = collect_memory_consolidation_candidates(root)
            self.assertEqual(report.candidates, ())
            self.assertFalse(root.exists())

    def test_collection_uses_latest_record_and_limit(self):
        with TemporaryDirectory() as directory:
            paths = MemoryStoragePaths.from_runtime_root(directory)
            paths.titan_metadata.parent.mkdir(parents=True)
            records = [
                {"memory_id":"m1","content":"old","active":True,"metadata":{}},
                {"memory_id":"m1","content":"new","active":True,"metadata":{"tags":["x"]}},
                {"memory_id":"m2","content":"second","active":True,"metadata":{}},
            ]
            paths.titan_metadata.write_text("".join(json.dumps(x)+"\n" for x in records),encoding="utf-8")
            report = collect_memory_consolidation_candidates(directory, assessment_limit=1)
            self.assertEqual(report.candidates[0].content, "new")
            self.assertTrue(report.truncated)
            self.assertEqual(report.unique_memories_seen, 2)

    def test_collection_filters_topic_and_counts_malformed(self):
        with TemporaryDirectory() as directory:
            paths = MemoryStoragePaths.from_runtime_root(directory)
            paths.titan_metadata.parent.mkdir(parents=True)
            paths.titan_metadata.write_text('{bad}\n'+json.dumps({"memory_id":"m1","content":"x","metadata":{"topic_block_id":"coding"}})+"\n",encoding="utf-8")
            report = collect_memory_consolidation_candidates(directory, topic_block_id="coding")
            self.assertEqual(len(report.candidates), 1)
            self.assertEqual(report.malformed_record_count, 1)

    def test_exact_duplicate(self):
        category, score = classify_memory_consolidation_pair(self.candidate("a","Elwen lives in Brest"), self.candidate("b","  elwen lives in brest "))
        self.assertIs(category, MemoryConsolidationCategory.EXACT_DUPLICATE)
        self.assertEqual(score, 1.0)

    def test_compatible_update_from_supersedes(self):
        category, _ = classify_memory_consolidation_pair(self.candidate("a","Old value"), self.candidate("b","New value", supersedes_memory_id="a"))
        self.assertIs(category, MemoryConsolidationCategory.COMPATIBLE_UPDATE)

    def test_near_duplicate(self):
        first = self.candidate("a","python password generator project", tags=("coding",))
        second = self.candidate("b","python password generator project tool", tags=("coding",))
        category, _ = classify_memory_consolidation_pair(first, second)
        self.assertIs(category, MemoryConsolidationCategory.NEAR_DUPLICATE)

    def test_independent(self):
        category, _ = classify_memory_consolidation_pair(self.candidate("a","Alan Walker music"), self.candidate("b","Python database architecture"))
        self.assertIs(category, MemoryConsolidationCategory.INDEPENDENT_MEMORIES)

    def test_groups_are_non_overlapping(self):
        candidates = (self.candidate("a","same text"), self.candidate("b","same text"), self.candidate("c","other subject"))
        groups = detect_memory_consolidation_groups(candidates)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].memory_ids, ("a","b"))

    def test_protected_group_requires_review(self):
        groups = detect_memory_consolidation_groups((self.candidate("a","same", protected=True), self.candidate("b","same")))
        self.assertIs(groups[0].recommended_action, MemoryConsolidationAction.REQUEST_MANUAL_REVIEW)

    def test_plan_is_dry_run(self):
        with TemporaryDirectory() as directory:
            paths = MemoryStoragePaths.from_runtime_root(directory)
            paths.titan_metadata.parent.mkdir(parents=True)
            paths.titan_metadata.write_text(json.dumps({"memory_id":"a","content":"same","metadata":{}})+"\n"+json.dumps({"memory_id":"b","content":"same","metadata":{}})+"\n",encoding="utf-8")
            collection = collect_memory_consolidation_candidates(directory)
            plan = plan_memory_consolidation(collection, plan_id="p1")
            self.assertTrue(plan.requires_human_review)
            self.assertFalse(plan.consolidation_executed)
            self.assertFalse(plan.hot_site_modified)
            self.assertFalse(plan.cold_site_modified)

    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            detect_memory_consolidation_groups((), maximum_groups=0)


if __name__ == "__main__":
    unittest.main()
