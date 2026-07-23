"""Canonical topic-block and assignment record normalization."""
from __future__ import annotations
from typing import Any, Mapping

TOPIC_SCHEMA_VERSION = 2


def normalize_topic_block_record(record: Mapping[str, Any]) -> dict[str, Any]:
    canonical = str(record.get("canonical_topic") or record.get("label") or "general")
    block_id = str(record.get("block_id") or record.get("topic_block_id") or "block_general")
    return {
        **dict(record),
        "schema_version": int(record.get("schema_version", TOPIC_SCHEMA_VERSION) or TOPIC_SCHEMA_VERSION),
        "block_id": block_id,
        "topic_block_id": block_id,
        "canonical_topic": canonical,
        "display_name": str(record.get("display_name") or record.get("label") or canonical),
        "memory_count": max(0, int(record.get("memory_count", record.get("used_items", 0)) or 0)),
        "protected_memory_count": max(0, int(record.get("protected_memory_count", 0) or 0)),
        "status": str(record.get("status") or "active"),
    }


def normalize_topic_assignment_record(record: Mapping[str, Any]) -> dict[str, Any]:
    block_id = str(
        record.get("topic_block_id")
        or record.get("target_block_id")
        or record.get("block_id")
        or "block_general"
    )
    item_id = str(record.get("item_id") or record.get("memory_id") or record.get("candidate_id") or "")
    return {
        **dict(record),
        "schema_version": int(record.get("schema_version", TOPIC_SCHEMA_VERSION) or TOPIC_SCHEMA_VERSION),
        "item_id": item_id,
        "memory_id": str(record.get("memory_id") or item_id),
        "block_id": block_id,
        "topic_block_id": block_id,
        "target_block_id": block_id,
    }
