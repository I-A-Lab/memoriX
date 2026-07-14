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

__all__ = [
    "PressureComponents",
    "PressureHistoryStore",
    "PressureLevel",
    "PressureObservation",
    "PressureObservationInput",
    "PressureThresholds",
    "PressureWeights",
    "calculate_entropy",
    "calculate_memory_pressure",
    "calculate_momentum",
    "calculate_pressure_persistence",
    "calculate_surprise",
    "calculate_usage_ratio",
    "classify_pressure_level",
    "observe_memory_pressure",
]
