"""Titan V2 short-term consolidation for memoriX.

Pipeline:

short-term events
-> importance / confidence / Titan surprise scoring
-> policy selection
-> dynamic grouping
-> deterministic group summary
-> update-target detection
-> pending memory-candidate creation

This module never validates candidates and never writes directly into the
Titan active-memory store. The cold archive is excluded from the consolidation
path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable

from memory.consolidation.candidate_service import (
    MemoryCandidateService,
)
from memory.consolidation.candidate_store import (
    MemoryCandidateStore,
)
from memory.consolidation.policy import (
    ConsolidationAction,
    ConsolidationDecision,
    ConsolidationPolicy,
    decide_event,
    normalize_content,
)
from memory.data import (
    CandidateStatus,
    MemoryCandidate,
    ShortTermEvent,
    ValidatedMemory,
    utc_now_iso,
)
from memory.hot_site.short_term_memory import (
    ShortTermEventStore,
)
from memory.hot_site.titan_active_memory import (
    HotSiteTitanMemory,
)


CONSOLIDATION_VERSION = "titan_v2"

UPDATE_MARKERS = (
    "update",
    "updated",
    "replace",
    "replaced",
    "change",
    "changed",
    "new value",
    "correction",
    "corrected",
    "actually",
    "instead",
    "now uses",
    "désormais",
    "corrige",
    "corrigé",
    "remplace",
    "remplacé",
    "modifie",
    "modifié",
    "maintenant",
)


@dataclass(frozen=True, slots=True)
class ScoredEvent:
    """Short-term event and its consolidation decision."""

    event: ShortTermEvent
    decision: ConsolidationDecision


@dataclass(frozen=True, slots=True)
class ConsolidationRunReport:
    """Result of one Titan V2 consolidation run."""

    mode: str
    started_at: str
    short_term_events: int
    events_promoted: int
    events_skipped: int
    groups_considered: int
    candidates_created: int
    duplicate_groups_skipped: int
    created_candidate_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialize the run report."""

        return {
            "status": "completed",
            "consolidation_version": CONSOLIDATION_VERSION,
            "mode": self.mode,
            "started_at": self.started_at,
            "short_term_events": self.short_term_events,
            "events_promoted": self.events_promoted,
            "events_skipped": self.events_skipped,
            "groups_considered": self.groups_considered,
            "candidates_created": self.candidates_created,
            "duplicate_groups_skipped": (
                self.duplicate_groups_skipped
            ),
            "created_candidate_ids": list(
                self.created_candidate_ids
            ),
            "target_storage_scope": (
                "hot_site_after_human_validation_only"
            ),
            "cold_site_contract": (
                "direct_archive_only_excluded_from_consolidation"
            ),
        }


def normalized_hash(value: str) -> str:
    """Return a deterministic compact SHA-256 hash."""

    normalized = re.sub(
        r"\s+",
        " ",
        value.strip().lower(),
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:16]


def short_text(value: str, limit: int = 260) -> str:
    """Normalize and truncate one summary fragment."""

    normalized = re.sub(
        r"\s+",
        " ",
        value.strip(),
    )

    if len(normalized) <= limit:
        return normalized

    return (
        normalized[: max(0, limit - 3)].rstrip()
        + "..."
    )


def event_group_key(event: ShortTermEvent) -> str:
    """Choose a dynamic group key without hard-coded topics."""

    if event.session_id:
        return f"session:{event.session_id}"

    if event.project_id:
        return f"project:{event.project_id}"

    for metadata_key in (
        "task_id",
        "message_id",
        "opencode_session_id",
        "conversation_id",
    ):
        value = event.metadata.get(metadata_key)

        if isinstance(value, str) and value.strip():
            return f"{metadata_key}:{value.strip()}"

    event_day = event.created_at[:10] or "unknown-day"

    return f"daily:{event_day}:{event.source}"


def group_scored_events(
    events: Iterable[ScoredEvent],
) -> dict[str, list[ScoredEvent]]:
    """Group promoted events by session, project, task, or day."""

    groups: dict[str, list[ScoredEvent]] = {}

    for scored_event in events:
        key = event_group_key(scored_event.event)
        groups.setdefault(key, []).append(scored_event)

    return groups


def contains_update_intent(event: ShortTermEvent) -> bool:
    """Detect explicit correction or update intent."""

    metadata_operation = event.metadata.get(
        "operation"
    )
    expected_operation = event.metadata.get(
        "expected_operation"
    )

    explicit_metadata_update = any(
        isinstance(value, str)
        and value.strip().lower()
        in {"update", "replace", "correction"}
        for value in (
            metadata_operation,
            expected_operation,
        )
    )

    if explicit_metadata_update:
        return True

    lowered = event.content.lower()

    return any(
        marker in lowered
        for marker in UPDATE_MARKERS
    )


