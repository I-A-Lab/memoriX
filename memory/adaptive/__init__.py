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

from memory.adaptive.runtime_retention_scoring import (
    RuntimeRetentionRankingReport,
    inspect_runtime_retention_item,
    inspect_runtime_retention_ranking,
    retention_input_from_metadata,
)
from memory.adaptive.runtime_adaptive_routing import (
    RuntimeAdaptiveRoutingReport,
    inspect_runtime_adaptive_routing,
)

__all__ += [
    "RuntimeRetentionRankingReport",
    "inspect_runtime_retention_item",
    "inspect_runtime_retention_ranking",
    "retention_input_from_metadata",
    "RuntimeAdaptiveRoutingReport",
    "inspect_runtime_adaptive_routing",
]

from memory.adaptive.adaptive_routing_policy import (
    AdaptiveRoutingContext,
    AdaptiveRoutingDecision,
    AdaptiveRoutingDecisionType,
    AdaptiveRoutingInput,
    AdaptiveRoutingPlan,
    AdaptiveRoutingPolicy,
    RoutingPruningCandidate,
    decide_adaptive_routing,
    plan_adaptive_routing,
)

__all__ += [
    "AdaptiveRoutingContext",
    "AdaptiveRoutingDecision",
    "AdaptiveRoutingDecisionType",
    "AdaptiveRoutingInput",
    "AdaptiveRoutingPlan",
    "AdaptiveRoutingPolicy",
    "RoutingPruningCandidate",
    "decide_adaptive_routing",
    "plan_adaptive_routing",
]

from memory.adaptive.policy_search import (
    MemoryPolicyCandidate,
    MemoryPolicyDataset,
    MemoryPolicyEvaluationCase,
    MemoryPolicyMetrics,
    MemoryPolicySearchConfig,
    MemoryPolicySearchResult,
    MemoryPolicySearchSpace,
    MemoryPolicyTrial,
    default_memory_policy_dataset,
    default_memory_policy_search_space,
    evaluate_memory_policy,
    search_memory_policies,
)

__all__ += [
    "MemoryPolicyCandidate",
    "MemoryPolicyDataset",
    "MemoryPolicyEvaluationCase",
    "MemoryPolicyMetrics",
    "MemoryPolicySearchConfig",
    "MemoryPolicySearchResult",
    "MemoryPolicySearchSpace",
    "MemoryPolicyTrial",
    "default_memory_policy_dataset",
    "default_memory_policy_search_space",
    "evaluate_memory_policy",
    "search_memory_policies",
]

from memory.adaptive.runtime_policy_search import (
    RuntimePolicySearchReport,
    inspect_runtime_policy_search,
)

__all__ += [
    "RuntimePolicySearchReport",
    "inspect_runtime_policy_search",
]

from memory.adaptive.policy_lifecycle import (
    MemoryPolicyComparison,
    MemoryPolicyLifecycleAudit,
    MemoryPolicyLifecycleResult,
    MemoryPolicyActivationPlan,
    MemoryPolicyRollbackPlan,
    MemoryPolicyLifecycleStatus,
    MemoryPolicyProposalPreview,
    MemoryPolicyRegistrySnapshot,
    MemoryPolicyVersion,
    audit_memory_policy_lifecycle,
    compare_memory_policy_versions,
    inspect_memory_policy_registry,
    preview_memory_policy_proposal,
    propose_memory_policy,
    review_memory_policy,
    plan_memory_policy_activation,
    activate_memory_policy,
    plan_memory_policy_rollback,
    rollback_memory_policy,
)

__all__ += [
    "MemoryPolicyComparison",
    "MemoryPolicyLifecycleAudit",
    "MemoryPolicyLifecycleResult",
    "MemoryPolicyActivationPlan",
    "MemoryPolicyRollbackPlan",
    "MemoryPolicyLifecycleStatus",
    "MemoryPolicyProposalPreview",
    "MemoryPolicyRegistrySnapshot",
    "MemoryPolicyVersion",
    "audit_memory_policy_lifecycle",
    "compare_memory_policy_versions",
    "inspect_memory_policy_registry",
    "preview_memory_policy_proposal",
    "propose_memory_policy",
    "review_memory_policy",
    "plan_memory_policy_activation",
    "activate_memory_policy",
    "plan_memory_policy_rollback",
    "rollback_memory_policy",
]

from memory.adaptive.dynamic_topic_blocks import (
    MemoryTopicBlock,
    MemoryTopicBlockLifecycleAudit,
    MemoryTopicBlockRegistrySnapshot,
    MemoryTopicBlockStatus,
    MemoryTopicDetection,
    MemoryTopicRoutingAction,
    MemoryTopicRoutingPlan,
    audit_dynamic_topic_blocks,
    detect_memory_topic,
    inspect_memory_topic_block_registry,
    plan_memory_topic_routing,
)

__all__ += [
    "MemoryTopicBlock",
    "MemoryTopicBlockLifecycleAudit",
    "MemoryTopicBlockRegistrySnapshot",
    "MemoryTopicBlockStatus",
    "MemoryTopicDetection",
    "MemoryTopicRoutingAction",
    "MemoryTopicRoutingPlan",
    "audit_dynamic_topic_blocks",
    "detect_memory_topic",
    "inspect_memory_topic_block_registry",
    "plan_memory_topic_routing",
]
