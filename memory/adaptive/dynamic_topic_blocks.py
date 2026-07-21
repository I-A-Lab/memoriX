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

from memory.adaptive.topic_schema import normalize_topic_assignment_record, normalize_topic_block_record
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
                blocks.append(MemoryTopicBlock.from_dict(normalize_topic_block_record(payload)))
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
                    blocks.append(MemoryTopicBlock.from_dict(normalize_topic_block_record(record)))
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


# ---------------------------------------------------------------------------
# Part 25.6-25.8: controlled topic-block mutations and rebalance planning.
# ---------------------------------------------------------------------------

from datetime import datetime, timezone
import os
import tempfile


@dataclass(frozen=True, slots=True)
class MemoryTopicBlockOperationResult:
    action: str
    ok: bool
    block: MemoryTopicBlock | None = None
    source_block_id: str | None = None
    target_block_id: str | None = None
    assignment_id: str | None = None
    message: str = ""
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
        payload["block"] = None if self.block is None else self.block.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class MemoryTopicBlockMergePlan:
    source_block_id: str
    target_block_id: str
    allowed: bool
    reasons: tuple[str, ...]
    operations: tuple[str, ...]
    dry_run: bool = True
    block_merged: bool = False
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "reasons": list(self.reasons), "operations": list(self.operations)}


@dataclass(frozen=True, slots=True)
class MemoryTopicBlockRebalancePlan:
    total_blocks: int
    overloaded_block_ids: tuple[str, ...]
    nearly_empty_block_ids: tuple[str, ...]
    merge_candidates: tuple[tuple[str, str], ...]
    recommendations: tuple[str, ...]
    dry_run: bool = True
    block_updated: bool = False
    block_merged: bool = False
    block_archived: bool = False
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "overloaded_block_ids": list(self.overloaded_block_ids),
            "nearly_empty_block_ids": list(self.nearly_empty_block_ids),
            "merge_candidates": [list(pair) for pair in self.merge_candidates],
            "recommendations": list(self.recommendations),
        }


def _topic_registry_paths(runtime_root: str | Path) -> tuple[Path, Path, Path]:
    root = Path(runtime_root).expanduser().resolve()
    directory = root / "topic_blocks"
    return directory, directory / "topic_blocks.jsonl", directory / "topic_block_state.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


