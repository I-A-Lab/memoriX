from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from memory.adaptive import (
    MemoryTopicBlock,
    MemoryTopicBlockStatus,
    MemoryTopicRoutingAction,
    audit_dynamic_topic_blocks,
    detect_memory_topic,
    inspect_memory_topic_block_registry,
    plan_memory_topic_routing,
)


class DynamicTopicBlocksTests(unittest.TestCase):
    def test_audit_reuses_existing_components(self) -> None:
        result = audit_dynamic_topic_blocks()
        self.assertTrue(result.logical_routing_present)
        self.assertFalse(result.versioned_registry_present)
        self.assertTrue(result.dry_run)

    def test_block_validation(self) -> None:
        block = MemoryTopicBlock(block_id="block_coding", canonical_topic="coding", display_name="Coding")
        block.validate()
        self.assertEqual(block.normalized_terms(), ("coding",))

    def test_missing_registry_does_not_create_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "missing"
            result = inspect_memory_topic_block_registry(root)
            self.assertFalse(result.registry_exists)
            self.assertFalse(root.exists())

    def test_versioned_registry_is_inspected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "topic_blocks"
            folder.mkdir()
            (folder / "topic_blocks.jsonl").write_text(json.dumps({"block_id": "block_coding", "canonical_topic": "coding", "display_name": "Coding", "status": "active"}) + "\n", encoding="utf-8")
            (folder / "topic_block_state.json").write_text(json.dumps({"active_block_ids": ["block_coding"]}), encoding="utf-8")
            result = inspect_memory_topic_block_registry(root)
            self.assertEqual(result.blocks[0].block_id, "block_coding")
            self.assertEqual(result.active_block_ids, ("block_coding",))
            self.assertFalse(result.registry_modified)

    def test_legacy_registry_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "topic_blocks.json").write_text(json.dumps({"schema_version": 1, "blocks": [{"block_id": "block_music", "label": "music", "used_items": 2}]}), encoding="utf-8")
            result = inspect_memory_topic_block_registry(root)
            self.assertTrue(result.legacy_registry_used)
            self.assertEqual(result.blocks[0].memory_count, 2)

    def test_explicit_topic_is_deterministic(self) -> None:
        result = detect_memory_topic("anything", explicit_topic="Python Development")
        self.assertEqual(result.canonical_topic, "pythondevelopment")
        self.assertEqual(result.confidence, 1.0)

    def test_empty_content_falls_back_to_general(self) -> None:
        result = detect_memory_topic("")
        self.assertEqual(result.canonical_topic, "general")
        self.assertTrue(result.fallback_used)

    def test_existing_alias_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = inspect_memory_topic_block_registry(directory)
            block = MemoryTopicBlock(block_id="block_coding", canonical_topic="coding", display_name="Coding", aliases=("python",))
            snapshot = replace(snapshot, blocks=(block,), active_block_ids=(block.block_id,))
            plan = plan_memory_topic_routing(item_id="m1", content="", explicit_topic="python", registry=snapshot)
            self.assertEqual(plan.action, MemoryTopicRoutingAction.USE_EXISTING_BLOCK)
            self.assertTrue(plan.routing_allowed)

    def test_high_confidence_topic_proposes_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = inspect_memory_topic_block_registry(directory)
            plan = plan_memory_topic_routing(item_id="m1", content="", explicit_topic="astronomy", registry=snapshot)
            self.assertEqual(plan.action, MemoryTopicRoutingAction.CREATE_NEW_BLOCK)
            self.assertTrue(plan.block_creation_required)
            self.assertFalse(plan.registry_modified)

    def test_low_confidence_uses_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = inspect_memory_topic_block_registry(directory)
            general = MemoryTopicBlock(block_id="block_general", canonical_topic="general", display_name="General")
            snapshot = replace(snapshot, blocks=(general,), active_block_ids=(general.block_id,), default_block_id=general.block_id)
            plan = plan_memory_topic_routing(item_id="m1", content="", registry=snapshot)
            self.assertEqual(plan.action, MemoryTopicRoutingAction.ROUTE_TO_DEFAULT)
            self.assertTrue(plan.routing_allowed)

    def test_low_confidence_without_default_requests_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = inspect_memory_topic_block_registry(directory)
            plan = plan_memory_topic_routing(item_id="m1", content="", registry=snapshot)
            self.assertEqual(plan.action, MemoryTopicRoutingAction.REQUEST_MANUAL_REVIEW)
            self.assertFalse(plan.routing_allowed)

    def test_plan_guarantees_no_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = inspect_memory_topic_block_registry(directory)
            plan = plan_memory_topic_routing(item_id="m1", content="", explicit_topic="coding", registry=snapshot)
            self.assertTrue(plan.dry_run)
            self.assertFalse(plan.block_created)
            self.assertFalse(plan.memory_routed)
            self.assertFalse(plan.runtime_modified)
            self.assertFalse(plan.cold_site_accessed)
            self.assertFalse(plan.neural_model_loaded)


if __name__ == "__main__":
    unittest.main()
