
from __future__ import annotations
import tempfile
import unittest
from memory.adaptive import (
    MemoryTopicBlockStatus,
    create_memory_topic_block,
    inspect_memory_topic_block_registry,
    merge_memory_topic_blocks,
    plan_memory_topic_block_merge,
    plan_memory_topic_block_rebalance,
    route_memory_to_topic_block,
    update_memory_topic_block,
)

class DynamicTopicBlockMutationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_create_is_idempotent(self):
        first = create_memory_topic_block(self.tmp.name, canonical_topic="coding", aliases=("python",))
        second = create_memory_topic_block(self.tmp.name, canonical_topic="coding")
        self.assertTrue(first.block_created)
        self.assertFalse(second.block_created)
        self.assertEqual(first.target_block_id, second.target_block_id)

    def test_rename_alias_archive_restore(self):
        created = create_memory_topic_block(self.tmp.name, canonical_topic="travel")
        block_id = created.target_block_id
        renamed = update_memory_topic_block(self.tmp.name, block_id=block_id, action="rename", value="Trips")
        self.assertEqual(renamed.block.display_name, "Trips")
        aliased = update_memory_topic_block(self.tmp.name, block_id=block_id, action="add_alias", value="vacation")
        self.assertIn("vacation", aliased.block.aliases)
        archived = update_memory_topic_block(self.tmp.name, block_id=block_id, action="archive")
        self.assertEqual(archived.block.status, MemoryTopicBlockStatus.ARCHIVED)
        restored = update_memory_topic_block(self.tmp.name, block_id=block_id, action="restore")
        self.assertEqual(restored.block.status, MemoryTopicBlockStatus.ACTIVE)

    def test_route_assignment_is_idempotent(self):
        created = create_memory_topic_block(self.tmp.name, canonical_topic="music")
        first = route_memory_to_topic_block(self.tmp.name, item_id="memory-1", block_id=created.target_block_id)
        second = route_memory_to_topic_block(self.tmp.name, item_id="memory-1", block_id=created.target_block_id)
        self.assertTrue(first.memory_routed)
        self.assertEqual(first.assignment_id, second.assignment_id)

    def test_merge_preserves_source_history(self):
        source = create_memory_topic_block(self.tmp.name, canonical_topic="python")
        target = create_memory_topic_block(self.tmp.name, canonical_topic="coding")
        plan = plan_memory_topic_block_merge(self.tmp.name, source_block_id=source.target_block_id, target_block_id=target.target_block_id)
        self.assertTrue(plan.allowed)
        result = merge_memory_topic_blocks(self.tmp.name, source_block_id=source.target_block_id, target_block_id=target.target_block_id)
        self.assertTrue(result.block_merged)
        snapshot = inspect_memory_topic_block_registry(self.tmp.name)
        source_after = next(item for item in snapshot.blocks if item.block_id == source.target_block_id)
        self.assertEqual(source_after.status, MemoryTopicBlockStatus.MERGED)
        self.assertEqual(source_after.merged_into_block_id, target.target_block_id)

    def test_rebalance_is_dry_run(self):
        create_memory_topic_block(self.tmp.name, canonical_topic="general", set_as_default=True)
        plan = plan_memory_topic_block_rebalance(self.tmp.name)
        self.assertTrue(plan.dry_run)
        self.assertFalse(plan.registry_modified)
        self.assertFalse(plan.neural_model_loaded)

if __name__ == "__main__":
    unittest.main()