def _write_topic_registry(runtime_root: str | Path, blocks: Sequence[MemoryTopicBlock], *, default_block_id: str | None = None) -> None:
    directory, versions_path, state_path = _topic_registry_paths(runtime_root)
    directory.mkdir(parents=True, exist_ok=True)
    ordered = sorted(blocks, key=lambda item: item.block_id)
    versions_content = "".join(json.dumps(block.to_dict(), sort_keys=True) + "\n" for block in ordered)
    active = [block.block_id for block in ordered if block.status in {MemoryTopicBlockStatus.ACTIVE, MemoryTopicBlockStatus.PROTECTED, MemoryTopicBlockStatus.OVERLOADED}]
    overloaded = [block.block_id for block in ordered if block.status is MemoryTopicBlockStatus.OVERLOADED]
    archived = [block.block_id for block in ordered if block.status in {MemoryTopicBlockStatus.ARCHIVED, MemoryTopicBlockStatus.MERGED}]
    state = {
        "active_block_ids": active,
        "default_block_id": default_block_id,
        "overloaded_block_ids": overloaded,
        "archived_block_ids": archived,
        "updated_at": _utc_now(),
    }
    _atomic_write(versions_path, versions_content)
    _atomic_write(state_path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def create_memory_topic_block(
    runtime_root: str | Path,
    *,
    canonical_topic: str,
    display_name: str | None = None,
    aliases: Sequence[str] = (),
    protected: bool = False,
    set_as_default: bool = False,
) -> MemoryTopicBlockOperationResult:
    topic = normalize_topic_term(canonical_topic)
    if not topic:
        raise ValueError("canonical_topic must be non-empty after normalization.")
    snapshot = inspect_memory_topic_block_registry(runtime_root)
    normalized_aliases = tuple(sorted({value for alias in aliases if (value := normalize_topic_term(alias)) and value != topic}))
    existing = next((block for block in snapshot.blocks if topic in block.normalized_terms()), None)
    if existing is not None:
        return MemoryTopicBlockOperationResult(action="create", ok=True, block=existing, target_block_id=existing.block_id, message="existing_block_reused")
    block = MemoryTopicBlock(
        block_id=build_topic_block_id(topic),
        canonical_topic=topic,
        display_name=(display_name or canonical_topic).strip() or topic,
        aliases=normalized_aliases,
        status=MemoryTopicBlockStatus.PROTECTED if protected else MemoryTopicBlockStatus.ACTIVE,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    block.validate()
    default_id = block.block_id if set_as_default or (topic == "general" and snapshot.default_block_id is None) else snapshot.default_block_id
    _write_topic_registry(runtime_root, (*snapshot.blocks, block), default_block_id=default_id)
    return MemoryTopicBlockOperationResult(action="create", ok=True, block=block, target_block_id=block.block_id, message="block_created", block_created=True, registry_modified=True)


def update_memory_topic_block(
    runtime_root: str | Path,
    *,
    block_id: str,
    action: str,
    value: str | None = None,
) -> MemoryTopicBlockOperationResult:
    snapshot = inspect_memory_topic_block_registry(runtime_root)
    current = next((block for block in snapshot.blocks if block.block_id == block_id), None)
    if current is None:
        return MemoryTopicBlockOperationResult(action=action, ok=False, source_block_id=block_id, message="block_not_found")
    normalized_action = action.strip().lower()
    aliases = list(current.aliases)
    status = current.status
    display_name = current.display_name
    archived = False
    if normalized_action == "rename":
        if value is None or not value.strip():
            raise ValueError("rename requires a non-empty value.")
        display_name = value.strip()
    elif normalized_action == "add_alias":
        alias = normalize_topic_term(value or "")
        if not alias:
            raise ValueError("add_alias requires a non-empty value.")
        if alias not in aliases and alias != normalize_topic_term(current.canonical_topic):
            aliases.append(alias)
    elif normalized_action == "remove_alias":
        alias = normalize_topic_term(value or "")
        aliases = [item for item in aliases if normalize_topic_term(item) != alias]
    elif normalized_action == "archive":
        if current.status is MemoryTopicBlockStatus.PROTECTED:
            return MemoryTopicBlockOperationResult(action=action, ok=False, block=current, source_block_id=block_id, message="protected_block_cannot_be_archived")
        status = MemoryTopicBlockStatus.ARCHIVED
        archived = True
    elif normalized_action == "restore":
        status = MemoryTopicBlockStatus.ACTIVE
    else:
        raise ValueError("Unsupported topic block update action.")
    updated = MemoryTopicBlock(
        block_id=current.block_id,
        canonical_topic=current.canonical_topic,
        display_name=display_name,
        aliases=tuple(sorted(set(aliases))),
        status=status,
        memory_count=current.memory_count,
        protected_memory_count=current.protected_memory_count,
        created_at=current.created_at,
        updated_at=_utc_now(),
        parent_block_id=current.parent_block_id,
        merged_into_block_id=current.merged_into_block_id,
    )
    blocks = tuple(updated if item.block_id == block_id else item for item in snapshot.blocks)
    default_id = None if archived and snapshot.default_block_id == block_id else snapshot.default_block_id
    _write_topic_registry(runtime_root, blocks, default_block_id=default_id)
    return MemoryTopicBlockOperationResult(action=normalized_action, ok=True, block=updated, source_block_id=block_id, message="block_updated", block_updated=True, block_archived=archived, registry_modified=True)


def route_memory_to_topic_block(runtime_root: str | Path, *, item_id: str, block_id: str, actor: str = "manual") -> MemoryTopicBlockOperationResult:
    if not item_id.strip():
        raise ValueError("item_id must be non-empty.")
    snapshot = inspect_memory_topic_block_registry(runtime_root)
    block = next((item for item in snapshot.blocks if item.block_id == block_id), None)
    if block is None or block.status in {MemoryTopicBlockStatus.ARCHIVED, MemoryTopicBlockStatus.MERGED}:
        return MemoryTopicBlockOperationResult(action="route", ok=False, target_block_id=block_id, message="target_block_unavailable")
    directory, _, _ = _topic_registry_paths(runtime_root)
    assignments_path = directory / "topic_assignments.jsonl"
    existing = assignments_path.read_text(encoding="utf-8").splitlines() if assignments_path.is_file() else []
    assignment_id = f"assignment-{item_id}-{block_id}"
    record = normalize_topic_assignment_record({"assignment_id": assignment_id, "item_id": item_id, "block_id": block_id, "actor": actor, "created_at": _utc_now()})
    if not any(json.loads(line).get("assignment_id") == assignment_id for line in existing if line.strip()):
        existing.append(json.dumps(record, sort_keys=True))
        _atomic_write(assignments_path, "\n".join(existing) + "\n")
    return MemoryTopicBlockOperationResult(action="route", ok=True, block=block, target_block_id=block_id, assignment_id=assignment_id, message="memory_routed", memory_routed=True, registry_modified=True)


def plan_memory_topic_block_merge(runtime_root: str | Path, *, source_block_id: str, target_block_id: str) -> MemoryTopicBlockMergePlan:
    snapshot = inspect_memory_topic_block_registry(runtime_root)
    by_id = {block.block_id: block for block in snapshot.blocks}
    reasons: list[str] = []
    allowed = True
    if source_block_id == target_block_id:
        allowed = False
        reasons.append("source_and_target_are_identical")
    source = by_id.get(source_block_id)
    target = by_id.get(target_block_id)
    if source is None:
        allowed = False
        reasons.append("source_block_missing")
    if target is None:
        allowed = False
        reasons.append("target_block_missing")
    if source is not None and source.status is MemoryTopicBlockStatus.PROTECTED:
        allowed = False
        reasons.append("protected_source_block")
    if target is not None and target.status in {MemoryTopicBlockStatus.ARCHIVED, MemoryTopicBlockStatus.MERGED}:
        allowed = False
        reasons.append("target_block_unavailable")
    if allowed:
        reasons.append("merge_is_allowed")
    return MemoryTopicBlockMergePlan(source_block_id=source_block_id, target_block_id=target_block_id, allowed=allowed, reasons=tuple(reasons), operations=("verify_source_and_target", "preserve_source_history", "move_logical_assignments", "mark_source_merged", "verify_registry_state"))


def merge_memory_topic_blocks(runtime_root: str | Path, *, source_block_id: str, target_block_id: str) -> MemoryTopicBlockOperationResult:
    plan = plan_memory_topic_block_merge(runtime_root, source_block_id=source_block_id, target_block_id=target_block_id)
    if not plan.allowed:
        return MemoryTopicBlockOperationResult(action="merge", ok=False, source_block_id=source_block_id, target_block_id=target_block_id, message=",".join(plan.reasons))
    snapshot = inspect_memory_topic_block_registry(runtime_root)
    by_id = {block.block_id: block for block in snapshot.blocks}
    source = by_id[source_block_id]
    target = by_id[target_block_id]
    source_updated = MemoryTopicBlock(**{**source.__dict__, "status": MemoryTopicBlockStatus.MERGED, "merged_into_block_id": target_block_id, "updated_at": _utc_now()}) if hasattr(source, "__dict__") else MemoryTopicBlock(block_id=source.block_id, canonical_topic=source.canonical_topic, display_name=source.display_name, aliases=source.aliases, status=MemoryTopicBlockStatus.MERGED, memory_count=source.memory_count, protected_memory_count=source.protected_memory_count, created_at=source.created_at, updated_at=_utc_now(), parent_block_id=source.parent_block_id, merged_into_block_id=target_block_id)
    target_updated = MemoryTopicBlock(block_id=target.block_id, canonical_topic=target.canonical_topic, display_name=target.display_name, aliases=tuple(sorted(set((*target.aliases, source.canonical_topic, *source.aliases)))), status=target.status, memory_count=target.memory_count + source.memory_count, protected_memory_count=target.protected_memory_count + source.protected_memory_count, created_at=target.created_at, updated_at=_utc_now(), parent_block_id=target.parent_block_id, merged_into_block_id=target.merged_into_block_id)
    blocks = tuple(source_updated if item.block_id == source_block_id else target_updated if item.block_id == target_block_id else item for item in snapshot.blocks)
    default_id = target_block_id if snapshot.default_block_id == source_block_id else snapshot.default_block_id
    _write_topic_registry(runtime_root, blocks, default_block_id=default_id)
    return MemoryTopicBlockOperationResult(action="merge", ok=True, block=target_updated, source_block_id=source_block_id, target_block_id=target_block_id, message="blocks_merged", block_updated=True, block_merged=True, registry_modified=True)


def plan_memory_topic_block_rebalance(runtime_root: str | Path, *, overloaded_threshold: int = 50000, nearly_empty_threshold: int = 1) -> MemoryTopicBlockRebalancePlan:
    if overloaded_threshold < 1 or nearly_empty_threshold < 0:
        raise ValueError("rebalance thresholds are invalid.")
    snapshot = inspect_memory_topic_block_registry(runtime_root)
    active = [block for block in snapshot.blocks if block.status in {MemoryTopicBlockStatus.ACTIVE, MemoryTopicBlockStatus.OVERLOADED}]
    overloaded = tuple(sorted(block.block_id for block in active if block.memory_count >= overloaded_threshold))
    nearly_empty = tuple(sorted(block.block_id for block in active if block.memory_count <= nearly_empty_threshold and block.block_id != snapshot.default_block_id))
    pairs: list[tuple[str, str]] = []
    for index, source in enumerate(active):
        for target in active[index + 1:]:
            if set(source.normalized_terms()) & set(target.normalized_terms()):
                pairs.append((source.block_id, target.block_id))
    recommendations: list[str] = []
    if overloaded:
        recommendations.append("split_overloaded_blocks")
    if nearly_empty:
        recommendations.append("review_or_archive_nearly_empty_blocks")
    if pairs:
        recommendations.append("review_similar_blocks_for_merge")
    if not recommendations:
        recommendations.append("keep_unchanged")
    return MemoryTopicBlockRebalancePlan(total_blocks=len(snapshot.blocks), overloaded_block_ids=overloaded, nearly_empty_block_ids=nearly_empty, merge_candidates=tuple(sorted(pairs)), recommendations=tuple(recommendations))
