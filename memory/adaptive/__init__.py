"""Observable adaptive-memory primitives.

Part 12B exposes metrics only. Nothing in this package performs expansion,
pruning, validation, cold fallback, or automatic rehydration.
"""

from memory.adaptive.contracts import (
    PressureComponents,
    PressureLevel,
    PressureObservation,
    PressureObservationInput,
    PressureThresholds,
    ControlledTopicRouting,
    PressureWeights,
    TopicBlockInput,
    TopicBlockObservation,
    TopicBlockRoutingObservation,
    TopicTerm,
)
from memory.adaptive.pressure import (
    calculate_entropy,
    calculate_memory_pressure,
    calculate_momentum,
    calculate_pressure_persistence,
    calculate_surprise,
    calculate_usage_ratio,
    classify_pressure_level,
    observe_memory_pressure,
)
from memory.adaptive.pressure_history import (
    PressureHistoryStore,
)
from memory.adaptive.block_registry import (
    TopicBlockRegistry,
)
from memory.adaptive.routing import (
    merge_topic_routing_metadata,
    route_validated_candidate,
    topic_routing_from_metadata,
)
from memory.adaptive.routing_service import (
    ControlledTopicRoutingService,
)
from memory.adaptive.topic_blocks import (
    build_topic_block_id,
    calculate_routing_confidence,
    content_digest,
    extract_topic_terms,
    normalize_topic_term,
    observe_topic_block,
    select_topic_label,
    term_counts,
)

__all__ = [
    "ControlledTopicRouting",
    "ControlledTopicRoutingService",
    "PressureComponents",
    "PressureHistoryStore",
    "PressureLevel",
    "PressureObservation",
    "PressureObservationInput",
    "PressureThresholds",
    "PressureWeights",
    "TopicBlockInput",
    "TopicBlockObservation",
    "TopicBlockRegistry",
    "TopicBlockRoutingObservation",
    "TopicTerm",
    "calculate_entropy",
    "calculate_memory_pressure",
    "calculate_momentum",
    "calculate_pressure_persistence",
    "calculate_surprise",
    "calculate_usage_ratio",
    "classify_pressure_level",
    "observe_memory_pressure",
    "build_topic_block_id",
    "calculate_routing_confidence",
    "content_digest",
    "extract_topic_terms",
    "normalize_topic_term",
    "observe_topic_block",
    "select_topic_label",
    "term_counts",
    "merge_topic_routing_metadata",
    "route_validated_candidate",
    "topic_routing_from_metadata",
]
from memory.adaptive.capacity import (
    recommend_dynamic_capacity,
)
from memory.adaptive.capacity_history import (
    CapacityRecommendationStore,
)
from memory.adaptive.contracts import (
    CapacityPolicy,
    CapacityRecommendation,
    CapacityRecommendationInput,
    CapacityRecommendationLevel,
)

__all__ += [
    "CapacityPolicy",
    "CapacityRecommendation",
    "CapacityRecommendationInput",
    "CapacityRecommendationLevel",
    "CapacityRecommendationStore",
    "recommend_dynamic_capacity",
]
from memory.adaptive.contracts import (
    HotMemoryPruningInput,
    SoftPruningAction,
    SoftPruningPlan,
    SoftPruningPolicy,
    SoftPruningRecommendation,
)
from memory.adaptive.pruning import (
    calculate_retention_score,
    plan_soft_pruning,
    recommend_soft_pruning,
)
from memory.adaptive.pruning_history import (
    SoftPruningPlanStore,
)

__all__ += [
    "HotMemoryPruningInput",
    "SoftPruningAction",
    "SoftPruningPlan",
    "SoftPruningPlanStore",
    "SoftPruningPolicy",
    "SoftPruningRecommendation",
    "calculate_retention_score",
    "plan_soft_pruning",
    "recommend_soft_pruning",
]
from memory.adaptive.contracts import (
    AdaptiveControllerDecision,
    AdaptiveControllerInput,
    AdaptiveDecisionStatus,
)
from memory.adaptive.controller import (
    evaluate_adaptive_controller,
)
from memory.adaptive.controller_history import (
    AdaptiveDecisionStore,
)

__all__ += [
    "AdaptiveControllerDecision",
    "AdaptiveControllerInput",
    "AdaptiveDecisionStatus",
    "AdaptiveDecisionStore",
    "evaluate_adaptive_controller",
]
from memory.adaptive.runtime_capacity import (
    RuntimeCapacitySnapshot,
    classify_runtime_pressure,
    inspect_runtime_capacity,
    validate_external_runtime_root,
)

__all__ += [
    "RuntimeCapacitySnapshot",
    "classify_runtime_pressure",
    "inspect_runtime_capacity",
    "validate_external_runtime_root",
]
from memory.adaptive.memory_pressure import (
    HotSitePressureSnapshot,
    MemoryPressureAssessment,
    MemoryPressureComponents,
    MemoryPressureInput,
    MemoryPressureWeights,
    assess_memory_pressure,
    normalize_age,
    normalize_low_usage,
    normalize_non_negative,
    normalize_unit,
    observe_hot_site_pressure,
)

__all__ += [
    "HotSitePressureSnapshot",
    "MemoryPressureAssessment",
    "MemoryPressureComponents",
    "MemoryPressureInput",
    "MemoryPressureWeights",
    "assess_memory_pressure",
    "normalize_age",
    "normalize_low_usage",
    "normalize_non_negative",
    "normalize_unit",
    "observe_hot_site_pressure",
]
from memory.adaptive.runtime_memory_pressure import (
    RuntimeMemoryPressureReport,
    inspect_runtime_memory_pressure,
    inspect_runtime_memory_pressure_item,
    pressure_input_from_metadata,
)

__all__ += [
    "RuntimeMemoryPressureReport",
    "inspect_runtime_memory_pressure",
    "inspect_runtime_memory_pressure_item",
    "pressure_input_from_metadata",
]
from memory.adaptive.retention_scoring import (
    HotSiteRetentionRanking,
    RetentionScoreAssessment,
    RetentionScoreComponents,
    RetentionScoringInput,
    RetentionScoringThresholds,
    RetentionScoringWeights,
    assess_adaptive_retention,
    calculate_adaptive_retention_score,
    rank_hot_site_memories,
)

__all__ += [
    "HotSiteRetentionRanking",
    "RetentionScoreAssessment",
    "RetentionScoreComponents",
    "RetentionScoringInput",
    "RetentionScoringThresholds",
    "RetentionScoringWeights",
    "assess_adaptive_retention",
    "calculate_adaptive_retention_score",
    "rank_hot_site_memories",
]
