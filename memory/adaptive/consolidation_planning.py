"""Read-only consolidation planning for validated memoriX memories.

Part 26.1-26.5 audits the existing consolidation stack, collects a bounded
sample from Titan metadata, detects deterministic similarity groups, and
produces dry-run plans. It never loads Titan, writes runtime data, or accesses
the cold site.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from memory.data.paths import MemoryStoragePaths


class MemoryConsolidationStatus(str, Enum):
    """Lifecycle status reserved for consolidation sessions."""

    PLANNED = "planned"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERED = "recovered"


class MemoryConsolidationCategory(str, Enum):
    """Deterministic relationship between memories."""

    EXACT_DUPLICATE = "exact_duplicate"
    NEAR_DUPLICATE = "near_duplicate"
    COMPATIBLE_UPDATE = "compatible_update"
    CONFLICTING_UPDATE = "conflicting_update"
    RELATED_MEMORIES = "related_memories"
    INDEPENDENT_MEMORIES = "independent_memories"


class MemoryConsolidationAction(str, Enum):
    """Dry-run action recommended for one group."""

    KEEP_SEPARATE = "keep_separate"
    MERGE_INTO_SUMMARY = "merge_into_summary"
    MARK_AS_DUPLICATE = "mark_as_duplicate"
    SUPERSEDE_OLDER_MEMORY = "supersede_older_memory"
    REQUEST_MANUAL_REVIEW = "request_manual_review"
    PROMOTE_TO_HOT = "promote_to_hot"
    DEMOTE_TO_COLD = "demote_to_cold"
    ARCHIVE_INACTIVE = "archive_inactive"


@dataclass(frozen=True, slots=True)
class MemoryConsolidationAudit:
    """Summary of the consolidation capabilities already present."""

    event_promotion_policy_present: bool = True
    candidate_lifecycle_present: bool = True
    titan_v2_consolidation_present: bool = True
    bounded_runtime_collection_present: bool = True
    deterministic_grouping_present: bool = True
    execution_workflow_present: bool = False
    schedule_registry_present: bool = False
    recovery_workflow_present: bool = False
    dry_run: bool = True
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class MemoryConsolidationCandidate:
    """One bounded, read-only candidate collected from Titan metadata."""

    memory_id: str
    content: str
    active: bool
    created_at: str | None
    validated_at: str | None
    topic_block_id: str | None
    tags: tuple[str, ...]
    source: str | None
    project_id: str | None
    session_id: str | None
    supersedes_memory_id: str | None
    protected: bool
    metadata: dict[str, Any]

    def validate(self) -> None:
        if not self.memory_id.strip():
            raise ValueError("memory_id must not be empty.")
        if not self.content.strip():
            raise ValueError("content must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "active": self.active,
            "created_at": self.created_at,
            "validated_at": self.validated_at,
            "topic_block_id": self.topic_block_id,
            "tags": list(self.tags),
            "source": self.source,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "supersedes_memory_id": self.supersedes_memory_id,
            "protected": self.protected,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class MemoryConsolidationCollection:
    """Bounded collection report."""

    candidates: tuple[MemoryConsolidationCandidate, ...]
    records_scanned: int
    unique_memories_seen: int
    malformed_record_count: int
    assessment_limit: int
    truncated: bool
    topic_block_id: str | None
    metadata_path: str
    dry_run: bool = True
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "records_scanned": self.records_scanned,
            "unique_memories_seen": self.unique_memories_seen,
            "malformed_record_count": self.malformed_record_count,
            "assessment_limit": self.assessment_limit,
            "truncated": self.truncated,
            "topic_block_id": self.topic_block_id,
            "metadata_path": self.metadata_path,
            "dry_run": self.dry_run,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
        }


@dataclass(frozen=True, slots=True)
class MemoryConsolidationGroup:
    """One deterministic consolidation group."""

    group_id: str
    category: MemoryConsolidationCategory
    memory_ids: tuple[str, ...]
    similarity_score: float
    duplicate_score: float
    conflict_detected: bool
    protected_memory_ids: tuple[str, ...]
    recommended_action: MemoryConsolidationAction
    summary_preview: str | None
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "category": self.category.value,
            "memory_ids": list(self.memory_ids),
            "similarity_score": self.similarity_score,
            "duplicate_score": self.duplicate_score,
            "conflict_detected": self.conflict_detected,
            "protected_memory_ids": list(self.protected_memory_ids),
            "recommended_action": self.recommended_action.value,
            "summary_preview": self.summary_preview,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class MemoryConsolidationPlan:
    """Read-only consolidation plan."""

    plan_id: str
    status: MemoryConsolidationStatus
    groups: tuple[MemoryConsolidationGroup, ...]
    candidate_count: int
    grouped_memory_count: int
    independent_memory_ids: tuple[str, ...]
    operations: tuple[str, ...]
    requires_human_review: bool
    dry_run: bool = True
    consolidation_executed: bool = False
    summary_stored: bool = False
    memory_replaced: bool = False
    memory_archived: bool = False
    memory_promoted: bool = False
    memory_demoted: bool = False
    hot_site_modified: bool = False
    cold_site_modified: bool = False
    runtime_modified: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status.value,
            "groups": [group.to_dict() for group in self.groups],
            "candidate_count": self.candidate_count,
            "grouped_memory_count": self.grouped_memory_count,
            "independent_memory_ids": list(self.independent_memory_ids),
            "operations": list(self.operations),
            "requires_human_review": self.requires_human_review,
            "dry_run": self.dry_run,
            "consolidation_executed": self.consolidation_executed,
            "summary_stored": self.summary_stored,
            "memory_replaced": self.memory_replaced,
            "memory_archived": self.memory_archived,
            "memory_promoted": self.memory_promoted,
            "memory_demoted": self.memory_demoted,
            "hot_site_modified": self.hot_site_modified,
            "cold_site_modified": self.cold_site_modified,
            "runtime_modified": self.runtime_modified,
            "neural_model_loaded": self.neural_model_loaded,
        }


def audit_memory_consolidation() -> MemoryConsolidationAudit:
    """Return the part 26.1 capability audit without touching runtime data."""

    return MemoryConsolidationAudit()


def collect_memory_consolidation_candidates(
    runtime_root: str | Path,
    *,
    assessment_limit: int = 100,
    topic_block_id: str | None = None,
    active_only: bool = False,
) -> MemoryConsolidationCollection:
    """Collect the latest bounded Titan metadata records without loading Titan."""

    if assessment_limit <= 0:
        raise ValueError("assessment_limit must be positive.")

    paths = MemoryStoragePaths.from_runtime_root(runtime_root)
    source = paths.titan_metadata
    records: list[dict[str, Any]] = []
    malformed = 0

    if source.exists():
        with source.open("r", encoding="utf-8-sig") as stream:
            for raw_line in stream:
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                if not isinstance(payload, dict):
                    malformed += 1
                    continue
                records.append(payload)

    latest_by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in records:
        memory_id = str(record.get("memory_id") or record.get("id") or "").strip()
        if not memory_id:
            malformed += 1
            continue
        if memory_id not in latest_by_id:
            order.append(memory_id)
        latest_by_id[memory_id] = record

    candidates: list[MemoryConsolidationCandidate] = []
    for memory_id in order:
        record = latest_by_id[memory_id]
        metadata = dict(record.get("metadata") or {})
        active = bool(record.get("active", metadata.get("active", True)))
        if active_only and not active:
            continue
        candidate_topic = _optional_string(
            metadata.get("topic_block_id")
            or metadata.get("block_id")
            or metadata.get("topic")
        )
        if topic_block_id is not None and candidate_topic != topic_block_id:
            continue
        content = str(record.get("content") or metadata.get("content") or "").strip()
        if not content:
            malformed += 1
            continue
        tags_value = metadata.get("tags") or ()
        tags = tuple(str(value).strip() for value in tags_value if str(value).strip()) if isinstance(tags_value, (list, tuple, set)) else ()
        candidate = MemoryConsolidationCandidate(
            memory_id=memory_id,
            content=content,
            active=active,
            created_at=_optional_string(metadata.get("created_at") or record.get("stored_at")),
            validated_at=_optional_string(metadata.get("validated_at") or record.get("stored_at")),
            topic_block_id=candidate_topic,
            tags=tags,
            source=_optional_string(metadata.get("source") or record.get("source_agent")),
            project_id=_optional_string(metadata.get("project_id")),
            session_id=_optional_string(metadata.get("session_id")),
            supersedes_memory_id=_optional_string(metadata.get("supersedes_memory_id")),
            protected=bool(metadata.get("protected") or metadata.get("pinned") or metadata.get("policy_protected")),
            metadata=metadata,
        )
        candidate.validate()
        candidates.append(candidate)

    truncated = len(candidates) > assessment_limit
    selected = tuple(candidates[:assessment_limit])
    return MemoryConsolidationCollection(
        candidates=selected,
        records_scanned=len(records),
        unique_memories_seen=len(latest_by_id),
        malformed_record_count=malformed,
        assessment_limit=assessment_limit,
        truncated=truncated,
        topic_block_id=topic_block_id,
        metadata_path=str(source),
    )


def classify_memory_consolidation_pair(
    first: MemoryConsolidationCandidate,
    second: MemoryConsolidationCandidate,
) -> tuple[MemoryConsolidationCategory, float]:
    """Classify one pair using normalized text and metadata signals."""

    if first.memory_id == second.memory_id:
        return MemoryConsolidationCategory.EXACT_DUPLICATE, 1.0

    normalized_first = normalize_consolidation_content(first.content)
    normalized_second = normalize_consolidation_content(second.content)
    if normalized_first == normalized_second:
        return MemoryConsolidationCategory.EXACT_DUPLICATE, 1.0

    similarity = consolidation_similarity(first, second)
    if first.supersedes_memory_id == second.memory_id or second.supersedes_memory_id == first.memory_id:
        return MemoryConsolidationCategory.COMPATIBLE_UPDATE, max(similarity, 0.9)
    if similarity >= 0.82:
        return MemoryConsolidationCategory.NEAR_DUPLICATE, similarity
    if _same_scope(first, second) and similarity >= 0.45 and _conflict_terms(first.content, second.content):
        return MemoryConsolidationCategory.CONFLICTING_UPDATE, similarity
    if similarity >= 0.35:
        return MemoryConsolidationCategory.RELATED_MEMORIES, similarity
    return MemoryConsolidationCategory.INDEPENDENT_MEMORIES, similarity


def detect_memory_consolidation_groups(
    candidates: Iterable[MemoryConsolidationCandidate],
    *,
    minimum_similarity: float = 0.35,
    maximum_groups: int = 50,
    maximum_memories_per_group: int = 10,
) -> tuple[MemoryConsolidationGroup, ...]:
    """Build deterministic non-overlapping groups from a bounded candidate set."""

    if not 0.0 <= minimum_similarity <= 1.0:
        raise ValueError("minimum_similarity must be between 0 and 1.")
    if maximum_groups <= 0 or maximum_memories_per_group < 2:
        raise ValueError("group limits are invalid.")

    remaining = list(candidates)
    groups: list[MemoryConsolidationGroup] = []
    used: set[str] = set()
    for index, first in enumerate(remaining):
        if first.memory_id in used or len(groups) >= maximum_groups:
            continue
        members = [first]
        categories: list[MemoryConsolidationCategory] = []
        scores: list[float] = []
        for second in remaining[index + 1:]:
            if second.memory_id in used or len(members) >= maximum_memories_per_group:
                continue
            category, score = classify_memory_consolidation_pair(first, second)
            if category is MemoryConsolidationCategory.INDEPENDENT_MEMORIES or score < minimum_similarity:
                continue
            members.append(second)
            categories.append(category)
            scores.append(score)
        if len(members) < 2:
            continue
        for member in members:
            used.add(member.memory_id)
        category = _select_group_category(categories)
        score = sum(scores) / len(scores)
        protected = tuple(member.memory_id for member in members if member.protected)
        action = _recommended_action(category, bool(protected))
        groups.append(MemoryConsolidationGroup(
            group_id="group_" + "_".join(member.memory_id for member in members),
            category=category,
            memory_ids=tuple(member.memory_id for member in members),
            similarity_score=round(score, 6),
            duplicate_score=round(1.0 if category is MemoryConsolidationCategory.EXACT_DUPLICATE else score, 6),
            conflict_detected=category is MemoryConsolidationCategory.CONFLICTING_UPDATE,
            protected_memory_ids=protected,
            recommended_action=action,
            summary_preview=_summary_preview(members) if action is MemoryConsolidationAction.MERGE_INTO_SUMMARY else None,
            reasons=(f"deterministic_category:{category.value}", f"member_count:{len(members)}"),
        ))
    return tuple(groups)


def plan_memory_consolidation(
    collection: MemoryConsolidationCollection,
    *,
    plan_id: str = "consolidation-plan",
    minimum_similarity: float = 0.35,
    maximum_groups: int = 50,
    maximum_memories_per_group: int = 10,
) -> MemoryConsolidationPlan:
    """Produce a mutation-free consolidation plan."""

    identifier = plan_id.strip()
    if not identifier:
        raise ValueError("plan_id must not be empty.")
    groups = detect_memory_consolidation_groups(
        collection.candidates,
        minimum_similarity=minimum_similarity,
        maximum_groups=maximum_groups,
        maximum_memories_per_group=maximum_memories_per_group,
    )
    grouped = {memory_id for group in groups for memory_id in group.memory_ids}
    independent = tuple(candidate.memory_id for candidate in collection.candidates if candidate.memory_id not in grouped)
    requires_review = any(
        group.recommended_action is not MemoryConsolidationAction.KEEP_SEPARATE
        for group in groups
    )
    return MemoryConsolidationPlan(
        plan_id=identifier,
        status=MemoryConsolidationStatus.AWAITING_REVIEW if requires_review else MemoryConsolidationStatus.PLANNED,
        groups=groups,
        candidate_count=len(collection.candidates),
        grouped_memory_count=len(grouped),
        independent_memory_ids=independent,
        operations=(
            "verify_bounded_collection",
            "review_detected_groups",
            "protect_protected_memories",
            "approve_or_reject_plan",
            "execute_in_separate_workflow",
        ),
        requires_human_review=requires_review,
    )


def normalize_consolidation_content(content: str) -> str:
    normalized = content.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ -]", "", normalized)


def consolidation_similarity(first: MemoryConsolidationCandidate, second: MemoryConsolidationCandidate) -> float:
    first_tokens = _tokens(first)
    second_tokens = _tokens(second)
    if not first_tokens or not second_tokens:
        return 0.0
    union = first_tokens | second_tokens
    lexical = len(first_tokens & second_tokens) / len(union)
    scope_bonus = 0.0
    if first.topic_block_id and first.topic_block_id == second.topic_block_id:
        scope_bonus += 0.08
    if first.project_id and first.project_id == second.project_id:
        scope_bonus += 0.05
    if first.session_id and first.session_id == second.session_id:
        scope_bonus += 0.03
    return min(1.0, lexical + scope_bonus)


def _tokens(candidate: MemoryConsolidationCandidate) -> set[str]:
    text = normalize_consolidation_content(candidate.content)
    tokens = {token for token in text.split() if len(token) > 1}
    tokens.update(tag.lower() for tag in candidate.tags)
    return tokens


def _same_scope(first: MemoryConsolidationCandidate, second: MemoryConsolidationCandidate) -> bool:
    return bool(
        (first.topic_block_id and first.topic_block_id == second.topic_block_id)
        or (first.project_id and first.project_id == second.project_id)
        or (first.session_id and first.session_id == second.session_id)
    )


def _conflict_terms(first: str, second: str) -> bool:
    patterns = (("not ", ""), ("no longer", "now"), ("ancien", "maintenant"), ("old", "new"))
    lowered_first = first.lower()
    lowered_second = second.lower()
    return any((left in lowered_first and right in lowered_second) or (left in lowered_second and right in lowered_first) for left, right in patterns)


def _select_group_category(categories: list[MemoryConsolidationCategory]) -> MemoryConsolidationCategory:
    priority = (
        MemoryConsolidationCategory.CONFLICTING_UPDATE,
        MemoryConsolidationCategory.COMPATIBLE_UPDATE,
        MemoryConsolidationCategory.EXACT_DUPLICATE,
        MemoryConsolidationCategory.NEAR_DUPLICATE,
        MemoryConsolidationCategory.RELATED_MEMORIES,
    )
    return next(category for category in priority if category in categories)


def _recommended_action(category: MemoryConsolidationCategory, protected: bool) -> MemoryConsolidationAction:
    if protected or category is MemoryConsolidationCategory.CONFLICTING_UPDATE:
        return MemoryConsolidationAction.REQUEST_MANUAL_REVIEW
    if category is MemoryConsolidationCategory.EXACT_DUPLICATE:
        return MemoryConsolidationAction.MARK_AS_DUPLICATE
    if category is MemoryConsolidationCategory.NEAR_DUPLICATE:
        return MemoryConsolidationAction.MERGE_INTO_SUMMARY
    if category is MemoryConsolidationCategory.COMPATIBLE_UPDATE:
        return MemoryConsolidationAction.SUPERSEDE_OLDER_MEMORY
    return MemoryConsolidationAction.KEEP_SEPARATE


def _summary_preview(memories: list[MemoryConsolidationCandidate]) -> str:
    unique: list[str] = []
    for memory in memories:
        content = memory.content.strip()
        if content not in unique:
            unique.append(content)
    return " | ".join(unique)[:500]


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