def lexical_tokens(value: str) -> set[str]:
    """Return meaningful lowercase lexical tokens."""

    return {
        token
        for token in re.findall(
            r"[a-zA-ZÀ-ÿ0-9_'-]+",
            value.lower(),
        )
        if len(token) > 2
    }


def lexical_overlap(left: str, right: str) -> float:
    """Return Jaccard lexical overlap in [0, 1]."""

    left_tokens = lexical_tokens(left)
    right_tokens = lexical_tokens(right)

    if not left_tokens or not right_tokens:
        return 0.0

    return len(
        left_tokens & right_tokens
    ) / len(
        left_tokens | right_tokens
    )


def find_update_target(
    summary: str,
    active_memories: Iterable[ValidatedMemory],
    *,
    minimum_overlap: float = 0.08,
) -> tuple[ValidatedMemory | None, float]:
    """Select the best active hot-site target for an update."""

    best_memory: ValidatedMemory | None = None
    best_score = 0.0

    for memory in active_memories:
        if not memory.active:
            continue

        score = lexical_overlap(
            summary,
            memory.content,
        )

        if score > best_score:
            best_memory = memory
            best_score = score

    if best_score < minimum_overlap:
        return None, best_score

    return best_memory, best_score


def build_group_summary(
    group_key: str,
    group: list[ScoredEvent],
) -> str:
    """Build a deterministic reviewable candidate summary."""

    event_types = sorted(
        {
            item.event.event_type
            for item in group
        }
    )
    sources = sorted(
        {
            item.event.source
            for item in group
        }
    )

    lines = [
        "Titan V2 consolidated memory candidate.",
        f"Group: {group_key}.",
        (
            "Sources: "
            + (
                ", ".join(sources)
                if sources
                else "unknown"
            )
            + "."
        ),
        (
            "Event types: "
            + (
                ", ".join(event_types)
                if event_types
                else "unknown"
            )
            + "."
        ),
        "Summary:",
    ]

    for index, item in enumerate(
        group[:10],
        start=1,
    ):
        content = (
            item.decision.candidate_content
            or item.event.content
        )

        lines.append(
            f"{index}. "
            f"[{item.event.event_type}] "
            f"{short_text(content)}"
        )

    if len(group) > 10:
        lines.append(
            f"... {len(group) - 10} additional "
            "event(s) omitted."
        )

    lines.append(
        "Human review is required before this candidate "
        "may enter the Titan hot site."
    )

    return "\n".join(lines)


def existing_group_hashes(
    candidates: Iterable[MemoryCandidate],
) -> set[str]:
    """Collect hashes of groups already proposed."""

    hashes: set[str] = set()

    for candidate in candidates:
        value = candidate.metadata.get(
            "titan_v2_group_hash"
        )

        if isinstance(value, str) and value:
            hashes.add(value)

    return hashes


