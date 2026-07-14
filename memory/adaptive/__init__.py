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
]
