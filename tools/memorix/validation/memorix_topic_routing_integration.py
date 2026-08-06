"""Validate controlled topic metadata on human-approved hot memories."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="memorix-topic-routing-"
    ) as root:
        gateway = MemoriXGateway(
            storage_paths=(
                MemoryStoragePaths.from_runtime_root(
                    root
                )
            ),
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

        candidate = (
            gateway.propose_memory_candidate(
                content=(
                    "Astronomy astronomy telescope "
                    "stars planets."
                ),
                reason=(
                    "Controlled topic-routing "
                    "integration."
                ),
                source_event_ids=(
                    "event_topic_integration",
                ),
                importance=0.9,
                confidence=1.0,
                surprise=0.5,
                metadata={
                    "subject": (
                        "Astronomy observations"
                    ),
                    "tags": [
                        "astronomy",
                        "space",
                    ],
                },
            )
        )

        pending_has_routing = (
            "adaptive" in candidate.metadata
        )

        memory = (
            gateway.validate_memory_candidate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved integration test."
                ),
            )
        )

        topic_block = (
            memory.metadata
            .get("adaptive", {})
            .get("topic_block")
        )

        retrieval = gateway.retrieve_memory(
            "Astronomy telescope stars"
        )

        result = {
            "pending_candidate_had_routing": (
                pending_has_routing
            ),
            "validated_memory_id": (
                memory.memory_id
            ),
            "topic_block": topic_block,
            "retrieval_source": (
                retrieval.source
            ),
            "retrieval_count": len(
                retrieval.matches
            ),
            "cold_fallback_used": False,
            "physical_partitioning": (
                topic_block.get(
                    "physical_partitioning"
                )
                if isinstance(
                    topic_block,
                    dict,
                )
                else None
            ),
            "retrieval_behavior_changed": (
                topic_block.get(
                    "retrieval_behavior_changed"
                )
                if isinstance(
                    topic_block,
                    dict,
                )
                else None
            ),
        }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        if pending_has_routing:
            return 1

        if not isinstance(topic_block, dict):
            return 2

        if retrieval.source != "hot_site":
            return 3

        if topic_block.get(
            "physical_partitioning"
        ):
            return 4

        if topic_block.get(
            "retrieval_behavior_changed"
        ):
            return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
