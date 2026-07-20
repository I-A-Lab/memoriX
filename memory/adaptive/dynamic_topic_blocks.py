"""Read-only planning for dynamic topic blocks.

Part 25.1-25.5 audits the existing observation-only routing, models versioned
logical blocks, inspects optional registries without creating them, detects a
canonical topic deterministically, and returns a dry-run routing plan. It does
not create blocks, route memories, merge blocks, mutate the runtime, access the
cold site, or load Titan.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from memory.adaptive.topic_blocks import (
    build_topic_block_id,
    calculate_routing_confidence,
    extract_topic_terms,
    normalize_topic_term,
    select_topic_label,
)


class MemoryTopicBlockStatus(str, Enum):
    ACTIVE = "active"
    OVERLOADED = "overloaded"
    MERGING = "merging"
    MERGED = "merged"
    ARCHIVED = "archived"
    PROTECTED = "protected"


class MemoryTopicRoutingAction(str, Enum):
    USE_EXISTING_BLOCK = "use_existing_block"
    CREATE_NEW_BLOCK = "create_new_block"
    ROUTE_TO_DEFAULT = "route_to_default"
    REQUEST_MANUAL_REVIEW = "request_manual_review"


@dataclass(frozen=True, slots=True)
class MemoryTopicBlockLifecycleAudit:
    existing_observation_module: str
    existing_registry_module: str
    existing_routing_module: str
    logical_routing_present: bool
    versioned_registry_present: bool
    mutation_operations_present: bool
    observations: tuple[str, ...]
    dry_run: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryTopicBlock:
    block_id: str
    canonical_topic: str
    display_name: str
    aliases: tuple[str, ...] = ()
    status: MemoryTopicBlockStatus = MemoryTopicBlockStatus.ACTIVE
    memory_count: int = 0
    protected_memory_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    parent_block_id: str | None = None
    merged_into_block_id: str | None = None

    def validate(self) -> None:
        if not self.block_id.strip():
            raise ValueError("block_id must be non-empty.")
        if not normalize_topic_term(self.canonical_topic):
            raise ValueError("canonical_topic must be non-empty after normalization.")
        if self.memory_count < 0 or self.protected_memory_count < 0:
            raise ValueError("memory counts must be non-negative.")
        if self.protected_memory_count > self.memory_count:
            raise ValueError("protected_memory_count cannot exceed memory_count.")
        if self.status is MemoryTopicBlockStatus.MERGED and not self.merged_into_block_id:
            raise ValueError("merged blocks require merged_into_block_id.")

    def normalized_terms(self) -> tuple[str, ...]:
        values = (self.canonical_topic, self.display_name, *self.aliases)
        return tuple(sorted({term for value in values if (term := normalize_topic_term(value))}))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["aliases"] = list(self.aliases)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MemoryTopicBlock":
        aliases_value = payload.get("aliases", ())
        aliases = tuple(str(item) for item in aliases_value) if isinstance(aliases_value, Sequence) and not isinstance(aliases_value, (str, bytes, bytearray)) else ()
        status_value = str(payload.get("status", "active"))
        try:
            status = MemoryTopicBlockStatus(status_value)
        except ValueError:
            status = MemoryTopicBlockStatus.ACTIVE
        canonical = str(payload.get("canonical_topic", payload.get("label", "general")))
        result = cls(
            block_id=str(payload.get("block_id", build_topic_block_id(canonical))),
            canonical_topic=canonical,
            display_name=str(payload.get("display_name", payload.get("label", canonical))),
            aliases=aliases,
            status=status,
            memory_count=max(0, int(payload.get("memory_count", payload.get("used_items", 0)) or 0)),
            protected_memory_count=max(0, int(payload.get("protected_memory_count", 0) or 0)),
            created_at=None if payload.get("created_at") is None else str(payload.get("created_at")),
            updated_at=None if payload.get("updated_at") is None else str(payload.get("updated_at")),
            parent_block_id=None if payload.get("parent_block_id") is None else str(payload.get("parent_block_id")),
            merged_into_block_id=None if payload.get("merged_into_block_id") is None else str(payload.get("merged_into_block_id")),
        )
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class MemoryTopicBlockRegistrySnapshot:
    runtime_root: str
    versions_path: str
    state_path: str
    legacy_registry_path: str
    blocks: tuple[MemoryTopicBlock, ...]
    active_block_ids: tuple[str, ...]
    default_block_id: str | None
    overloaded_block_ids: tuple[str, ...]
    archived_block_ids: tuple[str, ...]
    malformed_record_count: int
    registry_exists: bool
    legacy_registry_used: bool
    observation_only: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "blocks": [block.to_dict() for block in self.blocks],
            "active_block_ids": list(self.active_block_ids),
            "overloaded_block_ids": list(self.overloaded_block_ids),
            "archived_block_ids": list(self.archived_block_ids),
        }


@dataclass(frozen=True, slots=True)
class MemoryTopicDetection:
    canonical_topic: str
    confidence: float
    matched_signals: tuple[str, ...]
    alternative_topics: tuple[str, ...]
    fallback_used: bool
    explicit_topic_used: bool
    dry_run: bool = True
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryTopicRoutingPlan:
    plan_id: str
    item_id: str
    action: MemoryTopicRoutingAction
    target_block_id: str | None
    target_topic: str
    block_creation_required: bool
    routing_allowed: bool
    confidence: float
    reasons: tuple[str, ...]
    alternative_block_ids: tuple[str, ...]
    operations: tuple[str, ...]
    dry_run: bool = True
    block_created: bool = False
    block_updated: bool = False
    memory_routed: bool = False
    block_merged: bool = False
    block_archived: bool = False
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


def audit_dynamic_topic_blocks() -> MemoryTopicBlockLifecycleAudit:
    return MemoryTopicBlockLifecycleAudit(
        existing_observation_module="memory.adaptive.topic_blocks",
        existing_registry_module="memory.adaptive.block_registry",
        existing_routing_module="memory.adaptive.routing",
        logical_routing_present=True,
        versioned_registry_present=False,
        mutation_operations_present=False,
        observations=(
            "existing_topic_blocks_are_observation_only",
            "existing_labels_are_inferred_without_fixed_business_domains",
            "existing_routing_is_metadata_only",
            "legacy_registry_is_single_json_not_versioned_jsonl",
            "part_25_reuses_existing_term_normalization_and_block_ids",
        ),
    )


def inspect_memory_topic_block_registry(runtime_root: str | Path) -> MemoryTopicBlockRegistrySnapshot:
    root = Path(runtime_root).expanduser().resolve()
    directory = root / "topic_blocks"
    versions_path = directory / "topic_blocks.jsonl"
    state_path = directory / "topic_block_state.json"
    legacy_path = root / "topic_blocks.json"
    blocks: list[MemoryTopicBlock] = []
    malformed = 0
    legacy_used = False

    if versions_path.is_file():
        for line in versions_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, Mapping):
                    raise ValueError("topic block record must be an object")
                blocks.append(MemoryTopicBlock.from_dict(payload))
            except (json.JSONDecodeError, TypeError, ValueError):
                malformed += 1
    elif legacy_path.is_file():
        legacy_used = True
        try:
            payload = json.loads(legacy_path.read_text(encoding="utf-8"))
            records = payload.get("blocks", []) if isinstance(payload, Mapping) else []
            if not isinstance(records, list):
                records = []
                malformed += 1
            for record in records:
                try:
                    if not isinstance(record, Mapping):
                        raise ValueError("legacy block record must be an object")
                    blocks.append(MemoryTopicBlock.from_dict(record))
                except (TypeError, ValueError):
                    malformed += 1
        except json.JSONDecodeError:
            malformed += 1

    state: Mapping[str, Any] = {}
    if state_path.is_file():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, Mapping):
                state = loaded
            else:
                malformed += 1
        except json.JSONDecodeError:
            malformed += 1

    unique = {block.block_id: block for block in blocks}
    ordered = tuple(unique[key] for key in sorted(unique))
    active = tuple(str(item) for item in state.get("active_block_ids", ()) if str(item).strip()) if isinstance(state.get("active_block_ids", ()), Sequence) and not isinstance(state.get("active_block_ids", ()), (str, bytes, bytearray)) else tuple(block.block_id for block in ordered if block.status in {MemoryTopicBlockStatus.ACTIVE, MemoryTopicBlockStatus.PROTECTED, MemoryTopicBlockStatus.OVERLOADED})
    overloaded = tuple(block.block_id for block in ordered if block.status is MemoryTopicBlockStatus.OVERLOADED)
    archived = tuple(block.block_id for block in ordered if block.status in {MemoryTopicBlockStatus.ARCHIVED, MemoryTopicBlockStatus.MERGED})
    default_value = state.get("default_block_id")
    default_id = str(default_value) if default_value is not None else next((block.block_id for block in ordered if normalize_topic_term(block.canonical_topic) == "general"), None)

    return MemoryTopicBlockRegistrySnapshot(
        runtime_root=str(root),
        versions_path=str(versions_path),
        state_path=str(state_path),
        legacy_registry_path=str(legacy_path),
        blocks=ordered,
        active_block_ids=active,
        default_block_id=default_id,
        overloaded_block_ids=overloaded,
        archived_block_ids=archived,
        malformed_record_count=malformed,
        registry_exists=versions_path.is_file() or state_path.is_file() or legacy_path.is_file(),
        legacy_registry_used=legacy_used,
    )


def detect_memory_topic(
    content: str,
    *,
    explicit_topic: str | None = None,
    tags: Sequence[str] = (),
    source: str | None = None,
    event_type: str | None = None,
    project_id: str | None = None,
    minimum_confidence: float = 0.55,
) -> MemoryTopicDetection:
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError("minimum_confidence must be between zero and one.")
    explicit = normalize_topic_term(explicit_topic or "")
    signals = tuple(str(value) for value in (*tags, source, event_type, project_id) if value is not None and str(value).strip())
    if explicit:
        return MemoryTopicDetection(
            canonical_topic=explicit,
            confidence=1.0,
            matched_signals=(f"explicit_topic:{explicit}",),
            alternative_topics=(),
            fallback_used=False,
            explicit_topic_used=True,
        )
    terms = extract_topic_terms(content, metadata_terms=signals, maximum_terms=8)
    confidence = calculate_routing_confidence(terms)
    label = select_topic_label(terms)
    fallback = not terms or confidence < minimum_confidence
    canonical = "general" if fallback else normalize_topic_term(label)
    alternatives = tuple(term.term for term in terms if term.term != canonical)[:3]
    matched = tuple(f"term:{term.term}" for term in terms[:5])
    if signals:
        matched += tuple(f"metadata:{normalize_topic_term(value)}" for value in signals if normalize_topic_term(value))
    return MemoryTopicDetection(
        canonical_topic=canonical,
        confidence=confidence,
        matched_signals=matched,
        alternative_topics=alternatives,
        fallback_used=fallback,
        explicit_topic_used=False,
    )


def plan_memory_topic_routing(
    *,
    item_id: str,
    content: str,
    registry: MemoryTopicBlockRegistrySnapshot,
    explicit_topic: str | None = None,
    tags: Sequence[str] = (),
    source: str | None = None,
    event_type: str | None = None,
    project_id: str | None = None,
    minimum_confidence: float = 0.55,
    creation_confidence: float = 0.70,
    plan_id: str | None = None,
) -> MemoryTopicRoutingPlan:
    if not item_id.strip():
        raise ValueError("item_id must be non-empty.")
    if not 0.0 <= creation_confidence <= 1.0:
        raise ValueError("creation_confidence must be between zero and one.")
    detection = detect_memory_topic(
        content,
        explicit_topic=explicit_topic,
        tags=tags,
        source=source,
        event_type=event_type,
        project_id=project_id,
        minimum_confidence=minimum_confidence,
    )
    topic = normalize_topic_term(detection.canonical_topic) or "general"
    candidates = [block for block in registry.blocks if block.status not in {MemoryTopicBlockStatus.ARCHIVED, MemoryTopicBlockStatus.MERGED} and topic in block.normalized_terms()]
    candidates.sort(key=lambda block: (block.status is MemoryTopicBlockStatus.OVERLOADED, block.memory_count, block.block_id))
    alternatives = tuple(block.block_id for block in registry.blocks if any(value in block.normalized_terms() for value in detection.alternative_topics) and block.status not in {MemoryTopicBlockStatus.ARCHIVED, MemoryTopicBlockStatus.MERGED})[:3]
    resolved_plan_id = plan_id or f"topic-plan-{item_id}"

    if candidates and not detection.fallback_used:
        target = candidates[0]
        reasons = ["matching_active_block_found"]
        if target.status is MemoryTopicBlockStatus.OVERLOADED:
            reasons.append("selected_block_is_overloaded_manual_review_recommended")
        return MemoryTopicRoutingPlan(
            plan_id=resolved_plan_id,
            item_id=item_id,
            action=MemoryTopicRoutingAction.USE_EXISTING_BLOCK,
            target_block_id=target.block_id,
            target_topic=target.canonical_topic,
            block_creation_required=False,
            routing_allowed=target.status is not MemoryTopicBlockStatus.OVERLOADED,
            confidence=detection.confidence,
            reasons=tuple(reasons),
            alternative_block_ids=alternatives,
            operations=("verify_item_is_human_validated", "verify_target_block_state", "route_in_separately_authorized_step"),
        )

    if detection.fallback_used:
        if registry.default_block_id:
            return MemoryTopicRoutingPlan(
                plan_id=resolved_plan_id,
                item_id=item_id,
                action=MemoryTopicRoutingAction.ROUTE_TO_DEFAULT,
                target_block_id=registry.default_block_id,
                target_topic="general",
                block_creation_required=False,
                routing_allowed=True,
                confidence=detection.confidence,
                reasons=("topic_confidence_below_threshold", "default_block_available"),
                alternative_block_ids=alternatives,
                operations=("verify_item_is_human_validated", "route_to_default_in_separately_authorized_step"),
            )
        return MemoryTopicRoutingPlan(
            plan_id=resolved_plan_id,
            item_id=item_id,
            action=MemoryTopicRoutingAction.REQUEST_MANUAL_REVIEW,
            target_block_id=None,
            target_topic="general",
            block_creation_required=False,
            routing_allowed=False,
            confidence=detection.confidence,
            reasons=("topic_confidence_below_threshold", "default_block_missing"),
            alternative_block_ids=alternatives,
            operations=("request_manual_topic_review",),
        )

    if detection.confidence >= creation_confidence:
        return MemoryTopicRoutingPlan(
            plan_id=resolved_plan_id,
            item_id=item_id,
            action=MemoryTopicRoutingAction.CREATE_NEW_BLOCK,
            target_block_id=build_topic_block_id(topic),
            target_topic=topic,
            block_creation_required=True,
            routing_allowed=False,
            confidence=detection.confidence,
            reasons=("no_matching_block_found", "topic_confidence_allows_creation_proposal"),
            alternative_block_ids=alternatives,
            operations=("request_block_creation_permission", "create_block_in_separately_authorized_step", "route_item_after_block_creation"),
        )

    return MemoryTopicRoutingPlan(
        plan_id=resolved_plan_id,
        item_id=item_id,
        action=MemoryTopicRoutingAction.REQUEST_MANUAL_REVIEW,
        target_block_id=None,
        target_topic=topic,
        block_creation_required=False,
        routing_allowed=False,
        confidence=detection.confidence,
        reasons=("no_matching_block_found", "topic_confidence_requires_manual_review"),
        alternative_block_ids=alternatives,
        operations=("request_manual_topic_review",),
    )