class TitanV2ConsolidationService:
    """Create pending candidates from short-term memory."""

    def __init__(
        self,
        short_term_store: ShortTermEventStore,
        candidate_store: MemoryCandidateStore,
        candidate_service: MemoryCandidateService,
        hot_site: HotSiteTitanMemory,
        *,
        policy: ConsolidationPolicy | None = None,
    ) -> None:
        self._short_term_store = short_term_store
        self._candidate_store = candidate_store
        self._candidate_service = candidate_service
        self._hot_site = hot_site
        self._policy = policy or ConsolidationPolicy()

    def score_events(
        self,
        events: Iterable[ShortTermEvent],
    ) -> tuple[ScoredEvent, ...]:
        """Compute Titan surprise and classify each event."""

        scored_events: list[ScoredEvent] = []
        promoted_normalized_contents: set[str] = set()

        for event in events:
            titan_surprise = self._hot_site.compute_surprise(
                event.content
            )

            decision = decide_event(
                event,
                titan_surprise=titan_surprise,
                policy=self._policy,
            )

            if (
                decision.action
                is ConsolidationAction.PROMOTE
            ):
                normalized = normalize_content(
                    decision.candidate_content or ""
                )

                if normalized in promoted_normalized_contents:
                    decision = ConsolidationDecision(
                        event_id=decision.event_id,
                        action=ConsolidationAction.SKIP,
                        reason=(
                            "Duplicate promoted content "
                            "in the current batch."
                        ),
                        candidate_content=None,
                        importance=decision.importance,
                        confidence=decision.confidence,
                        original_surprise=(
                            decision.original_surprise
                        ),
                        titan_surprise=(
                            decision.titan_surprise
                        ),
                        effective_surprise=(
                            decision.effective_surprise
                        ),
                        combined_score=(
                            decision.combined_score
                        ),
                    )
                else:
                    promoted_normalized_contents.add(
                        normalized
                    )

            scored_events.append(
                ScoredEvent(
                    event=event,
                    decision=decision,
                )
            )

        return tuple(scored_events)

    def run(
        self,
        *,
        mode: str = "manual",
    ) -> ConsolidationRunReport:
        """Run one candidate-creation pass.

        Short-term events remain stored after this method. Clearing and nightly
        scheduling will be handled by a later integration phase.
        """

        normalized_mode = mode.strip()

        if not normalized_mode:
            raise ValueError("mode must not be empty.")

        started_at = utc_now_iso()
        events = self._short_term_store.list_events()
        scored_events = self.score_events(events)

        promoted = tuple(
            item
            for item in scored_events
            if item.decision.action
            is ConsolidationAction.PROMOTE
        )

        skipped_count = (
            len(scored_events) - len(promoted)
        )

        groups = group_scored_events(promoted)

        stored_candidates = (
            self._candidate_store.list_candidates()
        )
        group_hashes = existing_group_hashes(
            stored_candidates
        )

        active_memories = self._hot_site.list_memories(
            active_only=True
        )

        created_candidate_ids: list[str] = []
        duplicate_groups_skipped = 0

        for group_key, group in groups.items():
            source_event_ids = tuple(
                item.event.event_id
                for item in group
            )

            group_hash = normalized_hash(
                "|".join(
                    sorted(source_event_ids)
                )
                or group_key
            )

            if group_hash in group_hashes:
                duplicate_groups_skipped += 1
                continue

            summary = build_group_summary(
                group_key,
                group,
            )

            update_intent = any(
                contains_update_intent(item.event)
                for item in group
            )

            target_memory = None
            update_overlap = 0.0

            if update_intent:
                target_memory, update_overlap = (
                    find_update_target(
                        summary,
                        active_memories,
                    )
                )

            importance_values = [
                item.decision.importance
                for item in group
            ]
            confidence_values = [
                item.decision.confidence
                for item in group
            ]
            surprise_values = [
                item.decision.effective_surprise
                for item in group
            ]
            combined_values = [
                item.decision.combined_score
                for item in group
            ]

            importance = max(
                importance_values,
                default=0.0,
            )
            confidence = (
                sum(confidence_values)
                / len(confidence_values)
                if confidence_values
                else 0.0
            )
            surprise = max(
                surprise_values,
                default=0.0,
            )

            metadata = {
                "created_by_consolidation": True,
                "consolidation_version": (
                    CONSOLIDATION_VERSION
                ),
                "consolidation_mode": normalized_mode,
                "requires_validation": True,
                "uses_titan_surprise": True,
                "titan_v2_group_key": group_key,
                "titan_v2_group_hash": group_hash,
                "short_term_event_ids": list(
                    source_event_ids
                ),
                "short_term_event_types": sorted(
                    {
                        item.event.event_type
                        for item in group
                    }
                ),
                "event_count": len(group),
                "importance_max": importance,
                "confidence_average": confidence,
                "surprise_max": surprise,
                "combined_score_max": max(
                    combined_values,
                    default=0.0,
                ),
                "update_candidate": update_intent,
                "update_target_score": update_overlap,
                "update_target_found": (
                    target_memory is not None
                ),
                "target_storage_scope": (
                    "hot_site_after_validation_only"
                ),
                "cold_site_contract": (
                    "excluded_from_consolidation_path"
                ),
                "cold_site_source": (
                    "direct_short_term_event_archive"
                ),
                "planned_at": started_at,
            }

            reason = (
                "Titan V2 selected this short-term group "
                "using importance, confidence, and Titan "
                "surprise. Human review is required."
            )

            if update_intent:
                reason += (
                    " The group appears to update or "
                    "correct an existing memory."
                )

            candidate = self._candidate_service.propose(
                content=summary,
                reason=reason,
                source_event_ids=source_event_ids,
                importance=importance,
                confidence=confidence,
                surprise=surprise,
                target_memory_id=(
                    target_memory.memory_id
                    if target_memory is not None
                    else None
                ),
                metadata=metadata,
            )

            created_candidate_ids.append(
                candidate.candidate_id
            )
            group_hashes.add(group_hash)

        return ConsolidationRunReport(
            mode=normalized_mode,
            started_at=started_at,
            short_term_events=len(events),
            events_promoted=len(promoted),
            events_skipped=skipped_count,
            groups_considered=len(groups),
            candidates_created=len(
                created_candidate_ids
            ),
            duplicate_groups_skipped=(
                duplicate_groups_skipped
            ),
            created_candidate_ids=tuple(
                created_candidate_ids
            ),
        )
